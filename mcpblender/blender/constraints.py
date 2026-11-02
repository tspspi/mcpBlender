"""Typed constraint authoring with object/bone dependency checks."""
import hashlib
import json
import math

import bpy

from .assets import local_object,mesh_object,inspect_mesh
from .rigging import armature_object
from .simulations import props
from mcpblender.animation_graph import SUPPORTED,validate_graph

COMMANDS={'bake_constraint_animation','create_animation_control','inspect_animation_constraints','configure_animation_constraint','remove_animation_constraint','move_animation_constraint','sample_constraint_animation'}
NATIVE={'COPY_LOCATION':'CopyLocationConstraint','COPY_ROTATION':'CopyRotationConstraint','COPY_TRANSFORMS':'CopyTransformsConstraint','LIMIT_LOCATION':'LimitLocationConstraint','LIMIT_ROTATION':'LimitRotationConstraint','LIMIT_SCALE':'LimitScaleConstraint','DAMPED_TRACK':'DampedTrackConstraint','IK':'KinematicConstraint'}


def owner(p,edit=False):
    obj=local_object(p['name']) if edit else bpy.data.objects.get(p['name'])
    if edit and obj and obj.data and obj.data.override_library:raise ValueError('Local non-overridden data required')
    if not obj or obj.mode!='OBJECT':raise ValueError('Expected an object in Object mode')
    if p.get('bone'):
        if obj.type!='ARMATURE' or p['bone'] not in obj.pose.bones:raise ValueError('Constraint owner bone not found')
        return obj,obj.pose.bones[p['bone']]
    return obj,obj


def animation_paths(obj):
    from .domains import curves
    anim=obj.animation_data
    if not anim:return []
    paths={c.data_path for c in anim.drivers}
    bindings=[(anim.action,getattr(anim,'action_slot',None))] if anim.action else []
    bindings += [(s.action,getattr(s,'action_slot',None)) for t in anim.nla_tracks for s in t.strips if s.action]
    for action,slot in bindings:
        paths.update(c.data_path for c in curves(action,slot))
    return sorted(paths)


def descriptor(c):
    values={k:v for k,v in props(c).items() if k not in {'show_expanded','active'}}
    return {'constraint':c.name,'type':c.type,'properties':values,
            'references':{key:getattr(c,key).name if getattr(c,key,None) else None for key in ('target','pole_target','space_object')}}


def fingerprint(obj,target):
    content={'name':obj.name,'bone':target.name if target!=obj else None,
             'parent':obj.parent.name if obj.parent else None,'parent_type':obj.parent_type,'parent_bone':obj.parent_bone,
             'rotation_mode':target.rotation_mode,'stack':[descriptor(c) for c in target.constraints],
             'animation_paths':animation_paths(obj)}
    if obj.type=='ARMATURE':
        if len(obj.data.bones)>2000:raise ValueError('Constraint rig inspection is limited to 2000 bones')
        content['skeleton']=[{'name':b.name,'parent':b.parent.name if b.parent else None,'matrix':[list(r) for r in b.matrix_local]} for b in obj.data.bones]
        content['ik_solver']=obj.pose.ik_solver
    return hashlib.sha256(json.dumps(content,sort_keys=True,allow_nan=False).encode()).hexdigest()



def ik_diagnostics(obj,bone,c):
    chain=[];current=bone
    while current and (not c.chain_count or len(chain)<c.chain_count):
        chain.append(current);current=current.parent
    directions=[b.bone.tail_local-b.bone.head_local for b in chain]
    collinear=len(directions)>1 and all(abs(a.normalized().dot(b.normalized()))>1-1e-6 for a,b in zip(directions,directions[1:]))
    result={'chain_length':len(chain),'rest_chain_collinear':collinear}
    if collinear:result['warning']='Near-collinear rest chain: establish a preferred bend before judging IK reach'
    if c.target:
        deps=bpy.context.evaluated_depsgraph_get();ev=obj.evaluated_get(deps);goal=c.target.evaluated_get(deps)
        tip=ev.pose.bones[bone.name];endpoint=ev.matrix_world@(tip.tail if c.use_tail else tip.head)
        if c.subtarget and (goal.type!='ARMATURE' or c.subtarget not in goal.pose.bones):return result
        point=goal.matrix_world@goal.pose.bones[c.subtarget].head if c.subtarget else goal.matrix_world.translation
        result.update(endpoint_world=list(endpoint),target_world=list(point),endpoint_distance=(endpoint-point).length)
    return result


