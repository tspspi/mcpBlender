"""Lifecycle authority, explicit guards and bounded replacement recipes."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.lod_contracts import Rebuild,SourceVisibility


def test_lifecycle_contracts():
    recipe={'chain':'Asset','name':'Source','expected_source':'a'*64,'expected_management':'b'*64,'levels':[{'triangle_budget':100}]}
    assert Rebuild.model_validate(recipe).preserve_placement
    for patch in ({'expected_management':'bad'},{'levels':[]},{'chain':'a'*41}):
        with pytest.raises(ValueError):Rebuild.model_validate(recipe|patch)
    with pytest.raises(ValueError):SourceVisibility.model_validate({'chain':'Asset','expected_management':'b'*64})
    assert SourceVisibility.model_validate({'chain':'Asset','expected_management':'b'*64,'hide_render':False}).hide_render is False


def test_lifecycle_readonly_discovery(tmp_path):
    cfg=Config();cfg.stdio.library_root=str(tmp_path);cfg.stdio.allow_scene_edit=False
    server,_=build_server(cfg)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_lod_management' in names
            assert not {'rebuild_lod_chain','remove_lod_chain','configure_lod_source_visibility'}&names
    asyncio.run(run())
