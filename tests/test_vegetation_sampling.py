"""Independent grids reject aliasing; priorities never depend on raster positions."""
import copy
import pytest
from test_vegetation_lod import fixture
from mcpblender import vegetation_lod as lod,vegetation_sampling as sampling,foliage_coverage as coverage


def test_grid_independent_nested_priorities_and_validation_masks():
    model,layout=fixture();levels=[{'leaf_budget':110,'radial_sides':6},{'leaf_budget':100,'max_coverage_loss':.55,'max_silhouette_loss':.55}]
    a=lod.plan(model,layout,levels,resolution=64);b=lod.plan(model,layout,levels,resolution=128)
    assert a['sampling_method']==sampling.METHOD
    assert [l['leaf_indices'] for l in a['levels']]==[l['leaf_indices'] for l in b['levels']]
    assert b['valid']
    for level in b['levels']:
        subset=layout|{'leaves':[layout['leaves'][i] for i in level['leaf_indices']]}
        source=coverage.analyze(model,layout,256,include_masks=True);target=coverage.analyze(model,subset,256,include_masks=True)
        for view in b['views']:
            s=[int(v,16) for v in source['views'][view]['mask_rows_hex']];t=[int(v,16) for v in target['views'][view]['mask_rows_hex']]
            loss=sum((x&~y).bit_count() for x,y in zip(s,t))/sum(x.bit_count() for x in s)
            assert loss==level['validation_quality']['FINE'][view]['coverage_loss']
    assert set(b['levels'][1]['leaf_indices'])<set(b['levels'][0]['leaf_indices'])
    with pytest.raises(ValueError,match='multigrid.*budget'):lod.plan(model,layout,levels,max_projected_triangles=b['projected_triangles']-1)
    with pytest.raises(ValueError,match='evaluation budget'):lod.plan(model,layout,levels,max_gain_evaluations=len(layout['leaves'])-1)
    assert lod.plan(model,layout,levels,resolution=256)['quality_grids']==sampling.grids(256)


def test_finer_grid_rejects_coarse_pixel_counterexample(monkeypatch):
    model,layout=fixture();layout=copy.deepcopy(layout);model['crown']['center']=[0,0,0];model['crown']['radii']=[1,1,1]
    from mcpblender import botany
    layout['source_model_sha256']=botany.digest(model)
    # Two small blades per tile. One hits the coarse centre and misses finer
    # centres; the other hits a finer centre and is invisible on the coarse grid.
    layout['leaves']=layout['leaves'][:32]
    for i,leaf in enumerate(layout['leaves']):
        tile=i%16;col=2+tile%4*6;row=2+tile//4*6;shift=.5 if i<16 else .25
        leaf.update(position=[-1+(col+shift)*2/32,-1+(row+shift)*2/32-.066*.035,0],rotation=[0,0,0],scale=.035)
    kwargs={'resolution':32,'views':['TOP'],'margin':0}
    level={'leaf_budget':16,'max_coverage_loss':0,'max_silhouette_loss':0}
    legacy=lod.plan(model,layout,[level],sampling_method=sampling.LEGACY,**kwargs)
    assert legacy['valid'] and legacy['levels'][0]['quality']['TOP']['coverage_loss']==0
    # Deliberately feed the problematic coarse-optimised choice to the new
    # independent verifier, separate from the new area/hash ranking.
    first=legacy['levels'][0]['leaf_indices'];rest=[i for i in range(32) if i not in first]
    monkeypatch.setattr(sampling,'order',lambda *args:first+rest)
    actual=lod.plan(model,layout,[level],**kwargs)
    assert actual['levels'][0]['quality']['TOP']['coverage_loss']==0
    assert not actual['valid'] and any(q['TOP']['coverage_loss']>0 for q in actual['levels'][0]['validation_quality'].values())


def test_legacy_plan_bytes_still_match_recorded_implementation():
    # Checked-in hash represents the pre-multigrid algorithm on this fixture.
    model,layout=fixture();legacy=lod.plan(model,layout,[{'leaf_budget':70,'radial_sides':6}],sampling_method=sampling.LEGACY)
    assert 'sampling_method' not in legacy and 'validation_quality' not in legacy['levels'][0]
    from mcpblender import botany
    assert botany.digest({k:v for k,v in legacy.items() if k not in {'mask_payload_estimated_bytes','plan_sha256'}})=='04eb735ed2ebd967a7a47fdeb1b0d2ffcebb1f67afa17d6e10e98dda67f55699'
    with pytest.raises(ValueError,match='sampling method'):lod.plan(model,layout,[{'leaf_budget':70}],sampling_method='UNKNOWN')