def inspect(p):
    bpy.context.view_layer.update();obj,target=owner(p);stack=target.constraints
    if len(stack)>256:raise ValueError('Constraint inspection supports at most 256 constraints per owner')
    paths=animation_paths(obj);records=[]
    for i,c in enumerate(list(stack)[p.get('offset',0):p.get('offset',0)+p.get('limit',64)],start=p.get('offset',0)):
        record=descriptor(c);prefix=c.path_from_id()+'.';animated=[s for s in paths if s.startswith(prefix)]
        record.update(index=i,is_valid=c.is_valid,error_location=c.error_location,error_rotation=c.error_rotation,
                      animated_paths=animated,typed_editable=c.type in SUPPORTED and not animated)
        if c.type=='IK' and target!=obj:record['ik_diagnostics']=ik_diagnostics(obj,target,c)
        records.append(record)
    return {'name':obj.name,'bone':p.get('bone'),'constraints_sha256':fingerprint(obj,target),'total_constraints':len(stack),
            'constraints':records,'next_offset':p.get('offset',0)+len(records) if p.get('offset',0)+len(records)<len(stack) else None}


def target_reference(spec):
    obj=bpy.data.objects.get(spec['name'])
    if not obj:raise ValueError('Constraint target object not found')
    if spec.get('bone') and (obj.type!='ARMATURE' or spec['bone'] not in obj.pose.bones):raise ValueError('Constraint target bone not found')
    return obj,spec.get('bone','')


def properties(p,obj,target):
    s=p['settings'];kind=s['type'];v={k:s[k] for k in ('influence','mute')}
    if s.get('owner_space'):
        if target==obj and s['owner_space'] not in {'WORLD','LOCAL'}:raise ValueError('Object owner space must be WORLD or LOCAL')
        v['owner_space']=s['owner_space']
    if s.get('target'):
        v['target'],v['subtarget']=target_reference(s['target'])
        if s.get('target_space'):
            if not v['subtarget'] and s['target_space'] not in {'WORLD','LOCAL'}:raise ValueError('Object target space must be WORLD or LOCAL')
            v['target_space']=s['target_space']
    if kind in {'COPY_LOCATION','COPY_ROTATION'}:
        for i,axis in enumerate('xyz'):v['use_'+axis]=s['axes'][i];v['invert_'+axis]=s['invert'][i]
    if kind=='COPY_LOCATION':v['use_offset']=s['use_offset']
    if kind=='COPY_ROTATION':v['mix_mode']=s['mix_mode']
    if kind=='COPY_TRANSFORMS':v.update(mix_mode=s['mix_mode'],remove_target_shear=s['remove_target_shear'])
    if kind in {'LIMIT_LOCATION','LIMIT_SCALE'}:
        for i,axis in enumerate('xyz'):
            for prefix,key in (('min_','minimum'),('max_','maximum'),('use_min_','use_min'),('use_max_','use_max')):v[prefix+axis]=s[key][i]
        v['use_transform_limit']=s['use_transform_limit']
    if kind=='LIMIT_ROTATION':
        for i,axis in enumerate('xyz'):
            v['min_'+axis]=math.radians(s['minimum_degrees'][i]);v['max_'+axis]=math.radians(s['maximum_degrees'][i]);v['use_limit_'+axis]=s['axes'][i]
        v['use_transform_limit']=s['use_transform_limit']
    if kind=='DAMPED_TRACK':v['track_axis']=s['track_axis']
    if kind=='IK':
        if target==obj or obj.type!='ARMATURE':raise ValueError('IK requires a pose-bone owner')
        if obj.pose.ik_solver!='LEGACY':raise ValueError('Typed IK currently requires the standard LEGACY solver')
        chain=target
        for _ in range(s['chain_count']):
            if not chain:raise ValueError('IK chain_count exceeds the available ancestor chain')
            chain=chain.parent
        v.update({k:s[k] for k in ('iterations','chain_count','use_tail','use_stretch')});v['pole_angle']=math.radians(s['pole_angle_degrees']);v['ik_type']='COPY_POSE'
        v['pole_target'],v['pole_subtarget']=target_reference(s['pole']) if s.get('pole') else (None,'')
    rna=getattr(bpy.types,NATIVE[kind]).bl_rna
    for key,value in {'space_object':None,'space_subtarget':'','use_bbone_shape':False,'head_tail':0}.items():
        if key in rna.properties:v[key]=value
    for key,value in v.items():
        prop=rna.properties.get(key)
        if not prop or prop.is_readonly:raise ValueError(f'Installed Blender does not expose editable {key}')
        if prop.type=='ENUM' and value not in {e.identifier for e in prop.enum_items}:raise ValueError('Unsupported native constraint enum: '+key)
        if prop.type in {'FLOAT','INT'} and not prop.hard_min<=value<=prop.hard_max:raise ValueError('Constraint value outside native range: '+key)
    return v


