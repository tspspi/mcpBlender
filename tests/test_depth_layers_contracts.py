"""Batch schemas, conservative budgets and policy-contained capture reads."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.depth_asset_contracts import LayersSource,LayersCreate,LayerLimits
from mcpblender.server import build_server,State


def test_layer_contract_bounds_and_names():
    source={'directory':'input','prefix':'Canopy','layers':[{'view':'FRONT','render_role':'CAMERA_ONLY'},{'view':'BACK','render_role':'SECONDARY'}]}
    assert LayersSource(**source).limits.max_total_texture_bytes==256*1024**2
    assert not LayersCreate(**source,expected_plan='a'*64).accept_approximate_optics
    for patch in ({'layers':[]},{'layers':[{'view':'TOP'},{'view':'TOP'}]},{'prefix':'x'*60},{'prefix':'ä'*30},{'prefix':'bad\0name'},{'layers':[{'view':'FRONT','render_role':'INVENT'}]}):
        with pytest.raises(ValueError):LayersSource(**(source|patch))
    for patch in ({'max_total_pixels':True},{'max_total_texture_bytes':513*1024**2},{'max_total_triangles':1310721}):
        with pytest.raises(ValueError):LayerLimits(**patch)


def test_layer_tools_policy_paths_and_async_default(tmp_path):
    cfg=Config();cfg.stdio.allow_scene_edit=False;cfg.stdio.library_root=str(tmp_path/'library');cfg.bridge.socket_path=str(tmp_path/'sock')
    root=tmp_path/'library';(root/'input').mkdir(parents=True);server,state=build_server(cfg)
    args=LayersSource(directory='input',prefix='Set',layers=[{'view':'FRONT'}]).model_dump()
    prepared=state.prepare('inspect_botanical_depth_layers',args)
    assert prepared['directory']==str(root/'input')
    assert State.input_paths('inspect_botanical_depth_layers',prepared)==[prepared['directory']]
    assert State.input_paths('create_botanical_depth_layers',prepared)==[prepared['directory']]
    with pytest.raises(ValueError):state.prepare('inspect_botanical_depth_layers',args|{'directory':'../outside'})
    async def run():
        async with Client(server) as client:
            names={t.name:t for t in await client.list_tools()}
            assert 'inspect_botanical_depth_layers' in names and 'create_botanical_depth_layers' not in names
            assert names['inspect_botanical_depth_layers'].input_schema['properties']['wait']['default'] is False
    asyncio.run(run())
