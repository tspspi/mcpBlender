"""All-level, all-template PBR delivery with code execution disabled."""
import asyncio
import json
import os
from pathlib import Path
import shutil
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_complete_four_level_textured_profile(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='Source',recipe=recipe,expected_model=plan['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':5,'variants':3};pop=await wait(client,'plan_botanical_foliage',collection='Source',foliage=cfg)
            tree=await wait(client,'configure_botanical_foliage',collection='Source',foliage=cfg,expected_tree=tree['tree_sha256'],expected_foliage=pop['foliage_sha256'])
            for m in (await tool(client,'inspect_vegetation_materials',collection='Source'))['contract']['materials']:
                state=await tool(client,'inspect_botanical_surface',material=m['name'])
                await wait(client,'configure_botanical_surface',material=m['name'],settings={'profile':'OAK_LEAF' if m['model']=='MANAGED_THIN_FOLIAGE' else 'OAK_BARK'},expected_material=state['material_sha256'])
            args={'collection':'Source','levels':[{'leaf_budget':70,'radial_sides':6},{'leaf_budget':35,'radial_sides':5,'max_coverage_loss':.6,'max_silhouette_loss':.6},{'leaf_budget':20,'radial_sides':5,'max_coverage_loss':.75,'max_silhouette_loss':.75}]}
            plan=await wait(client,'inspect_botanical_lod_source',**args)
            profile=await wait(client,'create_botanical_lods',**args,expected_plan=plan['plan_sha256'],lod_collection='Lods')
            maps=['BASE_COLOR','NORMAL','AO','ROUGHNESS','METALLIC','EMISSION','ALPHA']
            before=await tool(client,'inspect_vegetation_delivery',lod_collection='Lods',required_maps=maps,min_texture_size=64)
            assert not before['complete'] and len(before['missing_assets'])==11
            await tool(client,'remove_botanical_tree',collection='Source',expected_tree=tree['tree_sha256'])
            args={'lod_collection':'Lods','missing_uv_policy':'BAKE_LAYOUT'}
            plan=await tool(client,'inspect_vegetation_bake_source',**args)
            prep=await wait(client,'prepare_vegetation_bake',**args,expected_plan=plan['plan_sha256'],bake_collection='AllMaps')
            assert len(prep['components'])==11
            entries=[]
            for role,row in prep['components'].items():
                info=await tool(client,'inspect_texture_bake',**row['inspect_texture_bake']);assert info['complete']
                result=(await client.call_tool('bake_textures',{'params':row['inspect_texture_bake']|{'expected_bake':info['bake_sha256'],'directory':role,'maps':maps,'width':64,'height':64,'samples':2,'margin':1},'wait':True})).data
                assert result['live_scene_unchanged']
                saved=json.loads((root/'library'/role/'manifest.json').read_text())
                emission=next(m for m in saved['maps'] if m['map']=='EMISSION')
                assert max(emission['statistics']['max'][:3])==0,emission
                entries.append({'asset':role,'directory':role})
            args={'lod_collection':'Lods','bake_collection':'AllMaps','entries':entries,'accept_front_pbr':True}
            plan=await wait(client,'inspect_vegetation_bake_adoption',**args)
            state=await wait(client,'adopt_vegetation_bakes',**args,expected_plan=plan['plan_sha256'])
            report=await tool(client,'inspect_vegetation_delivery',lod_collection='Lods',required_maps=maps,min_texture_size=64)
            assert report['complete'] and report['levels']==4 and report['shared_leaf_templates']==3
            assert report['budget']['rgba8_base_bytes']==11*7*64*64*4
            assert report['budget']['rgba8_full_mip_bytes']==11*7*21844
            assert report['optical_omissions'] and report['sampling_changed_assets']
            small=await tool(client,'inspect_vegetation_delivery',lod_collection='Lods',required_maps=maps,min_texture_size=128)
            assert not small['complete'] and len(small['resolution_gaps'])==11
            limited=await tool(client,'inspect_vegetation_delivery',lod_collection='Lods',required_maps=maps,min_texture_size=64,max_mip_bytes=report['budget']['rgba8_full_mip_bytes']-1)
            assert not limited['complete'] and not limited['budget']['passed']
            await tool(client,'remove_vegetation_bake',bake_collection='AllMaps',expected_preparation=prep['preparation_sha256'])
            for entry in entries:shutil.rmtree(root/'library'/entry['directory'])
            await client.call_tool('save_blend',{'path':'full-profile.blend'})
            await client.call_tool('open_blend',{'path':'full-profile.blend'})
            state=await tool(client,'inspect_botanical_lods',lod_collection='Lods');assert state['valid']
            exported=await wait(client,'export_botanical_lods',lod_collection='Lods',expected_lods=state['lods_sha256'],directory='delivery')
            assert len(exported['proof']['assets'])==11
            manifest=json.loads((root/'library/delivery/manifest.json').read_text())
            assert len(manifest['material_delivery'])==11 and all(r['images'] for r in manifest['material_delivery'].values())
            operation=(await client.call_tool('get_operation',{'operation_id':exported['operation_id']})).data
            assert operation['storage']['free_bytes']>0 and operation['storage']['available_after_reserve_bytes']>=0
            (root/'library/coverage.json').write_text(json.dumps(report,indent=2))
            if dest:=os.environ.get('MCPBLENDER_FULL_PROFILE_EVIDENCE_DIR'):shutil.copytree(root/'library',Path(dest),dirs_exist_ok=True)
            await tool(client,'remove_botanical_lods',lod_collection='Lods',expected_lods=state['lods_sha256'])
            assert len((await wait(client,'validate_botanical_lod_bundle',directory='delivery'))['assets'])==11
    asyncio.run(run())
