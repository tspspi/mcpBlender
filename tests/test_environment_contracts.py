"""Bounded image headers, library boundaries and world editing discovery."""
import asyncio
import struct
import pytest
from fastmcp import Client
from mcpblender import environment_files as files
from mcpblender.environment_contracts import Configure
from mcpblender.config import Config
from mcpblender.server import build_server


def test_headers_and_predecode_budgets(tmp_path):
    png=b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',16,8)+b'\x08\x02\0\0\0'+b'\0'*4
    hdr=b'#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y 8 +X 16\n'
    assert files.dimensions(png)==files.dimensions(hdr)==(16,8)
    assert files.dimensions(hdr.replace(b'\n',b'\r\n'))==(16,8)
    jpeg=b'\xff\xd8\xff\xc0'+struct.pack('>HBHHB',8,8,8,16,0)
    assert files.dimensions(jpeg)==(16,8)
    channels=b''.join(n+b'\0'+struct.pack('<iB3xii',2,0,1,1) for n in (b'R',b'G',b'B'))+b'\0'
    box=struct.pack('<4i',0,0,15,7)
    def attribute(name,kind,data):return name+b'\0'+kind+b'\0'+struct.pack('<I',len(data))+data
    exr=b'\x76\x2f\x31\x01'+struct.pack('<I',2)+attribute(b'channels',b'chlist',channels)+attribute(b'dataWindow',b'box2i',box)+attribute(b'displayWindow',b'box2i',box)+b'\0'
    assert files.dimensions(exr)==(16,8)
    with pytest.raises(ValueError):files.dimensions(exr[:4]+struct.pack('<I',2|0x1000)+exr[8:])
    path=tmp_path/'source.hdr';path.write_bytes(hdr)
    with pytest.raises(ValueError,match='before decode'):files.inspect(path,1024,127)
    with pytest.raises(ValueError,match='max_image_bytes'):files.inspect(path,1,128)
    assert files.inspect(path,1024,128)['rgba32_estimated_bytes']==16*8*16
    import os
    fifo=tmp_path/'fifo';os.mkfifo(fifo)
    with pytest.raises(ValueError,match='regular'):files.inspect(fifo,1024,128)


def test_typed_environment_and_library_policy(tmp_path):
    base={'expected_environment':'a'*64}
    for settings in ({'mode':'COLOR','strength':float('nan')},{'mode':'SKY','sun_elevation_degrees':91},
                     {'mode':'HDRI','image_path':'file.exr','max_image_pixels':True},
                     {'mode':'HDRI','image_path':'file.exr','max_image_bytes':512*1024**2+1}):
        with pytest.raises(ValueError):Configure(**base,settings=settings)
    cfg=Config();cfg.stdio.library_root=str(tmp_path/'library');cfg.stdio.allow_scene_edit=False;cfg.bridge.socket_path=str(tmp_path/'bridge/socket')
    server,state=build_server(cfg)
    # Check path handling under an editable key without invoking Blender.
    cfg.stdio.allow_scene_edit=True;server,state=build_server(cfg)
    with pytest.raises(ValueError,match='inside'):state.prepare('configure_environment',base|{'settings':{'mode':'HDRI','image_path':'../outside.exr'}})
    cfg.stdio.allow_scene_edit=False;server,_=build_server(cfg)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'environment_catalog','inspect_environment'}<=names and 'configure_environment' not in names
    asyncio.run(run())
