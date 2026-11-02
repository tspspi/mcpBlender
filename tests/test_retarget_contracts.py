"""Explicit mapping, time and read-only retarget contracts."""
import asyncio
from fastmcp import Client
import pytest
from mcpblender.config import Config
from mcpblender.retarget_contracts import RetargetAnimation
from mcpblender.server import build_server


def test_mapping_and_timeline_guards():
    base={'name':'Target','source':'Source','mappings':[{'source':'Hip','target':'Pelvis'}],'output_rig':'Result','clip':'Motion',
          'frame_start':1,'frame_end':9,'expected_source_rig':'a'*64,'expected_target_rig':'b'*64}
    assert RetargetAnimation.model_validate(base).object_motion=='COPY'
    for patch in ({'mappings':[]},{'mappings':[{'source':'Hip','target':'Pelvis'},{'source':'Hip','target':'Root'}]},
                  {'frame_end':501},{'playback_speed':0},{'frame_start':True},{'translation_scale':float('nan')},
                  {'source_start':1048570},{'output_rig':'Bad\0Name'},
                  {'meshes':[{'source':'Skin','output':'Result'}]}):
        with pytest.raises(ValueError):RetargetAnimation.model_validate(base|patch)


def test_readonly_retarget_plan(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_animation_retarget' in names and 'retarget_animation' not in names
    asyncio.run(run())
