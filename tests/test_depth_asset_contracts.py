"""Strict bounded contracts, policy discovery and library-contained capture reads."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.depth_asset_contracts import Source,Create,Settings
from mcpblender.server import build_server,State


def test_strict_patch_settings_and_default_approximation_acceptance():
    for patch in ({'tile_pixels':True},{'tile_pixels':3},{'max_pixels':4194304},{'edge_radius_pixels':65},{'edge_depth_policy':'INVENT'},{'alpha_threshold':0},{'geometry_mode':'GUESS'},{'normal_tolerance_degrees':True},{'max_slope':False},{'max_refinement_work':True},{'max_triangles':True}):
        with pytest.raises(ValueError):Settings(**patch)
    from mcpblender import depth_tiles
    assert depth_tiles.options({'normal_tolerance_degrees':15,'max_slope':16})==depth_tiles.options({'normal_tolerance_degrees':15.0,'max_slope':16.0})
    assert not Create(directory='capture',view='FRONT',collection='Far',expected_plan='a'*64).accept_approximate_optics


def test_readonly_tools_and_capture_path_containment(tmp_path):
    cfg=Config();cfg.bridge.socket_path=str(tmp_path/'sock');cfg.stdio.library_root=str(tmp_path/'library');cfg.stdio.allow_scene_edit=False
    server,state=build_server(cfg);(tmp_path/'library').mkdir();(tmp_path/'library/capture').mkdir()
    args=Source(directory='capture',view='FRONT').model_dump()
    prepared=state.prepare('inspect_botanical_depth_source',args)
    assert prepared['directory']==str(tmp_path/'library/capture')
    assert State.input_paths('inspect_botanical_depth_source',prepared)==[prepared['directory']]
    with pytest.raises(ValueError):state.prepare('inspect_botanical_depth_source',args|{'directory':'../escape'})
    async def run():
        async with Client(server) as client:
            tools={t.name:t for t in await client.list_tools()}
            assert 'inspect_botanical_depth_source' in tools and 'inspect_botanical_depth_asset' in tools
            assert 'create_botanical_depth_asset' not in tools and 'remove_botanical_depth_asset' not in tools
            assert tools['inspect_botanical_depth_source'].input_schema['properties']['wait']['default'] is False
    asyncio.run(run())
