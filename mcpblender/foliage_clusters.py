"""Bounded semantic/spatial leaf partitions; no Blender or mesh realization."""
import math
from . import botany

METHOD='BRANCH_AXIS_MEDIAN_V1'


def partition(model,layout,triangle_counts,*,anchor_order=2,max_leaves=512,
              max_triangles=100000,max_clusters=1024,cancelled=lambda:None,progress=lambda v:None):
    """Partition every leaf exactly once, respecting actual variant triangle costs.

    Inputs are canonical parent-first branch graphs and generated leaf populations.
    Bounds describe leaf centres in source-local metres, not blade extents or cards.
    """
    for name,value,low,high in [('anchor_order',anchor_order,0,8),('max_leaves',max_leaves,1,1024),
                              ('max_triangles',max_triangles,1,250000),('max_clusters',max_clusters,1,4096)]:
        if type(value)!=int or not low<=value<=high:raise ValueError('Invalid cluster '+name)
    branches=model['branches'];leaves=layout['leaves']
    if not 1<=len(branches)<=4000 or not 1<=len(leaves)<=200000:raise ValueError('Cluster source population budget exceeded')
    if not 1<=len(triangle_counts)<=16 or any(type(n)!=int or n<1 or n>250000 for n in triangle_counts):raise ValueError('Invalid variant triangle counts')
    cancelled();lookup={};anchors=[];axis_roots=[]
    for index,b in enumerate(branches):
        if b['id'] in lookup:raise ValueError('Duplicate cluster source branch ID')
        parent=lookup.get(b['parent_id'])
        if b['parent_id'] is not None and parent is None:raise ValueError('Cluster source requires parent-first branches')
        if type(b['order'])!=int or not 0<=b['order']<=8:raise ValueError('Invalid cluster branch order')
        # A canonical axis is a connected parent chain. Retain its first segment.
        axis_root=axis_roots[parent] if parent is not None and branches[parent]['axis_id']==b['axis_id'] else index
        axis_roots.append(axis_root)
        anchor=anchors[parent] if b['order']>anchor_order and parent is not None else axis_root
        anchors.append(anchor);lookup[b['id']]=index
    groups={};identities=set();costs=[]
    for index,leaf in enumerate(leaves):
        if index%256==0:
            cancelled();progress({'phase':'grouping canonical foliage clusters','completed':index,'total':len(leaves)})
        parent=leaf['parent_branch_index'];variant=leaf['variant'];position=leaf['position']
        if type(parent)!=int or not 0<=parent<len(branches) or type(variant)!=int or not 0<=variant<len(triangle_counts):raise ValueError('Invalid cluster leaf branch/variant index')
        if not isinstance(leaf['id'],str) or not leaf['id'] or leaf['id'] in identities:raise ValueError('Cluster leaves require distinct IDs')
        if len(position)!=3 or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in position):raise ValueError('Finite cluster leaf centres required')
        cost=triangle_counts[variant]
        if cost>max_triangles:raise ValueError('One leaf exceeds cluster triangle budget')
        costs.append(cost);identities.add(leaf['id']);groups.setdefault(anchors[parent],[]).append(index)
    # Subdivision only increases group count: refuse lower bounds before sorting.
    if sum(max(math.ceil(len(g)/max_leaves),math.ceil(sum(costs[i] for i in g)/max_triangles)) for g in groups.values())>max_clusters:
        raise ValueError('Foliage cluster count budget exceeded')
    pending=[(anchor,groups[anchor]) for anchor in sorted(groups,reverse=True)];result=[]
    while pending:
        cancelled();anchor,indices=pending.pop();cost=sum(costs[i] for i in indices)
        low=[min(leaves[i]['position'][a] for i in indices) for a in range(3)]
        high=[max(leaves[i]['position'][a] for i in indices) for a in range(3)]
        if len(indices)>max_leaves or cost>max_triangles:
            axis=max(range(3),key=lambda a:high[a]-low[a]);indices.sort(key=lambda i:(leaves[i]['position'][axis],leaves[i]['id']))
            mid=len(indices)//2;pending.extend(((anchor,indices[mid:]),(anchor,indices[:mid])))
            if len(result)+len(pending)>max_clusters:raise ValueError('Foliage cluster count budget exceeded')
            continue
        indices.sort();ids=sorted(leaves[i]['id'] for i in indices)
        row={'index':len(result),'anchor_branch_index':anchor,'anchor_branch_id':branches[anchor]['id'],
             'anchor_axis_id':branches[anchor]['axis_id'],'leaf_count':len(indices),'source_triangles':cost,
             'center_bounds_local_m':{'min':low,'max':high},'leaf_ids_sha256':botany.digest(ids),'leaf_indices':indices}
        result.append(row);progress({'phase':'partitioning bounded foliage clusters','completed':len(result),'pending':len(pending)})
    summary={'method':METHOD,'settings':{'anchor_order':anchor_order,'max_leaves':max_leaves,'max_triangles':max_triangles,'max_clusters':max_clusters},
             'source_leaves':len(leaves),'source_branches':len(branches),'source_triangles':sum(costs),'variant_triangle_counts':list(triangle_counts),
             'cluster_count':len(result),'anchor_groups':len(groups),'clusters':result,
             'scope':'Exact leaf membership partition, excluding woody sleeves/shoots. Bounds are leaf centres, not blade extents. No realization, card fitting, bake, optical, wind or far-LOD quality claim.'}
    cancelled();return summary|{'partition_sha256':botany.digest(summary)}
