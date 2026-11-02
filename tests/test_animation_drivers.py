"""Real control-driven limb and morph deformation, with Python disabled."""
import asyncio
import math
import os
from pathlib import Path
import shutil
import subprocess

from fastmcp.exceptions import ToolError
import pytest

from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_animation_curves import key
from test_constraints import edit,sample
from test_skeletal_animation import make_limb


async def inspect(client,name):return await tool(client,'inspect_animation_drivers',name=name)
async def configure(client,name,channel,settings):
    info=await inspect(client,name)
    return await tool(client,'configure_animation_driver',name=name,channel=channel,settings=settings,expected_drivers=info['drivers_sha256'])


def test_same_rig_scalar_drives_bone_and_portable_visual_bake(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await make_limb(client,'DrivenRig','DrivenSkin',x=10)
            await tool(client,'set_animation_property',name='DrivenRig',property='Bend',value=0)
            channel={'kind':'TRANSFORM','bone':'Tip','property':'rotation_euler','component':0}
            settings={'expression':'bend*pi/2','variables':[{'kind':'PROPERTY','name':'bend','object':'DrivenRig','property':'Bend'}]}
            first=await configure(client,'DrivenRig',channel,settings)
            assert first['drivers'][0]['is_simple_expression'] and first['drivers'][0]['is_valid']
            feedback={'kind':'PROPERTY','property':'Bend'}
            with pytest.raises(ToolError,match='cycle'):
                await configure(client,'DrivenRig',feedback,{'expression':'angle','variables':[{'kind':'TRANSFORM','name':'angle','object':'DrivenRig','bone':'Tip','transform':'ROT_X'}]})
            await key(client,'DrivenRig','DrivenControls',property='custom_scalar',custom_property='Bend',keyframes=[{'frame':1,'value':0},{'frame':9,'value':1}])
            motion=await sample(client,'DrivenRig',frames=[1,5,9],bones=['Tip'],meshes=['DrivenSkin'])
            for row,expected in zip(motion['samples'],([10,0,2],[10,-math.sqrt(.5),1+math.sqrt(.5)],[10,-1,1])):
                assert math.dist(row['bones'][0]['tail_world'],expected)<.001
            assert len({r['meshes'][0]['geometry_sha256'] for r in motion['samples']})==3
            with pytest.raises(ToolError,match='driven'):
                await tool(client,'set_animation_property',name='DrivenRig',property='Bend',value=.5)
            before=await inspect(client,'DrivenRig')
            assert (await inspect(client,'DrivenRig'))['drivers_sha256']==before['drivers_sha256']
            baked=(await client.call_tool('bake_constraint_animation',{'params':{'name':'DrivenRig','output_rig':'DrivenBaked','clip':'DrivenBakedMotion','meshes':[{'source':'DrivenSkin','output':'DrivenBakedSkin'}],'frame_start':1,'frame_end':9},'wait':True})).data
            assert baked['max_vertex_world_error']<.0001
            await client.call_tool('save_blend',{'path':'drivers.blend'})
            await client.call_tool('open_blend',{'path':'drivers.blend'})
            reopened=await inspect(client,'DrivenRig')
            assert reopened['drivers'][0]['typed_editable'] and reopened['drivers_sha256']==before['drivers_sha256']
            await client.call_tool('set_frame',{'frame':5})
            updated=await configure(client,'DrivenRig',channel,settings|{'expression':'bend*pi/4'})
            changed=await sample(client,'DrivenRig',frames=[9],bones=['Tip'])
            assert changed['samples'][0]['bones'][0]['tail_world']==pytest.approx([10,-math.sqrt(.5),1+math.sqrt(.5)],abs=.001)
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'remove_animation_driver',name='DrivenRig',channel=channel,expected_drivers=before['drivers_sha256'])
            removed=await tool(client,'remove_animation_driver',name='DrivenRig',channel=channel,expected_drivers=updated['drivers_sha256'])
            assert removed['total_drivers']==0
            await tool(client,'set_animation_property',name='DrivenRig',bone='Tip',property='BoneBend',value=0)
            await configure(client,'DrivenRig',channel,{'expression':'angle','variables':[{'kind':'PROPERTY','name':'angle','object':'DrivenRig','bone':'Tip','property':'BoneBend'}]})
            await key(client,'DrivenRig','DrivenBoneCustomControls',bone='Tip',property='custom_scalar',custom_property='BoneBend',keyframes=[{'frame':1,'value':0},{'frame':9,'value':.5}])
            bone_motion=await sample(client,'DrivenRig',frames=[9],bones=['Tip'])
            assert bone_motion['samples'][0]['bones'][0]['tail_world']==pytest.approx([10,-math.sin(.5),1+math.cos(.5)],abs=.001)
            if destination:=os.environ.get('MCPBLENDER_DRIVER_EVIDENCE_DIR'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'library/drivers.blend',out/'drivers.blend')
    asyncio.run(run())


