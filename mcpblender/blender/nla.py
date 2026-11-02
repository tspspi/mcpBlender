"""Native NLA action strips with guarded, staged track replacement."""
import hashlib
import json
import math
import uuid

import bpy

from .assets import local_object
from .animation_curves import channels,channel_info,allowed_paths
from .simulations import props

COMMANDS={'inspect_nla','configure_nla_track','configure_nla_strip','remove_nla_strip','remove_nla_track','move_nla_track','configure_nla_playback'}
OWNED='mcpblender_nla'


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()
def metadata(block):return json.loads(block.get(OWNED,'{}'))


def owner(p,edit=False):
    obj=local_object(p['name']) if edit else bpy.data.objects.get(p['name'])
    if not obj:raise ValueError('NLA object not found')
    if edit and obj.data and obj.data.override_library:raise ValueError('Local non-overridden data required')
    if p.get('target','OBJECT')=='OBJECT':return obj,obj
    if obj.type!='MESH' or not obj.data.shape_keys:raise ValueError('Shape-key target requires a mesh with relative shape keys')
    from .morphs import validate_target
    validate_target(obj);block=obj.data.shape_keys
    if edit and (obj.data.users>1 or block.library or block.override_library):raise ValueError('Independent local mesh/shape-key data required')
    return obj,block


def source(action,slot,cache):
    if not action:return None
    key=(action.as_pointer(),slot.identifier if slot else None)
    if key not in cache:
        records=[channel_info(c) for c in channels(action,slot)]
        value={'name':action.name,'slot':slot.identifier if slot else None,'channels':records,
               'range':list(action.frame_range),'action_properties':{k:getattr(action,k) for k in ('use_frame_range','frame_start','frame_end','use_cyclic')},'layers':[props(layer) for layer in getattr(action,'layers',())]}
        cache[key]={'name':action.name,'slot':slot.identifier if slot else None,'action_sha256':digest(value),
                    'frame_range':list(action.frame_range),'total_channels':len(records)}
    return cache[key]


def strip_record(strip,cache,depth=0,structural=False):
    if depth>4 or len(strip.strips)>128 or len(strip.fcurves)>8:raise ValueError('Imported NLA nesting/control count exceeds inspection limits')
    if sum(len(c.keyframe_points)+len(c.sampled_points) for c in strip.fcurves)>10000:raise ValueError('NLA control curve inspection supports 10000 points per strip')
    return {'name':strip.name,'type':strip.type,'properties':{k:v for k,v in props(strip).items() if k not in {'select','show_expanded','influence','strip_time'}},
            'action':({'name':strip.action.name,'slot':strip.action_slot.identifier if getattr(strip,'action_slot',None) else None} if strip.action else None) if structural else source(strip.action,getattr(strip,'action_slot',None),cache),
            'control_curves':len(strip.fcurves),'controls_sha256':digest([channel_info(c) for c in strip.fcurves]),
            'children':[strip_record(s,cache,depth+1,structural) for s in strip.strips]}


def native_strip_hash(strip):
    return digest(strip_record(strip,{},structural=True))


def envelope(settings):
    s=settings;stop=s['start']+(s['action_end']-s['action_start'])*s['scale']*s['repeat'];weight=s['influence']
    points={s['start']:0 if s['blend_in'] else weight,stop:0 if s['blend_out'] else weight}
    if s['blend_in']:points[s['start']+s['blend_in']]=weight
    if s['blend_out']:points[stop-s['blend_out']]=weight
    return sorted(points.items())


