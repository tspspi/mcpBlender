"""Opt-in full-density typed native/depth assembly; no optical acceptance claim."""
import asyncio,hashlib,json,os,shutil,time
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_capture_workflow import drain_captures

source=os.environ.get('MCPBLENDER_DENSE_SUBSET_SOURCE')
pytestmark=pytestmark+[pytest.mark.skipif(not source or not Path(source).is_file(),reason='Requires retained dense Canopy3 project')]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def test_full_density_public_capture_and_complementary_assembly(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(source,library/'source.blend')
    evidence=Path(os.environ['MCPBLENDER_DENSE_SUBSET_EVIDENCE']) if os.environ.get('MCPBLENDER_DENSE_SUBSET_EVIDENCE') else None
    if evidence:evidence.mkdir(parents=True,exist_ok=True)
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            async def operation(command,**params):
                job=(await client.call_tool('submit_operation',{'command':command,'params':params})).data
                deadline=time.monotonic()+3600
                while True:
                    try:state=(await client.call_tool('wait_operation',{'operation_id':job['operation_id'],'timeout_seconds':15})).data
                    except ToolError as exc:
                        if not any(t in str(exc) for t in ('Bridge timed out;','Bridge disconnected before a complete response')):raise
                        assert time.monotonic()<deadline;continue
                    if evidence:
                        (evidence/'progress.json').write_text(json.dumps({'command':command,'operation':state},indent=2))
                    assert state['state'] not in {'failed','cancelled','interrupted','outcome_unknown'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline
            await client.call_tool('open_blend',{'path':'source.blend'})
            original=await operation('inspect_botanical_tree',collection='Canopy3')
            assert original['valid'] and original['foliage']['metrics']['leaves']==88704
            opts={'collection':'Canopy3','views':['FRONT','BACK'],'resolution':512,'samples':1,'material_fields':True,'component_ids':True,'geometric_normals':True}
            plan=await operation('inspect_botanical_view_capture',**opts)
            capture=await operation('capture_botanical_views',**opts,directory='dense-capture',expected_capture=plan['capture_sha256'])
            assert capture['botanical_capture']['component_ids']['leaf_count']==88704
            data=await operation('inspect_botanical_capture_data',directory='dense-capture',views=['FRONT'])
            identity=data['views'][0]['component_ids'];assert identity['integer_ids_valid']
            if evidence:shutil.copytree(library/'dense-capture',evidence/'capture',dirs_exist_ok=True)
            depth={'directory':'dense-capture','view':'FRONT','component_filter':'LEAVES','render_role':'ALL_RAYS',
                   'settings':{'geometry_mode':'ADAPTIVE_NORMAL','plane_normal_source':'GEOMETRIC_AOV','tile_pixels':1,'max_slope':64,'max_triangles':131072}}
            primary_plan=await operation('inspect_botanical_depth_source',**depth)
            assert primary_plan['component_filter']['selected_pixels']==identity['leaf_pixels']
            assert primary_plan['geometry']['triangles']==2*identity['leaf_pixels']<=131072
            primary=await operation('create_botanical_depth_asset',**depth,collection='DenseLeafPrimary',expected_plan=primary_plan['plan_sha256'],accept_approximate_optics=True)
            subset={'directory':'dense-capture','views':['FRONT'],'selection':'UNOBSERVED','include_structure':True,'render_role':'SECONDARY','structure_render_role':'ALL_RAYS'}
            native_plan=await operation('inspect_botanical_subset_source',**subset)
            assert native_plan['observed_leaf_count']==identity['distinct_leaf_count']
            assert native_plan['selected_leaf_count']+native_plan['observed_leaf_count']==88704
            native=await operation('create_botanical_subset',**subset,subset_collection='DenseNativeComplement',expected_plan=native_plan['plan_sha256'])
            assert primary['valid'] and native['valid'] and native['source_unchanged']
            assert (await operation('inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==original['tree_sha256']
            await client.call_tool('save_blend',{'path':'dense-assembly.blend'})
            await client.call_tool('open_blend',{'path':'dense-assembly.blend'})
            after_open=await operation('inspect_botanical_tree',collection='Canopy3')
            if evidence:
                shutil.copy2(library/'dense-assembly.blend',evidence/'dense-assembly.blend')
                for file in (library/'dense-capture').rglob('*'):
                    if file.is_file():assert sha(file)==sha(evidence/'capture'/file.relative_to(library/'dense-capture'))
                assert sha(library/'dense-assembly.blend')==sha(evidence/'dense-assembly.blend')
            shutil.rmtree(library/'dense-capture')
            primary_read=await operation('inspect_botanical_depth_asset',collection='DenseLeafPrimary')
            native_read=await operation('inspect_botanical_subset',subset_collection='DenseNativeComplement')
            assert primary_read['valid'] and native_read['valid'] and native_read['source_unchanged']
            assert not primary_read['source_files_required'] and not native_read['capture_files_required']
            removed_primary=await operation('remove_botanical_depth_asset',collection='DenseLeafPrimary',expected_asset=primary_read['asset_sha256'])
            removed_native=await operation('remove_botanical_subset',subset_collection='DenseNativeComplement',expected_subset=native_read['subset_sha256'])
            assert (await operation('inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==after_open['tree_sha256']
            return {'capture':capture,'data':data,'primary_plan':primary_plan,'native_plan':native_plan,'primary':primary,'native':native,
                    'reopened_primary':primary_read,'reopened_native':native_read,'removed_primary':removed_primary,'removed_native':removed_native,
                    'scope':'Full-density functional typed assembly and persistence only. Assets remain hidden; no optical, angular, shadow, wind or population acceptance.'}
    try:
        proof=asyncio.run(run())
        if evidence:(evidence/'proof.json').write_text(json.dumps(proof,indent=2))
    finally:
        if evidence:
            for file in ('blender.log','bridge/broker.log'):
                if (root/file).exists():shutil.copy2(root/file,evidence/Path(file).name)
