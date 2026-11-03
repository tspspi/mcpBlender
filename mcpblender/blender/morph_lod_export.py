"""Owned timeline-baked morph LOD proxies and independently verified GLB bundles."""
import json
import math
from pathlib import Path
import shutil
import struct
import uuid

import bpy
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree

from . import lods,morph_lods,skin_lods
from .domains import curves
from .skin_lod_export import CONVERSION as C,editable_rig
from .workflows import export_objects_glb
from mcpblender.lod_files import MORPH_MARKER,read_glb,file_hash,glb_report,validate
from mcpblender.skin_glb import Document,multiply,point,replay_digest
from mcpblender.storage import require_space


def ranges(p):
    if not p.get('animations',True):
        if p.get('timeline_clips'):raise ValueError('timeline_clips requires animations=true')
        return []
    scene=bpy.context.scene
    clips=p.get('timeline_clips') or [{'name':'Timeline','frame_start':scene.frame_start,'frame_end':scene.frame_end}]
    if len(clips)>32 or len({c['name'] for c in clips})!=len(clips):raise ValueError('Choose at most 32 distinct timeline clips')
    if any(not -1048574<=c['frame_start']<c['frame_end']<=1048574 or c['frame_end']-c['frame_start']>10000 for c in clips):raise ValueError('Timeline clips require 2..10001 integer frames within native limits')
    return clips


def guard(meta,clips):
    source=bpy.data.objects[meta['source']];rig=bpy.data.objects[meta['skin']['rig']] if meta.get('skin') else None
    scene=bpy.context.scene
    return lods.digest({'controller':morph_lods.controller_snapshot(source),'rig':skin_lods.animation_signature(rig) if rig else None,
                        'clips':clips,'fps':scene.render.fps/scene.render.fps_base,'frame':scene.frame_current+scene.frame_subframe})


def preflight(p):
    _,_,objects,meta,records,issues,signature=lods.native_chain(p)
    if not meta.get('morph'):raise ValueError('Morph bundle requires a morph LOD chain')
    if issues:raise ValueError('LOD ownership/content validation failed: '+'; '.join(sorted(set(issues))))
    if bpy.context.mode!='OBJECT':raise ValueError('Object mode required for morph bundle export')
    rig=bpy.data.objects[meta['skin']['rig']] if meta.get('skin') else None
    if rig:editable_rig(rig)
    clips=ranges(p);frames=sum(c['frame_end']-c['frame_start']+1 for c in clips)
    if frames*max(len(o.data.vertices) for o in objects)>10000000:raise ValueError('Morph bake supports ten million vertex-frame samples per level')
    if rig and frames*len(rig.pose.bones)>32768:raise ValueError('Morph bake supports 32768 bone-frame samples per level')
    if frames*(len(objects[0].data.shape_keys.key_blocks)-1)>2000000:raise ValueError('Morph bake supports two million weight keys per level')
    return objects,meta,records,signature,rig,clips


def plan(p):
    _,_,_,meta,_,issues,signature=lods.native_chain(p)
    result={'chain':p['chain'],'chain_sha256':signature,'deformation':'SKINNED' if meta.get('skin') else 'MORPH',
            'export_profile':'BAKED_MORPH_TIMELINE','animations':p.get('animations',True),'can_export':False,'blockers':list(issues),'animation_sha256':None,'clips':[],
            'animation_source':'Current evaluated timeline; requested ranges bake controls, drivers and active NLA without switching authored clips.'}
    try:
        objects,meta,records,signature,rig,clips=preflight(p)
        result.update(can_export=True,animation_sha256=guard(meta,clips),clips=clips,
                      reference_frame=clips[0]['frame_start'] if clips else bpy.context.scene.frame_current+bpy.context.scene.frame_subframe)
    except (ValueError,RuntimeError) as e:result['blockers'].append(str(e))
    return result


def error(a,b):
    values=[abs(x-y) for ra,rb in zip(a,b) for x,y in zip(ra,rb)]
    if not all(math.isfinite(v) for v in values):raise ValueError('Nonfinite baked matrix')
    return max(values)


