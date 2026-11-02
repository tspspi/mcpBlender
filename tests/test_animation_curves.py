"""Real constrained controller and action-curve refinement with Python off."""
import asyncio
import math
import os
from pathlib import Path
import shutil
import subprocess

from fastmcp.exceptions import ToolError
import pytest

from test_asset_editing import assets_live, client_for, tool, pytestmark
from test_constraints import edit, sample


async def channels(client,name,**params):
    return await tool(client,'inspect_animation_channels',name=name,**params)


async def key(client,name,clip,**params):
    state=await channels(client,name)
    return await tool(client,'set_control_keyframes',name=name,output_clip=clip,expected_animation=state['animation_sha256'],**params)


async def change(client,name,clip,**params):
    state=await channels(client,name)
    return await tool(client,'edit_animation_curve',name=name,output_clip=clip,expected_animation=state['animation_sha256'],**params)


def test_bone_controls_after_ik_and_constraint_influence(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_armature',name='CurveRig',bones=[
                {'name':'Base','head':[0,0,0],'tail':[.15,0,1]},
                {'name':'Tip','head':[.15,0,1],'tail':[0,0,2],'parent':'Base','connected':True},
                {'name':'Control','head':[.8,0,1.4],'tail':[.8,0,1.7],'deform':False}])
            await tool(client,'create_animation_control',name='CurvePole',location=[0,-2,1])
            await edit(client,'CurveRig','Reach',{'type':'IK','target':{'name':'CurveRig','bone':'Control'},'pole':{'name':'CurvePole'}},bone='Tip')
            await client.call_tool('set_frame',{'frame':3})
            created=await key(client,'CurveRig','ControlFirst',bone='Control',property='location',keyframes=[
                {'frame':1,'value':[0,0,0]},{'frame':9,'value':[-1.4,.1,-.3]}])
            assert created['source_action'] is None and created['restored_frame']==3
            expected=[[.8,0,1.4],[.1,.15,1.45],[-.6,.3,1.5]]
            motion=await sample(client,'CurveRig',frames=[1,5,9],bones=['Tip','Control'])
            for row,goal in zip(motion['samples'],expected):assert math.dist(row['bones'][0]['tail_world'],goal)<.015
            influence=await key(client,'CurveRig','ControlAndInfluence',bone='Tip',constraint='Reach',property='influence',keyframes=[
                {'frame':1,'value':0},{'frame':9,'value':1}])
            assert influence['source_action']=='ControlFirst' and influence['source_preserved']
            motion=await sample(client,'CurveRig',frames=[1,9],bones=['Tip'])
            assert motion['samples'][0]['bones'][0]['tail_world']==pytest.approx([0,0,2],abs=.001)
            assert math.dist(motion['samples'][1]['bones'][0]['tail_world'],expected[-1])<.015
            paths={c['data_path'] for c in influence['channels']}
            assert 'pose.bones["Control"].location' in paths
            assert 'pose.bones["Tip"].constraints["Reach"].influence' in paths
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'set_control_keyframes',name='CurveRig',output_clip='StaleController',expected_animation=created['animation_sha256'],bone='Control',property='location',keyframes=[{'frame':1,'value':[0,0,0]}])
            await client.call_tool('save_blend',{'path':'controller-curves.blend'})
            await client.call_tool('open_blend',{'path':'controller-curves.blend'})
            info=await channels(client,'CurveRig',key_limit=1)
            old=await tool(client,'inspect_animation',name='CurveRig',clip='ControlFirst')
            assert old['detail']['total_tracks']==3
            assert info['action']=='ControlAndInfluence' and info['channels'][0]['next_key_offset']==1
            if dest:=os.environ.get('MCPBLENDER_CURVE_EVIDENCE_DIR'):
                output=Path(dest);output.mkdir(parents=True,exist_ok=True)
                shutil.copy2(_/'library/controller-curves.blend',output/'controller-curves.blend')
            continued=await channels(client,'CurveRig',limit=1,key_offset=1)
            assert continued['animation_sha256']==info['animation_sha256'] and continued['channels'][0]['keys'][0]['co'][0]==9
    asyncio.run(run())


