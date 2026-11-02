"""Copy-on-edit action slots for constrained controllers and curve refinement."""
import hashlib
import json
import math
import struct

import bpy

from .assets import local_object
from .simulations import props


def native_float(value):
    return struct.unpack('f',struct.pack('f',value))[0]


COMMANDS = {'inspect_animation_channels', 'set_control_keyframes', 'edit_animation_curve'}


def binding(p, edit=False):
    obj = local_object(p['name']) if edit else bpy.data.objects.get(p['name'])
    if not obj or obj.mode != 'OBJECT': raise ValueError('Named object in Object mode required')
    if obj.type == 'ARMATURE' and len(obj.pose.bones) > 256: raise ValueError('Channel tools support up to 256 bones')
    anim = obj.animation_data
    action = anim.action if anim else None
    slot = getattr(anim, 'action_slot', None) if anim else None
    if action and hasattr(action, 'slots') and slot is None: raise ValueError('Active action has no bound object slot')
    return obj, anim, action, slot


def channels(action, slot):
    from .domains import curves
    result = list(curves(action, slot)) if action else []
    if len(result) > 4096 or sum(len(c.keyframe_points)+len(c.sampled_points) for c in result) > 200000:
        raise ValueError('Channel inspection supports 4096 curves and 200000 key/sample points')
    if sum(len(c.modifiers) for c in result)>512 or sum(len(m.control_points) for c in result for m in c.modifiers if m.type=='ENVELOPE')>200000:
        raise ValueError('Channel inspection supports 512 modifiers and 200000 envelope points')
    return result


def key_info(key):
    return {'co':list(key.co), 'left':list(key.handle_left), 'right':list(key.handle_right),
            'left_type':key.handle_left_type, 'right_type':key.handle_right_type,
            'interpolation':key.interpolation, 'easing':key.easing,
            'amplitude':key.amplitude, 'back':key.back, 'period':key.period, 'type':key.type}


def channel_info(c):
    return {'data_path':c.data_path, 'component':c.array_index, 'mute':c.mute, 'lock':c.lock,
            'extrapolation':c.extrapolation, 'auto_smoothing':c.auto_smoothing,
            'group':{'name':c.group.name,'mute':c.group.mute,'lock':c.group.lock} if c.group else None,
            'modifiers':[{'type':m.type, 'properties':props(m),
                          'envelope_points':[{'frame':p.frame,'min':p.min,'max':p.max} for p in m.control_points] if m.type=='ENVELOPE' else []} for m in c.modifiers],
            'keys':[key_info(k) for k in c.keyframe_points], 'samples':[list(s.co) for s in c.sampled_points]}


