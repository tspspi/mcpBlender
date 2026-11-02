"""Closed native asset graphs, source-preserving prototypes and shared instances."""
import json
import hashlib
import struct
import math
from pathlib import Path
import tempfile
import uuid

import bpy
from mathutils import Vector

from . import lods
from .assets import local_object
from .simulations import props
from .drivers import native_record
from .nla import source as action_record
from .mesh_edit import geometry_digest
from mcpblender.storage import require_space,snapshot

COMMANDS={'inspect_asset_assembly_source','create_asset_assembly','inspect_asset_assembly','place_asset_instance','set_asset_assembly_editing','inspect_asset_instance','remove_asset_instance'}
META='mcpblender_asset_assembly';INSTANCE='mcpblender_asset_instance';MARKER='mcpblender-asset-assembly-v1'


def metadata(collection):
    text=collection.get(META)
    if not isinstance(text,str) or len(text)>1024**2:raise ValueError('Managed asset assembly not found')
    value=json.loads(text)
    if not isinstance(value,dict) or value.get('format')!=MARKER or not isinstance(value.get('id'),str) or len(value['id'])!=32 or any(c not in '0123456789abcdef' for c in value['id']):raise ValueError('Invalid assembly ownership marker')
    members=value.get('members')
    if not isinstance(members,list) or not 1<=len(members)<=128 or not all(isinstance(n,str) and n for n in members) or len(set(members))!=len(members):raise ValueError('Invalid assembly member inventory')
    actions=value.get('actions',[])
    if not isinstance(actions,list) or not all(isinstance(n,str) and n for n in actions) or len(set(actions))!=len(actions):raise ValueError('Invalid assembly action inventory')
    return value


def references():
    result={}
    for ref,users in bpy.data.user_map().items():
        for user in users:result.setdefault(user,set()).add(ref)
    return result


def dependencies(roots,refs,*,nested_leaf=True):
    visited=set();pending=list(roots);nested=set();blockers=[]
    while pending:
        current=pending.pop()
        if current in visited:continue
        visited.add(current)
        if len(visited)>20000:raise ValueError('Asset dependency graph exceeds 20000 datablocks')
        if isinstance(current,(bpy.types.Scene,bpy.types.World)):
            blockers.append('Scene/world context dependency: '+current.name);continue
        if isinstance(current,bpy.types.Collection) and nested_leaf:
            if current.get(META):metadata(current);nested.add(current)
            else:blockers.append('Collection dependency is not a managed prototype: '+current.name)
            continue
        pending.extend(refs.get(current,()))
    return visited,nested,blockers


def managed_actions(objects):
    names={o.name for o in objects};result=set()
    for action in bpy.data.actions:
        try:targets=json.loads(action.get('mcpblender_morph_targets','{}'))
        except (ValueError,TypeError):targets={}
        if not isinstance(targets,dict):targets={}
        target=action.get('mcpblender_target')
        if (isinstance(target,str) and target in names) or names.intersection(targets):result.add(action)
    return result


def animation(block):
    from .nla import strip_record
    anim=block.animation_data
    if not anim:return None
    cache={}
    return {'action':action_record(anim.action,getattr(anim,'action_slot',None),cache),
            'settings':{k:getattr(anim,k) for k in ('action_blend_type','action_extrapolation','action_influence','use_nla','use_tweak_mode')},
            'drivers':[native_record(c) for c in anim.drivers],
            'tracks':[(t.name,t.mute,t.is_solo,[strip_record(s,cache) for s in t.strips]) for t in anim.nla_tracks]}


def custom(value):
    if isinstance(value,bpy.types.ID):return {'type':type(value).__name__,'name':value.name}
    if value is None or isinstance(value,(str,int,float,bool)):return value
    if hasattr(value,'items'):return {k:custom(v) for k,v in value.items()}
    return [custom(v) for v in value]


def idprops(value):
    try:return custom(dict(value.items()))
    except (TypeError,AttributeError):return {}


def pointers(value):
    return {p.identifier:getattr(value,p.identifier).name for p in value.bl_rna.properties if p.type=='POINTER' and isinstance(getattr(value,p.identifier,None),bpy.types.ID)}



