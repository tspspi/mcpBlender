"""Python-disabled shared LOD export, persistence and source-free validation."""
import asyncio
import json
import os
from pathlib import Path
import shutil
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_structured_lod_export_and_standalone_validation(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='Source',recipe=recipe,expected_model=plan['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':5};pop=await wait(client,'plan_botanical_foliage',collection='Source',foliage=cfg)
            tree=await wait(client,'configure_botanical_foliage',collection='Source',foliage=cfg,expected_tree=tree['tree_sha256'],expected_foliage=pop['foliage_sha256'])
            args={'collection':'Source','levels':[{'leaf_budget':110,'radial_sides':8,'min_branch_radius_m':0},{'leaf_budget':100,'radial_sides':8,'min_branch_radius_m':0,'max_coverage_loss':.55,'max_silhouette_loss':.55}]}
            plan=await wait(client,'inspect_botanical_lod_source',**args)
            profile=await wait(client,'create_botanical_lods',**args,expected_plan=plan['plan_sha256'],lod_collection='Lods',display_offset_m=[8,0,0])
            await tool(client,'remove_botanical_tree',collection='Source',expected_tree=tree['tree_sha256'])
            materials=await tool(client,'inspect_vegetation_materials',lod_collection='Lods')
            result=await wait(client,'export_botanical_lods',lod_collection='Lods',expected_lods=profile['lods_sha256'],directory='lod-bundle',material_mode='PARAMETERS',expected_materials=materials['materials_sha256'])
            journal=await tool(client,'inspect_export_job',directory='lod-bundle')
            assert journal['record']['kind']=='VEGETATION_LOD' and journal['record']['state']=='published'
            assert journal['record']['binding']['materials_sha256']==materials['materials_sha256'] and journal['record']['operation_id']==result['operation_id'] and journal['target_is_original_stage']
            assert result['proof']['placement_mode']=='SOURCE' and len(result['proof']['assets'])==9
            assert result['proof']['shared_leaf_templates']==3
            assert [x['expanded_triangles'] for x in result['proof']['levels']]==[28548,22668,20708]
            assert (await tool(client,'inspect_botanical_lods',lod_collection='Lods'))['lods_sha256']==profile['lods_sha256']
            await client.call_tool('save_blend',{'path':'lod-export-source.blend'})
            await client.call_tool('open_blend',{'path':'lod-export-source.blend'})
            current=await tool(client,'inspect_botanical_lods',lod_collection='Lods')
            await tool(client,'remove_botanical_lods',lod_collection='Lods',expected_lods=current['lods_sha256'])
            proof=await wait(client,'validate_botanical_lod_bundle',directory='lod-bundle')
            assert {k:v for k,v in proof.items() if k!='operation_id'}==result['proof']
            if directory:=os.environ.get('MCPBLENDER_LOD_EXPORT_EVIDENCE_DIR'):
                target=Path(directory);target.mkdir(parents=True,exist_ok=True)
                shutil.copytree(root/'library/lod-bundle',target/'lod-bundle',dirs_exist_ok=True)
                shutil.copy2(root/'library/lod-export-source.blend',target/'source.blend')
                (target/'proof.json').write_text(json.dumps(result['proof'],indent=2))
    asyncio.run(run())
