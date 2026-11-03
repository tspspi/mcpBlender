"""Standalone deterministic botanical graph and actual hierarchy invariants."""
import copy
import json
import pytest
from mcpblender import botany
from mcpblender.botanical_contracts import Recipe,Create

SMALL={'attractors':128,'iterations':10,'node_budget':400}


def test_recipe_normalization_and_seed_reproducibility():
    p=Recipe.model_validate(SMALL).model_dump();a=botany.generate(p);b=botany.generate(p)
    assert a==b and botany.digest(a)==botany.digest(b)
    assert botany.digest(botany.generate(SMALL|{'height':14}))==botany.digest(botany.generate(SMALL|{'height':14.0}))
    assert a==botany.generate(Recipe.model_validate(a['recipe']).model_dump())
    assert botany.generate(SMALL|{'seed':2})['branches']!=a['branches']
    altered=botany.generate(SMALL|{'height':12})
    assert {b['id'] for b in altered['branches']}&{b['id'] for b in a['branches']}
    assert botany.metrics(altered)['height']==12
    assert json.loads(json.dumps(a,allow_nan=False))==a


def test_three_full_oak_seed_hierarchies_and_structural_budgets():
    signatures=[]
    for seed in (1,2,3):
        model=botany.generate({'seed':seed});report=botany.metrics(model)
        assert 500<report['branches']<=1600 and report['organs']>100
        assert report['height']==14 and report['max_order']>=2
        assert report['width_x']>5 and report['width_y']>5
        by_id={b['id']:b for b in model['branches']};children={key:[] for key in by_id}
        for branch in model['branches']:
            if branch['parent_id']:children[branch['parent_id']].append(branch)
        for branch in model['branches']:
            assert 0<branch['radius_end']<=branch['radius_start']
            assert sum(c['radius_start']**2 for c in children[branch['id']])<=branch['radius_end']**2+1e-6
        signatures.append(botany.digest(model))
    assert len(set(signatures))==3


def test_model_rejects_damaged_semantics_and_cooperates_with_cancellation():
    source=botany.generate(SMALL)
    for change in ('cycle','radius','position','version','phase','organ','crown','axis','birth','growth','bud_nan'):
        model=copy.deepcopy(source)
        if change=='cycle':model['branches'][0]['parent_id']=model['branches'][-1]['id']
        if change=='radius':model['branches'][1]['radius_start']=99
        if change=='position':model['branches'][2]['start'][0]+=1
        if change=='version':model['format']='unknown'
        if change=='phase':model['branches'][2]['phase']=float('nan')
        if change=='organ':model['organs'][0]['parent_id']='missing'
        if change=='crown':model['crown']['radii'][0]=-1
        if change=='axis':model['branches'][1]['anchor'][0]+=1
        if change=='birth':model['branches'][1]['birth_step']=-1
        if change=='growth':model['growth']['remaining']+=1
        if change=='bud_nan':model['organs'][0]['position'][0]=float('nan')
        with pytest.raises(ValueError):botany.validate(model)
    phases=[]
    def progress(value):phases.append(value['phase'])
    def cancel():
        if phases:raise InterruptedError('cancel growth')
    with pytest.raises(InterruptedError):botany.generate(SMALL,progress=progress,cancelled=cancel)


def test_recipe_limits_and_genuinely_undersized_scaffold():
    for patch in ({'seed':True},{'attractors':0},{'light_direction':[0,0,0]},{'height':float('nan')},{'unknown':1},{'root_flare':2,'trunk_radius':1,'height':1}):
        with pytest.raises(ValueError):botany.generate(SMALL|patch)
    with pytest.raises(ValueError,match='budget'):botany.generate(SMALL|{'height':40,'segment_length':.1,'node_budget':128})
    with pytest.raises(ValueError):Create.model_validate({'collection':'ä'*21,'expected_model':'a'*64})


def test_crown_base_and_directional_controls_change_actual_geometry():
    low=botany.generate(SMALL|{'crown_base':.15});high=botany.generate(SMALL|{'crown_base':.5})
    first=lambda model:next(b for b in model['branches'] if b['order']==1)['start'][2]
    assert first(high)>first(low)
    a=botany.generate(SMALL|{'light_direction':[1,0,1],'light_weight':.7})
    b=botany.generate(SMALL|{'light_direction':[-1,0,1],'light_weight':.7})
    assert [v['end'] for v in a['branches']]!=[v['end'] for v in b['branches']]
    for model in (a,b,low,high):
        by_id={b['id']:b for b in model['branches']}
        assert all(b['age_years']<=by_id[b['parent_id']]['age_years']+1e-6 for b in model['branches'] if b['parent_id'])
