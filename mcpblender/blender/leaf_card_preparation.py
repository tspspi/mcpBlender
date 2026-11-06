"""Owned normal-aligned blade targets for the existing isolated texture baker."""
import json,uuid
import bpy,bmesh
from mathutils import Vector,Matrix
from mcpblender import botany,card_fit
from mcpblender.uv_math import inset_tile
from . import vegetation_bake as preparation,vegetation_materials,textures,lods,assemblies
from .assets import require_static

RECIPE='NATIVE_THIN_BLADE_CARD_PREPARATION_V1'


def material(mat):
    textures.material_signature(mat,thin_foliage_mode='FRONT_PBR')
    nodes=mat.node_tree.nodes
    if {n.name:n.bl_idname for n in nodes}!=textures.THIN_NODES:raise ValueError('Blade cards require the constant managed thin-leaf graph')
    expected=[('Leaf Sides',0,'Surface Side','Backfacing'),('Leaf Surface','Base Color','Leaf Sides',0),
              ('Optical Mix',1,'Leaf Surface',0),('Optical Mix',2,'Thin Backlighting',0),
              ('Backface Enabled',0,'Surface Side','Backfacing'),('Backface Cull',0,'Backface Enabled',0),
              ('Backface Cull',1,'Optical Mix',0),('Backface Cull',2,'Culled Backface',0),('Output','Surface','Backface Cull',0)]
    wanted={(nodes[t].inputs[s].as_pointer(),nodes[f].outputs[o].as_pointer()) for t,s,f,o in expected}
    if {(l.to_socket.as_pointer(),l.from_socket.as_pointer()) for l in mat.node_tree.links}!=wanted:raise ValueError('Blade cards cannot preserve custom thin-leaf input sampling')
    if nodes['Leaf Surface'].inputs['Alpha'].default_value!=1:raise ValueError('Blade cards require opaque source blade geometry')


def plan(p):
    from .bridge import check_cancelled,report_progress
    if bpy.context.mode!='OBJECT':raise ValueError('Object mode required for blade-card preparation')
    if p['uv_strategy']!='NEW' or p.get('chart_layout'):raise ValueError('Blade cards require NEW UVs without chart_layout')
    available,guard=preparation.objects(p);chosen=p.get('assets') or [key for key in available if key.startswith('leaf-')]
    if not chosen or any(key not in available or not key.startswith('leaf-') for key in chosen):raise ValueError('Blade cards require available shared leaf-template roles only')
    selected={key:available[key] for key in chosen};unit=bpy.context.scene.unit_settings.scale_length;rows={};corners=0
    for role,obj in selected.items():
        check_cancelled();report_progress({'phase':'planning shared blade-card targets','asset':role});require_static(obj);mesh=obj.data
        if obj.library or obj.override_library or mesh.library or mesh.override_library or obj.parent or obj.modifiers or mesh.shape_keys or mesh.animation_data or mesh.has_custom_normals or obj.matrix_basis!=Matrix.Identity(4):raise ValueError('Blade cards require local static identity-placed shared templates')
        summary=lods.summary(mesh);corners+=len(mesh.loops)+4
        if corners>p['max_corners']:raise ValueError('Blade-card preparation corner budget exceeded')
        if len(mesh.materials)!=2 or summary['used_material_indices']!=[0,1]:raise ValueError('Blade cards require blade/petiole material regions')
        regions=[{v for face in mesh.polygons if face.material_index==i for v in face.vertices} for i in (0,1)]
        if regions[0]&regions[1]:raise ValueError('Blade/petiole vertices must be disconnected to preserve blade normals')
        material(mesh.materials[0]);mesh.calc_loop_triangles();triangles=[t for t in mesh.loop_triangles if t.material_index==0]
        normal=sum((t.normal*t.area for t in triangles),Vector())
        if normal.length<1e-10:raise ValueError('Blade has no stable mean geometric normal')
        normal.normalize();rotation=normal.rotation_difference(Vector((0,0,1))).to_matrix().to_4x4()
        coords=[rotation@v.co*unit for v in mesh.vertices];points=[[list(coords[i]) for i in t.vertices] for t in triangles]
        fit=card_fit.fit(points,view='TOP',outline='RECTANGLE',padding=p['blade_cards']['padding'],standoff_m=p['blade_cards']['standoff_m'],resolution=p['blade_cards']['resolution'],max_vertices=4,max_triangles=250000,cancelled=check_cancelled,progress=report_progress)
        uv=[v for pair in fit['uv'] for v in pair]
        if p['tile_padding_pixels']:uv=inset_tile(uv,p['texture_width'],p['texture_height'],p['tile_padding_pixels'],True)
        else:uv=[p['margin']+(1-2*p['margin'])*v for v in uv]
        rows[role]={'source_object':obj.name,'mesh':textures.mesh_signature(obj,mesh),'source_mesh_sha256':summary['mesh_sha256'],
                    'source_leaf_material_sha256':botany.digest(assemblies.record(mesh.materials[0])),
                    'alignment_matrix':[list(r) for r in rotation],'mean_normal_local':list(normal),'card':fit,'target_uv':uv,
                    'midplane_offset_m':fit['source_depth_m']/2+p['blade_cards']['standoff_m']}
    options={k:p[k] for k in ('blade_cards','uv_map','margin','uv_strategy','tile_padding_pixels','texture_width','texture_height','max_corners')}
    result={'format':preparation.FORMAT,'recipe':RECIPE,'source_guard':guard,'scene_unit_scale':unit,'assets':rows,'available_assets':[k for k in available if k.startswith('leaf-')],
            'source_materials':vegetation_materials.contract(selected),'options':options,'corners':corners,'private_images_copied':0,'estimated_copy_bytes':corners*256,
            'source_sampling_changes':[],'can_prepare':True,'unsupported_reasons':[],
            'scope':'Independent constant-managed-thin blade source copies in template-native coordinates (not placed-instance density) and two-triangle normal-aligned rectangular bake targets. Source geometry/visibility/materials preserved. Existing NORMAL/ALPHA baker is explicit. NORMAL/ALPHA bundles are data inputs with a neutral PBR output; they do not adopt native color/thin/back-side optics; no card adoption, exact source UV/shape equivalence, wind or far-budget certificate.'}
    return selected,result|{'plan_sha256':botany.digest(result)}


