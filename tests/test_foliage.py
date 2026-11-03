"""Portable leaf geometry and actual deterministic attachment/budget invariants."""
import math
import pytest
from mcpblender import botany,foliage
from mcpblender.foliage_contracts import Foliage,Leaf


def test_lobed_leaf_surface_uv_area_and_curvature():
    a=foliage.leaf_mesh({});b=foliage.leaf_mesh({'curl':-.02,'lobes':7})
    assert len(a['vertices'])==len(a['uv']) and a['blade_area']>0 and a['triangles']<300
    assert min(v[1] for v in a['vertices'])==0
    assert max(v[1] for v in a['vertices'])==pytest.approx(.126)
    assert all(0<=u<=1 and 0<=v<=1 for u,v in a['uv'])
    assert a['vertices']!=b['vertices']
    for face in a['faces']:
        p,q,r=(a['vertices'][i] for i in face[:3]);assert botany.length(foliage.cross(botany.sub(q,p),botany.sub(r,p)))>1e-12
    for value in ({'length':0},{'rows':True},{'curl':float('nan')},{'width':.2,'length':.03}):
        with pytest.raises(ValueError):Leaf.model_validate(value)


def test_attachment_patterns_reproducibility_and_real_supporting_shoots():
    model=botany.generate({'attractors':64,'iterations':4,'node_budget':192})
    cfg={'shoots_per_bud':2,'attachment_nodes':4}
    a=foliage.generate(model,cfg);assert a==foliage.generate(model,cfg)
    assert len({v['id'] for v in a['leaves']})==len(a['leaves'])
    assert a['metrics']['leaves']==len(model['organs'])*8
    opposite=foliage.generate(model,cfg|{'arrangement':'OPPOSITE'})
    whorled=foliage.generate(model,cfg|{'arrangement':'WHORLED'})
    assert len(opposite['leaves'])==2*len(a['leaves']) and len(whorled['leaves'])==3*len(a['leaves'])
    for leaf in a['leaves']:
        shoot=a['shoots'][leaf['shoot_index']];assert shoot['parent_branch_id']==model['branches'][leaf['parent_branch_index']]['id']
        assert all(math.isfinite(v) for v in leaf['position']+leaf['rotation'])
        assert .8<=leaf['scale']<=1.2 and 0<=leaf['variant']<3
        vector=botany.sub(shoot['end'],shoot['start']);delta=botany.sub(leaf['position'],shoot['start'])
        assert botany.length(foliage.cross(vector,delta))<1e-6
    with pytest.raises(ValueError,match='budget'):foliage.generate(model,cfg|{'max_leaves':1})
    with pytest.raises(ValueError):Foliage.model_validate({'shoots_per_bud':0})
    with pytest.raises(ValueError):Foliage.model_validate({'arrangement':'unknown'})
