"""Necessary direction-cap certificates, independent supported mixtures and errors."""
import copy
import json
import math
import random
import struct
import pytest
from mcpblender import normal_support,normal_quadrature


def point(z):
    return normal_quadrature.moments([{'weight':1,'direction':(math.sqrt(1-z*z),0,z)}])


def test_slope16_counterexample_and_nonautomatic_higher_cap_bounds():
    q=[.4568586978647444,-.662599629826016,.49646941551731694,
       .26989010431700283,-.27528590460618335,.26335749625124866,
       .45193968878852,-.3105718642473221,.2781702726173939]
    original=copy.deepcopy(q);result=normal_support.check(q,16)
    assert result['verdict']=='RULED_OUT' and q==original
    row=next(r for r in result['constraints'] if r['constraint']=='WEIGHTED_DIRECTION_NORM')
    assert row['slack']==pytest.approx(-.000371369645)
    assert row['error_bound']<.000035 and row['slack'] < -row['error_bound']
    assert result['next_not_ruled_out_max_slope']==32
    assert normal_support.check(q,32)['verdict']=='NOT_RULED_OUT'
    error=normal_support.DirectionCapError([1,2,3,4],result)
    assert error.diagnostic is result and error.pixel_rect==[1,2,3,4]
    payload=json.loads(str(error).split(': ',1)[1]);assert payload['direction_cap']==result


@pytest.mark.parametrize('quantized',[False,True])
def test_never_rules_out_independent_supported_mixtures(quantized):
    rng=random.Random(3881)
    for slope in (.01,.1,1,16,32,64):
        c=1/math.hypot(1,slope)
        for count in (1,2,4,32):
            points=[]
            for _ in range(count):
                z=rng.uniform(c,1);angle=rng.uniform(0,2*math.pi);r=math.sqrt(1-z*z)
                points.append((r*math.cos(angle),r*math.sin(angle),z))
            q=[sum(n[j] for n in points)/count for j in range(3)]
            q += [sum(n[i]*n[j] for n in points)/count for i,j in ((0,0),(0,1),(0,2),(1,1),(1,2),(2,2))]
            if quantized:q=[struct.unpack('<f',struct.pack('<f',v))[0] for v in q]
            assert normal_support.check(q,slope)['verdict']=='NOT_RULED_OUT'


def test_roundoff_margin_and_unsupported_backward_distribution():
    c=1/math.hypot(1,16)
    assert normal_support.check(point(c-1e-7),16)['verdict']=='NOT_RULED_OUT'
    assert normal_support.check(point(c-.001),16)['verdict']=='RULED_OUT'
    result=normal_support.check(point(-1),64)
    assert result['verdict']=='RULED_OUT' and result['next_not_ruled_out_max_slope'] is None


@pytest.mark.parametrize('patch',[dict(max_slope=65),dict(max_slope=True),dict(max_slope=0),
    dict(fit_tolerance=False),dict(fit_tolerance=float('nan')),dict(omission_tolerance=.1)])
def test_invalid_bounds(patch):
    with pytest.raises(ValueError):normal_support.check(point(1),**({'max_slope':16}|patch))


@pytest.mark.parametrize('q',[[0]*8,[0]*9,[float('inf')]*9,[True]*9])
def test_invalid_moment_inputs(q):
    with pytest.raises(ValueError):normal_support.check(q,16)
