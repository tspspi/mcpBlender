"""Skeletal LOD bundles checked against independent decoded skin playback."""
from pathlib import Path
import json
import math
import struct
import shutil
import uuid

import bpy
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree

from . import lods,rigging,skin_lods
from .domains import curves
from .nla import source as action_record
from .workflows import export_objects_glb
from mcpblender.lod_files import SKIN_MARKER,file_hash,glb_report,validate,read_glb
from mcpblender.skin_glb import Document,replay_digest
from mcpblender.storage import require_space

CONVERSION=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)))


def editable_rig(rig):
    if bpy.context.mode!='OBJECT':raise ValueError('Object mode required for LOD bundle export')
    if rig.library or rig.override_library or rig.data.library or rig.data.override_library:raise ValueError('Validated skin export requires a local non-overridden rig/data copy')


def clips(rig):
    editable_rig(rig);rigging.simple_animation(rig);anim=rig.animation_data
    actions={a for a in bpy.data.actions if a.get('mcpblender_target')==rig.name}
    if anim:
        if anim.action:actions.add(anim.action)
        actions.update(s.action for t in anim.nla_tracks for s in t.strips if s.action)
    if not 1<=len(actions)<=32:raise ValueError('Animated skin bundles require 1..32 compatible clips; choose animations=false for bind-only delivery')
    allowed={k for k in ('location','rotation_euler','rotation_quaternion','scale')}
    allowed.update(b.path_from_id(k) for b in rig.pose.bones for k in ('location','rotation_euler','rotation_quaternion','scale'))
    result={}
    for action in sorted(actions,key=lambda a:a.name):
        if action.library or action.override_library:raise ValueError('Validated animated export requires local non-overridden actions')
        if 'mcpblender_object_motion' in action and not isinstance(action.get('mcpblender_object_motion'),(bool,int,float,str)):raise ValueError('Unsupported object-motion metadata type')
        if anim and anim.action==action:slot=getattr(anim,'action_slot',None)
        else:
            slots=[s for s in getattr(action,'slots',()) if s.target_id_type=='OBJECT'];matches=[s for s in slots if s.name_display==rig.name]
            slot=matches[0] if len(matches)==1 else slots[0] if len(slots)==1 else None
            if slots and slot is None:raise ValueError('Ambiguous action slot in skin bundle')
        channels=list(curves(action,slot))
        if not channels or any(c.data_path not in allowed or c.mute or not c.is_valid for c in channels):raise ValueError('Skin bundle clips require valid object/bone transform channels; bake unsupported controls first')
        low,high=action.frame_range
        if any(not math.isfinite(v) or abs(v)>1048574 or v!=int(v) for v in (low,high)) or not 0<=high-low<=10000:raise ValueError('Skin bundle clips currently require integer frame endpoints and at most 10000 frames')
        record=action_record(action,slot,{})
        result[action.name]=(action,slot,record)
    return result


def animation_guard(rig,choices):
    return lods.digest({'rig':skin_lods.animation_signature(rig),'clips':[action_record(action,slot,{}) for action,slot,_ in choices.values()]})


def plan(p):
    _,_,objects,meta,records,issues,signature=lods.native_chain(p)
    result={'chain':p['chain'],'chain_sha256':signature,'can_export':not issues,'blockers':list(issues),
            'deformation':'SKINNED' if meta.get('skin') else 'MORPH' if meta.get('morph') else 'STATIC','animations':bool(meta.get('skin') and p.get('animations',True)),
            'animation_sha256':None,'clips':[],'reference_frame':bpy.context.scene.frame_current+bpy.context.scene.frame_subframe}
    if bpy.context.mode!='OBJECT':result['blockers'].append('Object mode required for LOD bundle export');result['can_export']=False
    if meta.get('morph'):
        from .morph_lod_export import plan as morph_plan
        return morph_plan(p)
    if p.get('timeline_clips'):result['blockers'].append('timeline_clips is supported by morph-bearing bundles only');result['can_export']=False
    if meta.get('skin') and not issues:
        try:
            rig=bpy.data.objects[meta['skin']['rig']];editable_rig(rig);choices=clips(rig) if p.get('animations',True) else {}
            result['animation_sha256']=animation_guard(rig,choices)
            result['clips']=[{'name':name,'native_frame_start':int(a.frame_range[0]),'native_frame_end':int(a.frame_range[1])} for name,(a,s,record) in choices.items()]
        except (ValueError,RuntimeError) as e:result['blockers'].append(str(e));result['can_export']=False
    return result


