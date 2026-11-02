"""Independent static LODs through MCP, with arbitrary Python disabled."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_shaders import png


async def info(client,chain):return await tool(client,'inspect_lod_chain',chain=chain)


async def generate(client,name,chain,levels,**settings):
    source=await tool(client,'inspect_lod_source',name=name)
    return (await client.call_tool('generate_lod_chain',{'params':{'name':name,'chain':chain,'expected_source':source['source_sha256'],'levels':levels,**settings},'wait':True})).data


async def activate(client,chain,level):
    before=await info(client,chain)
    return await tool(client,'activate_lod_level',chain=chain,expected_chain=before['chain_sha256'],level=level)


def test_static_collapse_normal_uv_source_preservation_and_bundle(assets_live):
    root,path=assets_live
    library=root/'library';library.mkdir(exist_ok=True)
    png(library/'lod-paint.png',lambda x,y:(25,90,200) if (x//4+y//4)%2 else (60,180,240))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_primitive',name='LODSource',kind='UV_SPHERE',location=[3,0,1])
            await tool(client,'apply_material_preset',material='LODBlue',preset='TEXTURED_PBR',base_color_texture='lod-paint.png',roughness=.4)
            await tool(client,'assign_material',objects=['LODSource'],material='LODBlue')
            source=await tool(client,'inspect_lod_source',name='LODSource')
            scene=(await client.call_tool('get_scene_info')).data
            chain=await generate(client,'LODSource','SphereLOD',[{'triangle_budget':500},{'triangle_budget':150}])
            assert chain['valid'] and not chain['source_stale_or_unavailable']
            assert [l['triangles'] for l in chain['levels']]==sorted([l['triangles'] for l in chain['levels']],reverse=True)
            for i,l in enumerate(chain['levels']):
                assert l['triangles']<=l['triangle_budget'] and l['uv_maps']==source['uv_maps'] and l['materials']==['LODBlue']
                assert l['quality']['max_relative_error']<=.1 and l['hide_viewport']==(i!=0)
            assert (await tool(client,'inspect_lod_source',name='LODSource'))['source_sha256']==source['source_sha256']
            assert (await client.call_tool('get_scene_info')).data['active_object']==scene['active_object']
            active=await activate(client,'SphereLOD',2)
            assert [l['hide_render'] for l in active['levels']]==[True,True,False]
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'activate_lod_level',chain='SphereLOD',expected_chain=chain['chain_sha256'],level=0)
            await client.call_tool('save_blend',{'path':'lods.blend'})
            await client.call_tool('open_blend',{'path':'lods.blend'})
            reopened=await info(client,'SphereLOD')
            assert reopened['chain_sha256']==active['chain_sha256']
            await client.call_tool('set_object_transform',{'name':'LODSource','location':[4,0,1]})
            stale=await info(client,'SphereLOD');assert stale['valid'] and stale['source_stale_or_unavailable']
            await client.call_tool('set_object_transform',{'name':'LODSource','location':[3,0,1]})
            queued=(await client.call_tool('export_lod_chain',{'params':{'chain':'SphereLOD','expected_chain':active['chain_sha256'],'directory':'lod-bundle'}})).data
            operation=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':60})).data
            assert operation['state']=='succeeded',operation
            assert 'storage' in operation['progress']
            assert (await info(client,'SphereLOD'))['chain_sha256']==active['chain_sha256']
            exported=await tool(client,'validate_lod_export',directory='lod-bundle')
            assert exported['valid'] and len(exported['levels'])==3
            assert all(l['images']==1 and l['materials']==1 for l in exported['levels'])
            assert exported['levels'][-1]['triangles']<=150 and all(p['normals'] and p['uv_sets'] for l in exported['levels'] for p in l['primitives'])
            member=library/'lod-bundle/level_02.glb';original=member.read_bytes();member.write_bytes(original[:-1]+bytes([original[-1]^1]))
            with pytest.raises(ToolError,match='hash mismatch'):await tool(client,'validate_lod_export',directory='lod-bundle')
            member.write_bytes(original)
            imported=(await client.call_tool('import_asset',{'path':'lod-bundle/level_02.glb'})).data
            meshes=[o for o in (await client.call_tool('get_scene_info')).data['objects'] if o['type']=='MESH' and o['name'] not in {x['name'] for x in scene['objects']} and o['name'] not in {l['object'] for l in active['levels']}]
            assert meshes
            report=await tool(client,'inspect_mesh',name=meshes[-1]['name'],sample_limit=0)
            assert report['triangles']==exported['levels'][-1]['triangles'] and report['uv_layers']
            assert abs((report['world_bounds']['min'][0]+report['world_bounds']['max'][0])/2-3)<.15
            await client.call_tool('set_object_transform',{'name':'SphereLOD_Root','location':[8,0,1]})
            assert (await info(client,'SphereLOD'))['valid']
            await tool(client,'configure_render',resolution_x=192,resolution_y=192,samples=8)
            await tool(client,'setup_preview_stage',objects=['SphereLOD_LOD2'],prefix='LODView')
            await tool(client,'frame_objects',name='LODView_Camera',objects=['SphereLOD_LOD2'],direction=[0,-1,.25])
            queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':'lod_far.png','camera':'LODView_Camera','engine':'CYCLES','width':192,'height':192}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':60})).data
            assert done['state']=='succeeded',done
            rgb=subprocess.run(['ffmpeg','-v','error','-i',str(library/'lod_far.png'),'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True,timeout=20).stdout
            assert sum(b>r+25 and b>g+10 for r,g,b in zip(rgb[0::3],rgb[1::3],rgb[2::3]))>100
            await client.call_tool('save_blend',{'path':'lods.blend','overwrite':True})
            evidence=os.environ.get('MCPBLENDER_LOD_EVIDENCE_DIR')
            if evidence:
                destination=Path(evidence);destination.mkdir(parents=True,exist_ok=True)
                shutil.copy2(library/'lods.blend',destination/'lods.blend');shutil.copy2(library/'lod_far.png',destination/'lod_far.png');shutil.copytree(root/'library/lod-bundle',destination/'lod-bundle',dirs_exist_ok=True)
    asyncio.run(run())


def test_planar_unsubdivide_and_atomic_budget_refusal(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_primitive',name='GridCube')
            await tool(client,'configure_modifier',name='GridCube',modifier='Grid',settings={'type':'SUBSURF','subdivision_type':'SIMPLE','levels':2,'render_levels':2})
            before=(await client.call_tool('get_scene_info')).data
            failed_names={o['name'] for o in before['objects']}
            with pytest.raises(ToolError,match='triangle budget'):
                await generate(client,'GridCube','RefusedLOD',[{'triangle_budget':4,'method':'PLANAR'}])
            assert {o['name'] for o in (await client.call_tool('get_scene_info')).data['objects']}==failed_names
            planar=await generate(client,'GridCube','RefusedLOD',[{'triangle_budget':12,'method':'PLANAR'}])
            assert planar['levels'][1]['triangles']==12
            unsub=await generate(client,'GridCube','UnsubLOD',[{'triangle_budget':100,'method':'UNSUBDIVIDE','iterations':1}])
            assert unsub['levels'][1]['triangles']<=100
            for chain in ('RefusedLOD','UnsubLOD'):assert (await info(client,chain))['valid']
            # Owned content changes are visible and block management/export.
            await tool(client,'configure_modifier',name='UnsubLOD_LOD1',modifier='UserEdit',settings={'type':'BEVEL','width':.01})
            changed=await info(client,'UnsubLOD');assert not changed['valid']
            with pytest.raises(ToolError,match='ownership/content'):
                await tool(client,'activate_lod_level',chain='UnsubLOD',expected_chain=changed['chain_sha256'],level=0)
    asyncio.run(run())


def test_procedural_textured_building_snapshot_and_multi_material_delivery(assets_live):
    root,path=assets_live
    library=root/'library';library.mkdir(exist_ok=True)
    png(library/'building-paint.png',lambda x,y:(150,90,50) if (x//4+y//4)%2 else (220,180,120))
    async def run():
        async with client_for(path) as client:
            await tool(client,'apply_material_preset',material='LODBrick',preset='TEXTURED_PBR',base_color_texture='building-paint.png')
            await tool(client,'apply_material_preset',material='LODWindows',base_color=[.03,.09,.13,1],metallic=.5)
            await tool(client,'apply_material_preset',material='LODRoof',base_color=[.15,.13,.12,1])
            await tool(client,'create_geometry_preset',group='LODBuildingRecipe',settings={'type':'BUILDING','floors':2,'wall_material':'LODBrick','window_material':'LODWindows','roof_material':'LODRoof'})
            await tool(client,'create_primitive',name='LODBuilding',location=[12,0,0])
            await tool(client,'attach_geometry_nodes',name='LODBuilding',group='LODBuildingRecipe')
            source=await tool(client,'inspect_lod_source',name='LODBuilding')
            result=await generate(client,'LODBuilding','BuildingLOD',[{'triangle_budget':int(source['triangles']*.8)}])
            assert result['valid'] and len(source['used_material_indices'])==3
            assert result['levels'][1]['used_material_indices']==source['used_material_indices']
            assert (await tool(client,'inspect_lod_source',name='LODBuilding'))['source_sha256']==source['source_sha256']
            exported=(await client.call_tool('export_lod_chain',{'params':{'chain':'BuildingLOD','expected_chain':result['chain_sha256'],'directory':'building-lod-bundle'},'wait':True})).data
            assert exported['valid'] and all(l['materials']==3 and l['images']==1 for l in exported['levels'])
    asyncio.run(run())
