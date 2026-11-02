"""Validated animated LOD bundles through MCP, including native/readback proof."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import struct
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_skin_lods import make_skin,generate,inspect
from test_constraints import sample
from test_shaders import png
from test_nla import edit as nla_edit


def test_two_clip_bundle_zero_origin_playback_state_and_bind_only(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    png(library/'skin-bundle-paint.png',lambda x,y:(40,100,200) if (x//4+y//4)%2 else (200,110,40))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await make_skin(client,'BundleSkin','BundleRig',x=10)
            await tool(client,'apply_material_preset',material='BundlePBR',preset='TEXTURED_PBR',base_color_texture='skin-bundle-paint.png')
            await tool(client,'assign_material',objects=['BundleSkin'],material='BundlePBR')
            await tool(client,'set_keyframes',name='BundleRig',data_path='location',keyframes=[{'frame':1,'value':[10,0,0]},{'frame':9,'value':[12,0,0]}])
            await client.call_tool('set_frame',{'frame':5})
            chain=await generate(client,'BundleSkin','AnimatedBundle')
            await tool(client,'activate_lod_level',chain='AnimatedBundle',expected_chain=chain['chain_sha256'],level=2)
            expected=await sample(client,'BundleRig',frames=[1,5,9],meshes=['AnimatedBundle_LOD2'],sample_limit=0)
            await tool(client,'create_animation_clip',name='BundleRig',clip='BundleIdle',activate=False,tracks=[{'bone':'Tip','property':'rotation_degrees','keyframes':[{'frame':2,'value':[0,0,0]},{'frame':10,'value':[0,0,0]}]}])
            await tool(client,'create_animation_clip',name='BundleRig',clip='BundleNegative',activate=False,tracks=[{'bone':'Tip','property':'rotation_degrees','keyframes':[{'frame':-5,'value':[0,20,0]},{'frame':3,'value':[0,-20,0]}]}])
            await tool(client,'set_active_clip',name='BundleRig',clip='BundleIdle')
            await client.call_tool('set_frame',{'frame':5})
            await tool(client,'configure_render',fps=12,frame_start=3,frame_end=5)
            before=await inspect(client,'AnimatedBundle');source=await tool(client,'inspect_lod_export',chain='AnimatedBundle')
            assert source['can_export'] and len(source['clips'])==3
            animation=await tool(client,'inspect_animation_channels',name='BundleRig')
            with pytest.raises(ToolError,match='animation fingerprint is stale'):
                await client.call_tool('export_lod_chain',{'params':{'chain':'AnimatedBundle','expected_chain':before['chain_sha256'],'expected_animation':'0'*64,'directory':'stale-skin-bundle'},'wait':True})
            assert not (library/'stale-skin-bundle').exists()
            queued=(await client.call_tool('export_lod_chain',{'params':{'chain':'AnimatedBundle','expected_chain':before['chain_sha256'],'expected_animation':source['animation_sha256'],'directory':'animated-bundle'}})).data
            operation=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data
            assert operation['state']=='succeeded',operation
            assert 'storage' in operation['progress']
            assert (await inspect(client,'AnimatedBundle'))['chain_sha256']==before['chain_sha256']
            assert (await tool(client,'inspect_animation_channels',name='BundleRig'))['animation_sha256']==animation['animation_sha256']
            assert (await client.call_tool('get_scene_info')).data['frame']==5
            checked=await tool(client,'validate_lod_export',directory='animated-bundle')
            assert checked['valid'] and len(checked['levels'])==3
            for level in checked['levels']:
                assert set(level['skin']['joints'])=={'Base','Tip'} and {c['name'] for c in level['skin']['clips']}=={'BundleRigBend','BundleIdle','BundleNegative'}
                assert all(c['start']==0 and c['end']==pytest.approx(8/12,abs=1e-6) for c in level['skin']['clips'])
                assert level['images']==1
            manifest=json.loads((library/'animated-bundle/manifest.json').read_text())
            assert manifest['reference_frame']==5 and manifest['fps']==12
            assert {c['name']:c['native_frame_start'] for c in manifest['clips']}=={'BundleRigBend':1,'BundleIdle':2,'BundleNegative':-5}
            assert all(p['max_joint_matrix_error']<.001 and p['max_vertex_error']<.001 for l in manifest['levels'] for p in l['playback'])
            imported=(await client.call_tool('import_asset',{'path':'animated-bundle/level_02.glb'})).data
            objects=(await client.call_tool('get_scene_info')).data['objects']
            rig=next(o['name'] for o in objects if o['name'] in imported['objects'] and o['type']=='ARMATURE');mesh=next(o['name'] for o in objects if o['name'] in imported['objects'] and o['type']=='MESH')
            actions=(await tool(client,'inspect_animation',name=rig))['clips'];clip=next(a['name'] for a in actions if a['managed_target'] is None and 'BundleRigBend' in a['name'])
            await nla_edit(client,'configure_nla_track',rig,track='VerifiedReplay')
            await nla_edit(client,'configure_nla_strip',rig,track='VerifiedReplay',strip='Replay',settings={'clip':clip,'start':0,'action_start':0,'action_end':8})
            await nla_edit(client,'configure_nla_playback',rig,clear_active_action=True)
            replay=await sample(client,rig,frames=[0,4,8],meshes=[mesh],sample_limit=0)
            for a,b in zip(replay['samples'],expected['samples']):
                for side in ('min','max'):assert a['meshes'][0]['world_bounds'][side]==pytest.approx(b['meshes'][0]['world_bounds'][side],abs=.001)
            current=await inspect(client,'AnimatedBundle')
            bound=(await client.call_tool('export_lod_chain',{'params':{'chain':'AnimatedBundle','expected_chain':current['chain_sha256'],'directory':'bind-only','animations':False},'wait':True})).data
            assert bound['valid'] and all(not l['skin']['clips'] for l in bound['levels'])
            await client.call_tool('save_blend',{'path':'animated-lods.blend'})
            if destination:=os.environ.get('MCPBLENDER_SKIN_BUNDLE_EVIDENCE_DIR'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                shutil.copytree(library/'animated-bundle',out/'animated-bundle',dirs_exist_ok=True);shutil.copy2(library/'animated-lods.blend',out/'animated-lods.blend')
    asyncio.run(run())
