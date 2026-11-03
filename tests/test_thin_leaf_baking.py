"""Explicit, lossy front-PBR transfer preserves native leaf optics in the editor."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import pytest
from fastmcp.exceptions import ToolError
from mcpblender.texture_files import read_json,write_json,MARKER
from test_asset_editing import assets_live,client_for,tool,pytestmark


def test_front_leaf_adapter_opt_in_binding_and_native_preservation(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            await tool(client,'create_primitive',name='LeafLow',kind='PLANE')
            # Reversed high face exercises baking the surface from its back side.
            await tool(client,'create_mesh',name='LeafHigh',vertices=[[-1,-1,.2],[1,-1,.2],[1,1,.2],[-1,1,.2]],faces=[[0,3,2,1]])
            await tool(client,'generate_uv',name='LeafHigh')
            surface=await tool(client,'create_botanical_surface',material='LeafBakeSource',settings={'profile':'OAK_LEAF','uv_map':'UVMap'})
            opt=await tool(client,'inspect_foliage_material',material='LeafBakeSource')
            await tool(client,'configure_foliage_material',material='LeafBakeSource',expected_material=opt['material_sha256'],front_color=[.03,.4,.05,1],back_color=[.8,.01,.01,1],translucent_mix=.8,double_sided=False)
            await tool(client,'assign_material',objects=['LeafHigh'],material='LeafBakeSource')
            params={'name':'LeafLow','sources':['LeafHigh']}
            refused=await tool(client,'inspect_texture_bake',**params)
            assert not refused['complete'] and any('FRONT_PBR' in v for v in refused['unsupported_reasons'])
            info=await tool(client,'inspect_texture_bake',**params,thin_foliage_mode='FRONT_PBR');assert info['complete'],info
            assert len(info['material_adapters'])==1 and info['material_adapters'][0]['omitted_features']
            before=await tool(client,'inspect_botanical_surface',material='LeafBakeSource')
            # Missing the explicit mode must not create an output directory.
            with pytest.raises(ToolError):
                await client.call_tool('bake_textures',{'params':params|{'expected_bake':info['bake_sha256'],'directory':'refused'},'wait':True})
            assert not (root/'library/refused').exists()
            result=(await client.call_tool('bake_textures',{'params':params|{'expected_bake':info['bake_sha256'],'thin_foliage_mode':'FRONT_PBR','directory':'front-pbr','width':96,'height':96,'samples':16,'margin':2,'cage_extrusion':.5,'max_ray_distance':1,'maps':['BASE_COLOR','NORMAL','ROUGHNESS','ALPHA']},'wait':True})).data
            assert result['material_adapters']==info['material_adapters'] and result['live_scene_unchanged']
            colors=next(v for v in result['maps'] if v['map']=='BASE_COLOR')['statistics']['mean']
            assert colors[1]>colors[0]*1.5,colors # front green, not the native red back color
            assert (await tool(client,'inspect_botanical_surface',material='LeafBakeSource'))['material_sha256']==before['material_sha256']
            assert (await tool(client,'inspect_texture_bake',**params,thin_foliage_mode='FRONT_PBR'))['bake_sha256']==info['bake_sha256']
            await client.call_tool('open_blend',{'path':'front-pbr/asset.blend'})
            checked=await tool(client,'validate_texture_bake',directory='front-pbr')
            assert checked['validated'] and checked['material_adapters']==info['material_adapters']
            manifest=root/'library/front-pbr/manifest.json';saved=read_json(manifest)
            write_json(manifest,saved|{'material_adapters':[]})
            with pytest.raises(ToolError,match='binding mismatch'):await tool(client,'validate_texture_bake',directory='front-pbr')
            # Recovery also binds the declared conversion, even for a complete bundle.
            marker=manifest.parent/MARKER;record=read_json(marker)
            write_json(marker,record|{'state':'running','parent_pid':0,'worker_pid':0})
            with pytest.raises(ToolError,match='manifest binding mismatch'):
                await tool(client,'recover_texture_job',directory='front-pbr')
            write_json(manifest,saved)
            recovered=await tool(client,'recover_texture_job',directory='front-pbr')
            assert recovered['reconciled'] and not recovered['replayed']
            assert (await tool(client,'validate_texture_bake',directory='front-pbr'))['validated']
            write_json(marker,record)
            if target:=os.environ.get('MCPBLENDER_THIN_BAKE_EVIDENCE_DIR'):
                out=Path(target);out.mkdir(parents=True,exist_ok=True);shutil.copytree(root/'library/front-pbr',out/'front-pbr',dirs_exist_ok=True)
                (out/'proof.json').write_text(json.dumps({'inspection':info,'result':result,'validated':checked},indent=2))
    asyncio.run(run())


def test_real_leaf_to_alpha_card_projection(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            shape=await tool(client,'plan_leaf_template')
            await tool(client,'create_leaf_template',name='CardLeaf',expected_leaf=shape['leaf_sha256'])
            state=await tool(client,'inspect_botanical_surface',material='CardLeaf_Surface')
            await tool(client,'configure_botanical_surface',material='CardLeaf_Surface',expected_material=state['material_sha256'],settings={'profile':'OAK_LEAF'})
            await tool(client,'create_primitive',name='LeafCard',kind='PLANE',location=[0,.063,-.02],scale=[.04,.07,1])
            args={'name':'LeafCard','sources':['CardLeaf'],'thin_foliage_mode':'FRONT_PBR'}
            info=await tool(client,'inspect_texture_bake',**args);assert info['complete'],info
            result=(await client.call_tool('bake_textures',{'params':args|{'expected_bake':info['bake_sha256'],'directory':'leaf-card','width':128,'height':128,'samples':16,'margin':2,'cage_extrusion':.1,'max_ray_distance':.3,'min_projection_coverage':.25,'maps':['BASE_COLOR','NORMAL','ROUGHNESS','ALPHA']},'wait':True})).data
            assert .25<result['projection']['fraction']<.7
            mask=next(v for v in result['maps'] if v['map']=='ALPHA')['statistics']
            assert mask['min'][0]==0 and mask['max'][0]>.95 and .2<mask['mean'][0]<.8,mask
            await client.call_tool('open_blend',{'path':'leaf-card/asset.blend'})
            checked=await tool(client,'validate_texture_bake',directory='leaf-card');assert checked['validated']
            # The delivered card remains editable two-triangle geometry with image maps.
            mesh=await tool(client,'inspect_mesh',name='LeafCard');assert mesh['triangles']==2
            await tool(client,'export_objects_glb',objects=['LeafCard'],path='leaf-card.glb')
            raw=(root/'library/leaf-card.glb').read_bytes();count=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+count])
            mat=gltf['materials'][0];assert mat.get('alphaMode','OPAQUE') in {'BLEND','MASK'},mat
            texture=gltf['textures'][mat['pbrMetallicRoughness']['baseColorTexture']['index']]
            image=gltf['images'][texture['source']];view=gltf['bufferViews'][image['bufferView']]
            begin=20+count+8+view.get('byteOffset',0);png=root/'library/card-export-albedo.png';png.write_bytes(raw[begin:begin+view['byteLength']])
            rgba=subprocess.run(['ffmpeg','-v','error','-i',str(png),'-f','rawvideo','-pix_fmt','rgba','-'],capture_output=True,check=True,timeout=20).stdout
            alpha=rgba[3::4];assert min(alpha)==0 and max(alpha)==255 and .15<sum(alpha)/(255*len(alpha))<.8
            await tool(client,'configure_render',resolution_x=256,resolution_y=256,samples=16)
            await tool(client,'setup_preview_stage',objects=['LeafCard'],prefix='AlphaCardView',strength=.35)
            queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':'leaf-card-preview.png','camera':'AlphaCardView_Camera','engine':'CYCLES','width':256,'height':256}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded',done
            if target:=os.environ.get('MCPBLENDER_THIN_BAKE_EVIDENCE_DIR'):
                out=Path(target);out.mkdir(parents=True,exist_ok=True);shutil.copytree(root/'library/leaf-card',out/'leaf-card',dirs_exist_ok=True);shutil.copy2(root/'library/leaf-card-preview.png',out/'leaf-card-preview.png');shutil.copy2(root/'library/leaf-card.glb',out/'leaf-card.glb');shutil.copy2(png,out/'card-export-albedo.png')
                (out/'leaf-card-proof.json').write_text(json.dumps({'result':result,'validated':checked,'mesh':mesh},indent=2))
    asyncio.run(run())
