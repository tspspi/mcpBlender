"""Independent readback of compact saved subsets and exact original native poses."""
import sys,json,resource
from pathlib import Path
resource.setrlimit(resource.RLIMIT_CORE,(0,0));args=sys.argv[sys.argv.index('--')+1:];sys.path.insert(0,args[0])
import bpy
from mcpblender.blender import botanical_subsets as subsets,botanical_trees,botanical_foliage,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.ops.wm.open_mainfile(filepath=str(Path(args[1]).resolve()),use_scripts=False)
source=botanical_trees.inspect({'collection':'Canopy3'});source_pop=botanical_foliage.resolve_roles(source['foliage'])['po']
expected={tuple(v.persistent_id):tuple(x for row in v.matrix_world for x in row) for v in bpy.context.evaluated_depsgraph_get().object_instances if v.is_instance and v.parent and v.parent.original==source_pop}
assert len(expected)==88704
sets=[];counts={}
for name in ('CompactObserved','CompactUnobserved'):
    col,owned,state=subsets.inspect({'subset_collection':name});assert state['valid']
    obj=bpy.data.objects[state['population']];points=obj.data
    assert len(points.vertices)==state['selected_leaf_count']
    ids=[v.value for v in points.attributes['leaf_index'].data]
    assert [v.value for v in points.attributes['id'].data]==ids and all(v.value for v in points.attributes[subsets.KEEP].data)
    hidden=col.hide_viewport;col.hide_viewport=False;bpy.context.view_layer.update()
    actual={tuple(v.persistent_id):tuple(x for row in v.matrix_world for x in row) for v in bpy.context.evaluated_depsgraph_get().object_instances if v.is_instance and v.parent and v.parent.original==obj}
    assert len(actual)==len(ids) and {k[0] for k in actual}==set(ids)
    assert all(expected[k]==matrix for k,matrix in actual.items())
    col.hide_viewport=hidden;bpy.context.view_layer.update();sets.append(set(ids));counts[name]=len(ids)
assert not sets[0]&sets[1] and sets[0]|sets[1]==set(range(88704))
print('DENSE_COMPACT_SUBSETS_OK',json.dumps(counts),flush=True)
