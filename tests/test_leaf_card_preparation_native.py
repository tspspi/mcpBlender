"""Native blade-target provenance, units, owned lifecycle and rollback."""
from pathlib import Path
import subprocess
import pytest
from test_botanical_native import pytestmark


@pytest.mark.parametrize('unit',[1,.01])
def test_blade_card_preparation_lifecycle(tmp_path,unit):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'cards.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nOUTPUT='+repr(str(tmp_path))+'\nUNIT='+repr(unit)+'\n'+r'''
import bpy
from mathutils import Matrix,Vector
from mcpblender import botany,foliage
from mcpblender.blender import botanical_trees as trees,botanical_foliage as leaves,vegetation_bake as prep,bridge,textures,leaf_card_preparation as cards
from mcpblender.vegetation_bake_contracts import Source
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.context.scene.unit_settings.scale_length=UNIT
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
plan=trees.plan({'recipe':recipe});tree=trees.create({'collection':'Oak','recipe':recipe,'expected_model':plan['model_sha256'],'location':[0,0,0],'radial_sides':8,'bark_tile_length':1})
cfg=foliage.recipe({'shoots_per_bud':2,'attachment_nodes':5,'variants':2});plan=leaves.dispatch('plan_botanical_foliage',{'collection':'Oak','foliage':cfg})
tree=leaves.dispatch('configure_botanical_foliage',{'collection':'Oak','foliage':cfg,'expected_tree':tree['tree_sha256'],'expected_foliage':plan['foliage_sha256']})
args=Source(collection='Oak',blade_cards={},texture_width=64,texture_height=128,tile_padding_pixels=2).model_dump()
source=prep.objects(args)[0];before={key:textures.mesh_signature(o,o.data) for key,o in source.items()}
ids=set(bpy.data.user_map());selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
objects,plan=prep.plan(args)
assert set(objects)=={'leaf-0','leaf-1'} and plan['can_prepare']
assert ids==set(bpy.data.user_map()) and selected==list(bpy.context.selected_objects) and active==bpy.context.view_layer.objects.active
for role,row in plan['assets'].items():
    assert row['card']['source_depth_m']>0 and row['midplane_offset_m']>0
    assert min(row['target_uv'])>0 and max(row['target_uv'])<1
try:prep.create(args|{'bake_collection':'Stale','expected_plan':'0'*64})
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Stale plan accepted')
try:prep.plan(args|{'assets':['wood']})
except ValueError as e:assert 'leaf-template' in str(e)
else:raise AssertionError('Wood accepted')
assert ids==set(bpy.data.user_map())
# The admitted native shader is deliberately constant; arbitrary input graphs refuse.
private=source['leaf-0'].data.materials[0].copy()
private.node_tree.nodes.new('ShaderNodeTexNoise')
try:cards.material(private)
except ValueError:pass
else:raise AssertionError('Custom source graph accepted')
bpy.data.materials.remove(private)
assert ids==set(bpy.data.user_map())
# Cancel during real allocation, after the first component has been prepared.
def cancel(v):
    if v.get('phase')=='preparing shared blade-card target' and v['completed_assets']==1:raise bridge.OperationCancelled('cancel cards')
bridge.report_progress=cancel
try:prep.create(args|{'bake_collection':'Cancelled','expected_plan':plan['plan_sha256']})
except bridge.OperationCancelled:pass
else:raise AssertionError('Cancellation not reached')
bridge.report_progress=lambda v:None
assert ids==set(bpy.data.user_map()) and selected==list(bpy.context.selected_objects) and active==bpy.context.view_layer.objects.active
state=prep.create(args|{'bake_collection':'Cards','expected_plan':plan['plan_sha256']})
assert state['valid'],state
assert tree['tree_sha256']==trees.inspect({'collection':'Oak'})['tree_sha256']
assert before=={key:textures.mesh_signature(o,o.data) for key,o in source.items()}
for role,row in state['components'].items():
    target=bpy.data.objects[row['name']];high=bpy.data.objects[row['prepared_source_object']]
    target.data.calc_loop_triangles();assert len(target.data.loop_triangles)==2
    assert len(high.data.polygons)==sum(f.material_index==0 for f in source[role].data.polygons)
    assert not set(high.data.materials)&set(source[role].data.materials)
    # Removing the disconnected petiole must retain source blade corner normals.
    source_normals=[n.vector.copy() for f in source[role].data.polygons if f.material_index==0 for n in [source[role].data.corner_normals[i] for i in f.loop_indices]]
    assert len(source_normals)==len(high.data.corner_normals)
    assert all((a-b.vector).length<1e-6 for a,b in zip(source_normals,high.data.corner_normals))
    assert target.hide_render and high.hide_render
    assert textures.inspect(row['inspect_texture_bake'])['bake_sha256']==row['initial_bake_sha256']
    assert row['bake_parameters']['maps']==['NORMAL','ALPHA']
    rotation=Matrix(row['card_recipe']['alignment_matrix'])
    expected=[rotation@v.co for v in source[role].data.vertices if any(v.index in f.vertices for f in source[role].data.polygons if f.material_index==0)]
    actual=[high.matrix_world@v.co for v in high.data.vertices]
    assert len(expected)==len(actual) and all(any((v-w).length<1e-6 for w in actual) for v in expected)
# Owned geometry and external users stay guarded.
row=state['components']['leaf-0'];obj=bpy.data.objects[row['name']];original=obj.data.vertices[0].co.copy();obj.data.vertices[0].co.x+=.01
assert prep.inspect({'bake_collection':'Cards'})[-1]['content_changed']
obj.data.vertices[0].co=original
state=prep.inspect({'bake_collection':'Cards'})[-1];assert state['valid']
try:prep.refresh({'bake_collection':'Cards','expected_preparation':state['preparation_sha256']})
except ValueError as e:assert 'Recreate blade-card' in str(e)
else:raise AssertionError('Card refresh accepted')
foreign=bpy.data.objects.new('Foreign',obj.data);bpy.context.scene.collection.objects.link(foreign)
blocked=prep.inspect({'bake_collection':'Cards'})[-1];assert blocked['ownership_blockers']
try:prep.remove({'bake_collection':'Cards','expected_preparation':blocked['preparation_sha256']})
except ValueError as e:assert 'External reference' in str(e)
else:raise AssertionError('Foreign mesh user removed')
bpy.data.objects.remove(foreign,do_unlink=True)
trees.remove({'collection':'Oak','expected_tree':tree['tree_sha256']})
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT+'/cards.blend')
bpy.ops.wm.open_mainfile(filepath=OUTPUT+'/cards.blend',load_ui=False,use_scripts=False)
state=prep.inspect({'bake_collection':'Cards'})[-1];assert state['valid'],state
for row in state['components'].values():assert textures.inspect(row['inspect_texture_bake'])['bake_sha256']==row['initial_bake_sha256']
prep.remove({'bake_collection':'Cards','expected_preparation':state['preparation_sha256']})
assert not bpy.data.collections.get('Cards')
print('BLADE_CARD_PREPARATION_OK',flush=True)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'BLADE_CARD_PREPARATION_OK' in result.stdout
