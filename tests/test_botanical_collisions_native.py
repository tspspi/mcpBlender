"""Semantic sleeve selection, convex containment, ownership, reload and rollback."""
from pathlib import Path
import subprocess
from test_botanical_native import pytestmark


def test_botanical_collision_native_guards_and_physical_placement(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'collisions.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nROOT='+repr(str(tmp_path))+'\n'+r'''
import bpy,json,bmesh,math
from mathutils import Vector
from pathlib import Path
from mcpblender import botany
from mcpblender.botanical_collision_contracts import Source,Create
from mcpblender.blender import botanical_trees as trees,botanical_collisions as api,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.context.scene.unit_settings.scale_length=.01
recipe=botany.recipe({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
plan=trees.plan({'recipe':recipe});source=trees.create({'collection':'CollisionSource','recipe':recipe,'expected_model':plan['model_sha256'],'location':[300,100,0],'radial_sides':8,'bark_tile_length':1})
root=bpy.data.objects[source['root']];root.rotation_euler.z=.3;root.scale.x*=1.2;bpy.context.view_layer.update()
source=trees.inspect({'collection':'CollisionSource'});ids=set(bpy.data.user_map());frame=bpy.context.scene.frame_current;selected=set(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
args=Source(collection='CollisionSource',min_radius_m=.08,max_branch_order=1).model_dump()
values,pieces,planned=api.plan(args);assert planned==api.plan(args)[-1] and set(bpy.data.user_map())==ids
assert planned['requested_branches'] and planned['collider_count']==len(pieces)
for patch,error in (({'max_colliders':1},'count budget'),({'triangle_budget':4},'triangle budget'),({'min_radius_m':10},'No branches')):
 try:api.plan(args|patch)
 except ValueError as e:assert error in str(e),(error,str(e))
 else:raise AssertionError('Expected collision budget refusal')
 assert set(bpy.data.user_map())==ids
# Frozen placement accepts nonuniform positive scale, but refuses reflection/shear.
root.scale.x=-root.scale.x;bpy.context.view_layer.update()
try:api.plan(args)
except ValueError as e:assert 'positive' in str(e)
else:raise AssertionError('Reflected collision placement accepted')
root.scale.x=-root.scale.x
parent=bpy.data.objects.new('ShearParent',None);bpy.context.scene.collection.objects.link(parent);parent.scale=(2,1,1);root.parent=parent;bpy.context.view_layer.update()
try:api.plan(args)
except ValueError as e:assert 'shear' in str(e)
else:raise AssertionError('Sheared collision placement accepted')
root.parent=None;bpy.data.objects.remove(parent,do_unlink=True);bpy.context.view_layer.update()
assert set(bpy.data.user_map())==ids and trees.inspect(args)['tree_sha256']==source['tree_sha256']
create=Create(**args,expected_plan=planned['plan_sha256'],collision_collection='CollisionPieces',display_offset_m=[7,0,0]).model_dump()
for phase in ('building botanical collision pieces','verified botanical collision before handoff'):
 def stop(value):
  if value.get('phase')==phase:raise bridge.OperationCancelled(phase)
 bridge.report_progress=stop
 try:api.create(create)
 except bridge.OperationCancelled:pass
 else:raise AssertionError('Collision cancellation ignored')
 assert set(bpy.data.user_map())==ids and trees.inspect(args)['tree_sha256']==source['tree_sha256']
bridge.report_progress=lambda v:None
try:api.create(create|{'expected_plan':'0'*64})
except ValueError as e:assert 'stale' in str(e)
else:raise AssertionError('Stale collision plan accepted')
assert set(bpy.data.user_map())==ids
created=api.create(create);assert created['valid'] and created['source_unchanged']
assert trees.inspect(args)['tree_sha256']==source['tree_sha256']
bpy.context.scene.unit_settings.scale_length=.02
changed_unit=api.inspect({'collision_collection':'CollisionPieces'})[-1];assert not changed_unit['valid'] and changed_unit['collision_sha256']!=created['collision_sha256']
bpy.context.scene.unit_settings.scale_length=.01
assert api.inspect({'collision_collection':'CollisionPieces'})[-1]['valid']
assert set(bpy.context.selected_objects)==selected and bpy.context.view_layer.objects.active==active and bpy.context.scene.frame_current==frame
collision_root=bpy.data.objects[created['root']]
assert (collision_root.matrix_world.translation-root.matrix_world.translation-Vector((700,0,0))).length<1e-4
model=values[-2];wood=values[2][0].data
for row,shape in zip(created['plan']['pieces'],pieces):
 obj=bpy.data.objects[next(x['object'] for x in created['colliders'] if x['branch_index']==row['branch_index'])]
 bm=bmesh.new();bm.from_mesh(obj.data);bm.normal_update()
 try:
  assert all(e.is_manifold for e in bm.edges) and bm.calc_volume(signed=True)>0
  assert abs(bm.calc_volume()-row['volume_local_m3'])<max(1e-8,row['volume_local_m3']*1e-5)
  from mcpblender.collision_hulls import subtract,cross,dot
  for face in obj.data.polygons:
   a,b,c=[tuple(obj.data.vertices[i].co) for i in face.vertices];normal=cross(subtract(b,a),subtract(c,a));size=math.sqrt(dot(normal,normal))
   assert all(dot(subtract(tuple(wood.vertices[i].co),a),normal)/size<=row['containment_tolerance_local_m'] for i in shape['source_vertex_indices'])
 finally:bm.free()
 assert obj.hide_render and not obj.rigid_body
 assert set(v.value for v in obj.data.attributes['bot_branch_index'].data)=={row['branch_index']}
# Branch identity and changed owned data require inspection and explicit discard.
obj=bpy.data.objects[created['objects'][0]];original=obj[api.BRANCH];obj[api.BRANCH]=-1
state=api.inspect({'collision_collection':'CollisionPieces'})[-1];assert not state['valid'] and state['collision_sha256']!=created['collision_sha256']
obj[api.BRANCH]=original
obj.data.vertices[0].co.x+=.01
state=api.inspect({'collision_collection':'CollisionPieces'})[-1];assert not state['valid']
try:api.dispatch('remove_botanical_collisions',{'collision_collection':'CollisionPieces','expected_collision':state['collision_sha256']})
except ValueError as e:assert 'discard' in str(e)
else:raise AssertionError('Edited collision silently removed')
obj.data.vertices[0].co.x-=.01
# Use a fresh untouched profile for persistence; edits are intentionally guarded.
state=api.inspect({'collision_collection':'CollisionPieces'})[-1]
api.dispatch('remove_botanical_collisions',{'collision_collection':'CollisionPieces','expected_collision':state['collision_sha256'],'discard_derived_edits':True})
created=api.create(create);bpy.ops.wm.save_as_mainfile(filepath=str(Path(ROOT)/'collisions.blend'))
bpy.ops.wm.open_mainfile(filepath=str(Path(ROOT)/'collisions.blend'),load_ui=False,use_scripts=False)
state=api.inspect({'collision_collection':'CollisionPieces'})[-1];assert state['valid'] and state['source_unchanged']
# Unparented placement is an explicit alternative for native rigid-body tools.
p2=Create(**args,expected_plan=api.plan(args)[-1]['plan_sha256'],collision_collection='Unparented',parent_to_root=False,display_offset_m=[7,0,0]).model_dump()
u=api.create(p2);assert u['valid'] and u['parent_to_root'] is False
expected=bpy.data.objects[u['root']].matrix_world
for name in u['objects']:
 obj=bpy.data.objects[name];assert obj.parent is None
 assert max(abs(obj.matrix_world[i][j]-expected[i][j]) for i in range(4) for j in range(4))<1e-4
api.dispatch('remove_botanical_collisions',{'collision_collection':'Unparented','expected_collision':u['collision_sha256']})
# A source move reports stale provenance but preserves the independent snapshot.
source=trees.inspect(args);bpy.data.objects[source['root']].location.x+=1
state=api.inspect({'collision_collection':'CollisionPieces'})[-1];assert state['valid'] and state['source_unchanged'] is False
source=trees.inspect(args);trees.remove({'collection':'CollisionSource','expected_tree':source['tree_sha256']})
state=api.inspect({'collision_collection':'CollisionPieces'})[-1];assert state['valid'] and not state['source_present']
# Foreign references, members, persistent IDs and attached physics block deletion.
obj=bpy.data.objects[state['objects'][0]];foreign=obj.copy();foreign.data=obj.data;bpy.context.scene.collection.objects.link(foreign)
state=api.inspect({'collision_collection':'CollisionPieces'})[-1];assert state['ownership_blockers']
try:api.dispatch('remove_botanical_collisions',{'collision_collection':'CollisionPieces','expected_collision':state['collision_sha256'],'discard_derived_edits':True})
except ValueError:pass
else:raise AssertionError('Foreign mesh reference removed')
bpy.data.objects.remove(foreign,do_unlink=True)
foreign=bpy.data.objects.new('Foreign',None);bpy.data.collections['CollisionPieces'].objects.link(foreign)
assert api.inspect({'collision_collection':'CollisionPieces'})[-1]['ownership_blockers'];bpy.data.objects.remove(foreign,do_unlink=True)
obj.use_fake_user=True;assert api.inspect({'collision_collection':'CollisionPieces'})[-1]['ownership_blockers'];obj.use_fake_user=False
bpy.context.view_layer.objects.active=obj;obj.select_set(True);bpy.ops.rigidbody.object_add();assert api.inspect({'collision_collection':'CollisionPieces'})[-1]['ownership_blockers'];bpy.ops.rigidbody.object_remove()
state=api.inspect({'collision_collection':'CollisionPieces'})[-1]
api.dispatch('remove_botanical_collisions',{'collision_collection':'CollisionPieces','expected_collision':state['collision_sha256'],'discard_derived_edits':True})
assert 'CollisionPieces' not in bpy.data.collections
print('BOTANICAL_COLLISION_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'BOTANICAL_COLLISION_NATIVE_OK' in result.stdout
