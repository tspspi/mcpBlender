"""Affine/imported adoption, strict guards, ownership and cancellation in Blender."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest
pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_external_adoption_affine_import_morph_skin_and_rollback(tmp_path):
    script=tmp_path/'probe.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json
from mathutils import Matrix,Vector
from mcpblender.blender import lods,lod_management as manager,lod_adoption as adoption,bridge
from mcpblender.lod_contracts import AdoptionPlan,Adopt,Readopt
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=(4,0,2));source=bpy.context.object;source.name='Source'
mat=bpy.data.materials.new('Canonical');source.data.materials.append(mat)
manual=source.copy();manual.data=source.data.copy();manual.name='Manual';bpy.context.scene.collection.objects.link(manual)
bpy.context.view_layer.objects.active=manual
for o in bpy.context.selected_objects:o.select_set(False)
manual.select_set(True)
mod=manual.modifiers.new('Authored','DECIMATE');mod.ratio=.35;bpy.ops.object.modifier_apply(modifier=mod.name)
# A mirrored/sheared input represents the same surface after normalization.
transform=Matrix(((-1,.25,0,0),(0,1,.1,0),(0,0,1,0),(0,0,0,1)))
manual.data.transform(transform.inverted());manual.data.flip_normals();manual.matrix_world=source.matrix_world@transform
bpy.context.view_layer.update()
base={'name':'Source','inputs':[{'name':'Manual'}],'error_samples':64,'max_relative_error':.3,'max_pose_error':.3,'pose_frames':[1,5,9]}
def plan(value=base):return AdoptionPlan.model_validate(value).model_dump(exclude_none=True)
def create(chain,value=base):
    p=plan(value);r=adoption.inspect(p)
    return adoption.adopt(Adopt.model_validate(p|{'chain':chain,'expected_source':r['source_sha256']}).model_dump(exclude_none=True))
def remove(chain):
    state=manager.inventory({'chain':chain})[-1];assert state['can_remove'],state
    return manager.remove({'chain':chain,'expected_management':state['management_sha256']})
before=set(bpy.data.user_map());original=lods.summary(manual.data);source_guard=lods.inspect_source({'name':'Source'})['source_sha256']
result=create('Affine');assert result['valid'],result
assert result['levels'][1]['triangles']==original['triangles']
assert lods.summary(manual.data)==original
assert lods.inspect_source({'name':'Source'})['source_sha256']==source_guard
assert result['levels'][1]['quality']['max_relative_error']<.1
for polygon in bpy.data.objects['Affine_LOD1'].data.polygons:
    assert polygon.center.dot(polygon.normal)>0
# Material remapping is explicit and never changes the candidate.
foreign=bpy.data.materials.new('ImportedMaterial');manual.data.materials[0]=foreign
try:adoption.inspect(plan())
except ValueError as e:assert 'material slots' in str(e)
else:raise AssertionError('No material-layout refusal')
remapped=base|{'inputs':[{'name':'Manual','material_slots':[0]}]}
r=adoption.inspect(plan(remapped));assert r['inputs'][0]['normalized']['materials']==['Canonical']
# Existing chain references may not be used as replacement inputs.
state=manager.inventory({'chain':'Affine'})[-1]
try:manager.rebuild({'chain':'Affine','name':'Source','inputs':[{'name':'Affine_LOD1'}],'expected_management':state['management_sha256']},generator=adoption.adopt)
except ValueError as e:assert 'replaced LOD chain' in str(e)
else:raise AssertionError('Replaced input accepted')
# Cancel at both creation and final replacement handoff; exact IDs survive.
phase={}
def progress(v):phase.clear();phase.update(v)
bridge.report_progress=progress
for target in ('verified LOD level','verified LOD handoff before deletion'):
    state=manager.inventory({'chain':'Affine'})[-1];p=plan(remapped);r=adoption.inspect(p)
    phase.clear();ids=set(bpy.data.user_map())
    def cancel():
        if phase.get('phase')==target:raise bridge.OperationCancelled(target)
    bridge.check_cancelled=cancel
    try:
        if target=='verified LOD level':adoption.adopt(p|{'chain':'Cancelled','expected_source':r['source_sha256']})
        else:manager.rebuild(p|{'chain':'Affine','expected_source':r['source_sha256'],'expected_management':state['management_sha256']},generator=adoption.adopt)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('No cancellation')
    bridge.check_cancelled=lambda:None
    assert set(bpy.data.user_map())==ids,(target,[(type(i).__name__,i.name) for i in set(bpy.data.user_map())-ids])
    assert manager.inventory({'chain':'Affine'})[-1]['management_sha256']==state['management_sha256']
bridge.report_progress=lambda v:None
# An actual GLB reimport uses RAW_BASIS coordinates and explicit material mapping.
manual.matrix_world=source.matrix_world;manual.data.transform(transform);manual.data.flip_normals();bpy.context.view_layer.update()
for o in bpy.context.selected_objects:o.select_set(False)
manual.select_set(True);bpy.context.view_layer.objects.active=manual
from mcpblender.blender.workflows import export_objects_glb
export_objects_glb({'objects':['Manual'],'path':OUTPUT+'/manual.glb','animations':False,'overwrite':False,'apply_modifiers':False})
objects=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=OUTPUT+'/manual.glb')
imported=next(o for o in set(bpy.data.objects)-objects if o.type=='MESH');imported.name='Imported'
imported.data.uv_layers[0].name='ImporterUV'
uv_mapping={a.name:b.name for a,b in zip(imported.data.uv_layers,source.data.uv_layers)}
import_base=base|{'inputs':[{'name':imported.name,'material_slots':[0],'uv_maps':uv_mapping}]}
imported_before=lods.summary(imported.data)
assert create('ImportedLOD',import_base)['valid'];remove('ImportedLOD')
assert lods.summary(imported.data)==imported_before
remove('Affine');assert not bpy.data.collections.get('Affine')
# Explicit loss policies affect only derived levels, never canonical LOD0.
attribute=source.data.attributes.new(name='Wind',type='FLOAT',domain='POINT')
try:adoption.inspect(plan(remapped))
except ValueError as e:assert 'attribute schema' in str(e)
else:raise AssertionError('Lost attribute silently accepted')
assert create('NoWind',remapped|{'preserve_attribute_schema':False})['valid'];remove('NoWind')
source.data.attributes.remove(source.data.attributes['Wind'])
extra=bpy.data.materials.new('SecondRegion');source.data.materials.append(extra)
source.data.polygons[0].material_index=1
try:adoption.inspect(plan(remapped))
except ValueError as e:assert 'material regions' in str(e)
else:raise AssertionError('Lost material region silently accepted')
assert create('NoRegion',remapped|{'preserve_material_regions':False})['valid'];remove('NoRegion')
source.data.polygons[0].material_index=0;source.data.materials.pop(index=1)
# Strict geometry limits, hidden inputs and stale guards.
p=plan(remapped);r=adoption.inspect(p);manual.data.vertices[0].co.x+=.02
try:adoption.adopt(p|{'chain':'Stale','expected_source':r['source_sha256']})
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Stale guard accepted')
manual.hide_viewport=True
try:adoption.inspect(p)
except ValueError as e:assert 'visible' in str(e)
else:raise AssertionError('Hidden input accepted')
manual.hide_viewport=False
try:adoption.inspect(p|{'max_relative_error':0})
except ValueError as e:assert 'surface error' in str(e)
else:raise AssertionError('Unbounded error accepted')
# Canonical skin plus relative morphs: input deformation/weights are ignored.
source.shape_key_add(name='Basis');tip=source.shape_key_add(name='Tip')
for v in tip.data:
    if v.co.z>0:v.co.x+=.12*v.co.z
source.data.shape_keys.key_blocks['Tip'].value=0
source.data.shape_keys.key_blocks['Tip'].keyframe_insert('value',frame=1)
source.data.shape_keys.key_blocks['Tip'].value=1
source.data.shape_keys.key_blocks['Tip'].keyframe_insert('value',frame=5)
source.data.shape_keys.key_blocks['Tip'].value=0
source.data.shape_keys.key_blocks['Tip'].keyframe_insert('value',frame=9)
# Dedicated two-bone linear rig.
bpy.ops.object.armature_add(location=(4,0,2));rig=bpy.context.object;rig.name='Rig'
bpy.ops.object.mode_set(mode='EDIT');rig.data.edit_bones[0].name='Base'
bone=rig.data.edit_bones.new('Top');bone.head=(0,0,0);bone.tail=(0,0,1);bone.parent=rig.data.edit_bones[0]
bpy.ops.object.mode_set(mode='OBJECT')
g0=source.vertex_groups.new(name='Base');g1=source.vertex_groups.new(name='Top')
for v in source.data.vertices:
    t=max(0,min(1,(v.co.z+.25)/.5))
    if t<1:g0.add([v.index],1-t,'REPLACE')
    if t>0:g1.add([v.index],t,'REPLACE')
mod=source.modifiers.new('Skin','ARMATURE');mod.object=rig
rig.pose.bones['Top'].rotation_mode='XYZ'
for frame,angle in ((1,0),(5,.5),(9,0)):
    rig.pose.bones['Top'].rotation_euler.x=angle;rig.pose.bones['Top'].keyframe_insert('rotation_euler',frame=frame)
# Bogus incoming groups and morph shapes must not reach the output.
manual.vertex_groups.new(name='Foreign').add(list(range(len(manual.data.vertices))),1,'REPLACE')
manual.shape_key_add(name='Basis');key=manual.shape_key_add(name='Unrelated')
for v in key.data:v.co.x+=50
key.value=1
raw=remapped|{'deformation':'SKINNED','input_geometry':'RAW_BASIS'}
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
canonical=lods.inspect_source({'name':'Source','deformation':'SKINNED'})['source_sha256']
ids=set(bpy.data.user_map());created=create('SkinMorph',raw)
assert created['valid'] and created['skin'] and created['morph'],created
assert len(created['pose_validation'])==3
output=bpy.data.objects['SkinMorph_LOD1']
assert list(output.vertex_groups.keys())==list(source.vertex_groups.keys())
assert 'Unrelated' not in output.data.shape_keys.key_blocks
assert created['levels'][1]['skin_weights']['weight_sum_min']>.999
remove('SkinMorph');assert set(bpy.data.user_map())==ids
assert lods.inspect_source({'name':'Source','deformation':'SKINNED'})['source_sha256']==canonical
# Cancellation after transferred keys must not leak copied Key datablocks.
phase.clear();bridge.report_progress=progress
p=plan(raw);r=adoption.inspect(p);phase.clear();ids=set(bpy.data.user_map())
# Match the actual progress family emitted by morph transfer/measurement.
def cancel():
    if 'morph' in phase.get('phase','') and phase.get('phase')!='mapping LOD morphs':raise bridge.OperationCancelled('morph transfer')
bridge.check_cancelled=cancel
try:adoption.adopt(p|{'chain':'CancelledMorph','expected_source':r['source_sha256']})
except bridge.OperationCancelled:pass
else:raise AssertionError(('No morph cancellation',phase))
bridge.check_cancelled=lambda:None
assert set(bpy.data.user_map())==ids,[(type(i).__name__,i.name) for i in set(bpy.data.user_map())-ids]
print('LOD_ADOPTION_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=150)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'LOD_ADOPTION_NATIVE_OK' in result.stdout
