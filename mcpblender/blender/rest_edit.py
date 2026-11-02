"""Native additive rest edits retaining existing rig/pose/data identities."""
import hashlib
import json
import math

import bpy

from .assets import active_object,finished
from .rigging import armature_object
from mcpblender.rest_math import plan_rest

COMMANDS={'inspect_armature_rest','edit_armature_rest'}
FIELDS={'deform':'use_deform','inherit_scale':'inherit_scale','inherit_rotation':'use_inherit_rotation','local_location':'use_local_location'}


def rest_row(bone,editing=False):
    roll=bone.roll if editing else bpy.types.Bone.AxisRollFromMatrix(bone.matrix_local.to_3x3())[1]
    return {'name':bone.name,'head':list(bone.head if editing else bone.head_local),
            'tail':list(bone.tail if editing else bone.tail_local),'roll_degrees':math.degrees(roll),
            'parent':bone.parent.name if bone.parent else None,'connected':bone.use_connect,
            **{key:getattr(bone,field) for key,field in FIELDS.items()}}


def impact(rig):
    users=sorted(o.name for o in bpy.data.objects if o.type=='ARMATURE' and o.data==rig.data)
    skins=[];attachments=[];targets=[]
    for obj in bpy.data.objects:
        for mod in obj.modifiers:
            if mod.type=='ARMATURE' and mod.object==rig:skins.append({'name':obj.name,'data':obj.data.name if obj.data else None,'modifier':mod.name,'viewport':mod.show_viewport,'render':mod.show_render})
        if obj.parent==rig and obj.parent_type in {'BONE','BONE_RELATIVE'}:attachments.append({'name':obj.name,'bone':obj.parent_bone,'type':obj.parent_type})
        owners=[('',obj.constraints)]+([(b.name,b.constraints) for b in obj.pose.bones] if obj.type=='ARMATURE' else [])
        for bone,constraints in owners:
            for c in constraints:
                if getattr(c,'target',None)==rig or getattr(c,'pole_target',None)==rig or any(t.target==rig for t in getattr(c,'targets',())):
                    targets.append({'name':obj.name,'bone':bone or None,'constraint':c.name})
    anim=rig.animation_data
    channels={'action':anim.action.name if anim and anim.action else None,'nla_tracks':len(anim.nla_tracks) if anim else 0,
              'drivers':len(anim.drivers) if anim else 0,'object_constraints':len(rig.constraints),
              'bone_constraints':sum(len(b.constraints) for b in rig.pose.bones),
              'posed_bones':sum(any(abs(b.matrix_basis[i][j]-(1 if i==j else 0))>1e-6 for i in range(4) for j in range(4)) for b in rig.pose.bones)}
    return {'data_users':users,'skin_bindings':skins,'bone_attachments':attachments,'constraint_consumers':targets,'animation':channels,
            'deformation_change_acknowledgement_required':bool(skins or attachments or targets or any(channels.values()))}


def inventory(p,edit=False):
    rig=armature_object(p['name'],edit=edit)
    if rig.name not in bpy.context.scene.objects:raise ValueError('Armature must belong to the current scene')
    if len(rig.data.bones)>512:raise ValueError('Rest refinement supports at most 512 bones')
    if edit and rig.data.override_library:raise ValueError('Local non-overridden armature data required')
    bpy.context.view_layer.update();rows={b.name:rest_row(b) for b in rig.data.bones};effects=impact(rig)
    inputs={'name':rig.name,'data':rig.data.name,'pose_position':rig.data.pose_position,
            'bones':[row|{'matrix':[list(r) for r in rig.data.bones[name].matrix_local]} for name,row in rows.items()],
            'users':effects['data_users'],'skin_bindings':effects['skin_bindings'],'attachments':effects['bone_attachments'],
            'constraint_consumers':effects['constraint_consumers']}
    signature=hashlib.sha256(json.dumps(inputs,sort_keys=True,allow_nan=False).encode()).hexdigest()
    return rig,rows,effects,signature


def inspect(p):
    rig,rows,effects,signature=inventory(p)
    offset,limit=p.get('offset',0),p.get('limit',128);bones=list(rows.values())
    blockers=[]
    if rig.library or rig.override_library or rig.data.library or rig.data.override_library:blockers.append('Linked/overridden editing requires a local asset')
    if rig.data.animation_data and (rig.data.animation_data.action or rig.data.animation_data.drivers or rig.data.animation_data.nla_tracks):blockers.append('Armature-data animation is inspect-only')
    if not rig.visible_get() or rig.hide_select or rig.hide_viewport:blockers.append('Visible selectable rig required for native edit mode')
    return {'name':rig.name,'data':rig.data.name,'rest_sha256':signature,'total_bones':len(bones),
            'bones':bones[offset:offset+limit],'next_offset':offset+limit if offset+limit<len(bones) else None,
            'impact':effects,'edit_blockers':blockers,
            'note':'Guard covers rest geometry/inheritance and binding/attachment inventory, not animation keys, weights or arbitrary external dependencies. Existing channels/weights retain their values; changed rest axes/hierarchy can change evaluated motion.'}


