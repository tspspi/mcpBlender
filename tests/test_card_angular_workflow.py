"""All ten real fitted/baked/atlas/packed/delivered views via code-disabled MCP."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import math
from mcpblender import card_views,card_family_files
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_ten_direction_textured_asset_family_delivery(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            async def operation(command,**params):
                result=await wait(client,command,**params)
                if dest:=os.environ.get('MCPBLENDER_ANGULAR_EVIDENCE'):
                    out=Path(dest);out.mkdir(parents=True,exist_ok=True);(out/'progress.json').write_text(json.dumps({'command':command,'result':result},indent=2))
                return result
            await tool(client,'create_primitive',name='AngularAsset',kind='CUBE',scale=[1.2,.7,1.8])
            await client.call_tool('set_object_transform',{'name':'AngularAsset','rotation_euler':[.2,.15,.3]})
            await tool(client,'apply_material_preset',material='AngularColour',base_color=[.2,.6,.1,1],roughness=.65)
            await tool(client,'configure_shader_node',material='AngularColour',node={'name':'Checker','type':'ShaderNodeTexChecker','inputs':[{'socket':'Color1','value':[.7,.08,.02,1]},{'socket':'Color2','value':[.04,.5,.1,1]},{'socket':'Scale','value':4}]})
            await tool(client,'connect_shader_nodes',material='AngularColour',links=[{'from_node':'Checker','from_socket':'Color','to_node':'Surface','to_socket':'Base Color'}])
            await tool(client,'assign_material',objects=['AngularAsset'],material='AngularColour')
            requested=list(card_views.DIRECTIONS)
            plan=await operation('inspect_foliage_card_views',sources=['AngularAsset'],views=requested,outline='RECTANGLE',resolution=32)
            assert len(plan['views'])==10 and plan['total_card_triangles']==20 and plan['projected_triangles']==120
            bundles=[];guards={}
            for row in plan['views']:
                view=row['view'];created=await operation('create_foliage_card',**row['create_parameters'],name='Target_'+view)
                guards[view]=created
                await operation('bake_textures',**(created['bake_parameters']|{'directory':view.lower(),'width':64,'height':64,'samples':1,'margin':2,'min_projection_coverage':created['suggested_min_projection_coverage']}))
                bundles.append({'id':view.lower(),'directory':view.lower()})
            await tool(client,'configure_camera',name='ObliqueReview',projection='ORTHO')
            diagonal=next(r for r in plan['views'] if r['view']=='BACK_RIGHT')
            assert diagonal['camera_frame_view'] is None and 'direction' in diagonal['camera_frame_parameters']
            frame=await tool(client,'frame_objects',name='ObliqueReview',objects=['AngularAsset',guards['BACK_RIGHT']['object']],**diagonal['camera_frame_parameters'])
            assert frame['fully_in_frame']
            packing={'entries':bundles,'width':512,'height':256,'gutter':4}
            atlas=await operation('inspect_texture_atlas',**packing)
            await operation('build_texture_atlas',**packing,expected_atlas=atlas['atlas_sha256'],directory='atlas',threads=2)
            await client.call_tool('open_blend',{'path':'atlas/asset.blend'})
            entries=[{'view':v,'object':v.lower()} for v in requested]
            params={'directory':'atlas','entries':entries}
            family_plan=await operation('inspect_foliage_card_family_source',**params)
            family=await operation('create_foliage_card_family',**params,family_collection='AngularFamily',expected_plan=family_plan['plan_sha256'])
            assert family['valid'] and len(family['entries'])==10
            for view,direction in card_views.DIRECTIONS.items():
                selected=await operation('inspect_foliage_card_family_selection',family_collection='AngularFamily',view_direction=list(direction))
                assert selected['supported'] and selected['selected_view']==view
                family=await operation('select_foliage_card_family_view',family_collection='AngularFamily',view_direction=list(direction),expected_selection=selected['selection_sha256'])
                assert family['valid']
            for degrees in range(0,360,15):
                angle=math.radians(degrees)
                selected=await operation('inspect_foliage_card_family_selection',family_collection='AngularFamily',view_direction=[math.sin(angle),-math.cos(angle),0])
                assert selected['supported']
                nearest=next(r for r in selected['candidates'] if r['view']==selected['selected_view'])
                assert nearest['centre_angle_degrees']<=22.5+1e-9
            family=await operation('inspect_foliage_card_family',family_collection='AngularFamily')
            exported=await operation('export_foliage_card_family',family_collection='AngularFamily',expected_family=family['family_sha256'],directory='delivered')
            proof=card_family_files.validate(library/'delivered')
            assert proof['valid'] and proof['format']==card_family_files.FORMAT and len(proof['variants'])==10
            await client.call_tool('open_blend',{'path':'delivered/asset.blend'})
            restored=await operation('inspect_foliage_card_family',family_collection='AngularFamily');assert restored['valid'] and len(restored['entries'])==10
            if dest:=os.environ.get('MCPBLENDER_ANGULAR_EVIDENCE'):
                out=Path(dest);out.mkdir(parents=True,exist_ok=True)
                shutil.copytree(library/'delivered',out/'bundle',dirs_exist_ok=True)
                shutil.copytree(library/'atlas',out/'atlas',dirs_exist_ok=True)
                (out/'proof.json').write_text(json.dumps({'plan':plan,'family':family,'export':exported,'native_reopen':restored,'oblique_camera':frame},indent=2))
    asyncio.run(run())


def test_back_diagonal_and_bottom_glb_render_copy(assets_live):
    import pytest
    import time
    fixture=os.environ.get('MCPBLENDER_ANGULAR_FIXTURE')
    if not fixture:pytest.skip('Retained ten-view bundle required')
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    source=Path(fixture);shutil.copy2(source/'asset.blend',library/'angular-input.blend')
    for view in ('BACK_RIGHT','BOTTOM'):shutil.copy2(source/(view.lower()+'.glb'),library/(view.lower()+'.glb'))
    async def run():
        async with client_for(path) as client:
            await client.call_tool('open_blend',{'path':'angular-input.blend'})
            async def visible(name,value):
                state=await wait(client,'inspect_render_visibility',name=name)
                await wait(client,'configure_render_visibility',name=name,expected_visibility=state['visibility_sha256'],hide_render=not value)
            imported={}
            for view in ('BACK_RIGHT','BOTTOM'):
                result=(await client.call_tool('import_asset',{'path':view.lower()+'.glb'})).data
                meshes={r['name'] for r in (await client.call_tool('get_scene_info')).data['objects'] if r['type']=='MESH'}
                imported[view]=next(name for name in result['objects'] if name in meshes);await visible(imported[view],False)
            env=await wait(client,'inspect_environment')
            await wait(client,'configure_environment',expected_environment=env['environment_sha256'],settings={'mode':'COLOR','color':[1,1,1],'strength':.5},film_transparent=True)
            await wait(client,'configure_render',resolution_x=256,resolution_y=256,samples=16)
            await wait(client,'configure_camera',name='AngularReview',projection='ORTHO')
            async def render(filename):
                queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':filename,'camera':'AngularReview','engine':'CYCLES','width':256,'height':256}})).data;deadline=time.monotonic()+300
                while True:
                    result=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':10})).data
                    assert result['state'] not in {'failed','cancelled','interrupted'},result
                    if result['state']=='succeeded':return
                    assert time.monotonic()<deadline,('Still running; do not replay',queued['operation_id'])
            reports={}
            for view in ('BACK_RIGHT','BOTTOM'):
                direction=list(card_views.DIRECTIONS[view]);plan=await wait(client,'inspect_foliage_card_family_selection',family_collection='AngularFamily',view_direction=direction)
                assert plan['selected_view']==view
                family=await wait(client,'select_foliage_card_family_view',family_collection='AngularFamily',view_direction=direction,expected_selection=plan['selection_sha256'])
                name=family['selection']['object']
                frame=await wait(client,'frame_objects',name='AngularReview',objects=[name],direction=direction);assert frame['fully_in_frame']
                await render(view.lower()+'-native.png')
                await visible(name,False);await visible(imported[view],True)
                await render(view.lower()+'-glb.png')
                await visible(imported[view],False);await visible(name,True)
                assert (await wait(client,'inspect_foliage_card_family',family_collection='AngularFamily'))['valid']
                reports[view]=await wait(client,'compare_png_images',reference=view.lower()+'-native.png',candidate=view.lower()+'-glb.png',quality={'min_mask_iou':.99,'min_soft_alpha_iou':.99,'max_alpha_mae':.005,'max_premultiplied_rgb_rmse':.01,'max_overlap_rgb_rmse':.005})
                if dest:=os.environ.get('MCPBLENDER_ANGULAR_EVIDENCE'):
                    out=Path(dest);out.mkdir(parents=True,exist_ok=True);(out/'render-comparisons.json').write_text(json.dumps(reports,indent=2))
                    for suffix in ('-native.png','-glb.png'):shutil.copy2(library/(view.lower()+suffix),out/(view.lower()+suffix))
                assert reports[view]['passed'],reports[view]
    asyncio.run(run())
