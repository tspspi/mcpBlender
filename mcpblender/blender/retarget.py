"""Rest-aware visual retargeting, without altering either input rig."""
from array import array
import hashlib
import json
import math
import statistics

import bpy
from mathutils import Euler,Matrix,Vector

from .rigging import armature_object
from .assets import mesh_object
from .constraints import descriptor

COMMANDS={'inspect_animation_retarget','retarget_animation'}


def rows(matrix):return [list(r) for r in matrix]
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()
def correction(degrees):return Euler([math.radians(v) for v in degrees],'XYZ').to_quaternion()


def signature(rig):
    from .nla import inspect as nla
    from .drivers import inspect as drivers
    if len(rig.pose.bones)>256:raise ValueError('Retargeting supports up to 256 bones per rig')
    return digest({'name':rig.name,'data':rig.data.name,'parent':rig.parent.name if rig.parent else None,
                   'parent_type':rig.parent_type,'parent_bone':rig.parent_bone,'parent_inverse':rows(rig.matrix_parent_inverse),
                   'pose_position':rig.data.pose_position,'ik_solver':rig.pose.ik_solver,'rotation_mode':rig.rotation_mode,
                   'bones':[{'name':b.name,'parent':b.parent.name if b.parent else None,'rest':rows(b.bone.matrix_local),
                             'length':b.bone.length,'connected':b.bone.use_connect,'deform':b.bone.use_deform,
                             'inherit_scale':b.bone.inherit_scale,'inherit_rotation':b.bone.use_inherit_rotation,
                             'local_location':b.bone.use_local_location,'segments':b.bone.bbone_segments,
                             'rotation_mode':b.rotation_mode,'constraints':[descriptor(c) for c in b.constraints]} for b in rig.pose.bones],
                   'constraints':[descriptor(c) for c in rig.constraints],
                   'nla':nla({'name':rig.name})['nla_sha256'],'drivers':drivers({'name':rig.name})['drivers_sha256']})


def mapped_roots(rig,mappings):
    names={m['target'] for m in mappings};result=set()
    for name in names:
        parent=rig.data.bones[name].parent
        while parent and parent.name not in names:parent=parent.parent
        if parent is None:result.add(name)
    return result


def validate_mapping(source,target,mappings):
    for m in mappings:
        if m['source'] not in source.pose.bones or m['target'] not in target.pose.bones:raise ValueError('Mapped source/target bone not found')
    if not len(source.pose.bones) or not len(target.pose.bones):raise ValueError('Nonempty armatures required')


def rig_inputs(p):
    source=armature_object(p['source']);target=armature_object(p['name'])
    if any(r.name not in bpy.context.scene.objects for r in (source,target)):raise ValueError('Retarget inputs must belong to the current scene')
    return source,target


def inspect(p):
    source,target=rig_inputs(p);mappings=p.get('mappings',[])
    validate_mapping(source,target,mappings)
    ratios=[target.data.bones[m['target']].length/source.data.bones[m['source']].length for m in mappings]
    roots=mapped_roots(target,mappings)
    forward={m['source']:m['target'] for m in mappings};mapped_targets=set(forward.values());hierarchy=[]
    for m in mappings:
        sp=source.data.bones[m['source']].parent;tp=target.data.bones[m['target']].parent
        skipped=[]
        while sp and sp.name not in forward:skipped.append(sp.name);sp=sp.parent
        while tp and tp.name not in mapped_targets:tp=tp.parent
        if skipped or (forward.get(sp.name) if sp else None)!=(tp.name if tp else None):
            hierarchy.append({'source':m['source'],'target':m['target'],'unmapped_source_ancestors':skipped,
                              'source_mapped_parent':sp.name if sp else None,'target_mapped_parent':tp.name if tp else None})
    return {'source':source.name,'name':target.name,'source_rig_sha256':signature(source),'target_rig_sha256':signature(target),
            'source_bones':len(source.pose.bones),'target_bones':len(target.pose.bones),
            'exact_name_suggestions':[{'source':b.name,'target':b.name} for b in source.data.bones if b.name in target.data.bones],
            'unmapped_source':[b.name for b in source.data.bones if b.name not in {m['source'] for m in mappings}],
            'unmapped_target':[b.name for b in target.data.bones if b.name not in {m['target'] for m in mappings}],
            'hierarchy_warnings':hierarchy,'connected_translation_roots':[n for n in roots if target.data.bones[n].use_connect],
            'translation_roots':sorted(roots),'translation_scale':p.get('translation_scale') or (statistics.median(ratios) if ratios else None),
            'rotation_mode':p['rotation_mode'],'object_motion':p['object_motion'],
            'mappings':[m|{'length_ratio':ratios[i],'source_rest':rows(source.data.bones[m['source']].matrix_local),
                           'target_rest':rows(target.data.bones[m['target']].matrix_local),
                           'source_parent':source.data.bones[m['source']].parent.name if source.data.bones[m['source']].parent else None,
                           'target_parent':target.data.bones[m['target']].parent.name if target.data.bones[m['target']].parent else None,
                           'target_connected':target.data.bones[m['target']].use_connect} for i,m in enumerate(mappings)],
            'note':'Mappings are explicit; path/name similarity does not establish anatomical equivalence or foot contact. Current external control dependencies are not frozen by the rig fingerprints.'}