def attribute_records(mesh):
    numeric=[a for a in mesh.attributes if a.data_type!='STRING']
    records=[]
    # Reuse the numeric reader per attribute through its same native RNA layout.
    for attr in numeric:
        item=attr.data[0] if attr.data else None
        prop=next((item.bl_rna.properties.get(k) for k in ('value','vector','color') if item.bl_rna.properties.get(k)),None) if item else None
        row={'name':attr.name,'domain':attr.domain,'type':attr.data_type,'count':len(attr.data)}
        if item:
            if not prop or prop.type not in {'FLOAT','INT','BOOLEAN'}:raise ValueError('Unsupported assembly attribute layout: '+attr.data_type)
            row['sha256']=lods.packed(attr.data,prop.identifier,len(attr.data)*(prop.array_length if prop.is_array else 1),'f' if prop.type=='FLOAT' else 'i')
        records.append(row)
    for attr in mesh.attributes:
        if attr.data_type=='STRING':
            h=hashlib.sha256()
            for item in attr.data:
                value=item.value;encoded=value.encode() if isinstance(value,str) else bytes(value);h.update(struct.pack('!I',len(encoded)));h.update(encoded)
            records.append({'name':attr.name,'domain':attr.domain,'type':attr.data_type,'count':len(attr.data),'sha256':h.hexdigest()})
    return records

def record(block):
    result={'type':type(block).__name__,'name':block.name,'properties':props(block),'custom':custom(dict(block.items()))}
    if getattr(block,'node_tree',None):result['node_tree']=record(block.node_tree)
    if hasattr(block,'animation_data'):result['animation']=animation(block)
    if isinstance(block,bpy.types.Object):
        result.update(matrix=lods.matrix(block.matrix_world),parent=block.parent.name if block.parent else None,
                      parent_inverse=lods.matrix(block.matrix_parent_inverse),parent_bone=block.parent_bone,
                      constraints=[(c.name,props(c),pointers(c),idprops(c)) for c in block.constraints],modifiers=[(m.name,props(m),pointers(m),idprops(m)) for m in block.modifiers])
        if block.type=='MESH':
            result['vertex_groups']=[(g.name,g.index,g.lock_weight) for g in block.vertex_groups]
            result['material_slots']=[(s.link,s.material.name if s.material else None) for s in block.material_slots]
        for field in ('rigid_body','rigid_body_constraint','collision','field','soft_body'):
            settings=getattr(block,field,None)
            if settings:result[field]=(props(settings),pointers(settings))
        if block.type=='ARMATURE':result['pose']=[(b.name,lods.matrix(b.matrix),props(b),custom(dict(b.items())),[(c.name,props(c),pointers(c),idprops(c)) for c in b.constraints]) for b in block.pose.bones]
    elif isinstance(block,bpy.types.Mesh):
        if len(block.vertices)>2000000:raise ValueError('Assembly mesh exceeds two million raw vertices')
        result['geometry']=geometry_digest(block);result['attributes']=attribute_records(block)
        result['materials']=[m.name if m else None for m in block.materials]
        result['material_indices']=lods.packed(block.polygons,'material_index',len(block.polygons),'i')
        h=hashlib.sha256();members=0
        for v in block.vertices:
            for g in v.groups:
                members+=1
                if members>2000000:raise ValueError('Assembly mesh exceeds two million group memberships')
                h.update(struct.pack('!IId',v.index,g.group,g.weight))
        result['deform_sha256']=h.hexdigest()
    elif isinstance(block,bpy.types.Key):
        if sum(len(b.data) for b in block.key_blocks)>4000000:raise ValueError('Assembly shape data exceeds four million entries')
        result['shapes']=[(b.name,b.relative_key.name,b.value,b.mute,b.vertex_group,props(b),lods.packed(b.data,'co',len(b.data)*3)) for b in block.key_blocks]
    elif isinstance(block,bpy.types.Action):
        from .domains import curves
        if sum(len(c.keyframe_points)+len(c.sampled_points) for slot in (list(block.slots) or [None]) for c in curves(block,slot))>200000:raise ValueError('Assembly action exceeds 200000 key/sample points')
        result['slots']=[action_record(block,s,{}) for s in (list(block.slots) or [None])]
    elif isinstance(block,bpy.types.Armature):result['bones']=[(b.name,b.parent.name if b.parent else None,lods.matrix(b.matrix_local),props(b),custom(dict(b.items()))) for b in block.bones]
    elif isinstance(block,bpy.types.NodeTree):
        result['nodes']=[(n.name,n.bl_idname,props(n),pointers(n),[(s.identifier,custom(s.default_value)) for s in n.inputs if hasattr(s,'default_value')]) for n in block.nodes]
        result['links']=[(l.from_node.name,l.from_socket.identifier,l.to_node.name,l.to_socket.identifier) for l in block.links]
    return result


