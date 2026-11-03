"""Coverage-scored LOD plans retain nested identities and closed ancestry."""
import pytest
from mcpblender import botany,foliage,foliage_coverage as coverage,vegetation_lod as lod


def fixture():
    model=botany.generate({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
    return model,foliage.generate(model,{'shoots_per_bud':2,'attachment_nodes':5})


def test_masks_match_existing_coverage_and_selection_is_nested():
    model,layout=fixture();count=len(layout['leaves'])
    levels=[{'leaf_budget':count//2,'radial_sides':6,'max_coverage_loss':1,'max_silhouette_loss':1},
            {'leaf_budget':count//4,'radial_sides':5,'min_branch_radius_m':.04,'max_coverage_loss':1,'max_silhouette_loss':1}]
    planned=lod.plan(model,layout,levels,resolution=128)
    assert planned['valid'] and not planned['source_frame_clipped']
    assert set(planned['levels'][1]['leaf_indices'])<set(planned['levels'][0]['leaf_indices'])
    assert planned==lod.plan(model,layout,levels,resolution=128)
    reference=coverage.analyze(model,layout,128,include_masks=True)
    for level in planned['levels']:
        subset=layout|{'leaves':[layout['leaves'][i] for i in level['leaf_indices']]}
        actual=coverage.analyze(model,subset,128,include_masks=True)
        for view in planned['views']:
            source=[int(v,16) for v in reference['views'][view]['mask_rows_hex']];selected=[int(v,16) for v in actual['views'][view]['mask_rows_hex']]
            loss=sum((a&~b).bit_count() for a,b in zip(source,selected))/max(1,sum(a.bit_count() for a in source))
            assert abs(level['quality'][view]['coverage_loss']-loss)<1e-12
        branch_indices=set(level['branch_indices']);lookup={b['id']:i for i,b in enumerate(model['branches'])}
        assert all(not model['branches'][i]['parent_id'] or lookup[model['branches'][i]['parent_id']] in branch_indices for i in branch_indices)
        assert all(layout['leaves'][i]['parent_branch_index'] in branch_indices for i in level['leaf_indices'])
        assert level['triangles']['expanded_total']==sum(level['triangles'][k] for k in ('wood','shoots','expanded_leaves'))


def test_quality_and_work_limits_are_not_silent():
    model,layout=fixture();level={'leaf_budget':1,'max_coverage_loss':0,'max_silhouette_loss':0}
    assert not lod.plan(model,layout,[level])['valid']
    for kwargs in ({'max_projected_triangles':1},{'max_mask_bytes':1},{'max_gain_evaluations':1}):
        with pytest.raises(ValueError,match='budget'):lod.plan(model,layout,[level],**kwargs)
    with pytest.raises(ValueError,match='decrease'):lod.plan(model,layout,[level,level])
