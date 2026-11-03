"""Static evaluated collision and Cycles shadow meshes with source provenance."""
import json
import math
import uuid

import bmesh
import bpy
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree

from . import assemblies,lods,assembly_realization as realization
from .assets import local_object

COMMANDS={'inspect_render_visibility','configure_render_visibility','inspect_asset_proxy_source','generate_asset_proxies','inspect_asset_proxies','remove_asset_proxies'}
META='mcpblender_asset_proxies'
MARKER='mcpblender-static-proxy-v1'
RAYS=('visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow')
SETTINGS=('objects','purpose','method','grouping','padding','triangle_budget','max_relative_error','sample_count')



def render_visibility(p):
    obj=local_object(p['name']);fields=('hide_render',*RAYS);animated=set();anim=obj.animation_data
    if anim:
        from .domains import curves
        animated.update(c.data_path for c in anim.drivers if c.data_path in fields)
        actions=[(anim.action,getattr(anim,'action_slot',None))] if anim.action else []
        actions.extend((strip.action,getattr(strip,'action_slot',None)) for track in anim.nla_tracks for strip in track.strips if strip.action)
        for action,slot in actions:animated.update(c.data_path for c in curves(action,slot) if c.data_path in fields)
    state={k:getattr(obj,k) for k in fields}
    return {'name':obj.name,'visibility':state,'animated_fields':sorted(animated),
            'visibility_sha256':lods.digest({'name':obj.name,'visibility':state,'animated_fields':sorted(animated)}),
            'scope':'hide_render excludes the object from rendering; per-ray visibility is Cycles-specific.'}


def configure_visibility(p):
    from .bridge import check_cancelled
    state=render_visibility(p)
    if state['visibility_sha256']!=p['expected_visibility']:raise ValueError('Render visibility fingerprint is stale; inspect again')
    changes={k:p[k] for k in ('hide_render',*RAYS) if p.get(k) is not None}
    if set(changes).intersection(state['animated_fields']):raise ValueError('Targeted render visibility is animated or driven')
    obj=local_object(p['name'])
    try:
        check_cancelled()
        for key,value in changes.items():setattr(obj,key,value)
        bpy.context.view_layer.update();check_cancelled();return render_visibility(p)
    except BaseException:
        for key in changes:setattr(obj,key,state['visibility'][key])
        bpy.context.view_layer.update();raise

