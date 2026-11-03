"""Structured foliage editing with Python tools disabled and rendered evidence."""
import asyncio
import json
import os
from pathlib import Path
import shutil
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_editable_foliage_render_and_reopen(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            leaf=await tool(client,'plan_leaf_template')
            await tool(client,'create_leaf_template',name='OakLeaf',expected_leaf=leaf['leaf_sha256'])
            cfg={'shoots_per_bud':4,'attachment_nodes':8}
            plan=await wait(client,'plan_botanical_tree')
            state=await wait(client,'create_botanical_tree',collection='LeafOak',expected_model=plan['model_sha256'])
            planned=await wait(client,'plan_botanical_foliage',collection='LeafOak',foliage=cfg)
            state=await wait(client,'configure_botanical_foliage',collection='LeafOak',foliage=cfg,expected_tree=state['tree_sha256'],expected_foliage=planned['foliage_sha256'])
            assert state['valid'] and state['foliage']['metrics']['leaves']>5000
            page=await tool(client,'list_botanical_leaves',collection='LeafOak',limit=3)
            assert len(page['items'])==3 and page['total']==planned['metrics']['leaves']
            material=state['foliage']['material']
            optics=await tool(client,'inspect_foliage_material',material=material)
            changed=await tool(client,'configure_foliage_material',material=material,expected_material=optics['material_sha256'],translucent_mix=.35,back_color=[.18,.35,.04,1])
            assert changed['settings']['double_sided'] and changed['settings']['translucent_mix']>.34
            default=await tool(client,'inspect_render_visibility',name='Cube')
            await tool(client,'configure_render_visibility',name='Cube',expected_visibility=default['visibility_sha256'],hide_render=True)
            await tool(client,'configure_render',resolution_x=384,resolution_y=384,samples=16)
            await tool(client,'setup_preview_stage',objects=['LeafOak_Wood'],prefix='FoliageView')
            async def render(name,camera):
                queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':name,'camera':camera,'engine':'CYCLES','width':384,'height':384}})).data
                done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data
                assert done['state']=='succeeded',done
            await render('oak-foliage.png','FoliageView_Camera')
            await tool(client,'setup_preview_stage',objects=['OakLeaf'],prefix='LeafView')
            await render('oak-leaf.png','LeafView_Camera')
            await client.call_tool('save_blend',{'path':'oak-foliage.blend'})
            await client.call_tool('open_blend',{'path':'oak-foliage.blend'})
            state=await tool(client,'inspect_botanical_tree',collection='LeafOak');assert state['valid']
            removed=await wait(client,'remove_botanical_foliage',collection='LeafOak',expected_tree=state['tree_sha256'])
            assert removed['valid'] and removed['foliage'] is None
            if target:=os.environ.get('MCPBLENDER_FOLIAGE_EVIDENCE_DIR'):
                out=Path(target);out.mkdir(parents=True,exist_ok=True)
                for name in ('oak-foliage.png','oak-leaf.png','oak-foliage.blend'):shutil.copy2(root/'library'/name,out/name)
                (out/'proof.json').write_text(json.dumps({'planned':planned,'reopened':state,'optics':changed},indent=2))
    asyncio.run(run())
