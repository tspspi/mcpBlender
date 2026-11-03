"""UV-only edits preserve mesh geometry, skinning and unrelated UV maps."""
import hashlib
import math
import struct

import bpy

from .assets import active_object, finished, mesh_object
from .mesh_edit import geometry_digest, resolve
from .morphs import topology_digest
from mcpblender.uv_math import signed_area, triangle_overlap

COMMANDS={"activate_uv_map","inspect_uv_layout","set_uv_seams","unwrap_uv_mesh","pack_uv_islands","normalize_uv_density"}


def fingerprint(obj,uv_map):
    mesh=obj.data
    digest=hashlib.sha256(bytes.fromhex(geometry_digest(mesh)))
    digest.update(uv_map.encode())
    for row in obj.matrix_world:digest.update(struct.pack('!4d',*row))
    digest.update(bytes(e.use_seam for e in mesh.edges))
    layer=mesh.uv_layers.get(uv_map)
    digest.update(b'1' if layer else b'0')
    digest.update(struct.pack('!i',mesh.uv_layers.active_index))
    digest.update(bytes(item.active_render for item in mesh.uv_layers))
    if layer:
        for item in layer.data:digest.update(struct.pack('!2d',*item.uv))
    return digest.hexdigest()


def check_size(mesh):
    if len(mesh.polygons)>100000 or len(mesh.loops)>500000:
        raise ValueError('UV workflows are limited to 100000 faces and 500000 corners')


