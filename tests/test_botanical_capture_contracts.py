"""Capture budgets, optional permissions and portable pass/metadata binding."""
import asyncio
import copy
import pytest
from fastmcp import Client
from mcpblender import botany,tree_capture
from mcpblender.botanical_capture_contracts import Source,Capture
from mcpblender.config import Config
from mcpblender.server import build_server


def test_contracts_and_readonly_discovery(tmp_path):
    for patch in ({'views':[]},{'views':['FRONT','FRONT']},{'resolution':True},{'max_leaves':250001},{'world_strength':0}):
        with pytest.raises(ValueError):Source(collection='Tree',**patch)
    assert Capture(collection='Tree',directory='capture',expected_capture='a'*64)
    cfg=Config();cfg.bridge.socket_path=str(tmp_path/'sock');cfg.stdio.allow_snapshots=False
    server,_=build_server(cfg)
    async def run():
        async with Client(server) as client:
            tools={t.name:t for t in await client.list_tools()}
            assert 'inspect_botanical_view_capture' in tools and 'capture_botanical_views' not in tools
            assert tools['inspect_botanical_view_capture'].input_schema['properties']['wait']['default'] is False
    asyncio.run(run())


def test_portable_capture_binding_and_required_data_channels():
    data={'format':tree_capture.FORMAT,'views':[{'view':'FRONT','camera':'C'}],'frame':7,'options':{'resolution':64,'samples':4}}
    data['capture_sha256']=botany.digest(data)
    job={'cameras':['C'],'formats':['PNG','OPEN_EXR_MULTILAYER'],'engine':'CYCLES','frame_start':7,'frame_end':7,'width':64,'height':64,'samples':4}
    assert tree_capture.validate(data,job)==data
    for patch in ({'cameras':['Other']},{'height':32},{'frame_end':8},{'formats':['PNG']}):
        with pytest.raises(ValueError):tree_capture.validate(data,job|patch)
    bad=copy.deepcopy(data);bad['frame']=1
    with pytest.raises(ValueError,match='digest'):tree_capture.validate(bad,job)
    suffixes=['Combined.R','Combined.G','Combined.B','Combined.A','Depth.Z']
    suffixes += [f'{key}.{axis}' for key in ('Normal','Position') for axis in 'XYZ']
    suffixes += [f'{key}.{axis}' for key in ('Diffuse Color','Glossy Color','Transmission Color') for axis in 'RGB']
    header={'channels':[{'name':'TreeCapture.'+v,'pixel_type':2} for v in suffixes]}
    tree_capture.validate_header(header)
    header['channels'].pop()
    with pytest.raises(ValueError,match='float32'):tree_capture.validate_header(header)
