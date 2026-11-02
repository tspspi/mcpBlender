"""Mid-pose cancellation, raw skin ownership and unsupported binding refusal."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_skin_lod_native_cancel_and_policy(tmp_path):
    source=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(source))+')\n'+r'''
import bpy,math
from mcpblender.blender import lods,skin_lods,rigging,bridge
from mcpblender.lod_contracts import Generate
rigging.create_armature({'name':'Rig','bones':[{'name':'Root','head':[0,0,-1],'tail':[0,0,1]}]})
rig=bpy.data.objects['Rig'];bpy.ops.mesh.primitive_uv_sphere_add();obj=bpy.context.object;obj.name='Skin'
group=obj.vertex_groups.new(name='Root');group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
pin=obj.vertex_groups.new(name='Pin');pin.add(list(range(len(obj.data.vertices))),.7,'REPLACE')
mod=obj.modifiers.new('Skin','ARMATURE');mod.object=rig
bpy.context.scene.frame_set(2,subframe=.25)
source=lods.inspect_source({'name':'Skin','deformation':'SKINNED'})
p=Generate.model_validate({'name':'Skin','deformation':'SKINNED','chain':'NativeSkinLOD','expected_source':source['source_sha256'],'levels':[{'triangle_budget':500},{'triangle_budget':150}],'pose_frames':[1,3]}).model_dump()
bridge.report_progress=lambda p:None;bridge.check_cancelled=lambda:None
# Source inspection reports without mutating data; unsupported DQ cannot silently
# become a linear glTF skin later.
mod.use_deform_preserve_volume=True
try:lods.inspect_source({'name':'Skin','deformation':'SKINNED'})
except ValueError as e:assert 'linear' in str(e)
else:raise AssertionError('Expected preserve-volume refusal')
mod.use_deform_preserve_volume=False

def counts():return len(bpy.data.objects),len(bpy.data.meshes),len(bpy.data.collections)
before=counts();saved=(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe);phase={}
def progress(v):phase.update(v)
def cancel():
    if phase.get('phase')=='verifying LOD skin poses':raise bridge.OperationCancelled('during native pose verification')
bridge.report_progress=progress;bridge.check_cancelled=cancel
try:lods.generate(p)
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected mid-pose cancellation')
assert counts()==before and (bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)==saved
assert lods.inspect_source({'name':'Skin','deformation':'SKINNED'})['source_sha256']==source['source_sha256']
assert not [g.name for g in obj.vertex_groups if g.name.startswith('mcp_LOD_joint')]
bridge.report_progress=lambda v:None;bridge.check_cancelled=lambda:None
result=lods.generate(p);assert result['valid']
for level in result['levels']:
    duplicate=bpy.data.objects[level['object']]
    assert 'Pin' in duplicate.vertex_groups
    assert all(abs(next(g.weight for g in v.groups if g.group==duplicate.vertex_groups['Pin'].index)-.7)<1e-5 for v in duplicate.data.vertices)
    assert not any(g.name.startswith('mcp_LOD_joint') for g in duplicate.vertex_groups)
# Sampling cancellation restores the already published chain's hidden levels.
original=lods.inspect_chain({'chain':'NativeSkinLOD'})['chain_sha256'];phase={};bridge.report_progress=progress;bridge.check_cancelled=cancel
try:skin_lods.sample({'chain':'NativeSkinLOD','expected_chain':original,'pose_frames':[1,2,3],'error_samples':32,'max_pose_error':.1})
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected sample cancellation')
assert lods.inspect_chain({'chain':'NativeSkinLOD'})['chain_sha256']==original
assert (bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)==saved
bridge.check_cancelled=lambda:None
# Rest changes invalidate the recorded skin binding, rather than reusing old proof.
bpy.context.view_layer.objects.active=rig;obj.select_set(False);rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT');rig.data.edit_bones['Root'].roll=.2;bpy.ops.object.mode_set(mode='OBJECT')
changed=lods.inspect_chain({'chain':'NativeSkinLOD'});assert not changed['valid'] and 'LOD rig rest definition changed' in changed['issues']
print('SKIN_LOD_NATIVE_OK',flush=True)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'SKIN_LOD_NATIVE_OK' in result.stdout
