"""Typed limits and readonly discovery for semantic botanical collision tools."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.botanical_collision_contracts import Source,Create
from mcpblender.config import Config
from mcpblender.server import build_server


def test_botanical_collision_bounds_and_permissions(tmp_path):
    for patch in ({'min_radius_m':float('nan')},{'max_colliders':True},{'triangle_budget':100001},{'max_branch_order':9}):
        with pytest.raises(ValueError):Source(collection='Tree',**patch)
    for patch in ({'collision_collection':'Tree'},{'collision_collection':'x'*41},{'display_offset_m':[float('inf'),0,0]}):
        base={'collection':'Tree','collision_collection':'Colliders','expected_plan':'a'*64}|patch
        with pytest.raises(ValueError):Create(**base)
    cfg=Config();cfg.bridge.socket_path=str(tmp_path/'bridge/sock');cfg.stdio.allow_scene_edit=False
    server,_=build_server(cfg)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_botanical_collision_source','inspect_botanical_collisions'}<=names
            assert not {'create_botanical_collisions','remove_botanical_collisions'}&names
    asyncio.run(run())