def object_pose(obj,world,tolerance,previous=None):
    location,rotation,scale=world.decompose()
    if error(Matrix.LocRotScale(location,rotation,scale),world)>tolerance:raise ValueError('Timeline object transform contains unrepresentable shear')
    if previous is not None:rotation.make_compatible(previous)
    obj.location=location;obj.rotation_quaternion=rotation;obj.scale=scale
    return rotation.copy()


class Proxy:
    def __init__(self,obj,rig):
        self.objects=[];self.meshes=[];self.armatures=[];self.keys=[];self.actions=[];self.obj=None;self.rig=None
        try:
            if rig:
                self.rig=rig.copy();self.objects.append(self.rig);self.rig.data=rig.data.copy();self.armatures.append(self.rig.data)
                bpy.context.scene.collection.objects.link(self.rig);self.prepare(self.rig)
                self.rig.data.animation_data_clear()
                for bone in self.rig.pose.bones:
                    for constraint in list(bone.constraints):bone.constraints.remove(constraint)
                    bone.rotation_mode='QUATERNION';bone.matrix_basis=Matrix.Identity(4)
            self.obj=obj.copy();self.objects.append(self.obj);self.obj.data=obj.data.copy();self.meshes.append(self.obj.data)
            if self.obj.data.shape_keys==obj.data.shape_keys:raise ValueError('Native copy did not isolate morph data')
            self.keys.append(self.obj.data.shape_keys.name);bpy.context.scene.collection.objects.link(self.obj);self.prepare(self.obj)
            keys=self.obj.data.shape_keys;keys.animation_data_clear();basis=keys.reference_key
            for block in list(keys.key_blocks)[1:]:
                original=obj.data.shape_keys.key_blocks[block.name]
                for i,v in enumerate(block.data):v.co=basis.data[i].co+original.data[i].co-original.relative_key.data[i].co
                block.relative_key=basis;block.mute=False;block.vertex_group='';block.value=original.value
            if rig:
                self.obj.parent=self.rig;self.obj.matrix_parent_inverse=Matrix.Identity(4)
                self.obj.modifiers[0].object=self.rig
                for group in list(self.obj.vertex_groups):
                    if group.name in rig.data.bones and not rig.data.bones[group.name].use_deform:self.obj.vertex_groups.remove(group)
        except BaseException:self.close();raise
    def prepare(self,obj):
        obj.name='mcp_morph_export_'+uuid.uuid4().hex[:16];obj.animation_data_clear();obj.parent=None
        for constraint in list(obj.constraints):obj.constraints.remove(constraint)
        obj.rotation_mode='QUATERNION';obj.delta_location=(0,0,0);obj.delta_scale=(1,1,1);obj.delta_rotation_euler=(0,0,0);obj.delta_rotation_quaternion=(1,0,0,0)
        obj.hide_viewport=False;obj.hide_render=False;obj.hide_select=False;obj.hide_set(False)
    def close(self):
        for obj in reversed(self.objects):bpy.data.objects.remove(obj,do_unlink=True)
        self.objects.clear()
        for data in self.meshes:bpy.data.meshes.remove(data)
        for name in self.keys:
            key=bpy.data.shape_keys.get(name)
            if key:bpy.data.batch_remove(ids=(key,))
        for data in self.armatures:bpy.data.armatures.remove(data)
        for action in self.actions:bpy.data.actions.remove(action)
        self.meshes.clear();self.keys.clear();self.armatures.clear();self.actions.clear()


def bind_action(owner,action,type,name):
    slot=action.slots.new(type,name);anim=owner.animation_data_create();anim.action=action;anim.action_slot=slot
    anim.use_nla=False;anim.action_blend_type='REPLACE';anim.action_influence=1
    return slot


def native_points(obj):
    deps=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
    try:
        if len(mesh.vertices)!=len(obj.data.vertices):raise ValueError('Timeline bake topology changed')
        points=[evaluated.matrix_world@v.co for v in mesh.vertices]
        if any(not math.isfinite(x) for p in points for x in p):raise ValueError('Nonfinite native deformation')
        return points
    finally:evaluated.to_mesh_clear()


