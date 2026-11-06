"""Independent saved-data, refusal and cooperative rollback checks."""
import sys,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
args=sys.argv[sys.argv.index('--')+1:]
sys.path.insert(0,args[0])
import bpy,json
from mcpblender.blender import botanical_subsets as subset,botanical_foliage,botanical_trees,bridge
bridge.check_cancelled=lambda:None
bridge.report_progress=lambda value:None
bpy.ops.wm.open_mainfile(filepath=str(Path(args[1]).resolve()),use_scripts=False)
mixed=json.loads(bpy.data.collections['StructureAndOtherLeaves'][subset.META])
for obj in bpy.data.collections['StructureAndOtherLeaves'].objects:
    if obj.type=='MESH':assert obj.visible_camera==(obj.name!=mixed['population'])
source=botanical_trees.inspect({'collection':'SubsetTree'})
source_pop=botanical_foliage.resolve_roles(source['foliage'])['po']
expected={tuple(v.persistent_id):tuple(x for row in v.matrix_world for x in row) for v in bpy.context.evaluated_depsgraph_get().object_instances if v.is_instance and v.parent and v.parent.original==source_pop}
sets=[]
for name in ['ObservedLeaves','OtherLeaves']:
    meta=json.loads(bpy.data.collections[name][subset.META]);points=bpy.data.objects[meta['population']].data
    assert [v.value for v in points.attributes['id'].data]==[v.value for v in points.attributes['leaf_index'].data]
    assert len(points.vertices)==meta['plan']['selected_leaf_count']
    col=bpy.data.collections[name];hidden=col.hide_viewport;col.hide_viewport=False;bpy.context.view_layer.update()
    pop=bpy.data.objects[meta['population']]
    actual={tuple(v.persistent_id):tuple(x for row in v.matrix_world for x in row) for v in bpy.context.evaluated_depsgraph_get().object_instances if v.is_instance and v.parent and v.parent.original==pop}
    assert len(actual)==len(points.vertices) and {k[0] for k in actual}=={v.value for v in points.attributes['leaf_index'].data}
    assert all(expected[k]==matrix for k,matrix in actual.items())
    col.hide_viewport=hidden;bpy.context.view_layer.update()
    sets.append({i.value for i,k in zip(points.attributes['leaf_index'].data,points.attributes[subset.KEEP].data) if k.value})
empty=points.copy()
subset.compact_points(empty,set())
subset.verify_compact_points(empty,meta['plan']|{'selected_leaf_count':0,'selected_indices_sha256':subset.botany.digest([])})
bpy.data.meshes.remove(empty)
assert not sets[0]&sets[1]
assert sets[0]|sets[1]==set(range(meta['plan']['source_leaf_count']))
opts={'subset_collection':'ObservedLeaves'}
col,owned,state=subset.inspect(opts);assert state['valid']
pop=bpy.data.objects[state['population']]
foreign=bpy.data.objects.new('ForeignSubsetUser',pop.data);bpy.context.scene.collection.objects.link(foreign)
assert not subset.inspect(opts)[-1]['valid']
bpy.data.objects.remove(foreign,do_unlink=True);assert subset.inspect(opts)[-1]['valid']
mat=next(bpy.data.materials[n] for n in state['plan']['materials'] if bpy.data.materials[n].node_tree.nodes.get('Leaf Surface'))
socket=mat.node_tree.nodes['Leaf Surface'].inputs['Roughness'];old=socket.default_value
socket.default_value=.9;assert not subset.inspect(opts)[-1]['valid']
socket.default_value=old;assert subset.inspect(opts)[-1]['valid']
root=bpy.data.objects[state['root']];old=tuple(root.scale)
root.scale=(2,2,2);assert subset.inspect(opts)[-1]['valid']
root.scale=old;col.hide_render=False;col.hide_viewport=False
assert subset.inspect(opts)[-1]['valid']
col.hide_render=True;col.hide_viewport=True
options={'directory':str(Path(args[2]).resolve()),'views':['FRONT'],'include_structure':False,'selection':'OBSERVED',
         'render_role':'ALL_RAYS','alpha_threshold':.001,'max_total_pixels':4194304}
source_root=bpy.data.objects['SubsetTree_Root'];old=source_root.location.x
source_root.location.x+=1;bpy.context.view_layer.update()
try:subset.plan(options);raise AssertionError('Changed source accepted')
except ValueError:pass
source_root.location.x=old;bpy.context.view_layer.update()
plan=subset.plan(options)[-1];before=set(bpy.data.user_map());original=subset.inspect

def fail(p):raise InterruptedError('publication cancelled')
subset.inspect=fail
try:
    try:subset.create(options|{'subset_collection':'CancelledSubset','expected_plan':plan['plan_sha256']});raise AssertionError('Cancellation ignored')
    except InterruptedError:pass
finally:subset.inspect=original
assert set(bpy.data.user_map())==before
assert subset.inspect(opts)[-1]['valid']
print('NATIVE_SUBSET_REFUSALS_OK',flush=True)
