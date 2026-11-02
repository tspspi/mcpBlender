"""Native analytic morph transfer, source controls and rollback qualification."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_morph_lods_native_controls_relative_masks_and_cleanup(tmp_path):
    source=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(source))+')\n'+r'''
import bpy,math,json
from mathutils import Vector
from mcpblender.blender import lods,morph_lods,bridge,rigging
from mcpblender.lod_contracts import Generate
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16)
obj=bpy.context.object;obj.name='MorphSource'
basis=obj.shape_key_add(name='Basis');stretch=obj.shape_key_add(name='Stretch');relative=obj.shape_key_add(name='Relative')
relative.relative_key=stretch
for i,v in enumerate(basis.data):
    stretch.data[i].co=v.co+Vector((.1*v.co.x,.2*v.co.y,.15*v.co.z))
    relative.data[i].co=stretch.data[i].co+Vector((0,0,.12))
mask=obj.vertex_groups.new(name='Half');mask.add(list(range(len(obj.data.vertices))),.5,'REPLACE');relative.vertex_group='Half'
# Action and a driver coexist on the original Key. Nothing copies or edits them.
for frame,value in [(1,0),(5,1),(9,0)]:stretch.value=value;stretch.keyframe_insert('value',frame=frame)
control=bpy.data.objects.new('Controller',None);bpy.context.scene.collection.objects.link(control);control['strength']=.75
f=relative.driver_add('value');f.driver.expression='strength';v=f.driver.variables.new();v.name='strength';v.type='SINGLE_PROP';v.targets[0].id=control;v.targets[0].data_path='["strength"]'
bpy.context.scene.frame_set(3,subframe=.25)
source_keys=obj.data.shape_keys;action=source_keys.animation_data.action
source_shape=morph_lods.definition(obj);source_driver=f.driver.expression
bridge.report_progress=lambda v:None;bridge.check_cancelled=lambda:None
# Independent analytic triangle: offsets are multiplied by source masks before
# barycentric interpolation; the target's normal displacement stays intact.
mesh=bpy.data.meshes.new('Analytic');mesh.from_pydata([(0,0,0),(2,0,0),(0,2,0)],[],[(0,1,2)])
analytic=bpy.data.objects.new('Analytic',mesh);bpy.context.scene.collection.objects.link(analytic)
a=analytic.shape_key_add(name='Basis');b=analytic.shape_key_add(name='Warp')
for i,delta in enumerate([(2,0,0),(0,4,0),(0,0,8)]):b.data[i].co=a.data[i].co+Vector(delta)
g=analytic.vertex_groups.new(name='Mask');g.add([0],0,'REPLACE');g.add([1],1,'REPLACE');g.add([2],.5,'REPLACE');b.vertex_group='Mask'
tm=bpy.data.meshes.new('Target');tm.from_pydata([(.5,.5,.2)],[],[]);target=bpy.data.objects.new('Target',tm);bpy.context.scene.collection.objects.link(target)
morph_lods.attach(target,analytic,False)
assert (target.data.shape_keys.key_blocks['Warp'].data[0].co-Vector((.5,1.5,1.2))).length<1e-6
for temp in (analytic,target):
    data=temp.data;bpy.data.objects.remove(temp,do_unlink=True);bpy.data.meshes.remove(data)
before=(len(bpy.data.objects),len(bpy.data.meshes),len(bpy.data.shape_keys),len(bpy.data.actions),len(bpy.data.collections))
source=lods.inspect_source({'name':obj.name,'deformation':'MORPH'})
assert before==(len(bpy.data.objects),len(bpy.data.meshes),len(bpy.data.shape_keys),len(bpy.data.actions),len(bpy.data.collections)), (before,[(d.name,d.users) for d in bpy.data.shape_keys],[(d.name,d.users) for d in bpy.data.actions])
p=Generate.model_validate({'name':obj.name,'deformation':'MORPH','chain':'MorphLOD','expected_source':source['source_sha256'],'levels':[{'triangle_budget':400},{'triangle_budget':120}],'pose_frames':[1,3.25,5,9],'max_pose_error':.1}).model_dump()
saved=(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
phase={}
def progress(v):phase.update(v)
def cancel():
    if phase.get('phase')==cancel_phase:raise bridge.OperationCancelled('during morph verification')
for cancel_phase in ('transferred LOD morph','verifying isolated LOD morphs','verifying LOD skin poses'):
    phase={};bridge.report_progress=progress;bridge.check_cancelled=cancel
    try:lods.generate(p)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Expected transfer/validation cancellation: '+cancel_phase)
    assert before==(len(bpy.data.objects),len(bpy.data.meshes),len(bpy.data.shape_keys),len(bpy.data.actions),len(bpy.data.collections))
    assert saved==(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
    assert source_keys.animation_data.action==action and f.driver.expression==source_driver and morph_lods.definition(obj)==source_shape
bridge.report_progress=lambda v:None;bridge.check_cancelled=lambda:None
result=lods.generate(p);assert result['valid'],result['issues']
assert not result['source_stale_or_unavailable']
assert [l['triangles'] for l in result['levels']]==sorted([l['triangles'] for l in result['levels']],reverse=True)
for level in result['levels']:
    out=bpy.data.objects[level['object']];keys=out.data.shape_keys
    assert keys.key_blocks['Relative'].relative_key==keys.key_blocks['Stretch']
    assert keys.key_blocks['Relative'].vertex_group==''
    for a,b in zip(keys.key_blocks['Relative'].data,keys.key_blocks['Stretch'].data):assert (a.co-b.co-Vector((0,0,.06))).length<1e-6
    assert keys.animation_data.action is None and len(keys.animation_data.drivers)==2
    assert all(t.id==source_keys for c in keys.animation_data.drivers for v in c.driver.variables for t in v.targets)
# Controls and action switching/NLA remain on the source, LOD controllers follow.
far=bpy.data.objects[result['levels'][-1]['object']];far.hide_viewport=False;far.hide_set(False)
for frame in (1,3.25,5,9):
    whole=math.floor(frame);bpy.context.scene.frame_set(whole,subframe=frame-whole);bpy.context.view_layer.update()
    for name in ('Stretch','Relative'):assert abs(far.data.shape_keys.key_blocks[name].value-source_keys.key_blocks[name].value)<1e-6, (frame,name,far.data.shape_keys.key_blocks[name].value,source_keys.key_blocks[name].value)
relative.mute=True;bpy.context.scene.frame_set(4);bpy.context.view_layer.update();assert far.data.shape_keys.key_blocks['Relative'].value==0
relative.mute=False
control['strength']=.2;control.update_tag();bpy.context.scene.frame_set(6);bpy.context.view_layer.update();assert abs(far.data.shape_keys.key_blocks['Relative'].value-.2)<1e-6
anim=source_keys.animation_data;anim.action=None;track=anim.nla_tracks.new();strip=track.strips.new('SourceNLA',1,action);strip.action_slot=action.slots[0]
bpy.context.scene.frame_set(5);bpy.context.view_layer.update();assert abs(far.data.shape_keys.key_blocks['Stretch'].value-stretch.value)<1e-6 and stretch.value>.99
current=lods.inspect_chain({'chain':'MorphLOD'});assert current['valid']
sampled=morph_lods.sample({'chain':'MorphLOD','expected_chain':current['chain_sha256'],'pose_frames':[1,5,9],'error_samples':64,'max_pose_error':.1});assert sampled['worst_relative_error']<.1
plan=lods.dispatch('inspect_lod_export',{'chain':'MorphLOD','animations':True});assert plan['can_export'] and plan['export_profile']=='BAKED_MORPH_TIMELINE'
# Corrupted generated key data must invalidate ownership.
point=far.data.shape_keys.key_blocks['Relative'].data[0];old=point.co.copy();point.co.z+=.01
assert not lods.inspect_chain({'chain':'MorphLOD'})['valid'];point.co=old
# Definition changes on the source are distinct from animated weight changes.
relative.data[0].co.z+=.01
assert not lods.inspect_chain({'chain':'MorphLOD'})['valid'];relative.data[0].co.z-=.01
# Combined morph+linear skin uses the same transfer and source controller.
rigging.create_armature({'name':'Rig','bones':[{'name':'Root','head':[0,0,-1],'tail':[0,0,1]}]})
rig=bpy.data.objects['Rig']
bone=rig.pose.bones['Root'];bone.rotation_mode='XYZ'
for frame,value in [(1,0),(5,.5),(9,0)]:bone.rotation_euler.z=value;bone.keyframe_insert('rotation_euler',frame=frame)
group=obj.vertex_groups.new(name='Root');group.add(list(range(len(obj.data.vertices))),1,'REPLACE');mod=obj.modifiers.new('Skin','ARMATURE');mod.object=rig
src=lods.inspect_source({'name':obj.name,'deformation':'SKINNED'})
p2=Generate.model_validate({'name':obj.name,'deformation':'SKINNED','chain':'CombinedLOD','expected_source':src['source_sha256'],'levels':[{'triangle_budget':400}],'pose_frames':[1,5,9]}).model_dump()
combined=lods.generate(p2);assert combined['valid'] and combined['skin'] and combined['morph']
assert source_keys.animation_data.action is None and anim.nla_tracks[0]==track
assert f.driver.expression==source_driver
bpy.ops.wm.save_as_mainfile(filepath=str(__import__('pathlib').Path(__file__).parent/'morph-lods.blend'))
bpy.ops.wm.open_mainfile(filepath=bpy.data.filepath)
assert lods.inspect_chain({'chain':'CombinedLOD'})['valid']
print('MORPH_LOD_NATIVE_OK',flush=True)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=150)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'MORPH_LOD_NATIVE_OK' in result.stdout
    if evidence:=os.environ.get('MCPBLENDER_MORPH_LOD_EVIDENCE_DIR'):
        out=Path(evidence);out.mkdir(parents=True,exist_ok=True);shutil.copy2(tmp_path/'morph-lods.blend',out/'morph-skin-lods.blend')
