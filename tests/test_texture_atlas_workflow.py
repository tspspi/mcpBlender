"""Verified two-bundle atlas: pixels, physical geometry, UVs and recovery binding."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import struct
import time
import pytest
from fastmcp.exceptions import ToolError
from mcpblender.texture_files import MARKER,read_json,write_json
from mcpblender.package_files import inspect_static_glb
from mcpblender.lod_files import read_glb
from test_asset_editing import assets_live,client_for,tool,pytestmark

def rgba(path):
    return subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','rgba','-'],capture_output=True,check=True,timeout=30).stdout


def test_verified_atlas_pixels_physical_units_and_recovery(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    script=root/'cm.py';script.write_text('import bpy\nbpy.context.scene.unit_settings.scale_length=.01\nbpy.ops.wm.save_as_mainfile(filepath='+repr(str(library/'cm.blend'))+')\n')
    prepared=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=60)
    assert prepared.returncode==0,prepared.stdout+prepared.stderr
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            maps=['BASE_COLOR','NORMAL','ROUGHNESS','ALPHA']
            for name,color,unit,x in [('Red',[.8,.02,.01,1],1,0),('Blue',[.01,.04,.8,1],.01,4)]:
                if unit!=1:await client.call_tool('open_blend',{'path':'cm.blend'})
                await tool(client,'create_primitive',name=name,kind='PLANE',location=[x/unit,0,0],scale=[1/unit]*3)
                await tool(client,'apply_material_preset',material=name+'Surface',base_color=color,roughness=.3)
                if name=='Red':
                    await tool(client,'configure_shader_node',material='RedSurface',node={'name':'Coordinates','type':'ShaderNodeTexCoord'})
                    await tool(client,'connect_shader_nodes',material='RedSurface',links=[{'from_node':'Coordinates','from_socket':'UV','to_node':'Surface','to_socket':'Base Color'}])
                await tool(client,'assign_material',objects=[name],material=name+'Surface')
                info=await tool(client,'inspect_texture_bake',name=name)
                baked=(await client.call_tool('bake_textures',{'params':{'name':name,'expected_bake':info['bake_sha256'],'directory':name.lower(),'width':32,'height':32,'samples':1,'maps':maps,'margin':0},'wait':True})).data
                assert baked['live_scene_unchanged']
            args={'entries':[{'id':'red','directory':'red'},{'id':'blue','directory':'blue'}],'width':128,'height':64,'gutter':4}
            plan=await tool(client,'inspect_texture_atlas',**args);assert plan['complete'] and 'recovery' not in plan
            assert plan['atlas']['layout']['base_rgba8_bytes']==128*64*4*4
            with pytest.raises(ToolError,match='stale'):
                await client.call_tool('build_texture_atlas',{'params':args|{'directory':'stale-atlas','expected_atlas':'0'*64},'wait':True})
            assert not (library/'stale-atlas').exists()
            with pytest.raises(ToolError,match='outside source'):
                await client.call_tool('build_texture_atlas',{'params':args|{'directory':'red/nested','expected_atlas':plan['atlas_sha256']},'wait':True})
            assert not (library/'red/nested').exists()
            result=(await client.call_tool('build_texture_atlas',{'params':args|{'directory':'atlas','expected_atlas':plan['atlas_sha256']},'wait':True})).data
            assert result['live_scene_unchanged'] and result['objects']==['blue','red']
            for kind in maps:
                atlas=rgba(library/'atlas/textures'/(kind.lower()+'.png'))
                for tile in result['atlas']['layout']['tiles']:
                    source=rgba(library/tile['id']/'textures'/(kind.lower()+'.png'));x,y,w,h=tile['pixel_rect']
                    for row in range(-4,h+4):
                        # PNG rows are top-down; packed rectangles use bottom-left.
                        sy=h-1-min(h-1,max(0,row));ay=64-1-(y+row)
                        for col in range(-4,w+4):
                            sx=min(w-1,max(0,col));a=source[(sy*w+sx)*4:(sy*w+sx+1)*4];b=atlas[(ay*128+x+col)*4:(ay*128+x+col+1)*4]
                            assert all(abs(i-j)<=1 for i,j in zip(a,b)),(kind,tile['id'],row,col,a,b)
            # Cancel during actual atlas image work and clean only its owned output.
            large=args|{'width':2048,'height':2048}
            big_plan=await tool(client,'inspect_texture_atlas',**large)
            payload={'params':large|{'directory':'cancelled-atlas','expected_atlas':big_plan['atlas_sha256']},'wait':False,'request_id':'cancel-atlas'}
            queued=(await client.call_tool('build_texture_atlas',payload)).data;deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                operation=(await client.call_tool('get_operation',{'operation_id':queued['operation_id']})).data
                assert operation['state'] in {'queued','running'},operation
                progress=operation.get('progress') or {}
                if progress.get('phase')=='packing atlas texture':break
                await asyncio.sleep(.1)
            else:pytest.fail('Atlas image packing did not start')
            assert progress['storage']['free_bytes']>0 and progress['storage']['estimated_output_bytes']>0
            worker=progress['worker_pid'];os.kill(worker,0)
            await client.call_tool('cancel_operation',{'operation_id':queued['operation_id']})
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':30})).data
            assert done['state']=='cancelled',done
            with pytest.raises(ProcessLookupError):os.kill(worker,0)
            assert (await client.call_tool('build_texture_atlas',payload)).data['operation_id']==queued['operation_id']
            await tool(client,'cleanup_texture_job',directory='cancelled-atlas',dry_run=False)
            assert not (library/'cancelled-atlas').exists()
            # Atlas object inventories must not weaken ordinary bake validation.
            blue_manifest=library/'blue/manifest.json';original_blue=read_json(blue_manifest)
            write_json(blue_manifest,original_blue|{'objects':[]})
            await client.call_tool('open_blend',{'path':'blue/asset.blend'})
            await client.call_tool('set_object_transform',{'name':'Blue','location':[900,0,0]})
            with pytest.raises(ToolError,match='binding'):await tool(client,'validate_texture_bake',directory='blue')
            write_json(blue_manifest,original_blue)
            await client.call_tool('open_blend',{'path':'atlas/asset.blend'})
            checked=await tool(client,'validate_texture_bake',directory='atlas');assert checked['validated'] and checked['objects']==['blue','red']
            await tool(client,'export_objects_glb',objects=['blue','red'],path='atlas.glb')
            proof=inspect_static_glb(library/'atlas.glb');assert proof['materials']==1 and proof['meshes']==2
            assert proof['world_bounds']['max'][0]==pytest.approx(5,abs=1e-5)
            doc,binary=read_glb(library/'atlas.glb')
            tiles={t['id']:t for t in result['atlas']['layout']['tiles']}
            for node in doc['nodes']:
                if 'mesh' not in node:continue
                tile=tiles[node['name']];u,v,uw,vh=tile['uv_rect']
                for primitive in doc['meshes'][node['mesh']]['primitives']:
                    accessor=doc['accessors'][primitive['attributes']['TEXCOORD_0']];view=doc['bufferViews'][accessor['bufferView']]
                    assert accessor['componentType']==5126 and accessor['type']=='VEC2'
                    start=view.get('byteOffset',0)+accessor.get('byteOffset',0);stride=view.get('byteStride',8)
                    uv=[struct.unpack_from('<2f',binary,start+i*stride) for i in range(accessor['count'])]
                    assert [min(x[0] for x in uv),max(x[0] for x in uv)]==pytest.approx([u,u+uw])
                    assert [min(x[1] for x in uv),max(x[1] for x in uv)]==pytest.approx([1-v-vh,1-v])
            # Declared layout must remain bound during both validation and recovery.
            manifest=library/'atlas/manifest.json';saved=read_json(manifest);changed=json.loads(manifest.read_text());changed['atlas']['layout']['gutter']=0;write_json(manifest,changed)
            with pytest.raises(ToolError,match='binding'):await tool(client,'validate_texture_bake',directory='atlas')
            marker=library/'atlas'/MARKER;record=read_json(marker);write_json(marker,record|{'state':'running','worker_pid':0,'parent_pid':0})
            with pytest.raises(ToolError,match='binding'):await tool(client,'recover_texture_job',directory='atlas')
            write_json(manifest,saved)
            recovered=await tool(client,'recover_texture_job',directory='atlas');assert recovered['reconciled'] and not recovered['replayed']
            assert (await tool(client,'validate_texture_bake',directory='atlas'))['validated']
            await client.call_tool('set_object_transform',{'name':'blue','location':[9,0,0]})
            with pytest.raises(ToolError,match='binding'):await tool(client,'validate_texture_bake',directory='atlas')
            if target:=os.environ.get('MCPBLENDER_ATLAS_EVIDENCE_DIR'):
                out=Path(target);out.mkdir(parents=True,exist_ok=True)
                for name in ('red','blue','atlas'):shutil.copytree(library/name,out/name,dirs_exist_ok=True)
                shutil.copy2(library/'atlas.glb',out/'atlas.glb');(out/'proof.json').write_text(json.dumps({'plan':plan,'result':result,'glb':proof},indent=2))
    asyncio.run(run())
