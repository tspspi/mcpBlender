"""Physical triangle metrics use linear transforms before global placement."""
import math
import pytest
from mcpblender.uv_math import affine_triangle_edges,triangle_edge_area
from mcpblender.uv_quality import directional_density


def test_edge_first_affine_shape_units_and_reflection():
    triangle=[(2**28,2**28,0),(2**28+2,2**28,0),(2**28,2**28+1,0)]
    a,b=affine_triangle_edges(triangle,[(-2,1,0),(0,.5,0),(0,0,1)],.01)
    assert a==pytest.approx([-.04,0,0]) and b==pytest.approx([.01,.005,0])
    assert triangle_edge_area(a,b)==pytest.approx(.0001)
    assert triangle==[(2**28,2**28,0),(2**28+2,2**28,0),(2**28,2**28+1,0)]
    edges=affine_triangle_edges([(0,0,0),(2,0,0),(0,2,0)],[(1,1,0),(0,1,0),(0,0,1)])
    low,high=directional_density([(0,0,0),*edges],[(0,0),(128,0),(0,128)])
    assert (low,high)==pytest.approx((64*(math.sqrt(5)-1)/2,64*(math.sqrt(5)+1)/2))


def test_edge_metric_degeneracy_and_nonfinite_refusal():
    assert triangle_edge_area(*affine_triangle_edges([(0,0,0),(1,0,0),(2,0,0)],[(1,0,0),(0,1,0),(0,0,1)]))==0
    with pytest.raises(ValueError,match='Finite'):affine_triangle_edges([(0,0,0),(1,0,0),(0,1,0)],[(float('inf'),0,0),(0,1,0),(0,0,1)])
    with pytest.raises(ValueError,match='Finite'):triangle_edge_area([1e308,0,0],[0,1e308,0])
