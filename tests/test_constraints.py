"""Real IK and object constraint editing through MCP with Python disabled."""
import asyncio
import json
import math
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from fastmcp.exceptions import ToolError

from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_skeletal_animation import make_limb


async def inspect(client,name,bone=None):
    return await tool(client,'inspect_animation_constraints',name=name,**({'bone':bone} if bone else {}))


async def edit(client,name,constraint,settings,bone=None):
    info=await inspect(client,name,bone)
    return await tool(client,'configure_animation_constraint',name=name,constraint=constraint,settings=settings,expected_constraints=info['constraints_sha256'],**({'bone':bone} if bone else {}))


async def sample(client,name,**params):
    return (await client.call_tool('sample_constraint_animation',{'params':{'name':name,**params},'wait':True})).data


def test_ik_pole_animated_controls_deformation_reopen_render(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_armature',name='IKRig',bones=[{'name':'Base','head':[0,0,0],'tail':[.15,0,1]},{'name':'Tip','head':[.15,0,1],'tail':[0,0,2],'parent':'Base','connected':True}])
            vertices=[[dx,dy,z/2] for z in range(5) for dx,dy in [(-.2,-.2),(.2,-.2),(.2,.2),(-.2,.2)]]
            faces=[[0,3,2,1],[16,17,18,19]]+[[4*z+i,4*z+(i+1)%4,4*(z+1)+(i+1)%4,4*(z+1)+i] for z in range(4) for i in range(4)]
            await tool(client,'create_mesh',name='IKLimb',vertices=vertices,faces=faces)
            weights=[{'vertex':i,'weights':{'Base':1} if v[2]<1 else ({'Tip':1} if v[2]>1 else {'Base':.5,'Tip':.5})} for i,v in enumerate(vertices)]
            await tool(client,'bind_mesh',name='IKLimb',armature='IKRig',method='EXPLICIT',weights=weights)
            await tool(client,'create_animation_control',name='IKTarget',location=[.8,0,1.4])
            await tool(client,'create_animation_control',name='IKPole',location=[0,-2,1])
            # A helper parented to the rig object is safe: it does not inherit
            # the solved bone pose. This must not become an object-level false cycle.
            await tool(client,'set_parent',name='IKTarget',parent='IKRig')
            before=await inspect(client,'IKRig','Tip')
            spec={'type':'IK','target':{'name':'IKTarget'},'pole':{'name':'IKPole'},'chain_count':2,'pole_angle_degrees':0}
            configured=await edit(client,'IKRig','Reach',spec,bone='Tip')
            assert configured['total_constraints']==1 and configured['constraints'][0]['is_valid']
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'remove_animation_constraint',name='IKRig',bone='Tip',constraint='Reach',expected_constraints=before['constraints_sha256'])
            frames=[1,5,9];locations=[[.8,0,1.4],[-.6,.3,1.5],[.4,-.3,1.7]]
            await tool(client,'set_keyframes',name='IKTarget',data_path='location',keyframes=[{'frame':f,'value':v} for f,v in zip(frames,locations)])
            await client.call_tool('set_frame',{'frame':3})
            sample_frames=[1,3,5,7,9];expected_locations=[locations[0],[.1,.15,1.45],locations[1],[-.1,0,1.6],locations[2]]
            result=await sample(client,'IKRig',frames=sample_frames,bones=['Base','Tip'],meshes=['IKLimb'],sample_limit=20)
            assert result['restored_frame']==3 and (await client.call_tool('get_scene_info')).data['frame']==3
            for row,expected in zip(result['samples'],expected_locations):
                tip=next(b for b in row['bones'] if b['name']=='Tip')
                assert math.dist(tip['tail_world'],expected)<.015,(row,expected)
                assert row['meshes'][0]['non_finite_vertices']==0
            assert len({s['meshes'][0]['geometry_sha256'] for s in result['samples']})==5
            elbow=result['samples'][1]['bones'][0]['tail_world']
            await client.call_tool('set_object_transform',{'name':'IKPole','location':[0,2,1]})
            opposite=await sample(client,'IKRig',frames=[3],bones=['Base','Tip'])
            assert math.dist(elbow,opposite['samples'][0]['bones'][0]['tail_world'])>.2
            assert math.dist(opposite['samples'][0]['bones'][1]['tail_world'],expected_locations[1])<.015
            await client.call_tool('set_object_transform',{'name':'IKPole','location':[0,-2,1]})
            disabled=await edit(client,'IKRig','Reach',spec|{'influence':0},bone='Tip')
            off=await sample(client,'IKRig',frames=[3],bones=['Tip'])
            assert off['samples'][0]['bones'][0]['tail_world']==pytest.approx([0,0,2],abs=.001)
            await edit(client,'IKRig','Reach',spec,bone='Tip')
            # Existing simple clip switching remains guarded; it must not reset
            # this constraint rig or silently treat controller motion as a clip.
            with pytest.raises(ToolError,match='constraints'):
                await tool(client,'set_active_clip',name='IKRig')
            await client.call_tool('save_blend',{'path':'ik-controls.blend'})
            await client.call_tool('open_blend',{'path':'ik-controls.blend'})
            restored=await sample(client,'IKRig',frames=frames,bones=['Tip'],meshes=['IKLimb'])
            for row,expected in zip(restored['samples'],locations):assert math.dist(row['bones'][0]['tail_world'],expected)<.015
            await tool(client,'apply_material_preset',material='IKBlue',base_color=[.03,.2,.65,1],roughness=.35)
            await tool(client,'assign_material',objects=['IKLimb'],material='IKBlue')
            await client.call_tool('set_object_transform',{'name':'Cube','location':[-100,0,0]})
            await client.call_tool('set_frame',{'frame':5})
            await client.call_tool('run_action',{'action':'preview_setup','inputs':{'objects':['IKLimb'],'prefix':'IKView'},'wait':True})
            await tool(client,'configure_render',samples=8)
            q=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':'ik-limb.png','width':256,'height':192,'camera':'IKView_Camera','engine':'CYCLES'}})).data
            done=(await client.call_tool('wait_operation',{'operation_id':q['operation_id'],'timeout_seconds':60})).data
            assert done['state']=='succeeded',done
            rgb=subprocess.run(['ffmpeg','-v','error','-i',str(root/'library/ik-limb.png'),'-f','rawvideo','-pix_fmt','rgb24','-'],capture_output=True,check=True,timeout=20).stdout
            assert sum(b>r+30 and b>g+20 for r,g,b in zip(rgb[0::3],rgb[1::3],rgb[2::3]))>300
            await client.call_tool('save_blend',{'path':'ik-controls.blend','overwrite':True})
            if dest:=os.environ.get('MCPBLENDER_CONSTRAINT_EVIDENCE_DIR'):
                target=Path(dest);target.mkdir(parents=True,exist_ok=True)
                for name in ('ik-controls.blend','ik-limb.png'):shutil.copy2(root/'library'/name,target/name)
                (target/'samples.json').write_text(json.dumps(result,indent=2))
    asyncio.run(run())


