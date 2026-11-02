"""In-place, version-guarded deform weights with planned edits and rollback."""
from array import array
import hashlib
import json
import math
import struct

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

from .assets import mesh_object
from .rigging import armature_object
from .morphs import topology_digest
from mcpblender.skin_math import clean_weights

COMMANDS={'inspect_skin_weights','set_skin_weights','repair_skin_weights','smooth_skin_weights','mirror_skin_weights','configure_skin_binding'}


def inventory(p,edit=False):
    mesh=mesh_object(p['name'],edit=edit)
    if mesh.name not in bpy.context.scene.objects:raise ValueError('Skin mesh must belong to the current scene')
    if edit and mesh.data.override_library:raise ValueError('Local non-overridden mesh data required')
    mods=[m for m in mesh.modifiers if m.type=='ARMATURE']
    if len(mods)!=1 or not mods[0].object:raise ValueError('Skin tools require exactly one armature modifier with a rig')
    mod=mods[0];rig=armature_object(p.get('armature') or mod.object.name)
    if mod.object!=rig:raise ValueError('Named armature does not match the skin binding')
    if rig.name not in bpy.context.scene.objects:raise ValueError('Skin armature must belong to the current scene')
    if len(mesh.data.vertices)>200000 or len(mesh.vertex_groups)>2048 or len(rig.data.bones)>512:raise ValueError('Skin limits: 200000 vertices, 2048 groups, 512 bones')
    bpy.context.view_layer.update();groups={g.index:g.name for g in mesh.vertex_groups};deform={b.name for b in rig.data.bones if b.use_deform}
    if not deform:raise ValueError('Skin rig has no deform bones')
    locked={g.name for g in mesh.vertex_groups if g.lock_weight};rows=[];members=0
    for v in mesh.data.vertices:
        members+=len(v.groups)
        if members>2000000:raise ValueError('Skin inspection supports two million memberships')
        rows.append({groups[g.group]:g.weight for g in v.groups})
    basis=mesh.data.shape_keys.reference_key.data if mesh.data.shape_keys else mesh.data.vertices
    if len(basis)!=len(rows):raise ValueError('Shape basis topology does not match skin vertices')
    coordinates=array('f',[0])*(len(rows)*3);basis.foreach_get('co',coordinates)
    try:relative=rig.matrix_world.inverted()@mesh.matrix_world
    except ValueError:raise ValueError('Skin inspection requires an invertible rig world transform') from None
    binding={k:getattr(mod,k) for k in ('use_vertex_groups','use_bone_envelopes','use_deform_preserve_volume','vertex_group','invert_vertex_group','show_viewport','show_render')}
    h=hashlib.sha256();h.update(json.dumps({'mesh':mesh.name,'data':mesh.data.name,'rig':rig.name,
        'groups':[(g.name,g.lock_weight) for g in mesh.vertex_groups],
        'bones':[(b.name,b.use_deform,list(b.head_local),list(b.tail_local),[list(r) for r in b.matrix_local]) for b in rig.data.bones],
        'topology':topology_digest(mesh.data),'relative':[list(r) for r in relative],'binding':binding},sort_keys=True,allow_nan=False).encode())
    h.update(coordinates.tobytes())
    for row in rows:
        for name,value in sorted(row.items()):h.update(name.encode());h.update(b'\0');h.update(struct.pack('!d',value))
        h.update(b'\xff')
    return mesh,rig,mod,rows,deform,locked,coordinates,relative,binding,h.hexdigest()


