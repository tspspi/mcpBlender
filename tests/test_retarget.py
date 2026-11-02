"""Motion transfer across distinct real skeletons/skins via MCP, Python off."""
import asyncio
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess

from fastmcp.exceptions import ToolError
import pytest

from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_constraints import sample
from test_skeletal_animation import make_limb


async def plan(client,source,target,mappings,**params):
    return await tool(client,'inspect_animation_retarget',source=source,name=target,mappings=mappings,**params)


async def transfer(client,source,target,mappings,output,clip,**params):
    settings={k:v for k,v in params.items() if k in {'rotation_mode','translation','translation_scale','scale_mode','alignment_degrees','object_motion'}}
    info=await plan(client,source,target,mappings,**settings)
    result=(await client.call_tool('retarget_animation',{'params':{'source':source,'name':target,'mappings':mappings,'output_rig':output,'clip':clip,
        'expected_source_rig':info['source_rig_sha256'],'expected_target_rig':info['target_rig_sha256'],'frame_start':1,'frame_end':9,**params},'wait':True})).data
    return info,result


async def target_skin(client,rig,mesh,x=30):
    await tool(client,'create_armature',name=rig,location=[x,0,0],bones=[
        {'name':'Pelvis','head':[0,0,0],'tail':[0,0,2]},
        {'name':'Forearm','head':[0,0,2],'tail':[0,0,5],'parent':'Pelvis','connected':True}])
    vertices=[[x+dx,dy,z] for z in (0,1,2,3.5,5) for dx,dy in [(-.2,-.2),(.2,-.2),(.2,.2),(-.2,.2)]]
    faces=[[0,3,2,1],[16,17,18,19]]+[[4*z+i,4*z+(i+1)%4,4*(z+1)+(i+1)%4,4*(z+1)+i] for z in range(4) for i in range(4)]
    await tool(client,'create_mesh',name=mesh,vertices=vertices,faces=faces)
    await tool(client,'bind_mesh',name=mesh,armature=rig,method='EXPLICIT',weights=[{'vertex':i,'weights':{'Pelvis':1} if v[2]<2 else {'Forearm':1}} for i,v in enumerate(vertices)])


