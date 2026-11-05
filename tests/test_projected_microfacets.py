"""Geometric readback and refusal boundaries for projected normal mixtures."""
import copy
import math
import struct

import pytest

from mcpblender import projected_microfacets as facets


def build(atoms, **kwargs):
    options = dict(depth=5., near=.1, far=10.)
    options.update(kwargs)
    return facets.build((-1., -1., 1., 1.), atoms, **options)


def test_projected_coverage_and_independent_geometric_readback():
    atoms = [{'weight': .25, 'direction': (.6, 0., .8)},
             {'weight': .75, 'direction': (0., -.6, .8)}]
    before = copy.deepcopy(atoms)
    result = build(atoms)
    assert atoms == before and result == build(atoms)
    assert result['triangle_count'] == 4 and result['omitted_mass'] == 0
    vertices = result['vertices']
    assert vertices[1][0] == vertices[4][0] == -.5
    assert vertices[0][:2] == (-1., -1.) and vertices[6][:2] == (1., 1.)
    for face, expected in zip(result['faces'], atoms):
        a, b, _, d = [vertices[i] for i in face]
        dx, dy = b[0]-a[0], d[1]-a[1]
        slope_x, slope_y = -(b[2]-a[2])/dx, -(d[2]-a[2])/dy
        length = math.hypot(slope_x, slope_y, 1)
        assert [slope_x/length, slope_y/length, 1/length] == pytest.approx(expected['direction'])
        assert dx*dy/4 == pytest.approx(expected['weight'])
    assert result['max_component_residual'] < 1e-6
    assert result['depth_bounds'] == [4.25, 5.75]
    for vertex in vertices:
        assert tuple(struct.unpack('<3f', struct.pack('<3f', *vertex))) == vertex
    assert all(0 <= u <= 1 and 0 <= v <= 1 for u, v in result['uvs'])


def test_backward_roundoff_mass_is_explicit_and_bounded():
    atoms = [{'weight': 1-1e-8, 'direction': (0, 0, 1)},
             {'weight': 1e-8, 'direction': (0, 0, -1)}]
    result = build(atoms)
    assert result['omitted_mass'] == 1e-8
    assert result['retained_mass'] == 1-1e-8
    assert result['max_component_residual'] == pytest.approx(2e-8)
    with pytest.raises(ValueError, match='omission'):
        build(atoms, omitted_mass_tolerance=0)
    with pytest.raises(ValueError, match='residual'):
        build(atoms, residual_tolerance=1e-8)


@pytest.mark.parametrize('direction', [(0, 0, -1), (1, 0, 0), (.9998, 0, math.sqrt(1-.9998**2))])
def test_significant_unrepresentable_mass_refused(direction):
    with pytest.raises(ValueError, match='omission'):
        build([{'weight': 1, 'direction': direction}])


def test_clipping_budget_and_float32_loss_refused():
    flat = [{'weight': 1, 'direction': (0, 0, 1)}]
    steep = [{'weight': 1, 'direction': (.8, 0, .6)}]
    with pytest.raises(ValueError, match='near/far'):
        build(steep, near=4.9, far=5.1)
    with pytest.raises(ValueError, match='budget'):
        build([{'weight': .5, 'direction': (0, 0, 1)}]*2, triangle_budget=2)
    with pytest.raises(ValueError, match='collapse'):
        facets.build((1e8, 0, 1e8+1, 1), flat, depth=5, near=1, far=10)
    with pytest.raises(ValueError, match='residual'):
        build(steep, depth=1e8, near=1, far=2e8)
    with pytest.raises(ValueError, match='float32 range'):
        build(flat, depth=1e40, near=1, far=1e41)
    for rect in ((-1e300, -1e300, 1e300, 1e300), (0, 0, 1e-300, 1e-300)):
        with pytest.raises(ValueError, match='numerical range'):
            facets.build(rect, flat, depth=5, near=1, far=10)


@pytest.mark.parametrize('override', [dict(depth=float('nan')), dict(near=0),
    dict(far=4), dict(max_slope=17), dict(max_slope=True), dict(triangle_budget=True),
    dict(omitted_mass_tolerance=.1), dict(residual_tolerance=0)])
def test_invalid_options(override):
    with pytest.raises(ValueError):
        build([{'weight': 1, 'direction': (0, 0, 1)}], **override)


@pytest.mark.parametrize('atoms', [[], [{'weight': 1, 'direction': (0, 0, 2)}],
    [{'weight': .5, 'direction': (0, 0, 1)}],
    [{'weight': float('nan'), 'direction': (0, 0, 1)}]])
def test_invalid_inputs(atoms):
    with pytest.raises(ValueError):
        build(atoms)


def test_cancellation_propagates_without_partial_output():
    calls = 0
    def cancelled():
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError, match='cancelled'):
        build([{'weight': 1, 'direction': (0, 0, 1)}], cancelled=cancelled)