def write_plan(data,planned,ordered,roll_names,progress=True):
    from .bridge import check_cancelled,report_progress
    # Disconnect before assigning coordinates, so native connected-joint setters
    # cannot silently move another planned bone during the transaction.
    for b in data.edit_bones:b.use_connect=False
    for name in ordered:
        if name not in data.edit_bones:
            created=data.edit_bones.new(name)
            if created.name!=name:raise ValueError('Native bone name changed unexpectedly')
    for name in ordered:
        b=data.edit_bones[name];row=planned[name]
        b.parent=data.edit_bones[row['parent']] if row['parent'] else None
        b.head=row['head'];b.tail=row['tail']
        if name in roll_names:b.roll=math.radians(row['roll_degrees'])
        for key,field in FIELDS.items():setattr(b,field,row[key])
    for i,name in enumerate(ordered):
        data.edit_bones[name].use_connect=planned[name]['connected']
        if progress and i%32==0:
            check_cancelled()
            report_progress({'phase':'editing rest hierarchy','bones':i+1,'total_bones':len(ordered),'fraction':.5*(i+1)/max(len(ordered),1)})


def verify(rig,planned):
    for name,row in planned.items():
        b=rig.data.bones.get(name)
        if b is None:raise ValueError('Native bone name changed unexpectedly')
        if any(not math.isfinite(v) for r in b.matrix_local for v in r):raise ValueError('Native rest matrix is nonfinite')
        if any(abs(v-w)>1e-5 for key,co in (('head',b.head_local),('tail',b.tail_local)) for v,w in zip(row[key],co)):raise ValueError('Native rest coordinates differ from the plan')
        if (b.parent.name if b.parent else None)!=row['parent'] or b.use_connect!=row['connected']:raise ValueError('Native hierarchy differs from the plan')
        if any(getattr(b,field)!=row[key] for key,field in FIELDS.items()):raise ValueError('Native inheritance differs from the plan')
        expected=bpy.types.Bone.MatrixFromAxisRoll((b.tail_local-b.head_local).normalized(),math.radians(row['roll_degrees']))
        if max(abs(a-c) for ra,rc in zip(expected,b.matrix_local.to_3x3()) for a,c in zip(ra,rc))>2e-5:raise ValueError('Native rest roll differs from the plan')


def edit(p):
    from .bridge import check_cancelled,report_progress
    rig,rows,effects,signature=inventory(p,True)
    if p['expected_rest']!=signature:raise ValueError('Rest fingerprint is stale; inspect_armature_rest again')
    info=inspect(p)
    if info['edit_blockers']:raise ValueError('; '.join(info['edit_blockers']))
    if len(effects['data_users'])>1 and not p['make_single_user']:raise ValueError('Armature data is shared; make_single_user=true explicitly isolates it')
    if effects['deformation_change_acknowledgement_required'] and not p['allow_deformation_change']:raise ValueError('Rest edits affect bindings/animation/attachments; allow_deformation_change=true explicitly accepts changed deformation')
    patches=[{k:v for k,v in row.items() if v is not None} for row in p['bones']]
    planned,ordered=plan_rest(rows,patches,p['add_bones']);new_names={r['name'] for r in p['add_bones']}
    roll_names=new_names|{r['name'] for r in patches if 'roll_degrees' in r}
    old_data=rig.data;copy=None;snapshot=None;success=False
    selected={b.name:{k:getattr(b,k) for k in ('select','select_head','select_tail') if hasattr(b,k)} for b in rig.data.bones}
    pose_selected={b.name:b.select for b in rig.pose.bones if hasattr(b,'select')}
    active=rig.data.bones.active.name if rig.data.bones.active else None
    try:
        check_cancelled()
        if len(effects['data_users'])>1:copy=old_data.copy();rig.data=copy
        with active_object(rig):
            try:
                finished(bpy.ops.object.mode_set(mode='EDIT'))
                snapshot={b.name:rest_row(b,True) for b in rig.data.edit_bones}
                # Plan again with exact native rolls, rather than decomposed read
                # values; unedited rolls retain their original float values.
                planned,ordered=plan_rest(snapshot,patches,p['add_bones'])
                write_plan(rig.data,planned,ordered,roll_names)
                finished(bpy.ops.object.mode_set(mode='OBJECT'))
                for name in new_names:rig.pose.bones[name].rotation_mode='XYZ'
                rig.update_tag();bpy.context.view_layer.update();verify(rig,planned);check_cancelled()
                report_progress({'phase':'verified rest hierarchy','bones':len(ordered),'fraction':1})
                success=True
            finally:
                if not success and snapshot is not None:
                    if rig.mode!='EDIT':finished(bpy.ops.object.mode_set(mode='EDIT'))
                    for b in list(rig.data.edit_bones):
                        if b.name not in snapshot:rig.data.edit_bones.remove(b)
                    restored,order=plan_rest(snapshot,[],[])
                    write_plan(rig.data,restored,order,set(restored),progress=False)
                    finished(bpy.ops.object.mode_set(mode='OBJECT'))
                    rig.update_tag();bpy.context.view_layer.update()
    finally:
        if not success and copy:
            rig.data=old_data;bpy.data.armatures.remove(copy);rig.update_tag();bpy.context.view_layer.update()
        if rig.mode=='OBJECT':
            for b in rig.data.bones:
                for key,value in selected.get(b.name,{}).items():setattr(b,key,value)
            for b in rig.pose.bones:
                if b.name in pose_selected:b.select=pose_selected[b.name]
            rig.data.bones.active=rig.data.bones.get(active) if active else None
    result=inspect(p)
    return result|{'added_bones':sorted(new_names),'patched_bones':[b['name'] for b in patches],
                  'followed_connected_heads':sorted(n for n,r in planned.items() if n in rows and r['head']!=rows[n]['head'] and n not in {b['name'] for b in patches if 'head' in b}),
                  'isolated_armature_data':copy is not None,'retained_animation_and_weight_values':True}


def dispatch(command,p):return inspect(p) if command=='inspect_armature_rest' else edit(p)
