"""Baked emission applies disabled, constant and linked source strengths."""
import asyncio
import json
import subprocess
from pathlib import Path
from test_asset_editing import assets_live,client_for,tool,pytestmark
from mcpblender.texture_files import EMISSION_ENCODING


def test_emission_maps_include_principled_strength(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_primitive',name='Surface',kind='PLANE')
            await tool(client,'apply_material_preset',material='Glow',base_color=[.2,.1,.05,1])
            await tool(client,'assign_material',objects=['Surface'],material='Glow')
            for directory,strength,expected in (('off',0,[0,0,0]),('constant',2,[.735,.537,.389]),('linked',.5,[.389,.277,.194])):
                await tool(client,'configure_shader_node',material='Glow',node={'name':'Surface','type':'ShaderNodeBsdfPrincipled','inputs':[{'socket':'Emission Color','value':[.25,.125,.0625,1]},{'socket':'Emission Strength','value':strength}]})
                if directory=='linked':
                    await tool(client,'configure_shader_node',material='Glow',node={'name':'Strength','type':'ShaderNodeValue','output_value':strength})
                    await tool(client,'connect_shader_nodes',material='Glow',links=[{'from_node':'Strength','from_socket':0,'to_node':'Surface','to_socket':'Emission Strength'}])
                info=await tool(client,'inspect_texture_bake',name='Surface')
                await client.call_tool('bake_textures',{'params':{'name':'Surface','expected_bake':info['bake_sha256'],'directory':directory,'maps':['EMISSION'],'width':32,'height':32,'samples':1,'margin':0},'wait':True})
                saved=json.loads((root/'library'/directory/'manifest.json').read_text())
                assert saved['emission_encoding']==EMISSION_ENCODING
                actual=saved['maps'][0]['statistics']['mean'][:3]
                assert max(abs(a-b) for a,b in zip(actual,expected))<.015,(directory,actual,expected)
    asyncio.run(run())

    script=root/'emission-convention.py';repo=Path(__file__).resolve().parents[1]
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nROOT='+repr(str(root/'library/off'))+'\n'+r'''
import bpy,json
from pathlib import Path
from mcpblender.blender import vegetation_adoption as adoption,bridge
bridge.check_cancelled=lambda:None
root=Path(ROOT);saved=json.loads((root/'manifest.json').read_text());job=json.loads((root/'job.json').read_text())
component={'name':saved['name'],'initial_bake_sha256':saved['source'],'inspect_texture_bake':{'uv_map':job['uv_map'],'thin_foliage_mode':job['thin_foliage_mode']},'material_adapters':saved['material_adapters']}
adoption.bundle(root,component,{'max_bytes':256*1024**2})
path=root/'manifest.json';original=path.read_bytes();saved.pop('emission_encoding');path.write_text(json.dumps(saved));before=set(bpy.data.user_map())
try:
    try:adoption.bundle(root,component,{'max_bytes':256*1024**2})
    except ValueError as e:assert 'strength-aware' in str(e)
    else:raise AssertionError('Legacy color-only emission accepted')
    assert set(bpy.data.user_map())==before
finally:path.write_bytes(original)
print('EMISSION_CONVENTION_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    assert 'EMISSION_CONVENTION_OK' in result.stdout
