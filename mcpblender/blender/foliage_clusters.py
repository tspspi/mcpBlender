"""Read-only native source admission for semantic foliage cluster workloads."""
import bpy
from mcpblender import botany,foliage_clusters as clusters
from . import botanical_trees as trees,botanical_foliage as foliage

COMMANDS={'inspect_botanical_foliage_clusters'}
SETTINGS=('anchor_order','max_leaves','max_triangles','max_clusters')


def plan(p):
    from .bridge import check_cancelled,report_progress
    if bpy.context.mode!='OBJECT':raise ValueError('Foliage cluster planning requires Object mode')
    bpy.context.view_layer.update();check_cancelled()
    values=trees.inventory({'collection':p['collection']});state=values[-1];model=values[-2]
    if not state['valid'] or state['model_error'] or state['replacement_blockers'] or not state['foliage']:
        raise ValueError('Foliage clusters require a valid uncontrolled botanical master with foliage')
    roles=foliage.resolve_roles(state['foliage']);counts=[]
    for i in range(state['foliage']['recipe']['variants']):
        check_cancelled();mesh=roles['lo'+str(i)].data
        if len(mesh.polygons)>250000:raise ValueError('Foliage cluster template geometry budget exceeded')
        # Polygon triangulation count is exact for these validated native leaf
        # templates; no calc_loop_triangles cache mutation is needed for a plan.
        count=sum(len(face.vertices)-2 for face in mesh.polygons)
        counts.append(count)
    layout=foliage.build_layout(model,state['foliage']['recipe'])
    partition=clusters.partition(model,layout,counts,**{k:p[k] for k in SETTINGS},cancelled=check_cancelled,progress=report_progress)
    # Full tree guard includes native template geometry/UV/material bindings,
    # and placement. Pagination does not alter this guard.
    guard={'source_tree_sha256':state['tree_sha256'],'partition_sha256':partition['partition_sha256']}
    offset=p['offset'];limit=p['limit']
    rows=[{k:v for k,v in row.items() if k!='leaf_indices'} for row in partition['clusters'][offset:offset+limit]]
    check_cancelled()
    return {k:v for k,v in partition.items() if k!='clusters'}|guard|{'collection':p['collection'],'plan_sha256':botany.digest(guard),
           'offset':offset,'limit':limit,'clusters':rows}


def dispatch(command,p):return plan(p)