def supported(block,track,strip):
    stored=metadata(block).get(track.name,{}).get('strips',{}).get(strip.name)
    if not (isinstance(stored,dict) and strip.type=='CLIP' and strip.use_animated_influence and not strip.use_animated_time
            and len(strip.fcurves)==1 and strip.fcurves[0].data_path=='influence' and not strip.strips
            and stored.get('native_sha256')==native_strip_hash(strip)):return False
    try:
        s=stored['settings'];control=strip.fcurves[0]
        if not strip.action or strip.action.name!=s['clip'] or strip.use_auto_blend or strip.use_sync_length:return False
        slot=getattr(strip,'action_slot',None)
        if (slot.identifier if slot else None)!=s.get('slot'):return False
        values={'frame_start':s['start'],'frame_end':s['start']+(s['action_end']-s['action_start'])*s['scale']*s['repeat'],'action_frame_start':s['action_start'],'action_frame_end':s['action_end'],
                'scale':s['scale'],'repeat':s['repeat'],'blend_in':s['blend_in'],'blend_out':s['blend_out']}
        if any(abs(getattr(strip,k)-v)>1e-4 for k,v in values.items()):return False
        if strip.use_reverse!=s['reverse'] or strip.blend_type!=s['blend'] or strip.extrapolation!=s['extrapolation'] or strip.mute!=s['mute']:return False
        points=envelope(s)
        if len(control.keyframe_points)!=len(points) or control.extrapolation!='CONSTANT' or control.modifiers or control.sampled_points or control.mute or control.lock:return False
        if any(k.interpolation!='LINEAR' or max(abs(k.co.x-x),abs(k.co.y-y))>1e-4 for k,(x,y) in zip(control.keyframe_points,points)):return False
    except (KeyError,AttributeError,TypeError,ValueError):return False
    return True


def inspect(p):
    obj,block=owner(p);anim=block.animation_data;cache={};tracks=[]
    if anim and len(anim.nla_tracks)>64:raise ValueError('NLA inspection supports 64 tracks')
    total=0
    for i,track in enumerate(anim.nla_tracks if anim else []):
        total+=len(track.strips)
        if total>512:raise ValueError('NLA inspection supports 512 top-level strips')
        tracks.append({'name':track.name,'index':i,'mute':track.mute,'solo':track.is_solo,'lock':track.lock,
                       'managed':track.name in metadata(block),'strips':[strip_record(s,cache)|{'typed_editable':supported(block,track,s)} for s in track.strips]})
    state={'name':obj.name,'target':p.get('target','OBJECT'),'use_nla':anim.use_nla if anim else False,
           'tweak_mode':anim.use_tweak_mode if anim else False,
           'active_action':source(anim.action,getattr(anim,'action_slot',None),cache) if anim else None,
           'active_settings':{k:getattr(anim,k) for k in ('action_blend_type','action_extrapolation','action_influence')} if anim else {},'tracks':tracks}
    signature=digest(state);offset,limit=p.get('offset',0),p.get('limit',16)
    return state|{'nla_sha256':signature,'total_tracks':len(tracks),'tracks':tracks[offset:offset+limit],
                  'next_offset':offset+limit if offset+limit<len(tracks) else None,'stack_order':'bottom to top'}


def slot_for(obj,block,action,identifier):
    if action.library or action.override_library:raise ValueError('NLA authoring currently requires local actions')
    slots=[s for s in getattr(action,'slots',()) if s.target_id_type==('KEY' if isinstance(block,bpy.types.Key) else 'OBJECT')]
    if hasattr(action,'slots'):
        preferred=[s for s in slots if s.identifier==identifier] if identifier else [s for s in slots if s.name_display in {obj.name,block.name}]
        if not preferred and not identifier and len(slots)==1:preferred=slots
        if len(preferred)!=1:raise ValueError('Choose exactly one compatible action slot using slot')
        slot=preferred[0]
    else:
        if identifier:raise ValueError('Legacy action has no named slots')
        slot=None
    allowed={k.path_from_id('value'):1 for k in block.key_blocks if k!=block.reference_key} if isinstance(block,bpy.types.Key) else allowed_paths(obj)
    curves=channels(action,slot)
    if not curves:raise ValueError('Selected action slot has no channels')
    for c in curves:
        if c.data_path not in allowed or c.array_index>=allowed[c.data_path]:raise ValueError('Action slot contains unsupported or incompatible target channels')
        block.path_resolve(c.data_path)
        if block.animation_data and any(d.data_path==c.data_path and d.array_index==c.array_index for d in block.animation_data.drivers):raise ValueError('Action channel is driven; layer its upstream control instead')
    return slot


