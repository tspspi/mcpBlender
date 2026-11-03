"""Real woody tree masters and guarded semantic edits with Python tools disabled."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from mcpblender import botany

async def wait(client,command,**params):return (await client.call_tool(command,{'params':params,'wait':True})).data


def test_three_seed_woody_masters_semantics_and_rendered_regeneration(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            catalog=await tool(client,'botanical_species_catalog');assert catalog['species'][0]['id']=='QUERCUS_ROBUR'
            plans=[];created=[]
            for seed in (1,2,3):
                recipe={'seed':seed}
                plan=await wait(client,'plan_botanical_tree',recipe=recipe);plans.append(plan)
                tree=await wait(client,'create_botanical_tree',collection=f'ReferenceOak{seed}',recipe=recipe,expected_model=plan['model_sha256'],location=[(seed-1)*25,0,0])
                assert tree['valid'] and tree['metrics']['height']==14 and tree['can_regenerate'],tree
                assert tree['metrics']['branches']>500
                wood=next(v for v in tree['members'] if v['role']=='WOOD')
                assert 'BarkUV' in wood['mesh']['uv_maps']
                assert {'bot_branch_index','branch_anchor','branch_stiffness','branch_phase','bend_weight'}<={v['name'] for v in wood['mesh']['attributes']}
                branches=await tool(client,'list_botanical_elements',collection=f'ReferenceOak{seed}',limit=3)
                assert len(branches['items'])==3 and branches['items'][0]['parent_id'] is None
                await tool(client,'export_botanical_model',collection=f'ReferenceOak{seed}',expected_tree=tree['tree_sha256'],path=f'oak{seed}.json')
                model=json.loads((root/'library'/f'oak{seed}.json').read_text());assert botany.validate(model)
                assert botany.digest(model)==plan['model_sha256']
                created.append(tree)
            assert len({p['model_sha256'] for p in plans})==3
            # A real woody preview, not a foliage-quality or biological claim.
            default=await tool(client,'inspect_render_visibility',name='Cube')
            await tool(client,'configure_render_visibility',name='Cube',expected_visibility=default['visibility_sha256'],hide_render=True)
            await tool(client,'configure_render',resolution_x=256,resolution_y=256,samples=8)
            await tool(client,'setup_preview_stage',objects=['ReferenceOak1_Wood'],prefix='OakView')
            queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':'oak-wood-before.png','camera':'OakView_Camera','engine':'CYCLES','width':256,'height':256}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded',done
            state=await tool(client,'inspect_botanical_tree',collection='ReferenceOak1')
            revised={'seed':1,'height':12,'crown_width':10,'light_direction':[1,0,1],'gravity':.15}
            plan=await wait(client,'plan_botanical_tree',recipe=revised)
            result=await wait(client,'regenerate_botanical_tree',collection='ReferenceOak1',recipe=revised,expected_model=plan['model_sha256'],expected_tree=state['tree_sha256'])
            assert result['valid'] and result['metrics']['height']==12 and result['geometry']['bark_material']==state['geometry']['bark_material']
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'remove_botanical_tree',collection='ReferenceOak1',expected_tree=state['tree_sha256'])
            await client.call_tool('save_blend',{'path':'oak-masters.blend'})
            await client.call_tool('open_blend',{'path':'oak-masters.blend'})
            reopened=await tool(client,'inspect_botanical_tree',collection='ReferenceOak1');assert reopened['valid']
            await tool(client,'frame_objects',name='OakView_Camera',objects=['ReferenceOak1_Wood'],view='ISOMETRIC')
            queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':'oak-wood-after.png','camera':'OakView_Camera','engine':'CYCLES','width':256,'height':256}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded',done
            state=await tool(client,'inspect_botanical_tree',collection='ReferenceOak3')
            await tool(client,'remove_botanical_tree',collection='ReferenceOak3',expected_tree=state['tree_sha256'])
            assert (await tool(client,'inspect_botanical_tree',collection='ReferenceOak2'))['valid']
            if destination:=os.environ.get('MCPBLENDER_BOTANICAL_EVIDENCE_DIR'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                for name in ('oak1.json','oak2.json','oak3.json','oak-masters.blend','oak-wood-before.png','oak-wood-after.png'):shutil.copy2(root/'library'/name,out/name)
                (out/'proof.json').write_text(json.dumps({'plans':plans,'initial':created,'revision':result,'reopened':reopened},indent=2))
    asyncio.run(run())
