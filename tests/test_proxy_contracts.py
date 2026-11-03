"""Explicit approximation choices, source bounds and authorization discovery."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.proxy_contracts import Source,ConfigureVisibility


def test_proxy_settings():
    assert Source(objects=['Body']).method=='CONVEX_HULL'
    for patch in ({'objects':['Body','Body']},{'padding':1},{'triangle_budget':100},{'purpose':'SHADOW'},
                  {'method':'DECIMATE'},{'max_relative_error':float('nan')},{'sample_count':2049}):
        with pytest.raises(ValueError):Source.model_validate({'objects':['Body']}|patch)
    shadow={'objects':['Body'],'purpose':'SHADOW','method':'DECIMATE','triangle_budget':100}
    assert Source.model_validate(shadow).grouping=='PER_LEAF'
    with pytest.raises(ValueError):Source.model_validate(shadow|{'grouping':'COMBINED'})
    assert Source.model_validate({'objects':['Body'],'method':'BOX','padding':.1}).padding==.1


def test_readonly_proxy_discovery(tmp_path):
    cfg=Config();cfg.stdio.library_root=str(tmp_path);cfg.stdio.allow_scene_edit=False
    server,_=build_server(cfg)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_asset_proxy_source','inspect_asset_proxies','inspect_render_visibility'}<=names
            assert not {'generate_asset_proxies','remove_asset_proxies','configure_render_visibility'}&names
    asyncio.run(run())


def test_visibility_patch():
    base={'name':'Source','expected_visibility':'a'*64}
    with pytest.raises(ValueError):ConfigureVisibility.model_validate(base)
    assert ConfigureVisibility.model_validate(base|{'visible_shadow':False}).visible_shadow is False