def test_curve_handles_easing_retime_delete_and_source_isolation(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_animation_control',name='CurveObject')
            initial=await key(client,'CurveObject','ObjectOriginal',property='location',keyframes=[
                {'frame':1,'value':[0,2,3]},{'frame':5,'value':[4,2,3]},{'frame':9,'value':[8,2,3]}])
            await tool(client,'duplicate_object',name='CurveObject',new_name='CurvePeer')
            peer_before=await channels(client,'CurvePeer')
            curve_path='location'
            modified=await change(client,'CurveObject','ObjectBezier',data_path=curve_path,component=0,frames=[1,5],settings={'operation':'INTERPOLATION','interpolation':'BEZIER'})
            modified=await change(client,'CurveObject','ObjectHandles',data_path=curve_path,component=0,frames=[1],settings={
                'operation':'HANDLES','left_type':'FREE','right_type':'FREE','left':[0,0],'right':[4,0]})
            assert modified['channels'][0]['keys'][0]['right']==pytest.approx([4,0])
            at=(await sample(client,'CurveObject',frames=[3]))['samples'][0]['matrix_world'][0][3]
            assert 0<at<2  # shaped ease-in, different from original linear x=2
            eased=await change(client,'CurveObject','ObjectEasing',data_path=curve_path,component=0,frames=[5],settings={
                'operation':'INTERPOLATION','interpolation':'QUAD','easing':'EASE_IN'})
            at7=(await sample(client,'CurveObject',frames=[7]))['samples'][0]['matrix_world'][0][3]
            assert at7==pytest.approx(5,abs=.001)
            retimed=await change(client,'CurveObject','ObjectRetimed',data_path=curve_path,component=0,frames=[1,5,9],settings={
                'operation':'TRANSFORM','pivot_frame':1,'time_scale':2,'time_offset':2,'value_scale':2,'value_offset':1})
            keys=retimed['channels'][0]['keys']
            assert [k['co'] for k in keys]==[[3,1],[11,9],[19,17]]
            assert keys[0]['right']==pytest.approx([9,1])
            at15=(await sample(client,'CurveObject',frames=[15]))['samples'][0]['matrix_world'][0][3]
            assert at15==pytest.approx(11,abs=.001)
            state=await channels(client,'CurveObject')
            saved_frame=(await client.call_tool('get_scene_info')).data['frame']
            with pytest.raises(ToolError,match='collide'):
                await change(client,'CurveObject','CollisionClip',data_path=curve_path,component=0,frames=[3],settings={'operation':'TRANSFORM','time_offset':8})
            assert (await channels(client,'CurveObject'))['animation_sha256']==state['animation_sha256']
            with pytest.raises(ToolError,match='numeric bounds'):
                await change(client,'CurveObject','ObjectDeleted',data_path=curve_path,component=0,frames=[11],settings={'operation':'TRANSFORM','value_scale':1e12})
            assert (await channels(client,'CurveObject'))['animation_sha256']==state['animation_sha256']
            assert (await client.call_tool('get_scene_info')).data['frame']==saved_frame
            deleted=await change(client,'CurveObject','ObjectDeleted',data_path=curve_path,component=0,frames=[3,19],settings={'operation':'DELETE'})
            assert [k['co'] for k in deleted['channels'][0]['keys']]==[[11,9]]
            peer_after=await channels(client,'CurvePeer')
            assert peer_before['animation_sha256']==peer_after['animation_sha256']
            assert peer_after['action']=='ObjectOriginal'
            at3=(await sample(client,'CurvePeer',frames=[3]))['samples'][0]['matrix_world'][0][3]
            assert at3==pytest.approx(2,abs=.001)
            assert (await channels(client,'CurveObject',offset=1,limit=1))['channels'][0]['keys']==initial['channels'][1]['keys']
            with pytest.raises(ToolError,match='Channel must'):
                await change(client,'CurveObject','BadPath',data_path='hide_render',component=0,frames=[11],settings={'operation':'DELETE'})
    asyncio.run(run())


def test_native_modifiers_drivers_nla_samples_and_rotation_modes(assets_live):
    root,path=assets_live
    library=root/'library';library.mkdir(exist_ok=True)
    script=root/'native-curves.py'
    script.write_text('''import bpy,sys
bpy.ops.wm.read_factory_settings(use_empty=True)
def make(name):
 obj=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(obj)
 for f,x in ((1,0),(9,8)):
  obj.location.x=x;obj.keyframe_insert(data_path="location",frame=f,group="Motion")
 bag=obj.animation_data.action.layers[0].strips[0].channelbag(obj.animation_data.action_slot)
 return obj,bag.fcurves[0]
obj,c=make("ImportedModified");c.modifiers.new("NOISE")
obj,c=make("ImportedDriver");obj.driver_add("location",0).driver.expression="1.0"
obj,c=make("ImportedNLA");track=obj.animation_data.nla_tracks.new();track.strips.new("Layer",1,obj.animation_data.action)
obj,c=make("ImportedLocked");c.group.lock=True
obj,c=make("ImportedSampled");c.convert_to_samples(1,9)
obj,c=make("ImportedEnvelope");m=c.modifiers.new("ENVELOPE");m.control_points.add(1)
obj,c=make("ImportedNonTransform");obj.keyframe_insert(data_path="hide_render",frame=1)
obj,c=make("ImportedQuaternion");obj.rotation_mode="QUATERNION"
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
''')
    subprocess.run([shutil.which('blender'),'--background','--factory-startup','--threads','2','--python',str(script),'--',str(library/'native-curves.blend')],capture_output=True,check=True,timeout=45)
    async def run():
        async with client_for(path) as client:
            await client.call_tool('open_blend',{'path':'native-curves.blend'})
            for name,reason in [('ImportedModified','inspect-only'),('ImportedDriver','drivers'),('ImportedNLA','NLA'),('ImportedLocked','inspect-only'),('ImportedSampled','inspect-only'),('ImportedEnvelope','inspect-only')]:
                info=await channels(client,name)
                if name in {'ImportedDriver','ImportedNLA'}:assert info['edit_blockers']
                if name not in {'ImportedDriver','ImportedNLA'}:assert not info['channels'][0]['typed_editable']
                if name=='ImportedSampled':assert info['channels'][0]['sample_count']>0
                if name=='ImportedEnvelope':assert len(info['channels'][0]['modifiers'][0]['envelope_points'])==1
                with pytest.raises(ToolError,match=reason):
                    await key(client,name,name+'Refused',property='location',keyframes=[{'frame':1,'value':[0,0,0]}])
                assert (await channels(client,name))['animation_sha256']==info['animation_sha256']
            with pytest.raises(ToolError,match='Channel must'):
                await change(client,'ImportedNonTransform','NoBoolEdits',data_path='hide_render',component=0,frames=[1],settings={'operation':'DELETE'})
            result=await key(client,'ImportedQuaternion','QuaternionEdited',property='rotation_quaternion',keyframes=[
                {'frame':1,'value':[1,0,0,0]},{'frame':9,'value':[math.sqrt(.5),0,0,math.sqrt(.5)]}])
            rotation=(await sample(client,'ImportedQuaternion',frames=[9]))['samples'][0]['matrix_world']
            assert rotation[0][0]==pytest.approx(0,abs=.0001) and rotation[1][0]==pytest.approx(1,abs=.0001)
            with pytest.raises(ToolError,match='Euler'):
                await key(client,'ImportedQuaternion','WrongRotationMode',property='rotation_degrees',keyframes=[{'frame':1,'value':[0,0,0]}])
            await tool(client,'create_animation_control',name='EulerController')
            await key(client,'EulerController','EulerEdited',property='rotation_degrees',keyframes=[{'frame':1,'value':[0,0,0]},{'frame':9,'value':[0,0,90]}])
            rotation=(await sample(client,'EulerController',frames=[5]))['samples'][0]['matrix_world']
            assert rotation[0][0]==pytest.approx(math.sqrt(.5),abs=.0001) and rotation[1][0]==pytest.approx(math.sqrt(.5),abs=.0001)
            state=await channels(client,'EulerController')
            with pytest.raises(ToolError,match='float precision'):
                await key(client,'EulerController','QuantizedFrames',property='location',keyframes=[{'frame':1000000,'value':[0,0,0]},{'frame':1000000.001,'value':[1,0,0]}])
            assert (await channels(client,'EulerController'))['animation_sha256']==state['animation_sha256']
    asyncio.run(run())
