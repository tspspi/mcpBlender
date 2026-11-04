"""Portable all-view family delivery with Python execution disabled."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import pytest
from fastmcp.exceptions import ToolError
from mcpblender import card_family_files as files
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_trees import wait


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_PACKED_CARD_FAMILY'),reason='Retained packed family required')
def test_export_all_alternatives_and_reopen_isolated_scene(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(os.environ['MCPBLENDER_PACKED_CARD_FAMILY'],library/'input.blend')
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await client.call_tool('open_blend',{'path':'input.blend'})
            family=await wait(client,'inspect_foliage_card_family',family_collection='PackedFamily');assert family['valid']
            await client.call_tool('set_object_transform',{'name':family['root'],'location':[6,-2,3],'rotation_euler':[.3,.5,.2],'scale':[1.2]*3})
            family=await wait(client,'inspect_foliage_card_family',family_collection='PackedFamily')
            before=(await client.call_tool('get_scene_info')).data;before.pop('operation_id',None)
            exported=await wait(client,'export_foliage_card_family',family_collection='PackedFamily',expected_family=family['family_sha256'],directory='delivered')
            assert exported['live_family_unchanged'] and exported['proof']['valid']
            assert {k:v for k,v in (await client.call_tool('get_scene_info')).data.items() if k!='operation_id'}==before
            assert (await wait(client,'inspect_foliage_card_family',family_collection='PackedFamily'))['family_sha256']==family['family_sha256']
            journal=await wait(client,'inspect_export_job',directory='delivered');assert journal['record']['state']=='published' and journal['record']['kind']=='CARD_FAMILY'
            checked=await wait(client,'validate_foliage_card_family_bundle',directory='delivered')
            assert checked['valid'] and 'recovery' not in checked
            assert files.validate(library/'delivered')['selector']['origin_world_m']==pytest.approx([6,3,2])
            with pytest.raises(ToolError,match='exists'):await wait(client,'export_foliage_card_family',family_collection='PackedFamily',expected_family=family['family_sha256'],directory='delivered')
            shutil.copytree(library/'delivered',library/'relocated')
            await client.call_tool('open_blend',{'path':'relocated/asset.blend'})
            restored=await wait(client,'inspect_foliage_card_family',family_collection='PackedFamily');assert restored['valid']
            scene=(await client.call_tool('get_scene_info')).data
            assert {o['name'] for o in scene['objects']}=={restored['root'],*(e['object'] for e in restored['entries'])}
            checked=await wait(client,'validate_foliage_card_family_bundle',directory='relocated');assert checked['valid']
            if os.environ.get('MCPBLENDER_CARD_FAMILY_DELIVERY_RENDER'):
                comparisons={};imported={}
                async def visible(name,value):
                    info=await wait(client,'inspect_render_visibility',name=name)
                    await wait(client,'configure_render_visibility',name=name,expected_visibility=info['visibility_sha256'],hide_render=not value)
                async def render_image(filename):
                    queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':filename,'camera':'DeliveryReview','engine':'CYCLES','width':256,'height':256}})).data
                    deadline=time.monotonic()+300
                    while True:
                        done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':10})).data
                        if dest:=os.environ.get('MCPBLENDER_CARD_FAMILY_DELIVERY_EVIDENCE'):
                            out=Path(dest);out.mkdir(parents=True,exist_ok=True);(out/'render-progress.json').write_text(json.dumps(done,indent=2))
                        assert done['state'] not in {'failed','cancelled','interrupted'},done
                        if done['state']=='succeeded':return
                        assert time.monotonic()<deadline,('Still live; do not replay',queued['operation_id'])
                for row in checked['variants']:
                    view=row['view'];result=(await client.call_tool('import_asset',{'path':'relocated/'+view.lower()+'.glb'})).data
                    scene=(await client.call_tool('get_scene_info')).data;meshes={o['name'] for o in scene['objects'] if o['type']=='MESH'}
                    imported[view]=next(name for name in result['objects'] if name in meshes)
                    await visible(imported[view],False)
                env=await wait(client,'inspect_environment')
                await wait(client,'configure_environment',expected_environment=env['environment_sha256'],settings={'mode':'COLOR','color':[1,1,1],'strength':.5},film_transparent=True)
                await wait(client,'configure_render',resolution_x=256,resolution_y=256,samples=16)
                await wait(client,'configure_camera',name='DeliveryReview',projection='ORTHO')
                for view,normal in checked['selector']['normals_world'].items():
                    direction=[normal[0],-normal[2],normal[1]]
                    info=await wait(client,'inspect_foliage_card_family_selection',family_collection='PackedFamily',view_direction=direction)
                    selected=await wait(client,'select_foliage_card_family_view',family_collection='PackedFamily',view_direction=direction,expected_selection=info['selection_sha256'])
                    obj=selected['selection']['object']
                    await wait(client,'frame_objects',name='DeliveryReview',objects=[obj],direction=direction)
                    await render_image(view.lower()+'-native.png')
                    await visible(obj,False);await visible(imported[view],True)
                    await render_image(view.lower()+'-glb.png')
                    await visible(imported[view],False);await visible(obj,True)
                    assert (await wait(client,'inspect_foliage_card_family',family_collection='PackedFamily'))['valid']
                    comparisons[view]=await wait(client,'compare_png_images',reference=view.lower()+'-native.png',candidate=view.lower()+'-glb.png',quality={'min_mask_iou':.99,'min_soft_alpha_iou':.99,'max_alpha_mae':.005,'max_premultiplied_rgb_rmse':.01,'max_overlap_rgb_rmse':.005})
                    if dest:=os.environ.get('MCPBLENDER_CARD_FAMILY_DELIVERY_EVIDENCE'):
                        out=Path(dest);out.mkdir(parents=True,exist_ok=True);(out/'comparisons.json').write_text(json.dumps(comparisons,indent=2))
                        for suffix in ('-native.png','-glb.png'):shutil.copy2(library/(view.lower()+suffix),out/(view.lower()+suffix))
                    assert comparisons[view]['passed'],comparisons[view]
            if dest:=os.environ.get('MCPBLENDER_CARD_FAMILY_DELIVERY_EVIDENCE'):
                out=Path(dest);out.mkdir(parents=True,exist_ok=True);shutil.copytree(library/'delivered',out/'bundle',dirs_exist_ok=True)
                (out/'proof.json').write_text(json.dumps(exported,indent=2));(out/'journal.json').write_text(json.dumps(journal,indent=2))
            changed=library/'relocated/top.glb';raw=changed.read_bytes();changed.write_bytes(raw+b'tampered')
            with pytest.raises(ToolError,match='hash'):await wait(client,'validate_foliage_card_family_bundle',directory='relocated')
    asyncio.run(run())


def test_centimetre_family_delivery_and_all_map_bindings(assets_live):
    from test_texture_baking import source_scene,inspect as inspect_bake
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    script=root/'centimetres.py'
    script.write_text('import bpy\nbpy.context.scene.unit_settings.scale_length=.01\nbpy.ops.wm.save_as_mainfile(filepath='+repr(str(library/'centimetres.blend'))+')\n')
    prepared=subprocess.run(['blender','--background','--factory-startup','-t','2','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=60)
    assert prepared.returncode==0,prepared.stdout+prepared.stderr
    async def run():
        async with client_for(path) as client:
            await client.call_tool('open_blend',{'path':'centimetres.blend'})
            await source_scene(client);info=await inspect_bake(client)
            await wait(client,'bake_textures',name='BakeLow',sources=['BakeHigh'],expected_bake=info['bake_sha256'],directory='cm-bake',width=32,height=32,samples=1,margin=0,cage_extrusion=.8,max_ray_distance=2,maps=['BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','AO','EMISSION','ALPHA'])
            await client.call_tool('open_blend',{'path':'cm-bake/asset.blend'})
            params={'directory':'cm-bake','entries':[{'view':'TOP','object':'BakeLow'}]}
            plan=await wait(client,'inspect_foliage_card_family_source',**params)
            family=await wait(client,'create_foliage_card_family',**params,family_collection='CentimetreFamily',expected_plan=plan['plan_sha256'])
            await client.call_tool('set_object_transform',{'name':family['root'],'location':[12,-3,5],'rotation_euler':[.2,.4,.1],'scale':[1.3]*3})
            family=await wait(client,'inspect_foliage_card_family',family_collection='CentimetreFamily')
            exported=await wait(client,'export_foliage_card_family',family_collection='CentimetreFamily',expected_family=family['family_sha256'],directory='cm-delivered')
            checked=files.validate(library/'cm-delivered');assert checked['valid']
            assert checked['selector']['origin_world_m']==pytest.approx([.12,.05,.03])
            proof=checked['variants'][0]['proof']
            assert {'BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','AO','EMISSION'}==set(proof['map_bindings'])
            assert proof['geometry']['scene_unit_scale']==pytest.approx(.01) and proof['geometry']['world_placement_verified']
            await client.call_tool('open_blend',{'path':'cm-delivered/asset.blend'})
            restored=await wait(client,'inspect_foliage_card_family',family_collection='CentimetreFamily');assert restored['valid']
            if dest:=os.environ.get('MCPBLENDER_CARD_FAMILY_DELIVERY_EVIDENCE'):
                out=Path(dest);out.mkdir(parents=True,exist_ok=True);shutil.copytree(library/'cm-delivered',out/'centimetre-bundle',dirs_exist_ok=True)
                (out/'centimetre-proof.json').write_text(json.dumps(exported,indent=2))
    asyncio.run(run())
