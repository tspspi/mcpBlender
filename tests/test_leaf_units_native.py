"""Standalone metre recipes are physically stable across native scene unit scales."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_standalone_leaf_physical_units_save_reopen_and_cancel(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json,math
from pathlib import Path
from mcpblender import foliage
from mcpblender.blender import botanical_foliage as f,bridge
bridge.check_cancelled=lambda:None
shape={'length':.1,'petiole':.004,'curl':-.02,'fold':-.004}
plan=f.dispatch('plan_leaf_template',{'leaf':shape});spec=foliage.leaf_mesh(shape)
expected={k:[fn(v[a] for v in spec['vertices']) for a in range(3)] for k,fn in (('min',min),('max',max))}
for number,(system,unit) in enumerate((('METRIC',.001),('METRIC',.01),('METRIC',1),('METRIC',100),('IMPERIAL',.3048))):
    scene=bpy.context.scene;scene.unit_settings.system=system;scene.unit_settings.scale_length=unit
    value=scene.unit_settings.scale_length
    assert f.dispatch('plan_leaf_template',{'leaf':shape})['leaf_sha256']==plan['leaf_sha256']
    result=f.dispatch('create_leaf_template',{'name':'UnitLeaf'+str(number),'leaf':shape,'expected_leaf':plan['leaf_sha256']})
    obj=bpy.data.objects[result['object']];bpy.context.view_layer.update()
    # Independent matrix readback, rather than trusting returned bounds or scale.
    points=[obj.matrix_world@v.co for v in obj.data.vertices]
    actual={k:[fn(v[a] for v in points)*value for a in range(3)] for k,fn in (('min',min),('max',max))}
    assert abs(actual['max'][1]-.104)<1e-7,actual
    for key in ('min','max'):
        assert all(abs(a-b)<1e-7 for a,b in zip(actual[key],expected[key])),(system,value,actual,expected)
        assert all(abs(a-b)<1e-7 for a,b in zip(result['world_bounds_m'][key],actual[key]))
    assert scene.unit_settings.scale_length==value and result['scene_unit_scale']==value
    assert json.loads(obj['mcpblender_leaf_template'])==spec['recipe']
# Nondefault unit placement persists without rewriting the project unit settings.
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=.01
result=f.dispatch('create_leaf_template',{'name':'SavedCentimetreLeaf','leaf':shape,'expected_leaf':plan['leaf_sha256']})
bpy.ops.wm.save_as_mainfile(filepath=str(Path(OUTPUT)/'centimetre-leaf.blend'));bpy.ops.wm.open_mainfile(filepath=str(Path(OUTPUT)/'centimetre-leaf.blend'))
obj=bpy.data.objects['SavedCentimetreLeaf'];scale=bpy.context.scene.unit_settings.scale_length
assert abs(max((obj.matrix_world@v.co).y for v in obj.data.vertices)*scale-.104)<1e-7
# Cancellation restores exact IDs even after unit placement and output inspection.
ids=set(bpy.data.user_map());calls=[0]
def stop():
    calls[0]+=1
    if calls[0]==2:raise bridge.OperationCancelled('unit leaf')
bridge.check_cancelled=stop
try:f.dispatch('create_leaf_template',{'name':'CancelledUnitLeaf','leaf':shape,'expected_leaf':plan['leaf_sha256']})
except bridge.OperationCancelled:pass
else:raise AssertionError('Missing cancellation')
assert set(bpy.data.user_map())==ids and bpy.context.scene.unit_settings.scale_length==scale
print('LEAF_UNIT_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'LEAF_UNIT_NATIVE_OK' in result.stdout