def graph(objects,extras=(),trail=()):
    refs=references();data,nested,issues=dependencies(set(objects)|set(extras),refs)
    external={d for d in data if isinstance(d,bpy.types.Object)}-set(objects)
    issues.extend('Object dependency must be included: '+o.name for o in sorted(external,key=lambda o:o.name))
    if any(d.library or d.override_library for d in data if not isinstance(d,bpy.types.Library)):issues.append('Assembly graph must be local and non-overridden')
    nested_records=[]
    for collection in sorted(nested,key=lambda c:c.name):
        value=inspect_asset({'collection':collection.name},trail)
        if not value['valid']:issues.append('Nested assembly is invalid: '+collection.name)
        nested_records.append({'collection':collection.name,'assembly_sha256':value['assembly_sha256']})
    for d in data:
        anim=getattr(d,'animation_data',None)
        if anim and any(c.driver.type=='SCRIPTED' and not c.driver.is_simple_expression for c in anim.drivers):issues.append('Non-simple Python driver cannot be audited as a closed asset: '+d.name)
    records=[record(d) for d in sorted(data,key=lambda d:(type(d).__name__,d.name)) if not isinstance(d,(bpy.types.Collection,bpy.types.Library,bpy.types.Scene,bpy.types.World))]
    edges=sorted((type(user).__name__,user.name,type(ref).__name__,ref.name) for user in data for ref in refs.get(user,()) if ref in data)
    digest=lods.digest({'records':records,'references':edges,'nested':nested_records,'frame':bpy.context.scene.frame_current+bpy.context.scene.frame_subframe})
    return data,nested,sorted(set(issues)),digest


def source_bounds(objects):
    points=[];deps=bpy.context.evaluated_depsgraph_get();targets=set(objects)
    for item in deps.object_instances:
        original=item.object.original
        if original.type!='MESH' or (item.parent.original not in targets if item.is_instance and item.parent else original not in targets):continue
        if not item.show_self or not item.object.data.vertices:continue
        points.extend(item.matrix_world@Vector(corner) for corner in item.object.bound_box)
    if not points:return None
    if any(not math.isfinite(x) for p in points for x in p):raise ValueError('Nonfinite assembly bounds')
    return {key:[fn(p[a] for p in points) for a in range(3)] for key,fn in (('min',min),('max',max))}


def source(p):
    if bpy.context.mode!='OBJECT':raise ValueError('Object mode required for assembly sources')
    objects=[local_object(name) for name in p['objects']];actions=managed_actions(objects)
    bpy.context.view_layer.update()
    all_data,_,_=dependencies(set(objects)|actions,references(),nested_leaf=False)
    from .domains import curves
    shape_entries=sum(len(b.data) for d in all_data if isinstance(d,bpy.types.Key) for b in d.key_blocks)
    curve_points=sum(len(c.keyframe_points)+len(c.sampled_points) for d in all_data if isinstance(d,bpy.types.Action) for slot in (list(d.slots) or [None]) for c in curves(d,slot))
    if shape_entries>4000000 or curve_points>2000000:raise ValueError('Assembly transfer exceeds four million shape entries or two million curve points')
    data,nested,issues,signature=graph(objects,actions)
    estimate=16*1024**2+shape_entries*24+curve_points*128
    vertices=sum(len(d.vertices) for d in all_data if isinstance(d,bpy.types.Mesh))
    if vertices>2000000:issues.append('Assembly source exceeds two million unique raw mesh vertices')
    estimate+=vertices*192+sum(max(1024,d.size[0]*d.size[1]*16) for d in all_data if isinstance(d,bpy.types.Image))
    return objects,actions,{'can_create':not issues,'blockers':issues,'source_sha256':signature,'objects':[o.name for o in objects],
                            'dependencies':[{'type':type(d).__name__,'name':d.name} for d in sorted(data,key=lambda d:(type(d).__name__,d.name))][p.get('dependency_offset',0):p.get('dependency_offset',0)+p.get('dependency_limit',100)],'total_dependencies':len(data),
                            'next_dependency_offset':p.get('dependency_offset',0)+p.get('dependency_limit',100) if p.get('dependency_offset',0)+p.get('dependency_limit',100)<len(data) else None,
                            'nested_assemblies':[c.name for c in sorted(nested,key=lambda c:c.name)],'bounds':source_bounds(objects),'estimated_transfer_bytes':estimate,
                            'scope':'Known current object/data/action/reference state. Image pixel buffers, external files and arbitrary Python dependencies are not frozen.'}