def test_proportions_names_root_motion_source_preservation_and_glb(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await make_limb(client,'MotionSource','SourceSkin',x=10)
            await target_skin(client,'CharacterTarget','CharacterSkin')
            await tool(client,'apply_material_preset',material='RetargetBlue',base_color=[.03,.18,.65,1],roughness=.4)
            await tool(client,'assign_material',objects=['CharacterSkin'],material='RetargetBlue')
            await tool(client,'create_animation_clip',name='MotionSource',clip='SourceMotion',tracks=[
                {'bone':'Tip','property':'rotation_degrees','keyframes':[{'frame':1,'value':[0,0,0]},{'frame':9,'value':[90,0,0]}]},
                {'bone':'Base','property':'location','keyframes':[{'frame':1,'value':[0,0,0]},{'frame':9,'value':[1,0,0]}]}])
            await tool(client,'set_keyframes',name='MotionSource',data_path='location',keyframes=[{'frame':1,'value':[10,0,0]},{'frame':9,'value':[14,0,0]}])
            await tool(client,'create_animation_clip',name='CharacterTarget',clip='TargetOriginal',tracks=[{'bone':'Forearm','property':'rotation_degrees','keyframes':[{'frame':1,'value':[0,0,15]},{'frame':9,'value':[0,0,25]}]}])
            await client.call_tool('set_frame',{'frame':3})
            mappings=[{'source':'Base','target':'Pelvis'},{'source':'Tip','target':'Forearm'}]
            before=await plan(client,'MotionSource','CharacterTarget',mappings)
            target_before=await sample(client,'CharacterTarget',frames=[1,5,9],meshes=['CharacterSkin'])
            source_before=await sample(client,'MotionSource',frames=[1,5,9],meshes=['SourceSkin'])
            info,result=await transfer(client,'MotionSource','CharacterTarget',mappings,'Transferred','TransferredWalk',meshes=[{'source':'CharacterSkin','output':'TransferredSkin'}])
            assert info['translation_scale']==2.5 and result['max_world_matrix_error']<.0001
            assert result['restored_frame']==3 and (await client.call_tool('get_scene_info')).data['frame']==3
            after=await plan(client,'MotionSource','CharacterTarget',mappings)
            assert (after['source_rig_sha256'],after['target_rig_sha256'])==(before['source_rig_sha256'],before['target_rig_sha256'])
            motion=await sample(client,'Transferred',frames=[1,5,9],bones=['Pelvis','Forearm'],meshes=['TransferredSkin'])
            for row,t in zip(motion['samples'],(0,.5,1)):
                expected=[30+12.5*t,-3*math.sin(t*math.pi/2),2+3*math.cos(t*math.pi/2)]
                assert row['bones'][1]['tail_world']==pytest.approx(expected,abs=.001)
            assert len({r['meshes'][0]['geometry_sha256'] for r in motion['samples']})==3
            for name,mesh,original in [('MotionSource','SourceSkin',source_before),('CharacterTarget','CharacterSkin',target_before)]:
                current=await sample(client,name,frames=[1,5,9],meshes=[mesh])
                assert [r['meshes'][0]['geometry_sha256'] for r in current['samples']]==[r['meshes'][0]['geometry_sha256'] for r in original['samples']]
            await client.call_tool('save_blend',{'path':'retarget.blend'})
            await client.call_tool('open_blend',{'path':'retarget.blend'})
            await client.call_tool('select_objects',{'names':['Transferred','TransferredSkin']})
            await client.call_tool('export_glb',{'path':'retarget.glb'})
            blob=(root/'library/retarget.glb').read_bytes();length=struct.unpack_from('<I',blob,12)[0];gltf=json.loads(blob[20:20+length])
            assert len(gltf['skins'])==len(gltf['meshes'])==1 and [a['name'] for a in gltf['animations']]==['TransferredWalk']
            await client.call_tool('set_frame',{'frame':5})
            await tool(client,'configure_render',samples=8,resolution_x=256,resolution_y=192)
            await client.call_tool('run_action',{'action':'preview_setup','inputs':{'objects':['TransferredSkin'],'prefix':'RetargetView'},'wait':True})
            await tool(client,'frame_objects',name='RetargetView_Camera',objects=['TransferredSkin'],direction=[.2,-1,.3])
            queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':'retarget.png','width':256,'height':192,'camera':'RetargetView_Camera','engine':'CYCLES'}})).data
            rendered=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':60})).data
            assert rendered['state']=='succeeded',rendered
            rgb=subprocess.run(['ffmpeg','-v','error','-i',str(root/'library/retarget.png'),'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True,timeout=20).stdout
            assert sum(b>r+30 and b>g+20 for r,g,b in zip(rgb[0::3],rgb[1::3],rgb[2::3]))>300
            await client.call_tool('save_blend',{'path':'retarget.blend','overwrite':True})
            imported=(await client.call_tool('import_asset',{'path':'retarget.glb'})).data
            objects=(await client.call_tool('get_scene_info')).data['objects']
            imported_rig=next(o['name'] for o in objects if o['name'] in imported['objects'] and o['type']=='ARMATURE')
            imported_info=await tool(client,'inspect_rig',name=imported_rig)
            imported_mesh=next(m['name'] for m in imported_info['meshes'] if m['name'] in imported['objects'])
            replay=await sample(client,imported_rig,frames=[1,5,9],meshes=[imported_mesh])
            for a,b in zip(replay['samples'],motion['samples']):
                for side in ('min','max'):assert a['meshes'][0]['world_bounds'][side]==pytest.approx(b['meshes'][0]['world_bounds'][side],abs=.0003)
            if destination:=os.environ.get('MCPBLENDER_RETARGET_EVIDENCE_DIR'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                for name in ('retarget.blend','retarget.glb','retarget.png'):shutil.copy2(root/'library'/name,out/name)
                (out/'comparison.json').write_text(json.dumps({'plan':info,'result':result,'motion':motion,'imported':replay},indent=2))
    asyncio.run(run())


def test_armature_delta_different_rest_axes_and_corrections(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await make_limb(client,'AxisSource','AxisSourceSkin',x=0)
            await tool(client,'create_animation_clip',name='AxisSource',clip='AxisBend',tracks=[{'bone':'Tip','property':'rotation_degrees','keyframes':[{'frame':1,'value':[0,0,0]},{'frame':9,'value':[90,0,0]}]}])
            await tool(client,'create_armature',name='AxisTarget',bones=[{'name':'Root','head':[0,0,0],'tail':[0,0,1]},
                {'name':'Arm','head':[0,0,1],'tail':[1,0,1],'parent':'Root','connected':True,'roll_degrees':30}])
            mappings=[{'source':'Base','target':'Root'},{'source':'Tip','target':'Arm'}]
            await transfer(client,'AxisSource','AxisTarget',mappings,'GlobalTransfer','GlobalAxis',rotation_mode='ARMATURE_DELTA',translation='NONE',object_motion='IGNORE')
            global_pose=await sample(client,'GlobalTransfer',frames=[1,9],bones=['Arm'])
            for row in global_pose['samples']:assert row['bones'][0]['tail_world']==pytest.approx([1,0,1],abs=.001)
            await transfer(client,'AxisSource','AxisTarget',mappings,'LocalTransfer','LocalAxis',translation='NONE',object_motion='IGNORE')
            local_pose=await sample(client,'LocalTransfer',frames=[1,9],bones=['Arm'])
            assert math.dist(local_pose['samples'][1]['bones'][0]['tail_world'],[1,0,1])>1
            corrected=[mappings[0],mappings[1]|{'rotation_correction_degrees':[0,0,90]}]
            await transfer(client,'AxisSource','AxisTarget',corrected,'CorrectedTransfer','CorrectedAxis',translation='NONE',object_motion='IGNORE')
            corrected_pose=await sample(client,'CorrectedTransfer',frames=[9],bones=['Arm'])
            assert corrected_pose['samples'][0]['bones'][0]['tail_world']==pytest.approx([1,0,1],abs=.001)
            await tool(client,'create_armature',name='OffsetTarget',bones=[{'name':'Hip','head':[0,0,2],'tail':[0,0,5]}])
            await transfer(client,'AxisSource','OffsetTarget',[{'source':'Tip','target':'Hip'}],'OffsetTransfer','OffsetMotion',rotation_mode='ARMATURE_DELTA',object_motion='IGNORE')
            offset_pose=await sample(client,'OffsetTransfer',frames=[9],bones=['Hip'])
            assert offset_pose['samples'][0]['bones'][0]['head_world']==pytest.approx([0,0,2],abs=.001)
            assert offset_pose['samples'][0]['bones'][0]['tail_world']==pytest.approx([0,-3,2],abs=.001)
    asyncio.run(run())


def test_time_mapping_scale_modes_unmapped_bones_and_static_morph_copy(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await make_limb(client,'ScaleSource','ScaleSourceSkin',x=0)
            await target_skin(client,'ScaleTarget','ScaleTargetSkin',x=20)
            await tool(client,'create_shape_key',name='ScaleTargetSkin',key='Bulk',vertices=[{'vertex':i,'value':[.1,0,0]} for i in range(20)])
            await tool(client,'set_shape_key_weights',name='ScaleTargetSkin',values={'Bulk':.5})
            target_static=await tool(client,'inspect_mesh',name='ScaleTargetSkin')
            await tool(client,'create_animation_clip',name='ScaleSource',clip='ScaleMotion',tracks=[{'bone':'Tip','property':'scale','keyframes':[{'frame':1,'value':[1,1,1]},{'frame':9,'value':[1,2,1]}]}])
            mappings=[{'source':'Tip','target':'Forearm'}]
            _,result=await transfer(client,'ScaleSource','ScaleTarget',mappings,'NoStretch','NoStretchClip',object_motion='IGNORE',translation='NONE',frame_start=101,frame_end=105,source_start=1,playback_speed=2,meshes=[{'source':'ScaleTargetSkin','output':'NoStretchSkin'}])
            assert result['ignored_source_scale_bones']==['Tip'] and result['frame_count']==5
            rest=await sample(client,'NoStretch',frames=[101,103,105],bones=['Pelvis','Forearm'],meshes=['NoStretchSkin'])
            assert all(r['bones'][1]['tail_world']==pytest.approx([20,0,5],abs=.001) for r in rest['samples'])
            _,result=await transfer(client,'ScaleSource','ScaleTarget',mappings,'WithStretch','WithStretchClip',scale_mode='COPY_LOCAL',object_motion='IGNORE',translation='NONE',meshes=[{'source':'ScaleTargetSkin','output':'WithStretchSkin'}])
            posed=await sample(client,'WithStretch',frames=[1,5,9],bones=['Forearm'],meshes=['WithStretchSkin'])
            assert [r['bones'][0]['tail_world'][2] for r in posed['samples']]==pytest.approx([5,6.5,8],abs=.001)
            original=await tool(client,'inspect_mesh',name='ScaleTargetSkin')
            assert original['geometry_sha256']==target_static['geometry_sha256']
            # Copied shape data remains independently editable, without changing
            # the target's reference shape weight or vertex geometry.
            await tool(client,'set_shape_key_weights',name='WithStretchSkin',values={'Bulk':1})
            assert (await tool(client,'inspect_mesh',name='ScaleTargetSkin'))['geometry_sha256']==target_static['geometry_sha256']
            _,aligned=await transfer(client,'ScaleSource','ScaleTarget',mappings,'AlignedGlobal','AlignedGlobalClip',rotation_mode='ARMATURE_DELTA',scale_mode='COPY_LOCAL',object_motion='IGNORE',translation='NONE')
            assert aligned['max_world_matrix_error']<.0001
            await client.call_tool('set_object_transform',{'name':'ScaleSource','scale':[.0001,.0001,.0001]})
            _,tiny=await transfer(client,'ScaleSource','ScaleTarget',mappings,'TinyUnitTransfer','TinyUnitClip',translation='NONE')
            assert tiny['max_world_matrix_error']<.0001 and tiny['within_nla_key_limit']
            _,fractional=await transfer(client,'ScaleSource','ScaleTarget',mappings,'FractionalTransfer','FractionalClip',translation='NONE',object_motion='IGNORE',scale_mode='COPY_LOCAL',frame_start=201,frame_end=203,source_start=1.25,playback_speed=.5)
            fractional_pose=await sample(client,'FractionalTransfer',frames=[201,202,203],bones=['Forearm'])
            assert [r['bones'][0]['tail_world'][2] for r in fractional_pose['samples']]==pytest.approx([5.09375,5.28125,5.46875],abs=.001)
    asyncio.run(run())


def test_stale_maps_unsupported_root_scale_rollback_and_cancel(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await make_limb(client,'FailureSource','FailureSourceSkin',x=0)
            await target_skin(client,'FailureTarget','FailureTargetSkin',x=40)
            await tool(client,'create_shape_key',name='FailureTargetSkin',key='Detail',vertices=[{'vertex':0,'value':[.1,0,0]}])
            mappings=[{'source':'Base','target':'Pelvis'},{'source':'Tip','target':'Forearm'}]
            state=await plan(client,'FailureSource','FailureTarget',mappings)
            await tool(client,'set_keyframes',name='FailureSource',data_path='scale',keyframes=[{'frame':1,'value':[1,1,1]},{'frame':9,'value':[2,2,2]}])
            params={'source':'FailureSource','name':'FailureTarget','mappings':mappings,'output_rig':'FailedTransfer','clip':'FailedTransferClip',
                    'expected_source_rig':state['source_rig_sha256'],'expected_target_rig':state['target_rig_sha256'],'frame_start':1,'frame_end':9,'meshes':[{'source':'FailureTargetSkin','output':'FailedTransferSkin'}]}
            with pytest.raises(ToolError,match='stale'):
                await client.call_tool('retarget_animation',{'params':params,'wait':True})
            await client.call_tool('set_frame',{'frame':3})
            before={o['name'] for o in (await client.call_tool('get_scene_info')).data['objects']}
            state=await plan(client,'FailureSource','FailureTarget',mappings)
            params|={'expected_source_rig':state['source_rig_sha256'],'expected_target_rig':state['target_rig_sha256']}
            with pytest.raises(ToolError,match='rigid'):
                await client.call_tool('retarget_animation',{'params':params,'wait':True})
            assert {o['name'] for o in (await client.call_tool('get_scene_info')).data['objects']}==before
            assert (await client.call_tool('get_scene_info')).data['frame']==3
            # Reusing names proves that the failed action/resource transaction
            # was discarded. Explicitly ignore unsupported object scaling.
            _,result=await transfer(client,'FailureSource','FailureTarget',mappings,'FailedTransfer','FailedTransferClip',object_motion='IGNORE',meshes=[{'source':'FailureTargetSkin','output':'FailedTransferSkin'}])
            assert result['max_world_matrix_error']<.0001
            assert (await tool(client,'inspect_shape_keys',name='FailureTargetSkin'))['total_keys']==2
            await tool(client,'set_keyframes',name='FailureSource',data_path='scale',keyframes=[{'frame':1,'value':[0,0,0]}])
            _,ignored=await transfer(client,'FailureSource','FailureTarget',mappings,'IgnoredObjectScale','IgnoredObjectClip',object_motion='IGNORE')
            assert ignored['max_world_matrix_error']<.0001
            await tool(client,'create_armature',name='CancelRetargetSource',bones=[{'name':f'Bone{i}','head':[i,0,0],'tail':[i,0,1]} for i in range(64)])
            await tool(client,'create_armature',name='CancelRetargetTarget',bones=[{'name':f'Bone{i}','head':[i,0,0],'tail':[i,0,1]} for i in range(64)])
            maps=[{'source':f'Bone{i}','target':f'Bone{i}'} for i in range(64)]
            state=await plan(client,'CancelRetargetSource','CancelRetargetTarget',maps)
            before={o['name'] for o in (await client.call_tool('get_scene_info')).data['objects']}
            params={'source':'CancelRetargetSource','name':'CancelRetargetTarget','mappings':maps,'output_rig':'CancelledRetarget','clip':'CancelledRetargetClip',
                    'expected_source_rig':state['source_rig_sha256'],'expected_target_rig':state['target_rig_sha256'],'frame_start':1,'frame_end':500}
            queued=(await client.call_tool('retarget_animation',{'params':params})).data
            for _ in range(500):
                operation=(await client.call_tool('get_operation',{'operation_id':queued['operation_id']})).data
                if operation.get('progress',{}).get('phase')=='retargeting motion':break
                assert operation['state'] not in {'succeeded','failed','cancelled'},operation
                await asyncio.sleep(.01)
            else:pytest.fail('Retargeting did not start keying')
            assert 'storage' in operation['progress']
            await client.call_tool('cancel_operation',{'operation_id':queued['operation_id']})
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':30})).data
            assert done['state']=='cancelled',done
            assert {o['name'] for o in (await client.call_tool('get_scene_info')).data['objects']}==before
            assert (await client.call_tool('get_scene_info')).data['frame']==3
            params['frame_end']=1
            retry=(await client.call_tool('retarget_animation',{'params':params,'wait':True})).data
            assert retry['frame_count']==1
    asyncio.run(run())


def test_current_nla_driver_ik_timeline_transfers_evaluated_joint_motion(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            from test_constraints import edit as edit_constraint
            from test_animation_drivers import configure
            from test_animation_curves import key
            from test_nla import edit as edit_nla
            await tool(client,'create_armature',name='CompositeSource',bones=[{'name':'Base','head':[0,0,0],'tail':[.15,0,1]},
                {'name':'Tip','head':[.15,0,1],'tail':[0,0,2],'parent':'Base','connected':True}])
            await target_skin(client,'CompositeTarget','CompositeTargetSkin',x=60)
            await tool(client,'create_animation_control',name='CompositeGoal',location=[.8,0,1.4])
            await tool(client,'create_animation_control',name='CompositePole',location=[0,-2,1])
            await edit_constraint(client,'CompositeSource','Reach',{'type':'IK','target':{'name':'CompositeGoal'},'pole':{'name':'CompositePole'}},bone='Tip')
            await tool(client,'set_animation_property',name='CompositeSource',property='IKWeight',value=0)
            await configure(client,'CompositeSource',{'kind':'CONSTRAINT','bone':'Tip','constraint':'Reach'},
                            {'expression':'blend','variables':[{'kind':'PROPERTY','name':'blend','object':'CompositeSource','property':'IKWeight'}]})
            await key(client,'CompositeSource','CompositeControlClip',property='custom_scalar',custom_property='IKWeight',keyframes=[{'frame':1,'value':0},{'frame':9,'value':1}])
            await edit_nla(client,'configure_nla_track','CompositeSource',track='ControlLayer')
            await edit_nla(client,'configure_nla_strip','CompositeSource',track='ControlLayer',strip='ControlStrip',settings={'clip':'CompositeControlClip','start':11,'action_start':1,'action_end':9,'scale':2})
            await edit_nla(client,'configure_nla_playback','CompositeSource',clear_active_action=True,reset_base=True)
            maps=[{'source':'Base','target':'Pelvis'},{'source':'Tip','target':'Forearm'}]
            _,result=await transfer(client,'CompositeSource','CompositeTarget',maps,'CompositeRetarget','CompositeRetargetClip',frame_start=101,frame_end=109,source_start=11,playback_speed=2,meshes=[{'source':'CompositeTargetSkin','output':'CompositeRetargetSkin'}])
            assert result['max_world_matrix_error']<.0001
            def multiply(a,b):return [[sum(a[i][k]*b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
            def transpose(a):return [[a[j][i] for j in range(3)] for i in range(3)]
            def rotation(m):return [r[:3] for r in m[:3]]
            def local(bone,parent):
                rest=rotation(bone['rest_matrix']);pose=rotation(bone['pose_matrix'])
                if parent: return multiply(multiply(multiply(transpose(rest),rotation(parent['rest_matrix'])),transpose(rotation(parent['pose_matrix']))),pose)
                return multiply(transpose(rest),pose)
            for sf,tf in ((11,101),(19,105),(27,109)):
                await client.call_tool('set_frame',{'frame':sf});src=(await tool(client,'inspect_rig',name='CompositeSource'))['bones']
                await client.call_tool('set_frame',{'frame':tf});dst=(await tool(client,'inspect_rig',name='CompositeRetarget'))['bones']
                for i in range(2):
                    actual=local(dst[i],dst[0] if i else None);expected=local(src[i],src[0] if i else None)
                    assert max(abs(x-y) for a,b in zip(actual,expected) for x,y in zip(a,b))<.002
            motion=await sample(client,'CompositeRetarget',frames=[101,105,109],meshes=['CompositeRetargetSkin'])
            assert len({r['meshes'][0]['geometry_sha256'] for r in motion['samples']})==3
    asyncio.run(run())
