"""Two distinct dense clusters through lossless atlas and matched native/GLB views."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import time
import pytest
from mcpblender.skin_glb import read_glb
from test_asset_editing import assets_live,client_for,tool,pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_CLUSTER_ATLAS_FIXTURE'),reason='Corrected dense card fixture required')
def test_two_cluster_atlas_independent_pixels_placement_and_render(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    fixture=Path(os.environ['MCPBLENDER_CLUSTER_ATLAS_FIXTURE']);first=json.loads((fixture/'proof.json').read_text())
    bundle=next(p for p in fixture.iterdir() if p.is_dir() and (p/'source.blend').is_file())
    shutil.copytree(bundle,library/'card_a');shutil.copy2(bundle/'source.blend',library/'input.blend');shutil.copy2(next(fixture.glob('*.glb')),library/'a.glb')
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            start=time.monotonic();out=Path(os.environ['MCPBLENDER_CLUSTER_ATLAS_EVIDENCE']) if os.environ.get('MCPBLENDER_CLUSTER_ATLAS_EVIDENCE') else None
            if out:out.mkdir(parents=True,exist_ok=True)
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data;deadline=time.monotonic()+600
                while True:
                    state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':10})).data
                    if out:(out/'progress.json').write_text(json.dumps({'command':command,'state':state['state'],'operation_id':queued['operation_id'],'progress':state.get('progress'),'storage':state.get('storage'),'seconds':time.monotonic()-start},indent=2))
                    assert state['state'] not in {'failed','cancelled','interrupted'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline,('Still live; do not replay',queued['operation_id'])
            await client.call_tool('open_blend',{'path':'card_a/asset.blend'})
            assert (await operation('validate_texture_bake',directory='card_a'))['map_policy']['alpha_margin']==0
            await client.call_tool('open_blend',{'path':'input.blend'})
            index=first['cluster']['cluster']['index']+1
            args={'collection':'Canopy3','max_leaves':512,'max_triangles':100000,'max_clusters':512,'offset':index,'limit':1}
            plan=await operation('inspect_botanical_foliage_clusters',**args)
            second=await operation('create_botanical_foliage_cluster',**args,cluster_collection='AtlasSecond',cluster_index=index,expected_plan=plan['plan_sha256'],display_offset_m=first['cluster']['display_offset_m'])
            assert {r['id'] for r in first['cluster']['leaf_mapping']}.isdisjoint(r['id'] for r in second['leaf_mapping'])
            assert second['valid'] and second['source_unchanged'] and second['cluster']['leaf_ids_sha256']!=first['cluster']['cluster']['leaf_ids_sha256']
            cards={'sources':[second['object']],'thin_foliage_mode':'FRONT_PBR','view':'TOP','resolution':128,'max_triangles':100000}
            fit=await operation('inspect_foliage_card',**cards)
            target=await operation('create_foliage_card',**cards,name='CardB',expected_card=fit['card_sha256'])
            baked=await operation('bake_textures',**(target['bake_parameters']|{'directory':'card_b','width':256,'height':256,'samples':8,'margin':2,'min_projection_coverage':target['suggested_min_projection_coverage']}))
            assert baked['live_scene_unchanged'] and baked['map_policy']['alpha_margin']==0
            await client.call_tool('save_blend',{'path':'comparison-source.blend'})
            await client.call_tool('open_blend',{'path':'card_b/asset.blend'})
            assert (await operation('validate_texture_bake',directory='card_b'))['validated']
            await operation('export_objects_glb',objects=['CardB'],path='b.glb')
            atlas_args={'entries':[{'id':'a','directory':'card_a'},{'id':'b','directory':'card_b'}],'width':1024,'height':512,'gutter':8}
            planned=await operation('inspect_texture_atlas',**atlas_args)
            atlas=await operation('build_texture_atlas',**atlas_args,expected_atlas=planned['atlas_sha256'],directory='atlas')
            assert atlas['live_scene_unchanged'] and len(atlas['pixel_copy_proof'])==4
            assert all(len(p['tiles'])==2 and all(t['max_channel_error']==0 for t in p['tiles']) for p in atlas['pixel_copy_proof'])
            # Revalidate after copies of original input bundles have been removed.
            if out:
                for name in ('card_a','card_b'):shutil.copytree(library/name,out/name,dirs_exist_ok=True)
            shutil.rmtree(library/'card_a');shutil.rmtree(library/'card_b')
            await client.call_tool('open_blend',{'path':'atlas/asset.blend'})
            checked=await operation('validate_texture_bake',directory='atlas');assert checked['validated'] and checked['pixel_copy_proof']==atlas['pixel_copy_proof']
            await operation('export_objects_glb',objects=['a','b'],path='atlas.glb')
            doc,_=read_glb(library/'atlas.glb')
            assert len(doc['meshes'])==2 and len(doc['materials'])==1 and doc['materials'][0]['alphaMode']=='BLEND'
            assert all('bufferView' in i and 'uri' not in i for i in doc['images'])
            await client.call_tool('open_blend',{'path':'comparison-source.blend'})
            imported=[]
            for name in ('a','b','atlas'):
                result=(await client.call_tool('import_asset',{'path':name+'.glb'})).data;imported.append(result['objects'])
            scene=(await client.call_tool('get_scene_info',{'limit':1000})).data
            meshes={o['name'] for o in scene['objects'] if o['type']=='MESH'}
            refs=[n for group in imported[:2] for n in group if n in meshes];packed=[n for n in imported[2] if n in meshes]
            assert len(refs)==len(packed)==2
            native=[first['cluster']['object'],second['object']]
            async def visible(name,value):
                info=await operation('inspect_render_visibility',name=name)
                await operation('configure_render_visibility',name=name,expected_visibility=info['visibility_sha256'],hide_render=not value)
            for obj in scene['objects']:
                if obj['type'] in {'MESH','LIGHT'}:await visible(obj['name'],obj['name'] in native)
            env=await operation('inspect_environment')
            await operation('configure_environment',expected_environment=env['environment_sha256'],settings={'mode':'COLOR','color':[1,1,1],'strength':.5},film_transparent=True)
            verts=first['fit']['vertices_m']+fit['vertices_m'];low=[min(v[a] for v in verts) for a in range(3)];high=[max(v[a] for v in verts) for a in range(3)];unit=scene['unit_scale']
            span=max(high[a]-low[a] for a in (0,1));centre=[(a+b)/2/unit for a,b in zip(low,high)];location=centre[:];location[2]+=(max(first['fit']['source_depth_m'],fit['source_depth_m'])+span*2+1)/unit
            camera=await operation('configure_camera',name='AtlasComparison',location=location,target=centre,projection='ORTHO',ortho_scale=span*1.1/unit)
            await operation('configure_render',resolution_x=512,resolution_y=512,samples=16)
            await operation('render_still',path='native.png',camera='AtlasComparison',engine='CYCLES',width=512,height=512)
            for name in native:await visible(name,False)
            for name in refs:await visible(name,True)
            await operation('render_still',path='individual.png',camera='AtlasComparison',engine='CYCLES',width=512,height=512)
            for name in refs:await visible(name,False)
            for name in packed:await visible(name,True)
            await operation('render_still',path='atlas.png',camera='AtlasComparison',engine='CYCLES',width=512,height=512)
            comparisons={}
            for label,reference,candidate,quality in [('native_to_individual','native.png','individual.png',{}),('individual_to_atlas','individual.png','atlas.png',{'min_mask_iou':.99,'min_soft_alpha_iou':.99,'max_alpha_mae':.005,'max_premultiplied_rgb_rmse':.01}),('native_to_atlas','native.png','atlas.png',{})]:
                comparisons[label]=await operation('compare_png_images',reference=reference,candidate=candidate,scales=[1,2,4,8],quality=quality)
            after=(await client.call_tool('get_object_info',{'name':'AtlasComparison'})).data;assert after['matrix_world']==camera['matrix_world']
            if out:
                shutil.copytree(library/'atlas',out/'atlas',dirs_exist_ok=True)
                for name in ('native.png','individual.png','atlas.png','a.glb','b.glb','atlas.glb'):shutil.copy2(library/name,out/name)
                (out/'proof.json').write_text(json.dumps({'first_cluster':first['cluster'],'second_cluster':second,'fit_b':fit,'bake_b':baked,'atlas':atlas,'validation':checked,'camera':camera,'comparisons':comparisons,'seconds':time.monotonic()-start},indent=2))
            assert all(c['passed'] for c in comparisons.values()),comparisons
    asyncio.run(run())