def _inspect_asset(p,trail=()):
    collection=bpy.data.collections.get(p['collection'])
    if collection is None:raise ValueError('Assembly collection not found')
    meta=metadata(collection)
    if meta['id'] in trail or len(trail)>=8:raise ValueError('Assembly dependency cycle or depth exceeds eight')
    objects=list(collection.objects);issues=[]
    if set(o.name for o in objects)!=set(meta['members']) or collection.children:issues.append('Assembly membership/hierarchy changed')
    if not collection.use_fake_user:issues.append('Prototype persistence flag changed')
    if len(objects)>128:issues.append('Assembly exceeds 128 direct members')
    actions=[bpy.data.actions.get(n) for n in meta.get('actions',[])]
    if any(a is None for a in actions):issues.append('Assembly clip is missing')
    data,nested,other,signature=graph(objects,[a for a in actions if a],trail+ (meta['id'],));issues.extend(other)
    signature=lods.digest({'metadata':meta,'graph':signature,'offset':list(collection.instance_offset),'issues':issues})
    return {'collection':collection.name,'id':meta['id'],'valid':not issues,'issues':sorted(set(issues)),'assembly_sha256':signature,
            'origin':list(collection.instance_offset),'members':[{'name':o.name,'type':o.type,'data':o.data.name if o.data else None,'parent':o.parent.name if o.parent else None} for o in objects],
            'actions':[a.name for a in actions if a],'nested_assemblies':[c.name for c in sorted(nested,key=lambda c:c.name)],
            'editing':collection.name in bpy.context.scene.collection.children,
            'instances':[o.name for o in bpy.data.objects if o.instance_type=='COLLECTION' and o.instance_collection==collection][p.get('offset',0):p.get('offset',0)+p.get('limit',100)],
            'total_instances':sum(o.instance_type=='COLLECTION' and o.instance_collection==collection for o in bpy.data.objects),
            'scope':'Instances share this graph and active animation. Membership is owned; geometry/controls may be edited while linked for editing. Image pixel buffers and external files are not frozen.'}



def inspect_asset(p,trail=()):
    collection=bpy.data.collections.get(p['collection'])
    if collection is None:raise ValueError('Assembly collection not found')
    meta=metadata(collection)
    if meta['id'] in trail or len(trail)>=8:raise ValueError('Assembly dependency cycle or depth exceeds eight')
    children=bpy.context.scene.collection.children;temporary=collection.name not in children
    try:
        if temporary:children.link(collection)
        bpy.context.view_layer.update();result=_inspect_asset(p,trail)
    finally:
        if temporary and collection.name in children:children.unlink(collection)
        bpy.context.view_layer.update()
    result['editing']=not temporary
    return result