def inspect(p):
    mesh,rig,mod,rows,deform,locked,coords,relative,binding,signature=inventory(p)
    counts={'unweighted':0,'unnormalized':0,'over_limit':0,'invalid':0};records=[];maximum=0;nondeform={g.name for g in mesh.vertex_groups}-deform
    for index,row in enumerate(rows):
        weights={n:v for n,v in row.items() if n in deform};positive={n:v for n,v in weights.items() if math.isfinite(v) and v>0};total=sum(positive.values())
        issues=[]
        if total<=1e-8:issues.append('unweighted')
        elif abs(total-1)>1e-4:issues.append('unnormalized')
        if len(positive)>p.get('max_influences',4):issues.append('over_limit')
        if any(not math.isfinite(v) or not 0<=v<=1 for v in weights.values()):issues.append('invalid')
        for issue in issues:counts[issue]+=1
        maximum=max(maximum,len(positive))
        if not p.get('issues_only',False) or issues:
            records.append({'vertex':index,'weights':{n:v if math.isfinite(v) else None for n,v in weights.items()},'weight_sum':total,'influences':len(positive),'issues':issues,
                            'nondeform_weights':{n:v if math.isfinite(v) else None for n,v in row.items() if n in nondeform}})
    offset,limit=p.get('offset',0),p.get('limit',32)
    return {'name':mesh.name,'armature':rig.name,'vertices':len(rows),'weights_sha256':signature,'issues':counts,'max_influences':maximum,
            'locked_groups':sorted(locked),'deform_bones':sorted(deform),'nondeform_groups':sorted(nondeform),
            'binding':binding,'shared_mesh_users':mesh.data.users,'total_matching_vertices':len(records),
            'vertex_samples':records[offset:offset+limit],'next_offset':offset+limit if offset+limit<len(records) else None,
            'coordinates':'Raw basis vertex indices; nearest/mirror armature space uses the current mesh-to-rig transform and rig rest segments'}


def fallback_for(p,rig,locked,point):
    policy=p.get('unweighted','ERROR')
    if policy=='FALLBACK':
        name=p['fallback_bone']
        if name not in rig.data.bones or not rig.data.bones[name].use_deform or name in locked:raise ValueError('Fallback must be an unlocked deform bone')
        return name
    if policy=='NEAREST':
        best=None
        for bone in rig.data.bones:
            if not bone.use_deform or bone.name in locked:continue
            a,b=bone.head_local,bone.tail_local;segment=b-a;t=max(0,min(1,(point-a).dot(segment)/max(segment.length_squared,1e-30)))
            candidate=((point-(a+segment*t)).length_squared,bone.name)
            if best is None or candidate<best:best=candidate
        if best is None:raise ValueError('No unlocked deform bone for nearest repair')
        return best[1]
    return None


def apply(mesh,rig,rows,deform,locked,changes,p):
    from .bridge import check_cancelled,report_progress
    if mesh.data.users>1 and not p['make_single_user']:raise ValueError('Mesh data is shared; make_single_user=true explicitly isolates it')
    missing=sorted({n for row in changes.values() for n in row}-set(mesh.vertex_groups.keys()))
    if len(mesh.vertex_groups)+len(missing)>2048:raise ValueError('New group count exceeds skin limit')
    old_data=mesh.data;new_data=None;created=[];touched=[];success=False;editable=[]
    # Complete the plan before writing any memberships. A shared-data copy is
    # explicit; ordinary edits retain mesh/shape IDs and their external references.
    try:
        check_cancelled()
        if old_data.users>1:new_data=old_data.copy();mesh.data=new_data
        for name in missing:
            group=mesh.vertex_groups.new(name=name);created.append(group.name)
            if group.name!=name:raise ValueError('Native group name changed unexpectedly')
        editable=[g for g in mesh.vertex_groups if g.name in deform and g.name not in locked]
        for index,(vertex,weights) in enumerate(changes.items()):
            if index%128==0:check_cancelled()
            touched.append(vertex)
            for group in editable:
                if group.name in rows[vertex]:group.remove([vertex])
            for name,value in weights.items():
                if name not in locked and value>0:mesh.vertex_groups[name].add([vertex],value,'REPLACE')
            if index%128==0:report_progress({'phase':'applying skin weights','vertices':index+1,'total_vertices':len(changes),'fraction':.5+.5*(index+1)/max(len(changes),1)})
        mesh.data.update();mesh.update_tag();bpy.context.view_layer.update();check_cancelled();success=True
    finally:
        if not success:
            if new_data:
                mesh.data=old_data;bpy.data.meshes.remove(new_data)
            else:
                for i,vertex in enumerate(reversed(touched)):
                    for group in editable:
                        if group.name in deform:group.remove([vertex])
                    for name,value in rows[vertex].items():
                        if name in deform and name not in locked:mesh.vertex_groups[name].add([vertex],value,'REPLACE')
                    if i%128==0:report_progress({'phase':'rolling back skin weights','vertices':i+1,'total_vertices':len(touched)})
                for name in reversed(created):mesh.vertex_groups.remove(mesh.vertex_groups[name])
            mesh.data.update();mesh.update_tag();bpy.context.view_layer.update()
    return {'changed_vertices':len(changes),'isolated_mesh_data':new_data is not None}


