"""Code-disabled master UV authoring, regeneration policies and GLB inheritance."""
import asyncio
import json
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_master_secondary_layout_regeneration_and_lod_inheritance(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            state=await wait(client,'create_botanical_tree',collection='AuthoredMaster',recipe=recipe,expected_model=plan['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':5,'variants':1}
            pop=await wait(client,'plan_botanical_foliage',collection='AuthoredMaster',foliage=cfg)
            state=await wait(client,'configure_botanical_foliage',collection='AuthoredMaster',foliage=cfg,expected_tree=state['tree_sha256'],expected_foliage=pop['foliage_sha256'])
            baseline=state['model_sha256']
            args={'collection':'AuthoredMaster','expected_tree':state['tree_sha256'],'assets':['wood','leaf-0'],'texture_width':512,'texture_height':512,
                  'chart_layout':{'min_area_pixels':64,'min_span_pixels':2,'gutter_pixels':4,'allow_stretch':True}}
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_secondary_uv',**(args|{'expected_tree':'0'*64}))
            state=await wait(client,'create_botanical_secondary_uv',**args)
            assert state['valid'] and state['model_sha256']==baseline
            records=state['secondary_uv'];assert set(records)=={'wood','leaf-0'}
            for role in records:
                info=await tool(client,'inspect_uv_layout',name=state['mesh_assets'][role]['name'],uv_map='UV2')
                assert info['uv_channel']==1 and info['active_uv_map']==info['render_uv_map']!='UV2'
            regenerate={'collection':'AuthoredMaster','recipe':recipe,'expected_model':baseline,'expected_tree':state['tree_sha256']}
            state=await wait(client,'regenerate_botanical_tree',**regenerate)
            assert state['valid'] and state['secondary_uv']==records
            changed=recipe|{'height':6,'seed':2}
            plan=await wait(client,'plan_botanical_tree',recipe=changed)
            regenerate={'collection':'AuthoredMaster','recipe':changed,'expected_model':plan['model_sha256'],'expected_tree':state['tree_sha256']}
            with pytest.raises(ToolError,match='identical geometry'):
                await wait(client,'regenerate_botanical_tree',**regenerate)
            assert (await tool(client,'inspect_botanical_tree',collection='AuthoredMaster'))['tree_sha256']==state['tree_sha256']
            state=await wait(client,'regenerate_botanical_tree',**regenerate,secondary_uv_policy='REPROJECT')
            assert state['valid'] and set(state['secondary_uv'])==set(records)
            assert state['secondary_uv']['wood'][0]['uv_witness']!=records['wood'][0]['uv_witness']
            records=state['secondary_uv']
            await client.call_tool('save_blend',{'path':'authored-master.blend'})
            await client.call_tool('open_blend',{'path':'authored-master.blend'})
            state=await tool(client,'inspect_botanical_tree',collection='AuthoredMaster');assert state['valid'] and state['secondary_uv']==records
            plan=await wait(client,'inspect_botanical_export',collection='AuthoredMaster')
            exported=await wait(client,'export_botanical_bundle',collection='AuthoredMaster',expected_export=plan['export_sha256'],directory='master-secondary-delivery')
            assert {a['asset']:a['proof']['uv_channels'] for a in exported['proof']['assets']}=={'wood':2,'shoots':0,'leaf-0':2}
            semantic=json.loads((root/'library/master-secondary-delivery/semantics.json').read_text());assert semantic['secondary_uv']==records
            args={'collection':'AuthoredMaster','levels':[{'leaf_budget':70,'radial_sides':6,'max_coverage_loss':1,'max_silhouette_loss':1}]}
            plan=await wait(client,'inspect_botanical_lod_source',**args)
            lod=await wait(client,'create_botanical_lods',**args,lod_collection='AuthoredLods',expected_plan=plan['plan_sha256'])
            assert lod['valid'] and set(lod['secondary_uv'])=={'lod-0-wood','leaf-0'}
            assert lod['secondary_uv']['lod-0-wood']==records['wood'] and lod['secondary_uv']['leaf-0']==records['leaf-0']
            assert lod['mesh_assets']['lod-1-wood']['uv_maps']==['BarkUV']
            lod=await wait(client,'create_vegetation_secondary_uv',lod_collection='AuthoredLods',expected_lods=lod['lods_sha256'],assets=['lod-1-wood'],texture_width=512,texture_height=512,chart_layout={'min_area_pixels':64,'min_span_pixels':2,'gutter_pixels':4,'allow_stretch':True})
            delivered=await wait(client,'export_botanical_lods',lod_collection='AuthoredLods',expected_lods=lod['lods_sha256'],directory='inherited-lod-secondary')
            assert all(a['proof']['uv_channels']==2 for a in delivered['proof']['assets'] if a['asset'] in {'lod-0-wood','lod-1-wood','leaf-0'})
            # Removing the foliage is explicit about dropping authored leaf maps.
            state=await tool(client,'inspect_botanical_tree',collection='AuthoredMaster')
            with pytest.raises(ToolError,match='removes a secondary UV role'):
                await wait(client,'remove_botanical_foliage',collection='AuthoredMaster',expected_tree=state['tree_sha256'])
            state=await wait(client,'remove_botanical_foliage',collection='AuthoredMaster',expected_tree=state['tree_sha256'],secondary_uv_policy='DISCARD')
            assert state['valid'] and not state['foliage'] and state['secondary_uv']=={}
            assert state['mesh_assets']['wood']['uv_maps']==['BarkUV']
            await tool(client,'remove_botanical_tree',collection='AuthoredMaster',expected_tree=state['tree_sha256'])
            assert (await wait(client,'validate_botanical_bundle',directory='master-secondary-delivery'))['semantic_sha256']==exported['proof']['semantic_sha256']
            assert (await wait(client,'validate_botanical_lod_bundle',directory='inherited-lod-secondary'))['semantic_sha256']==delivered['proof']['semantic_sha256']
            await tool(client,'remove_botanical_lods',lod_collection='AuthoredLods',expected_lods=lod['lods_sha256'])
    asyncio.run(run())
