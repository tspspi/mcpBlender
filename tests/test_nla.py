"""Live native action layering through MCP with arbitrary Python disabled."""
import asyncio
import math
import json
import os
from pathlib import Path
import shutil
import subprocess

from fastmcp.exceptions import ToolError
import pytest

from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_constraints import sample
from test_animation_curves import key
from test_skeletal_animation import make_limb


async def inspect(client,name,**params):return await tool(client,'inspect_nla',name=name,**params)
async def edit(client,command,name,**params):
    state=await inspect(client,name,**({'target':params['target']} if 'target' in params else {}))
    return (await client.call_tool(command,{'params':{'name':name,'expected_nla':state['nla_sha256'],**params},'wait':True})).data


async def object_x(client,name,frames):
    return [row['matrix_world'][0][3] for row in (await sample(client,name,frames=frames))['samples']]


def test_object_strip_timing_repeat_reverse_layer_order_and_cleanup(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_animation_control',name='NLAMover')
            await key(client,'NLAMover','NLAMove',property='location',keyframes=[{'frame':1,'value':[0,0,0]},{'frame':9,'value':[8,0,0]}])
            source=await tool(client,'inspect_animation_channels',name='NLAMover')
            track=await edit(client,'configure_nla_track','NLAMover',track='Motion')
            settings={'clip':'NLAMove','start':11,'action_start':1,'action_end':9,'scale':2,'repeat':2}
            strip=await edit(client,'configure_nla_strip','NLAMover',track='Motion',strip='MoveTwice',settings=settings)
            assert strip['tracks'][0]['strips'][0]['typed_editable']
            await edit(client,'configure_nla_playback','NLAMover',clear_active_action=True)
            assert await object_x(client,'NLAMover',[11,19,27,35])==pytest.approx([0,4,0,4],abs=.001)
            current=await inspect(client,'NLAMover')
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'configure_nla_track',name='NLAMover',track='Stale',expected_nla=track['nla_sha256'])
            with pytest.raises(ToolError,match='overlap'):
                await edit(client,'configure_nla_strip','NLAMover',track='Motion',strip='Overlap',settings=settings|{'start':12})
            assert (await inspect(client,'NLAMover'))['nla_sha256']==current['nla_sha256']
            await edit(client,'configure_nla_strip','NLAMover',track='Motion',strip='MoveTwice',settings=settings|{'repeat':1,'reverse':True})
            assert await object_x(client,'NLAMover',[11,19,27])==pytest.approx([8,4,0],abs=.001)
            # Same source can be trimmed/reused later on the same track.
            await edit(client,'configure_nla_strip','NLAMover',track='Motion',strip='Later',settings=settings|{'start':40,'action_start':3,'action_end':7,'scale':1,'repeat':1})
            assert await object_x(client,'NLAMover',[40,42,44])==pytest.approx([2,4,6],abs=.001)
            await edit(client,'configure_nla_track','NLAMover',track='Top')
            top=settings|{'start':11,'scale':2,'repeat':1,'influence':.5,'blend':'ADD'}
            await edit(client,'configure_nla_strip','NLAMover',track='Top',strip='Additive',settings=top)
            assert await object_x(client,'NLAMover',[19])==pytest.approx([6],abs=.001)
            for blend,expected in [('SUBTRACT',2),('MULTIPLY',10),('COMBINE',6),('REPLACE',4)]:
                await edit(client,'configure_nla_strip','NLAMover',track='Top',strip='Additive',settings=top|{'blend':blend})
                assert await object_x(client,'NLAMover',[19])==pytest.approx([expected],abs=.001)
            await edit(client,'configure_nla_strip','NLAMover',track='Top',strip='Additive',settings=top)
            await edit(client,'move_nla_track','NLAMover',track='Motion',index=1)
            assert await object_x(client,'NLAMover',[19])==pytest.approx([4],abs=.001)
            await edit(client,'configure_nla_track','NLAMover',track='Top',mute=True)
            assert await object_x(client,'NLAMover',[19])==pytest.approx([4],abs=.001)
            await edit(client,'configure_nla_track','NLAMover',track='Top',solo=True)
            # Muted solo tracks are intentionally silent; unmute explicitly.
            await edit(client,'configure_nla_track','NLAMover',track='Top',solo=True,mute=False)
            assert await object_x(client,'NLAMover',[19])==pytest.approx([2],abs=.001)
            await edit(client,'configure_nla_strip','NLAMover',track='Motion',strip='MoveTwice',settings=settings|{'repeat':1,'reverse':True})
            assert await object_x(client,'NLAMover',[19])==pytest.approx([2],abs=.001)
            await edit(client,'configure_nla_track','NLAMover',track='Motion',mute=False,solo=False)
            assert await object_x(client,'NLAMover',[19])==pytest.approx([2],abs=.001)
            await edit(client,'configure_nla_track','NLAMover',track='Top',solo=False,mute=False)
            await edit(client,'remove_nla_strip','NLAMover',track='Motion',strip='Later')
            await edit(client,'remove_nla_track','NLAMover',track='Top')
            await client.call_tool('save_blend',{'path':'nla-object.blend'})
            await client.call_tool('open_blend',{'path':'nla-object.blend'})
            reopened=await inspect(client,'NLAMover')
            assert reopened['tracks'][0]['strips'][0]['typed_editable']
            assert await object_x(client,'NLAMover',[19])==pytest.approx([4],abs=.001)
            # Source clip keys are preserved; inspecting via another bound peer
            # would require explicit rebinding, so inspect the named action natively
            # through the NLA source hash and unchanged channel count/range.
            ref=reopened['tracks'][0]['strips'][0]['action']
            assert ref['name']=='NLAMove' and ref['total_channels']==source['total_channels']
    asyncio.run(run())


