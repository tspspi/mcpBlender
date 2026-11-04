"""Readonly discovery and explicit bounded cluster planning contracts."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.foliage_cluster_contracts import Plan,Create,Remove


def test_limits_and_readonly_discovery(tmp_path):
    for patch in ({'max_leaves':True},{'max_triangles':250001},{'max_clusters':4097},{'anchor_order':9},{'limit':65},{'offset':-1}):
        with pytest.raises(ValueError):Plan(collection='Tree',**patch)
    for patch in ({'cluster_index':True},{'cluster_collection':'Tree'},{'display_offset_m':[float('inf'),0,0]}):
        with pytest.raises(ValueError):Create(**({'collection':'Tree','cluster_collection':'Cluster','cluster_index':0,'expected_plan':'a'*64}|patch))
    cfg=Config();cfg.bridge.socket_path=str(tmp_path/'bridge/sock');cfg.stdio.allow_scene_edit=False
    server,_=build_server(cfg)
    async def run():
        async with Client(server) as client:
            tools={t.name:t for t in await client.list_tools()}
            assert {'inspect_botanical_foliage_clusters','inspect_botanical_foliage_cluster'}<=tools.keys()
            assert not {'create_botanical_foliage_cluster','remove_botanical_foliage_cluster'}&tools.keys()
            assert tools['inspect_botanical_foliage_clusters'].input_schema['properties']['wait']['default'] is False
    asyncio.run(run())
