"""Three fitted dense-cluster alternatives, independent bakes, atlas and matched views."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import time
import pytest
from test_asset_editing import assets_live,client_for,pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_CARD_VIEWS_FIXTURE'),reason='Retained corrected dense source required')
def test_dense_view_family_bakes_atlas_and_matched_images(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    fixture=Path(os.environ['MCPBLENDER_CARD_VIEWS_FIXTURE']);original=json.loads((fixture/'proof.json').read_text());source=original['cluster']['object']
    bundle=next(p for p in fixture.iterdir() if p.is_dir() and (p/'source.blend').is_file());shutil.copy2(bundle/'source.blend',library/'input.blend')
    size=int(os.environ.get('MCPBLENDER_CARD_VIEW_TEXTURE_SIZE','256'))
    sizes=json.loads(os.environ.get('MCPBLENDER_CARD_VIEW_TEXTURE_SIZES','{}'))
    sizes={v:sizes.get(v,size) for v in ('TOP','FRONT','SIDE')}
    assert all(type(n)==int and n in (256,512,1024) for n in sizes.values())
    largest=max(sizes.values());aw=1024 if largest==256 else 2048;ah=512 if largest==256 else 1024 if largest==512 else 2048
    assert sum(n+16 for n in sizes.values())<=aw and largest+16<=ah
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            start=time.monotonic();out=Path(os.environ['MCPBLENDER_CARD_VIEWS_EVIDENCE']) if os.environ.get('MCPBLENDER_CARD_VIEWS_EVIDENCE') else None
            if out:out.mkdir(parents=True,exist_ok=True)
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data;deadline=time.monotonic()+600
                while True:
                    state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':10})).data
                    if out:(out/'progress.json').write_text(json.dumps({'command':command,'operation_id':queued['operation_id'],'state':state['state'],'progress':state.get('progress'),'storage':state.get('storage'),'error':state.get('error'),'seconds':time.monotonic()-start},indent=2))
                    assert state['state'] not in {'failed','cancelled','interrupted'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline,('Still live; do not replay',queued['operation_id'])
            await client.call_tool('open_blend',{'path':'input.blend'})
            family=await operation('inspect_foliage_card_views',sources=[source],thin_foliage_mode='FRONT_PBR')
            assert 'recovery' not in family and family['source_triangles']==90552 and family['projected_triangles']==271656
            created={};bakes={}
            for row in family['views']:
                view=row['view'];created[view]=await operation('create_foliage_card',**row['create_parameters'],name='Family_'+view)
                assert created[view]['card']['card_sha256']==row['card']['card_sha256']
                bakes[view]=await operation('bake_textures',**(created[view]['bake_parameters']|{'directory':view.lower(),'width':sizes[view],'height':sizes[view],'samples':8,'margin':2,'min_projection_coverage':created[view]['suggested_min_projection_coverage']}))
                assert bakes[view]['live_scene_unchanged'] and bakes[view]['map_policy']['alpha_margin']==0
            await client.call_tool('save_blend',{'path':'family-source.blend'})
            for view in created:
                await client.call_tool('open_blend',{'path':view.lower()+'/asset.blend'})
                assert (await operation('validate_texture_bake',directory=view.lower()))['validated']
                await operation('export_objects_glb',objects=[created[view]['object']],path=view.lower()+'.glb')
            atlasargs={'entries':[{'id':v.lower(),'directory':v.lower()} for v in created],'width':aw,'height':ah,'gutter':8}
            plan=await operation('inspect_texture_atlas',**atlasargs)
            atlas=await operation('build_texture_atlas',**atlasargs,expected_atlas=plan['atlas_sha256'],directory='atlas')
            assert all(len(p['tiles'])==3 for p in atlas['pixel_copy_proof'])
            await client.call_tool('open_blend',{'path':'atlas/asset.blend'})
            assert (await operation('validate_texture_bake',directory='atlas'))['validated']
            await operation('export_objects_glb',objects=[v.lower() for v in created],path='atlas.glb')
            await client.call_tool('open_blend',{'path':'family-source.blend'})
            imported={}
            for view in created:
                result=(await client.call_tool('import_asset',{'path':view.lower()+'.glb'})).data;imported[view]=result['objects']
            packed=(await client.call_tool('import_asset',{'path':'atlas.glb'})).data['objects']
            scene=(await client.call_tool('get_scene_info',{'limit':1000})).data;meshes={o['name'] for o in scene['objects'] if o['type']=='MESH'}
            refs={v:next(n for n in ns if n in meshes) for v,ns in imported.items()};atlasobjs={v:next(n for n in packed if n==v.lower()) for v in created}
            async def visible(name,value):
                info=await operation('inspect_render_visibility',name=name)
                await operation('configure_render_visibility',name=name,expected_visibility=info['visibility_sha256'],hide_render=not value)
            for obj in scene['objects']:
                if obj['type'] in {'MESH','LIGHT'}:await visible(obj['name'],False)
            env=await operation('inspect_environment')
            await operation('configure_environment',expected_environment=env['environment_sha256'],settings={'mode':'COLOR','color':[1,1,1],'strength':.5},film_transparent=True)
            await operation('configure_render',resolution_x=512,resolution_y=512,samples=16)
            await operation('configure_camera',name='FamilyCamera',projection='ORTHO')
            comparisons={};cameras={}
            for row in family['views']:
                view=row['view'];await visible(source,True)
                camera=await operation('frame_objects',name='FamilyCamera',objects=[source,created[view]['object']],view=row['camera_frame_view'],margin=1.1)
                assert camera['fully_in_frame'];cameras[view]=camera
                await operation('render_still',path=view.lower()+'-native.png',camera='FamilyCamera',engine='CYCLES',width=512,height=512)
                await visible(source,False);await visible(refs[view],True)
                await operation('render_still',path=view.lower()+'-individual.png',camera='FamilyCamera',engine='CYCLES',width=512,height=512)
                await visible(refs[view],False);await visible(atlasobjs[view],True)
                await operation('render_still',path=view.lower()+'-atlas.png',camera='FamilyCamera',engine='CYCLES',width=512,height=512)
                await visible(atlasobjs[view],False)
                after=(await client.call_tool('get_object_info',{'name':'FamilyCamera'})).data;assert after['matrix_world']==camera['matrix_world']
                comparisons[view]={}
                for label,reference,candidate,quality in [('native_to_individual','native','individual',{}),('individual_to_atlas','individual','atlas',{'min_mask_iou':.99,'min_soft_alpha_iou':.99,'max_alpha_mae':.005,'max_premultiplied_rgb_rmse':.01}),('native_to_atlas','native','atlas',{})]:
                    comparisons[view][label]=await operation('compare_png_images',reference=view.lower()+'-'+reference+'.png',candidate=view.lower()+'-'+candidate+'.png',scales=[1,2,4,8],quality=quality)
                if out:
                    for suffix in ('native','individual','atlas'):shutil.copy2(library/(view.lower()+'-'+suffix+'.png'),out/(view.lower()+'-'+suffix+'.png'))
                    (out/'measurements.json').write_text(json.dumps(comparisons,indent=2))
            if out:
                for name in ('top','front','side','atlas'):shutil.copytree(library/name,out/name,dirs_exist_ok=True);shutil.copy2(library/(name+'.glb'),out/(name+'.glb'))
                (out/'proof.json').write_text(json.dumps({'family':family,'created':created,'bakes':bakes,'atlas':atlas,'cameras':cameras,'comparisons':comparisons,'texture_sizes':sizes,'seconds':time.monotonic()-start},indent=2))
            assert all(c['passed'] for group in comparisons.values() for c in group.values()),comparisons
    asyncio.run(run())
