"""Structured MCP admission and an isolated bake retain the measured policy."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark


def test_quality_gate_and_bake_witness(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_primitive',name='QualityPlane',kind='PLANE')
            await tool(client,'apply_material_preset',material='QualityPaint',base_color=[.3,.1,.05,1])
            await tool(client,'assign_material',objects=['QualityPlane'],material='QualityPaint')
            low={'width':32,'height':32,'min_texels_per_meter':32,'padding_pixels':0,'mip_levels':1}
            async def quality(policy):
                return (await client.call_tool('inspect_texture_quality',{'params':{'name':'QualityPlane',**policy},'wait':True})).data
            failed=await quality(low)
            assert failed['complete'] and not failed['passed'] and failed['minimum_directional_texels_per_meter']==16
            high=low|{'width':128,'height':128}
            passed=await quality(high)
            assert passed['passed'] and passed['minimum_directional_texels_per_meter']==64
            assert passed['quality_sha256']==(await quality(high))['quality_sha256']
            assert not (await quality(high|{'padding_pixels':2}))['passed']
            assert not (await quality(high|{'max_raster_tests':1}))['complete']
            original=await tool(client,'inspect_texture_bake',name='QualityPlane')
            refused=await tool(client,'inspect_texture_bake',name='QualityPlane',quality=low)
            assert not refused['complete'] and refused['bake_sha256'] is None
            common={'name':'QualityPlane','maps':['BASE_COLOR','NORMAL'],'samples':1,'margin':0}
            with pytest.raises(ToolError,match='quality gate'):
                await client.call_tool('bake_textures',{'params':common|{'expected_bake':original['bake_sha256'],'quality':low,'width':32,'height':32,'directory':'refused'},'wait':True})
            assert not (root/'library/refused').exists()
            admitted=await tool(client,'inspect_texture_bake',name='QualityPlane',quality=high)
            assert admitted['complete'] and admitted['bake_sha256']!=original['bake_sha256']
            result=(await client.call_tool('bake_textures',{'params':common|{'expected_bake':admitted['bake_sha256'],'quality':high,'width':128,'height':128,'directory':'quality-baked'},'wait':True})).data
            assert result['live_scene_unchanged']
            assert (await tool(client,'inspect_texture_bake',name='QualityPlane'))['bake_sha256']==original['bake_sha256']
            saved=json.loads((root/'library/quality-baked/manifest.json').read_text())
            assert saved['texture_quality']['passed'] and saved['texture_quality']['policy']['width']==128
            assert saved['texture_quality']['minimum_directional_texels_per_meter']==64
            if dest:=os.environ.get('MCPBLENDER_TEXTURE_QUALITY_EVIDENCE_DIR'):
                target=Path(dest);target.mkdir(parents=True,exist_ok=True)
                shutil.copytree(root/'library/quality-baked',target/'baked',dirs_exist_ok=True)
                (target/'proof.json').write_text(json.dumps({'failed':failed,'passed':passed,'manifest':saved},indent=2))
            await client.call_tool('open_blend',{'path':'quality-baked/asset.blend'})
            assert (await tool(client,'validate_texture_bake',directory='quality-baked'))['validated']
    asyncio.run(run())


def test_native_physical_units_shear_and_no_mutations(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'quality.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from mathutils import Matrix
from mcpblender.blender import texture_quality as quality,textures
from mcpblender.texture_quality_contracts import Inspect
bpy.ops.mesh.primitive_plane_add(size=2);obj=bpy.context.object;obj.name='Measured'
p=Inspect(name=obj.name,width=128,height=128,padding_pixels=0,min_texels_per_meter=32).model_dump()
before=textures.mesh_signature(obj,obj.data);ids=set(bpy.data.user_map())
base=quality.inspect(p);assert base['passed'] and base['minimum_directional_texels_per_meter']==64
assert textures.mesh_signature(obj,obj.data)==before and set(bpy.data.user_map())==ids
obj.scale=(100,100,100);bpy.context.scene.unit_settings.scale_length=.01
assert abs(quality.inspect(p)['minimum_directional_texels_per_meter']-64)<1e-4
obj.scale=(1000,10,100)
stretched=quality.inspect(p)
assert not stretched['passed'] and abs(stretched['minimum_directional_texels_per_meter']-6.4)<1e-4
obj.matrix_world=Matrix(((1,1,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)))
bpy.context.scene.unit_settings.scale_length=1
sheared=quality.inspect(p)
assert sheared['minimum_directional_texels_per_meter']<64 and sheared['quality_sha256']!=base['quality_sha256']
print('TEXTURE_QUALITY_NATIVE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'TEXTURE_QUALITY_NATIVE_OK' in result.stdout
