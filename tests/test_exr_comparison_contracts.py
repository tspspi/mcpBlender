"""Explicit HDR pass/alpha declarations, policy-null transport and read authority."""
import asyncio
from fastmcp import Client
import pytest
from mcpblender.config import Config
from mcpblender.server import State,build_server
from mcpblender.image_comparison_contracts import CompareEXR


def test_contracts_hdr_policy_and_passes(tmp_path):
    args={'reference':'a.exr','candidate':'b.exr','reference_pass':'Layer.Combined','candidate_pass':''}
    assert CompareEXR(**args,quality={'max_overlap_rgb_rmse':5}).quality.max_overlap_rgb_rmse==5
    for patch in ({'reference_pass':'a\0b'},{'candidate_pass':'ä'*129},{'reference_alpha_mode':'AUTO'},{'color_space':'SRGB'},{'max_pixels':True},{'max_pixels':0},{'max_pixels':4*1024**2+1},{'scales':[True]},{'quality':{'max_overlap_rgb_rmse':True}}):
        with pytest.raises(ValueError):CompareEXR(**(args|patch))
    cfg=Config();cfg.bridge.socket_path=str(tmp_path/'bridge/sock');cfg.stdio.library_root=str(tmp_path/'library');cfg.stdio.allow_scene_edit=False;cfg.stdio.allow_library_write=False
    root=tmp_path/'library';root.mkdir()
    for name in ('a.exr','b.exr','c.png'):(root/name).write_bytes(b'fixture')
    server,state=build_server(cfg)
    prepared=state.prepare('compare_exr_images',args|{'quality':{'max_overlap_rgb_rmse':None,'max_abs_overlap_luminance_relative_bias':None}})
    assert prepared['quality']['max_overlap_rgb_rmse'] is None and prepared['quality']['max_abs_overlap_luminance_relative_bias'] is None
    assert State.input_paths('compare_exr_images',prepared)==[str(root/'a.exr'),str(root/'b.exr')]
    for patch in ({'reference':'../escape.exr'},{'candidate':'c.png'}):
        with pytest.raises((ValueError,FileNotFoundError,PermissionError)):state.prepare('compare_exr_images',args|patch)
    async def run():
        async with Client(server) as client:
            tools={t.name:t for t in await client.list_tools()}
            assert 'compare_exr_images' in tools and tools['compare_exr_images'].input_schema['properties']['wait']['default'] is False
    asyncio.run(run())
