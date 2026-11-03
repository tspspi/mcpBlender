"""Exact botanical ownership, edited meshes/model refusal and staged rollback."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest
pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_botanical_ids_references_and_regeneration_rollback(tmp_path):
    script=tmp_path/'probe.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json
from mcpblender.blender import botanical_trees as trees,bridge
from mcpblender.botanical_contracts import Plan,Create,Regenerate
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
recipe={'attractors':96,'iterations':6,'node_budget':256}
p=Plan.model_validate({'recipe':recipe}).model_dump();plan=trees.plan(p)
args=Create.model_validate(p|{'collection':'Oak','expected_model':plan['model_sha256']}).model_dump(exclude_none=True)
base=set(bpy.data.user_map());created=trees.create(args);assert created['valid'],created
col,root,objects,text,owned,_,model,state=trees.inventory({'collection':'Oak'})
# Numeric semantics and UVs match the canonical source, without claiming export retention.
wood=objects[0];indices=[v.value for v in wood.data.attributes['bot_branch_index'].data]
assert min(indices)==0 and max(indices)==len(model['branches'])-1
assert len(wood.data.uv_layers)==1 and wood.data.uv_layers[0].name=='BarkUV'
assert wood.data.uv_layers[0].active_render
assert min(v.co.z for v in wood.data.vertices)==0
for vertex in wood.data.vertices:
    assert all(__import__('math').isfinite(v) for v in vertex.co)
# External collection instance and shared mesh references refuse deletion/replacement.
instance=bpy.data.objects.new('ForeignInstance',None);instance.instance_type='COLLECTION';instance.instance_collection=col;bpy.context.scene.collection.objects.link(instance)
state=trees.inspect({'collection':'Oak'});assert not state['can_remove']
try:trees.remove({'collection':'Oak','expected_tree':state['tree_sha256']})
except ValueError as e:assert 'External native reference' in str(e)
else:raise AssertionError('Foreign instance removed')
bpy.data.objects.remove(instance)
copy=bpy.data.objects.new('SharedWood',wood.data);bpy.context.scene.collection.objects.link(copy)
assert not trees.inspect({'collection':'Oak'})['can_remove'];bpy.data.objects.remove(copy)
# Preserve placement, parent links, material identity, data names and visibility.
parent=bpy.data.objects.new('Placement',None);bpy.context.scene.collection.objects.link(parent);parent.location=(4,1,0);parent.rotation_euler.z=.2
root.parent=parent;root.location=(2,0,0);root.scale=(1.1,.9,1.2);root.rotation_euler.z=.3
root.display_type='WIRE';wood.visible_shadow=False
container=bpy.data.collections.new('Nested');bpy.context.scene.collection.children.link(container);container.children.link(col);bpy.context.scene.collection.children.unlink(col)
bpy.context.view_layer.update();matrix=root.matrix_world.copy();state=trees.inspect({'collection':'Oak'})
new_recipe=p['recipe']|{'height':12,'crown_width':10};planned=trees.plan({'recipe':new_recipe})
regen=Regenerate.model_validate(args|{'recipe':new_recipe,'expected_model':planned['model_sha256'],'expected_tree':state['tree_sha256']}).model_dump(exclude_none=True)
ids=set(bpy.data.user_map());names={i:i.name for i in ids};phase={}
def progress(v):phase.clear();phase.update(v)
bridge.report_progress=progress
for boundary in ('meshing botanical wood','verified botanical handoff before deletion'):
    phase.clear()
    def cancel():
        if phase.get('phase')==boundary:raise bridge.OperationCancelled(boundary)
    bridge.check_cancelled=cancel
    try:trees.regenerate(regen)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('No botanical cancellation')
    bridge.check_cancelled=lambda:None
    assert set(bpy.data.user_map())==ids
    assert all(item.name==name for item,name in names.items())
    assert trees.inspect({'collection':'Oak'})['tree_sha256']==state['tree_sha256']
bridge.report_progress=lambda v:None
# Edited derived geometry is not discarded without opt-in.
wood.data.vertices[0].co.x+=.01;state=trees.inspect({'collection':'Oak'});assert not state['valid'] and state['can_remove']
regen['expected_tree']=state['tree_sha256']
try:trees.regenerate(regen)
except ValueError as e:assert 'discard_derived_edits' in str(e)
else:raise AssertionError('Derived edits silently discarded')
material=wood.data.materials[0];data_names=[o.data.name for o in objects]
result=trees.regenerate(regen|{'discard_derived_edits':True});assert result['valid'],result
col,root,objects,text,owned,_,model,state=trees.inventory({'collection':'Oak'})
assert objects[0].data.materials[0]==material and [o.data.name for o in objects]==data_names
assert root.parent==parent and col.name in container.children and root.display_type=='WIRE' and not objects[0].visible_shadow
assert all(abs(root.matrix_world[i][j]-matrix[i][j])<1e-6 for i in range(4) for j in range(4))
# Semantic export uses owned staging, preserving foreign conventional temp files.
from pathlib import Path
path=Path(OUTPUT)/'model.json';foreign=Path(str(path)+'.tmp');foreign.write_text('foreign')
state=trees.inspect({'collection':'Oak'});calls=[0]
def cancel_export():
    calls[0]+=1
    if calls[0]==2:raise bridge.OperationCancelled('cancel model publish')
bridge.check_cancelled=cancel_export
try:trees.export_model({'collection':'Oak','expected_tree':state['tree_sha256'],'path':str(path),'overwrite':False})
except bridge.OperationCancelled:pass
else:raise AssertionError('Missing export cancellation')
bridge.check_cancelled=lambda:None
assert not path.exists() and foreign.read_text()=='foreign' and not list(Path(OUTPUT).glob('.mcpblender-model-*'))
trees.export_model({'collection':'Oak','expected_tree':state['tree_sha256'],'path':str(path),'overwrite':False})
assert foreign.read_text()=='foreign'
# Edited canonical JSON is protected even under derived-edit opt-in.
text.write(' ');model=json.loads(text.as_string());model['recipe']['seed']=99;text.clear();text.write(json.dumps(model))
state=trees.inspect({'collection':'Oak'});assert state['model_error']
try:trees.regenerate(regen|{'expected_tree':state['tree_sha256'],'discard_derived_edits':True})
except ValueError as e:assert 'canonical model' in str(e)
else:raise AssertionError('Canonical edits overwritten')
# Owned removal retains source-independent reusable materials and parent structure.
trees.remove({'collection':'Oak','expected_tree':state['tree_sha256']})
assert material.name in bpy.data.materials and parent.name in bpy.data.objects and container.name in bpy.data.collections
assert not bpy.data.collections.get('Oak') and not bpy.data.texts.get('Oak_Model.json')
# Model metres convert into native scene units without changing the scene scale.
bpy.context.scene.unit_settings.scale_length=.01
unit_scale=bpy.context.scene.unit_settings.scale_length
converted=trees.create(args|{'collection':'MetricOak'})
root=bpy.data.objects[converted['root']];wood=bpy.data.objects['MetricOak_Wood']
assert abs(root.scale.z-100)<1e-6
assert abs(max((wood.matrix_world@v.co).z for v in wood.data.vertices)*.01-14)<.1
assert bpy.context.scene.unit_settings.scale_length==unit_scale
state=trees.inspect({'collection':'MetricOak'});trees.remove({'collection':'MetricOak','expected_tree':state['tree_sha256']})
print('BOTANICAL_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'BOTANICAL_NATIVE_OK' in result.stdout
