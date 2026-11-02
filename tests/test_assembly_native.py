"""Native dependency-closed graph copying, nested instances and rollback."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_assembly_native_copy_refs_clips_nested_bounds_and_cleanup(tmp_path):
    source=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(source))+')\n'+r'''
import bpy,json
from pathlib import Path
from mathutils import Vector
from mcpblender.blender import assemblies as assets,bridge
from mcpblender.assembly_contracts import Create,Place
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.mesh.primitive_cube_add(location=(4,0,1));obj=bpy.context.object;obj.name='Body'
control=bpy.data.objects.new('Control',None);bpy.context.scene.collection.objects.link(control);control.location=(4,0,0);control['amount']=.2
world=obj.matrix_world.copy();obj.parent=control;obj.matrix_world=world
basis=obj.shape_key_add(name='Basis');key=obj.shape_key_add(name='Lift')
for i,p in enumerate(basis.data):key.data[i].co=p.co+Vector((0,0,.5))
f=key.driver_add('value');f.driver.expression='amount';v=f.driver.variables.new();v.name='amount';v.type='SINGLE_PROP';v.targets[0].id=control;v.targets[0].data_path='["amount"]'
for frame,x in [(1,4),(9,6)]:control.location.x=x;control.keyframe_insert('location',frame=frame)
action=control.animation_data.action;action['mcpblender_target']=control.name
inactive=action.copy();inactive.name='Inactive';inactive['mcpblender_target']=control.name;inactive.use_fake_user=True
constraint=obj.constraints.new('LIMIT_SCALE');constraint.use_min_x=True;constraint.min_x=.5
material=bpy.data.materials.new('ObjectMaterial');material.use_nodes=True;node=material.node_tree.nodes.new('ShaderNodeTexCoord');node.object=control;obj.data.materials.append(material)
bpy.context.scene.frame_set(3,subframe=.25)
bad=assets.source({'objects':['Body']})[2];assert not bad['can_create'] and any('Control' in b for b in bad['blockers'])
planned=assets.source({'objects':['Body','Control']})[2];assert planned['can_create'],planned
p=Create.model_validate({'objects':['Body','Control'],'collection':'Prototype','expected_source':planned['source_sha256']}).model_dump()
before=set(bpy.data.user_map());source_guard=planned['source_sha256'];saved_frame=(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
source_selected=[o.name for o in bpy.context.selected_objects];source_active=bpy.context.view_layer.objects.active.name
phase={}
def progress(value):phase.update(value)
for cancel_phase in ('appending independent assembly graph','verified assembly prototype'):
    phase.clear()
    def cancel():
        if phase.get('phase')==cancel_phase:raise bridge.OperationCancelled('after owned transfer')
    bridge.report_progress=progress;bridge.check_cancelled=cancel
    try:assets.create(p)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Expected assembly cancellation')
    assert set(bpy.data.user_map())==before
    assert not any(k.startswith('mcp_assembly_source_') for o in (obj,control) for k in o.keys())
    assert assets.source({'objects':['Body','Control']})[2]['source_sha256']==source_guard
bridge.report_progress=lambda v:None;bridge.check_cancelled=lambda:None
result=assets.create(p);assert result['valid'] and not result['editing'],result
copies=result['copied_objects'];body=bpy.data.objects[copies['Body']];driver=bpy.data.objects[copies['Control']]
assert body.parent==driver and body.data!=obj.data and body.data.shape_keys!=obj.data.shape_keys
assert body.data.shape_keys.animation_data.drivers[0].driver.variables[0].targets[0].id==driver
assert body.data.materials[0]!=material and body.data.materials[0].node_tree.nodes[node.name].object==driver
assert len(result['actions'])==2
assert all(bpy.data.actions[n]['mcpblender_target']==driver.name for n in result['actions'])
assert (bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)==saved_frame
assert assets.source({'objects':['Body','Control']})[2]['source_sha256']==source_guard
assert [o.name for o in bpy.context.selected_objects]==source_selected and bpy.context.view_layer.objects.active.name==source_active
place=Place.model_validate({'collection':'Prototype','expected_asset':result['assembly_sha256'],'name':'One','location':[10,0,0]}).model_dump()
one=assets.place(place);two=assets.place(place|{'name':'Two','location':[20,0,0]})
assert bpy.data.objects['One'].instance_collection==bpy.data.objects['Two'].instance_collection
assert abs(two['world_bounds']['min'][0]-one['world_bounds']['min'][0]-10)<1e-5
assert len([o for o in bpy.data.objects if o.data==body.data])==1
# Nest an existing linked placement; preserve its prototype rather than leaking
# copied nested objects, data or clips.
plan=assets.source({'objects':['One']})[2];assert plan['can_create'],plan
before_nested=set(bpy.data.user_map())
nested=assets.create(Create.model_validate({'objects':['One'],'collection':'Nested','expected_source':plan['source_sha256']}).model_dump())
new=set(bpy.data.user_map())-before_nested
assert not [d for d in new if isinstance(d,(bpy.types.Mesh,bpy.types.Key,bpy.types.Action,bpy.types.Material))],[(type(d).__name__,d.name) for d in new]
assert nested['nested_assemblies']==['Prototype']
outer=assets.place(Place.model_validate({'collection':'Nested','expected_asset':nested['assembly_sha256'],'name':'Outer','location':[30,0,0]}).model_dump())
assert outer['world_bounds'] and len(outer['leaves'])>=2
# Source independent edit: prototype changes reach placements, not source data.
edit=assets.editing({'collection':'Prototype','expected_asset':assets.inspect_asset({'collection':'Prototype'})['assembly_sha256'],'enabled':True});assert edit['editing']
old_source=control['amount'];driver['amount']=.8;driver.update_tag();bpy.context.scene.frame_set(3,subframe=.25);bpy.context.view_layer.update()
assert control['amount']==old_source and abs(body.data.shape_keys.key_blocks['Lift'].value-.8)<1e-6
changed=assets.inspect_asset({'collection':'Prototype'});assert changed['assembly_sha256']!=result['assembly_sha256']
new_one=assets.instance({'name':'One'});assert new_one['world_bounds']['max'][2]>one['world_bounds']['max'][2]+.2
assets.editing({'collection':'Prototype','expected_asset':changed['assembly_sha256'],'enabled':False})
# Referencing an instance as a parent blocks removal; removing a free placement
# preserves the whole shared prototype.
child=bpy.data.objects.new('Dependent',None);bpy.context.scene.collection.objects.link(child);child.parent=bpy.data.objects['Two']
current=assets.instance({'name':'Two'})
try:assets.remove({'name':'Two','expected_instance':current['instance_sha256']})
except ValueError as e:assert 'referenced' in str(e)
else:raise AssertionError('Expected dependent instance refusal')
bpy.data.objects.remove(child,do_unlink=True)
current=assets.instance({'name':'Two'});assets.remove({'name':'Two','expected_instance':current['instance_sha256']})
assert 'Prototype' in bpy.data.collections and body.name in bpy.data.objects
path=Path(__file__).parent/'assemblies.blend';bpy.ops.wm.save_as_mainfile(filepath=str(path));bpy.ops.wm.open_mainfile(filepath=str(path))
assert assets.inspect_asset({'collection':'Prototype'})['valid'] and assets.instance({'name':'Outer'})['world_bounds']
print('ASSEMBLY_NATIVE_OK',flush=True)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=150)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'ASSEMBLY_NATIVE_OK' in result.stdout
    if evidence:=os.environ.get('MCPBLENDER_ASSEMBLY_EVIDENCE_DIR'):
        out=Path(evidence);out.mkdir(parents=True,exist_ok=True);shutil.copy2(tmp_path/'assemblies.blend',out/'assemblies-native.blend')