def set_frame(frame):
    whole=math.floor(frame);bpy.context.scene.frame_set(whole,subframe=frame-whole);bpy.context.view_layer.update()


def matrix_error(a,b):
    values=[abs(x-y) for ra,rb in zip(a,b) for x,y in zip(ra,rb)]
    if not all(math.isfinite(x) for x in values):raise ValueError('Non-finite retarget matrix')
    return max(values)


def parent_args(bone,computed):
    return {'parent_matrix':computed[bone.parent.name],'parent_matrix_local':bone.parent.matrix_local} if bone.parent else {}


def source_basis(bone):
    kwargs={'parent_matrix':bone.parent.matrix,'parent_matrix_local':bone.parent.bone.matrix_local} if bone.parent else {}
    return bone.bone.convert_local_to_pose(bone.matrix,bone.bone.matrix_local,invert=True,**kwargs)


def desired_pose(source,target,p,scale,roots):
    mapping={m['target']:m for m in p['mappings']};alignment=correction(p['alignment_degrees']);result={};ignored=set()
    def depth(b):
        n=0
        while b.parent:n+=1;b=b.parent
        return n
    for bone in sorted(target.data.bones,key=depth):
        args=parent_args(bone,result);basis=Matrix.Identity(4)
        if bone.name in mapping:
            m=mapping[bone.name];sb=source.pose.bones[m['source']];sm=source_basis(sb);loc,rot,stretch=sm.decompose()
            if any(not math.isfinite(v) or v<=1e-8 for v in stretch):raise ValueError('Retargeting requires finite positive source pose scales')
            if any(abs(v-1)>1e-5 for v in stretch) and p['scale_mode']=='IGNORE':ignored.add(sb.name)
            transfer_location=p['translation']=='ALL' or (p['translation']=='ROOT' and bone.name in roots)
            adjust=correction(m['rotation_correction_degrees'])
            if p['rotation_mode']=='LOCAL_POSE':
                rotation=adjust@rot@adjust.inverted();location=adjust@loc*scale if transfer_location else Vector((0,0,0))
                basis=Matrix.LocRotScale(location,rotation,stretch if p['scale_mode']=='COPY_LOCAL' else Vector((1,1,1)))
                pose=bone.convert_local_to_pose(basis,bone.matrix_local,**args)
            else:
                sr=sb.bone.matrix_local.to_quaternion();tr=bone.matrix_local.to_quaternion()
                delta=sb.matrix.to_quaternion()@sr.inverted();mapped=alignment@delta@alignment.inverted()
                global_adjust=tr@adjust@tr.inverted();mapped=global_adjust@mapped@global_adjust.inverted()
                rest_pose=bone.convert_local_to_pose(basis,bone.matrix_local,**args);head=rest_pose.translation.copy()
                if transfer_location:
                    if bone.name in roots:
                        displacement=sb.matrix.translation-sb.bone.matrix_local.translation
                        head=bone.matrix_local.translation+(alignment@displacement)*scale
                    else:
                        without_location=sm.copy();without_location.translation=Vector((0,0,0))
                        skwargs={'parent_matrix':sb.parent.matrix,'parent_matrix_local':sb.parent.bone.matrix_local} if sb.parent else {}
                        untranslated=sb.bone.convert_local_to_pose(without_location,sb.bone.matrix_local,**skwargs)
                        head+=(alignment@(sb.matrix.translation-untranslated.translation))*scale
                inherited=rest_pose.to_scale()
                if p['scale_mode']=='COPY_LOCAL':inherited=Vector([a*b for a,b in zip(inherited,stretch)])
                pose=Matrix.LocRotScale(head,mapped@tr,inherited)
            result[bone.name]=pose
        else:result[bone.name]=bone.convert_local_to_pose(basis,bone.matrix_local,**args)
        matrix_error(result[bone.name],result[bone.name])
    return result,ignored


