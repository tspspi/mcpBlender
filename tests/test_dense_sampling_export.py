"""Full-density multigrid LOD delivery and source-free file verification."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import time
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_DENSE_LOD_PROJECT'),reason='Requires qualified dense LOD project')
def test_dense_lod_shared_delivery_and_source_free_validation(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(os.environ['MCPBLENDER_DENSE_LOD_PROJECT'],library/'source.blend')
    evidence=Path(os.environ['MCPBLENDER_DENSE_LOD_EXPORT_EVIDENCE_DIR']) if os.environ.get('MCPBLENDER_DENSE_LOD_EXPORT_EVIDENCE_DIR') else None
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            assert (await client.call_tool('bridge_status')).data['bridge']['pid']>0
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data
                deadline=time.monotonic()+3600
                while True:
                    try:state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':15})).data
                    except ToolError as exc:
                        if not any(t in str(exc) for t in ('Bridge timed out;','Bridge disconnected before a complete response')):raise
                        assert time.monotonic()<deadline;continue
                    if evidence:
                        evidence.mkdir(parents=True,exist_ok=True)
                        trace={'command':command,'operation':state}
                        (evidence/'latest-operation.json').write_text(json.dumps(trace,indent=2))
                        with (evidence/'operations.jsonl').open('a') as stream:stream.write(json.dumps(trace)+'\n')
                    assert state['state'] not in {'failed','cancelled','interrupted','outcome_unknown'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline
            await client.call_tool('open_blend',{'path':'source.blend'})
            source=await operation('inspect_botanical_tree',collection='Canopy3')
            profile=await operation('inspect_botanical_lods',lod_collection='SamplingLods')
            assert profile['valid'] and source['valid']
            assert [v['leaves'] for v in profile['levels']]==[88704,70000,60000]
            assert profile['plan']['sampling_method']=='AREA_PRIORITY_MULTIGRID_V2'
            material=await tool(client,'inspect_vegetation_materials',lod_collection='SamplingLods')
            result=await operation('export_botanical_lods',lod_collection='SamplingLods',expected_lods=profile['lods_sha256'],directory='delivery',material_mode='PARAMETERS',expected_materials=material['materials_sha256'])
            proof=result['proof']
            assert proof['placement_mode']=='SOURCE' and proof['shared_leaf_templates']==3 and len(proof['assets'])==9
            assert [v['leaf_instances'] for v in proof['levels']]==[88704,70000,60000]
            assert (await operation('inspect_botanical_lods',lod_collection='SamplingLods'))['lods_sha256']==profile['lods_sha256']
            assert (await operation('inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==source['tree_sha256']
            journal=await tool(client,'inspect_export_job',directory='delivery')
            assert journal['record']['kind']=='VEGETATION_LOD' and journal['record']['state']=='published' and journal['target_is_original_stage']
            assert journal['record']['binding']['materials_sha256']==material['materials_sha256']
            await operation('remove_botanical_lods',lod_collection='SamplingLods',expected_lods=profile['lods_sha256'])
            source=await operation('inspect_botanical_tree',collection='Canopy3')
            await operation('remove_botanical_tree',collection='Canopy3',expected_tree=source['tree_sha256'])
            standalone=await operation('validate_botanical_lod_bundle',directory='delivery')
            assert standalone==proof
            data=json.loads((library/'delivery/semantics.json').read_text())
            assert data['selection']['sampling_method']=='AREA_PRIORITY_MULTIGRID_V2'
            assert data['coordinates'] and len(data['selection']['quality_grids'])==3
            assert len(data['foliage']['leaves'])==88704 and len(data['templates'])==3
            assert set(data['levels'][2]['leaf_indices'])<set(data['levels'][1]['leaf_indices'])
            (library/'delivery-proof.json').write_text(json.dumps({'proof':proof,'source_free_proof':standalone,'journal':journal,'native_profile':profile},indent=2))
    try:asyncio.run(run())
    finally:
        if evidence and library.exists():shutil.copytree(library,evidence/'library',dirs_exist_ok=True)
        if evidence and (root/'blender.log').exists():shutil.copy2(root/'blender.log',evidence/'blender.log')
