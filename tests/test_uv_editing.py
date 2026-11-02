"""Actual seam unwrap, density/overlap controls and saved UV/GLB deliverables."""
import asyncio
import os
from pathlib import Path
import shutil

from fastmcp.exceptions import ToolError
import pytest

from test_asset_editing import assets_live,client_for,tool,pytestmark


async def inspect(client,name,**kw):
    return await tool(client,'inspect_uv_layout',name=name,**kw)


async def edit(client,command,name,**kw):
    current=await inspect(client,name,**{k:kw[k] for k in ('uv_map','texture_width','texture_height') if k in kw})
    return await tool(client,command,name=name,expected_uv=current['uv_sha256'],**kw)


def test_seams_unwrap_density_pack_and_delivery(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_primitive',name='UVBox',scale=[2,1,.5],location=[8,0,1])
            geometry=await tool(client,'inspect_mesh_elements',name='UVBox')
            original=await inspect(client,'UVBox')
            await tool(client,'duplicate_object',name='UVBox',new_name='UVSibling',linked_data=True,offset=[5,0,0])
            with pytest.raises(ToolError,match='shared'):
                await edit(client,'set_uv_seams','UVBox',edges={'indices':list(range(12))},mode='SET')
            await tool(client,'select_mesh_elements',name='UVBox',domain='EDGE',elements={'indices':list(range(12))},selection_name='AllSeams',expected_topology=geometry['topology_sha256'],make_single_user=True)
            seams=await edit(client,'set_uv_seams','UVBox',edges={'selection':'AllSeams'},mode='SET')
            assert seams['seam_count']==12
            sibling=await inspect(client,'UVSibling')
            assert sibling['seam_count']==0
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'unwrap_uv_mesh',name='UVBox',expected_uv=original['uv_sha256'])
            uv=await edit(client,'unwrap_uv_mesh','UVBox',uv_map='DeliveryUV',method='CONFORMAL')
            assert uv['island_count']==6 and uv['degenerate_islands']==0
            assert uv['overlap']['complete'] and uv['overlap']['face_pair_count']==0
            normalized=await edit(client,'normalize_uv_density','UVBox',uv_map='DeliveryUV',pixels_per_unit=128)
            assert all(i['pixels_per_unit']==pytest.approx(128,rel=1e-5) for i in normalized['islands'])
            packed=await edit(client,'pack_uv_islands','UVBox',uv_map='DeliveryUV',scale=False)
            assert packed['overlap']['complete'] and packed['overlap']['face_pair_count']==0
            assert all(i['pixels_per_unit']==pytest.approx(128,rel=1e-5) for i in packed['islands'])
            packed=await edit(client,'activate_uv_map','UVBox',uv_map='DeliveryUV')
            assert packed['active_uv_map']==packed['render_uv_map']=='DeliveryUV'
            unchanged=await tool(client,'inspect_mesh_elements',name='UVBox')
            assert unchanged['geometry_sha256']==geometry['geometry_sha256']
            assert unchanged['topology_sha256']==geometry['topology_sha256']
            await client.call_tool('save_blend',{'path':'uv-edited.blend'})
            await client.call_tool('open_blend',{'path':'uv-edited.blend'})
            restored=await inspect(client,'UVBox',uv_map='DeliveryUV')
            assert restored['uv_sha256']==packed['uv_sha256']
            assert (await inspect(client,'UVSibling'))['uv_sha256']==sibling['uv_sha256']
            # Original map stays untouched by editing a second named map.
            assert (await inspect(client,'UVBox'))['island_count']==original['island_count']
            await tool(client,'apply_material_preset',material='UVChecker',preset='PBR')
            await tool(client,'configure_shader_node',material='UVChecker',node={'name':'Checker','type':'ShaderNodeTexChecker','inputs':[{'socket':'Scale','value':12}]})
            await tool(client,'configure_shader_node',material='UVChecker',node={'name':'Coordinates','type':'ShaderNodeTexCoord'})
            await tool(client,'connect_shader_nodes',material='UVChecker',links=[{'from_node':'Coordinates','from_socket':'UV','to_node':'Checker','to_socket':'Vector'}])
            await tool(client,'connect_shader_nodes',material='UVChecker',links=[{'from_node':'Checker','from_socket':'Color','to_node':'Surface','to_socket':'Base Color'}])
            await tool(client,'assign_material',objects=['UVBox'],material='UVChecker')
            await client.call_tool('run_action',{'action':'preview_setup','inputs':{'objects':['UVBox'],'prefix':'UVPreview'},'wait':True})
            await tool(client,'configure_render',samples=8)
            q=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':'uv-checker.png','width':256,'height':192,'camera':'UVPreview_Camera','engine':'CYCLES'}})).data
            result=(await client.call_tool('wait_operation',{'operation_id':q['operation_id'],'timeout_seconds':60})).data
            assert result['state']=='succeeded',result
            await client.call_tool('save_blend',{'path':'uv-edited.blend','overwrite':True})
            await tool(client,'export_objects_glb',objects=['UVBox'],path='uv-box.glb')
            await client.call_tool('import_asset',{'path':'uv-box.glb'})
            scene=(await client.call_tool('get_scene_info')).data
            meshes=[o['name'] for o in scene['objects'] if o['type']=='MESH' and o['name'].startswith('UVBox') and o['name']!='UVBox']
            assert meshes,scene
            imported=await tool(client,'inspect_mesh',name=meshes[-1],evaluated=False)
            assert imported['uv_layers'] and all(u['zero_area_faces']==0 for u in imported['uv_layers'])
            layouts=[await inspect(client,meshes[-1],uv_map=u['name']) for u in imported['uv_layers']]
            assert any(q['island_count']==6 and all(i['pixels_per_unit']==pytest.approx(128,rel=1e-4) for i in q['islands']) for q in layouts),layouts
            if dest:=os.environ.get('MCPBLENDER_UV_EVIDENCE_DIR'):
                target=Path(dest);target.mkdir(parents=True,exist_ok=True)
                for name in ('uv-edited.blend','uv-box.glb','uv-checker.png'):shutil.copy2(root/'library'/name,target/name)
    asyncio.run(run())


