"""Explicit profiles, guarded worker overrides and repeated native images via MCP."""
import asyncio,json,os,shutil,subprocess
from copy import deepcopy
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait
from test_render_batches import drain_owned_renders
from mcpblender import exr_scanline,render_sampling


def test_sampling_profile_guarded_batch_witnesses_and_saved_controls(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await wait(client,'create_primitive',name='SamplingCube')
            await wait(client,'setup_preview_stage',objects=['SamplingCube'],prefix='SamplingView')
            await wait(client,'configure_render',engine='CYCLES')
            before=await wait(client,'inspect_render_sampling')
            assert 'AUTOMATIC' in before['choices']['sampling_pattern']
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'configure_render_sampling',expected_sampling='0'*64,settings={'seed':0})
            with pytest.raises(ToolError,match='before master'):
                await wait(client,'configure_render_sampling',expected_sampling=before['sampling_sha256'],settings={'use_sample_subset':True,'sample_offset':before['settings']['samples']})
            assert (await wait(client,'inspect_render_sampling'))['sampling_sha256']==before['sampling_sha256']
            settings={'samples':64,'sampling_pattern':'AUTOMATIC','seed':0,'use_animated_seed':False,'use_adaptive_sampling':False,'use_denoising':False,'use_layer_samples':'IGNORE','pixel_filter_type':'BLACKMAN_HARRIS','filter_width':1.5,'use_sample_subset':False,'sample_offset':0,'sample_subset_length':64,'time_limit':0.,'max_bounces':12,'diffuse_bounces':4,'glossy_bounces':4,'transmission_bounces':12,'volume_bounces':0,'transparent_max_bounces':8}
            configured=await wait(client,'configure_render_sampling',expected_sampling=before['sampling_sha256'],settings=settings)
            for key,value in settings.items():assert configured['settings'][key]==value
            await client.call_tool('save_blend',{'path':'sampling.blend'})
            (root/'expected-sampling.json').write_text(json.dumps(configured['settings']))
            helper=Path(__file__).with_name('native_render_sampling.py')
            native=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(helper),'--',str(helper.resolve().parents[1]),str(root/'library/sampling.blend'),str(root/'expected-sampling.json')],capture_output=True,text=True,timeout=45)
            assert native.returncode==0,native.stdout+native.stderr
            pipeline=await wait(client,'inspect_render_pipeline')
            batch={'directory':'sampling-job','expected_settings':pipeline['settings_sha256'],'expected_sampling':configured['sampling_sha256'],'cameras':['SamplingView_Camera'],'frame_start':1,'frame_end':2,'width':32,'height':32,'samples':8,'threads':2,'formats':['PNG','OPEN_EXR_MULTILAYER']}
            result=await wait(client,'render_camera_batch',**batch)
            assert result['valid']
            validated=await wait(client,'validate_render_job',directory='sampling-job')
            assert len(validated['sampling_profiles'])==1 and len(validated['outputs'])==4
            profile=next(iter(validated['sampling_profiles'].values()))
            assert profile['settings']==configured['settings']|{'samples':8}
            assert profile['execution']=={'device':'CPU','threads_mode':'FIXED','threads':2}
            assert (await wait(client,'inspect_render_sampling'))['sampling_sha256']==configured['sampling_sha256']
            frames=[v for v in validated['outputs'] if v['format']=='OPEN_EXR_MULTILAYER'];channels=[pipeline['layers'][0]['name']+'.Combined.'+c for c in 'RGBA']
            decoded=[exr_scanline.decode(root/'library/sampling-job'/v['file'],channels)['channels'] for v in frames]
            assert decoded[0]==decoded[1],'Fixed seed/static scene changed across frames'
            bundle=root/'library/sampling-job';original=(bundle/'manifest.json').read_bytes();manifest=json.loads(original);tampered=deepcopy(profile);tampered['settings']['seed']=99
            changed=render_sampling.record(tampered['engine'],tampered['settings'],tampered['layers'],tampered['animated_fields'],tampered['execution'])
            manifest['sampling_profiles']={changed['sampling_sha256']:changed}
            for row in manifest['outputs']:row['sampling_sha256']=changed['sampling_sha256']
            (bundle/'manifest.json').write_text(json.dumps(manifest))
            try:
                with pytest.raises(ToolError,match='binding'):await wait(client,'validate_render_job',directory='sampling-job')
            finally:(bundle/'manifest.json').write_bytes(original)
            updated=await wait(client,'configure_render_sampling',expected_sampling=configured['sampling_sha256'],settings={'seed':1})
            assert updated['sampling_sha256']!=configured['sampling_sha256']
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'render_camera_batch',**(batch|{'directory':'stale-sampling'}))
            assert not (root/'library/stale-sampling').exists()
            subset=await wait(client,'configure_render_sampling',expected_sampling=updated['sampling_sha256'],settings={'use_sample_subset':True,'sample_offset':16,'sample_subset_length':8})
            with pytest.raises(ToolError,match='subset'):
                await wait(client,'render_camera_batch',**(batch|{'directory':'empty-subset','expected_sampling':subset['sampling_sha256']}))
            assert not (root/'library/empty-subset').exists()
            if destination:=os.environ.get('MCPBLENDER_SAMPLING_EVIDENCE'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True);shutil.copytree(bundle,out/'job',dirs_exist_ok=True);shutil.copy2(root/'library/sampling.blend',out/'sampling.blend');assert (out/'sampling.blend').read_bytes()==(root/'library/sampling.blend').read_bytes();(out/'native.log').write_text(native.stdout+native.stderr);(out/'proof.json').write_text(json.dumps({'configured':configured,'validated':validated},indent=2))
    asyncio.run(run())
