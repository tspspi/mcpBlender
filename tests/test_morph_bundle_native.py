"""Timeline-baked morph bundles, native fidelity and transactional cleanup."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


@pytest.mark.parametrize('scene_unit_scale',[1,.01])
def test_morph_bundle_native_timeline_controls_both_modes_and_rollback(tmp_path,scene_unit_scale):
    source=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(source))+')\nSCENE_UNIT_SCALE='+repr(scene_unit_scale)+'\n'+r'''
import bpy,json
from pathlib import Path
from mathutils import Vector
from mcpblender.blender import lods,morph_lods,morph_lod_export as delivery,rigging,bridge
from mcpblender.lod_contracts import Generate,Export,ExportPlan
from mcpblender.skin_glb import Document
from mcpblender.lod_files import validate
root=Path(__file__).parent
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda v:None
bpy.context.scene.render.fps=12
bpy.context.scene.unit_settings.scale_length=SCENE_UNIT_SCALE
for skinned in (False,True):
    label='SkinMorph' if skinned else 'MorphOnly'
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=(4,0,1));obj=bpy.context.object;obj.name=label
    basis=obj.shape_key_add(name='Basis');up=obj.shape_key_add(name='Up');relative=obj.shape_key_add(name='Relative');relative.relative_key=up
    for i,v in enumerate(basis.data):up.data[i].co=v.co+Vector((0,0,.2*(v.co.z+1)));relative.data[i].co=up.data[i].co+Vector((.1*v.co.x,0,0))
    mask=obj.vertex_groups.new(name='Mask');mask.add(list(range(len(obj.data.vertices))),.5,'REPLACE');relative.vertex_group='Mask'
    for frame,value in [(1,0),(5,1),(9,0)]:up.value=value;up.keyframe_insert('value',frame=frame)
    source_keys=obj.data.shape_keys;action=source_keys.animation_data.action;source_keys.animation_data.action=None
    track=source_keys.animation_data.nla_tracks.new();strip=track.strips.new('SourceComposition',1,action);strip.action_slot=action.slots[0]
    control=bpy.data.objects.new(label+'Control',None);bpy.context.scene.collection.objects.link(control);control['amount']=.6
    f=relative.driver_add('value');f.driver.expression='amount';var=f.driver.variables.new();var.name='amount';var.type='SINGLE_PROP';var.targets[0].id=control;var.targets[0].data_path='["amount"]'
    rig=None
    if skinned:
        rigging.create_armature({'name':'Rig','location':[4,0,1],'bones':[{'name':'object','head':[0,0,-1],'tail':[0,0,1]},{'name':'MaskBone','head':[0,0,1],'tail':[0,0,2]}]})
        rig=bpy.data.objects['Rig'];rig.data.bones['MaskBone'].use_deform=False
        g=obj.vertex_groups.new(name='object');g.add(list(range(len(obj.data.vertices))),1,'REPLACE');m=obj.modifiers.new('Skin','ARMATURE');m.object=rig
        g=obj.vertex_groups.new(name='MaskBone');g.add(list(range(len(obj.data.vertices))),.7,'REPLACE')
        world=obj.matrix_world.copy();obj.parent=rig;obj.matrix_world=world
        constraint=rig.pose.bones['object'].constraints.new('COPY_ROTATION');constraint.target=control
        for frame,value in [(1,0),(5,.4),(9,0)]:control.rotation_euler.y=value;control.keyframe_insert('rotation_euler',frame=frame)
        for frame,value in [(1,4),(9,5)]:rig.location.x=value;rig.keyframe_insert('location',frame=frame)
    bpy.context.scene.frame_set(3,subframe=.25)
    mode='SKINNED' if rig else 'MORPH';src=lods.inspect_source({'name':obj.name,'deformation':mode})
    generated=lods.generate(Generate.model_validate({'name':obj.name,'deformation':mode,'chain':label+'LOD','expected_source':src['source_sha256'],'levels':[{'triangle_budget':400}],'pose_frames':[1,5,9]}).model_dump())
    specs=[{'name':'Negative','frame_start':-3,'frame_end':1},{'name':'Motion','frame_start':1,'frame_end':9}]
    p=Export.model_validate({'chain':label+'LOD','expected_chain':generated['chain_sha256'],'directory':str(root/(label+'Bundle')),'timeline_clips':specs}).model_dump()
    planned=delivery.plan(ExportPlan.model_validate({'chain':label+'LOD','timeline_clips':specs}).model_dump());assert planned['can_export'],planned
    p['expected_animation']=planned['animation_sha256']
    def counts():return tuple(len(c) for c in (bpy.data.objects,bpy.data.meshes,bpy.data.armatures,bpy.data.shape_keys,bpy.data.actions,bpy.data.collections))
    if rig:rig.hide_select=True;rig.hide_set(True)
    original=counts();saved=(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe);source_guard=morph_lods.definition(obj)
    if not rig:
        control['amount']=.2;control.update_tag();bpy.context.scene.frame_set(saved[0],subframe=saved[1]);bpy.context.view_layer.update()
        try:delivery.export(p)
        except ValueError as e:assert 'fingerprint is stale' in str(e)
        else:raise AssertionError('Expected stale controller guard refusal')
        assert not Path(p['directory']).exists()
        control['amount']=.6;control.update_tag();bpy.context.scene.frame_set(saved[0],subframe=saved[1]);bpy.context.view_layer.update()
    if rig:
        rig.pose.bones['MaskBone'].scale.x=float('nan');bpy.context.scene.frame_set(saved[0],subframe=saved[1]);bpy.context.view_layer.update()
        try:
            try:delivery.export(p)
            except ValueError:pass
            else:raise AssertionError('Expected nonfinite unused bone pose refusal')
        finally:
            rig.pose.bones['MaskBone'].scale.x=1;bpy.context.scene.frame_set(saved[0],subframe=saved[1]);bpy.context.view_layer.update()
        assert counts()==original and not Path(p['directory']).exists()
    original_selected=[o.name for o in bpy.context.selected_objects];original_active=bpy.context.view_layer.objects.active.name
    if not rig:
        state={}
        def progress(v):state.update(v)
        def cancel():
            if state.get('phase')==cancel_phase:raise bridge.OperationCancelled('during '+cancel_phase)
        for cancel_phase in ('baking morph timeline','verified decoded morph playback'):
            state={};bridge.report_progress=progress;bridge.check_cancelled=cancel
            try:delivery.export(p)
            except bridge.OperationCancelled:pass
            else:raise AssertionError('Expected cancellation')
            assert counts()==original,(counts(),original)
            assert not Path(p['directory']).exists() and not list(root.glob('.mcpblender-lod-*'))
            assert saved==(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
            assert morph_lods.definition(obj)==source_guard
        bridge.report_progress=lambda v:None;bridge.check_cancelled=lambda:None
        replay=Document.replay
        def broken(self,*args,**kwargs):
            result=replay(self,*args,**kwargs);result['points']=[(p[0]+.1,p[1],p[2]) for p in result['points']];return result
        Document.replay=broken
        try:
            try:delivery.export(p)
            except ValueError as e:assert 'Decoded morph' in str(e),str(e)
            else:raise AssertionError('Expected independent replay refusal')
        finally:Document.replay=replay
        assert counts()==original and not Path(p['directory']).exists()
    result=delivery.export(p);assert result['valid'],result
    assert counts()==original,(counts(),original)
    assert saved==(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
    assert morph_lods.definition(obj)==source_guard
    assert [o.name for o in bpy.context.selected_objects]==original_selected and bpy.context.view_layer.objects.active.name==original_active
    assert lods.inspect_chain({'chain':label+'LOD'})['chain_sha256']==generated['chain_sha256']
    data=json.loads((Path(p['directory'])/'manifest.json').read_text())
    assert len(data['clips'])==2 and data['reference_frame']==-3
    for level in data['levels']:
        assert set(level['skin']['morph_targets'])=={'Up','Relative'} and len(level['skin']['clips'])==2
        assert max(s.get('max_vertex_error',0) for s in level['playback'])<.001
        assert all(c['native_vertex_error']<.001 for c in level['timeline_bake'])
    assert validate(p['directory'])['valid']
    unit=bpy.context.scene.unit_settings.scale_length
    raw=Document(Path(p['directory'])/'level_00.glb',morphs=True)
    native=Document(Path(p['directory'])/'level_00.glb',morphs=True,comparison_unit_scale=unit)
    indices=raw.representatives(16);a=raw.replay(None,0,indices)['points'];b=native.replay(None,0,indices)['points']
    assert all(abs(x-y*unit)<1e-6 for p0,p1 in zip(a,b) for x,y in zip(p0,p1))
    assert all(2*unit<p0[0]<7*unit for p0 in a)
    if unit!=1:assert raw.report()['coordinate_space']=='METRES' and native.report()['coordinate_space']=='SOURCE_SCENE_UNITS'
    manifest=Path(p['directory'])/'manifest.json';original_text=manifest.read_text()
    for corrupt in ('fps','proof','bounds'):
        changed=json.loads(original_text)
        if corrupt=='fps':changed['fps']*=2
        elif corrupt=='proof':changed['levels'][0]['playback'].pop(0)
        else:changed['levels'][0]['position_bounds']['min']=[float('nan')]*3
        manifest.write_text(json.dumps(changed))
        try:validate(p['directory'])
        except ValueError:pass
        else:raise AssertionError('Expected inconsistent timeline/proof refusal')
        manifest.write_text(original_text)
    bound=Export.model_validate({'chain':label+'LOD','expected_chain':generated['chain_sha256'],'directory':str(root/(label+'Bind')),'animations':False}).model_dump()
    assert delivery.export(bound)['valid']
    assert counts()==original and saved==(bpy.context.scene.frame_current,bpy.context.scene.frame_subframe)
    if rig:assert rig.hide_select and rig.hide_get()
    assert source_keys.animation_data.action is None and source_keys.animation_data.nla_tracks[0]==track and f.driver.expression=='amount'
print('MORPH_BUNDLE_NATIVE_OK',flush=True)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=180)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'MORPH_BUNDLE_NATIVE_OK' in result.stdout
    if evidence:=os.environ.get('MCPBLENDER_MORPH_BUNDLE_EVIDENCE_DIR'):
        out=Path(evidence);out.mkdir(parents=True,exist_ok=True)
        for name in ('MorphOnlyBundle','SkinMorphBundle'):shutil.copytree(tmp_path/name,out/name,dirs_exist_ok=True)