def test_overlap_and_density_degeneracy_controls(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            # Independent coincident faces have overlapping cube-projected UVs.
            await tool(client,'create_mesh',name='OverlappingUV',vertices=[[0,0,0],[1,0,0],[0,1,0],[0,0,.1],[1,0,.1],[0,1,.1]],faces=[[0,1,2],[3,4,5]])
            await tool(client,'generate_uv',name='OverlappingUV',method='CUBE')
            overlap=await inspect(client,'OverlappingUV')
            assert overlap['island_count']==2 and overlap['overlap']['face_pair_count']==1
            bounded=await inspect(client,'OverlappingUV',overlap_budget=1)
            assert bounded['overlap']['complete']
            await edit(client,'pack_uv_islands','OverlappingUV')
            assert (await inspect(client,'OverlappingUV'))['overlap']['face_pair_count']==0
            before=await inspect(client,'OverlappingUV')
            await client.call_tool('set_object_transform',{'name':'OverlappingUV','scale':[2,1,1]})
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'normalize_uv_density',name='OverlappingUV',expected_uv=before['uv_sha256'],pixels_per_unit=128)
            density=await edit(client,'normalize_uv_density','OverlappingUV',pixels_per_unit=256,texture_width=2048,texture_height=1024)
            assert all(i['pixels_per_unit']==pytest.approx(256,rel=1e-5) for i in density['islands'])
            await client.call_tool('set_object_transform',{'name':'OverlappingUV','scale':[0,1,1]})
            degenerate=await inspect(client,'OverlappingUV')
            assert degenerate['degenerate_islands']==2
            with pytest.raises(ToolError,match='degenerate'):
                await edit(client,'normalize_uv_density','OverlappingUV',pixels_per_unit=256)
            assert (await inspect(client,'OverlappingUV'))['uv_sha256']==degenerate['uv_sha256']
            await tool(client,'create_primitive',name='BudgetUV')
            await edit(client,'set_uv_seams','BudgetUV',edges={'indices':list(range(12))},mode='SET')
            await edit(client,'unwrap_uv_mesh','BudgetUV')
            await edit(client,'unwrap_uv_mesh','BudgetUV',method='MINIMUM_STRETCH')
            incomplete=await inspect(client,'BudgetUV',overlap_budget=1)
            assert not incomplete['overlap']['complete']

    asyncio.run(run())


def test_uv_edits_preserve_skinning_shapes_and_selection(assets_live):
    _,path=assets_live
    async def run():
        from test_skeletal_animation import make_limb
        async with client_for(path) as client:
            await make_limb(client,'UVRig','UVLimb',x=30)
            await tool(client,'create_shape_key',name='UVLimb',key='Flare',vertices=[{'vertex':19,'value':[.1,0,0]}])
            shapes=await tool(client,'inspect_shape_keys',name='UVLimb')
            rig=await tool(client,'inspect_rig',name='UVRig',meshes=['UVLimb'])
            geometry=await tool(client,'inspect_mesh_elements',name='UVLimb')
            selection={name:(await client.call_tool('get_object_info',{'name':name})).data['selected'] for name in ('UVLimb','UVRig','Cube')}
            seams=await edit(client,'set_uv_seams','UVLimb',edges={'indices':[0,1]})
            assert seams['seam_count']==2
            await edit(client,'set_uv_seams','UVLimb',edges={'indices':[1]},mode='REMOVE')
            assert (await inspect(client,'UVLimb'))['seam_count']==1
            await edit(client,'unwrap_uv_mesh','UVLimb',uv_map='SkinUV')
            await edit(client,'pack_uv_islands','UVLimb',uv_map='SkinUV')
            after_shapes=await tool(client,'inspect_shape_keys',name='UVLimb')
            assert after_shapes['keys']==shapes['keys']
            after_rig=await tool(client,'inspect_rig',name='UVRig',meshes=['UVLimb'])
            assert after_rig['meshes']==rig['meshes'] and after_rig['bones']==rig['bones']
            assert (await tool(client,'inspect_mesh_elements',name='UVLimb'))['geometry_sha256']==geometry['geometry_sha256']
            assert {name:(await client.call_tool('get_object_info',{'name':name})).data['selected'] for name in selection}==selection
    asyncio.run(run())