def adapt(objects,mapping,owned):
    from . import drivers,nla
    names={old.name:new.name for old,new in mapping.items()}
    for action in (d for d in owned if isinstance(d,bpy.types.Action)):
        if 'mcpblender_target' in action:
            target=action['mcpblender_target']
            if target in names:action['mcpblender_target']=names[target]
            else:del action['mcpblender_target']
        if 'mcpblender_morph_targets' in action:action['mcpblender_morph_targets']=json.dumps({names[n]:s for n,s in json.loads(action['mcpblender_morph_targets']).items() if n in names})
    for old,new in mapping.items():
        pairs=[(old,new)]+([(old.data.shape_keys,new.data.shape_keys)] if old.type=='MESH' and old.data.shape_keys else [])
        for original,block in pairs:
            if drivers.OWNED in block:
                value=json.loads(block[drivers.OWNED]);anim=block.animation_data
                for curve in anim.drivers if anim else []:
                    key=drivers.identity(curve.data_path,curve.array_index);entry=value.get(key)
                    old_curve=next((c for c in original.animation_data.drivers if c.data_path==curve.data_path and c.array_index==curve.array_index),None) if original.animation_data else None
                    if not entry or not old_curve or not drivers.owned(original,old_curve):continue
                    for variable in entry['settings']['variables']:
                        if variable.get('object') in names:variable['object']=names[variable['object']]
                    entry['native_sha256']=drivers.digest(drivers.native_record(curve))
                block[drivers.OWNED]=json.dumps(value)
            if nla.OWNED in block and block.animation_data and original.animation_data:
                value=json.loads(block[nla.OWNED])
                for track in block.animation_data.nla_tracks:
                    old_track=original.animation_data.nla_tracks.get(track.name)
                    for strip in track.strips:
                        entry=value.get(track.name,{}).get('strips',{}).get(strip.name)
                        old_strip=old_track.strips.get(strip.name) if old_track else None
                        if entry and old_strip and nla.supported(original,old_track,old_strip):
                            entry['settings']['clip']=strip.action.name;entry['settings']['slot']=strip.action_slot.identifier
                            entry['native_sha256']=nla.native_strip_hash(strip)
                block[nla.OWNED]=json.dumps(value)


