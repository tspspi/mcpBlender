"""Conservative UV broad phase against independent all-pairs exact clipping."""
import random
from mcpblender.uv_math import overlaps,triangle_overlap


def row(face,points):
    return (min(p[0] for p in points),max(p[0] for p in points),min(p[1] for p in points),max(p[1] for p in points),face,points)


def test_spatial_overlap_matches_all_pairs():
    rng=random.Random(412)
    for scale,offset in ((1,0),(.001,-20),(100,100)):
        triangles=[row(i,[(offset+scale*rng.random(),offset+scale*rng.random()) for _ in range(3)]) for i in range(60)]
        expected={tuple(sorted((a[4],b[4]))) for i,a in enumerate(triangles) for b in triangles[i+1:] if triangle_overlap(a[5],b[5])>1e-12}
        result=overlaps(triangles,100000)
        assert result['complete'] and result['face_pair_count']==len(expected)
        assert result['face_pairs']==[list(p) for p in sorted(expected)[:128]]
        assert result['pairs_truncated']==(len(expected)>128)


def test_separated_rows_avoid_false_budget_exhaustion():
    triangles=[row(i,[(0,i),(1,i),(0,i+.4)]) for i in range(1000)]
    result=overlaps(triangles,50000)
    assert result['complete'] and not result['face_pairs'] and result['comparisons']<50000
    assert overlaps([],0)['complete']
    identical=[row(i,[(0,0),(1,0),(0,1)]) for i in range(4)]
    result=overlaps(identical,2)
    assert not result['complete'] and result['comparisons']==2


def test_cross_bin_long_triangles_and_touching_edges():
    triangles=[row(0,[(0,-10),(1,-10),(0,10)]),row(1,[(0,-.5),(.5,-.5),(0,.5)]),row(2,[(1,0),(2,0),(1,1)])]
    result=overlaps(triangles,100)
    assert result['complete'] and result['face_pairs']==[[0,1]]
