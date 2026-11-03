"""Copy external/manual geometry into source-controlled managed LOD chains."""
import math
import uuid

import bpy
from mathutils import Vector
from mathutils.geometry import barycentric_transform
from mathutils.bvhtree import BVHTree

from . import lods
from .assets import mesh_object,require_static
from .assembly_realization import copy_evaluated_mesh
from mcpblender.lod_recipe import DEFAULTS,LEVEL_DEFAULTS

COMMANDS={'inspect_lod_adoption','adopt_lod_chain','readopt_lod_chain'}
CONFIG_KEYS={'name','deformation','inputs','input_geometry','preserve_material_regions','preserve_attribute_schema',
             'max_relative_error','error_samples','skin_max_influences','pose_frames','max_pose_error'}


def snapshot(p):
    from .bridge import check_cancelled,report_progress
    source,base,base_report,canonical=lods.source_snapshot(p);meshes=[];records=[];success=False
    try:
        previous=base_report['triangles'];graph=bpy.context.evaluated_depsgraph_get()
        names=[v['name'] for v in p['inputs']]
        if len(set(names))!=len(names) or source.name in names:raise ValueError('Adoption inputs must be distinct and exclude the canonical source')
        for entry in p['inputs']:
            check_cancelled();obj=mesh_object(entry['name'])
            if bpy.context.view_layer.objects.get(obj.name)!=obj or not obj.visible_get():raise ValueError('Adoption input must be visible in the current view layer: '+obj.name)
            evaluated=obj.evaluated_get(graph);transform=source.matrix_world.inverted()@evaluated.matrix_world
            if any(not math.isfinite(v) for row in transform for v in row) or abs(transform.determinant())<1e-12:raise ValueError('Finite invertible adoption transform required')
            if p['input_geometry']=='EVALUATED_STATIC':
                require_static(obj)
                if obj.find_armature() or obj.data.shape_keys:raise ValueError('Evaluated adoption requires static inputs without skin/morphs; choose RAW_BASIS explicitly to ignore their deformation')
                mesh=copy_evaluated_mesh(evaluated,transform)
            else:
                if obj.data.animation_data:raise ValueError('Raw adoption refuses mesh-data animation')
                from .morph_lods import rest_copy
                raw=rest_copy(obj) if obj.data.shape_keys else obj.data.copy();temp=None
                try:
                    temp=bpy.data.objects.new('mcp_LOD_adoption_basis',raw)
                    for i,slot in enumerate(obj.material_slots):
                        if slot.link=='OBJECT':raw.materials[i]=slot.material
                    mesh=copy_evaluated_mesh(temp,transform)
                finally:
                    if temp:bpy.data.objects.remove(temp)
                    bpy.data.meshes.remove(raw)
            meshes.append(mesh);original=lods.summary(mesh)
            uv_mapping=entry.get('uv_maps',{})
            if any(name not in mesh.uv_layers or target not in base.uv_layers for name,target in uv_mapping.items()):raise ValueError('UV mapping requires existing input names and canonical destinations')
            uv_names=[uv_mapping.get(layer.name,layer.name) for layer in mesh.uv_layers]
            if len(set(uv_names))!=len(uv_names):raise ValueError('UV mapping collides with another input layer')
            if uv_mapping:
                for i,layer in enumerate(mesh.uv_layers):layer.name='mcp_uv_'+uuid.uuid4().hex
                for layer,name in zip(mesh.uv_layers,uv_names):layer.name=name
            mapping=entry.get('material_slots')
            if mapping is not None:
                if len(mapping)!=max(1,len(mesh.materials)) or any(not 0<=v<max(1,len(base.materials)) for v in mapping):raise ValueError('Material slot map must cover every input slot with a valid canonical destination')
                for polygon in mesh.polygons:polygon.material_index=mapping[polygon.material_index]
                mesh.materials.clear()
                for material in base.materials:mesh.materials.append(material)
            report=lods.summary(mesh)
            if report['triangles']<4 or report['triangles']>=previous:raise ValueError('Adopted levels must have at least four and strictly decreasing triangles below the source')
            previous=report['triangles']
            if any(report[k]!=base_report[k] for k in ('materials','uv_maps','render_uv_map')):raise ValueError('Adopted UV layout/material slots must match source; supply material_slots to remap importer duplicates')
            if p['preserve_material_regions'] and report['used_material_indices']!=base_report['used_material_indices']:raise ValueError('Adoption lost used material regions')
            if p['preserve_attribute_schema'] and any(a not in report['attributes'] for a in base_report['attributes']):raise ValueError('Adoption lost named attribute schema')
            quality=lods.quality(base,mesh,p['error_samples'])
            if quality['max_relative_error']>p['max_relative_error']:raise ValueError('Adopted sampled surface error exceeds max_relative_error')
            records.append({'name':obj.name,'input_geometry':p['input_geometry'],'matrix_to_source':lods.matrix(transform),
                            'original':original,'normalized':report,'quality':quality,'material_slots':mapping,'uv_maps':uv_mapping})
            report_progress({'phase':'inspected external LOD','object':obj.name,'triangles':report['triangles'],'fraction':len(records)/len(p['inputs'])})
        config={k:v for k,v in p.items() if k in CONFIG_KEYS}
        signature=lods.digest({'canonical':canonical,'config':config,'inputs':records})
        report={'name':source.name,'canonical_source_sha256':canonical,'source_sha256':signature,'inputs':records,'config':config,
                'can_adopt':True,'source':base_report,
                'scope':'Owned geometry copies in canonical source space. Input modifiers apply only in EVALUATED_STATIC; RAW_BASIS ignores input deformation. Canonical source supplies skin weights and relative morphs/controllers; incoming animations stay on originals. Rest and pose errors are sampled, not exhaustive silhouette or anatomical proof.'}
        success=True;return meshes,report
    finally:
        bpy.data.meshes.remove(base)
        if not success:
            for mesh in meshes:bpy.data.meshes.remove(mesh)


