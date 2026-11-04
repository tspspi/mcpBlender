"""Opt-in retained dense source -> selected cluster -> card/PBR delivery via MCP."""
from mcpblender.skin_glb import Document
import asyncio
import json
import os
from pathlib import Path
import shutil
import time
import pytest
from test_asset_editing import assets_live,client_for,tool,pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_DENSE_CLUSTER_SOURCE'),reason='Retained dense source opt-in required')
def test_dense_cluster_card_bake_and_independent_delivery(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(os.environ['MCPBLENDER_DENSE_CLUSTER_SOURCE'],library/'dense-source.blend')
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            start=time.monotonic();events=[]
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data
                operation_id=queued['operation_id'];deadline=time.monotonic()+600
                while True:
                    result=(await client.call_tool('wait_operation',{'operation_id':operation_id,'timeout_seconds':10})).data
                    events.append({'command':command,'operation_id':operation_id,'state':result['state'],'progress':result.get('progress'),'storage':result.get('storage'),'elapsed_seconds':time.monotonic()-start})
                    if directory:=os.environ.get('MCPBLENDER_DENSE_CLUSTER_EVIDENCE'):
                        out=Path(directory);out.mkdir(parents=True,exist_ok=True);(out/'progress.json').write_text(json.dumps(events,indent=2))
                    assert result['state'] not in {'failed','cancelled','interrupted'},result
                    if result['state']=='succeeded':return result['result']
                    assert time.monotonic()<deadline,('Operation still live; do not replay',operation_id,result)
            await client.call_tool('open_blend',{'path':'dense-source.blend'})
            source=await operation('inspect_botanical_tree',collection='Canopy3')
            args={'collection':'Canopy3','max_leaves':512,'max_triangles':100000,'max_clusters':512,'limit':64}
            plan=await operation('inspect_botanical_foliage_clusters',**args);rows=list(plan['clusters'])
            for offset in range(64,plan['cluster_count'],64):
                page=await operation('inspect_botanical_foliage_clusters',**(args|{'offset':offset}));assert page['plan_sha256']==plan['plan_sha256'];rows.extend(page['clusters'])
            assert len(rows)==296 and sum(r['leaf_count'] for r in rows)==88704
            chosen=max(rows,key=lambda r:r['source_triangles'])
            cluster=await operation('create_botanical_foliage_cluster',**args,cluster_collection='DenseCluster',cluster_index=chosen['index'],expected_plan=plan['plan_sha256'],display_offset_m=[20,0,0])
            assert cluster['valid'] and cluster['source_unchanged'] and cluster['cluster']['source_triangles']==90552
            cards={'sources':[cluster['object']],'thin_foliage_mode':'FRONT_PBR','view':'TOP','resolution':128,'max_triangles':100000}
            fit=await operation('inspect_foliage_card',**cards)
            target=await operation('create_foliage_card',**cards,name='DenseCard',expected_card=fit['card_sha256'])
            baked=await operation('bake_textures',**(target['bake_parameters']|{'directory':'dense-card','width':256,'height':256,'samples':8,'margin':2,'min_projection_coverage':target['suggested_min_projection_coverage']}))
            assert baked['live_scene_unchanged'] and baked['projection']['fraction']>0
            alpha=next(m for m in baked['maps'] if m['map']=='ALPHA')['statistics']
            assert alpha['min'][0]==0 and alpha['max'][0]==1
            after=await operation('inspect_botanical_tree',collection='Canopy3');assert after['tree_sha256']==source['tree_sha256']
            snapshot=await operation('inspect_botanical_foliage_cluster',cluster_collection='DenseCluster');assert snapshot['valid'] and snapshot['source_unchanged']
            await operation('remove_botanical_tree',collection='Canopy3',expected_tree=after['tree_sha256'])
            snapshot=await operation('inspect_botanical_foliage_cluster',cluster_collection='DenseCluster');assert snapshot['valid'] and not snapshot['source_present']
            await operation('remove_botanical_foliage_cluster',cluster_collection='DenseCluster',expected_cluster=snapshot['cluster_sha256'])
            await client.call_tool('open_blend',{'path':'dense-card/asset.blend'})
            checked=await operation('validate_texture_bake',directory='dense-card');assert checked['validated']
            await operation('export_objects_glb',objects=['DenseCard'],path='dense-card.glb')
            glb=Document(root/'library/dense-card.glb',morphs=True)
            assert glb.doc['materials'][0]['alphaMode'] in {'MASK','BLEND'}
            assert all('bufferView' in image and 'uri' not in image for image in glb.doc['images'])
            await operation('configure_render',resolution_x=256,resolution_y=256,samples=8)
            await operation('setup_preview_stage',objects=['DenseCard'],prefix='DenseView',strength=.35)
            await operation('render_still',path='dense-card.png',camera='DenseView_Camera',engine='CYCLES',width=256,height=256)
            if directory:=os.environ.get('MCPBLENDER_DENSE_CLUSTER_EVIDENCE'):
                out=Path(directory);out.mkdir(parents=True,exist_ok=True)
                shutil.copytree(library/'dense-card',out/'dense-card',dirs_exist_ok=True)
                for name in ('dense-card.glb','dense-card.png'):shutil.copy2(library/name,out/name)
                (out/'proof.json').write_text(json.dumps({'source_leaves':plan['source_leaves'],'clusters':rows,'cluster':cluster,'fit':fit,'target':target,'bake':baked,'validation':checked,'seconds':time.monotonic()-start},indent=2))
    asyncio.run(run())
