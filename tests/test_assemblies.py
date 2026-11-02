"""Reusable textured procedural buildings and editable rig graphs through MCP."""
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
from test_skeletal_animation import make_limb
from test_animation_drivers import configure as drive


async def create(client,objects,collection):
    plan=await tool(client,'inspect_asset_assembly_source',objects=objects)
    assert plan['can_create'],plan
    job=(await client.call_tool('create_asset_assembly',{'params':{'objects':objects,'collection':collection,'expected_source':plan['source_sha256']}})).data
    done=(await client.call_tool('wait_operation',{'operation_id':job['operation_id'],'timeout_seconds':90})).data
    assert done['state']=='succeeded' and 'storage' in done['progress'],done
    assert 'temporary_storage' in done['result']
    return done['result']


async def place(client,asset,name,x):
    current=await tool(client,'inspect_asset_assembly',collection=asset)
    return await tool(client,'place_asset_instance',collection=asset,expected_asset=current['assembly_sha256'],name=name,location=[x,0,0])


def test_procedural_textured_building_prototype_preview_and_reopen(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    png(library/'assembly-brick.png',lambda x,y:(150,95,60) if y%4 and (x+(4 if y//4%2 else 0))%8 else (210,205,190))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'apply_material_preset',material='AssemblyBrick',preset='TEXTURED_PBR',base_color_texture='assembly-brick.png',texture_scale=[4,4,4])
            await tool(client,'apply_material_preset',material='AssemblyWindows',base_color=[.04,.13,.2,1],metallic=.6,roughness=.2)
            await tool(client,'apply_material_preset',material='AssemblyRoof',base_color=[.12,.14,.16,1])
            graph=await tool(client,'create_geometry_preset',group='AssemblyBuildingRecipe',settings={'type':'BUILDING','floors':2,'wall_material':'AssemblyBrick','window_material':'AssemblyWindows','roof_material':'AssemblyRoof'})
            await tool(client,'create_primitive',name='AssemblySource',location=[0,0,0])
            await tool(client,'attach_geometry_nodes',name='AssemblySource',group='AssemblyBuildingRecipe')
            source=await tool(client,'inspect_mesh',name='AssemblySource',sample_limit=0)
            asset=await create(client,['AssemblySource'],'BuildingAsset');assert asset['valid'] and not asset['editing']
            component=asset['copied_objects']['AssemblySource']
            a=await place(client,'BuildingAsset','BuildingOne',20);b=await place(client,'BuildingAsset','BuildingTwo',40)
            assert a['world_bounds']['max'][2]==pytest.approx(6.2) and b['world_bounds']['min'][0]-a['world_bounds']['min'][0]==pytest.approx(20)
            opened=await tool(client,'set_asset_assembly_editing',collection='BuildingAsset',expected_asset=(await tool(client,'inspect_asset_assembly',collection='BuildingAsset'))['assembly_sha256'],enabled=True)
            native=await tool(client,'inspect_mesh',name=component,sample_limit=0);group=native['modifiers'][0]['group']
            assert group!='AssemblyBuildingRecipe'
            copied=await tool(client,'inspect_geometry_graph',group=group)
            await tool(client,'configure_geometry_inputs',name=component,expected_graph=copied['graph_sha256'],values=[{'socket':'Floors','value':3}])
            changed=await tool(client,'inspect_asset_assembly',collection='BuildingAsset');assert changed['assembly_sha256']!=opened['assembly_sha256']
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'place_asset_instance',collection='BuildingAsset',expected_asset=opened['assembly_sha256'],name='StalePlacement')
            await tool(client,'set_asset_assembly_editing',collection='BuildingAsset',expected_asset=changed['assembly_sha256'],enabled=False)
            updated=await tool(client,'inspect_asset_instance',name='BuildingOne')
            assert updated['world_bounds']['max'][2]==pytest.approx(9.2)
            assert (await tool(client,'inspect_mesh',name='AssemblySource',sample_limit=0))['geometry_sha256']==source['geometry_sha256']
            assert (await tool(client,'inspect_asset_instance',name='BuildingTwo'))['world_bounds']['max'][2]==pytest.approx(9.2)
            await tool(client,'configure_render',resolution_x=192,resolution_y=192,samples=8)
            stage=await tool(client,'setup_preview_stage',objects=['BuildingOne'],prefix='AssemblyView')
            fit=await tool(client,'frame_objects',name='AssemblyView_Camera',objects=['BuildingOne'])
            assert fit['fully_in_frame']
            job=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':'assembly-preview.png','camera':'AssemblyView_Camera','engine':'CYCLES','width':192,'height':192}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':job['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded',done
            rgb=subprocess.run(['ffmpeg','-v','error','-i',str(library/'assembly-preview.png'),'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True,timeout=20).stdout
            assert len(rgb)==192*192*3 and sum(r>g+10 and g>b+5 for r,g,b in zip(rgb[0::3],rgb[1::3],rgb[2::3]))>100
            await client.call_tool('save_blend',{'path':'assemblies.blend'})
            await client.call_tool('open_blend',{'path':'assemblies.blend'})
            restored=await tool(client,'inspect_asset_instance',name='BuildingOne');assert restored['world_bounds']==updated['world_bounds']
            if evidence:=os.environ.get('MCPBLENDER_ASSEMBLY_EVIDENCE_DIR'):
                out=Path(evidence);out.mkdir(parents=True,exist_ok=True)
                for name in ('assemblies.blend','assembly-preview.png'):shutil.copy2(library/name,out/name)
                (out/'assembly-proof.json').write_text(json.dumps({'asset':asset,'changed':changed,'instance':restored},indent=2))
    asyncio.run(run())


def test_copied_managed_rig_driver_remains_typed_editable(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await make_limb(client,'AssemblyRig','AssemblySkin',x=0)
            await tool(client,'set_animation_property',name='AssemblyRig',property='Bend',value=.2)
            channel={'kind':'TRANSFORM','bone':'Tip','property':'rotation_euler','component':0}
            settings={'expression':'bend','variables':[{'kind':'PROPERTY','name':'bend','object':'AssemblyRig','property':'Bend'}]}
            await drive(client,'AssemblyRig',channel,settings)
            asset=await create(client,['AssemblyRig','AssemblySkin'],'RigAsset')
            newrig=asset['copied_objects']['AssemblyRig'];newskin=asset['copied_objects']['AssemblySkin']
            await place(client,'RigAsset','RigOne',10)
            current=await tool(client,'inspect_asset_assembly',collection='RigAsset')
            await tool(client,'set_asset_assembly_editing',collection='RigAsset',expected_asset=current['assembly_sha256'],enabled=True)
            drivers=await tool(client,'inspect_animation_drivers',name=newrig)
            assert drivers['drivers'][0]['typed_editable'] and drivers['drivers'][0]['settings']['variables'][0]['object']==newrig
            await tool(client,'set_animation_property',name=newrig,property='Bend',value=.8)
            changed=await tool(client,'inspect_asset_instance',name='RigOne');assert changed['world_bounds']
            original=await tool(client,'inspect_animation_drivers',name='AssemblyRig')
            assert original['drivers'][0]['settings']['variables'][0]['object']=='AssemblyRig'
            assert (await tool(client,'inspect_mesh',name=newskin,sample_limit=0))['geometry_sha256']!=(await tool(client,'inspect_mesh',name='AssemblySkin',sample_limit=0))['geometry_sha256']
    asyncio.run(run())