def layout(mesh,layer,matrix,width,height):
    coordinates=[tuple(v.uv) for v in layer.data]
    if any(not all(math.isfinite(v) for v in uv) for uv in coordinates):
        raise ValueError('UV coordinates must be finite')
    parents=list(range(len(mesh.polygons)))
    def root(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    edges={}
    for face in mesh.polygons:
        loops=list(face.loop_indices)
        for a,b in zip(loops,loops[1:]+loops[:1]):
            va,vb=mesh.loops[a].vertex_index,mesh.loops[b].vertex_index
            endpoints={va:coordinates[a],vb:coordinates[b]}
            key=tuple(sorted((va,vb)))
            for other,uvs in edges.get(key,[]):
                if all(abs(endpoints[v][axis]-uvs[v][axis])<=1e-7 for v in key for axis in (0,1)):
                    parents[root(face.index)]=root(other)
            if len(edges.get(key,[]))>=64:raise ValueError('UV inspection limits edge incidence to 64 faces')
            edges.setdefault(key,[]).append((face.index,endpoints))
    islands={}
    for face in mesh.polygons:
        islands.setdefault(root(face.index),{'faces':[],'loops':[],'uv_area':0.,'world_area':0.})['faces'].append(face.index)
        islands[root(face.index)]['loops'].extend(face.loop_indices)
    mesh.calc_loop_triangles();triangles=[]
    for tri in mesh.loop_triangles:
        uv=[coordinates[i] for i in tri.loops]
        area=abs(signed_area(uv))
        xyz=[matrix@mesh.vertices[i].co for i in tri.vertices]
        world=(xyz[1]-xyz[0]).cross(xyz[2]-xyz[0]).length/2
        if not math.isfinite(world):raise ValueError('World-space triangle areas must be finite')
        island=islands[root(tri.polygon_index)]
        island['uv_area']+=area;island['world_area']+=world
        triangles.append((min(p[0] for p in uv),max(p[0] for p in uv),min(p[1] for p in uv),max(p[1] for p in uv),tri.polygon_index,uv))
    for island in islands.values():
        island['pixels_per_unit']=math.sqrt(island['uv_area']*width*height/island['world_area']) if island['world_area']>1e-20 else None
    return coordinates,list(islands.values()),triangles


def overlaps(triangles,budget):
    from mcpblender.uv_math import overlaps as checked_overlaps
    return checked_overlaps(triangles,budget)


def inspect(p):
    obj=mesh_object(p['name']);mesh=obj.data;check_size(mesh)
    layer=mesh.uv_layers.get(p['uv_map'])
    result={'name':obj.name,'uv_map':p['uv_map'],'exists':bool(layer),'uv_sha256':fingerprint(obj,p['uv_map']),
            'topology_sha256':topology_digest(mesh),'geometry_sha256':geometry_digest(mesh),
            'data_users':mesh.users,'active_uv_map':mesh.uv_layers.active.name if mesh.uv_layers.active else None,
            'render_uv_map':next((v.name for v in mesh.uv_layers if v.active_render),None),'seam_edges':[e.index for e in mesh.edges if e.use_seam][:512],
            'seam_count':sum(e.use_seam for e in mesh.edges),'seams_truncated':sum(e.use_seam for e in mesh.edges)>512,
            'density_units':'pixels per Blender world unit','texture_size':[p['texture_width'],p['texture_height']]}
    if not layer:return result
    coords,islands,triangles=layout(mesh,layer,obj.matrix_world,p['texture_width'],p['texture_height'])
    overlap=overlaps(triangles,p['overlap_budget'])
    shown=[]
    for island in islands[:p['island_limit']]:
        shown.append({k:v for k,v in island.items() if k not in {'loops','faces'}}|{'face_count':len(island['faces']),'first_face':island['faces'][0]})
    result.update(island_count=len(islands),islands=shown,islands_truncated=len(islands)>len(shown),
                  bounds={'min':[min((v[a] for v in coords),default=0) for a in (0,1)],'max':[max((v[a] for v in coords),default=0) for a in (0,1)]},
                  degenerate_islands=sum(i['uv_area']<=1e-20 or i['world_area']<=1e-20 for i in islands),
                  overlap=overlap)
    return result


def dispatch(command,p):
    if command=='inspect_uv_layout':return inspect(p)
    obj=mesh_object(p['name'],edit=True);mesh=obj.data;check_size(mesh)
    if fingerprint(obj,p['uv_map'])!=p['expected_uv']:raise ValueError('UV fingerprint is stale; inspect_uv_layout again')
    if mesh.users>1 and not p['make_single_user']:raise ValueError('Mesh data is shared; pass make_single_user=true')
    if command=='activate_uv_map':
        if not mesh.uv_layers.get(p['uv_map']):raise ValueError('UV map not found')
        if mesh.users>1:obj.data=mesh.copy();mesh=obj.data
        mesh.uv_layers.active=mesh.uv_layers[p['uv_map']]
        mesh.uv_layers[p['uv_map']].active_render=True
        return inspect(p)
    if command=='set_uv_seams':
        selected={e.index for e in resolve(obj,p['edges'],'EDGE',topology_digest(mesh),mesh.edges)}
        if mesh.users>1:obj.data=mesh.copy();mesh=obj.data
        for e in mesh.edges:
            if p['mode']=='SET':e.use_seam=e.index in selected
            elif e.index in selected:e.use_seam=p['mode']=='ADD'
        mesh.update()
        return inspect(p)
    if not mesh.polygons:raise ValueError('UV editing requires faces')
    if command!='unwrap_uv_mesh' and not mesh.uv_layers.get(p['uv_map']):raise ValueError('UV map not found')
    temporary=mesh.copy();staged=bpy.data.objects.new('MCP_UV_Stage',temporary)
    bpy.context.scene.collection.objects.link(staged)
    settings=bpy.context.scene.tool_settings
    select_mode=tuple(settings.mesh_select_mode);sync=settings.use_uv_select_sync
    try:
        layer=temporary.uv_layers.get(p['uv_map']) or temporary.uv_layers.new(name=p['uv_map'])
        temporary.uv_layers.active=layer
        if command=='normalize_uv_density':
            coords,islands,_=layout(temporary,layer,obj.matrix_world,p['texture_width'],p['texture_height'])
            if any(i['uv_area']<=1e-20 or i['world_area']<=1e-20 for i in islands):raise ValueError('Cannot normalize degenerate UV or world-space islands')
            for island in islands:
                center=[sum(coords[i][a] for i in island['loops'])/len(island['loops']) for a in (0,1)]
                factor=p['pixels_per_unit']/island['pixels_per_unit']
                for i in island['loops']:layer.data[i].uv=[center[a]+(coords[i][a]-center[a])*factor for a in (0,1)]
        else:
            with active_object(staged):
                settings.mesh_select_mode=(False,False,True);settings.use_uv_select_sync=False
                finished(bpy.ops.object.mode_set(mode='EDIT'));finished(bpy.ops.mesh.select_all(action='SELECT'))
                finished(bpy.ops.uv.select_all(action='SELECT'))
                if command=='unwrap_uv_mesh':
                    finished(bpy.ops.uv.unwrap(method=p['method'],margin=p['margin'],correct_aspect=False))
                else:
                    finished(bpy.ops.uv.pack_islands(rotate=p['rotate'],scale=p['scale'],margin=p['margin'],margin_method='FRACTION'))
                finished(bpy.ops.object.mode_set(mode='OBJECT'))
        values=[value for item in temporary.uv_layers[p['uv_map']].data for value in item.uv]
        if not all(math.isfinite(v) for v in values):raise ValueError('Native UV edit produced non-finite coordinates')
        if mesh.users>1:obj.data=mesh.copy();mesh=obj.data
        target=mesh.uv_layers.get(p['uv_map']) or mesh.uv_layers.new(name=p['uv_map'])
        target.data.foreach_set('uv',values);mesh.update()
    finally:
        settings.mesh_select_mode=select_mode;settings.use_uv_select_sync=sync
        bpy.data.objects.remove(staged,do_unlink=True);bpy.data.meshes.remove(temporary)
    return inspect(p)