def state(obj, anim, action, slot):
    records = [channel_info(c) for c in channels(action, slot)]
    content = {'name':obj.name, 'action':action.name if action else None,
               'slot':slot.identifier if slot else None, 'channels':records,
               'action_properties':{k:getattr(action,k) for k in ('use_frame_range','frame_start','frame_end','use_cyclic')} if action else {},
               'layers':[props(layer) for layer in getattr(action,'layers',())] if action else [],
               'rotation_mode':obj.rotation_mode,
               'bones':[(b.name,b.rotation_mode) for b in obj.pose.bones] if obj.type=='ARMATURE' else [],
               'settings':{k:getattr(anim,k) for k in ('action_blend_type','action_extrapolation','action_influence','use_nla','use_tweak_mode')} if anim else {},
               'drivers':[(c.data_path,c.array_index) for c in anim.drivers] if anim else [],
               'nla':[(t.name,t.mute,t.is_solo) for t in anim.nla_tracks] if anim else []}
    digest = hashlib.sha256(json.dumps(content,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return digest, records


def allowed_paths(obj):
    targets = [obj] + (list(obj.pose.bones) if obj.type=='ARMATURE' else [])
    result = {}
    for target in targets:
        for prop, size in (('location',3),('rotation_euler',3),('rotation_quaternion',4),('scale',3)):
            result[target.path_from_id(prop)] = size
        for constraint in target.constraints: result[constraint.path_from_id('influence')] = 1
    return result


def edit_blockers(obj, anim, action):
    result=[]
    if obj.library or obj.override_library or (obj.data and (obj.data.library or obj.data.override_library)):
        result.append('Local non-overridden object/data required')
    if anim and (anim.drivers or anim.use_tweak_mode or any(not t.mute or t.is_solo for t in anim.nla_tracks)
                 or anim.action_blend_type != 'REPLACE' or abs(anim.action_influence-1) > 1e-6):
        result.append('Channel editing requires no drivers, active NLA or blended active action')
    if action and not hasattr(action,'fcurves') and (len(action.layers)>1 or any(len(l.strips)>1 for l in action.layers)):
        result.append('Channel editing currently requires at most one action layer and one keyframe strip')
    return result


def inspect(p):
    obj, anim, action, slot = binding(p)
    digest, records = state(obj, anim, action, slot)
    paths = allowed_paths(obj)
    offset, limit = p.get('offset',0), p.get('limit',16)
    ko, kl = p.get('key_offset',0), p.get('key_limit',16)
    for record in records[offset:offset+limit]:
        record['total_keys'] = len(record['keys']); record['sample_count'] = len(record.pop('samples'))
        record['keys'] = record['keys'][ko:ko+kl]
        record['next_key_offset'] = ko+kl if ko+kl < record['total_keys'] else None
        record['typed_editable'] = (record['data_path'] in paths and record['component'] < paths[record['data_path']]
                                    and not record['modifiers'] and not record['sample_count'] and not record['lock'] and not record['mute']
                                    and not (record['group'] and (record['group']['mute'] or record['group']['lock'])))
    return {'name':obj.name, 'action':action.name if action else None, 'slot':slot.identifier if slot else None,
            'animation_sha256':digest, 'total_channels':len(records), 'channels':records[offset:offset+limit],
            'next_offset':offset+limit if offset+limit < len(records) else None,
            'edit_blockers':edit_blockers(obj,anim,action),
            'editing_mode':'New independent clip, activated after editing; source action preserved'}


def preflight(p):
    obj, anim, action, slot = binding(p, True)
    digest, _ = state(obj, anim, action, slot)
    if digest != p['expected_animation']: raise ValueError('Animation fingerprint is stale; inspect_animation_channels again')
    if p['output_clip'] in bpy.data.actions or len(p['output_clip'].encode()) > 63:
        raise ValueError('Output clip name must be unused and fit 63 UTF-8 bytes')
    blockers=edit_blockers(obj,anim,action)
    if blockers: raise ValueError('; '.join(blockers))
    if action and hasattr(action,'slots'):
        if len(action.slots)>16: raise ValueError('Copy-on-edit supports up to 16 action slots')
        total=0
        for other_slot in action.slots:
            total+=sum(len(c.keyframe_points)+len(c.sampled_points) for c in channels(action,other_slot))
        if total>200000: raise ValueError('Copied action is limited to 200000 total key/sample points across slots')
    return obj, anim, action, slot


def editable(c):
    if c.lock or c.mute or c.modifiers or c.sampled_points or (c.group and (c.group.lock or c.group.mute)): raise ValueError('Selected channel is locked, muted, sampled or modified; inspect-only')


def find_keys(c, frames):
    selected = []
    for frame in frames:
        matches = [k for k in c.keyframe_points if abs(k.co.x-native_float(frame))<1e-5]
        if len(matches)!=1: raise ValueError('Each selected frame must identify exactly one existing key')
        selected.append(matches[0])
    if len({k.as_pointer() for k in selected}) != len(selected): raise ValueError('Selected frames resolve to duplicate native keys')
    return selected


def control_target(obj, p):
    target = obj
    if p.get('bone'):
        if obj.type!='ARMATURE' or p['bone'] not in obj.pose.bones: raise ValueError('Control bone not found')
        target = obj.pose.bones[p['bone']]
    if p.get('constraint'):
        if p['constraint'] not in target.constraints: raise ValueError('Control constraint not found')
        return target.constraints[p['constraint']], 'influence'
    prop = 'rotation_euler' if p['property']=='rotation_degrees' else p['property']
    if prop=='rotation_euler' and target.rotation_mode not in {'XYZ','XZY','YXZ','YZX','ZXY','ZYX'}:
        raise ValueError('Degree rotation keys require an Euler rotation mode')
    if prop=='rotation_quaternion' and target.rotation_mode!='QUATERNION': raise ValueError('Quaternion keys require quaternion rotation mode')
    return target, prop


def dispatch(command, p):
    if command=='inspect_animation_channels': return inspect(p)
    obj, anim, source, slot = preflight(p)
    source_curves = channels(source,slot)
    if command=='set_control_keyframes':
        target, prop = control_target(obj,p); path = target.path_from_id(prop)
        for c in source_curves:
            if c.data_path==path: editable(c)
        if any(sum(c.data_path==path and c.array_index==i for c in source_curves)>1 for i in range(4)):
            raise ValueError('Duplicate native channels are inspect-only')
        native_frames=sorted(native_float(k['frame']) for k in p['keyframes'])
        if any(b-a<1e-4 for a,b in zip(native_frames,native_frames[1:])):
            raise ValueError('Key frames collide at native float precision')
        for c in source_curves:
            if c.data_path==path:
                for frame in native_frames:
                    if any(1e-5<=abs(k.co.x-frame)<1e-4 for k in c.keyframe_points):
                        raise ValueError('New key nearly collides with an existing key')
        native = target.bl_rna.properties[prop]
        for key in p['keyframes']:
            values = key['value'] if isinstance(key['value'],list) else [key['value']]
            if p['property']=='rotation_degrees': values=[math.radians(v) for v in values]
            if any(not native.hard_min<=v<=native.hard_max for v in values): raise ValueError('Key value exceeds native property limits')
    else:
        path=p['data_path']; size=allowed_paths(obj).get(path)
        if size is None or p['component']>=size: raise ValueError('Channel must be an existing object/bone transform or constraint influence path')
        matches=[c for c in source_curves if c.data_path==path and c.array_index==p['component']]
        if len(matches)!=1: raise ValueError('Choose exactly one existing channel')
        c=matches[0]; editable(c); selected=find_keys(c,p['frames']); settings=p['settings']; op=settings['operation']
        if op=='TRANSFORM':
            destinations=[native_float(settings['pivot_frame']+(k.co.x-settings['pivot_frame'])*settings['time_scale']+settings['time_offset']) for k in selected]
            untouched=[k.co.x for k in c.keyframe_points if k.as_pointer() not in {v.as_pointer() for v in selected}]
            if any(not -1048574<=f<=1048574 for f in destinations): raise ValueError('Transformed frames exceed timeline limits')
            combined=sorted(destinations+untouched)
            if any(b-a<1e-4 for a,b in zip(combined,combined[1:])): raise ValueError('Retiming would collide with another key')
        if op=='HANDLES':
            for k in selected:
                if (settings.get('left') and settings['left'][0]>k.co.x) or (settings.get('right') and settings['right'][0]<k.co.x):
                    raise ValueError('Left/right handle times must bracket their key')
    saved_frame=bpy.context.scene.frame_current, bpy.context.scene.frame_subframe
    saved_value = getattr(target,prop) if command=='set_control_keyframes' else None
    if hasattr(saved_value,'copy'): saved_value=saved_value.copy()
    had_animation=anim is not None; working=None; committed=False
    try:
        working=source.copy() if source else bpy.data.actions.new(p['output_clip'])
        working.name=p['output_clip']; working.use_fake_user=True
        working['mcpblender_target']=obj.name; working['mcpblender_channel_source']=source.name if source else ''
        anim=obj.animation_data_create(); anim.action=working
        working_slot=next((s for s in working.slots if slot and s.identifier==slot.identifier),None) if hasattr(working,'slots') else None
        if working_slot is not None: anim.action_slot=working_slot
        if command=='set_control_keyframes':
            for key in p['keyframes']:
                value=key['value']
                if p['property']=='rotation_degrees': value=[math.radians(v) for v in value]
                setattr(target,prop,value)
                if not target.keyframe_insert(data_path=prop,frame=native_float(key['frame'])): raise RuntimeError('Blender refused a control key')
            for c in channels(working,getattr(anim,'action_slot',None)):
                if c.data_path==path:
                    for k in c.keyframe_points:
                        if any(abs(k.co.x-native_float(v['frame']))<1e-5 for v in p['keyframes']):
                            k.interpolation=p['interpolation']
                            if p['interpolation']=='BEZIER': k.handle_left_type=k.handle_right_type='AUTO_CLAMPED'
                    c.update()
        else:
            c=next(c for c in channels(working,working_slot) if c.data_path==path and c.array_index==p['component'])
            selected=find_keys(c,p['frames'])
            if op=='DELETE':
                # Removing a point can invalidate every cached RNA point reference.
                for frame in sorted(p['frames'],reverse=True):
                    c.keyframe_points.remove(find_keys(c,[frame])[0],fast=True)
            elif op=='TRANSFORM':
                for k in selected:
                    def convert(point): return (settings['pivot_frame']+(point.x-settings['pivot_frame'])*settings['time_scale']+settings['time_offset'], point.y*settings['value_scale']+settings['value_offset'])
                    co,left,right=convert(k.co),convert(k.handle_left),convert(k.handle_right)
                    if any(not math.isfinite(v) or abs(v)>1e12 for pair in (co,left,right) for v in pair): raise ValueError('Transformed key/handle exceeds numeric bounds')
                    k.co=co; k.handle_left=left; k.handle_right=right
            elif op=='INTERPOLATION':
                for k in selected:
                    for key in ('interpolation','easing','amplitude','back','period'): setattr(k,key,settings[key])
            else:
                for k in selected:
                    k.handle_left_type=settings['left_type']; k.handle_right_type=settings['right_type']
                    if settings.get('left') is not None:k.handle_left=settings['left']
                    if settings.get('right') is not None:k.handle_right=settings['right']
            c.update()
        # Enforce bounded output and finite values before accepting the new binding.
        state(obj,anim,working,getattr(anim,'action_slot',None))
        if hasattr(working,'slots') and sum(len(c.keyframe_points)+len(c.sampled_points) for s in working.slots for c in channels(working,s))>200000:
            raise ValueError('Edited action exceeds 200000 total key/sample points across slots')
        if source: source.use_fake_user=True
        committed=True
    finally:
        if command=='set_control_keyframes': setattr(target,prop,saved_value)
        if not committed:
            if had_animation:
                anim.action=source
                if slot is not None: anim.action_slot=slot
            else: obj.animation_data_clear()
            if working is not None: bpy.data.actions.remove(working)
        bpy.context.scene.frame_set(saved_frame[0],subframe=saved_frame[1]); bpy.context.view_layer.update()
    result=inspect({'name':obj.name})
    return result | {'source_action':source.name if source else None, 'restored_frame':saved_frame[0], 'source_preserved':True}