def bake(proxy,obj,rig,clips,reference,tolerance):
    from .bridge import check_cancelled,report_progress
    scene=bpy.context.scene;actions={};proof=[]
    scene.frame_set(reference);bpy.context.view_layer.update()
    ref_mesh=obj.matrix_world.copy();ref_rig=rig.matrix_world.copy() if rig else None
    if rig:
        if abs(ref_rig.determinant())<1e-12:raise ValueError('Invertible reference rig transform required')
        relative=ref_rig.inverted()@ref_mesh;object_pose(proxy.rig,ref_rig,tolerance);proxy.obj.matrix_basis=relative
    else:object_pose(proxy.obj,ref_mesh,tolerance)
    for spec in clips:
        action=bpy.data.actions.new('mcp_morph_clip_'+uuid.uuid4().hex[:16]);proxy.actions.append(action);actions[action.name]=spec['name']
        moving=proxy.rig or proxy.obj;object_slot=bind_action(moving,action,'OBJECT',moving.name)
        key_slot=bind_action(proxy.obj.data.shape_keys,action,'KEY',proxy.obj.name)
        action['mcpblender_morph_targets']=json.dumps({proxy.obj.name:key_slot.identifier})
        if rig:action['mcpblender_target']=proxy.rig.name;action['mcpblender_object_motion']=True
        previous={};maximum=0.;matrix_max=0.
        for frame in range(spec['frame_start'],spec['frame_end']+1):
            check_cancelled();scene.frame_set(frame);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
            if rig:
                evaluated=rig.evaluated_get(deps)
                if error(evaluated.matrix_world.inverted()@obj.matrix_world,relative)>tolerance:raise ValueError('Timeline mesh-to-rig transform changes; stabilize the bind layout before export')
                previous[('OBJECT',None)]=object_pose(proxy.rig,evaluated.matrix_world,tolerance,previous.get(('OBJECT',None)))
                for bone in proxy.rig.pose.bones:
                    source=evaluated.pose.bones[bone.name];kwargs={'parent_matrix':source.parent.matrix,'parent_matrix_local':source.parent.bone.matrix_local} if source.parent else {}
                    basis=bone.bone.convert_local_to_pose(source.matrix,bone.bone.matrix_local,invert=True,**kwargs)
                    if error(Matrix.LocRotScale(*basis.decompose()),basis)>tolerance:raise ValueError('Timeline bone basis contains unrepresentable shear')
                    location,rotation,scale=basis.decompose()
                    if ('BONE',bone.name) in previous:rotation.make_compatible(previous[('BONE',bone.name)])
                    previous[('BONE',bone.name)]=rotation.copy();bone.location=location;bone.rotation_quaternion=rotation;bone.scale=scale
                    for key in ('location','rotation_quaternion','scale'):
                        if not bone.keyframe_insert(key,frame=frame):raise ValueError('Native bone key insertion failed')
            else:previous[('OBJECT',None)]=object_pose(proxy.obj,obj.matrix_world,tolerance,previous.get(('OBJECT',None)))
            for key in ('location','rotation_quaternion','scale'):
                if not moving.keyframe_insert(key,frame=frame):raise ValueError('Native object key insertion failed')
            for block in list(proxy.obj.data.shape_keys.key_blocks)[1:]:
                block.value=obj.data.shape_keys.key_blocks[block.name].value
                if not block.keyframe_insert('value',frame=frame):raise ValueError('Native morph key insertion failed')
            scene.frame_set(frame);bpy.context.view_layer.update()
            actual=native_points(proxy.obj);expected=native_points(obj)
            maximum=max(maximum,max((a-b).length for a,b in zip(actual,expected)))
            if rig:
                deps=bpy.context.evaluated_depsgraph_get();a=rig.evaluated_get(deps);b=proxy.rig.evaluated_get(deps)
                matrix_max=max(matrix_max,max(error(a.matrix_world@bone.matrix,b.matrix_world@b.pose.bones[bone.name].matrix) for bone in a.pose.bones))
            if max(maximum,matrix_max)>tolerance:raise ValueError('Baked proxy differs from native timeline')
            report_progress({'phase':'baking morph timeline','object':obj.name,'clip':spec['name'],'frame':frame,'frame_end':spec['frame_end']})
        for slot in (object_slot,key_slot):
            for curve in curves(action,slot):
                for key in curve.keyframe_points:key.interpolation='LINEAR'
        proof.append({'clip':spec['name'],'native_vertex_error':maximum,'native_joint_matrix_error':matrix_max,'frames':spec['frame_end']-spec['frame_start']+1})
        # Explicit muted stashes preserve both slots for native ACTIONS discovery.
        for owner,slot in ((moving,object_slot),(proxy.obj.data.shape_keys,key_slot)):
            anim=owner.animation_data;track=anim.nla_tracks.new();track.mute=True;strip=track.strips.new(action.name,spec['frame_start'],action);strip.action_slot=slot
    if clips:
        action=proxy.actions[0]
        for owner,kind in ((proxy.rig or proxy.obj,'OBJECT'),(proxy.obj.data.shape_keys,'KEY')):
            owner.animation_data.action=action;owner.animation_data.action_slot=next(s for s in action.slots if s.target_id_type==kind)
    scene.frame_set(reference);bpy.context.view_layer.update()
    return actions,proof,ref_mesh,ref_rig


