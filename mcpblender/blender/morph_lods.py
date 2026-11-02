"""Relative morph transfer onto reduced rest meshes with source weight controls."""
import math
import bpy
from mathutils import Vector
from mathutils.geometry import barycentric_transform
from mathutils.bvhtree import BVHTree
from . import lods,morphs
from .assets import mesh_object,require_static

MARKER='mcpblender-morph-lod-v1'


def definition(obj):
    keys=obj.data.shape_keys
    if not keys or len(keys.key_blocks)<2:raise ValueError('Morph LODs require relative shape keys including a non-Basis key')
    morphs.validate_target(obj)
    if len(keys.key_blocks)>64 or len(obj.data.vertices)*len(keys.key_blocks)>4000000:raise ValueError('Morph LODs support 64 keys and four million key-vertex entries')
    if obj.show_only_shape_key:raise ValueError('Disable show_only_shape_key before morph LOD transfer')
    blocks=list(keys.key_blocks);records=[]
    for block in blocks:
        if not block.relative_key or block.relative_key not in blocks:raise ValueError('Invalid relative key relationship')
        seen=set();current=block
        while current!=keys.reference_key:
            if current.name in seen:raise ValueError('Relative shape-key dependency cycle')
            seen.add(current.name);current=current.relative_key
        if any(not math.isfinite(v) for point in block.data for v in point.co):raise ValueError('Finite morph coordinates required')
        if block.vertex_group and block.vertex_group not in obj.vertex_groups:raise ValueError('Morph mask group is missing')
        records.append({'name':block.name,'relative':block.relative_key.name,'coordinates':lods.packed(block.data,'co',len(block.data)*3),
                        'mask':block.vertex_group,'slider_min':block.slider_min,'slider_max':block.slider_max,'interpolation':block.interpolation})
    masks={b.vertex_group for b in blocks if b.vertex_group};names={g.index:g.name for g in obj.vertex_groups}
    memberships=[[(names[g.group],g.weight) for g in v.groups if names[g.group] in masks] for v in obj.data.vertices] if masks else []
    return {'controller_snapshot_sha256':controller_snapshot(obj),'source_keys':keys.name,'keys':records,'mask_sha256':lods.digest(memberships),
            'definition_sha256':lods.digest({'keys':records,'masks':memberships}),'control':'Original Key datablock values and mutes; source actions/drivers/NLA remain authoritative.'}


def rest_copy(obj):
    # Mesh.copy also copies Key animation. Clear only the owned copy through a
    # temporary unlinked object; never clear or switch the original controller.
    mesh=obj.data.copy();temp=None;owned_name=None
    try:
        if mesh.shape_keys==obj.data.shape_keys:raise ValueError('Native mesh copy did not isolate its shape-key data')
        owned_name=mesh.shape_keys.name if mesh.shape_keys else None
        temp=bpy.data.objects.new('mcp_LOD_rest_copy',mesh)
        if mesh.shape_keys:
            temp.shape_key_clear()
            if mesh.shape_keys:raise ValueError('Native morph basis copy could not clear owned shape keys')
            owned=bpy.data.shape_keys.get(owned_name)
            if owned:bpy.data.batch_remove(ids=(owned,))
        basis=obj.data.shape_keys.reference_key
        for v,p in zip(mesh.vertices,basis.data):v.co=p.co
        mesh.update();return mesh
    except BaseException:
        if temp:bpy.data.objects.remove(temp);temp=None
        bpy.data.meshes.remove(mesh)
        owned=bpy.data.shape_keys.get(owned_name) if owned_name else None
        if owned:bpy.data.batch_remove(ids=(owned,))
        raise
    finally:
        if temp and temp.name in bpy.data.objects:bpy.data.objects.remove(temp)


def source_snapshot(p):
    obj=mesh_object(p['name']);require_static(obj)
    if obj.modifiers or obj.find_armature() or obj.data.animation_data:raise ValueError('MORPH mode requires raw mesh geometry without modifiers/data animation; use SKINNED for a linear rig')
    if not obj.visible_get() or bpy.context.view_layer.objects.get(obj.name)!=obj:raise ValueError('Morph source must be visible in the current view layer')
    if any(not math.isfinite(v) for row in obj.matrix_world for v in row) or abs(obj.matrix_world.determinant())<1e-12:raise ValueError('Finite invertible morph source transform required')
    info=definition(obj);mesh=rest_copy(obj)
    try:
        for i,slot in enumerate(obj.material_slots):
            if slot.link=='OBJECT':mesh.materials[i]=slot.material
        report=lods.summary(mesh);report['morph']=info;report['deformation']='MORPH'
        return obj,mesh,report,lods.digest({'name':obj.name,'matrix':lods.matrix(obj.matrix_world),'mesh':report['mesh_sha256'],'morph':info})
    except BaseException:bpy.data.meshes.remove(mesh);raise


