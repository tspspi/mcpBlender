"""Typed native drivers, explicit ownership and conservative dependency validation."""
import hashlib
import json
import math

import bpy

from .assets import local_object
from .constraints import dependency_records, animation_paths
from .simulations import props
from mcpblender.driver_graph import validate_drivers

COMMANDS={'inspect_animation_drivers','configure_animation_driver','remove_animation_driver','set_animation_property'}
OWNED='mcpblender_drivers'


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()
def mapping(block):return json.loads(block.get(OWNED,'{}'))
def identity(path,index):return json.dumps([path,index],separators=(',',':'))
def raw(block,path,index=0):return ('RAW','KEY' if isinstance(block,bpy.types.Key) else 'OBJECT',block.name,path,index)


def object_for(name,edit=False):
    obj=local_object(name) if edit else bpy.data.objects.get(name)
    if not obj or obj.name not in bpy.context.scene.objects:raise ValueError('Driver object must be in the current scene')
    if edit and obj.data and obj.data.override_library:raise ValueError('Local non-overridden data required')
    return obj


def bone_owner(obj,spec):
    if not spec.get('bone'):return obj
    if obj.type!='ARMATURE' or spec['bone'] not in obj.pose.bones:raise ValueError('Driver bone not found')
    return obj.pose.bones[spec['bone']]


def scalar_path(owner,name):return ('' if isinstance(owner,bpy.types.Object) else owner.path_from_id())+'['+json.dumps(name)+']'


def scalar(owner,name):
    if name.startswith('mcpblender_') or name not in owner or type(owner[name]) not in {int,float} or not math.isfinite(owner[name]):
        raise ValueError('Expected an existing finite numeric custom control property')
    return scalar_path(owner,name)


def resolve(obj,spec,edit=False):
    kind=spec['kind'];owner=bone_owner(obj,spec);block=obj;index=0;component=-1;affects=[]
    if kind=='SHAPE_KEY':
        if obj.type!='MESH' or not obj.data.shape_keys or spec['key'] not in obj.data.shape_keys.key_blocks:raise ValueError('Shape key not found')
        from .morphs import validate_target
        validate_target(obj)
        block=obj.data.shape_keys;owner=block.key_blocks[spec['key']]
        if edit and (obj.data.users>1 or block.library or block.override_library):raise ValueError('Shape driver requires independent local mesh/shape-key data')
        if edit and owner==block.reference_key:raise ValueError('Basis cannot be driven')
        path=owner.path_from_id('value')
    elif kind=='PROPERTY':path=scalar(owner,spec['property'])
    elif kind=='CONSTRAINT':
        constraint=owner.constraints.get(spec['constraint'])
        if not constraint:raise ValueError('Driven constraint not found')
        path=constraint.path_from_id('influence');affects=[(obj.name,spec.get('bone'))]
        if constraint.type=='IK' and owner!=obj:
            current=owner;affects=[]
            while current and (not constraint.chain_count or len(affects)<constraint.chain_count):
                affects.append((obj.name,current.name));current=current.parent
    else:
        prop=spec['property'];index=component=spec['component']
        if prop=='rotation_euler' and owner.rotation_mode not in {'XYZ','XZY','YXZ','YZX','ZXY','ZYX'}:raise ValueError('Euler driver requires Euler rotation mode')
        if prop=='rotation_quaternion' and owner.rotation_mode!='QUATERNION':raise ValueError('Quaternion driver requires quaternion rotation mode')
        path=owner.path_from_id(prop);affects=[(obj.name,spec.get('bone'))]
    return block,path,index,component,affects


def channel_value(obj,spec,value=None,write=False):
    target=bone_owner(obj,spec);kind=spec['kind']
    if kind=='PROPERTY':
        if write:target[spec['property']]=value
        return target[spec['property']]
    if kind=='CONSTRAINT':target=target.constraints[spec['constraint']];prop='influence'
    elif kind=='SHAPE_KEY':target=obj.data.shape_keys.key_blocks[spec['key']];prop='value'
    else:
        if write:getattr(target,spec['property'])[spec['component']]=value
        return getattr(target,spec['property'])[spec['component']]
    if write:setattr(target,prop,value)
    return getattr(target,prop)