def object_pose(source_world,source_ref,target_ref,p,scale):
    if p['object_motion']=='IGNORE':return target_ref.copy()
    delta=source_ref.inverted()@source_world;location,rotation,stretch=delta.decompose()
    rigid=Matrix.LocRotScale(location,rotation,Vector((1,1,1)))
    if matrix_error(delta,rigid)>1e-5:raise ValueError('Object motion must have rigid translation/rotation relative to reference; animated scale/shear is unsupported')
    a=correction(p['alignment_degrees']).to_matrix().to_4x4();mapped=a@rigid@a.inverted();mapped.translation*=scale
    return target_ref@mapped


def skin_sample(mesh,deps,budget):
    evaluated=mesh.evaluated_get(deps);data=None
    try:
        data=evaluated.to_mesh()
        if len(data.vertices)>budget:raise ValueError('Evaluated skin verification exceeded ten million vertex-frame samples')
        coordinates=array('f',[0])* (len(data.vertices)*3);data.vertices.foreach_get('co',coordinates)
        h=hashlib.sha256(coordinates.tobytes());h.update(json.dumps(rows(evaluated.matrix_world)).encode())
        low=[math.inf]*3;high=[-math.inf]*3
        for vertex in data.vertices:
            point=evaluated.matrix_world@vertex.co
            if not all(math.isfinite(v) for v in point):raise ValueError('Non-finite retargeted skin deformation')
            for i,v in enumerate(point):low[i]=min(low[i],v);high[i]=max(high[i],v)
        return {'name':mesh.name,'vertices':len(data.vertices),'geometry_sha256':h.hexdigest(),
                'world_bounds':{'min':low if data.vertices else None,'max':high if data.vertices else None}}
    finally:
        if data is not None:evaluated.to_mesh_clear()


