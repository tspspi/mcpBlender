"""Read-only evaluated UV quality and optional texture-bake admission."""
import time
import math
import bpy
from mcpblender import uv_quality,botany
from . import uv
from .assets import mesh_object

COMMANDS={'inspect_texture_quality'}


def measure(obj,mesh,uv_map,policy):
    from . import bridge
    uv.check_size(mesh);layer=mesh.uv_layers.get(uv_map)
    if not layer:raise ValueError('Texture quality UV map not found')
    unit=bpy.context.scene.unit_settings.scale_length
    if not math.isfinite(unit) or unit<=0:raise ValueError('Positive physical scene unit scale required')
    coords,islands,_=uv.layout(mesh,layer,obj.matrix_world,policy['width'],policy['height']);face_island={face:i for i,island in enumerate(islands) for face in island['faces']}
    mesh.calc_loop_triangles();triangles=[]
    for t in mesh.loop_triangles:
        triangles.append({'island':face_island[t.polygon_index],'uv':[list(coords[i]) for i in t.loops],'world_m':[list((obj.matrix_world@mesh.vertices[i].co)*unit) for i in t.vertices]})
    boundary={}
    for face in mesh.polygons:
        loops=list(face.loop_indices);island=face_island[face.index]
        for a,b in zip(loops,loops[1:]+loops[:1]):
            va,vb=mesh.loops[a].vertex_index,mesh.loops[b].vertex_index
            ends=sorted(((va,coords[a]),(vb,coords[b])))
            key=(island,*[(v,*point) for v,point in ends]);boundary.setdefault(key,[]).append((island,coords[a],coords[b]))
    edges=[values[0] for values in boundary.values() if len(values)!=2]
    last=[0.]
    def checkpoint():
        now=time.monotonic()
        if now-last[0]>=1:
            if bridge._bridge is not None:bridge.check_cancelled()
            bridge.report_progress({'phase':'inspecting geometric texture quality','width':policy['width'],'height':policy['height']});last[0]=now
    return uv_quality.analyze(triangles,edges,len(islands),policy,checkpoint=checkpoint)


def inspect(p):
    from .textures import mesh_signature
    obj=mesh_object(p['name']);evaluated=None
    bpy.context.view_layer.update()
    try:
        deps=bpy.context.evaluated_depsgraph_get();evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=deps)
        policy={k:p[k] for k in ('width','height','min_texels_per_meter','min_chart_pixels','padding_pixels','mip_levels','max_raster_tests','max_spacing_tests')}
        report=measure(evaluated,mesh,p['uv_map'],policy)
        source={'mesh':mesh_signature(evaluated,mesh),'scene_unit_scale':bpy.context.scene.unit_settings.scale_length,'uv_map':p['uv_map'],'frame':bpy.context.scene.frame_current}
        return report|{'source':source,'quality_sha256':botany.digest({'source':source,'report':report})}
    finally:
        if evaluated:evaluated.to_mesh_clear()


def dispatch(command,p):return inspect(p)