def check_native_weights(obj,document,reference_world,tolerance):
    rig=obj.find_armature();deform={b.name for b in rig.data.bones if b.use_deform};names={g.index:g.name for g in obj.vertex_groups}
    tree=KDTree(len(obj.data.vertices))
    for v in obj.data.vertices:tree.insert(reference_world@v.co,v.index)
    tree.balance();rows=[]
    for v in obj.data.vertices:
        row={names[g.group]:g.weight for g in v.groups if names[g.group] in deform and g.weight>0};total=sum(row.values())
        rows.append({n:w/total for n,w in row.items()})
    maximum=0.;mapping={};selected=set(document.representatives(128))
    for primitive,index,position,joints,weights in document.vertices():
        native=Vector((position[0],-position[2],position[1]));nearest=tree.find(native)
        if nearest[2]>tolerance:raise ValueError('Exported positions differ from native reference vertices')
        scale=max(abs(v) for v in native);ulp=math.ldexp(1.,math.frexp(scale)[1]-24) if scale else 1e-30
        candidates=tree.find_range(native,nearest[2]+2*ulp)
        if len(candidates)>256:raise ValueError('Export weight matching exceeds 256 coincident candidates')
        actual={}
        for joint,weight in zip(joints,weights):
            if weight:actual[document.names[joint]]=actual.get(document.names[joint],0)+weight
        matches=[(max(abs(rows[i].get(n,0)-actual.get(n,0)) for n in rows[i].keys()|actual.keys()),i) for _,i,_ in candidates]
        difference,native_index=min(matches,default=(1.,-1))
        if difference>4e-4:raise ValueError('Exported weights differ from native rest weights beyond native tiny-influence filtering tolerance')
        maximum=max(maximum,difference)
        if (primitive,index) in selected:mapping[primitive,index]=native_index
    return maximum,mapping


def export_proxy(obj,rig):
    ignored={b.name for b in rig.data.bones if not b.use_deform}
    if not any(g.name in ignored for g in obj.vertex_groups):return None
    proxy=obj.copy();proxy.data=obj.data.copy()
    try:
        proxy.name='mcp_LOD_export_'+uuid.uuid4().hex[:16];bpy.context.scene.collection.objects.link(proxy)
        proxy.hide_viewport=False;proxy.hide_render=False;proxy.hide_select=False;proxy.hide_set(False)
        for group in list(proxy.vertex_groups):
            if group.name in ignored:proxy.vertex_groups.remove(group)
        bpy.context.view_layer.update();return proxy
    except BaseException:
        mesh=proxy.data;bpy.data.objects.remove(proxy,do_unlink=True);bpy.data.meshes.remove(mesh);raise


def rename_proxy_node(path,name):
    # Restore authored names in the published data without renaming live IDs.
    doc,binary=read_glb(path)
    for node in doc.get('nodes',[]):
        if 'mesh' in node:node['name']=name
    for mesh in doc.get('meshes',[]):mesh['name']=name+'Mesh'
    encoded=json.dumps(doc,separators=(',',':'),allow_nan=False).encode();encoded+=b' '*((-len(encoded))%4)
    Path(path).write_bytes(struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary)


def native_points(obj,indices,rest=False):
    evaluated=None
    if rest:mesh=obj.data;world=obj.matrix_world
    else:
        deps=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=deps);world=evaluated.matrix_world
    try:
        if len(mesh.vertices)!=len(obj.data.vertices):raise ValueError('Native verification topology changed')
        points=[world@mesh.vertices[i].co for i in indices]
        if any(not math.isfinite(v) for p in points for v in p):raise ValueError('Nonfinite native playback')
        return points
    finally:
        if evaluated:evaluated.to_mesh_clear()


