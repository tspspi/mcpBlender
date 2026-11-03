"""Real manual LOD adoption, guarded re-adoption and delivery without Python tools."""
import asyncio
import json
import os
from pathlib import Path
import shutil

import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_skin_lods import make_skin,generate as generate_skin


async def wait(client,command,**params):
    return (await client.call_tool(command,{'params':params,'wait':True})).data


def test_manual_levels_remap_stale_replacement_and_delivery(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_primitive',name='AdoptSource',kind='UV_SPHERE',location=[4,0,2])
            await tool(client,'apply_material_preset',material='AdoptBlue',base_color=[.02,.1,.6,1])
            await tool(client,'assign_material',objects=['AdoptSource'],material='AdoptBlue')
            await tool(client,'apply_material_preset',material='ImporterBlue',base_color=[.02,.1,.6,1])
            for name,ratio in [('ManualNear',.35),('ManualFar',.15)]:
                await tool(client,'duplicate_object',name='AdoptSource',new_name=name)
                await tool(client,'configure_modifier',name=name,modifier='ManualReduction',settings={'type':'DECIMATE','ratio':ratio})
                await tool(client,'apply_modifier',name=name,modifier='ManualReduction')
                await tool(client,'assign_material',objects=[name],material='ImporterBlue')
            params={'name':'AdoptSource','inputs':[{'name':'ManualNear','material_slots':[0]},{'name':'ManualFar','material_slots':[0]}]}
            # Explicitly remap the imported material to the authoritative slot.
            plan=await tool(client,'inspect_lod_adoption',**params)
            before=await tool(client,'inspect_mesh',name='ManualNear',evaluated=False,sample_limit=0)
            with pytest.raises(ToolError,match='material slots'):
                await tool(client,'inspect_lod_adoption',name='AdoptSource',inputs=[{'name':'ManualNear'}])
            await client.call_tool('set_object_transform',{'name':'ManualNear','location':[4.01,0,2]})
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'adopt_lod_chain',chain='Adopted',expected_source=plan['source_sha256'],**params)
            before=await tool(client,'inspect_mesh',name='ManualNear',evaluated=False,sample_limit=0)
            plan=await tool(client,'inspect_lod_adoption',**params)
            adopted=await wait(client,'adopt_lod_chain',chain='Adopted',expected_source=plan['source_sha256'],**params)
            assert adopted['valid'] and adopted['adoption'] and len(adopted['levels'])==3
            assert adopted['levels'][1]['triangles']==before['triangles']
            assert adopted['levels'][1]['recipe']['method']=='ADOPT'
            assert (await tool(client,'inspect_mesh',name='ManualNear',evaluated=False,sample_limit=0))['geometry_sha256']==before['geometry_sha256']
            await client.call_tool('set_object_transform',{'name':'Adopted_Root','location':[8,0,2]})
            state=await tool(client,'inspect_lod_management',chain='Adopted')
            plan=await tool(client,'inspect_lod_adoption',**params)
            updated=await wait(client,'readopt_lod_chain',chain='Adopted',expected_management=state['management_sha256'],expected_source=plan['source_sha256'],**params)
            assert updated['valid'] and updated['replaced_id']==state['id']
            assert (await client.call_tool('get_object_info',{'name':'Adopted_Root'})).data['location']==[8,0,2]
            exported=await wait(client,'export_lod_chain',chain='Adopted',expected_chain=updated['chain_sha256'],directory='adopted-bundle')
            assert exported['valid'] and len(exported['levels'])==3
            await client.call_tool('save_blend',{'path':'adopted.blend'})
            await client.call_tool('open_blend',{'path':'adopted.blend'})
            state=await tool(client,'inspect_lod_management',chain='Adopted');assert state['can_remove'] and state['adoption']
            await tool(client,'remove_lod_chain',chain='Adopted',expected_management=state['management_sha256'])
            assert (await tool(client,'inspect_mesh',name='ManualNear',evaluated=False,sample_limit=0))['geometry_sha256']==before['geometry_sha256']
            if destination:=os.environ.get('MCPBLENDER_ADOPTION_EVIDENCE_DIR'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                shutil.copy2(root/'library/adopted.blend',out/'adopted.blend')
                shutil.copytree(root/'library/adopted-bundle',out/'adopted-bundle',dirs_exist_ok=True)
                (out/'proof.json').write_text(json.dumps({'plan':plan,'chain':updated,'export':exported},indent=2))
    asyncio.run(run())


def test_skin_and_morph_adoption_retain_authoritative_controls(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await make_skin(client,'AdoptSkin','AdoptRig',x=20)
            # These existing reductions represent independently supplied rest geometry;
            # adoption must not copy their deform groups or generated controls.
            donor=await generate_skin(client,'AdoptSkin','DonorSkin')
            source=await tool(client,'inspect_lod_source',name='AdoptSkin',deformation='SKINNED')
            animation=await tool(client,'inspect_animation_channels',name='AdoptRig')
            await tool(client,'activate_lod_level',chain='DonorSkin',expected_chain=donor['chain_sha256'],level=1)
            args={'name':'AdoptSkin','deformation':'SKINNED','inputs':[{'name':'DonorSkin_LOD1'}],'input_geometry':'RAW_BASIS','pose_frames':[1,5,9],'max_pose_error':.15}
            plan=await tool(client,'inspect_lod_adoption',**args)
            adopted=await wait(client,'adopt_lod_chain',chain='AdoptSkinChain',expected_source=plan['source_sha256'],**args)
            assert adopted['valid'] and adopted['skin'] and len(adopted['pose_validation'])==3
            export_plan=await tool(client,'inspect_lod_export',chain='AdoptSkinChain')
            exported=await wait(client,'export_lod_chain',chain='AdoptSkinChain',expected_chain=adopted['chain_sha256'],expected_animation=export_plan['animation_sha256'],directory='adopted-skin-bundle')
            assert exported['valid']
            assert (await tool(client,'inspect_animation_channels',name='AdoptRig'))['animation_sha256']==animation['animation_sha256']
            assert (await tool(client,'inspect_lod_source',name='AdoptSkin',deformation='SKINNED'))['source_sha256']==source['source_sha256']
            await tool(client,'create_primitive',name='AdoptMorph',kind='UV_SPHERE',location=[30,0,2])
            await tool(client,'create_shape_key',name='AdoptMorph',key='Tip',vertices=[{'vertex':0,'value':[0,0,.15]}])
            await tool(client,'create_morph_clip',name='AdoptMorph',clip='AdoptMorphClip',tracks=[{'key':'Tip','keyframes':[{'frame':1,'value':0},{'frame':5,'value':1},{'frame':9,'value':0}]}])
            await tool(client,'create_primitive',name='ManualMorph',kind='UV_SPHERE',location=[30,0,2])
            await tool(client,'configure_modifier',name='ManualMorph',modifier='Reduced',settings={'type':'DECIMATE','ratio':.2})
            await tool(client,'apply_modifier',name='ManualMorph',modifier='Reduced')
            args={'name':'AdoptMorph','deformation':'MORPH','inputs':[{'name':'ManualMorph'}],'pose_frames':[1,5,9],'max_pose_error':.3,'max_relative_error':.3}
            source=await tool(client,'inspect_lod_source',name='AdoptMorph',deformation='MORPH')
            plan=await tool(client,'inspect_lod_adoption',**args)
            adopted=await wait(client,'adopt_lod_chain',chain='AdoptMorphChain',expected_source=plan['source_sha256'],**args)
            assert adopted['valid'] and adopted['morph'] and len(adopted['pose_validation'])==3
            clips=[{'name':'AdoptedMorph','frame_start':1,'frame_end':9}]
            export_plan=await tool(client,'inspect_lod_export',chain='AdoptMorphChain',timeline_clips=clips)
            exported=await wait(client,'export_lod_chain',chain='AdoptMorphChain',expected_chain=adopted['chain_sha256'],expected_animation=export_plan['animation_sha256'],timeline_clips=clips,directory='adopted-morph-bundle')
            assert exported['valid']
            assert (await tool(client,'inspect_lod_source',name='AdoptMorph',deformation='MORPH'))['source_sha256']==source['source_sha256']
    asyncio.run(run())
