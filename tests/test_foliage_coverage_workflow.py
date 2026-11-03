"""Agents compare foliage recipes through tracked read-only coverage operations."""
import asyncio
import json
import os
from pathlib import Path
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_structured_coverage_refinement_without_python(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            recipe={'height':3,'crown_width':2.5,'trunk_radius':.08,'attractors':96,'iterations':6,'node_budget':256,'segment_length':.2}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='CoverageOak',recipe=recipe,expected_model=plan['model_sha256'])
            sparse={'shoots_per_bud':1,'attachment_nodes':2,'shoot_length':.3}
            dense={'shoots_per_bud':6,'attachment_nodes':12,'shoot_length':.5}
            before=await wait(client,'inspect_botanical_coverage',collection='CoverageOak',foliage=sparse,resolution=64,include_masks=True)
            after=await wait(client,'inspect_botanical_coverage',collection='CoverageOak',foliage=dense,resolution=64,include_masks=True)
            assert after['proposed_recipe'] and before['tree_sha256']==after['tree_sha256']==tree['tree_sha256']
            assert all(after['views'][v]['covered_crown_pixels']>before['views'][v]['covered_crown_pixels'] for v in before['views'])
            planned=await wait(client,'plan_botanical_foliage',collection='CoverageOak',foliage=dense)
            tree=await wait(client,'configure_botanical_foliage',collection='CoverageOak',foliage=dense,expected_tree=tree['tree_sha256'],expected_foliage=planned['foliage_sha256'])
            actual=await wait(client,'inspect_botanical_coverage',collection='CoverageOak',resolution=64,include_masks=True)
            assert not actual['proposed_recipe'] and actual['views']==after['views']
            assert (await tool(client,'inspect_botanical_tree',collection='CoverageOak'))['tree_sha256']==tree['tree_sha256']
            if target:=os.environ.get('MCPBLENDER_FOLIAGE_EVIDENCE_DIR'):
                out=Path(target);out.mkdir(parents=True,exist_ok=True);(out/'coverage-proof.json').write_text(json.dumps({'sparse':before,'dense':after,'actual':actual},indent=2))
    asyncio.run(run())
