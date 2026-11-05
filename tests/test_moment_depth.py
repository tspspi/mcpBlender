"""Witness anchoring, root-local precision, refusal and input moment weighting."""
from array import array
import copy
import math
import random
import pytest
from mcpblender import depth_tiles, normal_moments, normal_quadrature, moment_depth
from test_depth_tiles import fixture


def source(atoms=None):
    decoded, meta, view = fixture()
    meta['material_fields'] = {'normal_moments': {'format': normal_moments.FORMAT}}
    values = normal_quadrature.moments(atoms or [{'weight': .5, 'direction': (.6, 0, .8)}, {'weight': .5, 'direction': (-.6, 0, .8)}])
    decoded['channels']['TreeCapture.MCP_SurfaceWeight.X'] = array('f', [.5]*4)
    for name, value in zip(normal_moments.channels(), values):
        decoded['channels'][name] = array('f', [value*.5]*4)
    return decoded, meta, view


def build(d, m, v, **settings):
    return depth_tiles.geometry(d, m, v, {'geometry_mode': 'MOMENT_FACETS', 'tile_pixels': 2, **settings})


def test_moment_facets_winding_weighting_witness_and_reproducibility():
    d, m, v = source()
    before = copy.deepcopy(d)
    g = build(d, m, v)
    assert d == before and g == build(d, m, v)
    assert 2 <= g['report']['triangles'] <= 8
    assert g['report']['moment_tiles'] == 1 and g['report']['measured_tiles'] == 1
    assert g['report']['max_component_residual'] < 1e-5
    assert len(g['patch_records']) == 1
    record = g['patch_records'][0]
    assert record['witness_pixel'] == [0, 1] and record['plane_anchor_pixel'] == [.5, 1.5]
    assert record['normal_input_weight'] == 2
    # Each plane, including a strip away from the witness, passes through its
    # measured witness coordinate (-.5,-.5,0), rather than a guessed tile centre.
    for face in g['faces']:
        a, b, _, e = [g['vertices'][3*i:3*i+3] for i in face]
        sx, sy = (b[2]-a[2])/(b[0]-a[0]), (e[2]-a[2])/(e[1]-a[1])
        assert a[2]+sx*(-.5-a[0])+sy*(-.5-a[1]) == pytest.approx(0, abs=2e-6)
    assert min(g['uvs']) >= 0 and max(g['uvs']) <= 1


def test_world_input_moments_and_rotated_scaled_source_frame():
    d, m, v = source([{'weight': 1, 'direction': (0, 0, 1)}])
    expected = build(d, m, v)
    m['source_root_matrix_world'] = [[0, 0, 2, 4], [0, 2, 0, -3], [-2, 0, 0, 1], [0, 0, 0, 1]]
    v.update(matrix_world=[[0, 0, 1, 14], [0, 1, 0, -3], [-1, 0, 0, 1], [0, 0, 0, 1]], ortho_scale=4, clip_end=30)
    d['channels']['TreeCapture.Depth.Z'] = array('f', [10]*4)
    values = normal_quadrature.moments([{'weight': 1, 'direction': (1, 0, 0)}])
    for name, value in zip(normal_moments.channels(), values):
        d['channels'][name] = array('f', [value*.5]*4)
    assert build(d, m, v)['vertices'] == expected['vertices']
    assert moment_depth.rotate(values, [[0,0,-1],[0,1,0],[1,0,0]]) == [0,0,1,0,0,0,0,0,1]


def test_per_pixel_invalidity_cannot_cancel_in_tile_average():
    d, m, v = source()
    key = normal_moments.channels()[0]
    d['channels'][key] = array('f', [.5, -.5, .5, -.5])
    with pytest.raises(ValueError, match='per-pixel'):
        build(d, m, v)


def test_missing_moments_work_triangles_depth_and_support_refused():
    d, m, v = source()
    for options, match in (({'max_refinement_work': 1}, 'work budget'), ({'max_triangles': 2}, '[Tt]riangle budget')):
        with pytest.raises(ValueError, match=match):
            build(d, m, v, **options)
    m['material_fields'] = {}
    with pytest.raises(ValueError, match='recapture'):
        build(d, m, v)
    d, m, v = source([{'weight': 1, 'direction': (0,0,-1)}])
    with pytest.raises(ValueError, match='Unsupported normal mass'):
        build(d, m, v)
    d, m, v = source()
    v.update(clip_start=4.99, clip_end=5.01)
    with pytest.raises(ValueError, match='near/far'):
        build(d, m, v)


def test_sub_float32_precision_and_cancellation_refused():
    d, m, v = source()
    m['source_root_matrix_world'][0][3] = 1e8
    with pytest.raises(ValueError, match='float32'):
        build(d, m, v)
    def cancelled():
        raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError, match='cancelled'):
        depth_tiles.geometry(d, m, v, {'geometry_mode': 'MOMENT_FACETS'}, cancelled=cancelled)


def test_surface_weights_define_distribution_not_unweighted_average():
    d, m, v = source([{'weight': 1, 'direction': (0, 0, 1)}])
    weights = [1, .5, .25, .125]
    values = [normal_quadrature.moments([{'weight': 1, 'direction': (sx*.6, 0, .8)}]) for sx in (1, -1, -1, -1)]
    d['channels']['TreeCapture.MCP_SurfaceWeight.X'] = array('f', weights)
    for j, name in enumerate(normal_moments.channels()):
        d['channels'][name] = array('f', [weight*q[j] for weight,q in zip(weights,values)])
    g = build(d, m, v)
    assert g['patch_records'][0]['normal_moments_camera'][0] == pytest.approx(.6*(1-.875)/1.875)


def supported_distribution():
    rng=random.Random(412);atoms=[]
    for _ in range(12):
        z=rng.uniform(.2,.95);phi=rng.uniform(0,2*math.pi);r=math.sqrt(1-z*z)
        atoms.append({'weight':1/12,'direction':(r*math.cos(phi),r*math.sin(phi),z)})
    return atoms


def test_supported_alternative_preserves_moments_and_reports_search():
    d,m,v=source(supported_distribution());v['clip_end']=100
    d['channels']['TreeCapture.Depth.Z']=array('f',[50]*4);v['matrix_world'][2][3]=50
    with pytest.raises(ValueError,match='candidate budget exhausted'):
        build(d,m,v,max_moment_candidates=1)
    with pytest.raises(ValueError,match='work budget'):
        build(d,m,v,max_moment_candidates=64,max_refinement_work=272)
    g=build(d,m,v,max_moment_candidates=64)
    assert g['report']['candidate_attempts']>1
    assert g['report']['rejected_candidates']['Unsupported normal mass exceeds omission bound']>=1
    assert g['report']['max_component_residual']<=1e-5
    assert g['report']==build(d,m,v,max_moment_candidates=64)['report']
    assert all(r['candidate_attempts']<=64 for r in g['patch_records'])


def test_approximate_rotation_uses_actual_inverse_for_subpixel_readback():
    from mcpblender import projected_microfacets
    eps=1/262144
    piece=projected_microfacets.build((-1,-1,1,1),[{'weight':1,'direction':(0,0,1)}],depth=5,near=.1,far=10)
    identity=[[1,0,0],[0,1,0],[0,0,1]]
    frame=([0,0,5],[[1,0,0],[eps,1,0],[0,0,1]],[0,0,0],identity,[1,1,1],2/512,2,.1,10)
    vertices,_,residual,area_error=moment_depth.native_piece(piece,[0,0,1,0,0,0,0,0,1],frame)
    assert vertices[0]==-1-eps and residual==area_error==0
