"""Family cardinality, budgets, readonly discovery and per-view typed creation."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.card_contracts import Views


def test_view_contracts_and_discovery(tmp_path):
    for patch in ({'views':['TOP','TOP']},{'views':[]},{'views':['UNSUPPORTED']},{'max_projected_triangles':True},{'max_total_card_triangles':2541}):
        with pytest.raises(ValueError):Views(sources=['Cube'],**patch)
    cfg=Config();cfg.bridge.socket_path=str(tmp_path/'bridge/sock');cfg.stdio.allow_scene_edit=False
    server,_=build_server(cfg)
    async def run():
        async with Client(server) as client:
            tools={t.name:t for t in await client.list_tools()}
            assert tools['inspect_foliage_card_views'].input_schema['properties']['wait']['default'] is False
            assert 'create_foliage_card' not in tools
    asyncio.run(run())
