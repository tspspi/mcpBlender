"""Structured numeric fields drive a shader and survive instance-domain realization."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark


def link(a,out,b,socket):return {'from_node':a,'from_socket':out,'to_node':b,'to_socket':socket}


def test_structured_attributes_shader_instances_and_reopen(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_primitive',name='FieldCube',location=[3,0,1])
            before=await tool(client,'inspect_mesh_attributes',name='FieldCube');assert 'recovery' not in before
            created=await tool(client,'create_mesh_attribute',name='FieldCube',attribute='bend_weight',data_type='FLOAT',value=0,expected_attributes=before['attributes_sha256'])
            ramp=await tool(client,'ramp_mesh_attribute',name='FieldCube',attribute='bend_weight',axis='Z',expected_attributes=created['attributes_sha256'])
            assert {v['value'] for v in ramp['values']}=={0.,1.}
            assert ramp['geometry_sha256']==before['geometry_sha256'] and ramp['selectors']==before['selectors']
            evaluated=await tool(client,'inspect_mesh_attributes',name='FieldCube',evaluated=True)
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'set_mesh_attribute_values',name='FieldCube',attribute='bend_weight',value=.5,expected_attributes=evaluated['attributes_sha256'])
            await tool(client,'apply_material_preset',material='AttributeSurface',base_color=[1,1,1,1])
            await tool(client,'configure_shader_node',material='AttributeSurface',node={'name':'Field','type':'ShaderNodeAttribute','properties':{'attribute_name':'bend_weight','attribute_type':'GEOMETRY'}})
            await tool(client,'connect_shader_nodes',material='AttributeSurface',links=[link('Field','Fac','Surface','Base Color')])
            await tool(client,'assign_material',objects=['FieldCube'],material='AttributeSurface')
            # POINT field becomes an INSTANCE field, then survives realization.
            spec={'group':'AttributeInstances','nodes':[
                {'name':'In','type':'NodeGroupInput'},
                {'name':'Read','type':'GeometryNodeInputNamedAttribute','properties':{'data_type':'FLOAT'},'attribute':'bend_weight'},
                {'name':'Cube','type':'GeometryNodeMeshCube','inputs':[{'socket':'Size','value':[.3,.3,.3]}]},
                {'name':'Instances','type':'GeometryNodeInstanceOnPoints'},
                {'name':'Store','type':'GeometryNodeStoreNamedAttribute','properties':{'data_type':'FLOAT','domain':'INSTANCE'},'attribute':'instance_weight'},
                {'name':'Realize','type':'GeometryNodeRealizeInstances'},
                {'name':'Out','type':'NodeGroupOutput'}],
                'links':[link('In','Geometry','Instances','Points'),link('Cube','Mesh','Instances','Instance'),link('Instances','Instances','Store','Geometry'),link('Read','Attribute','Store','Value'),link('Store','Geometry','Realize','Geometry'),link('Realize','Geometry','Out','Geometry')]}
            graph=await tool(client,'configure_geometry_graph',**spec);assert graph['complete']
            attached=await tool(client,'attach_geometry_nodes',name='FieldCube',group='AttributeInstances')
            result=await tool(client,'inspect_mesh_attributes',name='FieldCube',attribute='instance_weight',evaluated=True,limit=128)
            assert result['total_values']==64 and {v['value'] for v in result['values']}=={0.,1.}
            assert sum(v['value']==0 for v in result['values'])==32
            base=await tool(client,'inspect_mesh_attributes',name='FieldCube',attribute='bend_weight')
            assert base['total_values']==8 and base['attributes_sha256']==ramp['attributes_sha256']
            # The original field can still drive a native shader after readback.
            await tool(client,'remove_modifier',name='FieldCube',modifier=attached['modifier'])
            options={'name':'FieldCube','fields':[{'attribute':'bend_weight','semantic':'wind.bend_weight'}]}
            plan=await tool(client,'inspect_attribute_export',**options)
            bundle=await tool(client,'export_attribute_bundle',**options,expected_export=plan['export_sha256'],directory='attribute-bundle')
            assert bundle['proof']['fields']==['_MCP_F00_C0'] and bundle['proof']['triangles']==12
            verified=await tool(client,'validate_attribute_bundle',directory='attribute-bundle')
            assert verified['proof']==bundle['proof']
            assert (await tool(client,'inspect_mesh_attributes',name='FieldCube'))['attributes_sha256']==ramp['attributes_sha256']

            await tool(client,'setup_preview_stage',objects=['FieldCube'],prefix='FieldView')
            await tool(client,'configure_render',resolution_x=192,resolution_y=192,samples=8)
            queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':'attribute-preview.png','camera':'FieldView_Camera','engine':'CYCLES','width':192,'height':192}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data;assert done['state']=='succeeded',done
            await client.call_tool('save_blend',{'path':'attributes.blend'})
            await client.call_tool('open_blend',{'path':'attributes.blend'})
            restored=await tool(client,'inspect_mesh_attributes',name='FieldCube',attribute='bend_weight')
            assert restored['attributes_sha256']==ramp['attributes_sha256']
            if directory:=os.environ.get('MCPBLENDER_ATTRIBUTE_EVIDENCE_DIR'):
                out=Path(directory);out.mkdir(parents=True,exist_ok=True)
                for name in ('attributes.blend','attribute-preview.png'):shutil.copy2(root/'library'/name,out/name)
                (out/'proof.json').write_text(json.dumps({'base':before,'ramp':ramp,'instances':result,'restored':restored},indent=2))
    asyncio.run(run())
    # Independent artifact readback: reject a uniformly black attribute shader.
    probe="import bpy; im=bpy.data.images.load("+repr(str(root/'library'/'attribute-preview.png'))+"); w,h=im.size; px=list(im.pixels); top=px[4*(130*w+96)]; side=px[4*(80*w+96)]; print('FIELD_RENDER',top,side); assert top>.6 and top-side>.15"
    check=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python-expr',probe],capture_output=True,text=True,timeout=60)
    assert check.returncode==0,check.stdout+'\n'+check.stderr
