"""Semantic membership, actual mixed costs, budgets and cooperative stops."""
import copy
import pytest
from mcpblender import foliage_clusters as clusters
from test_vegetation_lod import fixture


def test_complete_disjoint_deterministic_semantic_partitions():
    model,layout=fixture();plan=clusters.partition(model,layout,[196]*layout['recipe']['variants'],max_leaves=17,max_triangles=2500)
    assert plan==clusters.partition(model,layout,[196]*layout['recipe']['variants'],max_leaves=17,max_triangles=2500)
    indices=[i for row in plan['clusters'] for i in row['leaf_indices']]
    assert sorted(indices)==list(range(len(layout['leaves'])))
    assert sum(row['source_triangles'] for row in plan['clusters'])==196*len(indices)
    lookup={b['id']:i for i,b in enumerate(model['branches'])}
    for row in plan['clusters']:
        assert row['leaf_count']<=12 and row['source_triangles']<=2500
        for i in row['leaf_indices']:
            branch=layout['leaves'][i]['parent_branch_index'];ancestors={branch}
            while model['branches'][branch]['parent_id'] is not None:
                branch=lookup[model['branches'][branch]['parent_id']];ancestors.add(branch)
            assert row['anchor_branch_index'] in ancestors
    # Identity-based tie break keeps the same leaf groups if the source list is reordered.
    shuffled=copy.deepcopy(layout);shuffled['leaves'].reverse()
    other=clusters.partition(model,shuffled,[196]*layout['recipe']['variants'],max_leaves=17,max_triangles=2500)
    assert [r['leaf_ids_sha256'] for r in plan['clusters']]==[r['leaf_ids_sha256'] for r in other['clusters']]


def test_mixed_native_costs_limits_invalid_data_and_cancellation():
    model,layout=fixture();layout=copy.deepcopy(layout)
    for i,leaf in enumerate(layout['leaves']):leaf['variant']=i%2;leaf['position']=[0,0,0]
    plan=clusters.partition(model,layout,[3,97],max_leaves=1024,max_triangles=101)
    assert all(r['source_triangles']==sum([3,97][layout['leaves'][i]['variant']] for i in r['leaf_indices'])<=101 for r in plan['clusters'])
    for kwargs,message in (({'max_clusters':1},'count budget'),({'max_triangles':96},'One leaf'),({'max_leaves':True},'Invalid cluster'),({'anchor_order':9},'Invalid cluster')):
        with pytest.raises(ValueError,match=message):clusters.partition(model,layout,[3,97],**kwargs)
    bad=copy.deepcopy(layout);bad['leaves'][1]['id']=bad['leaves'][0]['id']
    with pytest.raises(ValueError,match='distinct IDs'):clusters.partition(model,bad,[3,97])
    bad=copy.deepcopy(layout);bad['leaves'][0]['position'][0]=float('nan')
    with pytest.raises(ValueError,match='Finite'):clusters.partition(model,bad,[3,97])
    ticks=[]
    def stop():
        ticks.append(1)
        if len(ticks)==3:raise InterruptedError('stop')
    with pytest.raises(InterruptedError):clusters.partition(model,layout,[3,97],cancelled=stop)