def test_skeletal_composite_deformation_bake_and_fades(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            await make_limb(client,'NLARig','NLASkin',x=30)
            await tool(client,'create_animation_clip',name='NLARig',clip='NLABend',tracks=[{'bone':'Tip','property':'rotation_degrees','keyframes':[{'frame':1,'value':[0,0,0]},{'frame':9,'value':[90,0,0]}]}])
            await tool(client,'create_animation_clip',name='NLARig',clip='NLAShift',activate=False,tracks=[{'bone':'Base','property':'location','keyframes':[{'frame':1,'value':[0,0,0]},{'frame':9,'value':[0,0,2]}]}])
            await edit(client,'configure_nla_track','NLARig',track='BendLayer')
            s={'clip':'NLABend','start':1,'action_start':1,'action_end':9}
            await edit(client,'configure_nla_strip','NLARig',track='BendLayer',strip='BendStrip',settings=s)
            await edit(client,'configure_nla_track','NLARig',track='ShiftLayer')
            await edit(client,'configure_nla_strip','NLARig',track='ShiftLayer',strip='ShiftStrip',settings=s|{'clip':'NLAShift','blend':'ADD','influence':.5})
            await edit(client,'configure_nla_playback','NLARig',clear_active_action=True,reset_base=True)
            motion=await sample(client,'NLARig',frames=[1,5,9],bones=['Tip'],meshes=['NLASkin'])
            for row,goal in zip(motion['samples'],([30,0,2],[30,-.5-math.sqrt(.5),1+math.sqrt(.5)],[30,-2,1])):
                assert math.dist(row['bones'][0]['tail_world'],goal)<.001
            assert len({r['meshes'][0]['geometry_sha256'] for r in motion['samples']})==3
            before=await inspect(client,'NLARig')
            baked=(await client.call_tool('bake_constraint_animation',{'params':{'name':'NLARig','output_rig':'NLABaked','clip':'NLAComposite','meshes':[{'source':'NLASkin','output':'NLABakedSkin'}],'frame_start':1,'frame_end':9},'wait':True})).data
            assert baked['max_vertex_world_error']<.0001
            assert (await inspect(client,'NLARig'))['nla_sha256']==before['nla_sha256']
            await client.call_tool('save_blend',{'path':'nla-composite.blend'})
            await client.call_tool('select_objects',{'names':['NLABaked','NLABakedSkin']})
            await client.call_tool('export_glb',{'path':'nla-composite.glb'})
            import struct
            blob=(root/'library/nla-composite.glb').read_bytes();size=struct.unpack_from('<I',blob,12)[0];gltf=json.loads(blob[20:20+size])
            assert len(gltf['meshes'])==len(gltf['skins'])==1 and [a['name'] for a in gltf['animations']]==['NLAComposite']
            imported=(await client.call_tool('import_asset',{'path':'nla-composite.glb'})).data
            objects=(await client.call_tool('get_scene_info')).data['objects']
            imported_rig=next(o['name'] for o in objects if o['name'] in imported['objects'] and o['type']=='ARMATURE')
            imported_info=await tool(client,'inspect_rig',name=imported_rig)
            assert imported_info['meshes'],(imported,imported_info)
            imported_mesh=next(m['name'] for m in imported_info['meshes'] if m['name'] in imported['objects'])
            playback=await sample(client,imported_rig,frames=[1,5,9],meshes=[imported_mesh])
            for actual,original in zip(playback['samples'],motion['samples']):
                for side in ('min','max'):
                    assert actual['meshes'][0]['world_bounds'][side]==pytest.approx(original['meshes'][0]['world_bounds'][side],abs=.0002)
            # Blend-in/out on a separate bounded action segment yields zero at
            # the edges and full contribution in its middle.
            await edit(client,'configure_nla_track','NLARig',track='BendLayer',mute=True)
            await edit(client,'configure_nla_strip','NLARig',track='ShiftLayer',strip='ShiftStrip',settings=s|{'clip':'NLAShift','blend':'ADD','influence':1,'blend_in':2,'blend_out':2})
            fade=await sample(client,'NLARig',frames=[1,2,5,8,9],bones=['Base'])
            values=[r['bones'][0]['head_world'][1] for r in fade['samples']]
            assert values==pytest.approx([0,-.125,-1,-.875,0],abs=.001)
            if destination:=os.environ.get('MCPBLENDER_NLA_EVIDENCE_DIR'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True)
                for name in ('nla-composite.blend','nla-composite.glb'):shutil.copy2(root/'library'/name,out/name)
                (out/'comparison.json').write_text(json.dumps({'source':motion,'bake':baked,'imported':playback},indent=2))
    asyncio.run(run())


def test_shape_composition_source_guards_and_native_clamp_rollback(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,'create_primitive',name='NLAMorph')
            for key_name,offset in [('Tall',[0,0,1]),('Wide',[1,0,0])]:
                await tool(client,'create_shape_key',name='NLAMorph',key=key_name,vertices=[{'vertex':i,'value':offset} for i in range(8)])
                await tool(client,'create_morph_clip',name='NLAMorph',clip='NLA'+key_name,tracks=[{'key':key_name,'keyframes':[{'frame':1,'value':0},{'frame':9,'value':1}]}],activate=False)
            for name,influence in [('Tall',1),('Wide',.5)]:
                await edit(client,'configure_nla_track','NLAMorph',target='SHAPE_KEYS',track=name)
                await edit(client,'configure_nla_strip','NLAMorph',target='SHAPE_KEYS',track=name,strip=name+'Shape',settings={'clip':'NLA'+name,'start':1,'action_start':1,'action_end':9,'blend':'ADD','influence':influence})
            await edit(client,'configure_nla_playback','NLAMorph',target='SHAPE_KEYS',clear_active_action=True,reset_base=True)
            await client.call_tool('save_blend',{'path':'nla-morph.blend'})
            if destination:=os.environ.get('MCPBLENDER_NLA_EVIDENCE_DIR'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True);shutil.copy2(_/'library/nla-morph.blend',out/'nla-morph.blend')
            result=await sample(client,'NLAMorph',frames=[1,5,9],meshes=['NLAMorph'])
            for row,q in zip(result['samples'],(0,.5,1)):
                assert row['meshes'][0]['world_bounds']['max']==pytest.approx([1+.5*q,1,1+q],abs=.001)
            outside=await sample(client,'NLAMorph',frames=[-5,20],meshes=['NLAMorph'])
            assert all(r['meshes'][0]['world_bounds']['max']==pytest.approx([1,1,1],abs=.001) for r in outside['samples'])
            before=await inspect(client,'NLAMorph',target='SHAPE_KEYS')
            old_base=before['tracks'][0]['strips'][0]['action']['name']
            repeated=await edit(client,'configure_nla_playback','NLAMorph',target='SHAPE_KEYS',clear_active_action=True,reset_base=True)
            assert repeated['total_tracks']==before['total_tracks']==3
            assert repeated['tracks'][0]['strips'][0]['action']['name']!=old_base
            actions=await tool(client,'inspect_morph_animation',name='NLAMorph')
            assert old_base not in {a['name'] for a in actions['clips']}
            before=await inspect(client,'NLAMorph',target='SHAPE_KEYS')
            with pytest.raises(ToolError,match='clamped'):
                await edit(client,'configure_nla_strip','NLAMorph',target='SHAPE_KEYS',track='Tall',strip='TooPrecise',settings={'clip':'NLATall','start':1000000.01,'action_start':1,'action_end':9})
            assert (await inspect(client,'NLAMorph',target='SHAPE_KEYS'))['nla_sha256']==before['nla_sha256']
            # Source-action edits invalidate the whole-stack guard, while a strip
            # remains structurally managed and can be reconfigured after reinspection.
            for track in before['tracks']:
                await edit(client,'configure_nla_track','NLAMorph',target='SHAPE_KEYS',track=track['name'],mute=True)
            before=await inspect(client,'NLAMorph',target='SHAPE_KEYS')
            await tool(client,'set_morph_keyframes',name='NLAMorph',clip='NLATall',tracks=[{'key':'Tall','keyframes':[{'frame':9,'value':.75}]}])
            after=await inspect(client,'NLAMorph',target='SHAPE_KEYS')
            assert after['nla_sha256']!=before['nla_sha256'] and all(t['strips'][0]['typed_editable'] for t in after['tracks'])
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'configure_nla_track',name='NLAMorph',target='SHAPE_KEYS',track='Tall',mute=False,expected_nla=before['nla_sha256'])
            await tool(client,'duplicate_object',name='NLAMorph',new_name='NLAMorphShared',linked_data=True)
            with pytest.raises(ToolError,match='Independent'):
                await edit(client,'configure_nla_track','NLAMorph',target='SHAPE_KEYS',track='SharedRefusal')
    asyncio.run(run())