def native_record(c):
    if len(c.driver.variables)>32 or len(c.keyframe_points)+len(c.sampled_points)>10000 or len(c.modifiers)>32:raise ValueError('Imported driver exceeds bounded inspection limits')
    if sum(len(m.control_points) for m in c.modifiers if m.type=='ENVELOPE')>10000:raise ValueError('Driver envelope exceeds inspection limits')
    from .animation_curves import key_info
    return {'data_path':c.data_path,'component':c.array_index,'mute':c.mute,'lock':c.lock,
            'extrapolation':c.extrapolation,'driver_type':c.driver.type,'expression':c.driver.expression,'use_self':c.driver.use_self,
            'variables':[{'name':v.name,'type':v.type,'targets':[{'id_type':t.id_type,'id':t.id.name if t.id else None,
                         'data_path':t.data_path,'bone_target':t.bone_target,'transform_type':t.transform_type,
                         'transform_space':t.transform_space,'rotation_mode':t.rotation_mode,
                         'use_fallback_value':t.use_fallback_value,'fallback_value':t.fallback_value} for t in v.targets]} for v in c.driver.variables],
            'modifiers':[{'type':m.type,'properties':props(m),'points':[{'frame':p.frame,'min':p.min,'max':p.max} for p in m.control_points] if m.type=='ENVELOPE' else []} for m in c.modifiers],
            'keys':[key_info(k) for k in c.keyframe_points],
            'samples':[list(k.co) for k in c.sampled_points]}


def owned(block,c):
    value=mapping(block).get(identity(c.data_path,c.array_index))
    if not value or value.get('native_sha256')!=digest(native_record(c)):return None
    # Metadata is a hint, not a dependency authority. Match typed metadata back
    # to real native channels/variables before relying on it in the graph.
    try:
        spec=value['channel'];settings=value['settings'];driver=c.driver
        if driver.type!='SCRIPTED' or driver.use_self or not driver.is_simple_expression or driver.expression!=settings['expression']:return None
        if c.modifiers or c.keyframe_points or c.sampled_points or c.mute or c.lock:return None
        if isinstance(block,bpy.types.Object):
            if resolve(block,spec)[:3]!=(block,c.data_path,c.array_index):return None
        elif spec['kind']!='SHAPE_KEY' or block.key_blocks[spec['key']].path_from_id('value')!=c.data_path or c.array_index!=0:return None
        if len(settings['variables'])!=len(driver.variables):return None
        for typed,native in zip(settings['variables'],driver.variables):
            expected,_=input_spec(typed)
            if native.name!=typed['name'] or native.type!=expected['type'] or len(native.targets)!=1:return None
            target=native.targets[0]
            if target.id!=expected['id'] or target.use_fallback_value:return None
            if any(getattr(target,k)!=v for k,v in expected.items() if k not in {'id','type'}):return None
    except (ValueError,KeyError,TypeError,AttributeError):return None
    return value


def blocks(obj):return [obj]+([obj.data.shape_keys] if obj.type=='MESH' and obj.data.shape_keys else [])


def records(obj):
    result=[]
    for block in blocks(obj):
        drivers=list(block.animation_data.drivers) if block.animation_data else []
        if len(drivers)>256:raise ValueError('Driver inspection supports 256 drivers per datablock')
        for c in drivers:
            record=native_record(c);info=owned(block,c);blockers=[]
            if obj.mode!='OBJECT' or obj.library or obj.override_library or block.library or block.override_library:
                blockers.append('Local Object-mode object/datablock required')
            if isinstance(block,bpy.types.Key) and obj.data.users>1:blockers.append('Independent mesh/shape-key data required')
            record.update(datablock=block.name,datablock_type='KEY' if isinstance(block,bpy.types.Key) else 'OBJECT',
                          typed_editable=bool(info) and not blockers,edit_blockers=blockers,channel=info['channel'] if info else None,
                          settings=info['settings'] if info else None,is_valid=c.driver.is_valid,
                          is_simple_expression=c.driver.is_simple_expression)
            result.append(record)
    return result


