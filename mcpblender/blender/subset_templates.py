"""Copy-only native leaf reduction with exact petiole geometry/UV retention."""
import bpy,bmesh
from mcpblender import botany
from . import lods

RECIPE='PROTECTED_PETIOLE_COLLAPSE_NORMALS_V1'


def area(mesh):
    mesh.calc_loop_triangles();result={}
    for tri in mesh.loop_triangles:
        a,b,c=(mesh.vertices[v].co for v in tri.vertices);result[tri.material_index]=result.get(tri.material_index,0)+(b-a).cross(c-a).length/2
    return result


def protected_signature(mesh):
    rows=[]
    for face in mesh.polygons:
        if face.material_index!=1:continue
        corners=[(tuple(mesh.vertices[mesh.loops[i].vertex_index].co),tuple(tuple(layer.data[i].uv) for layer in mesh.uv_layers)) for i in face.loop_indices]
        rows.append((face.use_smooth,min(tuple(corners[i:]+corners[:i]) for i in range(len(corners)))))
    return botany.digest(sorted(rows))


def build(base,settings):
    """Return one new mesh and its deterministic report; remove staging IDs."""
    from .bridge import check_cancelled,report_progress
    before=lods.summary(base);budget=settings['triangle_budget']
    if before['used_material_indices']!=[0,1] or len(base.materials)!=2 or base.shape_keys:raise ValueError('Template reduction requires a static blade/petiole template with two material slots')
    if budget>=before['triangles']:raise ValueError('Template triangle budget must reduce the source')
    region_vertices=[{v for face in base.polygons if face.material_index==i for v in face.vertices} for i in (0,1)]
    if region_vertices[0]&region_vertices[1]:raise ValueError('Template blade and petiole must have disjoint vertices')
    made=[];objects=[];result=None;success=False
    def part(material):
        mesh=base.copy();made.append(mesh);bm=bmesh.new()
        try:
            bm.from_mesh(mesh);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=material],context='FACES');loose=[v for v in bm.verts if not v.link_faces]
            if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
            bm.to_mesh(mesh)
        finally:bm.free()
        mesh.update();return mesh
    def proxy(mesh,name):
        obj=bpy.data.objects.new(name,mesh);objects.append(obj);bpy.context.scene.collection.objects.link(obj);obj.hide_render=True;return obj
    try:
        check_cancelled();report_progress({'phase':'reducing private native leaf template','source_triangles':before['triangles'],'triangle_budget':budget})
        stem=part(1);blade=part(0);stem.calc_loop_triangles();reserved=len(stem.loop_triangles)
        if budget-reserved<4:raise ValueError('Template budget cannot retain petiole plus blade')
        blade_report=lods.summary(blade);holder=blade.copy();made.append(holder);obj=proxy(holder,'MCP Template Blade')
        reduced=lods.reduce(obj,blade_report,{'method':'COLLAPSE','triangle_budget':budget-reserved});made.append(reduced)
        joined=base.copy();made.append(joined);bm=bmesh.new()
        try:bm.from_mesh(reduced);bm.from_mesh(stem);bm.to_mesh(joined)
        finally:bm.free()
        joined.update();obj.data=joined
        source_mesh=base.copy();made.append(source_mesh);source=proxy(source_mesh,'MCP Template Normals')
        mod=obj.modifiers.new('MCP Source Normals','DATA_TRANSFER');mod.object=source;mod.use_loop_data=True;mod.data_types_loops={'CUSTOM_NORMAL'};mod.loop_mapping='POLYINTERP_NEAREST'
        bpy.context.view_layer.update();check_cancelled()
        result=bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()),preserve_all_data_layers=True,depsgraph=bpy.context.evaluated_depsgraph_get());made.append(result)
        after=lods.summary(result);measurement=lods.quality(base,result,settings['error_samples']);original_area=area(base);reduced_area=area(result)
        changes={str(k):reduced_area.get(k,0)/a-1 for k,a in original_area.items()}
        if not result.has_custom_normals or after['triangles']>budget or after['triangles']>=before['triangles']:raise ValueError('Template reduction/normal transfer did not meet its budget')
        if after['materials']!=before['materials'] or after['used_material_indices']!=before['used_material_indices'] or after['uv_maps']!=before['uv_maps'] or after['render_uv_map']!=before['render_uv_map'] or any(a not in after['attributes'] for a in before['attributes']):raise ValueError('Template reduction lost material/UV/attribute schema')
        protected=protected_signature(base)
        if protected_signature(result)!=protected:raise ValueError('Template petiole geometry/UV changed')
        if measurement['max_relative_error']>settings['max_relative_error']:raise ValueError('Template sampled surface error exceeds policy')
        if any(abs(v)>settings['max_area_relative_error'] for v in changes.values()):raise ValueError('Template material-region area change exceeds policy')
        report={'recipe':RECIPE,'source_mesh_sha256':before['mesh_sha256'],'reduced_mesh_sha256_before_material_copy':after['mesh_sha256'],
                'source_triangles':before['triangles'],'triangles':after['triangles'],'petiole_triangles':reserved,'petiole_geometry_uv_sha256':protected,
                'quality':measurement,'area_relative_change_by_material':changes,'source_normals_transferred':True,
                'scope':'Copy-only collapse of blade; exact petiole topology/coordinates/all UVs retained; nearest interpolated source loop normals. Material/UV/attribute schema preserved. Sampled local surface error and per-region 3D area are not exhaustive silhouette, world-error, optical or wind certificates.'}
        check_cancelled();success=True;return result,report
    finally:
        for obj in reversed(objects):bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in reversed(made):
            if not success or mesh!=result:bpy.data.meshes.remove(mesh)
        bpy.context.view_layer.update()


def plan(roles,selected,settings):
    reports=[];chosen=set(selected);indices=[v.value for v in roles['pm'].attributes['leaf_index'].data];variants=[v.value for v in roles['pm'].attributes['leaf_variant'].data]
    prototypes=sorted((int(k[2:]),obj) for k,obj in roles.items() if k.startswith('lo'));counts=[0]*len(prototypes)
    for identifier,variant in zip(indices,variants):
        if identifier in chosen:counts[variant]+=1
    for variant,obj in prototypes:
        mesh=None
        try:
            mesh,report=build(obj.data,settings);reports.append({'variant':variant,'instances':counts[variant],**report})
        finally:
            if mesh is not None:bpy.data.meshes.remove(mesh)
    return {'recipe':RECIPE,'settings':settings,'variants':reports,'selected_instances':len(selected),
            'expanded_source_leaf_triangles':sum(r['instances']*r['source_triangles'] for r in reports),
            'expanded_reduced_leaf_triangles':sum(r['instances']*r['triangles'] for r in reports)}
