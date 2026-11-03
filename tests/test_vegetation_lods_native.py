"""Near/mid botanical LOD creation preserves semantics, native poses and ownership."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_native_nested_lods_shared_prototypes_and_owned_lifecycle(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'lods.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,json
from mcpblender import botany,foliage,wind
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,vegetation_lods as api,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.context.scene.unit_settings.scale_length=.01
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
planned=trees.plan({'recipe':recipe});state=trees.create({'collection':'LodOak','recipe':recipe,'expected_model':planned['model_sha256'],'location':[300,100,0],'radial_sides':8,'bark_tile_length':1})
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5});planned=leaves.dispatch('plan_botanical_foliage',{'collection':'LodOak','foliage':cfg})
state=leaves.dispatch('configure_botanical_foliage',{'collection':'LodOak','foliage':cfg,'expected_tree':state['tree_sha256'],'expected_foliage':planned['foliage_sha256']})
root=bpy.data.objects[state['root']];root.rotation_euler.z=.3;root.scale*=1.2;bpy.context.view_layer.update();guard=trees.inspect({'collection':'LodOak'})['tree_sha256'];ids=set(bpy.data.user_map())
p={'collection':'LodOak','wind':wind.recipe({}),'levels':[{'leaf_budget':70,'radial_sides':6,'max_coverage_loss':1,'max_silhouette_loss':1},{'leaf_budget':35,'radial_sides':5,'min_branch_radius_m':.04,'max_coverage_loss':1,'max_silhouette_loss':1},{'leaf_budget':2,'radial_sides':5,'min_branch_radius_m':1,'max_coverage_loss':1,'max_silhouette_loss':1}],
   'resolution':128,'views':['FRONT','SIDE','TOP'],'margin':2.5,'silhouette_weight':4,'max_projected_triangles':60000000,'max_mask_bytes':256*1024**2,'max_gain_evaluations':2000000}
details=api.plan(p);plan=details[-1];assert plan['valid'] and plan['native_wood_quality_pending']
try:api.plan(p|{'max_projected_triangles':details[2]['projected_triangles']})
except ValueError as e:assert 'Combined leaf/native wood' in str(e)
else:raise AssertionError('Combined native wood work was omitted from budget')
try:api.plan(p|{'max_mask_bytes':1024})
except ValueError as e:assert 'before attachment generation' in str(e)
else:raise AssertionError('Mask budget did not refuse early')
args=p|{'expected_plan':plan['plan_sha256'],'lod_collection':'OakLods','display_offset_m':[8,0,0]}
for stop_phase in ('building native botanical LOD','verified botanical LODs before handoff'):
    def stop(v):
        if v.get('phase')==stop_phase:raise bridge.OperationCancelled('LOD handoff')
    bridge.report_progress=stop
    try:api.create(args)
    except bridge.OperationCancelled:pass
    else:raise AssertionError('LOD cancellation ignored')
    bridge.report_progress=lambda v:None
    assert set(bpy.data.user_map())==ids and trees.inspect({'collection':'LodOak'})['tree_sha256']==guard
result=api.create(args);assert result['valid'] and len(result['levels'])==4 and result['prototypes']==3
assert [v['instances'] for v in result['verification']]==[140,70,35,2]
assert trees.inspect({'collection':'LodOak'})['tree_sha256']==guard
meshes={bpy.data.objects[n].data for level in result['levels'] for n in level['objects']}
assert len(meshes)==12
assert result['levels'][-1]['branches']<37
semantic=json.loads(bpy.data.collections['OakLods'][api.TEXT].as_string())
selected=set(semantic['selection']['levels'][-1]['branch_indices'])
assert {v.value for v in bpy.data.objects[result['levels'][-1]['objects'][0]].data.attributes['bot_branch_index'].data}==selected
owned=bpy.data.collections['OakLods'];sources=owned['mcpblender_leaf_sources'];assert len(sources.objects)==3
for level in result['levels']:
    leaf=bpy.data.objects[level['objects'][2]];assert leaf.modifiers[0].node_group.nodes.get('Collection Info').inputs['Collection'].default_value==sources
result=api.dispatch('activate_botanical_lod',{'lod_collection':'OakLods','expected_lods':result['lods_sha256'],'level':2});assert result['valid'] and result['active_level']==2
for level in result['levels']:
    assert all(bpy.data.objects[n].hide_render==(level['level']!=2) for n in level['objects'])
path=OUTPUT+'/lods.blend';bpy.ops.wm.save_as_mainfile(filepath=path);bpy.ops.wm.open_mainfile(filepath=path,load_ui=False,use_scripts=False)
result=api.dispatch('inspect_botanical_lods',{'lod_collection':'OakLods'});assert result['valid'] and result['active_level']==2
source=trees.inspect({'collection':'LodOak'});trees.remove({'collection':'LodOak','expected_tree':source['tree_sha256'],'discard_derived_edits':False})
result=api.dispatch('inspect_botanical_lods',{'lod_collection':'OakLods'});assert result['valid']
outside=bpy.data.objects.new('Outside',bpy.data.objects[result['levels'][0]['objects'][0]].data);bpy.context.scene.collection.objects.link(outside)
blocked=api.dispatch('inspect_botanical_lods',{'lod_collection':'OakLods'});assert blocked['ownership_blockers']
try:api.dispatch('remove_botanical_lods',{'lod_collection':'OakLods','expected_lods':blocked['lods_sha256']})
except ValueError:pass
else:raise AssertionError('Shared outside mesh user ignored')
bpy.data.objects.remove(outside,do_unlink=True)
foreign=bpy.data.objects.new('Foreign',None);bpy.data.collections['OakLods'].objects.link(foreign)
blocked=api.dispatch('inspect_botanical_lods',{'lod_collection':'OakLods'});assert blocked['ownership_blockers']
try:api.dispatch('remove_botanical_lods',{'lod_collection':'OakLods','expected_lods':blocked['lods_sha256']})
except ValueError:pass
else:raise AssertionError('Foreign member deleted')
bpy.data.objects.remove(foreign,do_unlink=True);result=api.dispatch('inspect_botanical_lods',{'lod_collection':'OakLods'})
assert result['valid'];api.dispatch('remove_botanical_lods',{'lod_collection':'OakLods','expected_lods':result['lods_sha256']})
assert 'OakLods' not in bpy.data.collections and bpy.data.materials.get('LodOak_Bark')
print('NATIVE_VEGETATION_LODS_OK')
'''.replace('OUTPUT',repr(str(tmp_path))))
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=240)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'NATIVE_VEGETATION_LODS_OK' in result.stdout
