"""Full-size preset early/late cancellation and existing-material isolation."""
import json
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark
from mcpblender.botanical_preset_contracts import Plan


def test_full_canopy_preset_rollback_and_material_isolation(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'preset-faults.py'
    script.write_text('import sys,json\nsys.path.insert(0,'+repr(str(repo))+')\nPARAMS=json.loads('+repr(json.dumps(Plan().model_dump()))+')\n'+r'''
import bpy
from mcpblender.blender import botanical_presets as api,botanical_trees as trees,botanical_foliage as foliage,bridge,assemblies
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
protected=bpy.data.materials.new('Trial_Bark');protected.use_nodes=True
protected.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.7,.1,.2,1)
original=assemblies.record(protected);ids=set(bpy.data.user_map());names={v:v.name for v in ids}
plan=api.plan(PARAMS)[-1];args=PARAMS|{'collection':'Trial','location':[0,0,0],'expected_preset':plan['preset_sha256']}
try:api.create(args|{'expected_preset':'0'*64})
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Stale preset plan accepted')
assert set(bpy.data.user_map())==ids
for phase in ('verified botanical master','verified botanical preset before handoff'):
    def stop(value):
        if value.get('phase')==phase:raise bridge.OperationCancelled('preset handoff')
    bridge.report_progress=stop
    try:api.create(args)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Preset cancellation ignored')
    bridge.report_progress=lambda v:None
    assert set(bpy.data.user_map())==ids and all(v.name==name for v,name in names.items())
    assert assemblies.record(protected)==original
state=api.create(args);assert state['valid'] and state['foliage']['metrics']['leaves']==92136
roles=foliage.resolve_roles(state['foliage'])
assert len(roles['pc'].objects)==3 and len(roles['pm'].vertices)==92136
assert any(n.bl_idname=='GeometryNodeInstanceOnPoints' for n in roles['gn'].nodes)
assert not any(n.bl_idname=='GeometryNodeRealizeInstances' for n in roles['gn'].nodes)
assert state['geometry']['bark_material']!=protected.name and assemblies.record(protected)==original
assert state['asset_preset']['creation_plan_sha256']==plan['preset_sha256']
trees.remove({'collection':'Trial','expected_tree':state['tree_sha256']})
assert assemblies.record(protected)==original
print('CANOPY_PRESET_ROLLBACK_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=360)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'CANOPY_PRESET_ROLLBACK_OK' in result.stdout