def rename_file(path,proxy,obj,rig,actions):
    doc,binary=read_glb(path);names={proxy.obj.name:obj.name}
    if rig:names[proxy.rig.name]=rig.name
    for node in doc['nodes']:
        if node.get('name') in names:node['name']=names[node['name']]
    for mesh in doc['meshes']:mesh['name']=obj.name+'Mesh'
    for skin in doc.get('skins',[]):skin['name']=rig.data.name
    for animation in doc.get('animations',[]):
        if animation['name'] not in actions:raise ValueError('Native export produced an unexpected action')
        animation['name']=actions[animation['name']]
    encoded=json.dumps(doc,separators=(',',':'),allow_nan=False).encode();encoded+=b' '*((-len(encoded))%4)
    Path(path).write_bytes(struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary)


def correspondence(obj,rig,document,ref_mesh,ref_rig,tolerance):
    """Match every rest vertex, target delta and optional normalized skin row."""
    from .bridge import check_cancelled
    if set(document.target_names)!={b.name for b in list(obj.data.shape_keys.key_blocks)[1:]}:raise ValueError('Exported morph target names differ from authored keys')
    expected_joints={b.name for b in rig.data.bones} if rig else set()
    if set(document.names)!=expected_joints:raise ValueError('Exported skeleton differs from source')
    expected_defaults=[obj.data.shape_keys.key_blocks[n].value for n in document.target_names]
    if any(abs(a-b)>1e-6 for a,b in zip(expected_defaults,document.default_weights)):raise ValueError('Exported default morph weights differ from reference controller values')
    world=document.world(None,0);mats=[multiply(world[node],inverse) for node,inverse in zip(document.joints,document.inverse)]
    if rig:
        for name,inverse in zip(document.names,document.inverse):
            if error((C@ref_rig@rig.data.bones[name].matrix_local).inverted(),inverse)>tolerance:raise ValueError('Exported inverse binds differ from reference rest skeleton')
    basis=obj.data.shape_keys.reference_key;tree=KDTree(len(basis.data))
    for i,v in enumerate(basis.data):tree.insert(C@ref_mesh@v.co,i)
    tree.balance();selected=set(document.representatives(128));mapping={};maximum=weight_error=0.
    names={g.index:g.name for g in obj.vertex_groups};deform={b.name for b in rig.data.bones if b.use_deform} if rig else set()
    rows=[]
    if rig:
        for vertex in obj.data.vertices:
            row={names[g.group]:g.weight for g in vertex.groups if names[g.group] in deform and g.weight>0};total=sum(row.values());rows.append({n:w/total for n,w in row.items()})
    blocks=[obj.data.shape_keys.key_blocks[n] for n in document.target_names]
    for primitive,index,position,joints,weights in document.vertices():
        if index%128==0:check_cancelled()
        transform=tuple(tuple(sum(w*mats[j][r][c] for j,w in zip(joints,weights)) for c in range(4)) for r in range(4)) if rig else world[document.mesh_node]
        base=Vector(point(transform,position));nearest=tree.find(base)
        if nearest[2]>tolerance:raise ValueError('Exported morph Basis differs from native rest geometry')
        scale=max(abs(v) for v in base);ulp=math.ldexp(1.,math.frexp(scale)[1]-24) if scale else 1e-30
        candidates=tree.find_range(base,nearest[2]+2*ulp)
        if len(candidates)>256:raise ValueError('Morph correspondence exceeds 256 coincident candidates')
        deltas=[]
        for target in document.morph_targets[primitive]:
            delta=target.row(index) if target else (0,0,0)
            deltas.append(Vector(tuple(sum(transform[r][c]*delta[c] for c in range(3)) for r in range(3))))
        exported={}
        for j,w in zip(joints,weights):
            if w:exported[document.names[j]]=exported.get(document.names[j],0)+w
        matches=[]
        for _,i,distance in candidates:
            delta_error=max((actual-(C.to_3x3()@ref_mesh.to_3x3()@(b.data[i].co-b.relative_key.data[i].co))).length for actual,b in zip(deltas,blocks))
            difference=max((abs(rows[i].get(n,0)-exported.get(n,0)) for n in rows[i].keys()|exported.keys()),default=0.) if rig else 0.
            if delta_error<=tolerance and difference<=4e-4:matches.append((delta_error,difference,i))
        if not matches:raise ValueError('Exported morph offsets/skin weights differ from corresponding native vertices')
        delta_error,difference,i=min(matches);maximum=max(maximum,delta_error);weight_error=max(weight_error,difference)
        if (primitive,index) in selected:mapping[primitive,index]=i
    return mapping,maximum,weight_error


