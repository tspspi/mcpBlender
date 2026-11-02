"""Verified visual baking and portable playback, through MCP without Python."""
import asyncio
import json
import math
import os
from pathlib import Path
import shutil
import struct

import pytest
from fastmcp.exceptions import ToolError

from test_asset_editing import assets_live, client_for, tool, pytestmark
from test_constraints import edit, inspect, sample
from test_skeletal_animation import make_limb


def test_visual_bake_preserves_source_and_exports_playback(assets_live):
    root, path = assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await make_limb(client, 'BakeSource', 'BakeSkin', x=12)
            await tool(client, 'create_animation_control', name='BakeControl')
            await tool(client, 'set_keyframes', name='BakeControl', data_path='rotation_euler',
                       keyframes=[{'frame':1,'value':[0,0,0]}, {'frame':9,'value':[1,0,.5]}])
            await edit(client, 'BakeSource', 'Bend', {'type':'COPY_ROTATION', 'target':{'name':'BakeControl'}, 'owner_space':'LOCAL', 'target_space':'LOCAL'}, bone='Tip')
            await client.call_tool('set_frame', {'frame':3})
            selected = (await client.call_tool('get_scene_info')).data['active_object']
            before = await inspect(client, 'BakeSource', 'Tip')
            source = await sample(client, 'BakeSource', frames=[1,3,5,7,9], meshes=['BakeSkin'], sample_limit=20)
            params = {'name':'BakeSource', 'output_rig':'BakedRig', 'clip':'BakedMotion',
                      'meshes':[{'source':'BakeSkin','output':'BakedSkin'}], 'frame_start':1, 'frame_end':9}
            result = (await client.call_tool('bake_constraint_animation', {'params':params,'wait':True})).data
            assert result['frame_count']==9 and result['max_vertex_world_error']<.0001 and result['max_pose_matrix_error']<.0001
            assert (await client.call_tool('get_scene_info')).data['active_object']==selected
            assert (await client.call_tool('get_scene_info')).data['frame']==3
            assert (await inspect(client, 'BakeSource', 'Tip'))['constraints_sha256']==before['constraints_sha256']
            assert (await inspect(client, 'BakedRig', 'Tip'))['total_constraints']==0
            baked = await tool(client, 'sample_animation', name='BakedRig', frames=[1,3,5,7,9], meshes=['BakedSkin'], sample_limit=20)
            for actual, expected in zip(baked['samples'], source['samples']):
                for a,b in zip(actual['bones'], expected['bones']):
                    assert math.dist(a['tail_world'], b['tail_world'])<.0001
                for key in ('min','max'):
                    assert actual['meshes'][0]['world_bounds'][key]==pytest.approx(expected['meshes'][0]['world_bounds'][key], abs=.0001)
            with pytest.raises(ToolError, match='unused'):
                await client.call_tool('bake_constraint_animation', {'params':params,'wait':True})
            await client.call_tool('save_blend', {'path':'visual-bake.blend'})
            await client.call_tool('open_blend', {'path':'visual-bake.blend'})
            await client.call_tool('select_objects', {'names':['BakedRig','BakedSkin']})
            await client.call_tool('export_glb', {'path':'visual-bake.glb'})
            blob = (root/'library/visual-bake.glb').read_bytes()
            length = struct.unpack_from('<I', blob, 12)[0]
            gltf = json.loads(blob[20:20+length])
            assert [a['name'] for a in gltf['animations']]==['BakedMotion']
            assert len(gltf['skins'])==1
            imported = (await client.call_tool('import_asset', {'path':'visual-bake.glb'})).data
            objects = (await client.call_tool('get_scene_info')).data['objects']
            rig = next(o['name'] for o in objects if o['name'] in imported['objects'] and o['type']=='ARMATURE')
            mesh = next(o['name'] for o in objects if o['name'] in imported['objects'] and o['type']=='MESH')
            replay = await tool(client, 'sample_animation', name=rig, frames=[1,3,5,7,9], meshes=[mesh])
            for actual, expected in zip(replay['samples'], source['samples']):
                for key in ('min','max'):
                    assert actual['meshes'][0]['world_bounds'][key]==pytest.approx(expected['meshes'][0]['world_bounds'][key], abs=.0002)
            source_after = await sample(client, 'BakeSource', frames=[1,3,5,7,9], meshes=['BakeSkin'])
            assert [s['meshes'][0]['geometry_sha256'] for s in source_after['samples']]==[s['meshes'][0]['geometry_sha256'] for s in source['samples']]
            if destination:=os.environ.get('MCPBLENDER_BAKE_EVIDENCE_DIR'):
                target=Path(destination);target.mkdir(parents=True,exist_ok=True)
                for name in ('visual-bake.blend','visual-bake.glb'):shutil.copy2(root/'library'/name,target/name)
                (target/'evidence.json').write_text(json.dumps({'result':result,'source':source,'baked':baked,'imported':replay},indent=2))
    asyncio.run(run())


