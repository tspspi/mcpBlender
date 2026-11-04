"""Full-map, all-role quality delivery and material previews through MCP."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import time

from fastmcp.exceptions import ToolError
from mcpblender import texture_files
from test_asset_editing import assets_live,client_for,tool,pytestmark


def test_full_quality_textures_delivery_and_previews(assets_live):
    root,path=assets_live;library=root/'library'
    evidence=Path(os.environ['MCPBLENDER_FULL_QUALITY_EVIDENCE_DIR']) if os.environ.get('MCPBLENDER_FULL_QUALITY_EVIDENCE_DIR') else None
    if evidence:evidence.mkdir(parents=True,exist_ok=True)
    resume=Path(os.environ['MCPBLENDER_FULL_QUALITY_RESUME_DIR']) if os.environ.get('MCPBLENDER_FULL_QUALITY_RESUME_DIR') else None
    if resume:shutil.copytree(resume,library,dirs_exist_ok=True)
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            assert (await client.call_tool('bridge_status')).data['bridge']['pid']>0
            scene=(await client.call_tool('get_scene_info')).data
            if any(o['name']=='Cube' for o in scene['objects']):
                visibility=await tool(client,'inspect_render_visibility',name='Cube')
                await tool(client,'configure_render_visibility',name='Cube',expected_visibility=visibility['visibility_sha256'],hide_render=True)
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data
                deadline=time.monotonic()+3600
                while True:
                    try:
                        state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':15})).data
                    except ToolError as exc:
                        if not any(message in str(exc) for message in ('Bridge timed out;','Bridge disconnected before a complete response')):raise
                        assert time.monotonic()<deadline,'Bounded test observation deadline exceeded'
                        if evidence:
                            with (evidence/'observations.jsonl').open('a') as stream:stream.write(json.dumps({'operation_id':queued['operation_id'],'observation_error':str(exc)})+'\n')
                        await asyncio.sleep(1)
                        continue
                    progress=state.get('progress') or {}
                    trace={'command':command,'operation_id':queued['operation_id'],'state':state['state'],'phase':progress.get('phase'),'map':progress.get('map'),'asset':progress.get('asset'),'storage':progress.get('storage') or state.get('storage'),'error':state.get('error')}
                    if evidence:
                        (evidence/'latest-operation.json').write_text(json.dumps(trace,indent=2))
                        with (evidence/'operations.jsonl').open('a') as stream:stream.write(json.dumps(trace)+'\n')
                    assert state['state'] not in {'failed','cancelled','interrupted'},state
                    if state['state']=='succeeded':return state['result']|{'operation_id':queued['operation_id']}
                    assert time.monotonic()<deadline,'Bounded test operation deadline exceeded'
            if resume:
                await client.call_tool('open_blend',{'path':'prepared.blend'})
                profile=await operation('inspect_botanical_lods',lod_collection='Lods')
                prep=await operation('inspect_vegetation_bake',bake_collection='Prepared')
                assert profile['valid'] and prep['valid'] and len(prep['components'])==11
            else:
                recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
                plan=await operation('plan_botanical_tree',recipe=recipe)
                tree=await operation('create_botanical_tree',collection='Source',recipe=recipe,expected_model=plan['model_sha256'])
                cfg={'shoots_per_bud':2,'attachment_nodes':5,'variants':3}
                plan=await operation('plan_botanical_foliage',collection='Source',foliage=cfg)
                tree=await operation('configure_botanical_foliage',collection='Source',foliage=cfg,expected_tree=tree['tree_sha256'],expected_foliage=plan['foliage_sha256'])
                for row in (await tool(client,'inspect_vegetation_materials',collection='Source'))['contract']['materials']:
                    mat=await tool(client,'inspect_botanical_surface',material=row['name'])
                    await operation('configure_botanical_surface',material=row['name'],settings={'profile':'OAK_LEAF' if row['model']=='MANAGED_THIN_FOLIAGE' else 'OAK_BARK'},expected_material=mat['material_sha256'])
                args={'collection':'Source','levels':[{'leaf_budget':70,'radial_sides':6},{'leaf_budget':35,'radial_sides':5,'max_coverage_loss':.6,'max_silhouette_loss':.6},{'leaf_budget':20,'radial_sides':5,'max_coverage_loss':.75,'max_silhouette_loss':.75}]}
                plan=await operation('inspect_botanical_lod_source',**args)
                profile=await operation('create_botanical_lods',**args,lod_collection='Lods',expected_plan=plan['plan_sha256'])
                await operation('remove_botanical_tree',collection='Source',expected_tree=tree['tree_sha256'])
                args={'lod_collection':'Lods','missing_uv_policy':'BAKE_LAYOUT','texture_width':1024,'texture_height':1024,'tile_padding_pixels':8,'chart_layout':{'allow_stretch':True}}
                plan=await operation('inspect_vegetation_bake_source',**args)
                prep=await operation('prepare_vegetation_bake',**args,expected_plan=plan['plan_sha256'],bake_collection='Prepared')
                assert len(prep['components'])==11
                await client.call_tool('save_blend',{'path':'prepared.blend'})
            policy={'width':1024,'height':1024,'min_texels_per_meter':32,'min_chart_pixels':4,'padding_pixels':2,'mip_levels':1}
            maps=['BASE_COLOR','NORMAL','AO','ROUGHNESS','METALLIC','EMISSION','ALPHA'];entries=[];proof={}
            for role,row in prep['components'].items():
                if not resume:
                    info=await operation('inspect_texture_bake',**row['inspect_texture_bake'],quality=policy)
                    assert info['complete'],(role,info)
                    result=await operation('bake_textures',**row['inspect_texture_bake'],quality=policy,expected_bake=info['bake_sha256'],directory='bakes/'+role,maps=maps,width=1024,height=1024,samples=4,margin=2)
                    assert result['live_scene_unchanged']
                saved=texture_files.read_json(library/'bakes'/role/'manifest.json')
                assert saved['texture_quality']['passed'] and len(saved['maps'])==7
                assert all(saved['texture_quality']['policy'][k]==v for k,v in policy.items())
                assert texture_files.bake_fingerprint(saved['source_inspection'],without_quality=True)==row['initial_bake_sha256']
                stats={m['map']:m['statistics'] for m in saved['maps']}
                assert max(stats['EMISSION']['max'][:3])==0
                assert max(stats['NORMAL']['max'][i]-stats['NORMAL']['min'][i] for i in (0,1))>.05
                proof[role]={'quality':saved['texture_quality'],'statistics':stats,'source':saved['source']}
                if evidence:(evidence/'bake-proof.json').write_text(json.dumps(proof,indent=2))
                print('BAKED',role,flush=True)
                entries.append({'asset':role,'directory':'bakes/'+role})
            assert (await tool(client,'inspect_vegetation_bake',bake_collection='Prepared'))['preparation_sha256']==prep['preparation_sha256']
            args={'lod_collection':'Lods','bake_collection':'Prepared','entries':entries,'accept_front_pbr':True,'max_bytes':512*1024**2,'max_texture_bytes':384*1024**2}
            plan=await operation('inspect_vegetation_bake_adoption',**args)
            state=await operation('adopt_vegetation_bakes',**args,expected_plan=plan['plan_sha256'])
            options={'lod_collection':'Lods','required_maps':maps,'min_texture_size':1024,'require_quality':True,'max_texture_bytes':384*1024**2,'max_mip_bytes':512*1024**2}
            report=await operation('inspect_vegetation_delivery',**options)
            assert report['complete'] and not report['assets_without_quality_reports'] and not report['quality_scene_unit_gaps']
            assert len(report['quality_policies'])==11 and report['budget']['rgba8_base_bytes']==11*7*1024**2*4
            assert report['budget']['rgba8_full_mip_bytes']==11*7*sum(4*(1024//2**i)**2 for i in range(11))
            assert report['optical_omissions'] and report['sampling_changed_assets']
            (library/'quality-delivery.json').write_text(json.dumps(report,indent=2))
            if evidence:(evidence/'quality-delivery.json').write_text(json.dumps(report,indent=2))
            await operation('remove_vegetation_bake',bake_collection='Prepared',expected_preparation=prep['preparation_sha256'])
            await client.call_tool('save_blend',{'path':'quality-profile.blend'})
            # Macro renders use the independent baked leaf asset, preserving the profile.
            await client.call_tool('open_blend',{'path':'bakes/leaf-0/asset.blend'})
            await tool(client,'configure_render',samples=16,resolution_x=384,resolution_y=384)
            stage=await operation('setup_preview_stage',objects=[prep['components']['leaf-0']['name']],prefix='LeafView',view='TOP',projection='ORTHO',margin=1.1)
            await operation('render_still',path='leaf-normal.png',width=384,height=384,camera='LeafView_Camera',engine='CYCLES')
            saved=texture_files.read_json(library/'bakes/leaf-0/manifest.json')
            await tool(client,'disconnect_shader_input',material=saved['material'],node='Surface',socket='Normal')
            await operation('render_still',path='leaf-flat-normal.png',width=384,height=384,camera='LeafView_Camera',engine='CYCLES')
            assert (library/'leaf-normal.png').read_bytes()!=(library/'leaf-flat-normal.png').read_bytes()
            await client.call_tool('open_blend',{'path':'quality-profile.blend'})
            shutil.rmtree(library/'bakes')
            state=await operation('inspect_botanical_lods',lod_collection='Lods');assert state['valid']
            await tool(client,'configure_render',samples=8,resolution_x=384,resolution_y=384)
            await operation('setup_preview_stage',objects=state['levels'][0]['objects'],prefix='ProfileView',margin=1.15)
            for level in (0,3):
                state=await operation('activate_botanical_lod',lod_collection='Lods',expected_lods=state['lods_sha256'],level=level)
                await operation('render_still',path=f'level-{level}.png',width=384,height=384,camera='ProfileView_Camera',engine='CYCLES')
            state=await operation('activate_botanical_lod',lod_collection='Lods',expected_lods=state['lods_sha256'],level=0)
            await client.call_tool('save_blend',{'path':'quality-profile.blend','overwrite':True})
            await client.call_tool('open_blend',{'path':'quality-profile.blend'})
            report=await operation('inspect_vegetation_delivery',**options);assert report['complete']
            state=await operation('inspect_botanical_lods',lod_collection='Lods')
            exported=await operation('export_botanical_lods',lod_collection='Lods',expected_lods=state['lods_sha256'],directory='delivery')
            assert len(exported['proof']['assets'])==11
            semantics=texture_files.read_json(library/'delivery/semantics.json')
            assert len(semantics['baked_materials'])==11 and all(r['texture_quality']['passed'] for r in semantics['baked_materials'].values())
            if evidence:shutil.copytree(library,evidence/'library',dirs_exist_ok=True)
            await operation('remove_botanical_lods',lod_collection='Lods',expected_lods=state['lods_sha256'])
            assert len((await operation('validate_botanical_lod_bundle',directory='delivery'))['assets'])==11
    try:asyncio.run(run())
    finally:
        if evidence and library.exists():shutil.copytree(library,evidence/'library',dirs_exist_ok=True)
        if evidence:
            for source,name in ((root/'blender.log','blender.log'),(root/'bridge/broker.log','broker.log')):
                if source.exists():shutil.copy2(source,evidence/name)
