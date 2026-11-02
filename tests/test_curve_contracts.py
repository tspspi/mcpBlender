"""Channel schemas and read-only discovery."""
import asyncio

from fastmcp import Client
import pytest

from mcpblender.config import Config
from mcpblender.curve_contracts import ControlKeys, EditCurve
from mcpblender.server import build_server


def test_typed_controller_keys_and_curve_operations():
    base={'name':'Rig','output_clip':'New','expected_animation':'a'*64}
    valid=base|{'bone':'Control','property':'location','keyframes':[{'frame':1,'value':[0,0,0]}]}
    assert ControlKeys.model_validate(valid).property=='location'
    for change in ({'keyframes':[{'frame':1,'value':.5}]},
                   {'keyframes':[{'frame':1,'value':[0,0,0]},{'frame':1,'value':[1,1,1]}]},
                   {'property':'influence'}, {'constraint':'Reach'},
                   {'property':'rotation_quaternion','keyframes':[{'frame':1,'value':[0,0,0,0]}]},
                   {'keyframes':[{'frame':1,'value':[float('nan'),0,0]}]},
                   {'keyframes':[{'frame':True,'value':[0,0,0]}]}):
        with pytest.raises(ValueError):ControlKeys.model_validate(valid|change)
    curve=base|{'data_path':'location','frames':[1,5],'settings':{'operation':'TRANSFORM','time_scale':2}}
    assert EditCurve.model_validate(curve).settings.time_scale==2
    for change in ({'frames':[1,1]}, {'settings':{'operation':'TRANSFORM','time_scale':0}},
                   {'settings':{'operation':'HANDLES','left':[0,1]}},
                   {'settings':{'operation':'HANDLES','left_type':'FREE','left':[0,1]}},
                   {'settings':{'operation':'PYTHON'}}):
        with pytest.raises(ValueError):EditCurve.model_validate(curve|change)


def test_channel_inspection_available_without_edit_permission(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_animation_channels' in names
            assert not {'set_control_keyframes','edit_animation_curve'} & names
    asyncio.run(run())
