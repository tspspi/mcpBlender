"""Native rest edits and real deformation through MCP, code execution disabled."""
import asyncio
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_skeletal_animation import make_limb
from test_constraints import sample


async def info(client,name,**params):return await tool(client,'inspect_armature_rest',name=name,**params)


async def edit(client,name,**params):
    before=await info(client,name)
    return (await client.call_tool('edit_armature_rest',{'params':{'name':name,'expected_rest':before['rest_sha256'],**params},'wait':True})).data


def test_existing_bones_additions_connections_and_validation(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_armature',name='RestRig',bones=[{'name':'Root','head':[0,0,0],'tail':[0,0,1]},{'name':'Arm','head':[0,0,1],'tail':[0,0,3],'parent':'Root','connected':True}])
            before=await info(client,'RestRig',limit=1)
            assert before['next_offset']==1 and before['bones'][0]['name']=='Root'
            selected=(await client.call_tool('get_scene_info')).data['active_object']
            after=await edit(client,'RestRig',bones=[{'name':'Root','tail':[0,0,2],'roll_degrees':30}],add_bones=[{'name':'Hand','head':[0,0,3],'tail':[0,0,4],'parent':'Arm','connected':True,'deform':False}])
            by_name={b['name']:b for b in after['bones']}
            assert by_name['Arm']['head']==[0,0,2] and by_name['Arm']['tail']==[0,0,3]
            assert by_name['Root']['roll_degrees']==pytest.approx(30,abs=1e-4)
            assert after['followed_connected_heads']==['Arm'] and after['added_bones']==['Hand']
            assert not after['isolated_armature_data'] and after['data']==before['data']
            assert (await client.call_tool('get_scene_info')).data['active_object']==selected
            with pytest.raises(ToolError,match='stale'):
                await client.call_tool('edit_armature_rest',{'params':{'name':'RestRig','expected_rest':before['rest_sha256'],'bones':[{'name':'Root','deform':False}]},'wait':True})
            for bones,message in [([{'name':'Root','parent':'Hand'}],'cycle'),([{'name':'Arm','head':[1,0,1]}],'connected head'),([{'name':'Hand','head':[0,0,3],'tail':[0,0,3]}],'nonzero')]:
                with pytest.raises(ToolError,match=message):await edit(client,'RestRig',bones=bones)
                assert (await info(client,'RestRig'))['rest_sha256']==after['rest_sha256']
            unparented=await edit(client,'RestRig',bones=[{'name':'Hand','parent':'','connected':False,'inherit_scale':'NONE','inherit_rotation':False,'local_location':False}])
            hand=next(b for b in unparented['bones'] if b['name']=='Hand')
            assert hand['parent'] is None and hand['inherit_scale']=='NONE' and not hand['inherit_rotation'] and not hand['local_location']
    asyncio.run(run())


def test_bound_animated_rest_change_preserves_channels_weights_and_peer(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await make_limb(client,'RestMotion','RestSkin',x=10)
            await tool(client,'create_animation_clip',name='RestMotion',clip='RestBend',tracks=[{'bone':'Tip','property':'rotation_degrees','keyframes':[{'frame':1,'value':[0,0,0]},{'frame':9,'value':[90,0,0]}]}])
            await client.call_tool('set_frame',{'frame':5})
            original=await info(client,'RestMotion')
            assert original['impact']['deformation_change_acknowledgement_required']
            with pytest.raises(ToolError,match='allow_deformation_change'):await edit(client,'RestMotion',bones=[{'name':'Tip','head':[0,0,1.5],'connected':False}])
            await tool(client,'duplicate_object',name='RestMotion',new_name='RestPeer',linked_data=True)
            peer=await info(client,'RestPeer')
            clip=await tool(client,'inspect_animation_channels',name='RestMotion')
            weights=await tool(client,'inspect_rig',name='RestMotion')
            before_pose=await sample(client,'RestMotion',frames=[1,9],meshes=['RestSkin'],sample_limit=20)
            with pytest.raises(ToolError,match='shared'):await edit(client,'RestMotion',allow_deformation_change=True,bones=[{'name':'Tip','head':[0,0,1.5],'connected':False}])
            changed=await edit(client,'RestMotion',make_single_user=True,allow_deformation_change=True,bones=[{'name':'Tip','head':[0,0,1.5],'connected':False,'roll_degrees':0}])
            peer_after=await info(client,'RestPeer')
            assert changed['isolated_armature_data'] and peer_after['bones']==peer['bones'] and peer_after['data']==peer['data']
            assert (await tool(client,'inspect_animation_channels',name='RestMotion'))['animation_sha256']==clip['animation_sha256']
            assert (await tool(client,'inspect_rig',name='RestMotion'))['meshes'][0]['vertex_samples']==weights['meshes'][0]['vertex_samples']
            after_pose=await sample(client,'RestMotion',frames=[1,9],meshes=['RestSkin'],sample_limit=20)
            assert after_pose['samples'][0]['meshes'][0]['geometry_sha256']==before_pose['samples'][0]['meshes'][0]['geometry_sha256']
            assert after_pose['samples'][1]['meshes'][0]['vertex_samples'][16]['world']==pytest.approx([9.8,-.5,1.3],abs=1e-5)
            assert before_pose['samples'][1]['meshes'][0]['vertex_samples'][16]['world']==pytest.approx([9.8,-1,.8],abs=1e-5)
            assert (await client.call_tool('get_scene_info')).data['frame']==5
            fingerprint=changed['rest_sha256']
            await client.call_tool('save_blend',{'path':'rest-refinement.blend'})
            await client.call_tool('open_blend',{'path':'rest-refinement.blend'})
            assert (await info(client,'RestMotion'))['rest_sha256']==fingerprint
    asyncio.run(run())