def plan(obj,block,specs):
    names=[v['strip'] for v in specs]
    if len(set(names))!=len(names):raise ValueError('Strip names must be unique')
    ordered=sorted(specs,key=lambda v:v['settings']['start']);end=None;prepared=[]
    for spec in ordered:
        settings=spec['settings'];action=bpy.data.actions.get(settings['clip'])
        if not action:raise ValueError('NLA action not found')
        slot=slot_for(obj,block,action,settings.get('slot'))
        stop=settings['start']+(settings['action_end']-settings['action_start'])*settings['scale']*settings['repeat']
        if end is not None and settings['start']<end-1e-5:raise ValueError('Strips on the same track cannot overlap; use separate blend tracks')
        end=stop
        if len(spec['strip'].encode())>63:raise ValueError('Strip name must fit 63 UTF-8 bytes')
        prepared.append((spec,action,slot))
    return prepared


def apply_strip(track,prepared):
    spec,action,slot=prepared;s=spec['settings'];strip=track.strips.new('stage_'+uuid.uuid4().hex,math.ceil(s['start']),action)
    if slot is not None:strip.action_slot=slot
    strip.use_sync_length=False;strip.use_auto_blend=False;strip.use_animated_influence=False;strip.use_animated_time=False
    # Expanding the bounds first avoids native setters clamping a disjoint range.
    strip.action_frame_start=min(strip.action_frame_start,s['action_start'])
    strip.action_frame_end=max(strip.action_frame_end,s['action_end'])
    strip.action_frame_start=s['action_start'];strip.action_frame_end=s['action_end']
    strip.frame_start=s['start'];strip.scale=s['scale'];strip.repeat=s['repeat']
    strip.frame_end=s['start']+(s['action_end']-s['action_start'])*s['scale']*s['repeat']
    strip.use_reverse=s['reverse'];strip.blend_type=s['blend'];strip.extrapolation=s['extrapolation'];strip.influence=s['influence']
    strip.blend_in=s['blend_in'];strip.blend_out=s['blend_out'];strip.mute=s['mute']
    expected={'frame_start':s['start'],'frame_end':s['start']+(s['action_end']-s['action_start'])*s['scale']*s['repeat'],
              'action_frame_start':s['action_start'],'action_frame_end':s['action_end'],'scale':s['scale'],'repeat':s['repeat'],
              'blend_in':s['blend_in'],'blend_out':s['blend_out'],'influence':s['influence']}
    if any(abs(getattr(strip,k)-v)>1e-4 for k,v in expected.items()):raise ValueError('Installed Blender clamped strip timing/blending; source track retained')
    # Native unanimated influence is overwritten with automatic 0..1 fades.
    # Use an explicit owned envelope so static weight and fades compose exactly.
    strip.use_animated_influence=True
    control=next(c for c in strip.fcurves if c.data_path=='influence')
    while control.keyframe_points:control.keyframe_points.remove(control.keyframe_points[-1],fast=True)
    for frame,value in envelope(s):
        key=control.keyframe_points.insert(frame,value,options={'FAST'});key.interpolation='LINEAR'
    control.extrapolation='CONSTANT';control.update()
    if strip.use_animated_time or len(strip.fcurves)!=1:raise ValueError('Unexpected native strip automation; source retained')
    return strip


def track_specs(block,track):
    if track.name not in metadata(block) or track.lock:raise ValueError('Track is imported/unmanaged or locked; inspect-only')
    if any(not supported(block,track,s) for s in track.strips):raise ValueError('Track contains imported/modified/animated strips; inspect-only')
    stored=metadata(block)[track.name]['strips']
    return [{'strip':s.name,'settings':stored[s.name]['settings']} for s in track.strips]


