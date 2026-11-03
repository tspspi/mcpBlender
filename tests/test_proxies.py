"""Python-disabled procedural collider use and textured shadow delivery."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_assemblies import create,place
from test_physics import physics
from test_shaders import png
from mcpblender.lod_files import glb_report


async def generate(client,collection,**settings):
    plan=await tool(client,'inspect_asset_proxy_source',**settings)
    job=(await client.call_tool('generate_asset_proxies',{'params':settings|{'collection':collection,'expected_source':plan['source_sha256']}})).data
    done=(await client.call_tool('wait_operation',{'operation_id':job['operation_id'],'timeout_seconds':90})).data
    assert done['state']=='succeeded' and 'storage' in done['progress'],done
    return done['result'],plan


def test_procedural_building_proxy_drop_and_textured_shadow_export(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    png(library/'proxy-texture.png',lambda x,y:(35,100,180) if x%4 else (180,200,220))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            graph=await tool(client,'create_geometry_preset',group='ProxyBuildingRecipe',settings={'type':'BUILDING','floors':2})
            await tool(client,'create_primitive',name='ProxyBuildingSource')
            await tool(client,'attach_geometry_nodes',name='ProxyBuildingSource',group=graph['group'])
            await create(client,['ProxyBuildingSource'],'ProxyBuildingAsset')
            placed=await place(client,'ProxyBuildingAsset','ProxyBuildingOne',10)
            generated,plan=await generate(client,'BuildingCollider',objects=['ProxyBuildingOne'],method='CONVEX_HULL')
            assert generated['valid'] and generated['source_matches'] and generated['total_proxies']==1
            collider=generated['proxies'][0];assert collider['volume']>0 and collider['mesh']['triangles']<plan['triangles']
            assert collider['quality']['max_sampled_outside_distance']<1e-4 and collider['hide_render']
            assert (await tool(client,'inspect_asset_instance',name='ProxyBuildingOne'))['instance_sha256']==placed['instance_sha256']
            await physics(client,'configure_rigid_world',frame_end=60)
            await physics(client,'configure_rigid_body',name=collider['name'],type='PASSIVE',collision_shape=collider['suggested_collision_shape'],reset_unbaked=True)
            await tool(client,'create_primitive',name='ProxyDrop',location=[10,0,10])
            await physics(client,'configure_rigid_body',name='ProxyDrop',collision_shape='BOX',reset_unbaked=True)
            sample=await physics(client,'sample_rigid_bodies',objects=['ProxyDrop'],sample_frames=[1,24,60])
            heights=[s['poses']['ProxyDrop'][2][3] for s in sample['samples']]
            assert heights[0]==pytest.approx(10) and heights[1]<heights[0]
            assert heights[-1]==pytest.approx(placed['world_bounds']['max'][2]+1,abs=.1),heights
            current=await tool(client,'inspect_asset_proxies',collection='BuildingCollider')
            with pytest.raises(ToolError,match='physics'):
                await tool(client,'remove_asset_proxies',collection='BuildingCollider',expected_proxy=current['proxy_sha256'])
            await physics(client,'remove_rigid_body',name=collider['name'],reset_unbaked=True)
            # A textured high-resolution prop supplies a reduced shadow representation.
            await tool(client,'create_primitive',name='ProxySphere',kind='UV_SPHERE',location=[30,0,2])
            await tool(client,'apply_material_preset',material='ProxyBlue',preset='TEXTURED_PBR',base_color_texture='proxy-texture.png')
            await tool(client,'assign_material',objects=['ProxySphere'],material='ProxyBlue')
            visibility=await tool(client,'inspect_render_visibility',name='ProxySphere')
            patched=await tool(client,'configure_render_visibility',name='ProxySphere',expected_visibility=visibility['visibility_sha256'],visible_shadow=False)
            assert not patched['visibility']['visible_shadow']
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'configure_render_visibility',name='ProxySphere',expected_visibility=visibility['visibility_sha256'],visible_shadow=True)
            shadow,shadow_plan=await generate(client,'PropShadow',objects=['ProxySphere'],purpose='SHADOW',method='DECIMATE',triangle_budget=150,max_relative_error=.2)
            prop=shadow['proxies'][0]
            assert prop['mesh']['triangles']<=150 and prop['mesh']['triangles']<shadow_plan['triangles'] and prop['mesh']['uv_maps']
            assert prop['ray_visibility']['visible_shadow'] and not prop['ray_visibility']['visible_camera']
            await tool(client,'export_objects_glb',objects=[prop['name']],path='shadow-proxy.glb',animations=False)
            decoded=glb_report(library/'shadow-proxy.glb')
            assert decoded['triangles']==prop['mesh']['triangles'] and decoded['images']==1
            await client.call_tool('save_blend',{'path':'asset-proxies.blend'})
            await client.call_tool('open_blend',{'path':'asset-proxies.blend'})
            assert (await tool(client,'inspect_asset_proxies',collection='PropShadow'))['valid']
            await client.call_tool('set_object_transform',{'name':'ProxySphere','location':[31,0,2]})
            changed=await tool(client,'inspect_asset_proxies',collection='PropShadow')
            assert changed['valid'] and not changed['source_matches']
            with pytest.raises(ToolError,match='stale'):
                await client.call_tool('generate_asset_proxies',{'params':{'objects':['ProxySphere'],'purpose':'SHADOW','method':'DECIMATE','triangle_budget':150,'max_relative_error':.2,'collection':'OldSource','expected_source':shadow_plan['source_sha256']},'wait':True})
            if evidence:=os.environ.get('MCPBLENDER_PROXY_EVIDENCE_DIR'):
                out=Path(evidence);out.mkdir(parents=True,exist_ok=True)
                for name in ('asset-proxies.blend','shadow-proxy.glb'):shutil.copy2(library/name,out/name)
                (out/'proxy-proof.json').write_text(json.dumps({'collider':generated,'drop_heights':heights,'shadow':shadow,'decoded':decoded},indent=2))
    asyncio.run(run())
