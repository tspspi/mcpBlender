"""Native rig metadata preservation and deterministic rest-edit cancellation."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_native_rest_rollback_identity_constraints_and_shared_isolation(tmp_path):
    source=Path(__file__).resolve().parents[1];script=tmp_path/'rest-probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(source))+')\n'+r'''
import bpy
from mcpblender.blender import rest_edit as rest,bridge
from mcpblender.rest_contracts import EditRest
bpy.ops.object.armature_add();rig=bpy.context.object;rig.name='Rig'
bpy.ops.object.mode_set(mode='EDIT');b=rig.data.edit_bones[0];b.name='Root';b.head=(.2,.3,.4);b.tail=(.7,.8,1.9);b.roll=.431
b=rig.data.edit_bones.new('Child');b.head=(.7,.8,1.9);b.tail=(.7,.8,2.9);b.parent=rig.data.edit_bones['Root'];b.use_connect=True
bpy.ops.object.mode_set(mode='OBJECT')
rig.pose.bones['Root']['marker']=.3;rig.data.bones['Root']['metadata']='keep'
rig.pose.bones['Root'].location=(.1,.2,.3)
control=bpy.data.objects.new('Control',None);bpy.context.scene.collection.objects.link(control)
c=rig.pose.bones['Child'].constraints.new('COPY_ROTATION');c.target=control;c.influence=.25
rig.pose.bones['Child'].driver_add('scale',0).driver.expression='1.1'
rig.pose.bones['Root'].select=True;rig.data.bones.active=rig.data.bones['Root']
attachment=bpy.data.objects.new('Attachment',None);bpy.context.scene.collection.objects.link(attachment);attachment.parent=rig;attachment.parent_type='BONE';attachment.parent_bone='Child'
old_data=rig.data;old_driver=rig.animation_data.drivers[0];old_constraint=rig.pose.bones['Child'].constraints[0]
bridge.report_progress=lambda p:None;bridge.check_cancelled=lambda:None

def info():return rest.inspect({'name':'Rig'})
def edit(**params):
    values=EditRest.model_validate({'name':'Rig','expected_rest':info()['rest_sha256'],'allow_deformation_change':True,**params}).model_dump(exclude_none=True)
    return rest.edit(values)

def same_metadata():
    assert rig.pose.bones['Root']['marker']==.3 and rig.data.bones['Root']['metadata']=='keep'
    assert rig.animation_data.drivers[0]==old_driver and rig.pose.bones['Child'].constraints[0]==old_constraint
    assert attachment.parent==rig and attachment.parent_bone=='Child'
    assert rig.data.bones.active.name=='Root' and rig.pose.bones['Root'].select
    assert tuple(rig.pose.bones['Root'].location)==tuple(map(float,(.1,.2,.3))) or max(abs(a-b) for a,b in zip(rig.pose.bones['Root'].location,(.1,.2,.3)))<1e-6

assert info()['impact']['bone_attachments'][0]['name']=='Attachment'
before=info()['rest_sha256'];checks=0

def cancel():
    global checks
    checks+=1
    if checks==2:raise bridge.OperationCancelled('cancel after native rest writes')
bridge.check_cancelled=cancel
try:edit(bones=[{'name':'Root','head':[1,2,3],'tail':[1,2,4],'roll_degrees':80},{'name':'Child','parent':'Helper','connected':False}],add_bones=[{'name':'Helper','head':[0,0,0],'tail':[0,0,1]}])
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected native cancellation')
assert checks==2 and info()['rest_sha256']==before and rig.data==old_data and 'Helper' not in rig.pose.bones
same_metadata()
# Cancellation with a new copied armature restores the original shared pointer.
peer=rig.copy();peer.name='Peer';bpy.context.scene.collection.objects.link(peer)
before=info()['rest_sha256'];counts=len(bpy.data.armatures);checks=0
try:edit(make_single_user=True,bones=[{'name':'Root','roll_degrees':70}])
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected shared cancellation')
assert checks==2 and info()['rest_sha256']==before and rig.data==peer.data==old_data and len(bpy.data.armatures)==counts
same_metadata()
bridge.check_cancelled=lambda:None
changed=edit(make_single_user=True,bones=[{'name':'Root','roll_degrees':70}])
assert changed['isolated_armature_data'] and rig.data!=peer.data and peer.data==old_data
same_metadata()
# Unsupported data animation remains inspectable and is refused before mutation.
rig.data['animated_setting']=.2;rig.data.driver_add('["animated_setting"]').driver.expression='0.3'
before=info()['rest_sha256'];assert info()['edit_blockers']
try:edit(bones=[{'name':'Root','deform':False}])
except ValueError as e:assert 'data animation' in str(e)
else:raise AssertionError('Expected data animation refusal')
assert info()['rest_sha256']==before
print('REST_NATIVE_OK',flush=True)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'REST_NATIVE_OK' in result.stdout
