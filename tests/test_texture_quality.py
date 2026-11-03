"""Analytic texture footprints and conservative bounded failure gates."""
import asyncio
import math
import random

import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.texture_contracts import BakeTextures
from mcpblender.texture_quality_contracts import Quality
from mcpblender.uv_quality import analyze,directional_density,raster,segment_distance,spacing


def square(lo=0,hi=1,island=0):
    corners=[(lo,lo),(hi,lo),(hi,hi),(lo,hi)]
    triangles=[{'island':island,'uv':[corners[i] for i in indices],
                'world_m':[(corners[i][0],corners[i][1],0) for i in indices]} for indices in ((0,1,2),(0,2,3))]
    return triangles,[(island,a,b) for a,b in zip(corners,corners[1:]+corners[:1])]


def test_directional_density_including_anisotropy():
    world=[(0,0,0),(2,0,0),(0,1,0)]
    assert directional_density(world,[(0,0),(64,0),(0,64)])==pytest.approx((32,64))
    # Equal area density can conceal arbitrarily bad directional sampling.
    assert directional_density(world,[(0,0),(1,0),(0,4096)])==pytest.approx((.5,4096))
    c,s=math.cos(.7),math.sin(.7)
    rotated=[(x*c-y*s,x*s+y*c,z+9) for x,y,z in world]
    assert directional_density(rotated,[(0,0),(64,0),(0,64)])==pytest.approx((32,64))


def test_raster_shared_diagonal_and_subpixel_chart():
    triangles,_=square()
    for reverse in (False,True):
        sample=[t|{'uv':list(reversed(t['uv'])) if reverse else t['uv']} for t in triangles]
        report=raster(sample,32,32,1,2048,lambda:None)
        assert report['complete'] and report['covered_pixels']==[1024] and report['ambiguous_pixels']==0
    tiny,_=square(.001,.002)
    assert raster(tiny,32,32,1,100,lambda:None)['covered_pixels']==[0]
    assert not raster(triangles,32,32,1,1,lambda:None)['complete']


def test_segment_distances_and_broadphase_against_all_pairs():
    assert segment_distance((0,0),(2,0),(1,-1),(1,1))==0
    assert segment_distance((0,0),(1,0),(2,0),(3,0))==1
    assert segment_distance((0,0),(0,0),(1,1),(1,1))==pytest.approx(math.sqrt(2))
    rng=random.Random(18)
    edges=[(i%5,(rng.uniform(-10,10),rng.uniform(-10,10)),(rng.uniform(-10,10),rng.uniform(-10,10))) for i in range(80)]
    expected={}
    for i,(a,p,q) in enumerate(edges):
        for b,r,s in edges[:i]:
            if a==b:continue
            gap=segment_distance(p,q,r,s)
            if gap<.3:
                pair=tuple(sorted((a,b)));expected[pair]=min(expected.get(pair,math.inf),gap)
    report=spacing(edges,.3,10000,lambda:None)
    assert report['complete']
    assert {tuple(r['islands']):r['gap_pixels'] for r in report['violations']}==pytest.approx(expected)
    assert not spacing(edges,.3,1,lambda:None)['complete']
    assert not spacing([(0,(0,0),(1,1))]*10,1,1,lambda:None)['complete']


def test_quality_thresholds_mips_overlap_and_work_budgets():
    triangles,edges=square(.125,.875)
    policy=Quality(width=32,height=32,min_texels_per_meter=32,padding_pixels=2,mip_levels=1).model_dump()
    report=analyze(triangles,edges,1,policy)
    assert report['passed'] and report['minimum_directional_texels_per_meter']==32
    assert [r['edge_margin_pixels'] for r in report['levels']]==[4,2]
    assert not analyze(triangles,edges,1,policy|{'min_texels_per_meter':33})['passed']
    assert not analyze(triangles,edges,1,policy|{'mip_levels':2})['passed']
    assert not analyze(triangles,edges,1,policy|{'max_raster_tests':1})['complete']
    assert not analyze(triangles*2,edges,1,policy)['complete']
    tiny,tiny_edges=square(.001,.002)
    assert analyze(tiny,tiny_edges,1,policy|{'padding_pixels':0})['levels'][0]['undersized_chart_count']==1
    # Two charts with four-pixel separation at base, only two at mip 1.
    a,ae=square(.125,.375,0);b,be=square(.5,.75,1)
    assert analyze(a+b,ae+be,2,policy|{'mip_levels':0})['passed']
    result=analyze(a+b,ae+be,2,policy)
    assert not result['passed'] and result['levels'][1]['spacing']['violation_pair_count']==1


def test_contract_resolution_and_readonly_discovery(tmp_path):
    base={'name':'Mesh','expected_bake':'a'*64,'directory':'baked'}
    with pytest.raises(ValueError,match='dimensions'):BakeTextures(**base,width=32,height=32,quality=Quality())
    with pytest.raises(ValueError,match='margin'):BakeTextures(**base,quality=Quality(padding_pixels=2))
    for values in ({'width':4096,'height':4096},{'min_texels_per_meter':float('nan')},{'max_raster_tests':0},{'mip_levels':9}):
        with pytest.raises(ValueError):Quality(**values)
    config=Config();config.stdio.library_root=str(tmp_path);config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_texture_quality' in names and 'bake_textures' not in names
    asyncio.run(run())
