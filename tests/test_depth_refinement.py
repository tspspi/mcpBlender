"""Depth discontinuities with identical normals, physical units and hard budgets."""
from array import array
from copy import deepcopy
import pytest
from mcpblender import depth_tiles as tiles,depth_accuracy
from mcpblender.depth_asset_contracts import Settings
from test_depth_tiles import fixture


def source():
    d,m,v=fixture();d['channels']['TreeCapture.Depth.Z']=array('f',[4,6,4,6])
    return d,m,v


def refined(d,m,v,**kw):
    return tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_DEPTH_NORMAL','tile_pixels':2,'depth_tolerance_m':.1}|kw)


def test_depth_jump_is_refined_when_normal_variation_is_zero():
    d,m,v=source();before=deepcopy((d,m,v))
    old=tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':2})
    assert old['report']['triangles']==2
    baseline=depth_accuracy.measure(d,m,v,old,.1)
    assert baseline['coverage_weighted_mae_m']==1 and baseline['maximum_error_m']==2
    new=refined(d,m,v);report=new['report'];depth=report['depth_residuals']
    assert report['triangles']==8 and report['equivalent_normal_error_degrees']==0
    assert depth['measured_tolerance_met'] and depth['measured_depth_pixels']==4 and depth['unknown_depth_pixels']==0
    assert depth['maximum_error_m']==0 and depth['coverage_weighted_mae_m']==0
    assert (d,m,v)==before
    assert refined(d,m,v)['report']==report


def test_budget_stops_are_explicit_and_do_not_claim_tolerance():
    d,m,v=source();g=refined(d,m,v,max_triangles=2);r=g['report']
    assert r['triangles']==2 and r['budget_blocked_candidates']==1
    assert r['depth_residuals']['tolerance_unmet_cells']==1 and not r['depth_residuals']['measured_tolerance_met']
    with pytest.raises(ValueError,match='work budget'):refined(d,m,v,max_refinement_work=1)


def test_units_and_exact_sloped_plane_do_not_force_unneeded_splits():
    d,m,v=source();m['scene_unit_scale']=.1
    assert refined(d,m,v,depth_tolerance_m=.21)['report']['triangles']==2
    assert refined(d,m,v,depth_tolerance_m=.19)['report']['triangles']==8
    d,m,v=fixture();n=[.3,.2,1];length=sum(x*x for x in n)**.5
    for axis,value in zip('XYZ',n):d['channels']['TreeCapture.Normal.'+axis]=array('f',[value/length]*4)
    d['channels']['TreeCapture.Depth.Z']=array('f',[5+.3*x+.2*y for y in (.5,-.5) for x in (-.5,.5)])
    report=refined(d,m,v,depth_tolerance_m=1e-4)['report']
    assert report['triangles']==2 and report['depth_residuals']['maximum_error_m']<1e-5


def test_unknown_depth_is_counted_and_actual_float32_buffers_are_measured():
    d,m,v=source();d['channels']['TreeCapture.Combined.A'][0]=.4;d['channels']['TreeCapture.Depth.Z'][0]=float('inf')
    g=refined(d,m,v);report=g['report']['depth_residuals']
    assert report['unknown_depth_pixels']==1 and report['measured_depth_pixels']==3
    assert report['measured_tolerance_met'] # Only the measured subset, never unknown coverage.
    for i in range(2,len(g['vertices']),3):g['vertices'][i]+=.25
    changed=depth_accuracy.measure(d,m,v,g,.1)
    assert changed['maximum_error_m']==pytest.approx(.25) and not changed['measured_tolerance_met']
    for i in range(0,len(g['vertices']),3):g['vertices'][i]+=100
    missed=depth_accuracy.measure(d,m,v,g,.1)
    assert missed['projected_sample_misses']==3 and missed['maximum_error_m'] is None and not missed['measured_tolerance_met']


def test_legacy_options_and_buffers_are_identical_when_disabled():
    assert tiles.options({})==tiles.options({'depth_tolerance_m':None})
    d,m,v=source()
    a=tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':2})
    b=tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':2,'depth_tolerance_m':None})
    assert a==b and 'depth_tolerance_m' not in a['report']['options']
    for kwargs in ({'geometry_mode':'ADAPTIVE_DEPTH_NORMAL'},{'depth_tolerance_m':.1},{'geometry_mode':'ADAPTIVE_DEPTH_NORMAL','depth_tolerance_m':True},{'geometry_mode':'ADAPTIVE_DEPTH_NORMAL','depth_tolerance_m':0}):
        with pytest.raises(ValueError):tiles.options(kwargs)
        with pytest.raises(ValueError):Settings(**kwargs)


def test_depth_refinement_cancellation():
    class Cancel(Exception):pass
    def stop():raise Cancel()
    d,m,v=source()
    with pytest.raises(Cancel):tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_DEPTH_NORMAL','depth_tolerance_m':.1},cancelled=stop)
    g=refined(d,m,v)
    with pytest.raises(Cancel):depth_accuracy.measure(d,m,v,g,.1,cancelled=stop)
    d['channels']['TreeCapture.Combined.A'][0]=float('nan')
    with pytest.raises(ValueError,match='coverage'):depth_accuracy.measure(d,m,v,g,.1)
