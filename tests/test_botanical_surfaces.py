"""Structured editable botanical look development and ordinary PBR baking."""
import asyncio
import json
import os
from pathlib import Path
import shutil
from test_asset_editing import assets_live,client_for,tool,pytestmark


def test_botanical_detail_render_reopen_and_bark_bake(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            planned=await tool(client,'plan_leaf_template')
            await tool(client,'create_leaf_template',name='DetailedLeaf',expected_leaf=planned['leaf_sha256'])
            state=await tool(client,'inspect_botanical_surface',material='DetailedLeaf_Surface')
            leaf=await tool(client,'configure_botanical_surface',material=state['material'],expected_material=state['material_sha256'],settings={'profile':'OAK_LEAF'})
            assert leaf['detail_valid']
            optics=await tool(client,'inspect_foliage_material',material=state['material'])
            await tool(client,'configure_foliage_material',material=state['material'],expected_material=optics['material_sha256'],translucent_mix=.3)
            assert (await tool(client,'inspect_botanical_surface',material=state['material']))['detail_valid']
            bark=await tool(client,'create_botanical_surface',material='DetailedBark',settings={'profile':'OAK_BARK','uv_map':'UVMap'})
            await tool(client,'create_primitive',name='BarkPanel',kind='PLANE',location=[.4,0,0],scale=[.15,.15,.15])
            await tool(client,'assign_material',objects=['BarkPanel'],material='DetailedBark')
            cube=await tool(client,'inspect_render_visibility',name='Cube')
            await tool(client,'configure_render_visibility',name='Cube',expected_visibility=cube['visibility_sha256'],hide_render=True)
            await tool(client,'configure_render',resolution_x=384,resolution_y=384,samples=32)
            for name,obj in (('leaf','DetailedLeaf'),('bark','BarkPanel')):
                prefix=name.title()+'DetailView';await tool(client,'setup_preview_stage',objects=[obj],prefix=prefix,strength=.35)
                queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':name+'-detail.png','camera':prefix+'_Camera','engine':'CYCLES','width':384,'height':384}})).data
                done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data
                assert done['state']=='succeeded',done
            await client.call_tool('save_blend',{'path':'botanical-details.blend'})
            await client.call_tool('open_blend',{'path':'botanical-details.blend'})
            assert (await tool(client,'inspect_botanical_surface',material='DetailedBark'))['detail_valid']
            assert (await tool(client,'inspect_botanical_surface',material='DetailedLeaf_Surface'))['detail_valid']
            await tool(client,'generate_uv',name='BarkPanel',uv_map='DeliveryUV')
            graph=await tool(client,'inspect_shader_graph',material='DetailedBark')
            assert next(n for n in graph['nodes'] if n['type']=='ShaderNodeUVMap')['properties']['uv_map']=='UVMap'
            bake=await tool(client,'inspect_texture_bake',name='BarkPanel',uv_map='DeliveryUV')
            assert bake['complete'],bake
            result=(await client.call_tool('bake_textures',{'params':{'name':'BarkPanel','uv_map':'DeliveryUV','expected_bake':bake['bake_sha256'],'directory':'bark-pbr','width':96,'height':96,'samples':16,'maps':['NORMAL','BASE_COLOR','ROUGHNESS'],'margin':2},'wait':True})).data
            assert result['live_scene_unchanged'] and len(result['maps'])==3
            maps={v['map']:v for v in result['maps']}
            for kind in ('NORMAL','BASE_COLOR'):
                stats=maps[kind]['statistics'];assert max(a-b for a,b in zip(stats['max'][:3],stats['min'][:3]))>.05,stats
            await client.call_tool('open_blend',{'path':'bark-pbr/asset.blend'})
            checked=await tool(client,'validate_texture_bake',directory='bark-pbr');assert checked['validated']
            # Native thin-leaf lobes deliberately retain the existing bake refusal.
            # A future explicit front-PBR adapter must qualify their lossy transfer.
            if target:=os.environ.get('MCPBLENDER_SURFACE_EVIDENCE_DIR'):
                out=Path(target);out.mkdir(parents=True,exist_ok=True)
                for name in ('leaf-detail.png','bark-detail.png','botanical-details.blend'):shutil.copy2(root/'library'/name,out/name)
                shutil.copytree(root/'library/bark-pbr',out/'bark-pbr',dirs_exist_ok=True)
                (out/'proof.json').write_text(json.dumps({'leaf':leaf,'bark':bark,'bake':result},indent=2))
    asyncio.run(run())