def inspect(p):
    meshes,report=snapshot(p)
    try:return report
    finally:
        for mesh in meshes:bpy.data.meshes.remove(mesh)


def transfer_groups(obj,source,base,report):
    """Discard input weights, then interpolate canonical groups on its rest surface."""
    from .bridge import check_cancelled,report_progress
    # Copied deform indices have no reliable relationship to source group names.
    highest=max((g.group for v in obj.data.vertices for g in v.groups),default=-1)
    if highest>=2048:raise ValueError('Input deform group index exceeds 2048-group adoption limit')
    for i in range(highest+1):obj.vertex_groups.new(name='discard_'+str(i))
    obj.vertex_groups.clear()
    if not report.get('skin'):return
    from .skin_lods import setup_groups
    setup_groups(obj,source)
    base.calc_loop_triangles();triangles=[tuple(t.vertices) for t in base.loop_triangles];coords=[v.co.copy() for v in base.vertices]
    tree=BVHTree.FromPolygons(coords,triangles,all_triangles=True)
    for index,vertex in enumerate(obj.data.vertices):
        if index%128==0:check_cancelled();report_progress({'phase':'transferring canonical skin weights','object':obj.name,'vertices':index,'total_vertices':len(obj.data.vertices)})
        location,normal,face,distance=tree.find_nearest(vertex.co)
        if face is None:raise ValueError('No canonical rest triangle for skin transfer')
        a,b,c=triangles[face]
        weights=barycentric_transform(location,coords[a],coords[b],coords[c],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        if not all(math.isfinite(w) and -.0001<=w<=1.0001 for w in weights):raise ValueError('Degenerate skin transfer triangle')
        total=sum(max(0,w) for w in weights)
        if total<=1e-12:raise ValueError('Degenerate skin transfer weights')
        groups={}
        for v,w in zip((a,b,c),weights):
            for group in source.data.vertices[v].groups:
                groups[group.group]=groups.get(group.group,0.)+group.weight*max(0,w)/total
        for group,value in groups.items():
            if value>0:obj.vertex_groups[group].add([index],value,'REPLACE')


def adopt(p):
    meshes,report=snapshot(p);owned={m.as_pointer() for m in meshes}
    try:
        if report['source_sha256']!=p['expected_source']:raise ValueError('Adoption fingerprint is stale; inspect_lod_adoption again')
        def verify():
            if inspect(report['config'])['source_sha256']!=report['source_sha256']:raise ValueError('Adoption inputs changed during creation')
        recipe=DEFAULTS|{k:p[k] for k in ('name','deformation','chain','max_relative_error','error_samples','skin_max_influences','pose_frames','max_pose_error') if k in p}
        recipe.update(expected_source=report['canonical_source_sha256'],transfer_normals=False,
                      levels=[LEVEL_DEFAULTS|{'triangle_budget':r['normalized']['triangles']} for r in report['inputs']])
        return lods.generate(recipe,adoption={'meshes':meshes,'records':report['inputs'],'config':report['config'],'signature':report['source_sha256'],'verify':verify})
    finally:
        # generate owns consumed meshes and removes unconsumed copies on its
        # normal path. Early failures may leave others; avoid dead RNA handles.
        for mesh in list(bpy.data.meshes):
            if mesh.as_pointer() in owned and mesh.users==0:bpy.data.meshes.remove(mesh)


def dispatch(command,p):
    if command=='inspect_lod_adoption':return inspect(p)
    if command=='adopt_lod_chain':return adopt(p)
    from .lod_management import rebuild
    return rebuild(p,generator=adopt)
