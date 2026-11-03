"""Batch associations, authority and library output boundaries."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.package_contracts import Plan
from mcpblender.server import build_server,State
from mcpblender.config import Config


def test_package_contracts():
    assert Plan(assets=[{'id':'prop','objects':['Source']}]).assets[0].lods==[]
    for assets in ([],[{'id':'../escape','objects':['Source']}],[{'id':'prop','objects':['Source','Source']}],[{'id':'prop','objects':['Source']},{'id':'PROP','objects':['Other']}],[{'id':'prop','objects':['Source'],'collision_proxies':['Proxy'],'shadow_proxies':['Proxy']}]):
        with pytest.raises(ValueError):Plan.model_validate({'assets':assets})


def test_package_discovery_and_paths(tmp_path):
    cfg=Config();cfg.stdio.library_root=str(tmp_path/'library');cfg.stdio.allow_scene_edit=False;cfg.stdio.allow_library_write=False
    server,state=build_server(cfg)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_asset_package','validate_asset_package'}<=names
            assert 'export_asset_package' not in names
    asyncio.run(run())
    with pytest.raises(ValueError,match='inside'):state.prepare('export_asset_package',{'directory':'../escape','expected_source':'a'*64,'assets':[{'id':'prop','objects':['Source']}]})
    assert State.input_paths('validate_asset_package',{'directory':'bundle'})==['bundle']
