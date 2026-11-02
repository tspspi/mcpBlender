"""Linear skeletal LODs retaining native deform layers and original rig actions."""
import math
import struct
import hashlib

import bpy

from . import lods,skin_weights
from .assets import require_static
from .retarget import signature as animation_signature
from mcpblender.skin_math import clean_weights

MARKER='mcpblender-skinned-lod-v1'
MOD_FIELDS=('use_vertex_groups','use_bone_envelopes','use_deform_preserve_volume','vertex_group','invert_vertex_group','use_multi_modifier','show_viewport','show_render')


def rest_signature(rig):
    return lods.digest({'rig':rig.name,'data':rig.data.name,'pose_position':rig.data.pose_position,
        'bones':[(b.name,b.parent.name if b.parent else None,lods.matrix(b.matrix_local),b.use_deform,b.use_connect,b.inherit_scale,b.use_inherit_rotation,b.use_local_location,b.bbone_segments,b.use_envelope_multiply) for b in rig.data.bones]})


def weights(obj,rig):
    names={g.index:g.name for g in obj.vertex_groups};deform={b.name for b in rig.data.bones if b.use_deform};h=hashlib.sha256()
    h.update(lods.digest([(g.name,g.lock_weight) for g in obj.vertex_groups]).encode());maximum=0;minimum=math.inf;largest=0;members=0
    for v in obj.data.vertices:
        row={names[g.group]:g.weight for g in v.groups};members+=len(row)
        if members>2000000:raise ValueError('Skin LODs support two million memberships per level')
        if any(not math.isfinite(w) or not 0<=w<=1 for w in row.values()):raise ValueError('Skin LOD weights must be finite in [0,1]')
        for name,value in sorted(row.items()):h.update(name.encode()+b'\0'+struct.pack('!d',value))
        h.update(b'\xff');values=[w for n,w in row.items() if n in deform and w>0];total=sum(values)
        if abs(total-1)>1e-4:raise ValueError('Skin LOD vertices require normalized nonempty deform weights; repair_skin_weights first')
        maximum=max(maximum,len(values));minimum=min(minimum,total);largest=max(largest,total)
    return {'weights_sha256':h.hexdigest(),'max_influences':maximum,'weight_sum_min':minimum,'weight_sum_max':largest,'memberships':members}


def binding(obj,rig):
    mods=list(obj.modifiers)
    if len(mods)!=1 or mods[0].type!='ARMATURE' or mods[0].object!=rig:raise ValueError('Skinned LODs require exactly one armature modifier and no other modifiers')
    mod=mods[0];values={k:getattr(mod,k) for k in MOD_FIELDS}
    if not values['show_viewport'] or not values['show_render'] or not values['use_vertex_groups'] or any(values[k] for k in ('use_bone_envelopes','use_deform_preserve_volume','vertex_group','invert_vertex_group','use_multi_modifier')):
        raise ValueError('Skin LODs require an enabled linear group-only armature binding without envelopes, preserve-volume or mask')
    return values


def frames_for(rig):
    current=bpy.context.scene.frame_current+bpy.context.scene.frame_subframe;anim=rig.animation_data
    ranges=[]
    if anim and anim.action:ranges.append(tuple(anim.action.frame_range))
    if anim:
        ranges.extend((s.frame_start,s.frame_end) for t in anim.nla_tracks if not t.mute for s in t.strips if not s.mute)
    if not ranges:ranges=[(bpy.context.scene.frame_start,bpy.context.scene.frame_end)]
    low,high=min(a for a,b in ranges),max(b for a,b in ranges)
    return sorted({float(current),float(low),float((low+high)/2),float(high)})


