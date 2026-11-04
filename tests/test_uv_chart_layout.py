"""Chart rectangle allocation, aspect preservation and explicit stretch floors."""
import copy
import math
import pytest
from mcpblender.uv_chart_layout import pack
from mcpblender.uv_layout_contracts import ChartLayout
from mcpblender.uv_contracts import UVPack
from mcpblender.vegetation_bake_contracts import Source
from mcpblender.uv_math import signed_area


def chart(x,y,w,h):
    return {'points':[(x,y),(x+w,y),(x+w,y+h),(x,y+h)],'area':w*h}


def test_pixel_gutters_floors_float32_and_determinism():
    charts=[chart(0,0,.7,.7),chart(.8,.1,.0001,.01),chart(2,3,.001,.001)]
    before=copy.deepcopy(charts);policy=ChartLayout(allow_stretch=True).model_dump()
    points,report=pack(charts,128,128,8,policy)
    assert pack(charts,128,128,8,policy)==(points,report) and charts==before
    assert report['stretched_charts']>0 and report['minimum_allocated_area_pixels']>=64-1e-6
    assert report['minimum_mean_span_pixels']>=2-1e-6
    assert report['search_attempts']<=25
    boxes=[]
    for polygon in points:
        assert abs(signed_area(polygon))*128**2>=64-1e-3
        low=[min(p[a] for p in polygon)*128 for a in (0,1)];high=[max(p[a] for p in polygon)*128 for a in (0,1)]
        assert min(low)>=8 and max(high)<=120
        boxes.append((low,high))
    for i,(lo,hi) in enumerate(boxes):
        for other_lo,other_hi in boxes[:i]:
            assert any(hi[a]+8<=other_lo[a]+1e-5 or other_hi[a]+8<=lo[a]+1e-5 for a in (0,1))


def test_no_stretch_preserves_uv_pixel_aspect_and_refuses_impossible_sliver():
    original=chart(0,0,.2,.1)
    c,s=math.cos(.7),math.sin(.7)
    original['points']=[(x*c-y*s,x*s+y*c) for x,y in original['points']]
    points,report=pack([original],128,128,0,ChartLayout().model_dump())
    def lengths(p):return [math.dist(a,b) for a,b in zip(p,p[1:]+p[:1])]
    ratios=[a/b for a,b in zip(lengths(points[0]),lengths(original['points']))]
    assert max(ratios)==pytest.approx(min(ratios),rel=1e-5) and report['stretched_charts']==0
    thin=[chart(0,0,1,1e-7)]
    with pytest.raises(ValueError,match='Minimum chart'):pack(thin,128,128,0,ChartLayout().model_dump())
    assert pack(thin,128,128,0,ChartLayout(allow_stretch=True).model_dump())[1]['stretched_charts']==1


def test_bounds_cancellation_and_explicit_contracts():
    policy=ChartLayout(max_charts=1).model_dump()
    with pytest.raises(ValueError,match='max_charts'):pack([chart(0,0,.1,.1)]*2,64,64,0,policy)
    with pytest.raises(ValueError,match='Minimum chart'):pack([chart(0,0,.1,.1)],32,32,8,policy|{'min_area_pixels':1024})
    def cancel():raise InterruptedError('cancel')
    with pytest.raises(InterruptedError):pack([chart(0,0,.1,.1)],64,64,0,policy,checkpoint=cancel)
    with pytest.raises(ValueError,match='NEW'):Source(collection='Tree',uv_strategy='EXISTING',chart_layout=ChartLayout())
    with pytest.raises(ValueError,match='scale=true'):UVPack(name='Object',expected_uv='a'*64,scale=False,chart_layout=ChartLayout())