def test_transform_inputs_shapes_and_native_failure_rollback(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_animation_control',name='DriverInput',location=[2,0,0])
            await tool(client,'create_animation_control',name='DriverOutput',location=[7,4,0])
            target={'kind':'TRANSFORM','property':'location','component':0}
            variable={'kind':'TRANSFORM','name':'x','object':'DriverInput','transform':'LOC_X'}
            info=await configure(client,'DriverOutput',target,{'expression':'x*3','variables':[variable]})
            actual=(await sample(client,'DriverOutput',frames=[1]))['samples'][0]['matrix_world'][0][3]
            assert actual==pytest.approx(6)
            before=await inspect(client,'DriverOutput')
            with pytest.raises(ToolError,match='invalid'):
                await configure(client,'DriverOutput',target,{'expression':'1/0'})
            assert (await inspect(client,'DriverOutput'))['drivers_sha256']==before['drivers_sha256']
            actual=(await sample(client,'DriverOutput',frames=[1]))['samples'][0]['matrix_world'][0][3]
            assert actual==pytest.approx(6)
            newtarget={'kind':'TRANSFORM','property':'location','component':1}
            with pytest.raises(ToolError,match='invalid'):
                await configure(client,'DriverOutput',newtarget,{'expression':'sqrt(-1)'})
            actual=(await sample(client,'DriverOutput',frames=[1]))['samples'][0]['matrix_world'][1][3]
            assert actual==pytest.approx(4)
            await tool(client,'create_primitive',name='DrivenMorph')
            await tool(client,'create_shape_key',name='DrivenMorph',key='Tall',vertices=[{'vertex':i,'value':[0,0,1]} for i in range(8)])
            await tool(client,'set_animation_property',name='DriverInput',property='Grow',value=.5)
            morph={'kind':'SHAPE_KEY','key':'Tall'}
            result=await configure(client,'DrivenMorph',morph,{'expression':'clamp(grow)','variables':[{'kind':'PROPERTY','name':'grow','object':'DriverInput','property':'Grow'}]})
            assert result['drivers'][0]['is_valid']
            mesh=await tool(client,'inspect_mesh',name='DrivenMorph')
            assert mesh['world_bounds']['max'][2]==pytest.approx(1.5)
            await tool(client,'set_animation_property',name='DriverInput',property='Grow',value=1)
            mesh=await tool(client,'inspect_mesh',name='DrivenMorph')
            assert mesh['world_bounds']['max'][2]==pytest.approx(2)
            # Raw shape-weight dependency can feed another object without inventing
            # a transform cycle on the mesh owning that shape-key datablock.
            await configure(client,'DriverOutput',{'kind':'TRANSFORM','property':'scale','component':2},{'expression':'1+weight','variables':[{'kind':'SHAPE_KEY','name':'weight','object':'DrivenMorph','key':'Tall'}]})
            scale=(await sample(client,'DriverOutput',frames=[1]))['samples'][0]['matrix_world'][2][2]
            assert scale==pytest.approx(2)
            await tool(client,'duplicate_object',name='DrivenMorph',new_name='SharedDrivenMorph',linked_data=True)
            shared=await inspect(client,'DrivenMorph')
            assert not shared['drivers'][0]['typed_editable'] and shared['drivers'][0]['edit_blockers']
            with pytest.raises(ToolError,match='independent'):
                await configure(client,'DrivenMorph',morph,{'expression':'0.5'})
    asyncio.run(run())


def test_world_local_inputs_constraint_influence_and_cycles(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_animation_control',name='DriverParent',location=[10,0,0])
            await tool(client,'create_animation_control',name='DriverChild',location=[2,0,0])
            await tool(client,'set_parent',name='DriverChild',parent='DriverParent',keep_world=False)
            await tool(client,'create_animation_control',name='DriverSpaceOutput')
            target={'kind':'TRANSFORM','property':'location','component':0}
            vars=[{'kind':'TRANSFORM','name':'world','object':'DriverChild','transform':'LOC_X','space':'WORLD_SPACE'},
                  {'kind':'TRANSFORM','name':'local','object':'DriverChild','transform':'LOC_X','space':'TRANSFORM_SPACE'}]
            await configure(client,'DriverSpaceOutput',target,{'expression':'world-local','variables':vars})
            value=(await sample(client,'DriverSpaceOutput',frames=[1]))['samples'][0]['matrix_world'][0][3]
            assert value==pytest.approx(10)
            vars[1]['space']='LOCAL_SPACE'
            await configure(client,'DriverSpaceOutput',target,{'expression':'world-local','variables':vars})
            value=(await sample(client,'DriverSpaceOutput',frames=[1]))['samples'][0]['matrix_world'][0][3]
            assert value==pytest.approx(10)
            with pytest.raises(ToolError,match='cycle'):
                await configure(client,'DriverParent',target,{'expression':'x','variables':[{'kind':'TRANSFORM','name':'x','object':'DriverSpaceOutput','transform':'LOC_X'}]})
            await tool(client,'set_animation_property',name='DriverChild',property='Follow',value=.5)
            await tool(client,'create_animation_control',name='DriverFollower')
            await edit(client,'DriverFollower','Follow',{'type':'COPY_LOCATION','target':{'name':'DriverChild'}})
            channel={'kind':'CONSTRAINT','constraint':'Follow'}
            await configure(client,'DriverFollower',channel,{'expression':'blend','variables':[{'kind':'PROPERTY','name':'blend','object':'DriverChild','property':'Follow'}]})
            value=(await sample(client,'DriverFollower',frames=[1]))['samples'][0]['matrix_world'][0][3]
            assert value==pytest.approx(6)
            with pytest.raises(ToolError,match='cycle'):
                await configure(client,'DriverChild',{'kind':'PROPERTY','property':'Follow'}, {'expression':'x','variables':[{'kind':'TRANSFORM','name':'x','object':'DriverFollower','transform':'LOC_X'}]})
            # The driver fingerprint describes configuration, not animated values.
            before=await inspect(client,'DriverFollower')
            await tool(client,'set_animation_property',name='DriverChild',property='Follow',value=1)
            assert (await inspect(client,'DriverFollower'))['drivers_sha256']==before['drivers_sha256']
            value=(await sample(client,'DriverFollower',frames=[1]))['samples'][0]['matrix_world'][0][3]
            assert value==pytest.approx(12)
    asyncio.run(run())


def test_imported_metadata_cannot_hide_native_dependencies(assets_live):
    root,path=assets_live
    library=root/'library';library.mkdir(exist_ok=True)
    script=root/'native-driver.py'
    script.write_text('''import bpy,sys,os,json,copy
sys.path.insert(0,os.getcwd())
from mcpblender.blender import drivers as d
bpy.ops.wm.read_factory_settings(use_empty=True)
def obj(name):
 o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);return o
source=obj("ActualSource");source["Amount"]=.2
other=obj("ClaimedSource");other["Amount"]=.8
output=obj("ImportedDriverOutput")
c=output.driver_add("location",0)
channel={"kind":"TRANSFORM","property":"location","component":0}
settings={"expression":"amount","variables":[{"kind":"PROPERTY","name":"amount","object":"ActualSource","property":"Amount"}]}
d.apply(c,settings);d.refresh(output)
forged=copy.deepcopy(settings);forged["variables"][0]["object"]="ClaimedSource"
output[d.OWNED]=json.dumps({d.identity("location",0):{"channel":channel,"settings":forged,"native_sha256":d.digest(d.native_record(c))}})
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
''')
    result=subprocess.run([shutil.which('blender'),'--background','--factory-startup','--threads','2','--python',str(script),'--',str(library/'native-driver.blend')],capture_output=True,text=True,timeout=45)
    assert result.returncode==0,result.stdout+result.stderr
    async def run():
        async with client_for(path) as client:
            await client.call_tool('open_blend',{'path':'native-driver.blend'})
            state=await inspect(client,'ImportedDriverOutput')
            assert not state['drivers'][0]['typed_editable']
            with pytest.raises(ToolError,match='inspect-only'):
                await configure(client,'ImportedDriverOutput',{'kind':'TRANSFORM','property':'location','component':0},{'expression':'1'})
            await tool(client,'create_animation_control',name='ImportedDriverConsumer')
            with pytest.raises(ToolError,match='inspect-only'):
                await configure(client,'ImportedDriverConsumer',{'kind':'TRANSFORM','property':'location','component':0},{'expression':'x','variables':[{'kind':'TRANSFORM','name':'x','object':'ImportedDriverOutput','transform':'LOC_X'}]})
            assert (await inspect(client,'ImportedDriverOutput'))['drivers_sha256']==state['drivers_sha256']
            # An unrelated bad driver must not block an independent raw input.
            result=await configure(client,'ImportedDriverConsumer',{'kind':'TRANSFORM','property':'location','component':0},{'expression':'amount','variables':[{'kind':'PROPERTY','name':'amount','object':'ClaimedSource','property':'Amount'}]})
            assert result['drivers'][0]['typed_editable']
            value=(await sample(client,'ImportedDriverConsumer',frames=[1]))['samples'][0]['matrix_world'][0][3]
            assert value==pytest.approx(.8)
    asyncio.run(run())