def rebuild(obj,block,replacements,all_tracks=False,after=None):
    """Stage complete replacement tracks before deleting any source tracks."""
    from .bridge import check_cancelled,report_progress
    anim=block.animation_data;staged=[];saved_active=anim.nla_tracks.active;active_pointer=saved_active.as_pointer() if saved_active else None;new_active=None;committed=False
    states={old.as_pointer():(old.name,old.mute,old.is_solo) for old,_ in replacements}
    saved_frame=bpy.context.scene.frame_current,bpy.context.scene.frame_subframe
    try:
        total=sum(len(specs) for _,specs in replacements);completed=0;previous=after
        for old,specs in replacements:
            check_cancelled()
            prepared=plan(obj,block,specs)
            new=anim.nla_tracks.new(prev=previous) if all_tracks else anim.nla_tracks.new(prev=after or old)
            if all_tracks:previous=new
            staged.append((old,new,[]));new.name='stage_'+uuid.uuid4().hex;new.mute=True
            for item in prepared:
                check_cancelled();staged[-1][2].append((apply_strip(new,item),item[0]));completed+=1
                report_progress({'phase':'staging NLA tracks','strips':completed,'total_strips':total,'fraction':completed/max(total,1)})
        check_cancelled()
        meta=metadata(block)
        for old,new,items in staged:
            name,mute,solo=states[old.as_pointer()]
            if old.as_pointer()==active_pointer:new_active=new
            for strip in old.strips:
                if strip.action:strip.action.use_fake_user=True
            anim.nla_tracks.remove(old);new.name=name;new.mute=mute
            meta[name]={'strips':{}}
            for strip,spec in items:
                strip.name=spec['strip']
                if strip.name!=spec['strip']:raise ValueError('Native strip name changed unexpectedly')
                settings=spec['settings']|{'slot':strip.action_slot.identifier if getattr(strip,'action_slot',None) else None}
                meta[name]['strips'][strip.name]={'settings':settings,'native_sha256':native_strip_hash(strip)}
        solo_name=next((name for name,mute,solo in states.values() if solo),None)
        if solo_name:anim.nla_tracks[solo_name].is_solo=True
        block[OWNED]=json.dumps(meta);committed=True
        if new_active:
            anim.nla_tracks.active=new_active
        elif saved_active:anim.nla_tracks.active=saved_active
    finally:
        if not committed:
            # Ordinary native/preflight failures occur during staging, so source
            # tracks/actions have not been removed. Inspect after exceptional
            # commit-phase failures from external callbacks or native corruption.
            for _,new,_ in reversed(staged):
                if new.name in anim.nla_tracks:anim.nla_tracks.remove(new)
            if saved_active and saved_active.name in anim.nla_tracks:anim.nla_tracks.active=saved_active
        block.update_tag();bpy.context.scene.frame_set(saved_frame[0],subframe=saved_frame[1]);bpy.context.view_layer.update()


