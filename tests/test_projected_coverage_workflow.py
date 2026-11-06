"""Isolated geometric occupancy via structured MCP, with Python execution disabled."""
import asyncio,json,os,shutil
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait


def test_projected_coverage_capture_is_guarded_self_contained_and_source_preserving(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            planned=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='CoverageTree',recipe=recipe,expected_model=planned['model_sha256'],location=[4,3,1])
            foliage={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection='CoverageTree',foliage=foliage)
            await wait(client,'configure_botanical_foliage',collection='CoverageTree',foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection='CoverageTree')
            args={'collection':'CoverageTree','views':['FRONT'],'resolution':32,'samples':1,'material_fields':True,'component_ids':True}
            reference=await wait(client,'inspect_botanical_view_capture',**args)
            await wait(client,'capture_botanical_views',**args,directory='reference',expected_capture=reference['capture_sha256'])
            options={'reference_directory':'reference','view':'FRONT','samples':64}
            plan=await wait(client,'inspect_botanical_projected_coverage',**options)
            assert plan['target_pixels']>0 and plan['sampling']['master_samples']==65
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'capture_botanical_projected_coverage',**options,directory='stale-coverage',expected_plan='0'*64)
            assert not (root/'library/stale-coverage').exists()
            submitted=(await client.call_tool('capture_botanical_projected_coverage',{'params':options|{'directory':'coverage','expected_plan':plan['plan_sha256']}})).data
            try:
                # Editing instance remains available; no original source mutation.
                current=await wait(client,'inspect_botanical_tree',collection='CoverageTree')
                assert current['tree_sha256']==before['tree_sha256']
                done=(await client.call_tool('wait_operation',{'operation_id':submitted['operation_id'],'timeout_seconds':90})).data
                assert done['state']=='succeeded',done
            finally:
                state=(await client.call_tool('get_operation',{'operation_id':submitted['operation_id']})).data
                if state['state'] in {'queued','running'}:
                    await client.call_tool('cancel_operation',{'operation_id':submitted['operation_id']})
                    await client.call_tool('wait_operation',{'operation_id':submitted['operation_id'],'timeout_seconds':30})
            validated=await wait(client,'validate_render_job',directory='coverage')
            assert validated['projected_coverage']==plan
            assert validated['coverage_reports'][0]['coverage_mass_pixels']>0
            assert validated['coverage_reports'][0]['white_alpha_max_error']<=1e-6
            assert (await wait(client,'inspect_botanical_tree',collection='CoverageTree'))['tree_sha256']==before['tree_sha256']
            assert (await wait(client,'inspect_botanical_projected_coverage',**options))==plan
            # Immutable input snapshot needs neither reference archive nor editing tree.
            shutil.rmtree(root/'library/reference')
            copied=root/'library/copied-coverage';shutil.copytree(root/'library/coverage',copied)
            from mcpblender import render_jobs
            proof=render_jobs.validate_contents(copied,json.loads((copied/'job.json').read_text())['job_id'])
            assert proof['coverage_reports']==validated['coverage_reports']
            original=(copied/'manifest.json').read_bytes();bad=json.loads(original);bad['projected_coverage']['grid_sha256']='0'*64;(copied/'manifest.json').write_text(json.dumps(bad))
            with pytest.raises(ValueError,match='binding'):render_jobs.validate_contents(copied,bad['job_id'])
            (copied/'manifest.json').write_bytes(original)
            if destination:=os.environ.get('MCPBLENDER_PROJECTED_COVERAGE_EVIDENCE'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True);shutil.copytree(root/'library/coverage',out/'coverage',dirs_exist_ok=True);(out/'proof.json').write_text(json.dumps(validated,indent=2))
    asyncio.run(run())
