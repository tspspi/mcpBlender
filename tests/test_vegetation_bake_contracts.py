"""Structured source selection and policy-controlled discovery."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.vegetation_bake_contracts import Source


def test_source_selection_and_limits():
    with pytest.raises(ValueError):Source()
    with pytest.raises(ValueError):Source(collection='Tree',lod_collection='Lods')
    with pytest.raises(ValueError):Source(collection='Tree',assets=['wood','wood'])
    with pytest.raises(ValueError):Source(collection='Tree',margin=0)
    assert Source(collection='Tree').missing_uv_policy=='REFUSE'


def test_readonly_discovery(tmp_path):
    config=Config();config.stdio.allow_scene_edit=False;config.stdio.library_root=str(tmp_path)
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_vegetation_bake_source','inspect_vegetation_bake'}<=names
            assert not {'prepare_vegetation_bake','remove_vegetation_bake'}&names
    asyncio.run(run())
