"""Large placement preserves UV measurements and guarded read/edit behavior."""
import asyncio
import subprocess
from pathlib import Path
import pytest
from test_asset_editing import assets_live,client_for,tool,pytestmark


def test_large_translation_quality_admission_and_density_edit(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_primitive',name='Measured',kind='PLANE')
            await tool(client,'apply_material_preset',material='Paint',base_color=[.3,.1,.05,1])
            await tool(client,'assign_material',objects=['Measured'],material='Paint')
            async def quality():return (await client.call_tool('inspect_texture_quality',{'params':{'name':'Measured','width':128,'height':128,'min_texels_per_meter':32,'padding_pixels':0},'wait':True})).data
            near=await quality();uv_near=await tool(client,'inspect_uv_layout',name='Measured',texture_width=128,texture_height=128)
            bake_near=await tool(client,'inspect_texture_bake',name='Measured')
            await client.call_tool('set_object_transform',{'name':'Measured','location':[100000000,100000000,100000000]})
            far=await quality();uv_far=await tool(client,'inspect_uv_layout',name='Measured',texture_width=128,texture_height=128)
            assert near['passed'] and far['passed'] and far['minimum_directional_texels_per_meter']==64
            assert uv_far['islands'][0]['world_area']==uv_near['islands'][0]['world_area']==4
            assert uv_far['islands'][0]['pixels_per_unit']==64 and uv_far['degenerate_islands']==0
            assert far['quality_sha256']!=near['quality_sha256'] and uv_far['uv_sha256']!=uv_near['uv_sha256']
            bake_far=await tool(client,'inspect_texture_bake',name='Measured')
            assert bake_far['complete'] and bake_far['bake_sha256']!=bake_near['bake_sha256']
            geometry=await tool(client,'inspect_mesh',name='Measured',evaluated=False)
            edited=await tool(client,'normalize_uv_density',name='Measured',expected_uv=uv_far['uv_sha256'],texture_width=128,texture_height=128,pixels_per_unit=32)
            assert edited['islands'][0]['pixels_per_unit']==pytest.approx(32)
            assert (await tool(client,'inspect_mesh',name='Measured',evaluated=False))['geometry_sha256']==geometry['geometry_sha256']
    asyncio.run(run())


def test_native_affine_and_unit_metrics_ignore_global_translation(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'precision.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,math
from mcpblender.blender import uv,texture_quality as quality,textures
from mcpblender.texture_quality_contracts import Inspect
bpy.ops.mesh.primitive_plane_add();obj=bpy.context.object;obj.name='Plane'
parent=bpy.data.objects.new('AffineParent',None);bpy.context.scene.collection.objects.link(parent)
parent.rotation_euler.z=.3;parent.scale=(2,.5,1);obj.parent=parent;obj.rotation_euler.z=.7
material=bpy.data.materials.new('Paint');material.use_nodes=True;obj.data.materials.append(material)
p=Inspect(name=obj.name,width=128,height=128,padding_pixels=0,min_texels_per_meter=30).model_dump()
records=[]
for unit in (1,.01):
    bpy.context.scene.unit_settings.scale_length=unit;rows=[]
    for location in ((0,0,0),(100000000,-100000000,100000000)):
        parent.location=location;bpy.context.view_layer.update()
        before=textures.mesh_signature(obj,obj.data);ids=set(bpy.data.user_map())
        report=quality.inspect(p)
        _,islands,_=uv.layout(obj.data,obj.data.uv_layers['UVMap'],obj.matrix_world,128,128)
        assert report['passed'] and abs(report['minimum_directional_texels_per_meter']-32/unit)<.01/unit
        assert abs(islands[0]['world_area']-4)<1e-5
        assert textures.mesh_signature(obj,obj.data)==before and set(bpy.data.user_map())==ids
        rows.append((report,islands))
    assert rows[0][0]['minimum_directional_texels_per_meter']==rows[1][0]['minimum_directional_texels_per_meter']
    assert rows[0][1]==rows[1][1]
parent.rotation_euler=(0,0,0);obj.rotation_euler=(0,0,0);parent.scale=(0,1,1);bpy.context.view_layer.update()
assert not quality.inspect(p)['passed']
print('TRANSLATION_INDEPENDENT_UV_METRICS_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'TRANSLATION_INDEPENDENT_UV_METRICS_OK' in result.stdout
