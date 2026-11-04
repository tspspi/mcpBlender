"""Analytic directions, scalar coverage, missing evidence and bounded admission."""
import pytest
from mcpblender.normal_transfer import inspect
from test_image_comparison import png


def test_directions_ignore_file_alpha_and_use_red_coverage():
    normals=png(5,1,[128,128,255,0,128,128,0,0,255,128,128,0,0,128,127,0,128,128,128,0])
    mask=png(5,1,[255,0,0,0]*4+[0,255,255,255])
    result=inspect(normals,mask)
    assert result['covered_pixels']==result['valid_direction_pixels']==4
    assert result['backward_pixels']==1 and result['backward_fraction']==.25
    assert result['grazing_pixels']==2 and result['grazing_fraction']==.5
    assert result['invalid_direction_pixels']==0
    assert 'passed' not in result


def test_empty_and_undefined_direction_are_unmeasured():
    normal=png(1,1,[128,128,128,255]);mask=png(1,1,[255]*4)
    result=inspect(normal,mask)
    assert result['invalid_direction_pixels']==result['covered_pixels']==1
    assert result['backward_fraction'] is None and result['mean_tangent_z'] is None
    empty=inspect(normal,png(1,1,[0,255,255,255]))
    assert empty['covered_pixels']==0 and empty['grazing_fraction'] is None
    with pytest.raises(ValueError,match='dimensions'):inspect(normal,png(2,1,[255]*8))
    with pytest.raises(ValueError):inspect(b'bad',mask)
    def cancel():raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError,match='cancelled'):inspect(normal,mask,cancelled=cancel)


def test_png16_and_unit_length_are_separate_from_direction():
    image=png(1,1,[65535,65535,65535,65535],depth=16)
    report=inspect(image,image)
    assert report['mean_tangent_z']==pytest.approx(1/3**.5)
    assert report['mean_unit_length_error']==pytest.approx(3**.5-1)
