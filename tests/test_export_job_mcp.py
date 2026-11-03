"""Broker-only recovery works with Blender closed and automatic startup disabled."""
import asyncio
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import client_for,tool
from test_package_files import manifest
from mcpblender.config import Config,write_config
from mcpblender.export_jobs import ExportJob
from mcpblender.wire import call


def test_broker_only_reconcile_publish_and_protected_cleanup(tmp_path):
    config=Config();config.launch.auto_start=False;config.storage.reserve_bytes=10**18;config.bridge.socket_path=str(tmp_path/'bridge/bridge.sock');config.stdio.library_root=str(tmp_path/'library')
    library=Path(config.stdio.library_root);library.mkdir();path=tmp_path/'config.json';write_config(path,config)
    directory=library/'package';job=ExportJob(directory,'stdio','PACKAGE',{'source_sha256':'a'*64},asset_ids=['prop']);job.__enter__();job.stage.mkdir();job.created();manifest(job.stage);job.verify();job.lock.__exit__(None,None,None);job.lock=None
    async def run():
        async with client_for(path) as client:
            listing=(await client.call_tool('list_export_jobs',{'params':{'directory':'.'},'wait':True})).data
            assert len(listing['jobs'])==1 and listing['jobs'][0]['directory']==str(directory)
            state=await tool(client,'inspect_export_job',directory='package');assert not state['writer_active'] and state['record']['state']=='verified'
            assert not state['storage']['enough_space'] and state['storage']['reserve_bytes']==10**18
            result=(await client.call_tool('recover_export_job',{'params':{'directory':'package','expected_job':state['job_sha256']},'wait':True})).data
            assert result['record']['state']=='ready' and not result['replayed']
            operation=(await client.call_tool('get_operation',{'operation_id':result['operation_id']})).data
            assert operation['progress']['storage']['free_bytes']>0
            with pytest.raises(ToolError,match='protected'):
                await client.call_tool('cleanup_export_job',{'params':{'directory':'package','expected_job':result['job_sha256'],'dry_run':False},'wait':True})
            published=(await client.call_tool('recover_export_job',{'params':{'directory':'package','expected_job':result['job_sha256'],'publish':True},'wait':True})).data
            assert published['record']['state']=='published' and (directory/'manifest.json').exists()
            with pytest.raises(ToolError,match='protected'):
                await client.call_tool('cleanup_export_job',{'params':{'directory':'package','expected_job':published['job_sha256'],'dry_run':False},'wait':True})
            status=(await client.call_tool('bridge_status')).data
            assert not status['bridge']['connected']
    try:asyncio.run(run())
    finally:
        if Path(config.bridge.socket_path).exists():call(config.bridge.socket_path,'shutdown',timeout=5)
