"""Opt-in full-density structured coverage against retained native data."""
import asyncio,json,os,shutil
from pathlib import Path
import pytest
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait
from mcpblender import exr_scanline

source=os.environ.get('MCPBLENDER_PROJECTED_COVERAGE_SOURCE')
reference=os.environ.get('MCPBLENDER_PROJECTED_COVERAGE_REFERENCE')
control=os.environ.get('MCPBLENDER_PROJECTED_COVERAGE_CONTROL')
pytestmark=pytestmark+[pytest.mark.skipif(not source or not reference or not control,reason='Requires retained dense source, matching reference and private geometric control')]


def test_dense_structured_coverage_agrees_with_independent_native_control(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(source,library/'source.blend');shutil.copytree(reference,library/'reference')
    async def run():
        async with client_for(path) as client:
            await client.call_tool('open_blend',{'path':'source.blend'})
            before=await wait(client,'inspect_botanical_tree',collection='Canopy3')
            options={'reference_directory':'reference','view':'FRONT','samples':256}
            plan=await wait(client,'inspect_botanical_projected_coverage',**options)
            assert plan['reference']['leaf_instances']==88704 and plan['target_pixels']==54882
            submitted=(await client.call_tool('capture_botanical_projected_coverage',{'params':options|{'directory':'coverage','expected_plan':plan['plan_sha256']}})).data
            try:
                for _ in range(20):
                    done=(await client.call_tool('wait_operation',{'operation_id':submitted['operation_id'],'timeout_seconds':90})).data
                    if done['state'] not in {'queued','running'}:break
                assert done['state']=='succeeded',done
                result=await wait(client,'validate_render_job',directory='coverage')
                assert (await wait(client,'inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==before['tree_sha256']
            finally:
                done=(await client.call_tool('get_operation',{'operation_id':submitted['operation_id']})).data
                if done['state'] in {'queued','running'}:
                    await client.call_tool('cancel_operation',{'operation_id':submitted['operation_id']})
                    await client.call_tool('wait_operation',{'operation_id':submitted['operation_id'],'timeout_seconds':30})
            candidate=exr_scanline.decode(library/'coverage'/result['outputs'][0]['file'],['ProjectedCoverage.Combined.A'])['channels']['ProjectedCoverage.Combined.A']
            native=exr_scanline.decode(control,['Occlusion.Combined.A'])['channels']['Occlusion.Combined.A']
            # The private control snapshots observed leaves; the public worker
            # renders original full-density geometry through derived-ID mattes.
            # Check pixel alpha, not a brightness fit or averaged ID estimate.
            errors=[abs(a-b) for a,b in zip(candidate,native)]
            report={'max_alpha_error':max(errors),'mean_alpha_error':sum(errors)/len(errors),'public_mass':sum(candidate),'control_mass':sum(native)}
            assert report['mean_alpha_error']<.001,report
            if destination:=os.environ.get('MCPBLENDER_PROJECTED_COVERAGE_EVIDENCE'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True);shutil.copytree(library/'coverage',out/'coverage',dirs_exist_ok=True);(out/'proof.json').write_text(json.dumps({'validated':result,'comparison':report},indent=2))
    asyncio.run(run())