def verify(obj,rig,document,choices,baseline,p,reference_world):
    from .bridge import check_cancelled,report_progress
    indices=document.representatives(128);samples=[];fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base;tolerance=p['skin_tolerance']
    if set(document.names)!={b.name for b in rig.data.bones}:raise ValueError('Exported joint names differ from the source skeleton')
    if set(document.clips)!=set(choices):raise ValueError('Exported clip inventory differs from the source rig')
    weight_error,mapping=check_native_weights(obj,document,reference_world,tolerance)
    bind_error=0.
    for name,inverse in zip(document.names,document.inverse):
        expected=(CONVERSION@rig.matrix_world@rig.data.bones[name].matrix_local).inverted()
        bind_error=max(bind_error,max(abs(a-b) for ra,rb in zip(expected,inverse) for a,b in zip(ra,rb)))
    if bind_error>tolerance:raise ValueError('Exported inverse binds differ from the native reference pose')
    requested=[(None,0.,baseline['frame']+baseline['subframe'])]
    for name,channels in document.clips.items():
        action=choices[name][0];start,end=(int(v) for v in action.frame_range)
        expected=(end-start)/fps
        if abs(min(c[2][0] for c in channels))>1e-6 or abs(max(c[2][-1] for c in channels)-expected)>1e-5+expected*1e-7:raise ValueError('Exported clip duration differs from native integer frame range')
        frames=sorted({round(start+i*(end-start)/(p['animation_samples']-1)) for i in range(p['animation_samples'])})
        for frame in frames:
            time=struct.unpack('<f',struct.pack('<f',(frame-start)/fps))[0]
            requested.append((name,time,frame))
    if len(obj.data.vertices)*len(requested)>10000000:raise ValueError('Native skin export checks support ten million vertex-frame samples')
    for index,(name,time,frame) in enumerate(requested):
        check_cancelled();rigging.restore_animation(rig,baseline)
        if name is not None:
            action,slot,_=choices[name];rigging.assign_action(rig,action,slot)
            for key,value in baseline['object_transform'].items():setattr(rig,key,value)
            whole=math.floor(frame);bpy.context.scene.frame_set(whole,subframe=frame-whole);bpy.context.view_layer.update()
        replay=document.replay(name,time,indices)
        maximum=0
        for bone in rig.data.bones:
            native=CONVERSION@rig.matrix_world@(bone.matrix_local if name is None else rig.pose.bones[bone.name].matrix)
            decoded=replay['joints'][bone.name]
            maximum=max(maximum,max(abs(a-b) for ra,rb in zip(native,decoded) for a,b in zip(ra,rb)))
        if maximum>tolerance:raise ValueError(f'Decoded joint playback differs from native rig: clip={name}, frame={frame}, error={maximum}')
        expected_points=native_points(obj,[mapping[i] for i in indices],rest=name is None);error=0.
        for decoded,native in zip(replay['points'],expected_points):
            converted=(decoded[0],-decoded[2],decoded[1]);error=max(error,math.sqrt(sum((a-b)**2 for a,b in zip(converted,native))))
        if error>tolerance:raise ValueError(f'Decoded skin playback differs from corresponding native vertices: clip={name}, frame={frame}, error={error}')
        samples.append({'clip':name,'time':time,'native_frame':frame,'point_limit':128,'points':len(indices),'replay_sha256':replay_digest(replay),
                        'max_joint_matrix_error':maximum,'max_vertex_error':error,'max_weight_error':weight_error,'max_inverse_bind_error':bind_error})
        report_progress({'phase':'verified decoded skin playback','object':obj.name,'clip':name,'frame':frame,'sample':index+1,'samples':len(requested)})
    return samples


