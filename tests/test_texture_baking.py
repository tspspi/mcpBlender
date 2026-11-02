"""Real high-to-low PBR maps and durable/cancellable isolated baking jobs."""
import asyncio
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest
from fastmcp.exceptions import ToolError

from mcpblender.texture_files import read_json,write_json,MARKER
from test_asset_editing import assets_live,client_for,tool,pytestmark


async def source_scene(client):
    await tool(client,'create_primitive',name='BakeLow',kind='PLANE')
    n=17
    vertices=[(x/(n-1)*2-1,y/(n-1)*2-1,.15+.2*(abs(x/(n-1)*2-1)+abs(y/(n-1)*2-1))+.06*math.cos(x)*math.cos(y)) for y in range(n) for x in range(n)]
    faces=[(y*n+x,y*n+x+1,(y+1)*n+x+1,(y+1)*n+x) for y in range(n-1) for x in range(n-1)]
    await tool(client,'create_mesh',name='BakeHigh',vertices=vertices,faces=faces)
    await tool(client,'apply_material_preset',material='BakeSource',base_color=[.6,.1,.02,1],roughness=.3,metallic=.7)
    await tool(client,'configure_shader_node',material='BakeSource',node={'name':'Checker','type':'ShaderNodeTexChecker','inputs':[{'socket':'Color1','value':[.8,.02,.01,1]},{'socket':'Color2','value':[.01,.04,.8,1]},{'socket':'Scale','value':4}]})
    await tool(client,'connect_shader_nodes',material='BakeSource',links=[{'from_node':'Checker','from_socket':'Color','to_node':'Surface','to_socket':'Base Color'}])
    await tool(client,'configure_shader_node',material='BakeSource',node={'name':'Surface','type':'ShaderNodeBsdfPrincipled','inputs':[{'socket':'Alpha','value':.8},{'socket':'Emission Color','value':[.04,.01,0,1]}]})
    await tool(client,'assign_material',objects=['BakeHigh'],material='BakeSource')


async def inspect(client,**kw):
    return await tool(client,'inspect_texture_bake',name='BakeLow',sources=['BakeHigh'],**kw)


