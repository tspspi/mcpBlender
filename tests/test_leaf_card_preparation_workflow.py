"""Python-disabled blade-target preparation and existing isolated normal/alpha bake."""
import asyncio
import pytest
from fastmcp.exceptions import ToolError
from mcpblender.texture_files import read_json
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_blade_card_bake_without_code(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='Source',recipe=recipe,expected_model=plan['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':5,'variants':1}
            pop=await wait(client,'plan_botanical_foliage',collection='Source',foliage=cfg)
            tree=await wait(client,'configure_botanical_foliage',collection='Source',foliage=cfg,expected_tree=tree['tree_sha256'],expected_foliage=pop['foliage_sha256'])
            args={'collection':'Source','blade_cards':{},'texture_width':64,'texture_height':128,'tile_padding_pixels':2}
            plan=await tool(client,'inspect_vegetation_bake_source',**args)
            assert plan['recipe']=='NATIVE_THIN_BLADE_CARD_PREPARATION_V1'
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'prepare_vegetation_bake',**args,expected_plan='0'*64,bake_collection='Stale')
            state=await wait(client,'prepare_vegetation_bake',**args,expected_plan=plan['plan_sha256'],bake_collection='Cards')
            assert state['valid'] and set(state['components'])=={'leaf-0'}
            assert (await tool(client,'inspect_botanical_tree',collection='Source'))['tree_sha256']==tree['tree_sha256']
            row=state['components']['leaf-0']
            # LOD profiles expose the same shared roles, and remain independent.
            lod_args={'collection':'Source','levels':[{'leaf_budget':110,'radial_sides':8,'min_branch_radius_m':0}]}
            lod_plan=await wait(client,'inspect_botanical_lod_source',**lod_args)
            lod=await wait(client,'create_botanical_lods',**lod_args,expected_plan=lod_plan['plan_sha256'],lod_collection='Lods',display_offset_m=[8,0,0])
            lp=await tool(client,'inspect_vegetation_bake_source',lod_collection='Lods',blade_cards={},assets=['leaf-0'],texture_width=64,texture_height=128)
            lc=await wait(client,'prepare_vegetation_bake',lod_collection='Lods',blade_cards={},assets=['leaf-0'],texture_width=64,texture_height=128,expected_plan=lp['plan_sha256'],bake_collection='LodCards')
            assert lc['valid']
            (root/'library/unused').mkdir(parents=True)
            with pytest.raises(ToolError,match='not unchanged-geometry'):
                await wait(client,'inspect_vegetation_bake_adoption',lod_collection='Lods',bake_collection='LodCards',entries=[{'asset':'leaf-0','directory':'unused'}])
            assert (await tool(client,'inspect_botanical_lods',lod_collection='Lods'))['lods_sha256']==lod['lods_sha256']
            await tool(client,'remove_botanical_lods',lod_collection='Lods',expected_lods=lod['lods_sha256'])
            assert (await tool(client,'inspect_vegetation_bake',bake_collection='LodCards'))['valid']
            await tool(client,'remove_vegetation_bake',bake_collection='LodCards',expected_preparation=lc['preparation_sha256'])
            await tool(client,'remove_botanical_tree',collection='Source',expected_tree=tree['tree_sha256'])
            await client.call_tool('save_blend',{'path':'cards.blend'})
            await client.call_tool('open_blend',{'path':'cards.blend'})
            state=await tool(client,'inspect_vegetation_bake',bake_collection='Cards');assert state['valid']
            info=await tool(client,'inspect_texture_bake',**row['inspect_texture_bake'])
            assert info['complete'] and info['bake_sha256']==row['initial_bake_sha256']
            result=(await client.call_tool('bake_textures',{'params':row['bake_parameters']|{'directory':'blade','samples':2,'margin':1},'wait':True})).data
            assert result['live_scene_unchanged']
            manifest=read_json(root/'library/blade/manifest.json')
            assert {r['map'] for r in manifest['maps']}=={'NORMAL','ALPHA'}
            alpha=next(r for r in manifest['maps'] if r['map']=='ALPHA')['statistics']
            assert alpha['min'][0]<.01 and alpha['max'][0]>.99
            assert manifest['material_adapters'] # Native optics are explicitly omitted by FRONT_PBR.
            assert (await tool(client,'inspect_vegetation_bake',bake_collection='Cards'))['preparation_sha256']==state['preparation_sha256']
            with pytest.raises(ToolError,match='Recreate blade-card'):
                await tool(client,'refresh_vegetation_bake',bake_collection='Cards',expected_preparation=state['preparation_sha256'])
            await tool(client,'remove_vegetation_bake',bake_collection='Cards',expected_preparation=state['preparation_sha256'])
            await client.call_tool('open_blend',{'path':'blade/asset.blend'})
            assert (await tool(client,'validate_texture_bake',directory='blade'))['validated']
    asyncio.run(run())
