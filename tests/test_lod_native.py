"""Owned-resource cleanup for deterministic mid-generation/export cancellation."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_native_lod_cancellation_cleanup_and_object_material_override(tmp_path):
    source=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(source))+')\nOUTPUT='+repr(str(tmp_path/'bundle'))+'\n'+r'''
import bpy
from pathlib import Path
from mcpblender.blender import lods,bridge
from mcpblender.lod_contracts import Generate
bpy.ops.mesh.primitive_uv_sphere_add();obj=bpy.context.object;obj.name='Source'
mat=bpy.data.materials.new('DataMaterial');override=bpy.data.materials.new('ObjectOverride');obj.data.materials.append(mat);obj.material_slots[0].link='OBJECT';obj.material_slots[0].material=override
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda p:None
second=bpy.data.materials.new('SecondRegion');obj.data.materials.append(second)
for polygon in obj.data.polygons:polygon.material_index=0 if polygon.center.z>=0 else 1
source=lods.inspect_source({'name':'Source'});assert source['materials']==['ObjectOverride','SecondRegion'] and source['used_material_indices']==[0,1]
p=Generate.model_validate({'name':'Source','chain':'NativeLOD','expected_source':source['source_sha256'],'levels':[{'triangle_budget':500},{'triangle_budget':150}]}).model_dump()
def counts():return (len(bpy.data.objects),len(bpy.data.meshes),len(bpy.data.collections))
before=counts();phase={}
def progress(values):phase.update(values)
def cancel():
    if phase.get('phase')=='verified LOD level' and phase.get('level')==1:raise bridge.OperationCancelled('after generated LOD1')
bridge.report_progress=progress;bridge.check_cancelled=cancel
try:lods.generate(p)
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected generation cancellation')
assert counts()==before and lods.inspect_source({'name':'Source'})['source_sha256']==source['source_sha256']
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda p:None
try:lods.generate(p|{'max_relative_error':0})
except ValueError as e:assert 'surface error' in str(e)
else:raise AssertionError('Expected geometric-error refusal')
assert counts()==before
chain=lods.generate(p);assert chain['valid']
assert all(level['used_material_indices']==[0,1] for level in chain['levels'])
original=chain['chain_sha256'];before=counts();phase={}
def cancel_export():
    if phase.get('phase')=='exported and decoded LOD':raise bridge.OperationCancelled('after one exported GLB')
bridge.report_progress=progress;bridge.check_cancelled=cancel_export
try:lods.export({'chain':'NativeLOD','expected_chain':original,'directory':OUTPUT})
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected export cancellation')
assert not Path(OUTPUT).exists() and not list(Path(OUTPUT).parent.glob('.mcpblender-lod-*'))
assert counts()==before and lods.inspect_chain({'chain':'NativeLOD'})['chain_sha256']==original
bridge.check_cancelled=lambda:None
bridge.report_progress=lambda p:None
result=lods.export({'chain':'NativeLOD','expected_chain':original,'directory':OUTPUT})
assert result['valid'] and lods.inspect_chain({'chain':'NativeLOD'})['chain_sha256']==original
print('LOD_NATIVE_OK',flush=True)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'LOD_NATIVE_OK' in result.stdout
