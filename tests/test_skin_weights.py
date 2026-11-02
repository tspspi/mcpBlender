"""Real skin editing with code execution disabled at the MCP boundary."""
import asyncio
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_skeletal_animation import make_limb
from test_constraints import sample


async def inspect(client,name,**params):return await tool(client,'inspect_skin_weights',name=name,**params)


async def edit(client,command,name,**params):
    info=await inspect(client,name)
    return (await client.call_tool(command,{'params':{'name':name,'expected_weights':info['weights_sha256'],**params},'wait':True})).data


def test_repair_smooth_stale_and_real_deformation(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await make_limb(client,'WeightRig','WeightSkin',x=0)
            before=await inspect(client,'WeightSkin');assert not any(before['issues'].values())
            broken=await edit(client,'set_skin_weights','WeightSkin',weights=[{'vertex':0,'weights':{}},{'vertex':16,'weights':{'Base':.2,'Tip':.1}}],normalize=False,allow_unweighted=True)
            assert broken['issues']['unweighted']==1 and broken['issues']['unnormalized']==1
            with pytest.raises(ToolError,match='stale'):
                await client.call_tool('repair_skin_weights',{'params':{'name':'WeightSkin','expected_weights':before['weights_sha256']},'wait':True})
            with pytest.raises(ToolError,match='No unlocked weights'):
                await edit(client,'repair_skin_weights','WeightSkin')
            assert (await inspect(client,'WeightSkin'))['weights_sha256']==broken['weights_sha256']
            fixed=await edit(client,'repair_skin_weights','WeightSkin',unweighted='NEAREST',max_influences=1)
            assert not any(fixed['issues'].values()) and fixed['max_influences']==1
            assert fixed['vertex_samples'][0]['weights']=={'Base':1}
            assert fixed['vertex_samples'][16]['weights']=={'Base':1}
            await tool(client,'create_animation_clip',name='WeightRig',clip='WeightMotion',tracks=[{'bone':'Tip','property':'rotation_degrees','keyframes':[{'frame':1,'value':[0,0,0]},{'frame':9,'value':[90,0,0]}]}])
            before_pose=await sample(client,'WeightRig',frames=[9],meshes=['WeightSkin'],sample_limit=20)
            await edit(client,'set_skin_weights','WeightSkin',weights=[{'vertex':16,'weights':{'Tip':1}}])
            after_pose=await sample(client,'WeightRig',frames=[9],meshes=['WeightSkin'],sample_limit=20)
            assert before_pose['samples'][0]['meshes'][0]['vertex_samples'][16]['world']!=after_pose['samples'][0]['meshes'][0]['vertex_samples'][16]['world']
            await edit(client,'set_skin_weights','WeightSkin',weights=[{'vertex':v,'weights':{'Base':1} if v!=4 else {'Tip':1}} for v in range(20)])
            smooth=await edit(client,'smooth_skin_weights','WeightSkin',vertices=[0,4],strength=1,iterations=1)
            # Vertex 0 neighbors 1,3,4. Vertex 4 uses the frozen original 0,5,7,8.
            assert smooth['vertex_samples'][0]['weights']==pytest.approx({'Base':2/3,'Tip':1/3})
            assert smooth['vertex_samples'][4]['weights']=={'Base':1}
            assert smooth['vertex_samples'][5]['weights']=={'Base':1}
            report=await inspect(client,'WeightSkin',issues_only=True,limit=1)
            assert report['total_matching_vertices']==0
            fingerprint=(await inspect(client,'WeightSkin'))['weights_sha256']
            await client.call_tool('save_blend',{'path':'skin-weights.blend'})
            await client.call_tool('open_blend',{'path':'skin-weights.blend'})
            assert (await inspect(client,'WeightSkin'))['weights_sha256']==fingerprint
    asyncio.run(run())


def test_mirror_shared_isolation_and_binding(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_armature',name='MirrorRig',bones=[{'name':'Left','head':[-1,0,0],'tail':[-1,0,2]},{'name':'Right','head':[1,0,0],'tail':[1,0,2]}])
            await tool(client,'create_mesh',name='MirrorSkin',vertices=[[-1,0,1],[-1,0,2],[-1,.2,1],[1,0,1],[1,0,2],[1,.2,1]],faces=[[0,1,2],[3,4,5]])
            await tool(client,'bind_mesh',name='MirrorSkin',armature='MirrorRig',method='RIGID',bone='Left')
            await tool(client,'duplicate_object',name='MirrorSkin',new_name='MirrorPeer',linked_data=True)
            peer=await inspect(client,'MirrorPeer')
            with pytest.raises(ToolError,match='shared'):
                await edit(client,'mirror_skin_weights','MirrorSkin',direction='NEGATIVE_TO_POSITIVE',bone_pairs=[{'left':'Left','right':'Right'}])
            mirrored=await edit(client,'mirror_skin_weights','MirrorSkin',make_single_user=True,direction='NEGATIVE_TO_POSITIVE',bone_pairs=[{'left':'Left','right':'Right'}])
            assert mirrored['isolated_mesh_data'] and mirrored['changed_vertices']==3
            assert mirrored['vertex_samples'][0]['weights']=={'Left':1} and mirrored['vertex_samples'][3]['weights']=={'Right':1}
            assert (await inspect(client,'MirrorPeer'))['weights_sha256']==peer['weights_sha256']
            await tool(client,'create_animation_clip',name='MirrorRig',clip='MirrorMotion',tracks=[{'bone':b,'property':'rotation_degrees','keyframes':[{'frame':1,'value':[0,0,0]},{'frame':9,'value':[angle,0,0]}]} for b,angle in [('Left',30),('Right',-30)]])
            posed=await sample(client,'MirrorRig',frames=[9],meshes=['MirrorSkin','MirrorPeer'])
            skin,peer_mesh=posed['samples'][0]['meshes']
            assert skin['vertex_samples'][4]['world'][1]>0 and peer_mesh['vertex_samples'][4]['world'][1]<0
            binding=await edit(client,'configure_skin_binding','MirrorSkin',preserve_volume=True,use_bone_envelopes=True)
            assert binding['binding']['use_deform_preserve_volume'] and binding['binding']['use_bone_envelopes']
            swapped=await edit(client,'mirror_skin_weights','MirrorSkin',direction='SWAP')
            assert swapped['vertex_samples'][0]['weights']=={'Right':1} and swapped['vertex_samples'][3]['weights']=={'Left':1}
            before=swapped['weights_sha256']
            with pytest.raises(ToolError,match='mask group'):
                await edit(client,'configure_skin_binding','MirrorSkin',vertex_group='Missing')
            assert (await inspect(client,'MirrorSkin'))['weights_sha256']==before
    asyncio.run(run())


def test_mid_write_cancellation_reports_storage_and_restores_weights(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_armature',name='CancelWeightRig',bones=[{'name':f'Bone{i}','head':[i,0,0],'tail':[i,0,1]} for i in range(32)])
            await tool(client,'create_mesh',name='CancelWeightSkin',vertices=[[i%100,i//100,0] for i in range(10000)],faces=[[0,1,100]])
            await tool(client,'bind_mesh',name='CancelWeightSkin',armature='CancelWeightRig',method='RIGID',bone='Bone0')
            before=await inspect(client,'CancelWeightSkin')
            scene=(await client.call_tool('get_scene_info')).data
            weights={f'Bone{i}':1/32 for i in range(32)}
            params={'name':'CancelWeightSkin','expected_weights':before['weights_sha256'],'weights':[{'vertex':i,'weights':weights} for i in range(10000)]}
            queued=(await client.call_tool('set_skin_weights',{'params':params})).data
            for _ in range(500):
                operation=(await client.call_tool('get_operation',{'operation_id':queued['operation_id']})).data
                if operation.get('progress',{}).get('phase')=='applying skin weights':break
                assert operation['state'] not in {'succeeded','failed','cancelled'},operation
                await asyncio.sleep(.01)
            else:pytest.fail('Skin operation did not start writing')
            assert operation['progress']['vertices']>0 and 'storage' in operation['progress']
            await client.call_tool('cancel_operation',{'operation_id':queued['operation_id']})
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':30})).data
            assert done['state']=='cancelled',done
            assert (await inspect(client,'CancelWeightSkin'))['weights_sha256']==before['weights_sha256']
            current=(await client.call_tool('get_scene_info')).data
            assert current['frame']==scene['frame'] and current['active_object']==scene['active_object']
            retry=await edit(client,'set_skin_weights','CancelWeightSkin',weights=[{'vertex':0,'weights':{'Bone1':1}}])
            assert retry['vertex_samples'][0]['weights']=={'Bone1':1}
    asyncio.run(run())


def test_mirror_plan_refuses_missing_and_conflicting_matches_atomically(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_armature',name='AmbiguousRig',bones=[{'name':'A','head':[0,0,0],'tail':[0,0,1]},{'name':'B','head':[0,0,1],'tail':[0,0,2]}])
            await tool(client,'create_mesh',name='AmbiguousSkin',vertices=[[-1,0,0],[-1,0,0],[1,0,0],[2,0,0]],faces=[[0,2,3],[1,2,3]])
            await tool(client,'bind_mesh',name='AmbiguousSkin',armature='AmbiguousRig',method='EXPLICIT',weights=[{'vertex':i,'weights':{'A' if i!=1 else 'B':1}} for i in range(4)])
            before=await inspect(client,'AmbiguousSkin')
            for selected,message in [([2],'ambiguous'),([3],'no source')]:
                with pytest.raises(ToolError,match=message):
                    await edit(client,'mirror_skin_weights','AmbiguousSkin',vertices=selected,direction='NEGATIVE_TO_POSITIVE')
                assert (await inspect(client,'AmbiguousSkin'))['weights_sha256']==before['weights_sha256']
    asyncio.run(run())
