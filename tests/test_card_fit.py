"""Known projections, hull savings, orientation, coverage and budget contracts."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.card_fit import fit,area
from mcpblender.card_contracts import Plan,Create
from mcpblender.config import Config
from mcpblender.server import build_server

TRIANGLES=[[(0,0,.01),(1,0,.02),(0,1,.03)]]


def test_fitted_triangle_encloses_source_and_reduces_empty_area():
    rect=fit(TRIANGLES,outline='RECTANGLE',padding=0)
    tight=fit(TRIANGLES,padding=0)
    assert rect['card_area_m2']==1 and tight['card_area_m2']==.5
    assert tight['projection']['geometry_coverage_fraction']==1
    assert .49<rect['projection']['geometry_coverage_fraction']<.51
    assert tight['vertices_m']==[[0,0,.005],[1,0,.005],[0,1,.005]]
    assert tight['uv']==[(0,0),(1,0),(0,1)]
    assert tight['bake_ray_length_m']==pytest.approx(.03)
    padded=fit(TRIANGLES,padding=.02)
    assert .5<padded['card_area_m2']<.6
    assert padded==fit(TRIANGLES,padding=.02)
    assert area([(1e9,1e9),(1e9+1,1e9),(1e9,1e9+1)])==.5
    for view,normal in [('TOP',(0,0,1)),('FRONT',(0,-1,0)),('SIDE',(1,0,0))]:
        # Nondegenerate projections in every view have the declared bake normal.
        p=fit([[(0,0,0),(1,0,1),(0,1,2)]],view=view,padding=.02)['vertices_m']
        a=[p[1][i]-p[0][i] for i in range(3)];b=[p[2][i]-p[0][i] for i in range(3)]
        cross=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
        assert sum(x*y for x,y in zip(cross,normal))>0


def test_limits_degenerate_and_cooperative_cancel():
    for patch in ({'resolution':1},{'max_triangles':0},{'standoff_m':0},{'padding':float('nan')},{'view':'BACK'}):
        with pytest.raises(ValueError):fit(TRIANGLES,**patch)
    with pytest.raises(ValueError,match='edge-on'):fit([[(0,0,0),(1,0,0),(2,0,0)]])
    with pytest.raises(ValueError,match='max_vertices'):fit(TRIANGLES,max_vertices=4)
    def cancel():raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError,match='cancelled'):fit(TRIANGLES,cancelled=cancel)
    for patch in ({'sources':[]},{'sources':['A','A']},{'max_vertices':3},{'thin_foliage_mode':'AUTO'}):
        with pytest.raises(ValueError):Plan.model_validate({'sources':['A']}|patch)
    with pytest.raises(ValueError):Create(sources=['A'],name='A',expected_card='a'*64)


def test_readonly_discovery(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path);config.stdio.allow_scene_edit=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_foliage_card' in names and 'create_foliage_card' not in names
    asyncio.run(run())