def source(p,check_cancelled=lambda:None):
    if bpy.context.mode!='OBJECT':raise ValueError('Object mode required for proxy generation')
    meshes=[];leaves=[];source_records=[];vertices=0;corners=0
    try:
        for name in p['objects']:
            check_cancelled();obj=local_object(name)
            if obj.instance_type=='COLLECTION' and obj.get(assemblies.INSTANCE):
                owned,plan=realization.snapshot({'instances':[name]},check_cancelled=check_cancelled)
                meshes.extend(owned);leaves.extend(plan['leaves']);source_records.append({'name':name,'signature':plan['source_sha256']})
            else:
                if obj.type!='MESH' or bpy.context.view_layer.objects.get(name)!=obj or not obj.visible_get():
                    raise ValueError('Proxy source must be a visible local mesh or managed placement: '+name)
                bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(graph)
                transform=evaluated.matrix_world.copy()
                if any(not math.isfinite(v) for row in transform for v in row) or abs(transform.determinant())<1e-12:
                    raise ValueError('Proxy source requires finite invertible transform')
                if len(evaluated.data.vertices)>2000000 or len(evaluated.data.loops)>8000000:raise ValueError('Proxy source exceeds geometry limits')
                mesh=realization.copy_evaluated_mesh(evaluated,transform);meshes.append(mesh)
                record=realization.mesh_record(mesh)
                if not record['bounds'] or not record['triangles']:raise ValueError('Proxy source requires a nonempty triangle surface')
                leaves.append({'instance':name,'source_object':name,'mesh':record})
                source_records.append({'name':name,'native':assemblies.record(obj)})
            vertices=sum(len(m.vertices) for m in meshes);corners=sum(len(m.loops) for m in meshes)
            if len(meshes)>2048 or vertices>2000000 or corners>8000000:raise ValueError('Proxy source exceeds 2048 leaves, two million vertices or eight million corners')
        if any(not leaf['mesh']['triangles'] for leaf in leaves):raise ValueError('Proxy leaves require triangle surfaces')
        groups=[]
        if p['grouping']=='COMBINED':groups=[list(range(len(meshes)))]
        elif p['grouping']=='PER_SOURCE':
            groups=[[i for i,leaf in enumerate(leaves) if leaf['instance']==name] for name in p['objects']]
        else:groups=[[i] for i in range(len(meshes))]
        if not groups or len(groups)>256:raise ValueError('Proxy generation requires 1..256 output groups')
        blockers=[]
        for indices in groups:
            group=[meshes[i] for i in indices]
            if p['method']=='CONVEX_HULL' and sum(len(m.vertices) for m in group)>200000:
                blockers.append('Convex hull group exceeds 200000 source vertices')
            if p['method'] in {'BOX','CONVEX_HULL'}:
                bounds=[(min(v.co[a] for m in group for v in m.vertices),max(v.co[a] for m in group for v in m.vertices)) for a in range(3)]
                padding=p['padding'] if p['method']=='BOX' else 0
                if any(high-low+2*padding<=1e-9 for low,high in bounds):blockers.append('Collision group has zero extent; use BOX padding or volumetric input')
        settings={k:p.get(k) for k in SETTINGS}
        settings['padding']=float(settings['padding'])
        if settings['max_relative_error'] is not None:settings['max_relative_error']=float(settings['max_relative_error'])
        signature=lods.digest({'sources':source_records,'leaves':leaves,'settings':settings,'frame':bpy.context.scene.frame_current+bpy.context.scene.frame_subframe})
        bounds={key:[fn(leaf['mesh']['bounds'][key][a] for leaf in leaves) for a in range(3)] for key,fn in (('min',min),('max',max))}
        return meshes,groups,{'can_generate':not blockers,'blockers':sorted(set(blockers)),'source_sha256':signature,'settings':settings,'source_leaves':len(leaves),'proxy_count':len(groups),
                              'vertices':vertices,'triangles':sum(l['mesh']['triangles'] for l in leaves),'world_bounds':bounds,
                              'frame':bpy.context.scene.frame_current+bpy.context.scene.frame_subframe,
                              'warnings':['Static current-viewport snapshot; animated/deformed sources are frozen.',
                                          'Boxes and convex hulls fill holes and spaces inside each group; choose grouping deliberately.',
                                          'Shadow visibility is Cycles-specific. Sources remain visible and retain their shadow settings.',
                                          'Materials are shared, not baked; sampled surface error is not a silhouette or alpha coverage guarantee.']}
    except BaseException:
        for mesh in meshes:bpy.data.meshes.remove(mesh)
        raise


def inspect_source(p):
    meshes,_,result=source(p)
    try:return result
    finally:
        for mesh in meshes:bpy.data.meshes.remove(mesh)


