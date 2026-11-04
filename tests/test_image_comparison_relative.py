"""Relative foreground luminance detects large errors on dark, sparse assets."""
import pytest
from mcpblender import image_comparison as api
from mcpblender.image_comparison_contracts import Quality
from test_image_comparison import png

KEY='max_abs_overlap_luminance_relative_bias'


def gray(value,alpha=65535):return png(1,1,[value,value,value,alpha],depth=16)


@pytest.mark.parametrize(('candidate','bias'),[(200,1.),(50,-.5),(400,3.)])
def test_dark_foreground_error_rejected_in_both_directions(candidate,bias):
    ref=gray(100);other=gray(candidate)
    default=api.compare(ref,other,color_space='LINEAR')
    assert default['passed'] and default['policy'][KEY] is None
    strict=api.compare(ref,other,color_space='LINEAR',policy={KEY:.1})
    assert not strict['passed']
    for row in strict['levels']:
        assert row['overlap_luminance_relative_bias']==pytest.approx(bias)
        assert row['abs_overlap_luminance_relative_bias']==pytest.approx(abs(bias))
        assert KEY in row['failures']


def test_relative_gate_is_not_diluted_by_background_and_keeps_alpha_separate():
    tight=api.compare(gray(100),gray(200),scales=[1],color_space='LINEAR')['levels'][0]
    ref=png(16,16,[100,100,100,65535]+[0,0,0,0]*255,depth=16)
    other=png(16,16,[200,200,200,65535]+[0,0,0,0]*255,depth=16)
    loose=api.compare(ref,other,scales=[1],color_space='LINEAR')['levels'][0]
    assert loose['abs_overlap_luminance_relative_bias']==tight['abs_overlap_luminance_relative_bias']==pytest.approx(1)
    same_color=api.compare(gray(100),gray(100,32768),scales=[1],color_space='LINEAR',policy={KEY:.001})['levels'][0]
    assert same_color['abs_overlap_luminance_relative_bias']==pytest.approx(0,abs=1e-7)
    assert KEY not in same_color['failures'] and same_color['soft_alpha_iou']<1


def test_black_reference_missing_overlap_and_disabled_or_large_thresholds():
    for ref,other in [(gray(0),gray(0)),(gray(0),gray(100)),(gray(100),gray(100,0))]:
        strict=api.compare(ref,other,scales=[1],policy={KEY:.1})
        assert strict['levels'][0]['abs_overlap_luminance_relative_bias'] is None
        assert KEY in strict['levels'][0]['failures']
    assert api.compare(gray(100),gray(200),policy={KEY:1.5})['passed']
    assert api.compare(gray(0),gray(0),policy={KEY:None})['passed']
    assert getattr(Quality(**{KEY:2}),KEY)==2
    for value in (-1,float('inf'),float('nan'),True):
        with pytest.raises(ValueError):api.compare(gray(100),gray(100),policy={KEY:value})


def test_opposite_local_errors_can_cancel_mean_bias_keep_rgb_gate_separate():
    ref=png(2,1,[1000,1000,1000,65535]*2,depth=16)
    other=png(2,1,[2000,2000,2000,65535,0,0,0,65535],depth=16)
    mean_only=api.compare(ref,other,scales=[1],color_space='LINEAR',policy={KEY:.1})
    assert mean_only['passed'] and mean_only['levels'][0]['abs_overlap_luminance_relative_bias']==pytest.approx(0)
    assert not api.compare(ref,other,scales=[1],color_space='LINEAR',policy={KEY:.1,'max_overlap_rgb_rmse':.005})['passed']
