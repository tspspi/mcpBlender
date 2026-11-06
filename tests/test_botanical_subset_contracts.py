"""Strict capture selection, policy discovery and contained source reads."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.botanical_subset_contracts import Source,Create
from mcpblender.server import build_server,State


def test_subset_selection_limits():
    assert Source(directory='capture').selection=='UNOBSERVED'
    for patch in ({'views':['FRONT','FRONT']},{'views':[]},{'selection':'HIDDEN'},{'max_total_pixels':True},{'alpha_threshold':0},{'render_role':'CAMERA'}):
        with pytest.raises(ValueError):Source(directory='capture',**patch)
    with pytest.raises(ValueError):Create(directory='capture',subset_collection='Copy')


def test_subset_policy_and_paths(tmp_path):
    cfg=Config();cfg.bridge.socket_path=str(tmp_path/'sock');cfg.stdio.library_root=str(tmp_path/'library');cfg.stdio.allow_scene_edit=False
    server,state=build_server(cfg);(tmp_path/'library/capture').mkdir(parents=True)
    args=Source(directory='capture').model_dump()
    prepared=state.prepare('inspect_botanical_subset_source',args)
    assert prepared['directory']==str(tmp_path/'library/capture')
    assert State.input_paths('inspect_botanical_subset_source',prepared)==[prepared['directory']]
    with pytest.raises(ValueError):state.prepare('inspect_botanical_subset_source',args|{'directory':'../escape'})
    async def run():
        async with Client(server) as client:
            tools={t.name:t for t in await client.list_tools()}
            assert {'inspect_botanical_subset_source','inspect_botanical_subset'}<=tools.keys()
            assert 'create_botanical_subset' not in tools and 'remove_botanical_subset' not in tools
            assert tools['inspect_botanical_subset_source'].input_schema['properties']['wait']['default'] is False
    asyncio.run(run())