def convex(meshes,p):
    bm=bmesh.new();mesh=None
    try:
        points=[v.co.copy() for m in meshes for v in m.vertices]
        if p['method']=='BOX':
            low=Vector([min(v[a] for v in points)-p['padding'] for a in range(3)])
            high=Vector([max(v[a] for v in points)+p['padding'] for a in range(3)])
            if min(high-low)<=1e-9:raise ValueError('BOX requires nonzero extent on every axis; supply padding for flat sources')
            bmesh.ops.create_cube(bm,size=2)
            center=(high+low)/2;extent=(high-low)/2
            for v in bm.verts:v.co=Vector([v.co[a]*extent[a]+center[a] for a in range(3)])
        else:
            if len(points)>200000:raise ValueError('Convex hull group exceeds 200000 source vertices')
            for point in points:bm.verts.new(point)
            bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
            unused=[v for v in bm.verts if not v.link_faces]
            if unused:bmesh.ops.delete(bm,geom=unused,context='VERTS')
        if not bm.faces or any(not e.is_manifold for e in bm.edges):raise ValueError('Collision proxy requires a closed manifold volume')
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        volume=bm.calc_volume(signed=True)
        if not math.isfinite(volume) or abs(volume)<1e-12:raise ValueError('Collision proxy volume is degenerate')
        if volume<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
        mesh=bpy.data.meshes.new('MCP_CollisionProxy');bm.to_mesh(mesh);mesh.update();return mesh,abs(volume)
    except BaseException:
        if mesh:bpy.data.meshes.remove(mesh)
        raise
    finally:bm.free()


