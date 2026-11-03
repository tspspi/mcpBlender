"""Native wind key/midpoint pose readback, ownership, save/reopen and rollback."""
from pathlib import Path
import subprocess
import pytest
from test_botanical_native import pytestmark


@pytest.mark.parametrize('with_foliage',[False,True])
def test_wind_preview_native_persistence_and_guarded_rollback(tmp_path,with_foliage):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'preview.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\nWITH_FOLIAGE='+repr(with_foliage)+'\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender import botany,foliage,wind
from mcpblender.wind_contracts import PreviewPlan
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,wind_preview as preview,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.context.scene.unit_settings.scale_length=.01
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
planned=trees.plan({'recipe':recipe})
state=trees.create({'collection':'WindOak','recipe':recipe,'expected_model':planned['model_sha256'],'location':[300,100,0],'radial_sides':5,'bark_tile_length':1})
if WITH_FOLIAGE:
    cfg=foliage.recipe({'shoots_per_bud':1,'attachment_nodes':2})
    population=leaves.dispatch('plan_botanical_foliage',{'collection':'WindOak','foliage':cfg})
    state=leaves.dispatch('configure_botanical_foliage',{'collection':'WindOak','foliage':cfg,'expected_tree':state['tree_sha256'],'expected_foliage':population['foliage_sha256']})
