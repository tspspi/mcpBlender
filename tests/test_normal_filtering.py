"""Coverage-conditioned normal-length diagnostics, with no shader/data correction."""
import copy
import math
import pytest
from mcpblender.capture_material_fields import normal_filtering


def geometry(alpha,normals):
    return {'channels':{'TreeCapture.Combined.A':alpha,**{'TreeCapture.Normal.'+a:[v[j] for v in normals] for j,a in enumerate('XYZ')}}}


def test_coverage_and_mixed_normals_are_distinguished_without_mutation():
    # Half-covered constant +Z and fully covered +/-60-degree facets both have
    # raw length .5. Their conditional lengths must be 1 and .5 respectively.
    source=geometry([.5,1,1,0],[(0,0,.5),(0,0,.5),(0,0,1),(0,0,0)]);weight=[.5,1,1,0];before=copy.deepcopy(source)
    result=normal_filtering(source,weight,.01)
    assert source==before and weight==[.5,1,1,0]
    assert result['covered_pixels']==3 and result['conditional_length_over_one']==0
    assert result['groups']['partial']['conditional_length']['mean']==1
    assert result['groups']['opaque']['conditional_length']['mean']==.75
    assert result['groups']['covered']['raw_length']['mean']==pytest.approx(2/3)
    assert result['groups']['covered']['conditional_length']['rms']==pytest.approx(math.sqrt(.75))


def test_unavailable_invalid_and_out_of_bound_observations_are_not_clamped():
    source=geometry([1]*7+[float('nan')],[(0,0,1),(0,0,1),(0,0,1),(0,0,float('inf')),(0,0,0),(0,0,1.2),(0,0,1),(0,0,1)])
    result=normal_filtering(source,[0,-1,float('nan'),1,1,1,2,1],.01)
    assert result['missing_surface_weight']==1 and result['invalid_surface_weight']==3
    assert result['invalid_alpha']==1 and result['nonfinite_normals']==1
    assert result['zero_conditional_normals']==1 and result['conditional_length_over_one']==1
    assert result['groups']['covered']['conditional_length']['max']==1.2
    assert result['groups']['partial']['conditional_length']['mean'] is None
    with pytest.raises(ValueError,match='lengths'):normal_filtering(source,[1],.01)
    def cancel():raise InterruptedError('cancel')
    with pytest.raises(InterruptedError):normal_filtering(source,[1]*8,.01,cancelled=cancel)