def retarget(p):
    from .bridge import check_cancelled,report_progress
    from .domains import curves
    source,target=rig_inputs(p);validate_mapping(source,target,p['mappings'])
    if signature(source)!=p['expected_source_rig'] or signature(target)!=p['expected_target_rig']:raise ValueError('Rig fingerprint is stale; inspect_animation_retarget again')
    count=p['frame_end']-p['frame_start']+1
    if len(target.pose.bones)*count>32768:raise ValueError('Retargeting supports 32768 target bone-frame samples')
    if source.data.pose_position!='POSE' or any(b.bbone_segments!=1 for rig in (source,target) for b in rig.data.bones):raise ValueError('Retargeting requires evaluated source pose and single-segment bones')
    meshes=[mesh_object(m['source']) for m in p['meshes']]
    if sum(len(m.data.vertices) for m in meshes)*count>10000000:raise ValueError('Skin verification supports ten million vertex-frame samples')
    outputs=[p['output_rig']]+[m['output'] for m in p['meshes']]
    if any(len(n.encode())>63 or n in bpy.data.objects for n in outputs) or len(p['clip'].encode())>63 or p['clip'] in bpy.data.actions:raise ValueError('Output object/clip names must be unused and fit 63 UTF-8 bytes')
    scene_objects=bpy.context.scene.objects
    surface={'ARMATURE','BEVEL','SUBSURF','WEIGHTED_NORMAL','TRIANGULATE','SOLIDIFY','DECIMATE'}
    for mesh in meshes:
        mods=[m for m in mesh.modifiers if m.type=='ARMATURE']
        if (mesh.name not in scene_objects or len(mods)!=1 or mods[0].object!=target or not mods[0].show_viewport or not mods[0].show_render
                or any(m.type not in surface for m in mesh.modifiers) or mesh.animation_data or mesh.data.animation_data or mesh.constraints
                or mesh.parent not in (None,target) or (mesh.parent and mesh.parent_type!='OBJECT')):
            raise ValueError('Target skins require one enabled target-armature modifier, static local objects, supported surface modifiers and no external/bone parent')
        if mesh.data.shape_keys:
            from .morphs import validate_target
            validate_target(mesh)
    scale=p.get('translation_scale') or statistics.median(target.data.bones[m['target']].length/source.data.bones[m['source']].length for m in p['mappings'])
    if not math.isfinite(scale) or not 0<scale<=1e12:raise ValueError('Automatic translation scale is outside (0,1e12]; choose an explicit valid scale')
    roots=mapped_roots(target,p['mappings']);scene=bpy.context.scene;saved=(scene.frame_current,scene.frame_subframe)
    created=[];blocks=[];action=None;success=False;samples=[];ignored=set();max_error=0.0
    source_start=p.get('source_start',p['frame_start']);reference=p.get('reference_frame',source_start)
    try:
        check_cancelled();set_frame(reference);deps=bpy.context.evaluated_depsgraph_get()
        source_ref=source.evaluated_get(deps).matrix_world.copy();target_ref=target.evaluated_get(deps).matrix_world.copy()
        try:
            for reference_matrix in ((source_ref,target_ref) if p['object_motion']=='COPY' else (target_ref,)):
                inverse=reference_matrix.inverted();matrix_error(inverse,inverse)
        except ValueError as exc:raise ValueError('Reference object matrices must have finite native inverses') from exc
        output=target.copy();created.append(output);output.data=target.data.copy();blocks.append(output.data)
        output.name=p['output_rig'];scene.collection.objects.link(output);output.animation_data_clear();output.data.animation_data_clear();output.data.pose_position='POSE'
        output.parent=None;output.rotation_mode='QUATERNION';output.matrix_world=target_ref
        for k in ('mcpblender_drivers','mcpblender_nla','mcpblender_nla_zero_base'):
            if k in output:del output[k]
        for c in list(output.constraints):output.constraints.remove(c)
        for bone in output.pose.bones:
            for c in list(bone.constraints):bone.constraints.remove(c)
            bone.rotation_mode='QUATERNION';bone.matrix_basis=Matrix.Identity(4)
        skins=[]
        for original,spec in zip(meshes,p['meshes']):
            check_cancelled();duplicate=original.copy();created.append(duplicate);duplicate.data=original.data.copy();blocks.append(duplicate.data)
            if duplicate.data.shape_keys:
                if duplicate.data.shape_keys==original.data.shape_keys:raise ValueError('Independent copied shape-key data required')
            duplicate.name=spec['output'];scene.collection.objects.link(duplicate);duplicate.parent=output;duplicate.parent_type='OBJECT';duplicate.matrix_world=original.matrix_world
            for mod in duplicate.modifiers:
                if mod.type=='ARMATURE':mod.object=output
            if duplicate.data.shape_keys:
                weights={b.name:b.value for b in original.data.shape_keys.key_blocks};duplicate.data.shape_keys.animation_data_clear()
                for b in duplicate.data.shape_keys.key_blocks:b.value=weights[b.name]
                for key in ('mcpblender_drivers','mcpblender_nla','mcpblender_nla_zero_base'):
                    if key in duplicate.data.shape_keys:del duplicate.data.shape_keys[key]
            skins.append(duplicate)
        action=bpy.data.actions.new(p['clip']);action.use_fake_user=True;action['mcpblender_target']=output.name
        action['mcpblender_retarget_source']=source.name;action['mcpblender_retarget_target']=target.name;action['mcpblender_object_motion']=p['object_motion']=='COPY'
        output.animation_data_create().action=action;slot=action.slots.new(id_type='OBJECT',name=output.name) if hasattr(action,'slots') else None
        if slot is not None:output.animation_data.action_slot=slot
        previous={};previous_object=None;vertex_budget=10000000
        for index,frame in enumerate(range(p['frame_start'],p['frame_end']+1)):
            check_cancelled();sf=source_start+(frame-p['frame_start'])*p['playback_speed'];set_frame(sf)
            evaluated=source.evaluated_get(bpy.context.evaluated_depsgraph_get());poses,stretch_ignored=desired_pose(evaluated,output,p,scale,roots);ignored.update(stretch_ignored)
            world=object_pose(evaluated.matrix_world,source_ref,target_ref,p,scale);location,rotation,stretch=world.decompose()
            if previous_object:rotation.make_compatible(previous_object)
            previous_object=rotation.copy();output.location=location;output.rotation_quaternion=rotation;output.scale=stretch
            if p['object_motion']=='COPY':
                for prop in ('location','rotation_quaternion','scale'):
                    if not output.keyframe_insert(data_path=prop,frame=frame):raise RuntimeError('Blender refused an object-motion key')
            for bone in output.pose.bones:
                basis=bone.bone.convert_local_to_pose(poses[bone.name],bone.bone.matrix_local,invert=True,**parent_args(bone.bone,poses))
                loc,rot,stretch=basis.decompose()
                if bone.name in previous:rot.make_compatible(previous[bone.name])
                previous[bone.name]=rot.copy();bone.location=loc;bone.rotation_quaternion=rot;bone.scale=stretch
                for prop in ('location','rotation_quaternion','scale'):
                    if not bone.keyframe_insert(data_path=prop,frame=frame,group=bone.name):raise RuntimeError('Blender refused a retargeted key')
            report_progress({'phase':'retargeting motion','frame':frame,'source_frame':sf,'fraction':.5*(index+1)/count})
        for curve in curves(action,slot):
            for key in curve.keyframe_points:key.interpolation='LINEAR'
        for index,frame in enumerate(range(p['frame_start'],p['frame_end']+1)):
            check_cancelled();sf=source_start+(frame-p['frame_start'])*p['playback_speed'];set_frame(sf)
            evaluated=source.evaluated_get(bpy.context.evaluated_depsgraph_get());poses,_=desired_pose(evaluated,output,p,scale,roots);world=object_pose(evaluated.matrix_world,source_ref,target_ref,p,scale)
            set_frame(frame);deps=bpy.context.evaluated_depsgraph_get();actual=output.evaluated_get(deps)
            max_error=max(max_error,matrix_error(actual.matrix_world,world))
            for name,pose in poses.items():max_error=max(max_error,matrix_error(actual.matrix_world@actual.pose.bones[name].matrix,world@pose))
            if max_error>p['tolerance']:raise ValueError('Retargeted keyed output exceeded matrix tolerance; outputs removed')
            mesh_samples=[]
            for mesh in skins:
                value=skin_sample(mesh,deps,vertex_budget);vertex_budget-=value['vertices'];mesh_samples.append(value)
            if index in {0,count//2,count-1}:samples.append({'frame':frame,'source_frame':sf,'meshes':mesh_samples})
            report_progress({'phase':'verifying retargeted motion','frame':frame,'source_frame':sf,'fraction':.5+.5*(index+1)/count})
        key_count=sum(len(c.keyframe_points) for c in curves(action,slot))
        check_cancelled();success=True
        return {'source':source.name,'target':target.name,'name':output.name,'clip':action.name,'meshes':[{'source':m['source'],'output':m['output']} for m in p['meshes']],
                'translation_scale':scale,'rotation_mode':p['rotation_mode'],'object_motion':p['object_motion'],'frame_count':count,
                'keyframe_point_count':key_count,'within_nla_key_limit':key_count<=200000,'max_world_matrix_error':max_error,'tolerance':p['tolerance'],'ignored_source_scale_bones':sorted(ignored),'samples':samples,
                'restored_frame':saved[0],'scope':'Every integer target frame verified against transfer math; anatomical mapping, foot contact and subframe accuracy require separate review'}
    finally:
        if not success:
            for obj in reversed(created):bpy.data.objects.remove(obj,do_unlink=True)
            for block in reversed(blocks):
                # Deleting a Mesh ID also deletes its owned Key ID in native Blender.
                collection=bpy.data.armatures if isinstance(block,bpy.types.Armature) else bpy.data.meshes
                collection.remove(block)
            if action is not None:bpy.data.actions.remove(action)
        scene.frame_set(saved[0],subframe=saved[1]);bpy.context.view_layer.update()


def dispatch(command,p):return inspect(p) if command=='inspect_animation_retarget' else retarget(p)