def export(p):
    from .bridge import check_cancelled,report_progress,_bridge
    _,_,objects,meta,records,_,signature=lods.guarded(p);rig=bpy.data.objects.get(meta['skin']['rig']);directory=Path(p['directory'])
    if directory.exists() or directory.is_symlink():raise FileExistsError('LOD output directory already exists')
    editable_rig(rig)
    if p.get('animations',True):rigging.simple_animation(rig)
    choices=clips(rig) if p.get('animations',True) else {};anim_guard=animation_guard(rig,choices)
    if p.get('expected_animation') and p['expected_animation']!=anim_guard:raise ValueError('Rig animation fingerprint is stale; inspect_lod_export again')
    estimate=16*1024**2+sum(r['vertices']*160+r['triangles']*16 for r in records)+len(objects)*sum(len(list(curves(a,s)))*int(a.frame_range[1]-a.frame_range[0]+1)*64 for a,s,_ in choices.values())
    images={n.image for obj in objects for mat in obj.data.materials if mat and mat.node_tree for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
    estimate+=len(objects)*sum(max(1024,i.size[0]*i.size[1]*8) for i in images)
    policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {};require_space(directory,estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='skeletal_geometry_keys_texture_heuristic')
    saved=rigging.animation_snapshot(rig);visibility=[(o,o.hide_viewport,o.hide_render,o.hide_select,o.hide_get()) for o in [rig,*objects]]
    stage=(p['_export_job'].stage if p.get('_export_job') else directory.parent/('.mcpblender-lod-'+uuid.uuid4().hex));created=False;published=False;tags=[];levels=[]
    try:
        if abs(rig.matrix_world.determinant())<1e-12:raise ValueError('Choose a reference frame with an invertible rig transform')
        check_cancelled();stage.mkdir(mode=0o700);created=True
        if p.get('_export_job'):p['_export_job'].created()
        rig.hide_viewport=False;rig.hide_render=False;rig.hide_select=False;rig.hide_set(False);bpy.context.view_layer.update()
        for action,slot,_ in choices.values():
            tags.append((action,'mcpblender_object_motion' in action,action.get('mcpblender_object_motion')))
            action['mcpblender_object_motion']=True
        for i,(obj,record) in enumerate(zip(objects,records)):
            check_cancelled();rigging.restore_animation(rig,saved)
            obj.hide_viewport=False;obj.hide_render=False;obj.hide_select=False;obj.hide_set(False);bpy.context.view_layer.update()
            reference_world=obj.matrix_world.copy();obj.data.calc_loop_triangles();used={v for t in obj.data.loop_triangles for v in t.vertices}
            buffer_points=[CONVERSION@reference_world@obj.data.vertices[v].co for v in used]
            buffer_bounds={'min':[min(v[a] for v in buffer_points) for a in range(3)],'max':[max(v[a] for v in buffer_points) for a in range(3)]}
            path=stage/f'level_{i:02}.glb';report_progress({'phase':'exporting skeletal LOD','level':i,'levels':len(objects)})
            proxy=export_proxy(obj,rig)
            try:
                export_objects_glb({'objects':[rig.name,(proxy or obj).name],'path':str(path),'animations':p.get('animations',True),'overwrite':False,'apply_modifiers':False,'_lod_animation_profile':True})
                if proxy:rename_proxy_node(path,obj.name)
            finally:
                if proxy:
                    mesh=proxy.data;bpy.data.objects.remove(proxy,do_unlink=True);bpy.data.meshes.remove(mesh)
                    bpy.context.view_layer.update()
            report=glb_report(path,skinned=True);document=Document(path,comparison_unit_scale=bpy.context.scene.unit_settings.scale_length)
            if report['triangles']!=record['triangles']:raise ValueError('Exported skin triangle count differs from native LOD')
            playback=verify(obj,rig,document,choices,saved,p,reference_world)
            levels.append({'file':path.name,'sha256':file_hash(path),'triangles':record['triangles'],'triangle_budget':record['triangle_budget'],'uv_required':bool(record['uv_maps']),
                           'position_bounds':buffer_bounds,
                           'quality':record['quality'],'skin':document.report(),'playback':playback})
            report_progress({'phase':'exported and verified skeletal LOD','level':i,'levels':len(objects),'bytes':path.stat().st_size,'fraction':(i+1)/len(objects)})
        for action,had,value in tags:
            if had:action['mcpblender_object_motion']=value
            else:del action['mcpblender_object_motion']
        tags.clear();rigging.restore_animation(rig,saved)
        for o,a,b,c,d in visibility:o.hide_viewport=a;o.hide_render=b;o.hide_select=c;o.hide_set(d)
        bpy.context.view_layer.update()
        if lods.native_chain(p)[-1]!=signature or animation_guard(rig,choices)!=anim_guard:raise ValueError('Skin chain or animation changed during export')
        doc={'format':SKIN_MARKER,'chain':p['chain'],'chain_sha256':signature,'source_sha256':meta['source_sha256'],'animation_sha256':anim_guard,
             'blender_version':bpy.app.version_string,'scene_unit_scale':bpy.context.scene.unit_settings.scale_length,'reference_frame':saved['frame']+saved['subframe'],'fps':bpy.context.scene.render.fps/bpy.context.scene.render.fps_base,
             'clips':[{'name':name,'native_frame_start':int(a.frame_range[0]),'native_frame_end':int(a.frame_range[1])} for name,(a,s,record) in choices.items()],
             'levels':levels,'switching':'Separate skeletal representations. Clip seconds start at zero; metadata maps to native frame endpoints.'}
        (stage/'manifest.json').write_text(json.dumps(doc,indent=2,allow_nan=False)+'\n');verified=validate(stage);check_cancelled()
        if directory.exists() or directory.is_symlink():raise FileExistsError(directory)
        if p.get('_export_job'):p['_export_job'].verify();check_cancelled()
        stage.rename(directory);published=True
        return verified|{'directory':str(directory),'path':str(directory/'manifest.json'),'files':[str(directory/l['file']) for l in levels],'estimated_bytes':estimate}
    finally:
        try:
            try:
                for action,had,value in tags:
                    if had:action['mcpblender_object_motion']=value
                    elif 'mcpblender_object_motion' in action:del action['mcpblender_object_motion']
            finally:rigging.restore_animation(rig,saved)
        finally:
            try:
                for o,a,b,c,d in visibility:o.hide_viewport=a;o.hide_render=b;o.hide_select=c;o.hide_set(d)
                bpy.context.view_layer.update()
            finally:
                if created and not published and stage.exists():shutil.rmtree(stage)
