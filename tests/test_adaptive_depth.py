"""Independent orientation, deterministic refinement, projected coverage and limits."""
from array import array
import math
import pytest
from mcpblender import depth_tiles
from test_depth_tiles import fixture


def normals(data,values):
    for j,axis in enumerate('XYZ'):data['channels']['TreeCapture.Normal.'+axis]=array('f',[v[j] for v in values])


def test_constant_tilt_matches_plane_and_does_not_spend_refinement_budget():
    d,m,v=fixture();normals(d,[(.6,0,.6)]*4);d['channels']['TreeCapture.Depth.Z']=array('f',[4.5,5.5,4.5,5.5])
    g=depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':2,'max_triangles':2,'max_refinement_work':8})
    assert list(g['vertices'])==pytest.approx([-1,-1,1,1,-1,-1,1,1,-1,-1,1,1])
    assert list(g['uvs'])==[0,0,1,0,1,1,0,1]
    assert g['report']['refinement_splits']==0 and g['report']['refinement_work']==8
    assert g['report']['equivalent_normal_error_degrees']<.1
    assert g['patch_records'][0]['slope_camera']==pytest.approx([1,0])
    assert d['channels']['TreeCapture.Normal.X'][0]==pytest.approx(.6)


def varying(size=4):
    d,m,v=fixture();d.update(width=size,height=size,data_window=(0,0,size-1,size-1))
    d['channels']['TreeCapture.Combined.A']=array('f',[1.]*(size*size));d['channels']['TreeCapture.Depth.Z']=array('f',[5.]*(size*size))
    normals(d,[(1 if x<size//2 else -1,0,1) for y in range(size) for x in range(size)])
    return d,m,v


def test_budgeted_refinement_is_deterministic_and_reports_unmet_tolerance():
    d,m,v=varying();p={'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':4,'normal_tolerance_degrees':10,'max_triangles':8}
    refined=depth_tiles.geometry(d,m,v,p);r=refined['report']
    assert r['triangles']==8 and r['refinement_splits']==1 and r['normal_tolerance_unmet_cells']==0
    assert r['initial_equivalent_normal_error_degrees']==pytest.approx(45,abs=.01)
    assert r['equivalent_normal_error_degrees']<.1 and r['represented_input_alpha_mass']==16
    assert depth_tiles.geometry(d,m,v,p)['report']['geometry_sha256']==r['geometry_sha256']
    blocked=depth_tiles.geometry(d,m,v,p|{'max_triangles':6})['report']
    assert blocked['triangles']==2 and blocked['budget_blocked_candidates']==1 and blocked['normal_tolerance_unmet_cells']==1
    assert blocked['equivalent_normal_error_degrees']>40
    # Every active input pixel lies in exactly one output rectangle.
    for y in range(4):
        for x in range(4):assert sum(a<=x<c and b<=y<e for a,b,c,e in (row['pixel_rect'] for row in refined['patch_records']))==1


def test_clipped_edge_rectangles_keep_projected_bounds_and_disconnected_vertices():
    d,m,v=varying(5);g=depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':4,'max_triangles':64})
    assert all(0<=a<c<=5 and 0<=b<e<=5 for a,b,c,e in (row['pixel_rect'] for row in g['patch_records']))
    assert len(g['vertices'])==len(g['faces'])*12
    for y in range(5):
        for x in range(5):assert sum(a<=x<c and b<=y<e for a,b,c,e in (row['pixel_rect'] for row in g['patch_records']))==1
    # Rotated/scaled/translated camera/root preserve canonical local geometry.
    original=g['vertices'];m['source_root_matrix_world']=[[0,0,2,4],[0,2,0,-3],[-2,0,0,1],[0,0,0,1]]
    v.update(matrix_world=[[0,0,1,14],[0,1,0,-3],[-1,0,0,1],[0,0,0,1]],ortho_scale=4,clip_end=30)
    d['channels']['TreeCapture.Depth.Z']=array('f',[10.]*25)
    old=[tuple(d['channels']['TreeCapture.Normal.'+axis][i] for axis in 'XYZ') for i in range(25)]
    normals(d,[(z,y,-x) for x,y,z in old])
    rotated=depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':4,'max_triangles':64})
    assert list(rotated['vertices'])==pytest.approx(list(original),abs=1e-5)


def test_clip_slope_backward_and_invalid_normal_policies():
    d,m,v=fixture();normals(d,[(1,0,1)]*4)
    g=depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':2,'max_slope':.5})
    assert g['report']['slope_limited_cells']==1 and g['patch_records'][0]['slope_camera']==[.5,0]
    v.update(clip_start=4.95,clip_end=5.05)
    g=depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':2})
    assert g['report']['clip_limited_cells']==1
    assert all(4.95<=5-z<=5.05 for z in g['vertices'][2::3])
    d,m,v=fixture();normals(d,[(0,0,-1)]*4)
    g=depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':2})
    assert g['report']['backward_normal_pixels']==4 and g['report']['unoriented_cells']==1
    assert g['patch_records'][0]['slope_camera']==[0,0] # No guessed normal flip.
    normals(d,[(0,0,0)]*4)
    with pytest.raises(ValueError,match='native normal'):depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL'})


def test_work_limits_cancellation_and_unchanged_flat_buffers():
    d,m,v=fixture();flat=depth_tiles.geometry(d,m,v,{'tile_pixels':2})
    assert list(flat['vertices'])==[-1,-1,0,1,-1,0,1,1,0,-1,1,0]
    with pytest.raises(ValueError,match='refinement work budget'):depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','max_refinement_work':1})
    def stop():raise InterruptedError('cancel')
    with pytest.raises(InterruptedError):depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL'},cancelled=stop)
    for patch in ({'geometry_mode':'GUESS'},{'max_slope':True},{'normal_tolerance_degrees':float('inf')},{'max_refinement_work':True}):
        with pytest.raises(ValueError):depth_tiles.geometry(d,m,v,patch)


def test_normal_tilting_does_not_grow_source_bounds_or_existing_overshoot():
    d,m,v=fixture();normals(d,[(1,0,1)]*4)
    m['bounds_root_local_m']={'min':[-1,-1,-.2],'max':[1,1,.2]}
    g=depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':2})
    assert g['report']['source_bounds_limited_cells']==1
    assert min(g['vertices'][2::3])>=-.200001 and max(g['vertices'][2::3])<=.200001
    assert max(abs(z) for z in g['vertices'][2::3])==pytest.approx(.2)
    # A pre-existing projected corner outside the box can stay there, but tilt
    # cannot expand that overshoot; no source pivot/bounds are silently moved.
    m['bounds_root_local_m']['min'][2]=.1
    g=depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':2})
    assert list(g['vertices'][2::3])==[0,0,0,0]


def test_nearest_ring_witness_matches_independent_exhaustive_oracle():
    import random
    rng=random.Random(119);w=h=13;valid={i for i in range(w*h) if rng.random()<.2}
    for _ in range(120):
        cx=rng.randrange(25)/2;cy=rng.randrange(25)/2;radius=rng.randrange(7);visits=[]
        expected=min((((x-cx)**2+(y-cy)**2,y*w+x) for y in range(h) for x in range(w) if y*w+x in valid and (x-cx)**2+(y-cy)**2<=radius*radius),default=None)
        actual=depth_tiles.nearest_depth_pixel(cx,cy,radius,w,h,lambda i:i in valid,lambda:visits.append(1),lambda:None)
        assert actual==expected and len(visits)<=w*h


def test_initial_triangle_budget_stops_before_excessive_cell_allocation():
    d,m,v=varying()
    # Sixteen normal reads and two initial cell fits are enough to prove that
    # the requested one-patch budget cannot cover this base grid.
    with pytest.raises(ValueError,match='triangle budget'):
        depth_tiles.geometry(d,m,v,{'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':1,'max_triangles':2,'max_refinement_work':18})
