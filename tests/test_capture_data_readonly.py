"""Opt-in portable reference inspection with no Blender or write permissions."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.wire import call

source=Path(os.environ['MCPBLENDER_CAPTURE_DATA_SOURCE']) if os.environ.get('MCPBLENDER_CAPTURE_DATA_SOURCE') else None
pytestmark=pytest.mark.skipif(source is None or not source.is_dir(),reason='Set MCPBLENDER_CAPTURE_DATA_SOURCE to a retained native capture bundle')


def test_portable_capture_data_without_blender_or_write_authority(tmp_path):
    cfg=Config();cfg.bridge.socket_path=str(tmp_path/'bridge/socket');cfg.launch.auto_start=False
    cfg.stdio.library_root=str(tmp_path/'library');cfg.stdio.allow_scene_edit=False;cfg.stdio.allow_snapshots=False;cfg.stdio.allow_start_blender=False;cfg.stdio.allow_library_write=False
    archive=Path(cfg.stdio.library_root)/'archive';shutil.copytree(source,archive)
    inventory={str(p.relative_to(archive)):(p.stat().st_size,p.stat().st_mtime_ns) for p in archive.rglob('*') if p.is_file()}
    server,state=build_server(cfg)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_botanical_capture_data' in names and 'capture_botanical_views' not in names
            result=(await client.call_tool('inspect_botanical_capture_data',{'params':{'directory':'archive','views':['FRONT']},'wait':True})).data
            assert result['views'][0]['covered_pixels']>0 and result['views'][0]['nonfinite_covered']==0
            broker=await state.control('status');assert broker['connected'] is False and 'pid' not in broker
            assert {str(p.relative_to(archive)):(p.stat().st_size,p.stat().st_mtime_ns) for p in archive.rglob('*') if p.is_file()}==inventory
            out=os.environ.get('MCPBLENDER_CAPTURE_DATA_EVIDENCE_DIR')
            if out:
                folder=Path(out);folder.mkdir(parents=True,exist_ok=True);(folder/'readonly-proof.json').write_text(json.dumps(result,indent=2))
    try:asyncio.run(run())
    finally:call(cfg.bridge.socket_path,'shutdown',timeout=5)
