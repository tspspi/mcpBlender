"""Bounded native preview contracts and read-only discovery."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.wind_contracts import PreviewPlan,CreatePreview

def test_preview_limits_and_policy(tmp_path):
    for patch in ({'frame_end':1},{'frame_end':1000},{'frame_step':0},{'max_instances':-1},{'display_offset_m':[float('nan'),0,0]}):
        with pytest.raises(ValueError):PreviewPlan.model_validate({'collection':'Oak'}|patch)
    with pytest.raises(ValueError):CreatePreview(collection='Oak',preview_collection='Oak',expected_plan='a'*64)
    config=Config();config.stdio.library_root=str(tmp_path);config.stdio.allow_scene_edit=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_botanical_wind_preview_source','inspect_botanical_wind_preview'}<=names
            assert not {'create_botanical_wind_preview','remove_botanical_wind_preview'}&names
    asyncio.run(run())

def test_numeric_frame_results_are_not_render_paths(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path)
    _,state=build_server(config)
    assert state.enrich_result({'frames':[1,2,3]},'wind-operation')=={'frames':[1,2,3]}
    path=tmp_path/'frame.png';path.write_bytes(b'frame artifact')
    result=state.enrich_result({'frames':[str(path)]},'render-operation')
    assert len(result['preview_artifacts'])==1
