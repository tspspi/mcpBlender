"""Native packed family lifecycle and real retained-bake selection via MCP."""
import asyncio
import json
import math
import os
from pathlib import Path
import shutil
import struct
import time
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_trees import wait


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_CARD_VIEWS_EVIDENCE'),reason='Retained view-family atlas required')
def test_packed_family_lifecycle_and_selection(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    source=Path(os.environ['MCPBLENDER_CARD_VIEWS_EVIDENCE']);shutil.copytree(source/'atlas',library/'input')
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await client.call_tool('open_blend',{'path':'input/asset.blend'})
            entries=[{'view':v,'object':v.lower()} for v in ('TOP','FRONT','SIDE')]
            params={'directory':'input','entries':entries,'accept_front_pbr':True}
            with pytest.raises(ToolError,match='accept_front_pbr'):await wait(client,'inspect_foliage_card_family_source',**(params|{'accept_front_pbr':False}))
            with pytest.raises(ToolError,match='triangle budget'):await wait(client,'inspect_foliage_card_family_source',**(params|{'max_total_triangles':10}))
            plan=await wait(client,'inspect_foliage_card_family_source',**params)
            assert 'recovery' not in plan and plan['total_triangles']==116
            with pytest.raises(ToolError,match='stale'):await wait(client,'create_foliage_card_family',**params,family_collection='PackedFamily',expected_plan='0'*64)
            family=await wait(client,'create_foliage_card_family',**params,family_collection='PackedFamily',expected_plan=plan['plan_sha256'])
            assert family['valid'] and family['selected_view'] is None and family['packed_images']==4
            assert (await wait(client,'validate_texture_bake',directory='input'))['validated']
            comparisons={};render=bool(os.environ.get('MCPBLENDER_CARD_FAMILY_RENDER'))
            async def render_image(**params):
                queued=(await client.call_tool('submit_operation',{'command':'render_still','params':params})).data
                deadline=time.monotonic()+300
                while True:
                    result=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':10})).data
                    if dest:=os.environ.get('MCPBLENDER_CARD_FAMILY_EVIDENCE'):
                        out=Path(dest);out.mkdir(parents=True,exist_ok=True);(out/'progress.json').write_text(json.dumps(result,indent=2))
                    assert result['state'] not in {'failed','cancelled','interrupted'},result
                    if result['state']=='succeeded':return result['result']
                    assert time.monotonic()<deadline,('Still live; do not replay',queued['operation_id'])

            async def visible(name,value):
                visibility=await wait(client,'inspect_render_visibility',name=name)
                await wait(client,'configure_render_visibility',name=name,expected_visibility=visibility['visibility_sha256'],hide_render=not value)
            if render:
                cameras=json.loads((source/'proof.json').read_text())['cameras']
                env=await wait(client,'inspect_environment')
                await wait(client,'configure_environment',expected_environment=env['environment_sha256'],settings={'mode':'COLOR','color':[1,1,1],'strength':.5},film_transparent=True)
                await wait(client,'configure_render',resolution_x=512,resolution_y=512,samples=16)
                for view in ('TOP','FRONT','SIDE'):
                    camera=cameras[view]
                    await wait(client,'configure_camera',name='Matched_'+view,projection='ORTHO',location=camera['location'],rotation_euler=camera['rotation_euler'],ortho_scale=camera['ortho_scale'])
                    for name in ('top','front','side'):await visible(name,name==view.lower())
                    await render_image(path=view.lower()+'-reference.png',camera='Matched_'+view,engine='CYCLES',width=512,height=512)
                for name in ('top','front','side'):await visible(name,False)
            async def state():return await wait(client,'inspect_foliage_card_family',family_collection='PackedFamily')
            family=await state();assert 'recovery' not in family
            async def choose(**kw):return await wait(client,'inspect_foliage_card_family_selection',family_collection='PackedFamily',**kw)
            async def apply(info,**kw):return await wait(client,'select_foliage_card_family_view',family_collection='PackedFamily',expected_selection=info['selection_sha256'],**kw)
            for view,direction in [('TOP',[0,0,1]),('FRONT',[0,-1,0]),('SIDE',[1,0,0])]:
                info=await choose(view_direction=direction);assert info['selected_view']==view
                family=await apply(info,view_direction=direction);assert family['valid'] and family['selected_view']==view
                if render:
                    await render_image(path=view.lower()+'-family.png',camera='Matched_'+view,engine='CYCLES',width=512,height=512)
                    comparisons[view]=await wait(client,'compare_png_images',reference=view.lower()+'-reference.png',candidate=view.lower()+'-family.png',quality={'min_mask_iou':.999,'min_soft_alpha_iou':.999,'max_alpha_mae':.001,'max_premultiplied_rgb_rmse':.001,'max_overlap_rgb_rmse':.005})
                    if dest:=os.environ.get('MCPBLENDER_CARD_FAMILY_EVIDENCE'):
                        out=Path(dest);out.mkdir(parents=True,exist_ok=True);(out/'comparisons.json').write_text(json.dumps(comparisons,indent=2))
                        for suffix in ('-reference.png','-family.png'):shutil.copy2(library/(view.lower()+suffix),out/(view.lower()+suffix))
                    assert comparisons[view]['passed'],comparisons[view]
                await wait(client,'export_objects_glb',objects=[info['object']],path=view.lower()+'-selected.glb')
                raw=(library/(view.lower()+'-selected.glb')).read_bytes();length=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+length])
                assert len(gltf['meshes'])==1 and len(gltf['materials'])==1 and len(gltf['images'])==3 # Base colour and alpha share a glTF image.
                assert all('bufferView' in image and 'uri' not in image for image in gltf['images'])
                triangles=sum(gltf['accessors'][p['indices']]['count']//3 for p in gltf['meshes'][0]['primitives'])
                assert triangles=={'TOP':34,'FRONT':49,'SIDE':33}[view]
            before=await state();info=await choose(view_direction=[0,0,-1]);assert not info['supported']
            with pytest.raises(ToolError,match='outside'):await apply(info,view_direction=[0,0,-1])
            assert (await state())['family_sha256']==before['family_sha256']
            await wait(client,'configure_camera',name='SelectionCamera',projection='ORTHO',location=[0,-20,0],target=[0,0,0])
            info=await choose(camera='SelectionCamera');assert info['selected_view']=='FRONT'
            await wait(client,'configure_camera',name='SelectionCamera',projection='ORTHO',location=[20,0,0],target=[0,0,0])
            with pytest.raises(ToolError,match='stale'):await apply(info,camera='SelectionCamera')
            info=await choose(camera='SelectionCamera');assert info['selected_view']=='SIDE'
            await apply(info,camera='SelectionCamera')
            centre=[(a+b)/2 for a,b in zip(plan['bounds_world']['min'],plan['bounds_world']['max'])]
            await wait(client,'configure_camera',name='Perspective',projection='PERSP',location=[centre[0],centre[1],centre[2]+100],target=centre)
            far=await choose(camera='Perspective');assert far['supported'] and far['selected_view']=='TOP' and far['checked_directions']==9
            await wait(client,'configure_camera',name='Perspective',projection='PERSP',location=[centre[0],centre[1],plan['bounds_world']['max'][2]+.01],target=centre)
            near=await choose(camera='Perspective');assert not near['supported']
            with pytest.raises(ToolError,match='outside'):await apply(near,camera='Perspective')
            rootname=family['root']
            await client.call_tool('set_object_transform',{'name':rootname,'rotation_euler':[0,0,math.pi/2]})
            assert (await state())['valid']
            assert (await choose(view_direction=[0,1,0]))['selected_view']=='SIDE'
            await client.call_tool('set_object_transform',{'name':rootname,'rotation_euler':[0,0,0],'scale':[2,1,1]})
            assert not (await state())['valid']
            await client.call_tool('set_object_transform',{'name':rootname,'scale':[1,1,1]})
            assert (await state())['valid']
            await client.call_tool('save_blend',{'path':'packed-family.blend'})
            shutil.move(str(library/'input'),str(root/'absent-source'))
            await client.call_tool('open_blend',{'path':'packed-family.blend'})
            family=await state();assert family['valid'] and not family['source_files_required']
            info=await choose(view_direction=[0,0,1]);family=await apply(info,view_direction=[0,0,1])
            await wait(client,'export_objects_glb',objects=[family['selection']['object']],path='selected.glb')
            if dest:=os.environ.get('MCPBLENDER_CARD_FAMILY_EVIDENCE'):
                out=Path(dest);out.mkdir(parents=True,exist_ok=True)
                (out/'family.json').write_text(json.dumps(family,indent=2));(out/'comparisons.json').write_text(json.dumps(comparisons,indent=2));shutil.copy2(library/'packed-family.blend',out/'packed-family.blend');shutil.copy2(library/'selected.glb',out/'selected.glb')
                for view in ('top','front','side'):
                    shutil.copy2(library/(view+'-selected.glb'),out/(view+'-selected.glb'))
                    if render:
                        for suffix in ('-reference.png','-family.png'):shutil.copy2(library/(view+suffix),out/(view+suffix))
            # Edited content and outside users cannot be removed as an intact family.
            selected=family['selection']['object']
            details=(await client.call_tool('get_object_info',{'name':selected})).data
            await client.call_tool('set_object_transform',{'name':selected,'location':[v+1 for v in details['location']]})
            edited=await state();assert not edited['valid']
            with pytest.raises(ToolError,match='changed'):await wait(client,'remove_foliage_card_family',family_collection='PackedFamily',expected_family=edited['family_sha256'])
            await client.call_tool('open_blend',{'path':'packed-family.blend'})
            family=await state();selected=next(e['object'] for e in family['entries'] if e['view']==family['selected_view'])
            await wait(client,'duplicate_object',name=selected,new_name='ExternalLinkedCopy',linked_data=True)
            blocked=await state();assert not blocked['valid'] and blocked['ownership_blockers']
            with pytest.raises(ToolError,match='externally'):await wait(client,'remove_foliage_card_family',family_collection='PackedFamily',expected_family=blocked['family_sha256'])
            await client.call_tool('open_blend',{'path':'packed-family.blend'})
            guard=(await state())['family_sha256']
            with pytest.raises(ToolError,match='stale'):await wait(client,'remove_foliage_card_family',family_collection='PackedFamily',expected_family='0'*64)
            result=await wait(client,'remove_foliage_card_family',family_collection='PackedFamily',expected_family=guard)
            assert result['removed']
            scene=(await client.call_tool('get_scene_info')).data
            assert {'top','front','side'}<={o['name'] for o in scene['objects']}
    asyncio.run(run())


def test_family_packs_all_maps_and_preserves_gltf_occlusion(assets_live):
    from test_texture_baking import source_scene,inspect as inspect_bake
    root,path=assets_live;(root/'library').mkdir(exist_ok=True)
    async def run():
        async with client_for(path) as client:
            await source_scene(client);info=await inspect_bake(client)
            await wait(client,'bake_textures',name='BakeLow',sources=['BakeHigh'],expected_bake=info['bake_sha256'],directory='allmaps',width=32,height=32,samples=1,margin=0,cage_extrusion=.8,max_ray_distance=2,maps=['BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','AO','EMISSION','ALPHA'])
            await client.call_tool('open_blend',{'path':'allmaps/asset.blend'})
            params={'directory':'allmaps','entries':[{'view':'TOP','object':'BakeLow'}]}
            plan=await wait(client,'inspect_foliage_card_family_source',**params)
            chain=plan['provenance']['source_placements'][0]['placement_chain']
            assert len(chain)==2 and chain[0]['parent']==chain[1]['name']
            # Reparenting can retain identical world geometry; the family guard
            # still binds the static placement chain rather than only its product.
            await wait(client,'set_parent',name='BakeLow',parent=None,keep_world=True)
            assert (await wait(client,'validate_texture_bake',directory='allmaps'))['validated']
            detached=await wait(client,'inspect_foliage_card_family_source',**params)
            assert detached['plan_sha256']!=plan['plan_sha256']
            with pytest.raises(ToolError,match='stale'):await wait(client,'create_foliage_card_family',**params,family_collection='AOFamily',expected_plan=plan['plan_sha256'])
            await client.call_tool('open_blend',{'path':'allmaps/asset.blend'})
            await wait(client,'set_keyframes',name=chain[1]['name'],data_path='location',keyframes=[{'frame':1,'value':[0,0,0]},{'frame':2,'value':[0,0,0]}])
            with pytest.raises(ToolError,match='static'):await wait(client,'inspect_foliage_card_family_source',**params)
            await client.call_tool('open_blend',{'path':'allmaps/asset.blend'})
            restored=await wait(client,'inspect_foliage_card_family_source',**params)
            assert restored['plan_sha256']==plan['plan_sha256']
            family=await wait(client,'create_foliage_card_family',**params,family_collection='AOFamily',expected_plan=plan['plan_sha256'])
            assert family['valid'] and family['packed_images']==7
            direction={'family_collection':'AOFamily','view_direction':[0,0,1]}
            selected=await wait(client,'inspect_foliage_card_family_selection',**direction)
            await wait(client,'select_foliage_card_family_view',**direction,expected_selection=selected['selection_sha256'])
            await client.call_tool('save_blend',{'path':'ao-family.blend'})
            shutil.move(str(root/'library/allmaps'),str(root/'absent-allmaps'))
            await client.call_tool('open_blend',{'path':'ao-family.blend'})
            family=await wait(client,'inspect_foliage_card_family',family_collection='AOFamily');assert family['valid']
            await wait(client,'export_objects_glb',objects=[selected['object']],path='ao-family.glb')
            raw=(root/'library/ao-family.glb').read_bytes();length=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+length]);material=gltf['materials'][0]
            assert {'occlusionTexture','normalTexture','emissiveTexture'}<=material.keys()
            assert {'baseColorTexture','metallicRoughnessTexture'}<=material['pbrMetallicRoughness'].keys()
            assert all('bufferView' in image and 'uri' not in image for image in gltf['images'])
            if dest:=os.environ.get('MCPBLENDER_CARD_FAMILY_EVIDENCE'):
                out=Path(dest);out.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'library/ao-family.glb',out/'ao-family.glb')
                (out/'ao-family.json').write_text(json.dumps(family,indent=2))
            await wait(client,'remove_foliage_card_family',family_collection='AOFamily',expected_family=family['family_sha256'])
    asyncio.run(run())