def shape_signature(obj):
    from .animation_curves import channel_info
    keys=obj.data.shape_keys
    if not keys:return None
    anim=keys.animation_data
    drivers=[]
    if anim:
        for curve in anim.drivers:
            d=curve.driver
            drivers.append({'curve':channel_info(curve),'path':curve.data_path,'index':curve.array_index,'mute':curve.mute,'modifiers':[m.type for m in curve.modifiers],'use_self':d.use_self,'type':d.type,'expression':d.expression,
                            'variables':[(v.name,v.type,[(t.id_type,t.id.name if t.id else None,t.data_path) for t in v.targets]) for v in d.variables]})
    return lods.digest({'keys':[(b.name,b.relative_key.name,b.vertex_group,b.mute,b.slider_min,b.slider_max,b.interpolation,lods.packed(b.data,'co',len(b.data)*3)) for b in keys.key_blocks],
                        'relative':keys.use_relative,'solo':obj.show_only_shape_key,'drivers':drivers,
                        'action':anim.action.name if anim and anim.action else None,'tracks':len(anim.nla_tracks) if anim else 0})


def attach(obj,source,exact):
    from .bridge import check_cancelled,report_progress
    keys=source.data.shape_keys;blocks=list(keys.key_blocks);basis=keys.reference_key
    mapping_mesh=rest_copy(source)
    try:
        mapping_mesh.calc_loop_triangles();triangles=[tuple(t.vertices) for t in mapping_mesh.loop_triangles]
    finally:bpy.data.meshes.remove(mapping_mesh)
    coords=[p.co.copy() for p in basis.data]
    tree=BVHTree.FromPolygons(coords,triangles,all_triangles=True);mapping=[];max_projection=0.
    for index,v in enumerate(obj.data.vertices):
        if index%128==0:check_cancelled();report_progress({'phase':'mapping LOD morphs','object':obj.name,'vertices':index,'total_vertices':len(obj.data.vertices)})
        if exact:mapping.append(((index,), (1.,)));continue
        location,normal,face,distance=tree.find_nearest(v.co)
        if face is None:raise ValueError('No source triangle for morph transfer')
        a,b,c=triangles[face];weights=barycentric_transform(location,coords[a],coords[b],coords[c],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        if not all(math.isfinite(w) and -.0001<=w<=1.0001 for w in weights):raise ValueError('Degenerate morph mapping triangle')
        total=sum(max(0,w) for w in weights)
        if total<=1e-12:raise ValueError('Degenerate morph mapping weights')
        mapping.append(((a,b,c),tuple(max(0,w)/total for w in weights)));max_projection=max(max_projection,distance)
    base=obj.shape_key_add(name=basis.name,from_mix=False);base.interpolation=basis.interpolation
    converted={basis.name:base};names={g.name:g.index for g in source.vertex_groups}
    masks={}
    for block in blocks[1:]:
        if block.vertex_group and block.vertex_group not in masks:
            group=names[block.vertex_group];masks[block.vertex_group]=[next((g.weight for g in v.groups if g.group==group),0.) for v in source.data.vertices]
    pending=blocks[1:]
    while pending:
        ready=[b for b in pending if b.relative_key.name in converted]
        if not ready:raise ValueError('Relative shape-key dependency cycle')
        for block in ready:
            check_cancelled();out=obj.shape_key_add(name=block.name,from_mix=False);parent=converted[block.relative_key.name]
            out.relative_key=parent;out.slider_min=block.slider_min;out.slider_max=block.slider_max;out.interpolation=block.interpolation
            mask=masks.get(block.vertex_group)
            for index,(indices,weights) in enumerate(mapping):
                if index%512==0:check_cancelled()
                delta=Vector((0,0,0))
                for i,w in zip(indices,weights):delta+=(block.data[i].co-block.relative_key.data[i].co)*(w*(mask[i] if mask is not None else 1))
                out.data[index].co=parent.data[index].co+delta
            converted[block.name]=out
            driver=out.driver_add('value').driver;driver.type='SCRIPTED';driver.expression='weight * (1 - muted)'
            for name,prop in (('weight','value'),('muted','mute')):
                var=driver.variables.new();var.name=name;var.type='SINGLE_PROP';target=var.targets[0];target.id_type='KEY';target.id=keys;target.data_path=block.path_from_id(prop)
            pending=[b for b in pending if b!=block]
            report_progress({'phase':'transferred LOD morph','object':obj.name,'key':block.name,'keys':len(blocks)-1})
    # Reordering is deliberate only when a relative parent occurs later in the
    # source. Names and dependencies, rather than numeric indices, are the contract.
    obj.data.shape_keys['mcpblender_topology']=morphs.topology_digest(obj.data)
    obj.data.update();bpy.context.view_layer.update()
    return {'definition_sha256':shape_signature(obj),'keys':len(blocks),'max_projection_distance':max_projection,'masks':'Baked into interpolated relative deltas','weights':'Follow original Key values/mutes through explicit local drivers'}


def native_checks(objects,meta,issues):
    source=bpy.data.objects.get(meta['source']);info=meta['morph']
    if source is None or not source.data or not source.data.shape_keys:issues.append('Morph source controller is missing')
    else:
        try:
            current=definition(source)
            if current['source_keys']!=info['source_keys'] or current['definition_sha256']!=info['definition_sha256']:issues.append('Source morph definition/masks changed; regenerate the chain')
        except ValueError as e:issues.append(str(e))
    for obj,record in zip(objects,meta['levels']):
        if shape_signature(obj)!=record['morph_transfer']['definition_sha256']:issues.append('LOD morph data or controller links changed')


def frames_for(source):
    anim=source.data.shape_keys.animation_data;scene=bpy.context.scene
    ranges=[tuple(anim.action.frame_range)] if anim and anim.action else []
    if anim:ranges.extend((s.frame_start,s.frame_end) for t in anim.nla_tracks if not t.mute for s in t.strips if not s.mute)
    if not ranges:ranges=[(scene.frame_start,scene.frame_end)]
    low,high=min(a for a,b in ranges),max(b for a,b in ranges)
    return sorted({float(scene.frame_current+scene.frame_subframe),float(low),float((low+high)/2),float(high)})


def sample(p):
    from .skin_lods import measure
    _,_,objects,meta,_,_,signature=lods.guarded(p)
    if not meta.get('morph'):raise ValueError('Morph sampling requires a morph LOD chain')
    source=bpy.data.objects.get(meta['source'])
    if source is None:raise ValueError('Morph source controller unavailable')
    _,mesh,report,_=lods.source_snapshot({'name':source.name,'deformation':'SKINNED' if meta.get('skin') else 'MORPH'})
    bpy.data.meshes.remove(mesh)
    result=measure(source,objects,p.get('pose_frames') or (report['skin']['recommended_pose_frames'] if meta.get('skin') else frames_for(source)),p['error_samples'],p['max_pose_error'])
    return {'chain':p['chain'],'chain_sha256':signature,'samples':result,'restored_frame':bpy.context.scene.frame_current+bpy.context.scene.frame_subframe,
            'worst_relative_error':max(l['max_relative_error'] for r in result for l in r['levels']),
            'scope':'Current source-controller timeline, sampled surfaces; source actions/drivers/NLA stay authoritative, no clips switched.'}


def measure_keys(source,obj,p):
    """Check every relative delta at unit weight independently of live controls."""
    from .bridge import check_cancelled,report_progress
    base=rest_copy(source);target=None;result=[]
    try:
        target=rest_copy(obj);keys=source.data.shape_keys;out=obj.data.shape_keys
        source_basis=[v.co.copy() for v in base.vertices];target_basis=[v.co.copy() for v in target.vertices]
        for block in list(keys.key_blocks)[1:]:
            check_cancelled();mask=source.vertex_groups.get(block.vertex_group) if block.vertex_group else None
            for i,v in enumerate(base.vertices):
                weight=next((g.weight for g in source.data.vertices[i].groups if g.group==mask.index),0.) if mask else 1.
                v.co=source_basis[i]+(block.data[i].co-block.relative_key.data[i].co)*weight
            shape=out.key_blocks[block.name]
            for i,v in enumerate(target.vertices):v.co=target_basis[i]+shape.data[i].co-shape.relative_key.data[i].co
            base.update();target.update();error=lods.quality(base,target,p['error_samples'])
            if error['max_relative_error']>p['max_pose_error']:raise ValueError('LOD isolated morph error exceeds max_pose_error: '+block.name)
            result.append({'key':block.name,**error});report_progress({'phase':'verifying isolated LOD morphs','object':obj.name,'key':block.name})
        return result
    finally:
        if target:bpy.data.meshes.remove(target)
        bpy.data.meshes.remove(base)


def controller_snapshot(obj):
    from .nla import source,strip_record
    keys=obj.data.shape_keys;anim=keys.animation_data;cache={}
    return lods.digest({'values':[(b.name,b.value,b.mute) for b in keys.key_blocks],
                        'definition':shape_signature(obj),
                        'action':source(anim.action,getattr(anim,'action_slot',None),cache) if anim else None,
                        'settings':{k:getattr(anim,k) for k in ('action_blend_type','action_extrapolation','action_influence','use_nla','use_tweak_mode')} if anim else {},
                        'tracks':[(t.name,t.mute,t.is_solo,[strip_record(s,cache) for s in t.strips]) for t in anim.nla_tracks] if anim else []})
