"""Wind policy and bounded semantic export paths."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server


def test_readonly_wind_and_output_paths(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False
    server,state=build_server(config)
    base={'collection':'Oak','expected_wind':'a'*64,'path':'wind.json'}
    assert state.prepare('export_botanical_wind',base)['path']==str(tmp_path/'library/wind.json')
    with pytest.raises(ValueError,match='inside'):state.prepare('export_botanical_wind',base|{'path':'../outside.json'})
    with pytest.raises(ValueError,match='json'):state.prepare('export_botanical_wind',base|{'path':'wind.blend'})
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_botanical_wind','sample_botanical_wind'}<=names and 'export_botanical_wind' not in names
    asyncio.run(run())
