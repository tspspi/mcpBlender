"""Source-preserving fitted card targets for the shared texture-bake pipeline."""
import bpy
from mcpblender import card_fit,botany
from . import textures
from .assets import mesh_object

COMMANDS={'inspect_foliage_card','create_foliage_card','inspect_foliage_card_views'}
OPTIONS=('sources','view','outline','padding','standoff_m','resolution','max_vertices','max_triangles','thin_foliage_mode')


def sources(p):
    from .bridge import check_cancelled,report_progress
    bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();unit=bpy.context.scene.unit_settings.scale_length
    triangles=[];records=[]
    targets={mesh_object(name,edit=True) for name in p['sources']}
    for i,item in enumerate(deps.object_instances):
        if i%256==0:check_cancelled()
        if i>=200000:raise ValueError('Card instance inspection budget exceeded')
        if item.is_instance and item.parent and item.parent.original in targets and item.show_self:raise ValueError('Card source has instances; realize instances before fitting')
    for name in p['sources']:
        check_cancelled();obj=mesh_object(name,edit=True)
        if bpy.context.view_layer.objects.get(name)!=obj:raise ValueError('Card source must be in current view layer')
        ev=obj.evaluated_get(deps)
        try:
            mesh=ev.to_mesh(preserve_all_data_layers=True,depsgraph=deps)
            if not mesh or not mesh.polygons:raise ValueError('Card source has no evaluated faces; realize Geometry Nodes/collection instances first')
            record=textures.mesh_signature(ev,mesh)
            if not mesh.materials or any(m is None for m in mesh.materials):raise ValueError('Card sources need supported materials in every slot')
            record['shaders']=[textures.material_signature(m,thin_foliage_mode=p['thin_foliage_mode']) for m in mesh.materials]
            records.append(record);mesh.calc_loop_triangles()
            if len(triangles)+len(mesh.loop_triangles)>p['max_triangles']:raise ValueError('Card triangle budget exceeded')
            coords=[tuple(x*unit for x in (ev.matrix_world@v.co)) for v in mesh.vertices]
            triangles.extend([coords[i] for i in t.vertices] for t in mesh.loop_triangles)
        finally:ev.to_mesh_clear()
        report_progress({'phase':'inspecting fitted card sources','sources':len(records),'triangles':len(triangles)})
    return triangles,records,unit


def fitted(p,triangles,records,unit):
    from .bridge import check_cancelled,report_progress
    options={k:p[k] for k in OPTIONS}
    spec=card_fit.fit(triangles,**{k:p[k] for k in OPTIONS if k not in {'sources','thin_foliage_mode'}},cancelled=check_cancelled,progress=report_progress)
    guard=botany.digest({'source':records,'options':options,'scene_unit_scale':unit,'frame':bpy.context.scene.frame_current+bpy.context.scene.frame_subframe,'fit':spec})
    return spec|{'card_sha256':guard,'scene_unit_scale':unit,'sources':p['sources'],
                 'material_adapters':[r['bake_adapter'] for record in records for r in record['shaders'] if 'bake_adapter' in r]}



def inspect(p):return fitted(p,*sources(p))


def views(p):
    from .bridge import check_cancelled,report_progress
    triangles,records,unit=sources(p);work=len(triangles)*len(p['views'])
    if work>p['max_projected_triangles']:raise ValueError('Foliage view-family projected triangle budget exceeded')
    rows=[];total=0;options={k:p[k] for k in OPTIONS if k!='view'}
    for index,view in enumerate(p['views']):
        check_cancelled();report_progress({'phase':'fitting foliage card alternatives','view':view,'completed':index,'total':len(p['views'])})
        params=options|{'view':view};state=fitted(params,triangles,records,unit);total+=state['triangles']
        if total>p['max_total_card_triangles']:raise ValueError('Foliage view-family total card triangle budget exceeded')
        rows.append({'view':view,'card':state,'create_parameters':params|{'expected_card':state['card_sha256']},
                     'camera_frame_view':{'TOP':'TOP','FRONT':'FRONT','SIDE':'RIGHT'}[view]})
    result={'method':'ORTHOGRAPHIC_CARD_VIEW_FAMILY_V1','sources':p['sources'],'views':rows,'source_triangles':len(triangles),
            'projected_triangles':work,'total_card_triangles':total,'scene_unit_scale':unit,
            'limits':{k:p[k] for k in ('max_projected_triangles','max_total_card_triangles')},
            'scope':'Individually fitted static alternatives with independent source-bound creation guards. No automatic baking, angular selection/interpolation, crossed-card union, wind, or whole-tree far representation.',
            'next_step':'For each selected alternative, call create_foliage_card with create_parameters and a distinct name. Bake separately, then optionally atlas verified bundles. Configure an ORTHO camera and frame_objects using source plus created target and camera_frame_view; keep that camera fixed for matched native/delivered review.'}
    check_cancelled();return result|{'views_sha256':botany.digest(result)}


def create(p):
    from .bridge import check_cancelled,report_progress
    state=inspect(p)
    if state['card_sha256']!=p['expected_card']:raise ValueError('Foliage card fingerprint is stale; inspect again')
    if p['name'] in bpy.data.objects:raise ValueError('Card object already exists')
    before=set(bpy.data.user_map());success=False
    try:
        check_cancelled();unit=state['scene_unit_scale'];verts=state['vertices_m'];origin=[sum(v[a] for v in verts)/len(verts) for a in range(3)]
        mesh=bpy.data.meshes.new(p['name']+'_Mesh');mesh.from_pydata([[(v[a]-origin[a])/unit for a in range(3)] for v in verts],[],[tuple(range(len(verts)))]);mesh.update()
        layer=mesh.uv_layers.new(name='CardUV')
        for loop in mesh.loops:layer.data[loop.index].uv=state['uv'][loop.vertex_index]
        material=bpy.data.materials.new(p['name']+'_Surface');material.use_nodes=True;material.use_backface_culling=False;mesh.materials.append(material)
        obj=bpy.data.objects.new(p['name'],mesh);bpy.context.scene.collection.objects.link(obj);obj.location=[v/unit for v in origin]
        obj['mcpblender_foliage_card']=state['card_sha256'];bpy.context.view_layer.update()
        args={'name':obj.name,'sources':p['sources'],'uv_map':'CardUV','thin_foliage_mode':p['thin_foliage_mode']}
        bake=textures.inspect(args)
        if not bake['complete']:raise ValueError('Generated card is not bakeable: '+'; '.join(bake['unsupported_reasons']))
        ray=state['bake_ray_length_m']/unit
        if ray>1000:raise ValueError('Required card bake cage exceeds supported native-unit range')
        result={'object':obj.name,'card':state,'bake_parameters':args|{'expected_bake':bake['bake_sha256'],'cage_extrusion':ray,'max_ray_distance':ray*2,
                'maps':['BASE_COLOR','NORMAL','ROUGHNESS','ALPHA']},'bake_inspection':bake,
                'suggested_min_projection_coverage':max(0.,min(.99,state['projection']['geometry_coverage_fraction']*.8)),
                'next_step':'Choose output directory, texture resolution and min_projection_coverage explicitly, then call bake_textures. Review masks and baked result; sampled geometry coverage is an estimate.'}
        report_progress({'phase':'verified fitted card before handoff','triangles':state['triangles']})
        check_cancelled();success=True;return result
    finally:
        if not success:bpy.data.batch_remove(ids=tuple(set(bpy.data.user_map())-before))


def dispatch(command,p):
    if command=='inspect_foliage_card_views':return views(p)
    return inspect(p) if command=='inspect_foliage_card' else create(p)
