"""Typed native NLA ranges and read-only surface."""
import asyncio
from fastmcp import Client
import pytest
from mcpblender.config import Config
from mcpblender.nla_contracts import StripSettings,Playback,TrackSettings
from mcpblender.server import build_server


def test_nla_settings_bounds_and_playback_policy():
    base={'clip':'Walk','start':1,'action_start':1,'action_end':9}
    assert StripSettings.model_validate(base).extrapolation=='NOTHING'
    for patch in ({'action_end':1},{'scale':0},{'repeat':0},{'start':1048573},{'blend_in':9},
                  {'influence':2},{'scale':float('nan')},{'start':True},{'blend':'SCRIPT'}):
        with pytest.raises(ValueError):StripSettings.model_validate(base|patch)
    with pytest.raises(ValueError):TrackSettings(name='Rig',track='Bad\0Name',expected_nla='a'*64)
    with pytest.raises(ValueError):Playback(name='Rig',expected_nla='a'*64,reset_base=True)


def test_readonly_nla_inspection(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_nla' in names
            assert not {'configure_nla_track','configure_nla_strip','configure_nla_playback','move_nla_track','remove_nla_track','remove_nla_strip'}&names
    asyncio.run(run())
