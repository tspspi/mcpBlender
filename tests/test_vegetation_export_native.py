"""Real botanical GLBs and shared-instance semantics retain editable masters."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_bare_foliated_bundles_native_instances_and_rollback(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'vegetation.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender import botany,foliage,wind,vegetation_interchange as schema
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,vegetation_export as api,bridge
from mcpblender.wind_contracts import BotanicalExportPlan,BotanicalExport
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.context.scene.unit_settings.scale_length=.01
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
plan=trees.plan({'recipe':recipe})
state=trees.create({'collection':'ExportOak','recipe':recipe,'expected_model':plan['model_sha256'],'location':[300,100,0],'radial_sides':5,'bark_tile_length':1})
root=bpy.data.objects[state['root']];root.rotation_euler.z=.3;root.scale*=1.2;bpy.context.view_layer.update()
def options():return BotanicalExportPlan(collection='ExportOak').model_dump()
def arguments(directory):
    p=options();return BotanicalExport(**p,expected_export=api.inspect(p)['export_sha256'],directory=str(Path(OUTPUT)/directory)).model_dump()
ids=set(bpy.data.user_map());guard=trees.inspect({'collection':'ExportOak'})['tree_sha256']
bare=api.export(arguments('bare'));assert bare['proof']['leaf_instances']==0 and len(bare['proof']['assets'])==1
assert set(bpy.data.user_map())==ids and trees.inspect({'collection':'ExportOak'})['tree_sha256']==guard
cfg=foliage.recipe({'shoots_per_bud':1,'attachment_nodes':2})
planned=leaves.dispatch('plan_botanical_foliage',{'collection':'ExportOak','foliage':cfg})
state=leaves.dispatch('configure_botanical_foliage',{'collection':'ExportOak','foliage':cfg,'expected_tree':guard,'expected_foliage':planned['foliage_sha256']})
p=arguments('foliated');ids=set(bpy.data.user_map());guard=state['tree_sha256'];frame=bpy.context.scene.frame_current;selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
for patch in ({'expected_export':'0'*64},{'max_bytes':1024}):
    try:api.export(p|patch)
    except ValueError:pass
    else:raise AssertionError('Botanical guard/byte budget bypassed')
for stop_phase in ('verified attribute bundle before publication','verified botanical bundle before publication'):
    def stop(v):
        if v.get('phase')==stop_phase:raise bridge.OperationCancelled('botanical staging')
    bridge.report_progress=stop
    try:api.export(p)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Botanical publication cancellation ignored')
    assert not Path(p['directory']).exists() and set(bpy.data.user_map())==ids
    assert not list(Path(OUTPUT).glob('.mcpblender-botanical-*'))
    assert trees.inspect({'collection':'ExportOak'})['tree_sha256']==guard
bridge.report_progress=lambda v:None
result=api.export(p);proof=schema.validate(p['directory'])
assert proof==result['proof'] and proof['leaf_instances']==state['foliage']['metrics']['leaves']
assert proof['shared_leaf_templates']==cfg['variants'] and len(proof['assets'])==2+cfg['variants']
assert result['native_instance_readback']['instances']==proof['leaf_instances']
assert result['native_instance_readback']['max_linear_component_error']<1e-5
assert set(bpy.data.user_map())==ids and trees.inspect({'collection':'ExportOak'})['tree_sha256']==guard
assert bpy.context.scene.frame_current==frame and list(bpy.context.selected_objects)==selected and bpy.context.view_layer.objects.active==active
folder=Path(p['directory']);semantic=folder/'semantics.json';original=semantic.read_bytes();record=json.loads((folder/'manifest.json').read_text())
data=json.loads(original);data['foliage']['leaves'][0]['flutter']+=.2;semantic.write_text(json.dumps(data))
try:schema.validate(folder)
except ValueError as e:assert 'hash' in str(e)
else:raise AssertionError('Semantic tamper ignored')
record['files']=schema.files(folder);(folder/'manifest.json').write_text(json.dumps(record))
try:schema.validate(folder)
except ValueError as e:assert 'attachments' in str(e) or 'binding' in str(e)
else:raise AssertionError('Changed instance semantics accepted after rehash')
semantic.write_bytes(original);record['files']=schema.files(folder);(folder/'manifest.json').write_text(json.dumps(record));schema.validate(folder)
trees.remove({'collection':'ExportOak','expected_tree':guard,'discard_derived_edits':False})
assert schema.validate(folder)==proof
print('BOTANICAL_BUNDLE_OK',proof['leaf_instances'])
'''.replace('OUTPUT',repr(str(tmp_path))))
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=240)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'BOTANICAL_BUNDLE_OK' in result.stdout