def shape_zero_base(obj,block):
    """NLA's native RNA default for shape weights is ONE, not static DNA zero.

    An explicit zero action at the bottom makes weighted/additive shape layers
    useful without altering Blender or changing any user source action.
    """
    anim=block.animation_data_create();tracks=list(anim.nla_tracks)
    recipes={t.name:track_specs(block,t) for t in tracks}
    marker=block.get('mcpblender_nla_zero_base','');base=anim.nla_tracks.get(marker)
    if base and not (len(base.strips)==1 and base.strips[0].action and base.strips[0].action.get('mcpblender_nla_zero')):
        raise ValueError('Existing shape-base marker no longer identifies an untouched generated base')
    if not base and len(tracks)>=64:raise ValueError('Leave room for the generated zero-shape base track')
    if sum(len(t.strips) for t in tracks if t!=base)+1>512:raise ValueError('Leave room for the generated zero-shape base strip')
    active=anim.nla_tracks.active;old_meta=block.get(OWNED);old_action=base.strips[0].action if base else None
    action=None;created_track=None;success=False
    try:
        action=bpy.data.actions.new('Shape_Zero_'+uuid.uuid4().hex[:12]);action['mcpblender_nla_zero']=block.name
        if hasattr(action,'slots'):
            slot=action.slots.new(id_type='KEY',name=obj.name)
            layer=action.layers.new('Zero shape base');native_strip=layer.strips.new(type='KEYFRAME')
            bag=native_strip.channelbags.new(slot);curves=bag.fcurves
        else:slot=None;curves=action.fcurves
        for key in block.key_blocks:
            path=key.path_from_id('value')
            if key==block.reference_key or (block.animation_data and any(c.data_path==path for c in block.animation_data.drivers)):continue
            c=curves.new(data_path=path,index=0)
            for frame in (1,2):c.keyframe_points.insert(frame,0).interpolation='CONSTANT'
            c.extrapolation='CONSTANT';c.update()
        if not len(curves):raise ValueError('No independent shape weights for a zero-base layer')
        if not base:
            created_track=anim.nla_tracks.new();base=created_track
            base.name='Shape Base' if 'Shape Base' not in anim.nla_tracks else 'Shape Base '+uuid.uuid4().hex[:8]
            meta=metadata(block);meta[base.name]={'strips':{}};block[OWNED]=json.dumps(meta)
        settings={'clip':action.name,'slot':slot.identifier if slot else None,'start':1,'action_start':1,'action_end':2,
                  'scale':1,'repeat':1,'reverse':False,'blend':'REPLACE','extrapolation':'HOLD','influence':1,'blend_in':0,'blend_out':0,'mute':False}
        specs=[{'strip':'Shape_Zero_'+uuid.uuid4().hex[:12],'settings':settings}]
        # Bottom-to-top reconstruction is necessary because the native append
        # API cannot insert before an existing first track.
        rebuild(obj,block,[(base,specs)]+[(t,recipes[t.name]) for t in tracks if t!=base],all_tracks=True)
        new_base=next(t for t in anim.nla_tracks if any(s.action==action for s in t.strips));new_base.mute=False
        block['mcpblender_nla_zero_base']=new_base.name;action.use_fake_user=True
        action['mcpblender_nla_zero_sha']=source(action,slot,{})['action_sha256'];success=True
        if (old_action and old_action.get('mcpblender_nla_zero')==block.name and old_action.users==1 and old_action.use_fake_user
                and set(old_action.keys())=={'mcpblender_nla_zero','mcpblender_nla_zero_sha'}
                and (not hasattr(old_action,'slots') or len(old_action.slots)==1)):
            old_slot=old_action.slots[0] if hasattr(old_action,'slots') and old_action.slots else None
            if old_action.get('mcpblender_nla_zero_sha')==source(old_action,old_slot,{})['action_sha256']:
                bpy.data.actions.remove(old_action)
    finally:
        if not success:
            if created_track and created_track.name in anim.nla_tracks:anim.nla_tracks.remove(created_track)
            if old_meta is None:
                if OWNED in block:del block[OWNED]
            else:block[OWNED]=old_meta
            if action and action.users==0:bpy.data.actions.remove(action)
            if active and active.name in anim.nla_tracks:anim.nla_tracks.active=active