def inspect(p):
    obj=object_for(p['name']);rows=records(obj)
    signature=[{k:v for k,v in r.items() if k not in {'is_valid','is_simple_expression'}} for r in rows]
    offset,limit=p.get('offset',0),p.get('limit',32)
    return {'name':obj.name,'drivers_sha256':digest(signature),'total_drivers':len(rows),'drivers':rows[offset:offset+limit],
            'next_offset':offset+limit if offset+limit<len(rows) else None}


def input_spec(spec):
    obj=object_for(spec['object']);kind=spec['kind']
    if kind=='TRANSFORM':
        bone_owner(obj,spec)
        return {'type':'TRANSFORMS','id':obj,'bone_target':spec.get('bone',''),'transform_type':spec['transform'],
                'transform_space':spec['space'],'rotation_mode':spec['rotation_mode']},('EVAL',obj.name,spec.get('bone'))
    block,path,index,_,_=resolve(obj,{'kind':kind,**{k:v for k,v in spec.items() if k not in {'name','object'}}})
    return {'type':'SINGLE_PROP','id':block,'data_path':path},raw(block,path,index)


def graph(obj,channel,settings):
    inventory=dependency_records(include_drivers=False)
    target_block,target_path,target_index,_,affects=resolve(obj,channel,True)
    candidate={'node':raw(target_block,target_path,target_index),'inputs':[input_spec(v)[1] for v in settings['variables']],'affects':affects}
    rows=[];seen=set()
    for other in bpy.context.scene.objects:
        for block in blocks(other):
            if block.as_pointer() in seen:continue
            seen.add(block.as_pointer())
            native_curves=list(block.animation_data.drivers) if block.animation_data else []
            if len(native_curves)>256:raise ValueError('Driver dependency inventory is limited to 256 drivers per datablock')
            for c in native_curves:
                if block==target_block and c.data_path==target_path and c.array_index==target_index:continue
                row={'node':raw(block,c.data_path,c.array_index),'inputs':[],'affects':[]};info=owned(block,c)
                if info:
                    try:
                        row['affects']=resolve(other,info['channel'])[4]
                        row['inputs']=[input_spec(v)[1] for v in info['settings']['variables']]
                    except (ValueError,KeyError):row['blocked']='Managed driver dependencies no longer resolve'
                else:
                    row['blocked']='Reachable imported or externally modified driver is inspect-only'
                    # Unknown native paths may affect bone settings not represented
                    # by transform channels; conservatively block that object's pose.
                    row['affects']=[(other.name,None)]+([(other.name,b.name) for b in other.pose.bones] if other.type=='ARMATURE' else [])
                rows.append(row)
                if len(rows)>4096:raise ValueError('Dependency inventory supports 4096 total scene drivers')
    rows.append(candidate);validate_drivers(inventory,rows,candidate['node'])


def apply(c,settings):
    driver=c.driver;driver.type='SCRIPTED';driver.use_self=False
    for v in list(driver.variables):driver.variables.remove(v)
    for spec in settings['variables']:
        native,_=input_spec(spec);v=driver.variables.new();v.name=spec['name'];v.type=native['type'];t=v.targets[0]
        if native['type']=='SINGLE_PROP':t.id_type='KEY' if isinstance(native['id'],bpy.types.Key) else 'OBJECT'
        t.id=native['id']
        for key,value in native.items():
            if key not in {'type','id'}:setattr(t,key,value)
        t.use_fallback_value=False
    driver.expression=settings['expression']
    if driver.expression!=settings['expression']:raise ValueError('Installed Blender truncated the driver expression')
    c.mute=False;c.lock=False
    for modifier in list(c.modifiers):c.modifiers.remove(modifier)
    # Native driver_add supplies identity-map points on this Blender build.
    # A typed expression uses direct output, without a second mapping curve.
    while c.keyframe_points:c.keyframe_points.remove(c.keyframe_points[-1],fast=True)
    c.update()


