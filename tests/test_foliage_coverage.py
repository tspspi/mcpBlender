"""Coverage measures projected union rather than a sum of overlapping blade areas."""
import copy
import math
import pytest
from mcpblender import botany,foliage,foliage_coverage as coverage
from mcpblender.foliage_contracts import Coverage


def test_triangle_raster_union_and_pixel_centers():
    rows=[0]*8
    coverage.raster_triangle(rows,[(1,1),(5,1),(5,5)],8)
    coverage.raster_triangle(rows,[(1,1),(5,5),(1,5)],8)
    assert rows==[0,30,30,30,30,0,0,0]
    before=rows.copy();coverage.raster_triangle(rows,[(1,1),(5,1),(5,5)],8);assert rows==before
    outside=[0]*8;coverage.raster_triangle(outside,[(-5,-5),(-2,-2),(-2,-5)],8);assert not any(outside)
    for points in ([(0,1),(4,1),(7,1)],[(3.5,0),(3.5,4),(3.5,7)],[(.5,.5),(3.5,3.5),(6.5,6.5)]):
        flat=[0]*8;coverage.raster_triangle(flat,points,8);assert not any(flat)


def test_overlap_projection_rotation_and_budget():
    model=botany.generate({'attractors':64,'iterations':4,'node_budget':192})
    layout=foliage.generate(model,{'shoots_per_bud':1,'attachment_nodes':2})
    layout['leaves']=[layout['leaves'][0]|{'position':list(model['crown']['center']),'rotation':[0,0,0],'scale':8}]
    first=coverage.analyze(model,layout,resolution=64,include_masks=True)
    duplicate=copy.deepcopy(layout);duplicate['leaves']*=2
    second=coverage.analyze(model,duplicate,resolution=64,include_masks=True)
    assert first['views']==second['views']
    assert first['views']['TOP']['covered_pixels']>0
    # At this coarse resolution the nearly edge-on blade is subpixel.
    assert all(first['views'][v]['covered_pixels']==0 for v in ('FRONT','SIDE'))
    rotated=copy.deepcopy(layout);rotated['leaves'][0]['rotation']=[math.pi/2,0,0]
    view=coverage.analyze(model,rotated,resolution=64)
    assert view['views']['FRONT']['covered_pixels']>first['views']['FRONT']['covered_pixels']
    outside=copy.deepcopy(layout);outside['leaves'][0]['position'][0]+=100
    clipped=coverage.analyze(model,outside,resolution=64,views=['FRONT'])['views']['FRONT']
    assert clipped['frame_clipped'] and clipped['covered_pixels']==0
    with pytest.raises(ValueError,match='budget'):coverage.analyze(model,layout,max_projected_triangles=1)
    wrong=copy.deepcopy(layout);wrong['source_model_sha256']='bad'
    with pytest.raises(ValueError,match='source'):coverage.analyze(model,wrong)
    with pytest.raises(ValueError):Coverage.model_validate({'collection':'Oak','views':['TOP','TOP']})


def test_coverage_cancels_at_cooperative_leaf_boundary():
    model=botany.generate({'attractors':64,'iterations':4,'node_budget':192})
    layout=foliage.generate(model,{'shoots_per_bud':1,'attachment_nodes':2})
    class Cancelled(Exception):pass
    def stop():raise Cancelled()
    with pytest.raises(Cancelled):coverage.analyze(model,layout,cancelled=stop)