def test_moving_object_refusal_rolls_back_outputs_and_restores_frame(assets_live):
    _, path = assets_live
    async def run():
        async with client_for(path) as client:
            await make_limb(client, 'MovingBakeSource', 'MovingBakeSkin', x=24)
            await tool(client, 'set_keyframes', name='MovingBakeSource', data_path='location',
                       keyframes=[{'frame':1,'value':[24,0,0]}, {'frame':5,'value':[25,0,0]}])
            await client.call_tool('set_frame', {'frame':1})
            before = {o['name'] for o in (await client.call_tool('get_scene_info')).data['objects']}
            with pytest.raises(ToolError, match='stationary'):
                await client.call_tool('bake_constraint_animation', {'params':{'name':'MovingBakeSource','output_rig':'RejectedRig','clip':'RejectedMotion','meshes':[{'source':'MovingBakeSkin','output':'RejectedSkin'}],'frame_start':1,'frame_end':5},'wait':True})
            scene = (await client.call_tool('get_scene_info')).data
            assert scene['frame']==1 and {o['name'] for o in scene['objects']}==before
            retry=(await client.call_tool('bake_constraint_animation', {'params':{'name':'MovingBakeSource','output_rig':'RejectedRig','clip':'RejectedMotion','frame_start':1,'frame_end':1},'wait':True})).data
            assert retry['frame_count']==1
    asyncio.run(run())


def test_ik_bake_reproduces_evaluated_chain(assets_live):
    _, path = assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client, 'create_armature', name='BakeIK', bones=[
                {'name':'Base','head':[0,0,0],'tail':[.15,0,1]},
                {'name':'Tip','head':[.15,0,1],'tail':[0,0,2],'parent':'Base','connected':True}])
            await tool(client, 'create_animation_control', name='BakeIKTarget', location=[.8,0,1.4])
            await tool(client, 'create_animation_control', name='BakeIKPole', location=[0,-2,1])
            await edit(client, 'BakeIK', 'Reach', {'type':'IK','target':{'name':'BakeIKTarget'},'pole':{'name':'BakeIKPole'}}, bone='Tip')
            await tool(client, 'set_keyframes', name='BakeIKTarget', data_path='location', keyframes=[
                {'frame':1,'value':[.8,0,1.4]},{'frame':9,'value':[-.6,.3,1.5]}])
            result=(await client.call_tool('bake_constraint_animation', {'params':{
                'name':'BakeIK','output_rig':'BakeIKOutput','clip':'BakedIKMotion','frame_start':1,'frame_end':9},'wait':True})).data
            assert result['max_pose_matrix_error']<.0001
            expected=await sample(client,'BakeIK',frames=[1,3,5,7,9])
            actual=await tool(client,'sample_animation',name='BakeIKOutput',frames=[1,3,5,7,9])
            for a,b in zip(actual['samples'],expected['samples']):
                for ab,bb in zip(a['bones'],b['bones']):
                    assert math.dist(ab['tail_world'],bb['tail_world'])<.0001
    asyncio.run(run())


def test_cancelled_visual_bake_removes_created_assets(assets_live):
    _, path = assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_armature',name='CancelVisualSource',bones=[
                {'name':f'Bone{i}','head':[i,0,0],'tail':[i,0,1]} for i in range(64)])
            await client.call_tool('set_frame',{'frame':7})
            before={o['name'] for o in (await client.call_tool('get_scene_info')).data['objects']}
            params={'name':'CancelVisualSource','output_rig':'CancelledVisualRig','clip':'CancelledVisualMotion','frame_start':1,'frame_end':500}
            queued=(await client.call_tool('bake_constraint_animation',{'params':params})).data
            for _ in range(500):
                operation=(await client.call_tool('get_operation',{'operation_id':queued['operation_id']})).data
                if operation.get('progress',{}).get('phase')=='baking visual pose': break
                assert operation['state'] not in {'failed','cancelled','succeeded'},operation
                await asyncio.sleep(.01)
            else:pytest.fail('Visual bake did not start keying')
            await client.call_tool('cancel_operation',{'operation_id':queued['operation_id']})
            result=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':30})).data
            assert result['state']=='cancelled',result
            scene=(await client.call_tool('get_scene_info')).data
            assert scene['frame']==7 and {o['name'] for o in scene['objects']}==before
            # Reusing the exact output names also proves the abandoned action was removed.
            retry=(await client.call_tool('bake_constraint_animation',{'params':params|{'frame_end':1},'wait':True})).data
            assert retry['frame_count']==1
    asyncio.run(run())
