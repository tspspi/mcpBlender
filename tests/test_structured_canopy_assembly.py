"""Full-density public MCP assembly and unchanged frozen optical policies."""
import asyncio,json,os,shutil,subprocess,hashlib
from pathlib import Path
import pytest
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait
from test_render_batches import drain_owned_renders
from mcpblender import render_jobs

source=os.environ.get('MCPBLENDER_ASSEMBLY_SOURCE');reference=os.environ.get('MCPBLENDER_ASSEMBLY_REFERENCE');coverage=os.environ.get('MCPBLENDER_ASSEMBLY_COVERAGE');frozen=os.environ.get('MCPBLENDER_ASSEMBLY_FROZEN')
pytestmark=pytestmark+[pytest.mark.skipif(not all((source,reference,coverage,frozen)),reason='Requires retained dense source, component reference, coverage data and frozen native controls')]


def test_structured_full_density_pair_under_all_three_frozen_lights(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(source,library/'source.blend');shutil.copytree(reference,library/'reference');shutil.copytree(coverage,library/'coverage');shutil.copytree(frozen,library/'frozen')
    source_hash=hashlib.sha256(Path(source).read_bytes()).hexdigest()
    out=Path(os.environ['MCPBLENDER_ASSEMBLY_EVIDENCE']) if os.environ.get('MCPBLENDER_ASSEMBLY_EVIDENCE') else None
    if out:out.mkdir(parents=True,exist_ok=True)
    pose_file=root/'poses.json';helper=Path(__file__).with_name('native_frozen_light_poses.py')
    poses=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(helper),'--',str(library/'reference'),str(pose_file)],capture_output=True,text=True,timeout=30)
    assert poses.returncode==0,poses.stdout+poses.stderr
    pose=json.loads(pose_file.read_text());proof={'scope':'Structured public MCP creation/display/environment/camera/light/sampling/render/EXR comparisons. One static FRONT view; not angular, wind, population, mature-reference or reduced-template acceptance.','quality':{},'frozen_controls':{},'jobs':{},'pose':pose}
    def checkpoint():
        if out:(out/'proof.json').write_text(json.dumps(proof,indent=2))
    def retain_job(name,result):
        if not out:return
        job_root=library/name;destination=out/'jobs'/name;shutil.copytree(job_root,destination,dirs_exist_ok=True)
        job=render_jobs.read_json(destination/'job.json');render_jobs.validate_contents(destination,job['job_id'])
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await client.call_tool('open_blend',{'path':'source.blend'})
            initial=await wait(client,'inspect_botanical_tree',collection='Canopy3');assert initial['valid']
            d={'directory':'reference','view':'FRONT','component_filter':'LEAVES','projected_coverage_directory':'coverage','settings':{'geometry_mode':'ADAPTIVE_NORMAL','plane_normal_source':'GEOMETRIC_AOV','tile_pixels':1,'max_slope':64.,'max_triangles':131072}}
            plan=await wait(client,'inspect_botanical_depth_source',**d)
            depth=await wait(client,'create_botanical_depth_asset',**d,collection='QualifiedPrimary',expected_plan=plan['plan_sha256'],accept_approximate_optics=True)
            n={'directory':'reference','views':['FRONT'],'selection':'COLUMN_COMPLEMENT','render_role':'ALL_RAYS'}
            native_plan=await wait(client,'inspect_botanical_subset_source',**n)
            native=await wait(client,'create_botanical_subset',**n,subset_collection='QualifiedComplement',expected_plan=native_plan['plan_sha256'])
            assert native['selected_leaf_count']==88704 and depth['triangles']==109764
            assert native_plan['capture_sha256']==plan['source']['capture_sha256'] and native_plan['snapshot_sha256']==plan['source']['snapshot_sha256']
            assert native_plan['column_complement']['grid_sha256']==plan['projected_coverage']['grid_sha256']
            assert native_plan['column_complement']['view']==plan['source']['view']
            proof['assets']={'depth':depth,'complement':native};checkpoint()
            # Match the isolated reference: factory geometry and lights must not
            # contaminate the native scene. Managed source object flags stay put.
            scene=(await client.call_tool('get_scene_info')).data
            for obj in scene['objects']:
                if obj['name']=='Cube' or obj['type']=='LIGHT':
                    vis=await wait(client,'inspect_render_visibility',name=obj['name'])
                    await wait(client,'configure_render_visibility',name=obj['name'],expected_visibility=vis['visibility_sha256'],hide_render=True)
            view=pose['view']
            cam=await wait(client,'configure_camera',name='QualifiedCamera',location=pose['camera_location'],rotation_euler=pose['camera_rotation_euler'],projection='ORTHO',ortho_scale=view['ortho_scale'],clip_start=view['clip_start'],clip_end=view['clip_end'])
            assert cam['matrix_world']==pose['camera_matrix_evaluated']
            await wait(client,'configure_light',name='QualifiedSun',type='SUN',energy=2.,angle=0.,rotation_euler=pose['sun_front'])
            await wait(client,'configure_render',engine='CYCLES')
            current=await wait(client,'inspect_render_sampling')
            settings={'samples':256,'sampling_pattern':'AUTOMATIC','seed':0,'use_animated_seed':False,'use_adaptive_sampling':False,'use_denoising':False,'use_layer_samples':'IGNORE','pixel_filter_type':'BLACKMAN_HARRIS','filter_width':1.5,'use_sample_subset':False,'sample_offset':0,'sample_subset_length':256,'time_limit':0.,'max_bounces':12,'diffuse_bounces':4,'glossy_bounces':4,'transmission_bounces':12,'volume_bounces':0,'transparent_max_bounces':8}
            sampling=await wait(client,'configure_render_sampling',expected_sampling=current['sampling_sha256'],settings=settings)
            refs=[{'kind':'SOURCE','collection':'Canopy3'},{'kind':'DEPTH','collection':'QualifiedPrimary'},{'kind':'SUBSET','collection':'QualifiedComplement'}]
            for lighting in ('world','sun_front','sun_back'):
                env=await wait(client,'inspect_environment')
                await wait(client,'configure_environment',expected_environment=env['environment_sha256'],settings={'mode':'COLOR','color':[1,1,1],'strength':.5 if lighting=='world' else 0.},film_transparent=True)
                if lighting!='world':await wait(client,'configure_light',name='QualifiedSun',type='SUN',energy=2.,angle=0.,rotation_euler=pose[lighting])
                vis=await wait(client,'inspect_render_visibility',name='QualifiedSun')
                await wait(client,'configure_render_visibility',name='QualifiedSun',expected_visibility=vis['visibility_sha256'],hide_render=lighting=='world')
                for variant in ('native','candidate'):
                    display=await wait(client,'inspect_botanical_display',targets=refs)
                    changes=[ref|{'hide_render':((i!=0) if variant=='native' else (i==0))} for i,ref in enumerate(refs)]
                    await wait(client,'configure_botanical_display',targets=changes,expected_display=display['display_sha256'])
                    pipeline=await wait(client,'inspect_render_pipeline');sampling=await wait(client,'inspect_render_sampling')
                    name=lighting+'-'+variant
                    result=await wait(client,'render_camera_batch',directory=name,expected_settings=pipeline['settings_sha256'],expected_sampling=sampling['sampling_sha256'],cameras=['QualifiedCamera'],frame_start=1,frame_end=1,width=128,height=128,samples=256,threads=2,formats=['OPEN_EXR_MULTILAYER'])
                    assert result['valid'];proof['jobs'][name]=result;retain_job(name,result);checkpoint()
                    if variant=='candidate' and lighting=='world':
                        await client.call_tool('save_blend',{'path':'assembly.blend'})
                        if out:shutil.copy2(library/'assembly.blend',out/'assembly.blend');assert (out/'assembly.blend').read_bytes()==(library/'assembly.blend').read_bytes()
                pass_name=pipeline['layers'][0]['name']+'.Combined'
                frozen_compare=await wait(client,'compare_exr_images',reference='frozen/'+lighting+'-native.exr',candidate=lighting+'-native/outputs/c00_f0000.exr',reference_pass='Occlusion.Combined',candidate_pass=pass_name,scales=[1],quality={'max_premultiplied_rgb_rmse':1e-6,'max_alpha_mae':1e-6})
                proof['frozen_controls'][lighting]=frozen_compare
                compared=await wait(client,'compare_exr_images',reference=lighting+'-native/outputs/c00_f0000.exr',candidate=lighting+'-candidate/outputs/c00_f0000.exr',reference_pass=pass_name,candidate_pass=pass_name,scales=[1,2,4],quality={'max_overlap_rgb_rmse':.05,'max_abs_overlap_luminance_relative_bias':.1})
                proof['quality'][lighting]=compared;checkpoint()
            # Return to source-only display and verify original model/resources.
            display=await wait(client,'inspect_botanical_display',targets=refs)
            await wait(client,'configure_botanical_display',targets=[ref|{'hide_render':i!=0} for i,ref in enumerate(refs)],expected_display=display['display_sha256'])
            assert (await wait(client,'inspect_botanical_subset',subset_collection='QualifiedComplement'))['source_unchanged']
            assert (await wait(client,'inspect_botanical_depth_asset',collection='QualifiedPrimary'))['valid']
            assert set(proof['quality'])==set(proof['frozen_controls'])=={'world','sun_front','sun_back'}
            assert set(proof['jobs'])=={light+'-'+kind for light in ('world','sun_front','sun_back') for kind in ('native','candidate')}
            proof['all_frozen_controls_passed']=all(v['passed'] for v in proof['frozen_controls'].values())
            proof['all_quality_passed']=all(v['passed'] for v in proof['quality'].values());checkpoint()
            assert proof['all_frozen_controls_passed'],{k:v['levels'][0] for k,v in proof['frozen_controls'].items()}
            assert proof['all_quality_passed'],{k:v['levels'][0] for k,v in proof['quality'].items()}
    asyncio.run(run())
    assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==source_hash
