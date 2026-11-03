"""Independent camera batches, pass files and concurrent editing via structured MCP."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import time
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark

@pytest.fixture(autouse=True)
def drain_owned_renders(assets_live):
    yield
    async def drain():
        async with client_for(assets_live[1]) as client:
            rows=(await client.call_tool('list_operations')).data['operations']
            for row in rows:
                if row['command']=='render_camera_batch' and row['state'] in {'queued','running'}:
                    await client.call_tool('cancel_operation',{'operation_id':row['operation_id']})
                    await client.call_tool('wait_operation',{'operation_id':row['operation_id'],'timeout_seconds':30})
    asyncio.run(drain())


async def start(client,directory,**patch):
    state=await tool(client,'inspect_render_pipeline')
    return (await client.call_tool('render_camera_batch',{'params':{'directory':directory,'expected_settings':state['settings_sha256'],'cameras':['BatchView_Camera'],'frame_start':1,'frame_end':1,'width':64,'height':64,'samples':4,**patch}})).data

async def wait_handoff(client,op):
    for _ in range(200):
        value=(await client.call_tool('get_operation',{'operation_id':op['operation_id']})).data
        if value.get('progress',{}).get('render_job_id') or value['state'] in {'succeeded','failed','cancelled','interrupted'}:return value
        await asyncio.sleep(.1)
    raise AssertionError('No render handoff')


def test_camera_batch_exr_render_and_live_editing(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_primitive',name='BatchObject',kind='UV_SPHERE',location=[4,0,2])
            from test_shaders import png
            (root/'library').mkdir(exist_ok=True)
            png(root/'library/batch-checker.png',lambda x,y:(40,110,180) if (x//4+y//4)%2 else (180,90,30))
            await tool(client,'apply_material_preset',material='BatchPaint',preset='TEXTURED_PBR',base_color_texture='batch-checker.png')
            shader_before=await tool(client,'inspect_shader_graph',material='BatchPaint')
            await tool(client,'assign_material',objects=['BatchObject'],material='BatchPaint')
            await tool(client,'set_keyframes',name='BatchObject',data_path='location',keyframes=[{'frame':1,'value':[4,0,2]},{'frame':2,'value':[4.5,0,2]}])
            await tool(client,'setup_preview_stage',objects=['BatchObject'],prefix='BatchView')
            await tool(client,'duplicate_object',name='BatchView_Camera',new_name='SecondCamera',offset=[.2,0,0])
            await tool(client,'configure_render',engine='CYCLES')
            state=await tool(client,'inspect_render_pipeline')
            await tool(client,'configure_render_passes',expected_settings=state['settings_sha256'],passes={'z':True,'normal':True})
            from test_compositing import spec
            fx=await tool(client,'configure_compositor_graph',**spec('BatchPost',exposure=.5))
            pipeline=await tool(client,'inspect_render_pipeline')
            await tool(client,'configure_compositing',expected_settings=pipeline['settings_sha256'],group='BatchPost',expected_graph=fx['graph_sha256'])
            pipeline=await tool(client,'inspect_render_pipeline')
            original=(await client.call_tool('get_scene_info')).data
            op=await start(client,'camera-batch',cameras=['BatchView_Camera','SecondCamera'],frame_end=2,formats=['PNG','OPEN_EXR_MULTILAYER'])
            handed=await wait_handoff(client,op);assert handed['state'] not in {'failed','interrupted'},handed
            # This must complete before a longer batch, proving the bridge is free.
            await tool(client,'create_primitive',name='EditedWhileRendering',location=[30,0,0])
            done=(await client.call_tool('wait_operation',{'operation_id':op['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded',done
            checked=await tool(client,'validate_render_job',directory='camera-batch')
            assert checked['valid'] and len(checked['outputs'])==8
            pngs=[i for i in checked['outputs'] if i['camera_index']==0 and i['format']=='PNG']
            assert pngs[0]['sha256']!=pngs[1]['sha256']
            assert (await tool(client,'inspect_render_pipeline'))['settings_sha256']==pipeline['settings_sha256']
            shader_after=await tool(client,'inspect_shader_graph',material='BatchPaint')
            assert {k:v for k,v in shader_after.items() if k!='operation_id'}=={k:v for k,v in shader_before.items() if k!='operation_id'}
            exr=next(i for i in checked['outputs'] if i['format']=='OPEN_EXR_MULTILAYER')
            channels={c['name'] for c in exr['header']['channels']}
            assert any('Depth' in c for c in channels) and any('Normal' in c for c in channels),channels
            current=(await client.call_tool('get_scene_info')).data
            assert current['frame']==original['frame'] and current['camera']==original['camera'] and current['filepath']==original['filepath']
            import subprocess
            code="import bpy\nwith bpy.data.libraries.load("+repr(str(root/'library/camera-batch/source.blend'))+") as (source,target):\n assert 'BatchObject' in source.objects and 'EditedWhileRendering' not in source.objects\n"
            probe=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python-expr',code],capture_output=True,text=True,timeout=30)
            assert probe.returncode==0,probe.stdout+probe.stderr
            assert 'EditedWhileRendering' in {o['name'] for o in (await client.call_tool('get_scene_info')).data['objects']}
            state=await tool(client,'inspect_render_job',directory='camera-batch');assert state['status']['state']=='succeeded' and not state['writer_alive']
            with pytest.raises(ToolError,match='success is protected'):
                await tool(client,'cleanup_render_job',directory='camera-batch',expected_job=state['job_sha256'],dry_run=False)
            if destination:=os.environ.get('MCPBLENDER_RENDER_EVIDENCE_DIR'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True);shutil.copytree(root/'library/camera-batch',out/'camera-batch',dirs_exist_ok=True)
                (out/'proof.json').write_text(json.dumps({'operation':done,'validation':checked},indent=2))
    asyncio.run(run())


def test_render_cancellation_and_broker_restart(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            op=await start(client,'cancel-batch',frame_end=40,samples=64,width=128,height=128)
            handed=await wait_handoff(client,op);assert handed['state']=='running',handed
            assert (await client.call_tool('get_operation',{'operation_id':op['operation_id']})).data['storage']['free_bytes']>0
            second=await start(client,'second-batch',frame_end=40,samples=64,width=128,height=128)
            assert (await wait_handoff(client,second))['state']=='running'
            third=await start(client,'third-batch',frame_end=40,samples=64,width=128,height=128)
            refused=(await client.call_tool('wait_operation',{'operation_id':third['operation_id'],'timeout_seconds':30})).data
            assert refused['state']=='failed' and 'Two independent render workers' in refused['error'],refused
            assert not (root/'library/third-batch').exists()
            await client.call_tool('restart_bridge')
            # No render is replayed; the independent worker remains observable.
            fresh=(await client.call_tool('get_operation',{'operation_id':op['operation_id']})).data
            assert fresh['state']=='running',fresh
            await tool(client,'create_primitive',name='DuringLongRender',location=[40,0,0])
            await client.call_tool('cancel_operation',{'operation_id':op['operation_id']})
            done=(await client.call_tool('wait_operation',{'operation_id':op['operation_id'],'timeout_seconds':30})).data
            assert done['state']=='cancelled',done
            state=await tool(client,'inspect_render_job',directory='cancel-batch');assert not state['writer_alive']
            dry=await tool(client,'cleanup_render_job',directory='cancel-batch',expected_job=state['job_sha256']);assert dry['dry_run']
            await tool(client,'cleanup_render_job',directory='cancel-batch',expected_job=state['job_sha256'],dry_run=False)
            assert not (root/'library/cancel-batch').exists()
            await client.call_tool('cancel_operation',{'operation_id':second['operation_id']})
            stopped=(await client.call_tool('wait_operation',{'operation_id':second['operation_id'],'timeout_seconds':30})).data
            assert stopped['state']=='cancelled',stopped
            state=await tool(client,'inspect_render_job',directory='second-batch')
            await tool(client,'cleanup_render_job',directory='second-batch',expected_job=state['job_sha256'],dry_run=False)
    asyncio.run(run())


def test_renderer_survives_editor_shutdown_and_crash_reconciles_without_replay(assets_live):
    import signal
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            op=await start(client,'crashed-batch',frame_end=100,samples=64,width=128,height=128)
            value=await wait_handoff(client,op);assert value['state']=='running',value
            # Capture only this fixture-owned render worker's reported identity.
            pid=value['progress']['worker_pid']
            await client.call_tool('shutdown_blender',{'params':{'discard_unsaved':True},'wait':True})
            value=(await client.call_tool('get_operation',{'operation_id':op['operation_id']})).data
            assert value['state']=='running',value
            state=await tool(client,'inspect_render_job',directory='crashed-batch');assert state['writer_alive']
            os.kill(pid,signal.SIGKILL)
            done=(await client.call_tool('wait_operation',{'operation_id':op['operation_id'],'timeout_seconds':30})).data
            assert done['state']=='interrupted',done
            state=await tool(client,'inspect_render_job',directory='crashed-batch');assert not state['writer_alive']
            recovered=await tool(client,'recover_render_job',directory='crashed-batch',expected_job=state['job_sha256'])
            assert recovered['status']['state']=='interrupted' and not recovered['replayed']
            await tool(client,'cleanup_render_job',directory='crashed-batch',expected_job=recovered['job_sha256'],include_interrupted=True,dry_run=False)
            assert not (root/'library/crashed-batch').exists()
    asyncio.run(run())