def create(p):
    from .bridge import check_cancelled,report_progress,_bridge
    objects,extras,planned=source(p)
    if planned['source_sha256']!=p['expected_source']:raise ValueError('Assembly source fingerprint is stale; inspect source again')
    if planned['blockers']:raise ValueError('; '.join(planned['blockers']))
    if p['collection'] in bpy.data.collections:raise ValueError('Assembly collection already exists')
    if p['origin_mode']=='CUSTOM':origin=p['origin']
    elif p['origin_mode']=='WORLD_ORIGIN':origin=[0,0,0]
    else:
        bounds=planned['bounds']
        if not bounds:raise ValueError('Source has no evaluated mesh bounds; choose WORLD_ORIGIN or CUSTOM')
        origin=[(a+b)/2 for a,b in zip(bounds['min'],bounds['max'])]
        if p['origin_mode']=='BOUNDS_BOTTOM':origin[2]=bounds['min'][2]
    before=set(bpy.data.user_map());tag='mcp_assembly_source_'+uuid.uuid4().hex;tagged=[];success=False;collection=None
    policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {};estimate=planned['estimated_transfer_bytes']
    reserve=policy.get('reserve_bytes',256*1024**2);temp_root=tempfile.gettempdir()
    require_space(temp_root,estimate,reserve_bytes=reserve,estimate_kind='native_asset_transfer_heuristic')
    try:
        check_cancelled()
        with tempfile.TemporaryDirectory(prefix='mcpblender-assembly-') as folder:
            path=Path(folder)/'transfer.blend'
            try:
                for obj in objects:
                    if tag in obj:raise ValueError('Temporary source marker collision')
                    obj[tag]=obj.name;tagged.append(obj)
                report_progress({'phase':'serializing assembly graph','temporary_storage':snapshot(temp_root,estimate,reserve_bytes=reserve)})
                bpy.data.libraries.write(str(path),set(objects)|extras,path_remap='ABSOLUTE',fake_user=False,compress=True)
            finally:
                for obj in tagged:
                    if tag in obj:del obj[tag]
                tagged.clear()
            check_cancelled();report_progress({'phase':'appending independent assembly graph','temporary_storage':snapshot(temp_root,estimate,reserve_bytes=reserve)})
            with bpy.data.libraries.load(str(path),link=False) as (available,loaded):
                loaded.objects=[o.name for o in objects];loaded.actions=[a.name for a in extras]
        owned=set(bpy.data.user_map())-before;copies=loaded.objects;mapping={bpy.data.objects[o[tag]]:o for o in copies}
        if set(mapping)!=set(objects):raise ValueError('Native assembly object mapping differs from requested sources')
        for obj in copies:
            del obj[tag]

        # Appended copies of existing nested prototypes are not independent new
        # assets. Repoint only proven-owned users to the original shared prototype.
        originals={}
        for c in before:
            if isinstance(c,bpy.types.Collection) and c.get(META):
                try:originals.setdefault(metadata(c)['id'],[]).append(c)
                except ValueError:pass
        for item in [d for d in owned if isinstance(d,bpy.types.Collection) and d.get(META)]:
            identifier=metadata(item)['id']
            if len(originals.get(identifier,[]))!=1:raise ValueError('Unknown or ambiguous appended nested prototype')
            users=bpy.data.user_map(subset={item}).get(item,set())
            if not users<=owned:raise ValueError('Nested prototype remap would affect unowned data')
            item.user_remap(originals[identifier][0])
        for obj in copies:
            if obj.get(INSTANCE):obj[INSTANCE]=json.dumps({'id':uuid.uuid4().hex,'assembly_id':metadata(obj.instance_collection)['id']})
        adapt(copies,mapping,owned)
        collection=bpy.data.collections.new(p['collection']);collection.use_fake_user=True
        collection.instance_offset=origin
        for obj in copies:collection.objects.link(obj)
        top_data,_,_=dependencies(copies,references())
        actions=list({a for a in loaded.actions if a}|{d for d in top_data if isinstance(d,bpy.types.Action) and d in owned})
        for action in actions:action.use_fake_user=True
        keep,_,_=dependencies({collection,*actions},references(),nested_leaf=False)
        unused=(set(bpy.data.user_map())-before)-keep
        if unused:bpy.data.batch_remove(ids=tuple(unused))
        collection[META]=json.dumps({'format':MARKER,'id':uuid.uuid4().hex,'members':sorted(o.name for o in copies),'actions':sorted(a.name for a in actions),
                                     'source_objects':sorted(o.name for o in objects),'source_sha256':p['expected_source'],
                                     'source_frame':bpy.context.scene.frame_current+bpy.context.scene.frame_subframe},sort_keys=True)
        bpy.context.view_layer.update();check_cancelled();result=inspect_asset({'collection':collection.name})
        if not result['valid']:raise ValueError('Copied assembly is not closed: '+'; '.join(result['issues']))
        if source({'objects':[o.name for o in objects]})[2]['source_sha256']!=p['expected_source']:raise ValueError('Source graph changed during assembly transfer')
        report_progress({'phase':'verified assembly prototype','members':len(copies),'temporary_storage':snapshot(temp_root,0,reserve_bytes=reserve)})
        check_cancelled()
        result=result|{'copied_objects':{old.name:new.name for old,new in mapping.items()},
                       'temporary_storage':snapshot(temp_root,0,reserve_bytes=reserve)}
        success=True;return result
    finally:
        for obj in tagged:
            if tag in obj:del obj[tag]
        if not success:
            owned=set(bpy.data.user_map())-before
            if owned:bpy.data.batch_remove(ids=tuple(owned))


def guarded(p):
    result=inspect_asset(p)
    if result['assembly_sha256']!=p['expected_asset']:raise ValueError('Assembly fingerprint is stale; inspect asset again')
    if not result['valid']:raise ValueError('Assembly ownership/dependencies are invalid')
    return bpy.data.collections[p['collection']],result