def source_snapshot(p):
    obj,rig,mod,rows,deform,locks,coords,relative,settings,weight_signature=skin_weights.inventory({'name':p['name']})
    require_static(obj)
    if obj.data.animation_data:raise ValueError('Mesh-data animation is unsupported for skinned LODs')
    morph=None
    if obj.data.shape_keys:
        from .morph_lods import definition
        morph=definition(obj)
    if len(rig.data.bones)>256 or any(b.bbone_segments!=1 for b in rig.data.bones):raise ValueError('Skin LODs support at most 256 single-segment bones')
    if any(b.use_deform and b.use_envelope_multiply for b in rig.data.bones):raise ValueError('Bone envelope multiplication is unsupported for linear group-only skin LODs')
    if rig.data.animation_data:raise ValueError('Armature-data animation is unsupported for skin LODs')
    if any(not math.isfinite(v) for row in obj.matrix_world for v in row) or abs(obj.matrix_world.determinant())<1e-12:raise ValueError('Finite invertible skin mesh transform required')
    if rig.data.pose_position!='POSE':raise ValueError('Skin LOD pose validation requires rig pose_position=POSE')
    if obj.parent not in (None,rig) or obj.parent and obj.parent_type!='OBJECT':raise ValueError('Skin source must be unparented or object-parented to its rig')
    if not obj.visible_get() or bpy.context.view_layer.objects.get(obj.name)!=obj:raise ValueError('Skin source must be visible in the current view layer')
    values=binding(obj,rig)
    report_weights=weights(obj,rig)
    if report_weights['max_influences']>4:raise ValueError('Skin LOD source supports four deform influences; explicitly prune with repair_skin_weights first')
    if morph:
        from .morph_lods import rest_copy
        mesh=rest_copy(obj)
    else:mesh=obj.data.copy()
    try:
        for i,slot in enumerate(obj.material_slots):
            if slot.link=='OBJECT':mesh.materials[i]=slot.material
        report=lods.summary(mesh);rig_rest=rest_signature(rig);anim=animation_signature(rig)
        layout={'parent':obj.parent.name if obj.parent else None,'parent_inverse':lods.matrix(obj.matrix_parent_inverse),'basis':lods.matrix(obj.matrix_basis)}
        report['skin']={'rig':rig.name,'rest_sha256':rig_rest,'animation_sha256':anim,'weights':report_weights,'binding':values,'root_layout':layout,'recommended_pose_frames':frames_for(rig)}
        report['deformation']='SKINNED'
        if morph:report['morph']=morph
        guard={'name':obj.name,'mesh':report['mesh_sha256'],'weights':weight_signature,'rest':rig_rest,'animation':anim,'layout':layout}
        if morph:
            from .morph_lods import frames_for as morph_frames
            guard['morph']=morph
            report['skin']['recommended_pose_frames']=sorted(set(frames_for(rig)+morph_frames(obj)))
        signature=lods.digest(guard)
        return obj,mesh,report,signature
    except BaseException:bpy.data.meshes.remove(mesh);raise


def setup_root(root,source):
    root.parent=source.parent;root.parent_type='OBJECT';root.rotation_mode=source.rotation_mode
    # Capture the effective basis (including source delta channels) into an
    # independent static root, following the same rig-object parent.
    root.matrix_parent_inverse=source.matrix_parent_inverse.copy();root.matrix_basis=source.matrix_basis.copy()


def setup_groups(obj,source):
    names=list(source.vertex_groups.keys())
    if not obj.vertex_groups:
        for name in names:obj.vertex_groups.new(name=name)
    if list(obj.vertex_groups.keys())!=names:raise ValueError('Native skin group definitions changed')
    for group in obj.vertex_groups:group.lock_weight=source.vertex_groups[group.name].lock_weight


def protect_joints(obj,source,p):
    """Raise native collapse costs near mixed/rapidly changing deform weights."""
    from .bridge import check_cancelled,report_progress
    if not p['skin_joint_importance']:return None
    rig=source.find_armature();deform={b.name for b in rig.data.bones if b.use_deform};names={g.index:g.name for g in obj.vertex_groups}
    rows=[{names[g.group]:g.weight for g in v.groups if names[g.group] in deform and g.weight>0} for v in obj.data.vertices]
    priorities=[min(1,2*sum(w*(1-w) for w in row.values())) for row in rows]
    for edge in obj.data.edges:
        a,b=edge.vertices;difference=sum(abs(rows[a].get(n,0)-rows[b].get(n,0)) for n in rows[a].keys()|rows[b].keys())
        priorities[a]=max(priorities[a],min(1,difference));priorities[b]=max(priorities[b],min(1,difference))
    name='mcp_LOD_joint_importance'
    if name in obj.vertex_groups:raise ValueError('Reserved skin-LOD reduction group already exists')
    group=obj.vertex_groups.new(name=name)
    for i,value in enumerate(priorities):
        if i%128==0:check_cancelled();report_progress({'phase':'protecting LOD joints','vertices':i,'total_vertices':len(priorities)})
        if value:group.add([i],value,'REPLACE')
    return name


def attach(obj,source,report,p,reduced):
    from .bridge import check_cancelled,report_progress
    rig=bpy.data.objects[report['skin']['rig']];deform={b.name for b in rig.data.bones if b.use_deform}
    setup_groups(obj,source)
    if reduced:
        names={g.index:g.name for g in obj.vertex_groups}
        for i,vertex in enumerate(obj.data.vertices):
            if i%128==0:check_cancelled();report_progress({'phase':'normalizing LOD skin weights','object':obj.name,'vertices':i,'total_vertices':len(obj.data.vertices)})
            values={names[g.group]:g.weight for g in vertex.groups if names[g.group] in deform}
            cleaned=clean_weights(values,set(),maximum=p['skin_max_influences'])
            for name in values:obj.vertex_groups[name].remove([i])
            for name,value in cleaned.items():obj.vertex_groups[name].add([i],value,'REPLACE')
    stats=weights(obj,rig)
    if stats['max_influences']>p['skin_max_influences']:raise ValueError('Source/LOD influence limit exceeded; choose a compatible skin_max_influences')
    mod=obj.modifiers.new('LOD_Skin','ARMATURE');mod.object=rig
    for key,value in report['skin']['binding'].items():setattr(mod,key,value)
    mod.show_viewport=False
    return stats