def playback(obj,rig,document,clips,reference,p,mapping):
    from .bridge import check_cancelled,report_progress
    scene=bpy.context.scene;fps=scene.render.fps/scene.render.fps_base;indices=document.representatives(128);result=[]
    if set(document.clips)!={c['name'] for c in clips}:raise ValueError('Exported clip inventory differs from requested timeline ranges')
    # Every target has already been compared at every exported vertex. Record
    # independent isolated-target fingerprints too for subsequent file validation.
    for target in range(document.morph_count):
        check_cancelled();weights=[0.]*document.morph_count;weights[target]=1.
        result.append({'clip':None,'time':0.,'morph_weights':weights,'point_limit':128,'points':len(indices),
                       'replay_sha256':replay_digest(document.replay(None,0,indices,morph_weights=weights))})
    result.append({'clip':None,'time':0.,'point_limit':128,'points':len(indices),'replay_sha256':replay_digest(document.replay(None,0,indices))})
    for spec in clips:
        name=spec['name'];channels=document.clips[name];duration=(spec['frame_end']-spec['frame_start'])/fps
        if abs(min(c[2][0] for c in channels))>1e-6 or abs(max(c[2][-1] for c in channels)-duration)>1e-5+duration*1e-7:raise ValueError('Exported morph clip duration differs from requested timeline')
        frames=sorted({round(spec['frame_start']+i*(spec['frame_end']-spec['frame_start'])/(p['animation_samples']-1)) for i in range(p['animation_samples'])})
        for frame in frames:
            check_cancelled();scene.frame_set(frame);bpy.context.view_layer.update();time=struct.unpack('<f',struct.pack('<f',(frame-spec['frame_start'])/fps))[0]
            replay=document.replay(name,time,indices);expected=native_points(obj)
            maximum=max((Vector(actual)-C@expected[mapping[ref]]).length for actual,ref in zip(replay['points'],indices));matrix_max=0.
            if rig:
                evaluated=rig.evaluated_get(bpy.context.evaluated_depsgraph_get())
                matrix_max=max(error(C@evaluated.matrix_world@b.matrix,replay['joints'][b.name]) for b in evaluated.pose.bones)
            if max(maximum,matrix_max)>p['skin_tolerance']:raise ValueError('Decoded morph playback differs from native timeline')
            result.append({'clip':name,'time':time,'native_frame':frame,'point_limit':128,'points':len(indices),'max_vertex_error':maximum,'max_joint_matrix_error':matrix_max,
                           'replay_sha256':replay_digest(replay)})
            report_progress({'phase':'verified decoded morph playback','object':obj.name,'clip':name,'frame':frame})
    return result


