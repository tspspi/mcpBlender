"""Structured morph LOD creation and live source clip playback without Python."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_shaders import png


def test_morph_lods_structured_clip_and_resample(assets_live):
    root,path=assets_live
    library=root/'library';library.mkdir(exist_ok=True)
    png(library/'morph-paint.png',lambda x,y:(30,100,200) if (x//4+y//4)%2 else (180,70,30))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            # A dense reusable prop with two full-mesh editable morph targets.
            import math
            vertices=[[.3*math.cos(i*2*math.pi/16),.3*math.sin(i*2*math.pi/16),z/8] for z in range(17) for i in range(16)]
            faces=[[z*16+i,z*16+(i+1)%16,(z+1)*16+(i+1)%16,(z+1)*16+i] for z in range(16) for i in range(16)]+[list(range(15,-1,-1)),list(range(256,272))]
            await tool(client,'create_mesh',name='MorphProp',vertices=vertices,faces=faces)
            await tool(client,'apply_material_preset',material='MorphPBR',preset='TEXTURED_PBR',base_color_texture='morph-paint.png')
            await tool(client,'assign_material',objects=['MorphProp'],material='MorphPBR')
            await tool(client,'generate_uv',name='MorphProp')
            await tool(client,'create_shape_key',name='MorphProp',key='Widen',vertices=[{'vertex':i,'value':[x*.4,y*.4,0]} for i,(x,y,z) in enumerate(vertices)])
            await tool(client,'create_shape_key',name='MorphProp',key='Lift',vertices=[{'vertex':i,'value':[0,0,z*.15]} for i,(x,y,z) in enumerate(vertices)])
            await tool(client,'create_morph_clip',name='MorphProp',clip='PropMotion',tracks=[{'key':k,'keyframes':[{'frame':1,'value':0},{'frame':5,'value':1},{'frame':9,'value':0}]} for k in ['Widen','Lift']])
            before=await tool(client,'inspect_morph_animation',name='MorphProp')
            src=await tool(client,'inspect_lod_source',name='MorphProp',deformation='MORPH')
            result=(await client.call_tool('generate_lod_chain',{'params':{'name':'MorphProp','deformation':'MORPH','chain':'MorphPropLOD','expected_source':src['source_sha256'],'levels':[{'triangle_budget':250},{'triangle_budget':120}],'pose_frames':[1,3,5,9]},'wait':True})).data
            assert result['valid'] and result['morph'] and all(len(l['morph_validation'])==2 for l in result['levels'])
            assert [l['triangles'] for l in result['levels']]==[540,250,120]
            after=await tool(client,'inspect_morph_animation',name='MorphProp')
            assert {k:v for k,v in after.items() if k!='operation_id'}=={k:v for k,v in before.items() if k!='operation_id'}
            for level in result['levels']:
                shapes=await tool(client,'inspect_shape_keys',name=level['object'])
                assert shapes['total_keys']==3 and shapes['managed_topology_matches']
            clips=[{'name':'Motion','frame_start':1,'frame_end':9},{'name':'Late','frame_start':3,'frame_end':7}]
            plan=await tool(client,'inspect_lod_export',chain='MorphPropLOD',timeline_clips=clips)
            assert plan['can_export'] and plan['deformation']=='MORPH'
            job=(await client.call_tool('export_lod_chain',{'params':{'chain':'MorphPropLOD','expected_chain':result['chain_sha256'],'expected_animation':plan['animation_sha256'],'directory':'morph-bundle','timeline_clips':clips}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':job['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded' and 'storage' in done['progress'],done
            exported=done['result']
            assert exported['valid'] and len(exported['levels'])==3
            assert all(l['images']==1 and len(l['skin']['clips'])==2 for l in exported['levels'])
            assert (await tool(client,'validate_lod_export',directory='morph-bundle'))['valid']
            parsed=(await client.call_tool('inspect_glb_deformation',{'params':{'path':'morph-bundle/level_02.glb'},'wait':True})).data
            assert len(parsed['deformation']['clips'])==2
            result=await tool(client,'activate_lod_level',chain='MorphPropLOD',expected_chain=result['chain_sha256'],level=2)
            expected=[]
            for frame in (1,5,9):
                await client.call_tool('set_frame',{'frame':frame})
                expected.append((await tool(client,'inspect_mesh',name='MorphPropLOD_LOD2',sample_limit=0))['world_bounds'])
            await client.call_tool('set_frame',{'frame':1})
            imported=(await client.call_tool('import_asset',{'path':'morph-bundle/level_02.glb'})).data
            meshes=[o['name'] for o in (await client.call_tool('get_scene_info')).data['objects'] if o['name'] in imported['objects'] and o['type']=='MESH']
            assert len(meshes)==1
            reimport=await tool(client,'inspect_morph_animation',name=meshes[0])
            motion=next(a for a in reimport['clips'] if a['name']=='Motion')
            await tool(client,'set_active_morph_clip',name=meshes[0],clip=motion['name'])
            # Native exported times start at zero: frame0/4/8 map to source1/5/9.
            replay=(await client.call_tool('sample_morph_animation',{'params':{'name':meshes[0],'frames':[0,4,8]},'wait':True})).data
            for actual,bounds in zip(replay['samples'],expected):
                for side in ('min','max'):assert actual['mesh']['world_bounds'][side]==pytest.approx(bounds[side],abs=.001)
            sampled=(await client.call_tool('sample_lod_chain',{'params':{'chain':'MorphPropLOD','expected_chain':result['chain_sha256'],'pose_frames':[1,3.5,5,9]},'wait':True})).data
            assert sampled['worst_relative_error']<.1
            await client.call_tool('save_blend',{'path':'morph-lods.blend'})
            await client.call_tool('open_blend',{'path':'morph-lods.blend'})
            reopened=await tool(client,'inspect_lod_chain',chain='MorphPropLOD');assert reopened['valid']
            await tool(client,'set_morph_keyframes',name='MorphProp',clip='PropMotion',tracks=[{'key':'Widen','keyframes':[{'frame':5,'value':.5}]}])
            changed=await tool(client,'inspect_lod_chain',chain='MorphPropLOD')
            assert changed['valid'] and changed['pose_validation_inputs_changed']
            if evidence:=os.environ.get('MCPBLENDER_MORPH_LOD_EVIDENCE_DIR'):
                out=Path(evidence);out.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'library/morph-lods.blend',out/'morph-lods.blend');shutil.copytree(library/'morph-bundle',out/'morph-bundle',dirs_exist_ok=True);(out/'morph-proof.json').write_text(json.dumps({'chain':result,'sampled':sampled},indent=2))
    asyncio.run(run())
