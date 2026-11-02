"""Live skeletal LOD reduction, pose error gates and explicit animated delivery."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import struct
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_constraints import sample
from test_animation_curves import key


async def make_skin(client,name='SkinLODSource',rig='SkinLODRig',x=10):
    await tool(client,'create_armature',name=rig,location=[x,0,0],bones=[{'name':'Base','head':[0,0,0],'tail':[0,0,1]},{'name':'Tip','head':[0,0,1],'tail':[0,0,2],'parent':'Base','connected':True}])
    # Regular dense tube: native reductions can preserve a meaningful joint bend.
    import math
    vertices=[[x+.2*math.cos(i*2*math.pi/16),.2*math.sin(i*2*math.pi/16),z/8] for z in range(17) for i in range(16)]
    faces=[[z*16+i,z*16+(i+1)%16,(z+1)*16+(i+1)%16,(z+1)*16+i] for z in range(16) for i in range(16)]
    faces += [list(reversed(range(16))),list(range(256,272))]
    await tool(client,'create_mesh',name=name,vertices=vertices,faces=faces)
    await tool(client,'generate_uv',name=name,method='SMART')
    weights=[]
    for i,v in enumerate(vertices):
        t=max(0,min(1,(v[2]-.75)/.5));values={}
        if t<1:values['Base']=1-t
        if t>0:values['Tip']=t
        weights.append({'vertex':i,'weights':values})
    await tool(client,'bind_mesh',name=name,armature=rig,method='EXPLICIT',weights=weights)
    await tool(client,'create_animation_clip',name=rig,clip=rig+'Bend',tracks=[{'bone':'Tip','property':'rotation_degrees','keyframes':[{'frame':1,'value':[0,0,0]},{'frame':5,'value':[70,0,0]},{'frame':9,'value':[0,0,0]}]}])


async def inspect(client,chain):return await tool(client,'inspect_lod_chain',chain=chain)


async def generate(client,name,chain,**params):
    before=await tool(client,'inspect_lod_source',name=name,deformation='SKINNED')
    return (await client.call_tool('generate_lod_chain',{'params':{'name':name,'deformation':'SKINNED','expected_source':before['source_sha256'],'chain':chain,
        'levels':[{'triangle_budget':250},{'triangle_budget':120}],'pose_frames':[1,5,9],**params},'wait':True})).data


def test_skin_lods_current_timeline_parent_motion_source_invariance_and_glb(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            await make_skin(client)
            await tool(client,'apply_material_preset',material='SkinLODBlue',base_color=[.03,.14,.55,1],roughness=.4)
            await tool(client,'assign_material',objects=['SkinLODSource'],material='SkinLODBlue')
            await client.call_tool('set_frame',{'frame':5})
            before=await tool(client,'inspect_skin_weights',name='SkinLODSource')
            animation=await tool(client,'inspect_animation_channels',name='SkinLODRig')
            motion=await sample(client,'SkinLODRig',frames=[1,5,9],meshes=['SkinLODSource'],sample_limit=0)
            result=await generate(client,'SkinLODSource','DeformLOD')
            assert result['valid'] and result['deformation']=='SKINNED' and not result['source_stale_or_unavailable']
            assert all(p['levels'][0]['max_relative_error']<1e-6 for p in result['pose_validation'])
            assert len(result['pose_validation'])==3 and all(l['max_relative_error']<.1 for p in result['pose_validation'] for l in p['levels'])
            for level in result['levels']:
                assert level['skin_weights']['max_influences']<=4 and level['skin_weights']['weight_sum_min']==pytest.approx(1,abs=1e-5)
            assert (await tool(client,'inspect_skin_weights',name='SkinLODSource'))['weights_sha256']==before['weights_sha256']
            assert (await tool(client,'inspect_animation_channels',name='SkinLODRig'))['animation_sha256']==animation['animation_sha256']
            assert (await client.call_tool('get_scene_info')).data['frame']==5
            posed=(await client.call_tool('sample_lod_chain',{'params':{'chain':'DeformLOD','expected_chain':result['chain_sha256'],'pose_frames':[1,3.5,5,7.25,9]},'wait':True})).data
            assert posed['worst_relative_error']<.1 and posed['restored_frame']==5
            assert (await inspect(client,'DeformLOD'))['chain_sha256']==result['chain_sha256']
            await tool(client,'activate_lod_level',chain='DeformLOD',expected_chain=result['chain_sha256'],level=2)
            await tool(client,'set_keyframes',name='SkinLODRig',data_path='location',keyframes=[{'frame':1,'value':[10,0,0]},{'frame':9,'value':[12,0,0]}])
            updated=await inspect(client,'DeformLOD');assert updated['valid']
            source_motion=await sample(client,'SkinLODRig',frames=[1,5,9],meshes=['SkinLODSource','DeformLOD_LOD2'],sample_limit=0)
            assert source_motion['samples'][2]['meshes'][1]['world_bounds']['max'][0]>source_motion['samples'][0]['meshes'][1]['world_bounds']['max'][0]+1.5
            await tool(client,'export_objects_glb',objects=['SkinLODRig','DeformLOD_LOD2'],path='skin-lod.glb',animations=True)
            data=(root/'library/skin-lod.glb').read_bytes();length=struct.unpack_from('<I',data,12)[0];gltf=json.loads(data[20:20+length])
            assert len(gltf['skins'])==len(gltf['meshes'])==1 and len(gltf['skins'][0]['joints'])==2
            assert any('JOINTS_0' in p['attributes'] and 'WEIGHTS_0' in p['attributes'] for p in gltf['meshes'][0]['primitives'])
            assert gltf['animations']
            imported=(await client.call_tool('import_asset',{'path':'skin-lod.glb'})).data
            objects=(await client.call_tool('get_scene_info')).data['objects']
            rig=next(o['name'] for o in objects if o['name'] in imported['objects'] and o['type']=='ARMATURE')
            mesh=next(o['name'] for o in objects if o['name'] in imported['objects'] and o['type']=='MESH')
            replay=await sample(client,rig,frames=[1,5,9],meshes=[mesh],sample_limit=0)
            for actual,expected in zip(replay['samples'],source_motion['samples']):
                for side in ('min','max'):assert actual['meshes'][0]['world_bounds'][side]==pytest.approx(expected['meshes'][1]['world_bounds'][side],abs=.001)
            await client.call_tool('save_blend',{'path':'skin-lods.blend'})
            await client.call_tool('open_blend',{'path':'skin-lods.blend'})
            assert (await inspect(client,'DeformLOD'))['valid']
            if destination:=os.environ.get('MCPBLENDER_SKIN_LOD_EVIDENCE_DIR'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                for name in ('skin-lods.blend','skin-lod.glb'):shutil.copy2(root/'library'/name,out/name)
                (out/'pose-comparison.json').write_text(json.dumps({'chain':result,'sampled':posed,'motion':source_motion,'reimported':replay},indent=2))
    asyncio.run(run())


def test_skin_lod_pose_gate_atomic_refusal_and_modified_weights(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await make_skin(client,'StrictSkin','StrictRig',x=20)
            before={o['name'] for o in (await client.call_tool('get_scene_info')).data['objects']}
            with pytest.raises(ToolError,match='posed surface error'):
                await generate(client,'StrictSkin','StrictLOD',skin_joint_importance=0)
            assert {o['name'] for o in (await client.call_tool('get_scene_info')).data['objects']}==before
            result=await generate(client,'StrictSkin','StrictLOD')
            obj=result['levels'][1]['object'];weights=await tool(client,'inspect_skin_weights',name=obj)
            await client.call_tool('set_skin_weights',{'params':{'name':obj,'expected_weights':weights['weights_sha256'],'weights':[{'vertex':0,'weights':{'Tip' if weights['vertex_samples'][0]['weights'].get('Base',0)>.5 else 'Base':1}}]},'wait':True})
            changed=await inspect(client,'StrictLOD')
            assert not changed['valid'] and any('skin weights changed' in s for s in changed['issues'])
    asyncio.run(run())


def test_control_driven_timeline_and_raw_binding_preserved(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await make_skin(client,'ControlSkinLOD','ControlSkinRig',x=30)
            await tool(client,'create_animation_control',name='LODRotationControl')
            await key(client,'LODRotationControl','LODControlMotion',property='rotation_degrees',keyframes=[{'frame':1,'value':[90,0,0]},{'frame':5,'value':[147,0,0]},{'frame':9,'value':[90,0,0]}])
            constraints=await tool(client,'inspect_animation_constraints',name='ControlSkinRig',bone='Tip')
            await tool(client,'configure_animation_constraint',name='ControlSkinRig',bone='Tip',constraint='LODControlCopy',expected_constraints=constraints['constraints_sha256'],settings={'type':'COPY_ROTATION','target':{'name':'LODRotationControl'},'owner_space':'POSE','target_space':'WORLD'})
            await client.call_tool('set_frame',{'frame':3})
            original=await sample(client,'ControlSkinRig',frames=[1,3,5,7,9],meshes=['ControlSkinLOD'],sample_limit=0)
            result=await generate(client,'ControlSkinLOD','ControlLOD',pose_frames=[1,3,5,7,9])
            assert result['valid'] and max(l['max_relative_error'] for s in result['pose_validation'] for l in s['levels'])<.1
            assert (await client.call_tool('get_scene_info')).data['frame']==3
            repeated=await sample(client,'ControlSkinRig',frames=[1,3,5,7,9],meshes=['ControlSkinLOD'],sample_limit=0)
            assert [s['meshes'][0]['geometry_sha256'] for s in repeated['samples']]==[s['meshes'][0]['geometry_sha256'] for s in original['samples']]
            assert len(set(s['meshes'][0]['geometry_sha256'] for s in original['samples']))>=3, [(s['frame'],s['meshes'][0]['world_bounds']) for s in original['samples']]
            # The static-only bundle surface must not drop skin data silently.
            with pytest.raises(ToolError,match='Skin bundles require'):
                await client.call_tool('export_lod_chain',{'params':{'chain':'ControlLOD','expected_chain':result['chain_sha256'],'directory':'not-a-static-bundle'},'wait':True})
    asyncio.run(run())
