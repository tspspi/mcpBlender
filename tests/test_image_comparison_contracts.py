"""PNG comparison discovery, strict scales and library containment."""
import asyncio
from pathlib import Path
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server,State
from mcpblender.image_comparison_contracts import Compare
from test_image_comparison import png


def test_contracts_readonly_and_input_path_policy(tmp_path):
    for patch in ({'scales':[True]},{'scales':[1.]},{'scales':[2]},{'scales':[1,1]},{'alpha_threshold':0},{'quality':{'min_mask_iou':float('nan')}},{'quality':{'max_abs_overlap_luminance_relative_bias':True}},{'quality':{'max_abs_overlap_luminance_relative_bias':-.1}}):
        with pytest.raises(ValueError):Compare(**({'reference':'a.png','candidate':'b.png'}|patch))
    cfg=Config();cfg.bridge.socket_path=str(tmp_path/'bridge/sock');cfg.stdio.library_root=str(tmp_path/'library');cfg.stdio.allow_scene_edit=False;cfg.stdio.allow_library_write=False
    root=Path(cfg.stdio.library_root);root.mkdir()
    for name in ('a.png','b.png','c.jpg'):(root/name).write_bytes(png(1,1,[255,0,0,255]))
    server,state=build_server(cfg)
    params={'reference':'a.png','candidate':'b.png'}
    prepared=state.prepare('compare_png_images',params)
    assert state.prepare('compare_png_images',params|{'quality':{'min_mask_iou':None}})['quality']['min_mask_iou'] is None
    assert State.input_paths('compare_png_images',prepared)==[str(root/'a.png'),str(root/'b.png')]
    for patch in ({'reference':'../outside.png'},{'candidate':'c.jpg'}):
        with pytest.raises((ValueError,PermissionError,FileNotFoundError)):state.prepare('compare_png_images',params|patch)
    async def run():
        async with Client(server) as client:
            tools={t.name:t for t in await client.list_tools()}
            assert tools['compare_png_images'].input_schema['properties']['wait']['default'] is False
    asyncio.run(run())