def test_high_low_maps_reopen_glb_and_binding(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await source_scene(client)
            info=await inspect(client);assert info['complete'],info
            with pytest.raises(ToolError,match='stale'):
                await client.call_tool('bake_textures',{'params':{'name':'BakeLow','sources':['BakeHigh'],'expected_bake':'0'*64,'directory':'stale'},'wait':True})
            with pytest.raises(ToolError,match='estimate'):
                await client.call_tool('bake_textures',{'params':{'name':'BakeLow','sources':['BakeHigh'],'expected_bake':info['bake_sha256'],'directory':'small','max_bytes':1024**2},'wait':True})
            assert not (root/'library/small').exists()
            before=(await client.call_tool('get_scene_info')).data
            try:
                result=(await client.call_tool('bake_textures',{'params':{'name':'BakeLow','sources':['BakeHigh'],'expected_bake':info['bake_sha256'],'directory':'baked','width':96,'height':96,'samples':16,'margin':2,'cage_extrusion':.8,'max_ray_distance':2,'maps':['NORMAL','AO','BASE_COLOR','ROUGHNESS','METALLIC','EMISSION','ALPHA']},'wait':True})).data
            except ToolError:
                pytest.fail((root/'library/baked/worker.log').read_text()[-18000:])
            assert result['live_scene_unchanged']
            assert (await client.call_tool('get_scene_info')).data['filepath']==before['filepath']
            assert (await inspect(client))['bake_sha256']==info['bake_sha256']
            bundle=root/'library/baked';saved=read_json(bundle/'manifest.json');maps={m['map']:m for m in saved['maps']}
            if dest:=os.environ.get('MCPBLENDER_TEXTURE_EVIDENCE_DIR'):
                target=Path(dest);target.mkdir(parents=True,exist_ok=True);shutil.copytree(bundle,target/'baked',dirs_exist_ok=True)
            assert saved['projection']['fraction']>.99
            assert set(maps)=={'NORMAL','AO','BASE_COLOR','ROUGHNESS','METALLIC','EMISSION','ALPHA'}
            assert maps['NORMAL']['statistics']['max'][0]-maps['NORMAL']['statistics']['min'][0]>.2
            assert maps['AO']['statistics']['min'][0]<.95 and maps['AO']['statistics']['max'][0]>.9
            assert all(maps['BASE_COLOR']['statistics']['max'][c]-maps['BASE_COLOR']['statistics']['min'][c]>.4 for c in (0,2))
            for kind,value in (('ROUGHNESS',.3),('METALLIC',.7),('ALPHA',.8)):
                assert maps[kind]['statistics']['mean'][0]==pytest.approx(value,abs=.02),maps[kind]
            await client.call_tool('open_blend',{'path':'baked/asset.blend'})
            assert (await tool(client,'validate_texture_bake',directory='baked'))['validated']
            await tool(client,'configure_shader_node',material=result['material'],node={'name':'Surface','type':'ShaderNodeBsdfPrincipled','label':'Baked surface'})
            assert (await tool(client,'validate_texture_bake',directory='baked'))['validated']
            await tool(client,'export_objects_glb',objects=['BakeLow'],path='baked-pbr.glb')
            raw=(root/'library/baked-pbr.glb').read_bytes();length=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+length])
            material=gltf['materials'][0]
            assert {'baseColorTexture','metallicRoughnessTexture'}<=material['pbrMetallicRoughness'].keys(),material
            assert 'normalTexture' in material and 'occlusionTexture' in material and 'emissiveTexture' in material,material
            assert gltf['images'] and all('bufferView' in i for i in gltf['images'])
            await client.call_tool('run_action',{'action':'preview_setup','inputs':{'objects':['BakeLow'],'prefix':'BakedView'},'wait':True})
            q=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':'baked-pbr.png','width':256,'height':192,'camera':'BakedView_Camera','engine':'CYCLES'}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':q['operation_id'],'timeout_seconds':60})).data
            assert done['state']=='succeeded',done
            rgb=subprocess.run(['ffmpeg','-v','error','-i',str(root/'library/baked-pbr.png'),'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True,timeout=20).stdout
            pixels=list(zip(rgb[0::3],rgb[1::3],rgb[2::3]))
            assert len(pixels)==256*192
            assert sum(r>b+30 for r,g,b in pixels)>200
            assert sum(b>r+30 for r,g,b in pixels)>200
            # Mutations invalidate the native asset even with untouched files.
            await client.call_tool('set_object_transform',{'name':'BakeLow','scale':[2,1,1]})
            with pytest.raises(ToolError,match='binding'):await tool(client,'validate_texture_bake',directory='baked')
            await client.call_tool('open_blend',{'path':'baked/asset.blend'})
            relocated=root/'library/relocated';shutil.copytree(bundle,relocated)
            await client.call_tool('open_blend',{'path':'relocated/asset.blend'})
            assert (await tool(client,'validate_texture_bake',directory='relocated'))['validated']
            with pytest.raises(ToolError,match='protected'):await tool(client,'cleanup_texture_job',directory='relocated',dry_run=False)
            image=relocated/'textures/normal.png';data=image.read_bytes();image.write_bytes(data+b'corrupt')
            with pytest.raises(ToolError,match='changed'):await tool(client,'validate_texture_bake',directory='relocated')
            if dest:=os.environ.get('MCPBLENDER_TEXTURE_EVIDENCE_DIR'):
                target=Path(dest);target.mkdir(parents=True,exist_ok=True);shutil.copytree(bundle,target/'baked',dirs_exist_ok=True)
                for name in ('baked-pbr.png','baked-pbr.glb'):shutil.copy2(root/'library'/name,target/name)
    asyncio.run(run())


async def open_source(client,root):
    if (root/'library/baked/source.blend').exists():await client.call_tool('open_blend',{'path':'baked/source.blend'})
    else:await source_scene(client)


async def start_long_bake(client,directory):
    info=await inspect(client);assert info['complete'],info
    payload={'params':{'name':'BakeLow','sources':['BakeHigh'],'expected_bake':info['bake_sha256'],'directory':directory,'width':1024,'height':1024,'samples':256,'maps':['AO'],'cage_extrusion':.8,'max_ray_distance':2},'request_id':directory,'wait':False}
    q=(await client.call_tool('bake_textures',payload)).data
    import time
    deadline=time.monotonic()+80
    while time.monotonic()<deadline:
        status=(await client.call_tool('get_operation',{'operation_id':q['operation_id']})).data
        assert status['state'] in {'running','queued'},status
        progress=status.get('progress') or {}
        if progress.get('phase')=='baking texture map':return q,payload,progress
        await asyncio.sleep(.1)
    pytest.fail('Texture worker never reached actual map baking: '+str(status))


def test_worker_cancel_reconnect_cleanup_and_completed_adoption(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            await open_source(client,root)
            q,payload,progress=await start_long_bake(client,'cancelled-textures')
            assert progress['storage']['free_bytes']>0 and progress['storage']['estimated_output_bytes']>0
            worker=progress['worker_pid'];os.kill(worker,0)
            parent=(await client.call_tool('bridge_status')).data['bridge']['pid']
            assert (await client.call_tool('restart_bridge')).data['pid']==parent
            await client.call_tool('cancel_operation',{'operation_id':q['operation_id']})
            done=(await client.call_tool('wait_operation',{'operation_id':q['operation_id'],'timeout_seconds':30})).data
            assert done['state']=='cancelled',done
            with pytest.raises(ProcessLookupError):os.kill(worker,0)
            repeated=(await client.call_tool('bake_textures',payload)).data
            assert repeated['operation_id']==q['operation_id'] and repeated['state']=='cancelled'
            job=await tool(client,'inspect_texture_job',directory='cancelled-textures')
            assert job['record']['state']=='cancelled' and not job['worker_alive']
            preview=await tool(client,'cleanup_texture_job',directory='cancelled-textures')
            assert preview['dry_run'] and preview['bytes']>0
            await client.call_tool('open_blend',{'path':'cancelled-textures/source.blend'})
            with pytest.raises(ToolError,match='references'):await tool(client,'cleanup_texture_job',directory='cancelled-textures',dry_run=False)
            await open_source(client,root)
            unknown=root/'library/cancelled-textures/preserve.txt';unknown.write_text('user data')
            with pytest.raises(ToolError,match='Unknown'):await tool(client,'cleanup_texture_job',directory='cancelled-textures',dry_run=False)
            assert unknown.read_text()=='user data';unknown.unlink()
            await tool(client,'cleanup_texture_job',directory='cancelled-textures',dry_run=False)
            assert not (root/'library/cancelled-textures').exists()
            if (root/'library/baked').exists():
                adopted=root/'library/adopted';shutil.copytree(root/'library/baked',adopted)
                record=read_json(adopted/MARKER);record['state']='running';write_json(adopted/MARKER,record)
                with pytest.raises(ToolError,match='alive'):await tool(client,'recover_texture_job',directory='adopted')
                # Model the post-worker/pre-publication crash window using genuine
                # complete outputs and the actual departed worker PID.
                record['parent_pid']=record['worker_pid'];write_json(adopted/MARKER,record)
                recovered=await tool(client,'recover_texture_job',directory='adopted')
                assert recovered['reconciled'] and not recovered['replayed'] and recovered['native_validation_required']
                await client.call_tool('open_blend',{'path':'adopted/asset.blend'})
                assert (await tool(client,'validate_texture_bake',directory='adopted'))['validated']
    asyncio.run(run())



def test_custom_cage_self_bake_and_missed_projection(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            await open_source(client,root)
            await tool(client,'create_primitive',name='BakeCage',kind='PLANE',location=[0,0,.9])
            info=await inspect(client,cage='BakeCage');assert info['complete'],info
            result=(await client.call_tool('bake_textures',{'params':{'name':'BakeLow','sources':['BakeHigh'],'cage':'BakeCage','expected_bake':info['bake_sha256'],'directory':'custom-cage','maps':['NORMAL'],'width':32,'height':32,'samples':4,'cage_extrusion':0},'wait':True})).data
            assert result['maps'][0]['map']=='NORMAL'
            assert read_json(root/'library/custom-cage/manifest.json')['projection']['fraction']>.99
            info=await inspect(client)
            with pytest.raises(ToolError,match='exited'):
                await client.call_tool('bake_textures',{'params':{'name':'BakeLow','sources':['BakeHigh'],'expected_bake':info['bake_sha256'],'directory':'missed-projection','maps':['NORMAL'],'width':32,'height':32,'samples':4,'cage_extrusion':0,'max_ray_distance':.001},'wait':True})
            failed=await tool(client,'inspect_texture_job',directory='missed-projection')
            assert failed['record']['state']=='failed'
            assert 'Projection coverage' in (root/'library/missed-projection/worker.log').read_text()
            await tool(client,'create_primitive',name='SelfBake',kind='PLANE',location=[3,0,0])
            from test_shaders import png
            png(root/'library/input.png',lambda x,y:(230,20,10) if x<8 else (10,20,230))
            await tool(client,'apply_material_preset',material='PackedSource',preset='TEXTURED_PBR',base_color_texture='input.png')
            await tool(client,'configure_shader_node',material='PackedSource',node={'name':'Surface','type':'ShaderNodeBsdfPrincipled','inputs':[{'socket':'Alpha','value':.8}]})
            await tool(client,'assign_material',objects=['SelfBake'],material='PackedSource')
            own=await tool(client,'inspect_texture_bake',name='SelfBake');assert own['complete'],own
            await client.call_tool('bake_textures',{'params':{'name':'SelfBake','expected_bake':own['bake_sha256'],'directory':'self-bake','maps':['NORMAL','AO','ALPHA','BASE_COLOR'],'width':32,'height':32,'samples':4},'wait':True})
            maps={v['map']:v for v in read_json(root/'library/self-bake/manifest.json')['maps']}
            assert maps['NORMAL']['statistics']['mean'][0]==pytest.approx(.5,abs=.01)
            assert maps['NORMAL']['statistics']['mean'][2]>.99
            assert maps['AO']['statistics']['mean'][0]>.99
            assert maps['ALPHA']['statistics']['mean'][0]==pytest.approx(.8,abs=.01)
            assert maps['BASE_COLOR']['statistics']['max'][0]-maps['BASE_COLOR']['statistics']['min'][0]>.5
    asyncio.run(run())


def test_parent_crash_stops_worker_and_preserves_interrupted_bundle(assets_live):
    import signal
    from mcpblender.broker import process_alive
    from mcpblender.config import Config,write_config
    from mcpblender.launcher import Launcher
    from mcpblender.wire import call
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            await open_source(client,root)
            q,_,progress=await start_long_bake(client,'interrupted-textures')
            worker=progress['worker_pid'];parent=(await client.call_tool('bridge_status')).data['bridge']['pid']
            os.kill(parent,signal.SIGKILL)
            for _ in range(300):
                status=(await client.call_tool('get_operation',{'operation_id':q['operation_id']})).data
                if status['state']=='interrupted' and not process_alive(worker):break
                await asyncio.sleep(.1)
            assert status['state']=='interrupted' and status['outcome_unknown'],status
            assert not process_alive(worker),'Owned bake child must stop after parent death'
            assert read_json(root/'library/interrupted-textures'/MARKER)['state']=='running'
        config=Config.model_validate_json(path.read_text());config.bridge.socket_path=str(root/'texture-recovery/bridge.sock');config.launch.log_path=str(root/'texture-recovery.log')
        fresh=root/'texture-recovery.json';write_config(fresh,config);launcher=Launcher(config)
        try:
            launcher.start()
            async with client_for(fresh) as other:
                recovered=await tool(other,'recover_texture_job',directory='interrupted-textures')
                assert recovered['reconciled'] and not recovered['replayed'] and recovered['record']['state']=='interrupted'
                with pytest.raises(ToolError,match='interrupted'):await tool(other,'cleanup_texture_job',directory='interrupted-textures',dry_run=False)
                preview=await tool(other,'cleanup_texture_job',directory='interrupted-textures',include_interrupted=True)
                assert preview['dry_run'] and preview['bytes']>0
                await tool(other,'cleanup_texture_job',directory='interrupted-textures',dry_run=False,include_interrupted=True)
                assert not (root/'library/interrupted-textures').exists()
        finally:
            if launcher.process and launcher.process.poll() is None:launcher.process.terminate();launcher.process.wait(timeout=15)
            call(config.bridge.socket_path,'shutdown',timeout=5)
    asyncio.run(run())
