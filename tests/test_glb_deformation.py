"""Read-only native GLB deformation inspection through queued MCP operations."""
import asyncio
from fastmcp.exceptions import ToolError
import pytest
from test_asset_editing import assets_live,client_for,tool,pytestmark


def test_structured_morph_export_and_independent_inspection(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            vertices=[[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]]
            faces=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
            await tool(client,'create_mesh',name='MorphInspection',vertices=vertices,faces=faces)
            await tool(client,'create_shape_key',name='MorphInspection',key='Roof',vertices=[{'vertex':i,'value':[0,0,.5]} for i in range(4,8)])
            await tool(client,'create_morph_clip',name='MorphInspection',clip='RoofLift',tracks=[{'key':'Roof','keyframes':[{'frame':1,'value':0},{'frame':5,'value':1},{'frame':9,'value':0}]}])
            await tool(client,'export_objects_glb',objects=['MorphInspection'],path='morph-inspection.glb',animations=True)
            before=await tool(client,'inspect_morph_animation',name='MorphInspection')
            scene=(await client.call_tool('get_scene_info')).data
            queued=(await client.call_tool('inspect_glb_deformation',{'params':{'path':'morph-inspection.glb','animation_samples':5,'sample_limit':2}})).data
            operation=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':60})).data
            assert operation['state']=='succeeded',operation
            assert 'storage' in operation['progress']
            report=operation['result'];assert report['deformation']['morph_targets']==['Roof'] and report['deformation']['joints']==[]
            assert len(report['samples'])==6 and len(report['sha256'])==64
            z=[s['sampled_world_bounds']['max'][1] for s in report['samples'] if s['clip'] is not None]
            assert max(z)-min(z)>.4
            after=await tool(client,'inspect_morph_animation',name='MorphInspection')
            assert {k:v for k,v in before.items() if k!='operation_id'}=={k:v for k,v in after.items() if k!='operation_id'}
            after_scene=(await client.call_tool('get_scene_info')).data
            assert {k:v for k,v in after_scene.items() if k!='operation_id'}=={k:v for k,v in scene.items() if k!='operation_id'}
            missing=await tool(client,'inspect_lod_source',name='MorphInspection',deformation='MORPH')
            assert missing['morph']['keys']
            (root/'library/bad.glb').write_bytes(b'bad')
            with pytest.raises(ToolError,match='GLB'):
                await client.call_tool('inspect_glb_deformation',{'params':{'path':'bad.glb'},'wait':True})
    asyncio.run(run())