def quality(meshes,target,count):
    coords=[];triangles=[]
    for mesh in meshes:
        offset=len(coords);coords.extend(v.co.copy() for v in mesh.vertices);mesh.calc_loop_triangles()
        triangles.extend(tuple(offset+i for i in t.vertices) for t in mesh.loop_triangles)
    original=BVHTree.FromPolygons(coords,triangles,all_triangles=True);proxy,_=lods.surface(target)
    diagonal=(Vector([max(v[a] for v in coords) for a in range(3)])-Vector([min(v[a] for v in coords) for a in range(3)])).length
    if diagonal<1e-12:raise ValueError('Proxy source extent is degenerate')
    distances=[];outside=[]
    # Sample each input leaf so small constituent components are not omitted.
    per_leaf=max(8,count//len(meshes))
    for mesh in meshes:
        for point in lods.samples(mesh,per_leaf):
            hit=proxy.find_nearest(point)
            if hit[0] is None:raise ValueError('Proxy surface measurement failed')
            distances.append(hit[3]);outside.append(max(0,(point-hit[0]).dot(hit[1])))
    for point in lods.samples(target,count):
        hit=original.find_nearest(point)
        if hit[0] is None:raise ValueError('Source surface measurement failed')
        distances.append(hit[3])
    return {'sample_count':len(distances),'max_distance':max(distances),'max_relative_error':max(distances)/diagonal,
            'rms_distance':math.sqrt(sum(v*v for v in distances)/len(distances)),
            'max_sampled_outside_distance':max(outside),'source_diagonal':diagonal,
            'scope':'Bidirectional sampled vertex/triangle-center world-space distances; signed outside distances apply to outward convex proxies only. Not exhaustive containment, collision or silhouette certification.'}


def decimate(original,budget,owned_objects,owned_meshes,check_cancelled):
    mesh=original.copy();owned_meshes.append(mesh);obj=bpy.data.objects.new('MCP_ProxyWork',mesh);owned_objects.append(obj)
    bpy.context.scene.collection.objects.link(obj)
    original.calc_loop_triangles();ratio=min(1,budget/max(1,len(original.loop_triangles)))
    modifier=obj.modifiers.new('ProxyDecimation','DECIMATE');modifier.decimate_type='COLLAPSE';modifier.use_collapse_triangulate=True
    for _ in range(4):
        check_cancelled();modifier.ratio=ratio;bpy.context.view_layer.update()
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        candidate=realization.copy_evaluated_mesh(evaluated,Matrix.Identity(4));owned_meshes.append(candidate);candidate.calc_loop_triangles()
        actual=len(candidate.loop_triangles)
        if 0<actual<=budget:return candidate
        if not actual:raise ValueError('Decimation produced empty geometry')
        owned_meshes.remove(candidate);bpy.data.meshes.remove(candidate);ratio*=budget/actual*.98
    raise ValueError('Decimation could not meet the triangle budget')


def inspect(p):
    collection=bpy.data.collections.get(p['collection'])
    if not collection:raise ValueError('Managed proxy collection not found')
    text=collection.get(META)
    if not isinstance(text,str) or len(text)>2*1024**2:raise ValueError('Invalid proxy ownership metadata')
    meta=json.loads(text)
    if not isinstance(meta,dict) or meta.get('format')!=MARKER or not isinstance(meta.get('members'),list) or not 1<=len(meta['members'])<=256:raise ValueError('Invalid proxy inventory')
    issues=[];records=[]
    if collection.children or {o.name for o in collection.objects}!={m['name'] for m in meta['members']}:issues.append('Proxy collection membership changed')
    for member in meta['members']:
        obj=bpy.data.objects.get(member['name'])
        if not obj or obj.type!='MESH':issues.append('Proxy mesh missing: '+member['name']);continue
        record=realization.mesh_record(obj.data)
        if lods.digest(record)!=member['mesh_sha256']:issues.append('Proxy mesh changed: '+obj.name)
        if obj.modifiers or obj.parent or obj.constraints or obj.animation_data or obj.data.shape_keys or obj.data.animation_data:issues.append('Proxy gained deformation: '+obj.name)
        if any(abs(obj.matrix_world[i][j]-(1 if i==j else 0))>1e-6 for i in range(4) for j in range(4)):issues.append('Proxy world-space placement changed: '+obj.name)
        if meta['settings']['purpose']=='SHADOW' and any(getattr(obj,key)!=(key=='visible_shadow') for key in RAYS):issues.append('Shadow ray visibility changed: '+obj.name)
        if meta['settings']['purpose']=='COLLISION' and not obj.hide_render:issues.append('Collision proxy became render-visible: '+obj.name)
        records.append(member|{'mesh':record,'native':assemblies.record(obj),'hide_render':obj.hide_render,'ray_visibility':{k:getattr(obj,k) for k in RAYS}})
    try:current=inspect_source(meta['settings'])['source_sha256'];source_matches=current==meta['source_sha256'];source_error=None
    except (ValueError,RuntimeError,ReferenceError) as exc:source_matches=False;source_error=str(exc)
    signature=lods.digest({'metadata':meta,'records':records,'issues':issues,'source_matches':source_matches})
    offset=p.get('offset',0);limit=p.get('limit',32)
    return {'collection':collection.name,'id':meta['id'],'purpose':meta['settings']['purpose'],'method':meta['settings']['method'],
            'proxy_sha256':signature,'valid':not issues,'issues':issues,'source_matches':source_matches,'source_error':source_error,
            'source_sha256':meta['source_sha256'],'settings':meta['settings'],'total_proxies':len(records),'proxies':records[offset:offset+limit],
            'next_offset':offset+limit if offset+limit<len(records) else None,'warnings':meta['warnings']}


def generate(p):
    from .bridge import check_cancelled,report_progress
    if p['collection'] in bpy.data.collections:raise ValueError('Proxy collection already exists')
    sources=[];meshes=[];objects=[];collection=None;success=False
    try:
        check_cancelled();sources,groups,plan=source(p,check_cancelled=check_cancelled)
        if plan['source_sha256']!=p['expected_source']:raise ValueError('Proxy source fingerprint is stale; inspect again')
        if plan['blockers']:raise ValueError('; '.join(plan['blockers']))
        collection=bpy.data.collections.new(p['collection']);members=[]
        for index,indices in enumerate(groups):
            check_cancelled();group=[sources[i] for i in indices]
            if p['method']=='DECIMATE':mesh=decimate(group[0],p['triangle_budget'],objects,meshes,check_cancelled);volume=None
            else:mesh,volume=convex(group,p);meshes.append(mesh)
            measurement=quality(group,mesh,p['sample_count'])
            if p.get('max_relative_error') is not None and measurement['max_relative_error']>p['max_relative_error']:
                raise ValueError('Proxy sampled surface error exceeds max_relative_error')
            name=f"{p['collection']}_{index:04}"
            if name in bpy.data.objects:raise ValueError('Proxy object name already exists: '+name)
            mesh.name=name+'_Mesh';obj=bpy.data.objects.new(name,mesh);objects.append(obj);collection.objects.link(obj)
            obj.hide_render=p['purpose']=='COLLISION';obj.display_type='WIRE' if p['purpose']=='COLLISION' else 'TEXTURED'
            if p['purpose']=='SHADOW':
                for key in RAYS:setattr(obj,key,key=='visible_shadow')
            record=realization.mesh_record(mesh)
            members.append({'name':obj.name,'mesh_sha256':lods.digest(record),'source_leaf_indices':indices,'quality':measurement,'volume':volume,
                            'suggested_collision_shape':('BOX' if p['method']=='BOX' else 'CONVEX_HULL') if p['purpose']=='COLLISION' else None})
            report_progress({'phase':'verified asset proxy','proxy':index+1,'proxies':len(groups),'fraction':(index+1)/len(groups)})
        if inspect_source(p)['source_sha256']!=p['expected_source']:raise ValueError('Proxy source changed during generation')
        retained={bpy.data.objects[m['name']] for m in members};kept_meshes={o.data for o in retained}
        for obj in list(objects):
            if obj not in retained:objects.remove(obj);bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in list(meshes):
            if mesh not in kept_meshes:meshes.remove(mesh);bpy.data.meshes.remove(mesh)
        collection[META]=json.dumps({'format':MARKER,'id':uuid.uuid4().hex,'settings':plan['settings'],'source_sha256':p['expected_source'],
                                     'frame':plan['frame'],'members':members,'warnings':plan['warnings']},sort_keys=True,allow_nan=False)
        bpy.context.scene.collection.children.link(collection);bpy.context.view_layer.update();check_cancelled()
        result=inspect({'collection':collection.name,'limit':128})
        if not result['valid'] or not result['source_matches']:raise ValueError('Generated proxy verification failed')
        success=True;return result
    finally:
        for mesh in sources:bpy.data.meshes.remove(mesh)
        if not success:
            for obj in objects:bpy.data.objects.remove(obj,do_unlink=True)
            if collection:bpy.data.collections.remove(collection)
            for mesh in meshes:bpy.data.meshes.remove(mesh)


def remove(p):
    from .bridge import check_cancelled
    result=inspect(p)
    if result['proxy_sha256']!=p['expected_proxy']:raise ValueError('Proxy fingerprint is stale; inspect again')
    collection=bpy.data.collections[p['collection']];meta=json.loads(collection[META]);objects=[bpy.data.objects.get(m['name']) for m in meta['members']]
    if collection.children or None in objects or set(collection.objects)!=set(objects):raise ValueError('Proxy inventory changed; removal refused')
    if collection.library or collection.override_library:raise ValueError('Proxy ownership must be local')
    for obj in objects:
        if obj.library or obj.override_library or obj.rigid_body or set(obj.users_collection)!={collection}:raise ValueError('Detach physics and foreign collection membership before proxy removal')
        users=bpy.data.user_map(subset={obj}).get(obj,set())
        if any(not isinstance(u,(bpy.types.Collection,bpy.types.Scene)) and u not in objects for u in users):raise ValueError('Proxy has external references')
    collection_users=bpy.data.user_map(subset={collection}).get(collection,set())
    if any(not isinstance(u,bpy.types.Scene) for u in collection_users):raise ValueError('Proxy collection has external references')
    check_cancelled();meshes={o.data for o in objects}
    for obj in objects:bpy.data.objects.remove(obj,do_unlink=True)
    bpy.data.collections.remove(collection)
    for mesh in meshes:
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    return {'removed':p['collection'],'objects':[m['name'] for m in meta['members']],'sources_preserved':True}


def dispatch(command,p):
    return {'inspect_render_visibility':render_visibility,'configure_render_visibility':configure_visibility,'inspect_asset_proxy_source':inspect_source,'generate_asset_proxies':generate,'inspect_asset_proxies':inspect,'remove_asset_proxies':remove}[command](p)
