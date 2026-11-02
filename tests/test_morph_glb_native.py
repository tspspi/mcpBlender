"""Independent replay compared with native morph and morph-plus-skin exports."""
import os
from pathlib import Path
import shutil
import subprocess
import pytest

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


def test_morph_glb_native_frame_and_vertex_correspondence(tmp_path):
    source=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(source))+')\n'+r'''
import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree
from mcpblender.blender import bridge,workflows,rigging
from mcpblender.skin_glb import Document,inspect_file
root=Path(__file__).parent
C=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))
for skinned in (False,True):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=12,location=(3,-2,1))
    obj=bpy.context.object;obj.name='SkinMorph' if skinned else 'MorphOnly'
    basis=obj.shape_key_add(name='Basis');up=obj.shape_key_add(name='Up');wide=obj.shape_key_add(name='Wide')
    for i,p in enumerate(basis.data):
        up.data[i].co=p.co+Vector((0,0,.3*(p.co.z+1)))
        wide.data[i].co=p.co+(Vector((.2*p.co.x,.2*p.co.y,0)) if p.co.z>.5 else Vector((0,0,0)))
    for frame,value in [(1,0),(5,1),(9,0)]:
        up.value=value;wide.value=value*.5;up.keyframe_insert('value',frame=frame);wide.keyframe_insert('value',frame=frame)
    targets=[obj.name];rig=None
    if skinned:
        rigging.create_armature({'name':'Rig','location':[3,-2,1],'bones':[{'name':'Root','head':[0,0,-1],'tail':[0,0,1]}]})
        rig=bpy.data.objects['Rig'];world=obj.matrix_world.copy();obj.parent=rig;obj.matrix_world=world
        group=obj.vertex_groups.new(name='Root');group.add(list(range(len(obj.data.vertices))),1,'REPLACE');mod=obj.modifiers.new('Skin','ARMATURE');mod.object=rig
        bone=rig.pose.bones['Root'];bone.rotation_mode='XYZ'
        # Shared action name makes the native exporter merge rig/morph channels.
        action=obj.data.shape_keys.animation_data.action
        rig.animation_data_create().action=action;slot=action.slots.new('OBJECT',rig.name);rig.animation_data.action_slot=slot
        for frame,value in [(1,0),(5,.6),(9,0)]:bone.rotation_euler.y=value;bone.keyframe_insert('rotation_euler',frame=frame)
        targets=[rig.name,obj.name]
    bpy.context.scene.render.fps=12;bpy.context.scene.frame_set(3)
    path=root/(obj.name+'.glb')
    workflows.export_objects_glb({'objects':targets,'path':str(path),'animations':True,'overwrite':False,'apply_modifiers':False,'_lod_animation_profile':True})
    decoded=Document(path,morphs=True);assert set(decoded.target_names)=={'Up','Wide'}
    assert len(decoded.clips)==1,decoded.report()
    clip=next(iter(decoded.clips));all_indices=[(p,i) for p,(position,j,w) in enumerate(decoded.primitives) for i in range(position.count)]
    rest=decoded.replay(None,0,all_indices,morph_weights=[0,0])['points'];tree=KDTree(len(basis.data))
    for i,v in enumerate(basis.data):tree.insert(C@obj.matrix_world@v.co,i)
    tree.balance();mapping=[]
    for point in rest:
        co,index,distance=tree.find(Vector(point));assert distance<1e-5,(distance,skinned);mapping.append(index)
    errors=[]
    for frame in (1,3,5,7,9):
        bpy.context.scene.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
        try:
            points=decoded.replay(clip,(frame-1)/12,all_indices)['points']
            error=max((Vector(actual)-(C@evaluated.matrix_world@mesh.vertices[index].co)).length for actual,index in zip(points,mapping))
            assert error<1e-5,(skinned,frame,error);errors.append(error)
        finally:evaluated.to_mesh_clear()
    report=inspect_file({'path':str(path),'animation_samples':5,'limit':4,'sample_limit':2})
    assert len(report['samples'])==6 and all(len(s['vertex_samples'])==2 for s in report['samples'])
    (root/(obj.name+'.json')).write_text(json.dumps({'inspection':report,'native_max_errors':errors},indent=2))
print('MORPH_GLB_NATIVE_OK',flush=True)
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'MORPH_GLB_NATIVE_OK' in result.stdout
    if evidence:=os.environ.get('MCPBLENDER_MORPH_GLB_EVIDENCE_DIR'):
        out=Path(evidence);out.mkdir(parents=True,exist_ok=True)
        for name in ('MorphOnly.glb','MorphOnly.json','SkinMorph.glb','SkinMorph.json'):shutil.copy2(tmp_path/name,out/name)
