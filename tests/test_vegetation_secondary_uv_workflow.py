"""Code-disabled owned secondary layouts retain real baked maps and delivery."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_owned_secondary_uv_baked_leaf_and_lod_export(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='SecondarySource',recipe=recipe,expected_model=plan['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':5,'variants':1}
            pop=await wait(client,'plan_botanical_foliage',collection='SecondarySource',foliage=cfg)
            tree=await wait(client,'configure_botanical_foliage',collection='SecondarySource',foliage=cfg,expected_tree=tree['tree_sha256'],expected_foliage=pop['foliage_sha256'])
            args={'collection':'SecondarySource','levels':[{'leaf_budget':70,'radial_sides':6,'max_coverage_loss':1,'max_silhouette_loss':1}]}
            plan=await wait(client,'inspect_botanical_lod_source',**args)
            state=await wait(client,'create_botanical_lods',**args,lod_collection='SecondaryLods',expected_plan=plan['plan_sha256'])
            prep_args={'lod_collection':'SecondaryLods','assets':['leaf-0'],'missing_uv_policy':'BAKE_LAYOUT'}
            plan=await tool(client,'inspect_vegetation_bake_source',**prep_args)
            prepared=await wait(client,'prepare_vegetation_bake',**prep_args,bake_collection='BeforeSecondary',expected_plan=plan['plan_sha256'])
            row=prepared['components']['leaf-0'];info=await tool(client,'inspect_texture_bake',**row['inspect_texture_bake'])
            baked=(await client.call_tool('bake_textures',{'params':row['inspect_texture_bake']|{'expected_bake':info['bake_sha256'],'directory':'before-secondary','width':64,'height':64,'samples':2,'margin':1,'maps':['BASE_COLOR','NORMAL','ROUGHNESS','ALPHA']},'wait':True})).data
            assert baked['live_scene_unchanged']
            adopt={'lod_collection':'SecondaryLods','bake_collection':'BeforeSecondary','entries':[{'asset':'leaf-0','directory':'before-secondary'}],'accept_front_pbr':True}
            plan=await wait(client,'inspect_vegetation_bake_adoption',**adopt)
            state=await wait(client,'adopt_vegetation_bakes',**adopt,expected_plan=plan['plan_sha256'])
            old_record=state['baked_materials']['leaf-0'];old_guard=state['lods_sha256']
            uvargs={'lod_collection':'SecondaryLods','expected_lods':old_guard,'assets':['lod-1-wood','leaf-0'],'texture_width':512,'texture_height':512,
                    'chart_layout':{'min_area_pixels':64,'min_span_pixels':2,'gutter_pixels':4,'allow_stretch':True}}
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_vegetation_secondary_uv',**(uvargs|{'expected_lods':'0'*64}))
            with pytest.raises(ToolError,match='corner budget'):
                await wait(client,'create_vegetation_secondary_uv',**uvargs,max_corners=1)
            assert (await tool(client,'inspect_botanical_lods',lod_collection='SecondaryLods'))['lods_sha256']==old_guard
            state=await wait(client,'create_vegetation_secondary_uv',**uvargs)
            assert state['valid'] and state['baked_materials']['leaf-0']==old_record
            assert set(state['secondary_uv'])=={'leaf-0','lod-1-wood'}
            records=state['secondary_uv']
            assert records['leaf-0'][0]['uv_channel']==2 and records['lod-1-wood'][0]['uv_channel']==1
            assert (await tool(client,'inspect_vegetation_bake',bake_collection='BeforeSecondary'))['preparation_sha256']==prepared['preparation_sha256']
            assert (await tool(client,'inspect_botanical_tree',collection='SecondarySource'))['tree_sha256']==tree['tree_sha256']
            # The pre-UV2 preparation cannot replace a profile mesh and lose UV2.
            with pytest.raises(ToolError,match='Retained preparation'):
                await wait(client,'inspect_vegetation_bake_adoption',**adopt,replace_existing=True)
            for role in uvargs['assets']:
                name=state['mesh_assets'][role]['name'];layout=await tool(client,'inspect_uv_layout',name=name,uv_map='UV2',texture_width=512,texture_height=512)
                assert layout['active_uv_map']==layout['render_uv_map']!='UV2'
                assert layout['overlap']['complete'] and layout['overlap']['face_pair_count']==0
            # New preparations carry the secondary map into material revisions.
            revision_args={'lod_collection':'SecondaryLods','assets':['leaf-0'],'uv_strategy':'EXISTING'}
            plan=await tool(client,'inspect_vegetation_bake_source',**revision_args)
            revision=await wait(client,'prepare_vegetation_bake',**revision_args,bake_collection='AfterSecondary',expected_plan=plan['plan_sha256'])
            row=revision['components']['leaf-0'];info=await tool(client,'inspect_texture_bake',**row['inspect_texture_bake'])
            await client.call_tool('bake_textures',{'params':row['inspect_texture_bake']|{'expected_bake':info['bake_sha256'],'directory':'after-secondary','width':64,'height':64,'samples':2,'margin':1,'maps':['BASE_COLOR','NORMAL','ROUGHNESS','ALPHA']},'wait':True})
            args={'lod_collection':'SecondaryLods','bake_collection':'AfterSecondary','entries':[{'asset':'leaf-0','directory':'after-secondary'}],'replace_existing':True,'accept_front_pbr':True}
            plan=await wait(client,'inspect_vegetation_bake_adoption',**args)
            state=await wait(client,'adopt_vegetation_bakes',**args,expected_plan=plan['plan_sha256'])
            assert state['valid'] and state['secondary_uv']==records
            assert state['baked_materials']['leaf-0']['revision']==2
            assert state['baked_materials']['leaf-0']['previous_adoption_sha256']==old_record['adoption_sha256']
            for name,prep in [('BeforeSecondary',prepared),('AfterSecondary',revision)]:
                await tool(client,'remove_vegetation_bake',bake_collection=name,expected_preparation=prep['preparation_sha256'])
            for directory in ('before-secondary','after-secondary'):shutil.rmtree(root/'library'/directory)
            await client.call_tool('save_blend',{'path':'secondary-profile.blend'})
            await client.call_tool('open_blend',{'path':'secondary-profile.blend'})
            state=await tool(client,'inspect_botanical_lods',lod_collection='SecondaryLods');assert state['valid'] and state['secondary_uv']==records
            exported=await wait(client,'export_botanical_lods',lod_collection='SecondaryLods',expected_lods=state['lods_sha256'],directory='secondary-delivery')
            proof={r['asset']:r['proof'] for r in exported['proof']['assets']}
            assert proof['leaf-0']['uv_channels']==3 and proof['lod-1-wood']['uv_channels']==2
            semantic=json.loads((root/'library/secondary-delivery/semantics.json').read_text());assert semantic['secondary_uv']==records
            if dest:=os.environ.get('MCPBLENDER_VEGETATION_SECONDARY_UV_EVIDENCE_DIR'):shutil.copytree(root/'library',Path(dest),dirs_exist_ok=True)
            # Preserve a local snapshot for native fault-injection checks below.
            shutil.copy2(root/'library/secondary-profile.blend',root/'secondary-profile.blend')
            await tool(client,'remove_botanical_lods',lod_collection='SecondaryLods',expected_lods=state['lods_sha256'])
            assert (await wait(client,'validate_botanical_lod_bundle',directory='secondary-delivery'))['semantic_sha256']==exported['proof']['semantic_sha256']
    asyncio.run(run())