def create(p):
    from .bridge import check_cancelled,report_progress,_bridge
    selected,source=plan(p)
    if source['plan_sha256']!=p['expected_plan']:raise ValueError('Blade-card source plan is stale')
    if bpy.data.collections.get(p['bake_collection']):raise ValueError('Bake collection already exists')
    if _bridge and _bridge.active:
        from mcpblender.storage import require_space
        policy=_bridge.active['storage'];estimate=max(16*1024**2,source['estimated_copy_bytes']);policy.update(estimated_bytes=estimate,estimate_kind='blade_card_preparation_copy_heuristic');require_space(policy['path'] if policy.get('path') else _bridge.path.parent,estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind=policy['estimate_kind'])
    owned=set();owner=uuid.uuid4().hex;success=False;components={}
    def own(value):owned.add(value);value[preparation.OWNER]=owner;value.use_fake_user=False;return value
    try:
        col=own(bpy.data.collections.new(p['bake_collection']));bpy.context.scene.collection.children.link(col);unit=source['scene_unit_scale']
        for role,obj in selected.items():
            check_cancelled();report_progress({'phase':'preparing shared blade-card target','asset':role,'completed_assets':len(components),'total_assets':len(selected)})
            row=source['assets'][role];prefix=col.name+'_'+role;mesh=own(obj.data.copy());bm=bmesh.new()
            try:
                bm.from_mesh(mesh);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=0],context='FACES');loose=[v for v in bm.verts if not v.link_faces]
                if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
                bm.to_mesh(mesh)
            finally:bm.free()
            mesh.materials.clear();mesh.materials.append(own(obj.data.materials[0].copy()));mesh.update()
            high=own(bpy.data.objects.new(prefix+'_BladeSource',mesh));col.objects.link(high);high.matrix_world=Matrix(row['alignment_matrix']);high.hide_render=True
            fit=row['card'];origin=Vector([sum(v[a] for v in fit['vertices_m'])/4/unit for a in range(3)]);target_mesh=own(bpy.data.meshes.new(prefix+'_CardMesh'));target_mesh.from_pydata([Vector(v)/unit-origin for v in fit['vertices_m']],[],[(0,1,2,3)]);target_mesh.update();uv=target_mesh.uv_layers.new(name=p['uv_map']);uv.data.foreach_set('uv',row['target_uv'])
            mat=own(bpy.data.materials.new(prefix+'_BakeTarget'));mat.use_nodes=True;target_mesh.materials.append(mat);target=own(bpy.data.objects.new(prefix+'_Card',target_mesh));col.objects.link(target);target.location=origin;target.hide_render=True;bpy.context.view_layer.update()
            inputs={'name':target.name,'sources':[high.name],'cage':None,'uv_map':p['uv_map'],'thin_foliage_mode':'FRONT_PBR'};info=textures.inspect(inputs)
            if not info['complete']:raise ValueError('Blade-card target is not bakeable: '+'; '.join(info['unsupported_reasons']))
            ray=fit['bake_ray_length_m']/unit
            if ray>1000:raise ValueError('Blade-card projection cage exceeds native range')
            components[role]={'name':target.name,'source_object':obj.name,'prepared_source_object':high.name,'inspect_texture_bake':inputs,'initial_bake_sha256':info['bake_sha256'],'material_adapters':info['material_adapters'],
                'prepared_mesh':textures.mesh_signature(target,target_mesh),'prepared_attributes':[a for a in assemblies.attribute_records(target_mesh) if not a['name'].startswith('.')],
                'bake_parameters':inputs|{'expected_bake':info['bake_sha256'],'maps':['NORMAL','ALPHA'],'width':p['texture_width'],'height':p['texture_height'],'cage_extrusion':ray,'max_ray_distance':ray*2,'min_projection_coverage':max(0.,min(.99,fit['projection']['geometry_coverage_fraction']*.8))},
                'card_recipe':row,'source_template_sha256':row['source_mesh_sha256']}
        check_cancelled()
        if plan(p)[-1]['plan_sha256']!=p['expected_plan']:raise ValueError('Source changed during blade-card preparation')
        meta={'format':preparation.FORMAT,'content_signature_version':2,'revision':0,'owner':owner,'source':source,'components':components,'owned':[{'type':v.bl_rna.identifier,'name':v.name} for v in sorted(owned,key=lambda v:(v.bl_rna.identifier,v.name))]};meta['content_sha256']=preparation.content(owned,version=2);col[preparation.META]=json.dumps(meta,sort_keys=True,allow_nan=False);result=preparation.inspect({'bake_collection':col.name})[-1]
        if not result['valid']:raise ValueError('Blade-card preparation failed owned verification')
        success=True;return result
    finally:
        if not success and owned:bpy.data.batch_remove(ids=tuple(owned))
        bpy.context.view_layer.update()