def native_checks(root,objects,meta,issues):
    skin=meta['skin'];rig=bpy.data.objects.get(skin['rig'])
    if not rig or rig.type!='ARMATURE':issues.append('LOD rig is missing');return
    if rest_signature(rig)!=skin['rest_sha256']:issues.append('LOD rig rest definition changed')
    layout=skin['root_layout']
    if (root.parent.name if root.parent else None)!=layout['parent'] or root.parent_type!='OBJECT':issues.append('LOD root rig parent changed')
    for value,key in ((root.matrix_basis,'basis'),(root.matrix_parent_inverse,'parent_inverse')):
        if any(abs(a-b)>1e-6 for ra,rb in zip(value,layout[key]) for a,b in zip(ra,rb)):issues.append('LOD root bind transform changed; move the rig instead')
    for obj,record in zip(objects,meta['levels']):
        try:
            if binding(obj,rig)!=skin['binding']:issues.append('LOD skin binding changed')
            if weights(obj,rig)!=record['skin_weights']:issues.append('LOD skin weights changed')
        except ValueError as e:issues.append(str(e))


def measure(source,objects,frames,count,maximum):
    from .bridge import check_cancelled,report_progress
    scene=bpy.context.scene;saved=(scene.frame_current,scene.frame_subframe)
    visibility=[(o,o.hide_viewport,o.hide_get()) for o in objects];result=[]
    if (len(source.data.vertices)+sum(len(o.data.vertices) for o in objects))*len(frames)>10000000:raise ValueError('Pose validation supports ten million vertex-frame samples')
    try:
        for o,_,_ in visibility:o.hide_viewport=False;o.hide_set(False)
        for index,frame in enumerate(frames):
            check_cancelled();whole=math.floor(frame);scene.frame_set(whole,subframe=frame-whole);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get()
            evaluated=source.evaluated_get(deps);base=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=deps)
            try:
                if len(base.vertices)!=len(source.data.vertices):raise ValueError('Skin source topology changed while sampling')
                if any(not math.isfinite(v) for vertex in base.vertices for v in vertex.co):raise ValueError('Nonfinite source skin deformation')
                levels=[]
                for level,obj in enumerate(objects):
                    check_cancelled();target=obj.evaluated_get(deps);mesh=target.to_mesh(preserve_all_data_layers=True,depsgraph=deps)
                    try:
                        if any(abs(a-b)>1e-5 for ra,rb in zip(evaluated.matrix_world,target.matrix_world) for a,b in zip(ra,rb)):raise ValueError('LOD source/target bind transforms diverged')
                        if len(mesh.vertices)!=len(obj.data.vertices) or any(not math.isfinite(v) for vertex in mesh.vertices for v in vertex.co):raise ValueError('Invalid reduced skin deformation')
                        error=lods.quality(base,mesh,count)
                        if error['max_relative_error']>maximum:raise ValueError(f'LOD posed surface error exceeds max_pose_error: level={level}, frame={frame}, measured={error["max_relative_error"]:.6g}, limit={maximum}')
                        levels.append({'level':level,**error})
                        report_progress({'phase':'verifying LOD skin poses','frame':frame,'level':level,'frames':len(frames),'fraction':(index+(level+1)/len(objects))/len(frames)})
                    finally:target.to_mesh_clear()
                result.append({'frame':frame,'levels':levels})
            finally:evaluated.to_mesh_clear()
        return result
    finally:
        scene.frame_set(saved[0],subframe=saved[1])
        for o,hidden,local in visibility:o.hide_viewport=hidden;o.hide_set(local)
        bpy.context.view_layer.update()


def sample(p):
    _,_,objects,meta,_,_,signature=lods.guarded(p)
    if meta.get('format')!=MARKER:raise ValueError('Pose sampling requires a SKINNED LOD chain')
    source=bpy.data.objects.get(meta['source']);rig=bpy.data.objects[meta['skin']['rig']]
    if source is None:raise ValueError('Source skin unavailable for comparison')
    # Revalidate source policy/binding before evaluating arbitrary modifiers.
    _,mesh,report,_=source_snapshot({'name':source.name})
    bpy.data.meshes.remove(mesh)
    if report['skin']['rig']!=rig.name:raise ValueError('Source skin changed rigs')
    frames=p.get('pose_frames') or frames_for(rig)
    result=measure(source,objects,frames,p['error_samples'],p['max_pose_error'])
    return {'chain':p['chain'],'chain_sha256':signature,'samples':result,'restored_frame':bpy.context.scene.frame_current+bpy.context.scene.frame_subframe,
            'worst_relative_error':max(l['max_relative_error'] for r in result for l in r['levels']),
            'scope':'Current timeline, sampled surfaces only; clips are not switched. External controls/dependencies are not frozen.'}