def test_object_constraints_stack_order_limits_tracks_and_cycles(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_animation_control',name='Follower',location=[0,0,0])
            await tool(client,'create_animation_control',name='Source',location=[2,3,4])
            copy=await edit(client,'Follower','Follow',{'type':'COPY_LOCATION','target':{'name':'Source'}})
            row=(await sample(client,'Follower',frames=[1]))['samples'][0]
            assert [r[3] for r in row['matrix_world'][:3]]==pytest.approx([2,3,4])
            clamped=await edit(client,'Follower','Clamp',{'type':'LIMIT_LOCATION','minimum':[-1,-1,-1],'maximum':[1,1,1]})
            row=(await sample(client,'Follower',frames=[1]))['samples'][0]
            assert [r[3] for r in row['matrix_world'][:3]]==pytest.approx([1,1,1])
            moved=await tool(client,'move_animation_constraint',name='Follower',constraint='Clamp',expected_constraints=clamped['constraints_sha256'],index=0)
            row=(await sample(client,'Follower',frames=[1]))['samples'][0]
            assert [r[3] for r in row['matrix_world'][:3]]==pytest.approx([2,3,4])
            original=await inspect(client,'Source')
            with pytest.raises(ToolError,match='cycle'):
                await edit(client,'Source','Loop',{'type':'COPY_LOCATION','target':{'name':'Follower'}})
            assert (await inspect(client,'Source'))['constraints_sha256']==original['constraints_sha256']
            with pytest.raises(ToolError,match='type must match'):
                await edit(client,'Follower','Follow',{'type':'COPY_ROTATION','target':{'name':'Source'}})
            await tool(client,'remove_animation_constraint',name='Follower',constraint='Follow',expected_constraints=moved['constraints_sha256'])
            await client.call_tool('set_object_transform',{'name':'Source','rotation_euler':[0,0,.5],'scale':[2,3,4]})
            await client.call_tool('set_object_transform',{'name':'Follower','rotation_euler':[0,0,.6],'scale':[2,3,4]})
            for kind in ('COPY_ROTATION','COPY_TRANSFORMS','DAMPED_TRACK','LIMIT_ROTATION','LIMIT_SCALE'):
                settings={'type':kind}
                if kind.startswith('COPY') or kind=='DAMPED_TRACK':settings['target']={'name':'Source'}
                if kind=='LIMIT_ROTATION':settings.update(minimum_degrees=[-10,-10,-10],maximum_degrees=[10,10,10])
                result=await edit(client,'Follower','Check',settings)
                assert next(c for c in result['constraints'] if c['constraint']=='Check')['is_valid']
                matrix=(await sample(client,'Follower',frames=[1]))['samples'][0]['matrix_world']
                if kind=='COPY_ROTATION':assert math.atan2(matrix[1][0],matrix[0][0])==pytest.approx(.5,abs=1e-5)
                elif kind=='COPY_TRANSFORMS':
                    assert [r[3] for r in matrix[:3]]==pytest.approx([2,3,4])
                    assert [math.sqrt(sum(matrix[r][c]**2 for r in range(3))) for c in range(3)]==pytest.approx([2,3,4])
                elif kind=='DAMPED_TRACK':
                    direction=[matrix[r][1] for r in range(3)];goal=[v-matrix[r][3] for r,v in enumerate([2,3,4])]
                    assert sum(a*b for a,b in zip(direction,goal))/(math.sqrt(sum(v*v for v in direction))*math.sqrt(sum(v*v for v in goal)))>.999
                elif kind=='LIMIT_ROTATION':assert math.atan2(matrix[1][0],matrix[0][0])==pytest.approx(math.radians(10),abs=1e-5)
                elif kind=='LIMIT_SCALE':assert [math.sqrt(sum(matrix[r][c]**2 for r in range(3))) for c in range(3)]==pytest.approx([1,1,1])
                await tool(client,'remove_animation_constraint',name='Follower',constraint='Check',expected_constraints=result['constraints_sha256'])
            # Adding a helper dependency on a solved IK ancestor must also detect
            # the cycle created by the existing constraint, not only the new one.
            if 'IKRig' in {o['name'] for o in (await client.call_tool('get_scene_info')).data['objects']}:
                before=await inspect(client,'IKTarget')
                with pytest.raises(ToolError,match='cycle'):
                    await edit(client,'IKTarget','AncestorLoop',{'type':'COPY_LOCATION','target':{'name':'IKRig','bone':'Base'}})
                assert (await inspect(client,'IKTarget'))['constraints_sha256']==before['constraints_sha256']
    asyncio.run(run())


def test_same_rig_bone_targets_and_straight_chain_diagnostics(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_armature',name='BoneControlRig',bones=[{'name':'Base','head':[0,0,0],'tail':[.15,0,1]},{'name':'Tip','head':[.15,0,1],'tail':[0,0,2],'parent':'Base','connected':True},{'name':'HandTarget','head':[.8,0,1.4],'tail':[.8,0,1.6],'deform':False}])
            await tool(client,'create_animation_clip',name='BoneControlRig',clip='BoneControls',tracks=[{'bone':'HandTarget','property':'location','keyframes':[{'frame':1,'value':[0,0,0]},{'frame':5,'value':[-.5,0,0]}]}])
            configured=await edit(client,'BoneControlRig','HandIK',{'type':'IK','target':{'name':'BoneControlRig','bone':'HandTarget'},'chain_count':2},bone='Tip')
            assert not configured['constraints'][0]['ik_diagnostics']['rest_chain_collinear']
            result=await sample(client,'BoneControlRig',frames=[1,3,5],bones=['Tip','HandTarget'])
            for row in result['samples']:assert math.dist(row['bones'][0]['tail_world'],row['bones'][1]['head_world'])<.015
            assert (await tool(client,'inspect_animation',name='BoneControlRig'))['active_clip']=='BoneControls'
            await make_limb(client,'StraightRig','StraightMesh',x=10)
            await tool(client,'create_animation_control',name='StraightTarget',location=[10.8,0,1.4])
            inspected=await edit(client,'StraightRig','SingularIK',{'type':'IK','target':{'name':'StraightTarget'},'chain_count':2},bone='Tip')
            assert inspected['constraints'][0]['ik_diagnostics']['rest_chain_collinear']
            assert 'preferred bend' in inspected['constraints'][0]['ik_diagnostics']['warning']
    asyncio.run(run())


def test_imported_keyed_constraints_and_unknown_dependencies_are_preserved(assets_live):
    root,path=assets_live
    script=root/'imported-constraints.py'
    script.write_text('''import bpy,sys,resource
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
a=bpy.data.objects.new('KeyedOwner',None);bpy.context.scene.collection.objects.link(a)
b=bpy.data.objects.new('KeyedTarget',None);bpy.context.scene.collection.objects.link(b);b.location=(2,0,0)
c=a.constraints.new('COPY_LOCATION');c.name='KeyedFollow';c.target=b
c.influence=0;c.keyframe_insert('influence',frame=1);c.influence=1;c.keyframe_insert('influence',frame=5)
d=bpy.data.objects.new('DrivenTarget',None);bpy.context.scene.collection.objects.link(d)
f=d.driver_add('location',0);f.driver.type='SCRIPTED';f.driver.expression='1.0'
bpy.ops.object.armature_add();rig=bpy.context.object;rig.name='UnsupportedRig'
rig.pose.bones[0].constraints.new('SPLINE_IK')
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1],check_existing=False)
''')
    prepared=subprocess.run([shutil.which('blender'),'-b','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(script),'--',str(root/'library/imported-constraints.blend')],capture_output=True,text=True,timeout=60)
    assert prepared.returncode==0,prepared.stdout+prepared.stderr
    async def run():
        async with client_for(path) as client:
            await client.call_tool('open_blend',{'path':'imported-constraints.blend'})
            initial=await inspect(client,'KeyedOwner')
            assert initial['constraints'][0]['animated_paths'] and not initial['constraints'][0]['typed_editable']
            with pytest.raises(ToolError,match='Keyed/driven'):
                await edit(client,'KeyedOwner','KeyedFollow',{'type':'COPY_LOCATION','target':{'name':'KeyedTarget'}})
            with pytest.raises(ToolError,match='Keyed/driven'):
                await tool(client,'remove_animation_constraint',name='KeyedOwner',constraint='KeyedFollow',expected_constraints=initial['constraints_sha256'])
            for target,reason in (({'name':'DrivenTarget'},'Driver'),({'name':'UnsupportedRig','bone':'Bone'},'Unsupported constraint')):
                with pytest.raises(ToolError,match=reason):
                    await edit(client,'KeyedOwner','UnsupportedDependency',{'type':'COPY_LOCATION','target':target})
            assert (await inspect(client,'KeyedOwner'))['constraints_sha256']==initial['constraints_sha256']
    asyncio.run(run())
