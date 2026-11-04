"""Hidden animated/modifier/GN sources frame identically after reload via MCP."""
import asyncio
import json
import os
import shutil
from pathlib import Path
import subprocess
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark


def test_hidden_sources_are_evaluated_and_visibility_is_restored(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    script=root/'hidden.py'
    script.write_text(r'''
import bpy,json
from pathlib import Path
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
parent=bpy.data.collections.new('HiddenParent');scene.collection.children.link(parent)
col=bpy.data.collections.new('Targets');parent.children.link(col)
root=bpy.data.objects.new('AnimatedParent',None);col.objects.link(root);root.rotation_euler=(.1,.2,.4);root.scale=(1.2,.8,1.1)
for frame,loc in ((1,(30,10,5)),(12,(60,-5,12))):root.location=loc;root.keyframe_insert(data_path='location',frame=frame)
mesh=bpy.data.meshes.new('Plane');mesh.from_pydata([(-2,-1,0),(2,-1,0),(2,1,0),(-2,1,0)],[],[(0,1,2,3)])
obj=bpy.data.objects.new('ThickPlane',mesh);col.objects.link(obj);obj.parent=root;obj.location=(4,-1,2)
m=obj.modifiers.new('Thickness','SOLIDIFY');m.thickness=4;m.offset=1
empty=bpy.data.meshes.new('InstanceOutput');gn=bpy.data.objects.new('GNInstances',empty);col.objects.link(gn);gn.parent=root;gn.location=(-4,2,0)
g=bpy.data.node_groups.new('TestInstances','GeometryNodeTree');g.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
cube=g.nodes.new('GeometryNodeMeshCube');line=g.nodes.new('GeometryNodeMeshLine');line.inputs['Count'].default_value=3;line.inputs['Offset'].default_value=(4,0,0)
inst=g.nodes.new('GeometryNodeInstanceOnPoints');out=g.nodes.new('NodeGroupOutput');g.links.new(line.outputs['Mesh'],inst.inputs['Points']);g.links.new(cube.outputs['Mesh'],inst.inputs['Instance']);g.links.new(inst.outputs['Instances'],out.inputs['Geometry'])
modifier=gn.modifiers.new('Instances','NODES');modifier.node_group=g
camera=bpy.data.objects.new('FramingCamera',bpy.data.cameras.new('FramingCamera'));scene.collection.objects.link(camera);camera.data.type='ORTHO'
for name,kind in (('ShiftCamera','ORTHO'),('PerspectiveCamera','PERSP'),('HiddenCamera','ORTHO')):
 c=bpy.data.objects.new(name,bpy.data.cameras.new(name));scene.collection.objects.link(c);c.data.type=kind
 if name=='ShiftCamera':c.data.shift_x=.2;c.data.shift_y=-.15
 if name=='HiddenCamera':c.hide_viewport=True;c.hide_set(True)
scene.frame_set(7);bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get();points=[];instances=0
for item in graph.object_instances:
 if item.is_instance and item.parent and item.parent.original==gn:
  instances+=1;points.extend(item.matrix_world@v.co for v in item.object.data.vertices)
 elif not item.is_instance and item.object.original==obj:points.extend(item.matrix_world@v.co for v in item.object.data.vertices)
assert instances==3 and points
bounds={key:[fn(v[a] for v in points) for a in range(3)] for key,fn in (('min',min),('max',max))}
Path(BOUNDS).write_text(json.dumps(bounds))
empty_obj=bpy.data.objects.new('EmptyTarget',bpy.data.meshes.new('Empty'));col.objects.link(empty_obj);empty_obj.hide_viewport=True;empty_obj.hide_set(True)
obj.hide_viewport=True;obj.hide_set(True);gn.hide_viewport=True;gn.hide_set(True)
parent.hide_viewport=True;col.hide_viewport=True;bpy.context.view_layer.layer_collection.children[parent.name].hide_viewport=True
bpy.ops.wm.save_as_mainfile(filepath=DEST)
'''.replace('BOUNDS',repr(str(library/'expected.json'))).replace('DEST',repr(str(library/'hidden.blend'))))
    run=subprocess.run(['blender','--background','--factory-startup','-t','2','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=60)
    assert run.returncode==0,run.stdout+run.stderr
    expected=json.loads((library/'expected.json').read_text())
    if dest:=os.environ.get('MCPBLENDER_HIDDEN_FRAME_EVIDENCE'):
        out=Path(dest);out.mkdir(parents=True,exist_ok=True);shutil.copy2(library/'hidden.blend',out/'hidden.blend');shutil.copy2(library/'expected.json',out/'expected.json')
    async def work():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await client.call_tool('open_blend',{'path':'hidden.blend'})
            before=(await client.call_tool('get_scene_info')).data
            fit=await tool(client,'frame_objects',name='FramingCamera',objects=['ThickPlane','GNInstances'],view='ISOMETRIC')
            if dest:=os.environ.get('MCPBLENDER_HIDDEN_FRAME_EVIDENCE'):
                (Path(dest)/'fit.json').write_text(json.dumps(fit,indent=2))
            for key in ('min','max'):assert fit['source_bounds_world'][key]==pytest.approx(expected[key],abs=2e-5)
            assert fit['fully_in_frame'],fit
            await tool(client,'configure_render',resolution_x=480,resolution_y=800)
            for camera in ('ShiftCamera','PerspectiveCamera','HiddenCamera'):
                other=await tool(client,'frame_objects',name=camera,objects=['ThickPlane','GNInstances'],view='ISOMETRIC')
                assert other['fully_in_frame'],other
                if camera=='HiddenCamera':assert other['visible'] is False
                for key in ('min','max'):assert other['source_bounds_world'][key]==pytest.approx(expected[key],abs=2e-5)
            stage=await tool(client,'setup_preview_stage',objects=['ThickPlane','GNInstances'],prefix='HiddenPreview',projection='ORTHO')
            assert stage['camera']['fully_in_frame']
            for key in ('min','max'):assert stage['asset_world_bounds'][key]==pytest.approx(expected[key],abs=2e-5)
            cam_before=(await client.call_tool('get_object_info',{'name':'FramingCamera'})).data
            with pytest.raises(ToolError,match='empty'):await tool(client,'frame_objects',name='FramingCamera',objects=['EmptyTarget'])
            assert (await client.call_tool('get_object_info',{'name':'FramingCamera'})).data['matrix_world']==cam_before['matrix_world']
            after=(await client.call_tool('get_scene_info')).data
            assert before['frame']==after['frame'] and before['filepath']==after['filepath']
            # Save the resulting source state and verify flags independently in stock Blender.
            await client.call_tool('save_blend',{'path':'after.blend'})
    asyncio.run(work())
    verify=root/'verify.py'
    verify.write_text('import bpy\nbpy.ops.wm.open_mainfile(filepath='+repr(str(library/'after.blend'))+')\n'+r'''
for name in ('ThickPlane','GNInstances','EmptyTarget'):
 obj=bpy.data.objects[name];assert obj.hide_viewport and obj.hide_get()
assert bpy.data.collections['HiddenParent'].hide_viewport and bpy.data.collections['Targets'].hide_viewport
assert bpy.context.view_layer.layer_collection.children['HiddenParent'].hide_viewport
assert bpy.context.scene.frame_current==7
assert bpy.data.objects['HiddenCamera'].hide_viewport and bpy.data.objects['HiddenCamera'].hide_get()
import sys
sys.path.insert(0,REPO)
from mcpblender.blender import assets,bridge
obj=bpy.data.objects['ThickPlane']
def flags():return (obj.hide_viewport,obj.hide_get(),bpy.data.collections['HiddenParent'].hide_viewport,bpy.data.collections['Targets'].hide_viewport,bpy.context.view_layer.layer_collection.children['HiddenParent'].hide_viewport)
original=flags();ids=set(bpy.data.user_map())
bridge.check_cancelled=lambda:None
try:
 with assets.evaluation_visibility(obj):
  assert obj.visible_get()
  raise RuntimeError('injected evaluation failure')
except RuntimeError:pass
else:raise AssertionError('Expected injected failure')
assert flags()==original and set(bpy.data.user_map())==ids
def cancel():raise bridge.OperationCancelled('injected cancellation')
bridge.check_cancelled=cancel
try:assets.evaluated_mesh_bounds(obj)
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected injected cancellation')
assert flags()==original and set(bpy.data.user_map())==ids
'''.replace('REPO',repr(str(Path(__file__).resolve().parents[1]))))
    checked=subprocess.run(['blender','--background','--factory-startup','-t','2','--python-exit-code','1','--python',str(verify)],capture_output=True,text=True,timeout=60)
    assert checked.returncode==0,checked.stdout+checked.stderr
