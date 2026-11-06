"""Exact camera clips and SUN size through structured controls, no Python tool."""
import asyncio,math,subprocess
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from mcpblender.commands import Light,Camera
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait


def test_clip_and_sun_schema_preflight():
    with pytest.raises(ValueError,match='SUN'):Light(name='L',type='POINT',angle=.1)
    with pytest.raises(ValueError,match='clip'):Camera(name='C',clip_start=2,clip_end=1)
    assert Light(name='L',type='SUN',angle=0).angle==0


def test_native_camera_light_readback_and_invalid_clipping_preserves_pose(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            camera=await wait(client,'configure_camera',name='ExactCamera',projection='ORTHO',ortho_scale=4.,location=[0,-8,2],rotation_euler=[math.pi/2,0,0],clip_start=.05,clip_end=50.)
            assert camera['camera_settings']['clip_start']==pytest.approx(.05) and camera['camera_settings']['clip_end']==50.
            sun=await wait(client,'configure_light',name='ExactSun',type='SUN',angle=0.,energy=2.,rotation_euler=[math.pi/2,0,0])
            assert sun['light_settings']['angle']==0. and sun['light_settings']['energy']==2.
            with pytest.raises(ToolError,match='clip'):
                await wait(client,'configure_camera',name='ExactCamera',location=[12,13,14],clip_end=.01)
            assert (await client.call_tool('get_object_info',{'name':'ExactCamera'})).data['location']==camera['location']
            with pytest.raises(ToolError,match='clip'):
                await wait(client,'configure_camera',name='NeverCreated',clip_end=.01)
            with pytest.raises(ToolError):await client.call_tool('get_object_info',{'name':'NeverCreated'})
            await client.call_tool('save_blend',{'path':'camera-light.blend'})
            code='import bpy\nbpy.ops.wm.open_mainfile(filepath='+repr(str(root/'library/camera-light.blend'))+',use_scripts=False)\n'
            code+="c=bpy.data.objects['ExactCamera'];s=bpy.data.objects['ExactSun']\nassert c.location[:]==(0.,-8.,2.)\nassert abs(c.data.clip_start-.05)<1e-7 and c.data.clip_end==50 and c.data.type=='ORTHO' and c.data.ortho_scale==4\nassert s.data.angle==0 and s.data.energy==2 and s.data.type=='SUN'\nprint('CAMERA_LIGHT_NATIVE_COMPLETE')\n"
            native=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python-expr',code],capture_output=True,text=True,timeout=30)
            assert native.returncode==0,native.stdout+native.stderr
    asyncio.run(run())
