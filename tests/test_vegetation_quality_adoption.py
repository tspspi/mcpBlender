"""Quality-gated maps remain bound through packed adoption and numeric export."""
import asyncio
import json
import os
from pathlib import Path
import shutil
from fastmcp.exceptions import ToolError
import pytest
from mcpblender import texture_files
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_quality_bake_adoption_and_standalone_delivery(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='Source',recipe=recipe,expected_model=plan['model_sha256'])
            foliage={'shoots_per_bud':2,'attachment_nodes':5,'variants':3}
            plan=await wait(client,'plan_botanical_foliage',collection='Source',foliage=foliage)
            tree=await wait(client,'configure_botanical_foliage',collection='Source',foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=plan['foliage_sha256'])
            for row in (await tool(client,'inspect_vegetation_materials',collection='Source'))['contract']['materials']:
                mat=await tool(client,'inspect_botanical_surface',material=row['name'])
                await wait(client,'configure_botanical_surface',material=row['name'],settings={'profile':'OAK_LEAF' if row['model']=='MANAGED_THIN_FOLIAGE' else 'OAK_BARK'},expected_material=mat['material_sha256'])
            args={'collection':'Source','levels':[{'leaf_budget':70,'radial_sides':6}]}
            plan=await wait(client,'inspect_botanical_lod_source',**args)
            original=await wait(client,'create_botanical_lods',**args,lod_collection='Lods',expected_plan=plan['plan_sha256'])
            args={'lod_collection':'Lods','assets':['lod-0-wood','leaf-0'],'missing_uv_policy':'BAKE_LAYOUT','texture_width':1024,'texture_height':1024,'tile_padding_pixels':16}
            plan=await tool(client,'inspect_vegetation_bake_source',**args)
            prep=await wait(client,'prepare_vegetation_bake',**args,bake_collection='Prepared',expected_plan=plan['plan_sha256'])
            policy={'width':1024,'height':1024,'min_texels_per_meter':32,'min_chart_pixels':4,'padding_pixels':1,'mip_levels':0}
            maps=['BASE_COLOR','NORMAL','ALPHA'];entries=[]
            for role,row in prep['components'].items():
                info=await tool(client,'inspect_texture_bake',**row['inspect_texture_bake'],quality=policy)
                assert info['complete'],info
                assert info['bake_sha256']!=row['initial_bake_sha256']
                try:
                    await client.call_tool('bake_textures',{'params':row['inspect_texture_bake']|{'quality':policy,'expected_bake':info['bake_sha256'],'directory':role,'width':1024,'height':1024,'maps':maps,'samples':1,'margin':1},'wait':True})
                except ToolError:
                    if dest:=os.environ.get('MCPBLENDER_QUALITY_ADOPTION_EVIDENCE_DIR'):
                        shutil.copytree(root/'library',Path(dest)/'failed',dirs_exist_ok=True)
                        (Path(dest)/'failed'/f'{role}-inspection.json').write_text(json.dumps(info,indent=2))
                    raise
                saved=texture_files.read_json(root/'library'/role/'manifest.json')
                assert texture_files.bake_fingerprint(saved['source_inspection'],without_quality=True)==row['initial_bake_sha256']
                entries.append({'asset':role,'directory':role})
            assert (await tool(client,'inspect_botanical_lods',lod_collection='Lods'))['lods_sha256']==original['lods_sha256']
            args={'lod_collection':'Lods','bake_collection':'Prepared','entries':entries,'accept_front_pbr':True}
            # A broken witness refuses before any profile mutation.
            manifest_path=root/'library/leaf-0/manifest.json';raw=manifest_path.read_bytes();saved=json.loads(raw);saved['source_inspection']['objects'][0]['geometry']='f'*64;manifest_path.write_text(json.dumps(saved))
            try:
                with pytest.raises(ToolError,match='unchanged preparation'):await wait(client,'inspect_vegetation_bake_adoption',**args)
            finally:manifest_path.write_bytes(raw)
            assert (await tool(client,'inspect_botanical_lods',lod_collection='Lods'))['lods_sha256']==original['lods_sha256']
            plan=await wait(client,'inspect_vegetation_bake_adoption',**args)
            adopted=await wait(client,'adopt_vegetation_bakes',**args,expected_plan=plan['plan_sha256'])
            for role,row in adopted['baked_materials'].items():
                assert row['texture_quality']['passed'] and row['texture_quality']['policy']['mip_levels']==0
                assert row['preparation_bake_sha256']==prep['components'][role]['initial_bake_sha256']
            report=await tool(client,'inspect_vegetation_delivery',lod_collection='Lods',required_maps=maps,require_quality=True)
            assert not report['complete'] and set(report['quality_policies'])=={'leaf-0','lod-0-wood'}
            assert not set(report['quality_policies'])&set(report['assets_without_quality_reports'])
            await tool(client,'remove_vegetation_bake',bake_collection='Prepared',expected_preparation=prep['preparation_sha256'])
            for row in entries:shutil.rmtree(root/'library'/row['directory'])
            await client.call_tool('save_blend',{'path':'quality-profile.blend'})
            await client.call_tool('open_blend',{'path':'quality-profile.blend'})
            state=await tool(client,'inspect_botanical_lods',lod_collection='Lods');assert state['valid']
            exported=await wait(client,'export_botanical_lods',lod_collection='Lods',expected_lods=state['lods_sha256'],directory='delivery')
            manifest=texture_files.read_json(root/'library/delivery/semantics.json')
            assert all(r['texture_quality']['passed'] for r in manifest['baked_materials'].values())
            if dest:=os.environ.get('MCPBLENDER_QUALITY_ADOPTION_EVIDENCE_DIR'):
                shutil.copytree(root/'library',Path(dest),dirs_exist_ok=True)
                (Path(dest)/'quality-delivery.json').write_text(json.dumps(report,indent=2))
            await tool(client,'remove_botanical_lods',lod_collection='Lods',expected_lods=state['lods_sha256'])
            assert (await wait(client,'validate_botanical_lod_bundle',directory='delivery'))['assets']
    asyncio.run(run())
