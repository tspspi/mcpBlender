"""Guarded current-viewport mesh snapshots of managed collection placements."""
import json
import math

import bpy
from mathutils import Matrix

from . import assemblies, lods
from .mesh_edit import geometry_digest

COMMANDS={'inspect_asset_realization','realize_asset_instances'}
META='mcpblender_asset_realization'


def mesh_record(mesh):
    mesh.calc_loop_triangles()
    if any(not math.isfinite(v) for vertex in mesh.vertices for v in vertex.co):
        raise ValueError('Realization requires finite mesh positions')
    if any(not math.isfinite(v) for normal in mesh.corner_normals for v in normal.vector):
        raise ValueError('Realization requires finite normals')
    for layer in mesh.uv_layers:
        if any(not math.isfinite(v) for item in layer.data for v in item.uv):
            raise ValueError('Realization requires finite UVs')
    if any(p.material_index>=max(1,len(mesh.materials)) for p in mesh.polygons):
        raise ValueError('Realization has invalid material indices')
    bounds={k:[fn(v.co[a] for v in mesh.vertices) for a in range(3)] for k,fn in (('min',min),('max',max))} if mesh.vertices else None
    return {'vertices':len(mesh.vertices),'triangles':len(mesh.loop_triangles),'bounds':bounds,
            'uv_maps':[l.name for l in mesh.uv_layers], 'materials':[m.name if m else None for m in mesh.materials],
            'geometry_sha256':geometry_digest(mesh),'attributes':assemblies.attribute_records(mesh),
            'normals_sha256':lods.packed(mesh.corner_normals,'vector',len(mesh.corner_normals)*3),
            'material_indices_sha256':lods.packed(mesh.polygons,'material_index',len(mesh.polygons),'i')}



def copy_evaluated_mesh(evaluated,transform):
    mesh=None
    try:
        # A Geometry Nodes instance may use the host object's identity but a
        # different evaluated mesh. new_from_object would re-evaluate the
        # host and lose the leaf geometry; copy the actual evaluated data.
        existing_keys=set(bpy.data.shape_keys)
        mesh=evaluated.data.copy()
        mesh.animation_data_clear()
        if mesh.shape_keys and mesh.shape_keys==evaluated.data.shape_keys:
            raise ValueError('Native copy retained unowned shape data')
        # Copying an evaluated mesh can create orphan Keys even when the
        # returned mesh.shape_keys is None. Delete exactly the Keys created
        # by this copy, preserving all existing source animation data.
        new_keys=set(bpy.data.shape_keys)-existing_keys
        if new_keys:bpy.data.batch_remove(ids=tuple(new_keys))
        for i,slot in enumerate(evaluated.material_slots):
            if slot.link=='OBJECT' and i<len(mesh.materials):mesh.materials[i]=slot.material
        # Bake affine placement, including shear, into an independent mesh.
        # Winding must follow a mirrored transform to retain outward faces.
        normal_matrix=transform.to_3x3().inverted().transposed()
        normals=[(normal_matrix@n.vector).normalized() for n in mesh.corner_normals]
        loop_vertices=[l.vertex_index for l in mesh.loops]
        mesh.transform(transform)
        if transform.determinant()<0:
            mesh.flip_normals()
            # flip_normals reverses corner order and native custom-normal
            # encoding is tied to the old tangent spaces. Reassign normals
            # explicitly after transforming geometry and fixing winding.
            reordered=[None]*len(normals)
            for polygon in mesh.polygons:
                lookup={loop_vertices[i]:normals[i] for i in polygon.loop_indices}
                if len(lookup)!=polygon.loop_total:raise ValueError('Mirrored realization requires faces without repeated vertices')
                for i in polygon.loop_indices:reordered[i]=lookup[mesh.loops[i].vertex_index]
            normals=reordered
        mesh.normals_split_custom_set(normals)
        mesh.update()
        return mesh
    except BaseException:
        if mesh:bpy.data.meshes.remove(mesh)
        raise