root=bpy.data.objects[state['root']];root.rotation_euler.z=.2;root.scale*=1.1;bpy.context.view_layer.update()
args=PreviewPlan(collection='WindOak',frame_end=7,display_offset_m=[7,0,0]).model_dump()
state=trees.inspect(args);ids=set(bpy.data.user_map());frame=bpy.context.scene.frame_current;selected=set(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
plan=preview.plan(args)
roundtrip=PreviewPlan.model_validate({'collection':'WindOak','wind':args['wind']}|plan['options']).model_dump()
assert preview.plan(roundtrip)['plan_sha256']==plan['plan_sha256']
for boundary in ('baking native wind coordinates','verified wind preview before handoff'):
    def progress(value):
        if value.get('phase')==boundary:raise bridge.OperationCancelled(boundary)
    bridge.report_progress=progress
    try:preview.create(args|{'preview_collection':'Rollback','expected_plan':plan['plan_sha256']})
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Preview cancellation did not trigger')
    assert set(bpy.data.user_map())==ids and bpy.context.scene.frame_current==frame
    assert trees.inspect(args)['tree_sha256']==state['tree_sha256']
bridge.report_progress=lambda v:None
result=preview.create(args|{'preview_collection':'WindCopy','expected_plan':plan['plan_sha256']})
assert result['valid'] and result['leaf_instances']==(state['foliage']['metrics']['leaves'] if WITH_FOLIAGE else 0) and result['prototypes']==(3 if WITH_FOLIAGE else 0)
assert result['verification']['max_key_position_error_m']<1e-4
assert trees.inspect(args)['tree_sha256']==state['tree_sha256'] and bpy.context.scene.frame_current==frame
assert set(bpy.context.selected_objects)==selected and bpy.context.view_layer.objects.active==active
guard=result['preview_sha256']
source_wood=bpy.data.objects[state['members'][0]['object']].data
base=[v.index for v in source_wood.vertices if abs(v.co.z)<1e-7 and source_wood.attributes['bot_branch_index'].data[v.index].value==0]
assert len(base)==5
preview_wood=bpy.data.objects[result['roles']['wood']];endpoint=None
for frame in (1,3,3.5,7,12):
    bpy.context.scene.frame_set(int(frame),subframe=frame-int(frame));assert preview.inspect({'preview_collection':'WindCopy'})[-1]['preview_sha256']==guard
    vertices=preview_wood.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices
    assert all((vertices[i].co-source_wood.vertices[i].co).length<1e-6 for i in base)
    if frame==7:endpoint=[tuple(v.co) for v in vertices]
    if frame==12:assert [tuple(v.co) for v in vertices]==endpoint
bpy.ops.wm.save_as_mainfile(filepath=str(Path(OUTPUT)/'preview.blend'),check_existing=False)
bpy.ops.wm.open_mainfile(filepath=str(Path(OUTPUT)/'preview.blend'),load_ui=False,use_scripts=False)
result=preview.inspect({'preview_collection':'WindCopy'})[-1];assert result['valid'],result
if not WITH_FOLIAGE:
    source=trees.inspect(args);trees.remove({'collection':'WindOak','expected_tree':source['tree_sha256']})
    assert preview.inspect({'preview_collection':'WindCopy'})[-1]['valid']
obj=bpy.data.objects[result['objects'][0]];copy=obj.copy();copy.data=obj.data;bpy.context.scene.collection.objects.link(copy)
blocked=preview.inspect({'preview_collection':'WindCopy'})[-1];assert blocked['ownership_blockers']
try:preview.remove({'preview_collection':'WindCopy','expected_preview':blocked['preview_sha256']})
except ValueError as e:assert 'External reference' in str(e)
else:raise AssertionError('Shared preview geometry deleted')
bpy.data.objects.remove(copy,do_unlink=True)
foreign=bpy.data.objects.new('Foreign',None);bpy.data.collections['WindCopy'].objects.link(foreign)
blocked=preview.inspect({'preview_collection':'WindCopy'})[-1];assert blocked['ownership_blockers']
try:preview.remove({'preview_collection':'WindCopy','expected_preview':blocked['preview_sha256']})
except ValueError:pass
else:raise AssertionError('Foreign collection member deleted')
assert bpy.data.objects.get('Foreign')==foreign;bpy.data.objects.remove(foreign,do_unlink=True)
constraint=obj.constraints.new('LIMIT_LOCATION')
assert not preview.inspect({'preview_collection':'WindCopy'})[-1]['valid']
obj.constraints.remove(constraint)
result=preview.inspect({'preview_collection':'WindCopy'})[-1]
preview.remove({'preview_collection':'WindCopy','expected_preview':result['preview_sha256']})
assert 'WindCopy' not in bpy.data.collections
assert trees.inspect(args)['valid'] if WITH_FOLIAGE else bpy.data.collections.get('WindOak') is None
print('NATIVE_WIND_PREVIEW_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'NATIVE_WIND_PREVIEW_OK' in result.stdout


def test_default_master_shared_wind_population_budget(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'large.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender import botany,foliage
from mcpblender.wind_contracts import PreviewPlan
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,wind_preview as preview,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
recipe=botany.recipe({});plan=trees.plan({'recipe':recipe})
state=trees.create({'collection':'DefaultOak','recipe':recipe,'expected_model':plan['model_sha256'],'location':[0,0,0],'radial_sides':8,'bark_tile_length':1})
cfg=foliage.recipe({});p=leaves.dispatch('plan_botanical_foliage',{'collection':'DefaultOak','foliage':cfg})
state=leaves.dispatch('configure_botanical_foliage',{'collection':'DefaultOak','foliage':cfg,'expected_tree':state['tree_sha256'],'expected_foliage':p['foliage_sha256']})
args=PreviewPlan(collection='DefaultOak').model_dump();default=preview.plan(args)
assert default['leaf_instances']>20000 and default['prototypes']==3
args['frame_end']=2;planned=preview.plan(args)
before_meshes=len(bpy.data.meshes)
result=preview.create(args|{'preview_collection':'DefaultWind','expected_plan':planned['plan_sha256']})
assert result['valid'] and result['leaf_instances']==default['leaf_instances']
assert len(result['prototype_objects'])==3 and len(bpy.data.meshes)-before_meshes==len(result['roles'])+len(result['prototype_objects'])
assert trees.inspect(args)['tree_sha256']==state['tree_sha256']
(Path(__file__).parent/'population-proof.json').write_text(json.dumps({'default_plan':default,'two_frame_preview':result},indent=2))
print('DEFAULT_WIND_POPULATION_OK',result['leaf_instances'],result['verification'])
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=240)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'DEFAULT_WIND_POPULATION_OK' in result.stdout