def dependency_records(obj,target,name,values,kind):
    if len(bpy.context.scene.objects)>5000:raise ValueError('Constraint dependency inspection supports up to 5000 scene objects')
    records=[]
    for other in bpy.context.scene.objects:
        item={'name':other.name,'bones':{},'constraints':[]}
        if other.parent:
            if other.parent_type not in {'OBJECT','BONE'}:item['blocked']='Vertex-parented dependencies are unsupported'
            item['parent']=(other.parent.name,other.parent_bone if other.parent_type=='BONE' else None)
        if other.animation_data and other.animation_data.drivers:item['blocked']='Driver dependencies require a specialized workflow'
        owners=[(None,other)]
        if other.type=='ARMATURE':
            if len(other.pose.bones)>2000:raise ValueError('Constraint dependency inspection supports up to 2000 bones per rig')
            item['bones']={b.name:b.parent.name if b.parent else None for b in other.pose.bones}
            owners += [(b.name,b) for b in other.pose.bones]
        for bone,container in owners:
            for constraint in container.constraints:
                if other==obj and container==target and constraint.name==name:continue
                row={'bone':bone,'type':constraint.type,'targets':[],'chain_count':getattr(constraint,'chain_count',0)}
                for pointer,subkey in (('target','subtarget'),('pole_target','pole_subtarget')):
                    ref=getattr(constraint,pointer,None)
                    if ref:row['targets'].append((ref.name,getattr(constraint,subkey,'') or None))
                if constraint.owner_space=='CUSTOM' or constraint.target_space=='CUSTOM' or getattr(constraint,'use_bbone_shape',False):row['blocked']='Custom-space/B-Bone constraint dependencies are unsupported'
                if other.type=='ARMATURE' and constraint.type not in SUPPORTED:item['blocked']='Unsupported constraint on dependency armature: '+constraint.type
                if constraint.type=='IK' and (other.type!='ARMATURE' or not bone or other.pose.ik_solver!='LEGACY' or constraint.ik_type!='COPY_POSE'):row['blocked']='Unsupported IK dependency solver/mode'
                item['constraints'].append(row)
        if other==obj:
            row={'bone':target.name if target!=obj else None,'type':kind,'targets':[],'chain_count':values.get('chain_count',0)}
            for pointer,subkey in (('target','subtarget'),('pole_target','pole_subtarget')):
                if values.get(pointer):row['targets'].append((values[pointer].name,values.get(subkey) or None))
            item['constraints'].append(row)
        records.append(item)
    return records