def refresh(block):
    block.update_tag();bpy.context.scene.frame_set(bpy.context.scene.frame_current,subframe=bpy.context.scene.frame_subframe);bpy.context.view_layer.update()


def edit(command,p):
    obj=object_for(p['name'],True)
    if inspect(p)['drivers_sha256']!=p['expected_drivers']:raise ValueError('Driver fingerprint is stale; inspect_animation_drivers again')
    block,path,index,component,_=resolve(obj,p['channel'],True)
    curves=list(block.animation_data.drivers) if block.animation_data else []
    matches=[c for c in curves if c.data_path==path and c.array_index==index]
    if len(matches)>1:raise ValueError('Ambiguous native driver channels are inspect-only')
    existing=matches[0] if matches else None;previous=owned(block,existing) if existing else None
    if existing and not previous:raise ValueError('Imported or externally modified driver is inspect-only')
    if command=='remove_animation_driver':
        if not existing:raise ValueError('Managed driver not found')
        value=channel_value(obj,p['channel'])
        block.driver_remove(path,component);channel_value(obj,p['channel'],value,True);meta=mapping(block);meta.pop(identity(path,index),None);block[OWNED]=json.dumps(meta)
        refresh(block);return inspect(p)
    if not existing and len(curves)>=256:raise ValueError('Driver datablock limit reached')
    from .constraints import animation_paths
    if path in animation_paths(block):
        # animation_paths also includes this driver's path; distinguish real keys.
        from .domains import curves as action_curves
        anim=block.animation_data;bindings=[(anim.action,anim.action_slot)] if anim and anim.action else []
        if anim:bindings += [(s.action,s.action_slot) for t in anim.nla_tracks for s in t.strips if s.action]
        if any(c.data_path==path and c.array_index==index for action,slot in bindings for c in action_curves(action,slot)):
            raise ValueError('Driven channel is already keyed in an action/NLA; remove or isolate those keys first')
    graph(obj,p['channel'],p['settings'])
    had_animation=block.animation_data is not None;c=existing;old_value=channel_value(obj,p['channel'])
    try:
        c=c or block.driver_add(path,component);apply(c,p['settings']);refresh(block)
        if not c.driver.is_simple_expression or not c.driver.is_valid:raise ValueError('Native simple driver expression is invalid at the current frame')
        value=block.path_resolve(path);value=value[index] if component>=0 else value
        if not math.isfinite(value):raise ValueError('Native driver output is non-finite')
        meta=mapping(block);meta[identity(path,index)]={'channel':p['channel'],'settings':p['settings'],'native_sha256':digest(native_record(c))};block[OWNED]=json.dumps(meta)
    except Exception:
        if existing:apply(existing,previous['settings'])
        elif c is not None:
            block.driver_remove(path,component);channel_value(obj,p['channel'],old_value,True)
        if not had_animation and block.animation_data and not block.animation_data.action and not block.animation_data.drivers and not block.animation_data.nla_tracks:block.animation_data_clear()
        refresh(block);raise
    return inspect(p)


def set_property(p):
    obj=object_for(p['name'],True);target=bone_owner(obj,p);path=scalar_path(target,p['property'])
    if p['property'] in target and type(target[p['property']]) not in {int,float}:raise ValueError('Existing property is not a numeric control')
    if path in animation_paths(obj):raise ValueError('Keyed/driven property requires animation editing instead')
    target[p['property']]=float(p['value'])
    target.id_properties_ui(p['property']).update(min=p['minimum'],max=p['maximum'],soft_min=p['minimum'],soft_max=p['maximum'],description=p['description'])
    refresh(obj)
    return {'name':obj.name,'bone':p.get('bone'),'property':p['property'],'value':target[p['property']],'data_path':path,
            'minimum':p['minimum'],'maximum':p['maximum']}


def dispatch(command,p):
    if command=='inspect_animation_drivers':return inspect(p)
    if command=='set_animation_property':return set_property(p)
    return edit(command,p)
