"""Structured botanical interchange with Python tools disabled and source gone."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_structured_shared_template_export_and_independent_revalidation(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='BundleOak',recipe=recipe,expected_model=plan['model_sha256'])
            cfg={'shoots_per_bud':1,'attachment_nodes':2}
            foliage=await wait(client,'plan_botanical_foliage',collection='BundleOak',foliage=cfg)
            tree=await wait(client,'configure_botanical_foliage',collection='BundleOak',foliage=cfg,expected_tree=tree['tree_sha256'],expected_foliage=foliage['foliage_sha256'])
            args={'collection':'BundleOak','wind':{'steady_mps':[3,1,0],'gust_mps':2}}
            planned=await tool(client,'inspect_botanical_export',**args);assert 'recovery' not in planned
            with pytest.raises(ToolError,match='budget'):await tool(client,'inspect_botanical_export',**args,max_instances=0)
            with pytest.raises(ToolError,match='stale'):await tool(client,'export_botanical_bundle',**args,expected_export='0'*64,directory='stale')
            queued=(await client.call_tool('submit_operation',{'command':'export_botanical_bundle','params':args|{'expected_export':planned['export_sha256'],'directory':'oak-bundle'}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded',done
            report=await tool(client,'validate_botanical_bundle',directory='oak-bundle')
            assert report['leaf_instances']==foliage['metrics']['leaves'] and report['shared_leaf_templates']==3
            assert len(report['assets'])==5
            assert (await tool(client,'inspect_botanical_tree',collection='BundleOak'))['tree_sha256']==tree['tree_sha256']
            await client.call_tool('save_blend',{'path':'botanical-export-source.blend'})
            await client.call_tool('open_blend',{'path':'botanical-export-source.blend'})
            checked=await tool(client,'validate_botanical_bundle',directory='oak-bundle')
            assert {k:v for k,v in checked.items() if k!='operation_id'}=={k:v for k,v in report.items() if k!='operation_id'}
            source=await tool(client,'inspect_botanical_tree',collection='BundleOak')
            await tool(client,'remove_botanical_tree',collection='BundleOak',expected_tree=source['tree_sha256'])
            checked=await tool(client,'validate_botanical_bundle',directory='oak-bundle')
            assert {k:v for k,v in checked.items() if k!='operation_id'}=={k:v for k,v in report.items() if k!='operation_id'}
            if directory:=os.environ.get('MCPBLENDER_BOTANICAL_EXPORT_EVIDENCE_DIR'):
                target=Path(directory);target.mkdir(parents=True,exist_ok=True)
                shutil.copytree(root/'library/oak-bundle',target/'oak-bundle',dirs_exist_ok=True)
                shutil.copy2(root/'library/botanical-export-source.blend',target/'source.blend')
                (target/'proof.json').write_text(json.dumps(report,indent=2))
    asyncio.run(run())
