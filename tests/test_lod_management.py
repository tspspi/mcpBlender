"""Structured LOD source isolation, rebuilding and owned removal without Python."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_skin_lods import make_skin,generate as generate_skin


async def management(client,chain):return await tool(client,'inspect_lod_management',chain=chain)


async def rebuild(client,state,**patch):
    recipe=state['suggested_rebuild']|patch
    return (await client.call_tool('rebuild_lod_chain',{'params':recipe|{'expected_management':state['management_sha256']},'wait':True})).data


def test_source_visibility_static_rebuild_and_remove(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_primitive',name='LifecycleSource',kind='UV_SPHERE',location=[4,0,2])
            before=await tool(client,'inspect_lod_source',name='LifecycleSource')
            first=(await client.call_tool('generate_lod_chain',{'params':{'name':'LifecycleSource','chain':'Lifecycle','expected_source':before['source_sha256'],'levels':[{'triangle_budget':250},{'triangle_budget':120}]},'wait':True})).data
            state=await management(client,'Lifecycle');assert state['can_rebuild']
            hidden=await tool(client,'configure_lod_source_visibility',chain='Lifecycle',expected_management=state['management_sha256'],hide_viewport=True,hide_render=True)
            assert hidden['source_visibility']['hide_viewport'] and not hidden['can_rebuild'] and hidden['can_remove']
            shown=await tool(client,'configure_lod_source_visibility',chain='Lifecycle',expected_management=hidden['management_sha256'],hide_viewport=False,hide_render=False)
            assert shown['can_rebuild'] and shown['source_sha256']==before['source_sha256']
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'remove_lod_chain',chain='Lifecycle',expected_management=hidden['management_sha256'])
            updated=await rebuild(client,shown,levels=[{'triangle_budget':200},{'triangle_budget':80}])
            assert updated['valid'] and updated['levels'][-1]['triangles']<=80
            operation=(await client.call_tool('get_operation',{'operation_id':updated['operation_id']})).data
            assert operation['progress']['storage']['free_bytes']>0
            assert (await tool(client,'inspect_lod_source',name='LifecycleSource'))['source_sha256']==before['source_sha256']
            await client.call_tool('save_blend',{'path':'lod-lifecycle.blend'})
            await client.call_tool('open_blend',{'path':'lod-lifecycle.blend'})
            fresh=await management(client,'Lifecycle');assert fresh['can_remove'] and fresh['can_rebuild']
            await tool(client,'remove_lod_chain',chain='Lifecycle',expected_management=fresh['management_sha256'])
            assert (await tool(client,'inspect_lod_source',name='LifecycleSource'))['source_sha256']==before['source_sha256']
            if evidence:=os.environ.get('MCPBLENDER_LOD_MANAGEMENT_EVIDENCE_DIR'):
                out=Path(evidence);out.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'library/lod-lifecycle.blend',out/'lod-lifecycle.blend')
                (out/'lifecycle-proof.json').write_text(json.dumps({'original':first,'replacement':updated},indent=2))
    asyncio.run(run())


def test_skinned_and_morph_rebuild_keep_source_controllers(assets_live):
    async def run():
        async with client_for(path) as client:
            await make_skin(client,'LifecycleSkin','LifecycleRig',x=20)
            await generate_skin(client,'LifecycleSkin','LifecycleSkinLOD')
            before=await tool(client,'inspect_animation_channels',name='LifecycleRig')
            state=await management(client,'LifecycleSkinLOD');assert state['can_rebuild'],state
            changed=await rebuild(client,state,levels=[{'triangle_budget':220},{'triangle_budget':100}])
            assert changed['valid'] and changed['skin']
            assert (await tool(client,'inspect_animation_channels',name='LifecycleRig'))['animation_sha256']==before['animation_sha256']
            fresh=await management(client,'LifecycleSkinLOD');assert fresh['can_remove']
            await tool(client,'remove_lod_chain',chain='LifecycleSkinLOD',expected_management=fresh['management_sha256'])
            assert (await tool(client,'inspect_animation_channels',name='LifecycleRig'))['animation_sha256']==before['animation_sha256']
            # A dense primitive with a sparse relative target follows source keys.
            await tool(client,'create_primitive',name='LifecycleMorph',kind='UV_SPHERE',location=[30,0,2])
            await tool(client,'create_shape_key',name='LifecycleMorph',key='Tip',vertices=[{'vertex':0,'value':[0,0,.15]}])
            await tool(client,'create_morph_clip',name='LifecycleMorph',clip='LifecycleMorphClip',tracks=[{'key':'Tip','keyframes':[{'frame':1,'value':0},{'frame':5,'value':1},{'frame':9,'value':0}]}])
            source=await tool(client,'inspect_lod_source',name='LifecycleMorph',deformation='MORPH')
            await client.call_tool('generate_lod_chain',{'params':{'name':'LifecycleMorph','deformation':'MORPH','chain':'LifecycleMorphLOD','expected_source':source['source_sha256'],'levels':[{'triangle_budget':250},{'triangle_budget':120}],'max_relative_error':.3,'max_pose_error':.3,'pose_frames':[1,5,9]},'wait':True})
            state=await management(client,'LifecycleMorphLOD');assert state['can_rebuild'],state
            changed=await rebuild(client,state,levels=[{'triangle_budget':220},{'triangle_budget':100}]);assert changed['valid'] and changed['morph']
            assert (await tool(client,'inspect_lod_source',name='LifecycleMorph',deformation='MORPH'))['source_sha256']==source['source_sha256']
            fresh=await management(client,'LifecycleMorphLOD');assert fresh['can_remove'],fresh
            await tool(client,'remove_lod_chain',chain='LifecycleMorphLOD',expected_management=fresh['management_sha256'])
            assert (await tool(client,'inspect_lod_source',name='LifecycleMorph',deformation='MORPH'))['source_sha256']==source['source_sha256']
    _,path=assets_live
    asyncio.run(run())