def edit(command,p):
    obj,target=owner(p,True)
    if len(p['constraint'].encode())>63:raise ValueError('Constraint name must fit 63 UTF-8 bytes')
    if fingerprint(obj,target)!=p['expected_constraints']:raise ValueError('Constraint fingerprint is stale; inspect_animation_constraints again')
    existing=target.constraints.get(p['constraint'])
    if existing:
        if existing.type not in SUPPORTED:raise ValueError('This imported constraint type is inspect-only')
        if any(path.startswith(existing.path_from_id()+'.') for path in animation_paths(obj)):raise ValueError('Keyed/driven constraint editing is refused; edit its animation first')
    if command!='configure_animation_constraint':
        if not existing:raise ValueError('Constraint not found')
        if command=='remove_animation_constraint':target.constraints.remove(existing)
        else:
            if p['index']>=len(target.constraints):raise ValueError('Constraint stack index is out of range')
            target.constraints.move(list(target.constraints).index(existing),p['index'])
        obj.update_tag();bpy.context.view_layer.update();return inspect(p)
    kind=p['settings']['type']
    if existing and existing.type!=kind:raise ValueError('Constraint type must match; remove it explicitly before replacement')
    if not existing and len(target.constraints)>=64:raise ValueError('Typed authoring supports at most 64 constraints per owner')
    values=properties(p,obj,target)
    validate_graph(dependency_records(obj,target,p['constraint'],values,kind),[(obj.name,p.get('bone'))])
    original={k:getattr(existing,k) for k in values} if existing else None
    constraint=existing or target.constraints.new(kind)
    try:
        constraint.name=p['constraint']
        for key,value in values.items():setattr(constraint,key,value)
        obj.update_tag();bpy.context.view_layer.update()
    except Exception:
        if existing:
            for key,value in original.items():setattr(existing,key,value)
        else:target.constraints.remove(constraint)
        obj.update_tag();bpy.context.view_layer.update();raise
    return inspect(p)


def sample(p):
    from .bridge import check_cancelled,report_progress
    obj,_=owner(p);names=p.get('bones')
    if names is None:names=[b.name for b in obj.pose.bones][:32] if obj.type=='ARMATURE' else []
    if names and (obj.type!='ARMATURE' or any(n not in obj.pose.bones for n in names)):raise ValueError('Sample bone not found')
    for name in p['meshes']:
        mesh=mesh_object(name)
        if obj.type=='ARMATURE' and not any(m.type=='ARMATURE' and m.object==obj for m in mesh.modifiers):raise ValueError('Sample mesh must be bound to the named armature')
    scene=bpy.context.scene;saved=scene.frame_current,scene.frame_subframe;rows=[]
    try:
        for i,frame in enumerate(p['frames']):
            check_cancelled();scene.frame_set(frame);bpy.context.view_layer.update()
            evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            meshes=[]
            for name in p['meshes']:
                info=inspect_mesh({'name':name,'sample_limit':p['sample_limit']})
                meshes.append({k:info[k] for k in ('name','vertices','world_bounds','geometry_sha256','vertex_samples','non_finite_vertices')})
            rows.append({'frame':frame,'matrix_world':[list(r) for r in evaluated.matrix_world],
                         'bones':[{'name':n,'head_world':list(evaluated.matrix_world@evaluated.pose.bones[n].head),'tail_world':list(evaluated.matrix_world@evaluated.pose.bones[n].tail)} for n in names], 'meshes':meshes})
            report_progress({'phase':'sampling constrained motion','frame':frame,'fraction':(i+1)/len(p['frames'])})
    finally:scene.frame_set(saved[0],subframe=saved[1]);bpy.context.view_layer.update()
    return {'name':obj.name,'samples':rows,'restored_frame':saved[0]}


def dispatch(command,p):
    if command=='bake_constraint_animation':
        from .animation_bake import bake
        return bake(p)
    if command=='inspect_animation_constraints':return inspect(p)
    if command=='sample_constraint_animation':return sample(p)
    if command=='create_animation_control':
        if len(p['name'].encode())>63 or p['name'] in bpy.data.objects:raise ValueError('Control name already exists or exceeds 63 UTF-8 bytes')
        if bpy.context.mode!='OBJECT':raise ValueError('Object mode required')
        prop=bpy.types.Object.bl_rna.properties['location']
        if any(not prop.hard_min<=v<=prop.hard_max for v in p['location']):raise ValueError('Control location exceeds native range')
        obj=bpy.data.objects.new(p['name'],None);bpy.context.scene.collection.objects.link(obj)
        obj.location=p['location'];obj.empty_display_type=p['display'];obj.empty_display_size=p['size'];obj.show_in_front=True
        obj['mcpblender_animation_control']=True;bpy.context.view_layer.update()
        return {'name':obj.name,'location':list(obj.location),'type':'EMPTY'}
    return edit(command,p)
