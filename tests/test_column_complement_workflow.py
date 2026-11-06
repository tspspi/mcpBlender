"""Structured component-column complement with private shader/image ownership."""
import asyncio,json,os,shutil,subprocess
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live as _assets_live,client_for,pytestmark
from test_depth_candidates import wait


@pytest.fixture
def assets_live():
    yield from _assets_live.__wrapped__()


@pytest.mark.parametrize('reduction',[None,{'triangle_budget':32,'max_relative_error':.02,'max_area_relative_error':.02,'error_samples':512}])
def test_column_complement_native_projector_guards_and_persistence(assets_live,reduction):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='ColumnTree',recipe=recipe,expected_model=plan['model_sha256'],location=[4,3,1])
            foliage={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection='ColumnTree',foliage=foliage)
            await wait(client,'configure_botanical_foliage',collection='ColumnTree',foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection='ColumnTree')
            opts={'collection':'ColumnTree','views':['FRONT'],'resolution':32,'samples':1,'material_fields':True,'component_ids':True}
            capture=await wait(client,'inspect_botanical_view_capture',**opts)
            await wait(client,'capture_botanical_views',**opts,directory='reference',expected_capture=capture['capture_sha256'])
            args={'directory':'reference','selection':'COLUMN_COMPLEMENT','views':['FRONT']}
            if reduction is not None:args['template_reduction']=reduction
            plan=await wait(client,'inspect_botanical_subset_source',**args)
            if reduction is not None:
                reduced=plan['template_reduction'];assert reduced['expanded_reduced_leaf_triangles']<reduced['expanded_source_leaf_triangles']
                assert all(v['triangles']<=32 and v['source_normals_transferred'] for v in reduced['variants'])
                with pytest.raises(ToolError,match='surface error'):
                    await wait(client,'inspect_botanical_subset_source',**(args|{'template_reduction':reduction|{'max_relative_error':1e-9}}))
            assert plan['selected_leaf_count']==plan['source_leaf_count'] and plan['column_complement']['target_pixels']>0
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_subset',**args,subset_collection='BadColumn',expected_plan='0'*64)
            made=await wait(client,'create_botanical_subset',**args,subset_collection='ColumnComplement',expected_plan=plan['plan_sha256'])
            assert made['valid'] and made['source_unchanged']
            assert (await wait(client,'inspect_botanical_tree',collection='ColumnTree'))['tree_sha256']==before['tree_sha256']
            await client.call_tool('save_blend',{'path':'column.blend'})
            if destination:=os.environ.get('MCPBLENDER_COLUMN_EVIDENCE'):
                out=Path(destination)/('reduced' if reduction else 'original');out.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'library/column.blend',out/'column.blend');shutil.copytree(root/'library/reference',out/'reference',dirs_exist_ok=True)
            helper=Path(__file__).with_name('native_column_complement.py')
            probe=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(helper),'--',str(helper.resolve().parents[1]),str(root/'library/column.blend'),str(root/'library/reference'),str(root/'native-check')],capture_output=True,text=True,timeout=90)
            if destination:=os.environ.get('MCPBLENDER_COLUMN_EVIDENCE'):
                out=Path(destination)/('reduced' if reduction else 'original');out.mkdir(parents=True,exist_ok=True);(out/'native.log').write_text(probe.stdout+probe.stderr)
            assert probe.returncode==0,probe.stdout+probe.stderr
            if destination:
                shutil.copy2(root/'library/column.blend',out/'column.blend');assert (root/'library/column.blend').read_bytes()==(out/'column.blend').read_bytes();(out/'plan.json').write_text(json.dumps(plan,indent=2));shutil.copytree(root/'native-check',out/'native-check',dirs_exist_ok=True)
            shutil.rmtree(root/'library/reference')
            await client.call_tool('open_blend',{'path':'column.blend'})
            state=await wait(client,'inspect_botanical_subset',subset_collection='ColumnComplement');assert state['valid'] and state['source_unchanged'] and not state['capture_files_required']
            deleted=await wait(client,'remove_botanical_subset',subset_collection='ColumnComplement',expected_subset=state['subset_sha256']);assert deleted['source_preserved'] and deleted['private_datablocks']>12
            return {'created':made,'removed':deleted}
    result=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_COLUMN_EVIDENCE'):(Path(destination)/('reduced' if reduction else 'original')/'proof.json').write_text(json.dumps(result,indent=2))
