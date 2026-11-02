"""Native lock/mask/shape identity and deterministic mid-write rollback probes."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_native_skin_transactions_and_lock_preservation(tmp_path):
    source=Path(__file__).resolve().parents[1]
    script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(source))+')\n'+r'''
import bpy
from mcpblender.blender import skin_weights as skin,bridge
from mcpblender.skin_contracts import COMMANDS
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
data=bpy.data.armatures.new('RigData');rig=bpy.data.objects.new('Rig',data);bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
for i,name in enumerate(['Left','Right','Extra']):
    bone=data.edit_bones.new(name);bone.head=(i,0,0);bone.tail=(i,0,1)
bpy.ops.object.mode_set(mode='OBJECT')
mesh=bpy.data.meshes.new('SkinData');mesh.from_pydata([(i,0,z) for z in range(100) for i in range(3)],[],[(i,i+1,i+3) for i in range(296) if i%3<2]);mesh.update()
obj=bpy.data.objects.new('Skin',mesh);bpy.context.scene.collection.objects.link(obj)
mod=obj.modifiers.new('Skin','ARMATURE');mod.object=rig
for name,value in [('Left',.25),('Right',.25),('Pin',.8)]:obj.vertex_groups.new(name=name).add(list(range(300)),value,'REPLACE')
obj.vertex_groups['Left'].lock_weight=True
basis=obj.shape_key_add(name='Basis');shape=obj.shape_key_add(name='Lift');shape.data[2].co.z+=.3
shape.driver_add('value').driver.expression='0.2'
old_mesh=obj.data;old_key=obj.data.shape_keys;old_driver=old_key.animation_data.drivers[0]
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda p:None

def info():return skin.inspect({'name':'Skin','limit':256})
def edit(command,**params):
    values=COMMANDS[command][0].model_validate({'name':'Skin','expected_weights':info()['weights_sha256'],**params}).model_dump()
    return skin.dispatch(command,values)

result=edit('repair_skin_weights',max_influences=2)
assert result['vertex_samples'][0]['weights']=={'Left':.25,'Right':.75}
assert result['vertex_samples'][0]['nondeform_weights']['Pin']>.799
assert obj.data==old_mesh and obj.data.shape_keys==old_key and old_key.animation_data.drivers[0]==old_driver
# A locked group absent from a neighbor must remain absent through smoothing.
obj.vertex_groups['Left'].remove([1]);obj.vertex_groups['Right'].add([1],1,'REPLACE')
edit('smooth_skin_weights',vertices=[1],strength=1)
assert info()['vertex_samples'][1]['weights'].get('Left',0)==0
assert abs(info()['vertex_samples'][1]['weight_sum']-1)<1e-6
# Fail after memberships have been written, including a newly created group.
before=info()['weights_sha256'];group_names=list(obj.vertex_groups.keys());checks=0

def cancel():
    global checks
    checks+=1
    if checks==3:raise bridge.OperationCancelled('injected after first 128 writes')
bridge.check_cancelled=cancel
try:edit('set_skin_weights',weights=[{'vertex':i,'weights':{'Extra':1}} for i in range(300)])
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected cancellation')
assert checks==3 and info()['weights_sha256']==before and list(obj.vertex_groups.keys())==group_names
assert obj.data==old_mesh and obj.data.shape_keys==old_key
# Explicitly overriding locks changes weights but never changes UI lock flags.
bridge.check_cancelled=lambda:None
edit('set_skin_weights',weights=[{'vertex':0,'weights':{'Right':1}}],respect_locks=False)
assert info()['vertex_samples'][0]['weights']=={'Right':1} and obj.vertex_groups['Left'].lock_weight
# Shared copy cancellation must restore original data and remove owned mesh+Key.
peer=obj.copy();peer.name='Peer';bpy.context.scene.collection.objects.link(peer)
before=info()['weights_sha256'];counts=(len(bpy.data.meshes),len(bpy.data.shape_keys));checks=0
bridge.check_cancelled=cancel
try:edit('set_skin_weights',weights=[{'vertex':i,'weights':{'Extra':1}} for i in range(300)],make_single_user=True)
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected shared cancellation')
assert obj.data==peer.data==old_mesh and info()['weights_sha256']==before
assert counts==(len(bpy.data.meshes),len(bpy.data.shape_keys))
bridge.check_cancelled=lambda:None
edit('repair_skin_weights',make_single_user=True)
assert obj.data!=peer.data and obj.data.shape_keys!=peer.data.shape_keys
assert peer.data==old_mesh and peer.data.shape_keys==old_key and old_key.animation_data.drivers[0]==old_driver
print('SKIN_NATIVE_OK',flush=True)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'SKIN_NATIVE_OK' in result.stdout
