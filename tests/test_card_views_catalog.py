"""Directional frames, fitting and horizon coverage without optical claims."""
import copy
import json
import math
import pytest
from mcpblender import card_fit,card_family,card_views,card_family_files
from mcpblender.card_contracts import Views
from mcpblender.card_family_contracts import Source
from test_card_family_files import bundle


def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def test_frames_are_orthonormal_and_fits_face_every_declared_direction():
    vertices=[(x,y,z) for x in (-2,3) for y in (-1,4) for z in (-3,2)]
    faces=[(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6),(0,4,6,2),(1,3,7,5)]
    triangles=[[vertices[i] for i in indices] for face in faces for indices in ((face[0],face[1],face[2]),(face[0],face[2],face[3]))]
    for view,n in card_views.DIRECTIONS.items():
        u,v=card_views.FRAMES[view]
        assert dot(u,u)==pytest.approx(1) and dot(v,v)==pytest.approx(1)
        assert dot(u,v)==pytest.approx(0) and cross(u,v)==pytest.approx(n)
        fitted=card_fit.fit(triangles,view=view,outline='RECTANGLE',padding=.02,resolution=32)
        points=fitted['vertices_m'];expected_plane=min(dot(p,n) for t in triangles for p in t)-.005
        assert [dot(p,n) for p in points]==pytest.approx([expected_plane]*len(points))
        assert dot(cross([points[1][a]-points[0][a] for a in range(3)],[points[2][a]-points[0][a] for a in range(3)]),n)>0
        assert fitted['uv']==[(0,0),(1,0),(1,1),(0,1)]
    assert Views(sources=['Cube'],views=list(card_views.DIRECTIONS),max_projected_triangles=2500000,max_total_card_triangles=2540)
    assert Source(directory='atlas',entries=[{'view':v,'object':v.lower()} for v in card_views.DIRECTIONS])


def test_eight_horizon_views_bound_nearest_angle_but_not_full_sphere():
    for degrees in range(3600):
        angle=math.radians(degrees/10);ray=(math.sin(angle),-math.cos(angle),0)
        report=card_family.choose(card_views.DIRECTIONS,[ray],30)
        assert report['supported']
        selected=next(r for r in report['candidates'] if r['view']==report['selected_view'])
        assert selected['centre_angle_degrees']<=22.5+1e-9
    assert card_family.choose(card_views.DIRECTIONS,[(0,0,-1)],30)['selected_view']=='BOTTOM'
    # Elevation between a pole and the horizontal ring is still unmeasured and
    # outside this declared 30-degree cone; no complete-sphere claim.
    assert not card_family.choose(card_views.DIRECTIONS,[(0,-1,1)],30)['supported']


def test_legacy_three_view_bundles_keep_original_tie_contract(tmp_path):
    saved=bundle(tmp_path);saved['format']=card_family_files.LEGACY_FORMAT
    saved['selector']['tie_order']=list(card_views.LEGACY)
    (tmp_path/'manifest.json').write_text(json.dumps(saved))
    assert card_family_files.validate(tmp_path)['format']==card_family_files.LEGACY_FORMAT
    bad=copy.deepcopy(saved);bad['selector']['tie_order']=list(card_views.DIRECTIONS)
    (tmp_path/'manifest.json').write_text(json.dumps(bad))
    with pytest.raises(ValueError,match='selector'):card_family_files.validate(tmp_path)