def snapshot(p,check_cancelled=lambda:None):
    """Return owned meshes; caller must remove or retain every mesh on success."""
    if bpy.context.mode!='OBJECT':raise ValueError('Object mode required for realization')
    sources=[assemblies.instance({'name':n}) for n in p['instances']]
    targets={bpy.data.objects[n] for n in p['instances']}
    bpy.context.view_layer.update();graph=bpy.context.evaluated_depsgraph_get()
    meshes=[];records=[];ignored={};vertices=0;corners=0
    try:
        for item in graph.object_instances:
            if not item.is_instance or not item.parent or item.parent.original not in targets or not item.show_self:continue
            if item.object.type!='MESH':
                kind=item.object.type;ignored[kind]=ignored.get(kind,0)+1
                if kind not in {'EMPTY','ARMATURE','LIGHT','CAMERA'}:
                    raise ValueError('Realization requires mesh geometry; convert unsupported leaf type first: '+kind)
                continue
            if not item.object.data.vertices:continue
            if len(meshes)>=2048:raise ValueError('Realization exceeds 2048 mesh leaves')
            vertices+=len(item.object.data.vertices);corners+=len(item.object.data.loops)
            if vertices>2000000 or corners>8000000:raise ValueError('Realization exceeds two million vertices or eight million corners')
            transform=item.matrix_world.copy()
            if any(not math.isfinite(v) for row in transform for v in row) or abs(transform.determinant())<1e-12:
                raise ValueError('Realization requires finite invertible leaf transforms')
            check_cancelled()
            mesh=copy_evaluated_mesh(item.object,transform)
            meshes.append(mesh)
            records.append({'instance':item.parent.original.name,'source_object':item.object.original.name,
                            'persistent_id':[i for i in item.persistent_id if i!=2147483647],
                            'source_matrix_world':lods.matrix(transform),'mesh':mesh_record(mesh)})
        if not records:raise ValueError('Realization requires nonempty visible evaluated mesh leaves')
        signature=lods.digest({'sources':[(s['name'],s['instance_sha256']) for s in sources],'leaves':records})
        bounds={key:[fn(r['mesh']['bounds'][key][a] for r in records) for a in range(3)] for key,fn in (('min',min),('max',max))}
        return meshes,{'instances':p['instances'],'source_sha256':signature,'leaves':records,'ignored_nonmesh_leaves':ignored,
                       'vertices':vertices,'triangles':sum(r['mesh']['triangles'] for r in records),'world_bounds':bounds,
                       'frame':bpy.context.scene.frame_current+bpy.context.scene.frame_subframe,
                       'scope':'Static current-viewport mesh snapshot, world-space geometry and native attributes. Materials remain shared; shader coordinates and external files are not baked. Animation, rigs, lights and cameras are not realized.'}
    except BaseException:
        for mesh in meshes:bpy.data.meshes.remove(mesh)
        raise


def inspect(p):
    meshes,result=snapshot(p)
    try:
        offset=p.get('leaf_offset',0);limit=p.get('leaf_limit',32)
        return result|{'total_leaves':len(result['leaves']),'leaves':result['leaves'][offset:offset+limit],
                       'next_leaf_offset':offset+limit if offset+limit<len(result['leaves']) else None}
    finally:
        for mesh in meshes:bpy.data.meshes.remove(mesh)


def realize(p):
    from .bridge import check_cancelled,report_progress
    if p['collection'] in bpy.data.collections:raise ValueError('Realization collection already exists')
    meshes=[];objects=[];collection=None;success=False
    try:
        check_cancelled();meshes,plan=snapshot(p,check_cancelled=check_cancelled)
        if plan['source_sha256']!=p['expected_source']:raise ValueError('Realization source fingerprint is stale; inspect again')
        collection=bpy.data.collections.new(p['collection'])
        for index,(mesh,record) in enumerate(zip(meshes,plan['leaves'])):
            check_cancelled()
            name=f"{p['collection']}_{index:04}"
            if name in bpy.data.objects:raise ValueError('Realization object name already exists: '+name)
            mesh.name=name+'_Mesh';obj=bpy.data.objects.new(name,mesh);objects.append(obj)
            obj.matrix_world=Matrix.Identity(4);collection.objects.link(obj)
            record['object']=obj.name
            report_progress({'phase':'realizing evaluated assembly meshes','mesh':index+1,'meshes':len(meshes),'fraction':(index+1)/len(meshes)})
        # Reinspect before publishing anything in the scene; graph data and source
        # selection/frame are unaffected by creating these unlinked mesh objects.
        if inspect(p)['source_sha256']!=p['expected_source']:raise ValueError('Realization source changed during snapshot')
        collection[META]=json.dumps({'format':'mcpblender-static-realization-v1','source_sha256':p['expected_source'],
                                     'frame':plan['frame'],'members':[o.name for o in objects]},sort_keys=True)
        bpy.context.scene.collection.children.link(collection);bpy.context.view_layer.update();check_cancelled()
        result=plan|{'collection':collection.name,'objects':[o.name for o in objects],'static_snapshot':True,'materials_shared':True}
        success=True;return result
    finally:
        if not success:
            for obj in objects:bpy.data.objects.remove(obj,do_unlink=True)
            if collection:bpy.data.collections.remove(collection)
            for mesh in meshes:bpy.data.meshes.remove(mesh)


def dispatch(command,p):
    return inspect(p) if command=='inspect_asset_realization' else realize(p)