def instance(p):
    obj=local_object(p['name']);text=obj.get(INSTANCE)
    if not isinstance(text,str):raise ValueError('Managed asset instance not found')
    meta=json.loads(text)
    if obj.instance_type!='COLLECTION' or not obj.instance_collection or metadata(obj.instance_collection)['id']!=meta.get('assembly_id'):raise ValueError('Instance prototype binding changed')
    if bpy.context.view_layer.objects.get(obj.name)!=obj:raise ValueError('Instance is outside the current view layer')
    asset=inspect_asset({'collection':obj.instance_collection.name})
    if not asset['valid']:raise ValueError('Instance prototype is invalid')
    bpy.context.view_layer.update();items=[];points=[];vertices=0
    for item in bpy.context.evaluated_depsgraph_get().object_instances:
        if not item.is_instance or not item.parent or item.parent.original!=obj:continue
        if len(items)>=2048:raise ValueError('Instance inspection supports 2048 evaluated leaf records')
        if item.object.type=='MESH' and item.show_self and item.object.data.vertices:
            vertices+=len(item.object.data.vertices)
            if vertices>2000000:raise ValueError('Instance inspection exceeds two million evaluated vertices')
            points.extend(item.matrix_world@Vector(corner) for corner in item.object.bound_box)
        items.append({'object':item.object.original.name,'type':item.object.type,'matrix_world':lods.matrix(item.matrix_world),
                      'persistent_id':[i for i in item.persistent_id if i!=2147483647]})
    bounds={key:[fn(p[a] for p in points) for a in range(3)] for key,fn in (('min',min),('max',max))} if points else None
    if points and any(not math.isfinite(v) for p in points for v in p):raise ValueError('Nonfinite instance bounds')
    signature=lods.digest({'id':meta,'object':record(obj),'prototype':asset['assembly_sha256'],'leaves':items,'collections':sorted(c.name for c in obj.users_collection)})
    return {'name':obj.name,'id':meta['id'],'collection':obj.instance_collection.name,'assembly_sha256':asset['assembly_sha256'],'instance_sha256':signature,
            'matrix_world':lods.matrix(obj.matrix_world),'world_bounds':bounds,'evaluated_vertices':vertices,'leaves':items[p.get('leaf_offset',0):p.get('leaf_offset',0)+p.get('leaf_limit',32)],'total_leaves':len(items),
            'next_leaf_offset':p.get('leaf_offset',0)+p.get('leaf_limit',32) if p.get('leaf_offset',0)+p.get('leaf_limit',32)<len(items) else None,
            'scope':'Current viewport dependency-graph instances, including nested prototypes. Active animation is shared; no geometry realization or render/engine certification.'}


def place(p):
    from .bridge import check_cancelled
    collection,_=guarded(p)
    if p['name'] in bpy.data.objects:raise ValueError('Instance object name already exists')
    obj=None;success=False
    try:
        check_cancelled();obj=bpy.data.objects.new(p['name'],None);obj.instance_type='COLLECTION';obj.instance_collection=collection
        obj.location=p['location'];obj.rotation_euler=[math.radians(a) for a in p['rotation_degrees']];obj.scale=p['scale']
        obj[INSTANCE]=json.dumps({'id':uuid.uuid4().hex,'assembly_id':metadata(collection)['id']})
        bpy.context.scene.collection.objects.link(obj);bpy.context.view_layer.update();check_cancelled()
        result=instance({'name':obj.name});check_cancelled();success=True;return result
    finally:
        if not success and obj:bpy.data.objects.remove(obj,do_unlink=True)


def editing(p):
    from .bridge import check_cancelled
    collection,_=guarded(p);children=bpy.context.scene.collection.children;was=collection.name in children
    try:
        check_cancelled()
        if p['enabled'] and not was:children.link(collection)
        elif not p['enabled'] and was:children.unlink(collection)
        bpy.context.view_layer.update();check_cancelled();result=inspect_asset(p);check_cancelled()
    except BaseException:
        linked=collection.name in children
        if was and not linked:children.link(collection)
        elif not was and linked:children.unlink(collection)
        bpy.context.view_layer.update();raise
    return result


def remove(p):
    from .bridge import check_cancelled
    result=instance(p)
    if result['instance_sha256']!=p['expected_instance']:raise ValueError('Instance fingerprint is stale; inspect instance again')
    obj=bpy.data.objects[p['name']];users=bpy.data.user_map(subset={obj}).get(obj,set())
    if any(c.get(META) for c in obj.users_collection):raise ValueError('Placement is an assembly component; membership editing is separate')
    if any(not isinstance(user,(bpy.types.Collection,bpy.types.Scene)) for user in users):raise ValueError('Instance is referenced by other data; remove those dependencies first')
    check_cancelled();bpy.data.objects.remove(obj,do_unlink=True)
    return {'removed':p['name'],'collection':result['collection'],'prototype_preserved':True}


def dispatch(command,p):
    if command=='inspect_asset_assembly_source':return source(p)[2]
    if command=='create_asset_assembly':return create(p)
    if command=='inspect_asset_assembly':return inspect_asset(p)
    if command=='place_asset_instance':return place(p)
    if command=='set_asset_assembly_editing':return editing(p)
    if command=='inspect_asset_instance':return instance(p)
    return remove(p)
