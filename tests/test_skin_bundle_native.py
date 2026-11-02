"""Cancellation/publication rollback and decoder/native mismatch refusal."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_native_skin_bundle_rollback_and_mismatch(tmp_path):
    source=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(source))+')\nOUTPUT='+repr(str(tmp_path/'bundle'))+'\n'+r'''
import bpy
from pathlib import Path
from mcpblender.blender import lods,rigging,bridge,skin_lod_export
from mcpblender.lod_contracts import Generate,Export
rigging.create_armature({'name':'Rig','bones':[{'name':'Bone','head':[0,0,0],'tail':[0,0,2]},{'name':'Control','head':[0,0,2],'tail':[0,0,3],'deform':False}]});rig=bpy.data.objects['Rig']
bpy.ops.mesh.primitive_uv_sphere_add();obj=bpy.context.object;obj.name='Skin';obj.vertex_groups.new(name='Bone').add(list(range(len(obj.data.vertices))),1,'REPLACE');m=obj.modifiers.new('Skin','ARMATURE');m.object=rig
obj.vertex_groups.new(name='Control').add(list(range(len(obj.data.vertices))),.7,'REPLACE')
rig.pose.bones['Bone'].rotation_mode='XYZ'
for frame,value in ((1,0),(3,.4),(5,0)):
    rig.pose.bones['Bone'].rotation_euler[0]=value;rig.pose.bones['Bone'].keyframe_insert(data_path='rotation_euler',frame=frame)
rig.animation_data.action['mcpblender_target']='Rig'
bpy.context.scene.frame_set(3,subframe=.25)
bridge.report_progress=lambda p:None;bridge.check_cancelled=lambda:None
source=lods.inspect_source({'name':'Skin','deformation':'SKINNED'})
p=Generate.model_validate({'name':'Skin','deformation':'SKINNED','chain':'ExportSkin','expected_source':source['source_sha256'],'levels':[{'triangle_budget':400}],'pose_frames':[1,3,5]}).model_dump()
chain=lods.generate(p);export=Export.model_validate({'chain':'ExportSkin','expected_chain':chain['chain_sha256'],'directory':OUTPUT}).model_dump(exclude_none=True)
rig.hide_select=True
action=rig.animation_data.action;had_tag='mcpblender_object_motion' in action;frame=bpy.context.scene.frame_current,bpy.context.scene.frame_subframe
selected=[o.name for o in bpy.context.selected_objects];active=bpy.context.view_layer.objects.active
before=(len(bpy.data.objects),len(bpy.data.meshes),len(bpy.data.actions));phase={}
def progress(value):phase.update(value)
def cancel():
    if phase.get('phase')=='verified decoded skin playback':raise bridge.OperationCancelled('after native replay proof')
bridge.report_progress=progress;bridge.check_cancelled=cancel
try:lods.export(export)
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected cancellation')
assert not Path(OUTPUT).exists() and not list(Path(OUTPUT).parent.glob('.mcpblender-lod-*'))
assert (len(bpy.data.objects),len(bpy.data.meshes),len(bpy.data.actions))==before
assert rig.hide_select and rig.animation_data.action==action and ('mcpblender_object_motion' in action)==had_tag
assert (bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)==frame
assert [o.name for o in bpy.context.selected_objects]==selected and bpy.context.view_layer.objects.active==active
assert lods.inspect_chain({'chain':'ExportSkin'})['chain_sha256']==chain['chain_sha256']
bridge.report_progress=lambda value:None;bridge.check_cancelled=lambda:None
# A forced independent-decode discrepancy must prevent publication as well.
original=skin_lod_export.Document.replay
def corrupt(self,clip,time,indices):
    result=original(self,clip,time,indices);result['joints']['Bone']=tuple(tuple(v+(1 if r==0 and c==3 else 0) for c,v in enumerate(row)) for r,row in enumerate(result['joints']['Bone']));return result
skin_lod_export.Document.replay=corrupt
try:lods.export(export)
except ValueError as e:assert 'joint playback' in str(e)
else:raise AssertionError('Expected native/decode mismatch')
finally:skin_lod_export.Document.replay=original
assert not Path(OUTPUT).exists() and not list(Path(OUTPUT).parent.glob('.mcpblender-lod-*'))
assert lods.inspect_chain({'chain':'ExportSkin'})['chain_sha256']==chain['chain_sha256']
result=lods.export(export);assert result['valid']
assert all('Control' in bpy.data.objects[r['object']].vertex_groups for r in chain['levels'])
assert not [o for o in bpy.data.objects if o.name.startswith('mcp_LOD_export_')]
assert ('mcpblender_object_motion' in action)==had_tag
# Fractional endpoints are refused before staging instead of truncating a clip.
rig.pose.bones['Bone'].keyframe_insert(data_path='rotation_euler',frame=.5)
try:lods.export(export|{'directory':OUTPUT+'-fractional'})
except ValueError as e:assert 'integer frame endpoints' in str(e)
else:raise AssertionError('Expected fractional clip range refusal')
assert not Path(OUTPUT+'-fractional').exists()
print('SKIN_BUNDLE_NATIVE_OK',flush=True)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'SKIN_BUNDLE_NATIVE_OK' in result.stdout
