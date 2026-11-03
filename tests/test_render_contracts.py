"""Bounded render requests and read-only/file-only policy boundaries."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.render_contracts import Batch


def test_batch_limits_and_paths(tmp_path):
    base={'directory':'batch','expected_settings':'a'*64,'cameras':['Cam'],'frame_start':1,'frame_end':1}
    assert Batch.model_validate(base)
    for patch in ({'cameras':[]},{'cameras':['Cam']*2},{'frame_end':0},{'frame_end':1001},{'frame_step':0},{'formats':['PNG']*2},{'formats':['JPEG']},{'width':15},{'threads':17},{'frame_start':1.5}):
        with pytest.raises(ValueError):Batch.model_validate(base|patch)
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_snapshots=False;config.stdio.allow_library_write=False
    server,state=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_render_job','validate_render_job'}<=names
            assert not {'render_camera_batch','recover_render_job','cleanup_render_job'}&names
    asyncio.run(run())
    with pytest.raises(ValueError,match='inside'):state.prepare('render_camera_batch',base|{'directory':'../outside'})
    assert state.input_paths('inspect_render_job',{'directory':'batch'})==['batch']