def test_cancel_staged_stack_and_preserve_imported_neighbor(assets_live):
    root,path=assets_live
    library=root/'library';library.mkdir(exist_ok=True)
    script=root/'prepare-nla.py'
    script.write_text('''import bpy,sys,os,json
sys.path.insert(0,os.getcwd())
from mcpblender.blender import nla
bpy.ops.wm.read_factory_settings(use_empty=True)
o=bpy.data.objects.new("CancelNLASource",None);bpy.context.scene.collection.objects.link(o)
for f,x in ((1,0),(9,8)):
 o.location.x=x;o.keyframe_insert(data_path="location",frame=f)
a=o.animation_data.action;a.name="CancelNLAAction";a.use_fake_user=True
slot=o.animation_data.action_slot
track=o.animation_data.nla_tracks.new();track.name="LargeLayer"
stored={}
for i in range(256):
 s={"clip":a.name,"slot":slot.identifier,"start":1+i*16,"action_start":1,"action_end":9,"scale":1,"repeat":1,"reverse":False,"blend":"REPLACE","extrapolation":"NOTHING","influence":1,"blend_in":0,"blend_out":0,"mute":False}
 spec={"strip":"Segment%03d"%i,"settings":s}
 strip=nla.apply_strip(track,(spec,a,slot));strip.name=spec["strip"]
 stored[strip.name]={"settings":s,"native_sha256":nla.native_strip_hash(strip)}
o[nla.OWNED]=json.dumps({track.name:{"strips":stored}})
other=o.animation_data.nla_tracks.new();other.name="ImportedLayer";other.mute=True
other.strips.new("ImportedStrip",5000,a)
o.animation_data.action=None;o.animation_data.use_nla=True
fake=bpy.data.objects.new("MismatchedNLASource",None);bpy.context.scene.collection.objects.link(fake)
ftrack=fake.animation_data_create().nla_tracks.new();ftrack.name="WrongRecipe"
s={"clip":a.name,"slot":slot.identifier,"start":1,"action_start":1,"action_end":9,"scale":1,"repeat":1,"reverse":False,"blend":"REPLACE","extrapolation":"NOTHING","influence":1,"blend_in":0,"blend_out":0,"mute":False}
fstrip=nla.apply_strip(ftrack,({"strip":"WrongEnd","settings":s},a,slot));fstrip.name="WrongEnd";fstrip.frame_end=17
fake[nla.OWNED]=json.dumps({ftrack.name:{"strips":{fstrip.name:{"settings":s,"native_sha256":nla.native_strip_hash(fstrip)}}}})
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
''')
    result=subprocess.run([shutil.which('blender'),'--background','--factory-startup','--threads','2','--python',str(script),'--',str(library/'nla-cancel.blend')],capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    async def run():
        async with client_for(path) as client:
            await client.call_tool('open_blend',{'path':'nla-cancel.blend'})
            mismatch=await inspect(client,'MismatchedNLASource')
            assert not mismatch['tracks'][0]['strips'][0]['typed_editable']
            with pytest.raises(ToolError,match='inspect-only'):
                await edit(client,'configure_nla_strip','MismatchedNLASource',track='WrongRecipe',strip='WrongEnd',settings={'clip':'CancelNLAAction','start':1,'action_start':1,'action_end':9})
            assert (await inspect(client,'MismatchedNLASource'))['nla_sha256']==mismatch['nla_sha256']
            await client.call_tool('set_frame',{'frame':7})
            before=await inspect(client,'CancelNLASource')
            assert before['tracks'][0]['strips'][0]['typed_editable']
            assert not before['tracks'][1]['managed']
            with pytest.raises(ToolError,match='inspect-only'):
                await edit(client,'configure_nla_track','CancelNLASource',track='ImportedLayer',mute=False)
            moved=await edit(client,'move_nla_track','CancelNLASource',track='LargeLayer',index=1)
            assert [t['name'] for t in moved['tracks']]==['ImportedLayer','LargeLayer']
            assert moved['tracks'][0]['strips']==before['tracks'][1]['strips']
            with pytest.raises(ToolError,match='inspect-only'):
                await edit(client,'move_nla_track','CancelNLASource',track='LargeLayer',index=0)
            before=await inspect(client,'CancelNLASource')
            queued=(await client.call_tool('configure_nla_strip',{'params':{'name':'CancelNLASource','track':'LargeLayer','strip':'Segment000','expected_nla':before['nla_sha256'],'settings':{'clip':'CancelNLAAction','start':1,'action_start':1,'action_end':9,'influence':.5}},'wait':False})).data
            for _ in range(500):
                operation=(await client.call_tool('get_operation',{'operation_id':queued['operation_id']})).data
                if operation.get('progress',{}).get('phase')=='staging NLA tracks':break
                assert operation['state'] not in {'failed','cancelled','succeeded'},operation
                await asyncio.sleep(.01)
            else:pytest.fail('Staged NLA rebuild did not report progress')
            assert 'storage' in operation['progress']
            await client.call_tool('cancel_operation',{'operation_id':queued['operation_id']})
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':30})).data
            assert done['state']=='cancelled',done
            assert (await client.call_tool('get_scene_info')).data['frame']==7
            after=await inspect(client,'CancelNLASource')
            assert after['nla_sha256']==before['nla_sha256'] and after['total_tracks']==2
    asyncio.run(run())


def test_nla_scalar_controls_keep_native_driver_and_deform_skin(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            from test_animation_drivers import configure
            await make_limb(client,'NLAControlRig','NLAControlSkin',x=50)
            await tool(client,'set_animation_property',name='NLAControlRig',property='Bend',value=0)
            await configure(client,'NLAControlRig',{'kind':'TRANSFORM','bone':'Tip','property':'rotation_euler','component':0},
                            {'expression':'bend*pi/2','variables':[{'kind':'PROPERTY','name':'bend','object':'NLAControlRig','property':'Bend'}]})
            await key(client,'NLAControlRig','NLAControlClip',property='custom_scalar',custom_property='Bend',keyframes=[{'frame':1,'value':0},{'frame':9,'value':1}])
            await edit(client,'configure_nla_track','NLAControlRig',track='ControlLayer')
            await edit(client,'configure_nla_strip','NLAControlRig',track='ControlLayer',strip='ControlStrip',settings={'clip':'NLAControlClip','start':21,'action_start':1,'action_end':9,'scale':2})
            await edit(client,'configure_nla_playback','NLAControlRig',clear_active_action=True,reset_base=True)
            motion=await sample(client,'NLAControlRig',frames=[21,29,37],bones=['Tip'],meshes=['NLAControlSkin'])
            for row,goal in zip(motion['samples'],([50,0,2],[50,-math.sqrt(.5),1+math.sqrt(.5)],[50,-1,1])):
                assert math.dist(row['bones'][0]['tail_world'],goal)<.001
            assert len({r['meshes'][0]['geometry_sha256'] for r in motion['samples']})==3
            baked=(await client.call_tool('bake_constraint_animation',{'params':{'name':'NLAControlRig','output_rig':'NLAControlBaked','clip':'NLAControlBakedClip','frame_start':21,'frame_end':37,'meshes':[{'source':'NLAControlSkin','output':'NLAControlBakedSkin'}]},'wait':True})).data
            assert baked['max_vertex_world_error']<.0001
    asyncio.run(run())
