"""Code-disabled typed MCP cluster plans preserve the editable native source."""
from mcpblender.skin_glb import Document
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_cluster_planning_mcp_pagination_budgets_and_source_preservation(assets_live):
    root,config=assets_live
    async def run():
        async with client_for(config) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            planned=await wait(client,'plan_botanical_tree',recipe=recipe)
            state=await wait(client,'create_botanical_tree',collection='ClusterMaster',recipe=recipe,expected_model=planned['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':5}
            pop=await wait(client,'plan_botanical_foliage',collection='ClusterMaster',foliage=cfg)
            state=await wait(client,'configure_botanical_foliage',collection='ClusterMaster',foliage=cfg,expected_tree=state['tree_sha256'],expected_foliage=pop['foliage_sha256'])
            args={'collection':'ClusterMaster','max_leaves':17,'limit':1}
            first=await wait(client,'inspect_botanical_foliage_clusters',**args)
            allrows=[]
            for offset in range(first['cluster_count']):
                page=await wait(client,'inspect_botanical_foliage_clusters',**(args|{'offset':offset}))
                assert page['plan_sha256']==first['plan_sha256'] and len(page['clusters'])==1
                allrows.extend(page['clusters'])
            assert sum(r['leaf_count'] for r in allrows)==first['source_leaves']
            assert sum(r['source_triangles'] for r in allrows)==first['source_triangles']
            assert all(r['leaf_count']<=17 and 'leaf_indices' not in r for r in allrows)
            with pytest.raises(ToolError,match='count budget'):
                await wait(client,'inspect_botanical_foliage_clusters',**(args|{'max_clusters':1}))
            unchanged=await tool(client,'inspect_botanical_tree',collection='ClusterMaster')
            assert unchanged['tree_sha256']==state['tree_sha256']
            cluster=await wait(client,'create_botanical_foliage_cluster',**args,cluster_collection='SelectedCluster',cluster_index=0,expected_plan=first['plan_sha256'],display_offset_m=[7,0,0])
            assert cluster['valid'] and cluster['source_unchanged'] and cluster['leaf_mapping']
            cards={'sources':[cluster['object']],'thin_foliage_mode':'FRONT_PBR','view':'TOP','resolution':64}
            fit=await tool(client,'inspect_foliage_card',**cards)
            target=await tool(client,'create_foliage_card',**cards,name='SelectedCard',expected_card=fit['card_sha256'])
            baked=await wait(client,'bake_textures',**(target['bake_parameters']|{'directory':'selected-card','width':96,'height':96,'samples':4,'margin':1,'min_projection_coverage':target['suggested_min_projection_coverage']}))
            assert baked['live_scene_unchanged'] and baked['projection']['fraction']>0
            alpha=next(m for m in baked['maps'] if m['map']=='ALPHA')['statistics']
            assert alpha['min'][0]==0 and alpha['max'][0]==1
            assert (await tool(client,'inspect_botanical_tree',collection='ClusterMaster'))['tree_sha256']==state['tree_sha256']
            snapshot=await tool(client,'inspect_botanical_foliage_cluster',cluster_collection='SelectedCluster')
            assert snapshot['valid'] and snapshot['source_unchanged']
            await tool(client,'remove_botanical_tree',collection='ClusterMaster',expected_tree=state['tree_sha256'])
            snapshot=await tool(client,'inspect_botanical_foliage_cluster',cluster_collection='SelectedCluster')
            assert snapshot['valid'] and not snapshot['source_present']
            await tool(client,'remove_botanical_foliage_cluster',cluster_collection='SelectedCluster',expected_cluster=snapshot['cluster_sha256'])
            await client.call_tool('open_blend',{'path':'selected-card/asset.blend'})
            assert (await tool(client,'validate_texture_bake',directory='selected-card'))['validated']
            await tool(client,'export_objects_glb',objects=['SelectedCard'],path='selected-card.glb')
            glb=Document(root/'library/selected-card.glb',morphs=True)
            assert glb.doc['materials'][0]['alphaMode'] in {'MASK','BLEND'}
            assert all('bufferView' in image and 'uri' not in image for image in glb.doc['images'])
            await tool(client,'configure_render',resolution_x=192,resolution_y=192,samples=8)
            await tool(client,'setup_preview_stage',objects=['SelectedCard'],prefix='ClusterView',strength=.35)
            queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':'selected-card.png','camera':'ClusterView_Camera','engine':'CYCLES','width':192,'height':192}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded',done
            if directory:=os.environ.get('MCPBLENDER_CLUSTER_EVIDENCE_DIR'):
                out=Path(directory);out.mkdir(parents=True,exist_ok=True)
                shutil.copytree(root/'library/selected-card',out/'selected-card',dirs_exist_ok=True)
                for name in ('selected-card.glb','selected-card.png'):shutil.copy2(root/'library'/name,out/name)
                (out/'proof.json').write_text(json.dumps({'cluster':cluster,'fit':fit,'target':target,'bake':baked},indent=2))
    asyncio.run(run())
