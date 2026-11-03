"""New bundle journals recover over MCP without starting Blender."""
import asyncio
from pathlib import Path
from fastmcp.exceptions import ToolError
import pytest
from test_asset_editing import client_for,tool
from test_vegetation_export_jobs import numeric_bundle
from mcpblender.config import Config,write_config
from mcpblender.export_jobs import ExportJob
from mcpblender.wire import call


def test_numeric_recovery_and_guarded_retention_without_blender(tmp_path):
    config=Config();config.launch.auto_start=False;config.bridge.socket_path=str(tmp_path/'bridge/bridge.sock');config.stdio.library_root=str(tmp_path/'library')
    library=Path(config.stdio.library_root);library.mkdir();path=tmp_path/'config.json';write_config(path,config)
    directory=library/'numeric';job=ExportJob(directory,'stdio','NUMERIC',{'export_sha256':'a'*64});job.__enter__();job.stage.mkdir();job.created();numeric_bundle(job.stage);job.verify();job.lock.__exit__(None,None,None);job.lock=None
    partial=library/'partial'
    with ExportJob(partial,'stdio','BOTANICAL',{}) as incomplete:
        incomplete.stage.mkdir();incomplete.created();nested=incomplete.stage/'.mcpblender-fields-abcdefgh';nested.mkdir();(nested/'asset.glb').write_bytes(b'partial')
    async def run():
        async with client_for(path) as client:
            state=await tool(client,'inspect_export_job',directory='numeric');assert state['record']['kind']=='NUMERIC' and not state['writer_active']
            ready=(await client.call_tool('recover_export_job',{'params':{'directory':'numeric','expected_job':state['job_sha256']},'wait':True})).data
            assert ready['record']['state']=='ready' and not ready['replayed']
            with pytest.raises(ToolError,match='protected'):await client.call_tool('cleanup_export_job',{'params':{'directory':'numeric','expected_job':ready['job_sha256'],'dry_run':False},'wait':True})
            call(config.bridge.socket_path,'shutdown',timeout=5)
            for _ in range(100):
                if not Path(config.bridge.socket_path).exists():break
                await asyncio.sleep(.05)
            else:raise AssertionError('Temporary broker did not stop')
            reconnected=await tool(client,'inspect_export_job',directory='numeric')
            assert reconnected['record']['state']=='ready' and reconnected['job_sha256']==ready['job_sha256']
            done=(await client.call_tool('recover_export_job',{'params':{'directory':'numeric','expected_job':ready['job_sha256'],'publish':True},'wait':True})).data
            assert done['record']['state']=='published' and done['target_is_original_stage']
            listed=(await client.call_tool('list_export_jobs',{'params':{'directory':'.','include_finished':True},'wait':True})).data
            assert any(j['record']['kind']=='NUMERIC' for j in listed['jobs'])
            partial_state=await tool(client,'inspect_export_job',directory='partial')
            interrupted=(await client.call_tool('recover_export_job',{'params':{'directory':'partial','expected_job':partial_state['job_sha256']},'wait':True})).data
            assert interrupted['record']['state']=='interrupted'
            preview=(await client.call_tool('cleanup_export_job',{'params':{'directory':'partial','expected_job':interrupted['job_sha256']},'wait':True})).data
            assert preview['dry_run'] and preview['bytes']==7
            removed=(await client.call_tool('cleanup_export_job',{'params':{'directory':'partial','expected_job':interrupted['job_sha256'],'dry_run':False},'wait':True})).data
            assert not removed['dry_run'] and not (await tool(client,'inspect_export_job',directory='partial'))['stage_exists']
            assert not (await client.call_tool('bridge_status')).data['bridge']['connected']
    try:asyncio.run(run())
    finally:
        if Path(config.bridge.socket_path).exists():call(config.bridge.socket_path,'shutdown',timeout=5)
