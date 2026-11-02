"""UV geometry controls and guarded/read-only MCP contract checks."""
import asyncio

from fastmcp import Client
import pytest

from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.uv_contracts import UVLayout, UVUnwrap, UVSeams, UVDensity
from mcpblender.uv_math import triangle_overlap


def test_overlap_positive_area_and_boundary_contacts():
    tri=[(0,0),(1,0),(0,1)]
    assert triangle_overlap(tri,tri)==pytest.approx(.5)
    assert triangle_overlap(tri,list(reversed(tri)))==pytest.approx(.5)
    assert triangle_overlap(tri,[(1,0),(1,1),(0,1)])==pytest.approx(0)
    assert triangle_overlap(tri,[(.5,0),(1.5,0),(.5,1)])==pytest.approx(.125)
    assert triangle_overlap(tri,[(2,0),(3,0),(2,1)])==0
    assert triangle_overlap(tri,[(.2,.2)]*3)==0
    assert triangle_overlap(tri,[(.1,.1),(.2,.2),(.3,.3)])==0


def test_uv_guards_limits_and_readonly_discovery(tmp_path):
    base={'name':'Box','expected_uv':'a'*64}
    for cls,values in ((UVLayout,{'texture_width':0}), (UVUnwrap,{'margin':float('nan')}),
                       (UVDensity,{'pixels_per_unit':0}), (UVSeams,{'edges':{'indices':[0,0]}})):
        with pytest.raises(ValueError):cls.model_validate(({'name':'Box'} if cls is UVLayout else base)|values)
    with pytest.raises(ValueError):UVUnwrap(name='Box',expected_uv='stale')
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False
    config.bridge.socket_path=str(tmp_path/'private/socket')
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_uv_layout' in names
            assert not names & {'unwrap_uv_mesh','pack_uv_islands','set_uv_seams','normalize_uv_density','activate_uv_map'}
    asyncio.run(run())
    assert not (tmp_path/'private/socket').exists()