def export(p):
    from .bridge import check_cancelled,report_progress,_bridge
    objects,meta,records,signature,rig,clips=preflight(p)
    if signature!=p['expected_chain']:raise ValueError('LOD fingerprint is stale; inspect_lod_chain again')
    animation=guard(meta,clips)
    if p.get('expected_animation') and p['expected_animation']!=animation:raise ValueError('Timeline animation fingerprint is stale; inspect_lod_export again')
    directory=Path(p['directory'])
    if directory.exists() or directory.is_symlink():raise FileExistsError('LOD output directory already exists')
    frame_count=sum(c['frame_end']-c['frame_start']+1 for c in clips);morphs=len(objects[0].data.shape_keys.key_blocks)-1
    estimate=16*1024**2+sum(r['vertices']*(160+morphs*48)+r['triangles']*16 for r in records)+len(objects)*frame_count*(morphs+10*(len(rig.pose.bones)+1 if rig else 1))*64
    images={n.image for o in objects for mat in o.data.materials if mat and mat.node_tree for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
    estimate+=len(objects)*sum(max(1024,i.size[0]*i.size[1]*8) for i in images)
    policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {};require_space(directory,estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='morph_geometry_baked_keys_texture_heuristic')
    scene=bpy.context.scene;saved=(scene.frame_current,scene.frame_subframe);reference=clips[0]['frame_start'] if clips else saved[0]+saved[1]
    visibility=[(o,o.hide_viewport,o.hide_render,o.hide_select,o.hide_get()) for o in [*objects,*([rig] if rig else [])]]
    selected=list(bpy.context.selected_objects);active=bpy.context.view_layer.objects.active
    stage=(p['_export_job'].stage if p.get('_export_job') else directory.parent/('.mcpblender-lod-'+uuid.uuid4().hex));created=False;published=False;levels=[]
    try:
        check_cancelled();stage.mkdir(mode=0o700);created=True
        if p.get('_export_job'):p['_export_job'].created()
        if rig:rig.hide_viewport=False;rig.hide_render=False;rig.hide_select=False;rig.hide_set(False)
        for level,(obj,record) in enumerate(zip(objects,records)):
            check_cancelled();obj.hide_viewport=False;obj.hide_render=False;obj.hide_select=False;obj.hide_set(False)
            scene.frame_set(math.floor(reference),subframe=reference-math.floor(reference));bpy.context.view_layer.update();proxy=Proxy(obj,rig)
            try:
                actions,proof,ref_mesh,ref_rig=bake(proxy,obj,rig,clips,math.floor(reference),p['skin_tolerance'])
                # Bind-only reference may be fractional; no clips are keyed.
                if not clips:
                    scene.frame_set(saved[0],subframe=saved[1]);bpy.context.view_layer.update();ref_mesh=obj.matrix_world.copy();ref_rig=rig.matrix_world.copy() if rig else None
                    if rig:object_pose(proxy.rig,ref_rig,p['skin_tolerance']);proxy.obj.matrix_basis=ref_rig.inverted()@ref_mesh
                    else:object_pose(proxy.obj,ref_mesh,p['skin_tolerance'])
                    for block in list(proxy.obj.data.shape_keys.key_blocks)[1:]:block.value=obj.data.shape_keys.key_blocks[block.name].value
                    bpy.context.view_layer.update()
                path=stage/f'level_{level:02}.glb';report_progress({'phase':'exporting baked morph LOD','level':level,'levels':len(objects)})
                export_objects_glb({'objects':[*([proxy.rig.name] if rig else []),proxy.obj.name],'path':str(path),'animations':bool(clips),'overwrite':False,'apply_modifiers':False,'_lod_animation_profile':True})
                rename_file(path,proxy,obj,rig,actions)
            finally:proxy.close();bpy.context.view_layer.update()
            report=glb_report(path,skinned=True,morphs=True);document=Document(path,morphs=True,check_cancelled=check_cancelled,comparison_unit_scale=bpy.context.scene.unit_settings.scale_length)
            if report['triangles']!=record['triangles']:raise ValueError('Exported morph triangle count differs from native LOD')
            mapping,delta_error,weight_error=correspondence(obj,rig,document,ref_mesh,ref_rig,p['skin_tolerance'])
            samples=playback(obj,rig,document,clips,reference,p,mapping)
            # Checked Basis correspondence supplies native position bounds after
            # glTF's skin-world baking, rather than trusting arbitrary buffer data.
            obj.data.calc_loop_triangles();used={v for t in obj.data.loop_triangles for v in t.vertices};basis=obj.data.shape_keys.reference_key
            positions=[C@ref_mesh@basis.data[i].co for i in used] if rig else [C.to_3x3()@basis.data[i].co for i in used]
            bounds={key:[fn(v[a] for v in positions) for a in range(3)] for key,fn in (('min',min),('max',max))}
            levels.append({'file':path.name,'sha256':file_hash(path),'triangles':record['triangles'],'triangle_budget':record['triangle_budget'],'uv_required':bool(record['uv_maps']),
                           'position_bounds':bounds,'quality':record['quality'],'skin':document.report(),'playback':samples,'timeline_bake':proof,'max_morph_offset_error':delta_error,'max_weight_error':weight_error})
            report_progress({'phase':'verified morph LOD bundle member','level':level,'levels':len(objects),'bytes':path.stat().st_size})
            obj.hide_viewport=visibility[level][1];obj.hide_render=visibility[level][2];obj.hide_select=visibility[level][3];obj.hide_set(visibility[level][4])
        scene.frame_set(saved[0],subframe=saved[1])
        for o,a,b,c,d in visibility:o.hide_viewport=a;o.hide_render=b;o.hide_select=c;o.hide_set(d)
        bpy.context.view_layer.update()
        if lods.native_chain(p)[-1]!=signature or guard(meta,clips)!=animation:raise ValueError('Morph chain or controller changed during export')
        doc={'format':MORPH_MARKER,'chain':p['chain'],'chain_sha256':signature,'source_sha256':meta['source_sha256'],'animation_sha256':animation,
             'blender_version':bpy.app.version_string,'scene_unit_scale':bpy.context.scene.unit_settings.scale_length,'reference_frame':reference,'animation_samples':p['animation_samples'],'skin_tolerance':p['skin_tolerance'],'fps':scene.render.fps/scene.render.fps_base,'clips':clips,'levels':levels,
             'animation_source':'Baked evaluated current timeline, integer frames, linear interpolation; clip seconds start at zero.'}
        (stage/'manifest.json').write_text(json.dumps(doc,indent=2,allow_nan=False)+'\n');verified=validate(stage);check_cancelled()
        if directory.exists() or directory.is_symlink():raise FileExistsError(directory)
        if p.get('_export_job'):p['_export_job'].verify();check_cancelled()
        stage.rename(directory);published=True
        return verified|{'directory':str(directory),'path':str(directory/'manifest.json'),'files':[str(directory/l['file']) for l in levels],'estimated_bytes':estimate}
    finally:
        try:
            scene.frame_set(saved[0],subframe=saved[1])
            for o,a,b,c,d in visibility:o.hide_viewport=a;o.hide_render=b;o.hide_select=c;o.hide_set(d)
            bpy.context.view_layer.update()
            for o in list(bpy.context.selected_objects):o.select_set(False)
            for o in selected:
                if o.name in bpy.context.view_layer.objects:o.select_set(True)
            bpy.context.view_layer.objects.active=active
        finally:
            if created and not published and stage.exists():shutil.rmtree(stage)