def edit(command,p):
    from .bridge import check_cancelled,report_progress
    mesh,rig,mod,rows,deform,locks,coords,relative,binding,signature=inventory(p,True)
    if signature!=p['expected_weights']:raise ValueError('Weight fingerprint is stale; inspect_skin_weights again')
    if command=='configure_skin_binding':
        if p['vertex_group'] and p['vertex_group'] not in mesh.vertex_groups:raise ValueError('Binding mask group not found')
        values={'use_vertex_groups':p['use_vertex_groups'],'use_bone_envelopes':p['use_bone_envelopes'],'use_deform_preserve_volume':p['preserve_volume'],
                'vertex_group':p['vertex_group'],'invert_vertex_group':p['invert_vertex_group']}
        try:
            check_cancelled()
            for k,v in values.items():setattr(mod,k,v)
            mesh.update_tag();bpy.context.view_layer.update();check_cancelled()
        except Exception:
            for k in values:setattr(mod,k,binding[k])
            mesh.update_tag();bpy.context.view_layer.update()
            raise
        mesh.update_tag();bpy.context.view_layer.update();return inspect(p)
    if not mod.use_vertex_groups:raise ValueError('Enable vertex-group skin binding before editing weights')
    if mesh.data.users>1 and not p['make_single_user']:raise ValueError('Mesh data is shared; make_single_user=true explicitly isolates it')
    locked=locks if p['respect_locks'] else set()
    if p.get('unweighted')=='FALLBACK':fallback_for(p,rig,locked,None)
    selected=p.get('vertices') or list(range(len(rows)));changes={}
    if any(v>=len(rows) for v in selected):raise ValueError('Selected raw vertex is out of range')
    def point(index,armature=True):
        value=Vector(coords[index*3:index*3+3]);value=relative@value if armature else value
        if not all(math.isfinite(v) for v in value):raise ValueError('Spatial skin repair requires finite basis coordinates')
        return value
    def clean(vertex,weights):
        fallback=(lambda:fallback_for(p,rig,locked,point(vertex))) if p.get('unweighted') in {'FALLBACK','NEAREST'} else None
        return clean_weights(weights,locked,p.get('threshold',0),p.get('max_influences'),p.get('normalize',True),p.get('unweighted','ERROR'),fallback)
    if command=='set_skin_weights':
        for entry in p['weights']:
            vertex=entry['vertex']
            if vertex>=len(rows) or set(entry['weights'])-deform:raise ValueError('Explicit weights reference an unknown raw vertex or deform bone')
            if any(n in locked and abs(v-rows[vertex].get(n,0))>1e-6 for n,v in entry['weights'].items()):raise ValueError('Explicit edit targets a locked bone group')
            values={n:v for n,v in rows[vertex].items() if n in locked and n in deform}|{n:v for n,v in entry['weights'].items() if n not in locked}
            changes[vertex]=clean_weights(values,locked,normalize=p['normalize'],unweighted='KEEP' if p['allow_unweighted'] else 'ERROR')
    elif command=='repair_skin_weights':
        for i,vertex in enumerate(selected):
            if i%128==0:check_cancelled();report_progress({'phase':'planning skin repair','vertices':i,'total_vertices':len(selected),'fraction':.5*i/max(len(selected),1)})
            changes[vertex]=clean(vertex,{n:v for n,v in rows[vertex].items() if n in deform})
    elif command=='smooth_skin_weights':
        if len(selected)*p['iterations']>2000000:raise ValueError('Smoothing supports two million selected vertex-iterations')
        adjacency=[set() for _ in rows]
        for edge in mesh.data.edges:a,b=edge.vertices;adjacency[a].add(b);adjacency[b].add(a)
        current=[{n:v for n,v in row.items() if n in deform} for row in rows]
        for iteration in range(p['iterations']):
            update={}
            for i,vertex in enumerate(selected):
                if i%128==0:check_cancelled();report_progress({'phase':'planning skin smoothing','iteration':iteration+1,'vertices':i,'fraction':.5*(iteration+i/max(len(selected),1))/p['iterations']})
                neighbors=adjacency[vertex];values=dict(current[vertex])
                if neighbors:
                    averaged={}
                    for neighbor in neighbors:
                        for name,value in current[neighbor].items():averaged[name]=averaged.get(name,0)+value/len(neighbors)
                    values={name:(1-p['strength'])*current[vertex].get(name,0)+p['strength']*averaged.get(name,0) for name in set(values)|set(averaged)}
                for name in locked:
                    values.pop(name,None)
                    if name in current[vertex]:values[name]=current[vertex][name]
                update[vertex]=clean(vertex,values)
            for vertex,values in update.items():current[vertex]=values
        changes={v:current[v] for v in selected}
    else:
        axis='XYZ'.index(p['axis']);plane=p['plane'];tolerance=p['tolerance'];armature=p['space']=='ARMATURE'
        pairs={}
        for pair in p['bone_pairs']:
            if {pair['left'],pair['right']}-deform:raise ValueError('Mirror pair bones must be deform bones')
            pairs[pair['left']]=pair['right'];pairs[pair['right']]=pair['left']
        positions=[point(v,armature) for v in range(len(rows))];tree=KDTree(len(rows));sources=0
        for i,co in enumerate(positions):
            sign=co[axis]-plane
            if p['direction']=='SWAP' or (p['direction']=='POSITIVE_TO_NEGATIVE' and sign>tolerance) or (p['direction']=='NEGATIVE_TO_POSITIVE' and sign<-tolerance):tree.insert(co,i);sources+=1
        if not sources:raise ValueError('No vertices on mirror source side')
        tree.balance()
        for i,vertex in enumerate(selected):
            if i%128==0:check_cancelled();report_progress({'phase':'planning skin mirror','vertices':i,'fraction':.5*i/max(len(selected),1)})
            sign=positions[vertex][axis]-plane
            if abs(sign)<=tolerance or (p['direction']=='POSITIVE_TO_NEGATIVE' and sign>0) or (p['direction']=='NEGATIVE_TO_POSITIVE' and sign<0):continue
            reflected=positions[vertex].copy();reflected[axis]=2*plane-reflected[axis]
            matches=sorted(tree.find_range(reflected,tolerance),key=lambda m:(m[2],m[1]))
            if not matches:raise ValueError('Mirror target has no source within tolerance')
            if len(matches)>256:raise ValueError('Mirror match exceeds 256 candidates; reduce tolerance or resolve coincident vertices')
            candidates=[]
            for _,source,distance in matches:
                if distance>matches[0][2]+1e-7:break
                values={pairs.get(n,n):v for n,v in rows[source].items() if n in deform}
                candidates.append(values)
            if any(set(c)!=set(candidates[0]) or any(abs(c[n]-candidates[0][n])>1e-6 for n in c) for c in candidates[1:]):raise ValueError('Mirror source match is ambiguous with different weights')
            values={n:v for n,v in candidates[0].items() if n not in locked}|{n:v for n,v in rows[vertex].items() if n in locked and n in deform}
            changes[vertex]=clean(vertex,values)
    # Avoid rewriting untouched rows and preserve zero-valued memberships unless
    # the requested operation actually changes that row.
    changes={v:w for v,w in changes.items() if w!={n:value for n,value in rows[v].items() if n in deform}}
    result=apply(mesh,rig,rows,deform,locked,changes,p)
    return inspect(p)|result


def dispatch(command,p):return inspect(p) if command=='inspect_skin_weights' else edit(command,p)
