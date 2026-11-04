"""Independent plane, orientation, volume and containment checks of small hulls."""
import math
import random
import pytest
from mcpblender.collision_hulls import hull,subtract,cross,dot


def verify(points):
    result=hull(points);v=result['vertices'];tol=result['containment_tolerance_local_m']
    for face in result['faces']:
        a,b,c=[v[i] for i in face];n=cross(subtract(b,a),subtract(c,a));size=math.sqrt(dot(n,n))
        assert size>0 and all(dot(subtract(p,a),n)/size<=tol for p in points)
    assert result['volume_local_m3']>0
    return result


def test_closed_hulls_tapered_and_near_coplanar_sleeves():
    box=[(x,y,z) for x in (-1.,1.) for y in (-1.,1.) for z in (-1.,1.)]
    assert verify(box)['volume_local_m3']==pytest.approx(8)
    assert hull(box)==hull(list(reversed(box)))
    assert verify([tuple(v+1e8 for v in p) for p in box])['volume_local_m3']==pytest.approx(8)
    for seed in range(12):
        rng=random.Random(seed)
        points=[(r*math.cos(2*math.pi*j/16)+z*.03,r*math.sin(2*math.pi*j/16),z+1e-6*rng.uniform(-1,1)) for z,r in ((0.,.36),(1.,.32)) for j in range(16)]
        verify(points)
    sphere=[]
    rng=random.Random(1)
    for i in range(32):
        p=[rng.gauss(0,1) for _ in range(3)];size=math.sqrt(dot(p,p));sphere.append(tuple(v/size for v in p))
    verify(sphere)
    for points in (box*5,[(0,0,0)]*4,[(i,i,i) for i in range(4)],[(0,0,0),(1,0,0),(0,1,0),(1,1,0)]):
        with pytest.raises(ValueError):hull(points)