def dispatch(command,p):
    if command=='inspect_nla':return inspect(p)
    obj,block=owner(p,True)
    if inspect(p)['nla_sha256']!=p['expected_nla']:raise ValueError('NLA fingerprint is stale; inspect_nla again')
    anim=block.animation_data
    if anim and anim.use_tweak_mode:raise ValueError('Leave NLA tweak mode before structured editing')
    if anim and len({t.name for t in anim.nla_tracks})!=len(anim.nla_tracks):raise ValueError('Duplicate imported track names are inspect-only')
    if anim and sum(t.is_solo for t in anim.nla_tracks)>1:raise ValueError('Ambiguous imported multiple-solo state is inspect-only')
    if command=='configure_nla_playback':
        if p['reset_base'] and block==obj and obj.type!='ARMATURE':raise ValueError('Base reset supports rig poses/shape weights; object transforms are preserved')
        if p['reset_base'] and block!=obj:shape_zero_base(obj,block)
        anim=block.animation_data_create()
        if p['clear_active_action']:
            if anim.action:anim.action.use_fake_user=True
            anim.action=None
        anim.use_nla=p['use_nla'];anim.action_blend_type=p['active_blend'];anim.action_influence=p['active_influence'];anim.action_extrapolation=p['active_extrapolation']
        if p['reset_base']:
            if block==obj:
                from .rigging import reset_pose
                reset_pose(obj)
            else:
                for key in block.key_blocks:
                    if key!=block.reference_key:key.value=0
        block.update_tag();bpy.context.scene.frame_set(bpy.context.scene.frame_current,subframe=bpy.context.scene.frame_subframe);bpy.context.view_layer.update()
        return inspect(p)
    if len(p['track'].encode())>63:raise ValueError('Track name must fit 63 UTF-8 bytes')
    track=anim.nla_tracks.get(p['track']) if anim else None
    if command=='configure_nla_track':
        if track and (track.name not in metadata(block) or track.lock):raise ValueError('Imported/unmanaged or locked track is inspect-only')
        if track and p.get('after_track'):raise ValueError('Use move_nla_track to reorder existing tracks')
        if not track:
            if anim and len(anim.nla_tracks)>=64:raise ValueError('Track limit reached')
            previous=anim.nla_tracks.get(p['after_track']) if anim and p.get('after_track') else None
            if p.get('after_track') and not previous:raise ValueError('Insertion track not found')
            anim=block.animation_data_create();track=anim.nla_tracks.new(prev=previous);track.name=p['track']
            meta=metadata(block);meta[track.name]={'strips':{}};block[OWNED]=json.dumps(meta)
        track.mute=p['mute']
        if track.is_solo!=p['solo']:track.is_solo=p['solo']
        block.update_tag();bpy.context.view_layer.update();return inspect(p)
    if not track:raise ValueError('NLA track not found')
    specs=track_specs(block,track)
    if command=='remove_nla_track':
        for strip in track.strips:
            if strip.action:strip.action.use_fake_user=True
        anim.nla_tracks.remove(track);meta=metadata(block);meta.pop(p['track']);block[OWNED]=json.dumps(meta)
    elif command=='move_nla_track':
        tracks=list(anim.nla_tracks)
        if p['index']>=len(tracks):raise ValueError('Track index outside stack')
        current=tracks.index(track)
        if p['index']==current:return inspect(p)
        tracks.remove(track);tracks.insert(p['index'],track)
        if p['index']>0:
            rebuild(obj,block,[(track,specs)],after=tracks[p['index']-1])
        else:
            prefix=list(anim.nla_tracks)[:current+1]
            order=[track]+[t for t in prefix if t!=track]
            rebuild(obj,block,[(t,track_specs(block,t)) for t in order],all_tracks=True,after=prefix[-1])
    else:
        existing=next((s for s in specs if s['strip']==p['strip']),None)
        if command=='remove_nla_strip':
            if not existing:raise ValueError('Managed strip not found')
            specs.remove(existing)
        else:
            if any(s.name==p['strip'] for t in anim.nla_tracks if t!=track for s in t.strips):raise ValueError('Strip names must be unique across the stack')
            if existing:specs.remove(existing)
            specs.append({'strip':p['strip'],'settings':p['settings']})
        if sum(len(t.strips) for t in anim.nla_tracks if t!=track)+len(specs)>512:raise ValueError('Strip limit reached')
        rebuild(obj,block,[(track,specs)])
    block.update_tag();bpy.context.scene.frame_set(bpy.context.scene.frame_current,subframe=bpy.context.scene.frame_subframe);bpy.context.view_layer.update()
    return inspect(p)
