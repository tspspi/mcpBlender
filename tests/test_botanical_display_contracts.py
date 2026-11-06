"""Explicit display batches, limits, flag types and read-only policy discovery."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.botanical_display_contracts import Inspect,Configure


def test_display_batch_contracts():
    target={'kind':'SOURCE','collection':'Tree'}
    assert Inspect(targets=[target]).targets[0].kind=='SOURCE'
    for values in ([],[target,target],[target|{'kind':'ARBITRARY'}],[{'kind':'SOURCE','collection':'X'+str(i)} for i in range(17)]):
        with pytest.raises(ValueError):Inspect(targets=values)
    for patch in ({},{'hide_render':1},{'hide_viewport':'yes'}):
        with pytest.raises(ValueError):Configure(targets=[target|patch],expected_display='a'*64)
    assert Configure(targets=[target|{'hide_viewport':False}],expected_display='a'*64).targets[0].hide_viewport is False


def test_display_inspection_survives_read_only_policy(tmp_path):
    cfg=Config();cfg.stdio.allow_scene_edit=False;cfg.stdio.library_root=str(tmp_path);cfg.bridge.socket_path=str(tmp_path/'socket');server,_=build_server(cfg)
    async def run():
        async with Client(server) as client:
            tools={t.name:t for t in await client.list_tools()}
            assert 'inspect_botanical_display' in tools and 'configure_botanical_display' not in tools
            assert tools['inspect_botanical_display'].input_schema['properties']['wait']['default'] is False
    asyncio.run(run())
