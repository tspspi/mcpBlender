"""Paired first-hit geometry, explicit unknowns and strict span selection."""
from array import array
from copy import deepcopy
import math
import pytest
from mcpblender import depth_shadow,card_views
from mcpblender.depth_asset_contracts import Source,Layer,ShadowMask


def fixture(layer='BACK',receiver='FRONT'):
    def camera(name):
        u,v=card_views.FRAMES[name];n=card_views.DIRECTIONS[name]
        return {'view':name,'matrix_world':[[u[i],v[i],n[i],5*n[i]+(10,20,30)[i]] for i in range(3)]+[[0,0,0,1]],'ortho_scale':2.,'clip_start':.1,'clip_end':20.}
    def data(depth):return {'width':2,'height':2,'data_window':(0,0,1,1),'channels':{'TreeCapture.Combined.A':array('f',[1]*4),'TreeCapture.Depth.Z':array('f',depth)}}
    return data([4,5,6,7]),data([2,3,4,5]),camera(layer),camera(receiver)


def build(*args,unit=1.,minimum=0.,**kw):return depth_shadow.build(*args,unit,{},dict(receiver_view=args[3]['view'],minimum_span_m=minimum),**kw)


@pytest.mark.parametrize('pair',[('BACK','FRONT'),('FRONT','BACK'),('SIDE','LEFT'),('LEFT','SIDE'),('TOP','BOTTOM'),('BOTTOM','TOP'),('FRONT_RIGHT','BACK_LEFT'),('BACK_RIGHT','FRONT_LEFT')])
def test_mirrored_pairing_world_units_and_strict_threshold(pair):
    args=fixture(*pair);pixels,report=build(*args)
    # Layer order spans: 10-4-3=3, 10-5-2=3, 10-6-5=-1, 10-7-4=-1.
    assert list(pixels)==[1,1,0,0]
    assert report['known_pixels']==4 and report['retained_pixels']==2
    assert report['original_alpha_mass']==4 and report['retained_alpha_mass']==2
    assert report['measured_span_range_m']==pytest.approx([-1,3])
    assert build(*args,unit=.1,minimum=.31)[0]==array('f',[0]*4)
    assert build(*args,minimum=3.01)[0]==array('f',[0]*4)
    assert build(*args)[1]==report


def test_exact_boundary_partial_coverage_unknown_depth_and_invalid_alpha():
    args=fixture();layer,receiver,*_=args
    layer['channels']['TreeCapture.Depth.Z']=array('f',[5]*4)
    receiver['channels']['TreeCapture.Depth.Z']=array('f',[4,5,math.inf,4])
    layer['channels']['TreeCapture.Combined.A']=array('f',[.5,.25,1,1])
    pixels,report=build(*args)
    assert list(pixels)==[0,1,1,0]  # zero span excluded; mirrored infinity excluded
    assert report['known_pixels']==3 and report['unknown_covered_pixels']==1
    assert report['retained_alpha_mass']==1.25
    receiver['channels']['TreeCapture.Combined.A'][0]=math.nan
    with pytest.raises(ValueError,match='coverage'):build(*args)


@pytest.mark.parametrize('change', ['orientation','translation','span','window','size','clip','budget'])
def test_incompatible_pairs_refuse_without_resampling(change):
    args=list(fixture());receiver=args[3]
    if change=='orientation':receiver['matrix_world'][0][0]*=-1
    if change=='translation':receiver['matrix_world'][0][3]+=.1
    if change=='span':receiver['ortho_scale']=2.01
    if change=='window':args[1]['data_window']=(1,0,2,1)
    if change=='size':args[1]['width']=3
    if change=='clip':receiver['clip_end']=.05
    if change=='budget':args[0]['width']=args[0]['height']=1025
    with pytest.raises(ValueError):build(*args)


def test_cancellation_and_unchanged_input():
    args=fixture();before=deepcopy(args)
    class Cancel(Exception):pass
    def stop():raise Cancel()
    with pytest.raises(Cancel):build(*args,cancelled=stop)
    build(*args);assert args==before


def test_contracts_require_shadow_role_and_pin_receiver_and_threshold():
    for cls in (Source,Layer):
        args={'view':'BACK','render_role':'SHADOW_ONLY','shadow_mask':{'receiver_view':'FRONT'}}
        if cls==Source:args['directory']='capture'
        assert cls(**args).shadow_mask.minimum_span_m==0
        for patch in ({'render_role':'ALL_RAYS'},{'shadow_mask':{'receiver_view':'BACK'}}):
            with pytest.raises(ValueError):cls(**(args|patch))
    for value in (True,-1,math.nan,math.inf,1000001):
        with pytest.raises(ValueError):ShadowMask(receiver_view='FRONT',minimum_span_m=value)
        with pytest.raises(ValueError):depth_shadow.options(dict(receiver_view='FRONT',minimum_span_m=value))
