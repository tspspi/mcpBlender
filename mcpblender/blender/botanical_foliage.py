"""Owned instanced leaf components, coordinated by botanical tree lifecycle."""
import json
import math
import bpy
from mathutils import Vector
from mcpblender import botany,foliage
from . import assemblies,assembly_realization as realization
from .botanical_trees import attribute,frame
COMMANDS={'inspect_botanical_coverage','inspect_foliage_material','configure_foliage_material','plan_leaf_template','create_leaf_template','plan_botanical_foliage','configure_botanical_foliage','remove_botanical_foliage','list_botanical_leaves'}


def material(name):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.use_backface_culling=False;tree=mat.node_tree;tree.nodes.clear()
    def node(kind,name):
        result=tree.nodes.new(kind);result.name=name;return result
    geometry=node('ShaderNodeNewGeometry','Surface Side');mix=node('ShaderNodeMixRGB','Leaf Sides')
    mix.inputs[1].default_value=(.055,.20,.012,1);mix.inputs[2].default_value=(.12,.28,.035,1);tree.links.new(geometry.outputs['Backfacing'],mix.inputs[0])
    surface=node('ShaderNodeBsdfPrincipled','Leaf Surface');surface.inputs['Roughness'].default_value=.65;tree.links.new(mix.outputs[0],surface.inputs['Base Color'])
    translucent=node('ShaderNodeBsdfTranslucent','Thin Backlighting');translucent.inputs['Color'].default_value=(.22,.42,.06,1)
    blend=node('ShaderNodeMixShader','Optical Mix');blend.inputs[0].default_value=.22;tree.links.new(surface.outputs[0],blend.inputs[1]);tree.links.new(translucent.outputs[0],blend.inputs[2])
    transparent=node('ShaderNodeBsdfTransparent','Culled Backface')
    enabled=node('ShaderNodeMath','Backface Enabled');enabled.operation='MULTIPLY';enabled.inputs[1].default_value=0
    tree.links.new(geometry.outputs['Backfacing'],enabled.inputs[0])
    cull=node('ShaderNodeMixShader','Backface Cull');tree.links.new(enabled.outputs[0],cull.inputs[0]);tree.links.new(blend.outputs[0],cull.inputs[1]);tree.links.new(transparent.outputs[0],cull.inputs[2])
    output=node('ShaderNodeOutputMaterial','Output');tree.links.new(cull.outputs[0],output.inputs['Surface'])
    mat['mcpblender_thin_foliage']=json.dumps({'version':1,'double_sided':True,'alpha_mode':'OPAQUE_GEOMETRY','roughness':.65,'translucent_mix':.22,'transmission_color':[.22,.42,.06],
        'scope':'Native thin-surface artistic mix, separate from double-sidedness and physical thickness. No alpha-card optics, glTF shader equivalence or radiometric calibration.'})
    return mat


def optical_settings(mat):
    n=mat.node_tree.nodes
    return {'front_color':list(n['Leaf Sides'].inputs[1].default_value),'back_color':list(n['Leaf Sides'].inputs[2].default_value),
      'transmission_color':list(n['Thin Backlighting'].inputs['Color'].default_value),'roughness':n['Leaf Surface'].inputs['Roughness'].default_value,
      'translucent_mix':n['Optical Mix'].inputs[0].default_value,'double_sided':n['Backface Enabled'].inputs[1].default_value==0}


def inspect_material(p):
    mat=bpy.data.materials.get(p['material'])
    if not mat or not mat.node_tree or not mat.get('mcpblender_thin_foliage'):raise ValueError('Managed thin-foliage material not found')
    settings=optical_settings(mat)
    return {'material':mat.name,'settings':settings,'material_sha256':botany.digest(assemblies.record(mat)),'users':mat.users,
            'scope':'Shared native thin-surface material. Shader mix is artistic, not physical thickness or an alpha-mask texture. Editing affects every material user; no interchange equivalence.'}


def configure_material(p):
    from .bridge import check_cancelled
    state=inspect_material(p);mat=bpy.data.materials[p['material']]
    if state['material_sha256']!=p['expected_material']:raise ValueError('Foliage material fingerprint is stale')
    if mat.library or mat.override_library or mat.animation_data or mat.node_tree.animation_data:raise ValueError('Optical editing requires local unanimated material')
    targets={'front_color':('Leaf Sides',1),'back_color':('Leaf Sides',2),'transmission_color':('Thin Backlighting','Color'),'roughness':('Leaf Surface','Roughness'),'translucent_mix':('Optical Mix',0),'double_sided':('Backface Enabled',1)}
    for key,(node,socket) in targets.items():
        if p.get(key) is not None and mat.node_tree.nodes[node].inputs[socket].is_linked:raise ValueError('Optical setting is linked: '+key)
    original=state['settings'];metadata=mat['mcpblender_thin_foliage'];changes={k:p[k] for k in original if p.get(k) is not None}
    def apply(values):
        n=mat.node_tree.nodes
        for key,node,socket in (('front_color','Leaf Sides',1),('back_color','Leaf Sides',2),('transmission_color','Thin Backlighting','Color'),('roughness','Leaf Surface','Roughness'),('translucent_mix','Optical Mix',0)):
            if key in values:n[node].inputs[socket].default_value=values[key]
        if 'double_sided' in values:n['Backface Enabled'].inputs[1].default_value=0 if values['double_sided'] else 1;mat.use_backface_culling=not values['double_sided']
    try:
        check_cancelled();apply(changes)
        info=json.loads(metadata);info.update(optical_settings(mat));mat['mcpblender_thin_foliage']=json.dumps(info,sort_keys=True,allow_nan=False)
        check_cancelled();return inspect_material(p)
    except BaseException:apply(original);mat['mcpblender_thin_foliage']=metadata;raise


def leaf_mesh(name,shape,leaf_material,bark):
    spec=foliage.leaf_mesh(shape);mesh=bpy.data.meshes.new(name)
    try:
        mesh.from_pydata(spec['vertices'],[],spec['faces']);mesh.update();uv=mesh.uv_layers.new(name='LeafUV')
        mesh.materials.append(leaf_material);mesh.materials.append(bark)
        for polygon,part in zip(mesh.polygons,spec['parts']):
            polygon.material_index=part;polygon.use_smooth=True
            for loop in polygon.loop_indices:uv.data[loop].uv=spec['uv'][mesh.loops[loop].vertex_index]
        return mesh
    except BaseException:bpy.data.meshes.remove(mesh);raise


def build_layout(model,cfg):
    from .bridge import check_cancelled,report_progress
    ticks=[0]
    def cancel():
        ticks[0]+=1
        if ticks[0]%32==0:check_cancelled()
    check_cancelled();return foliage.generate(model,cfg,progress=report_progress,cancelled=cancel)


def instance_population(name,population,points,prototypes,layout,source_indices=None):
    """Build shared native rest instances; callers own staged rollback/IDs."""
    for key,kind,values in (
      ('leaf_rotation','FLOAT_VECTOR',[v['rotation'] for v in layout['leaves']]),('leaf_scale','FLOAT_VECTOR',[(v['scale'],)*3 for v in layout['leaves']]),
      ('leaf_variant','INT',[v['variant'] for v in layout['leaves']]),('bot_branch_index','INT',[v['parent_branch_index'] for v in layout['leaves']]),
      ('leaf_index','INT',source_indices if source_indices is not None else list(range(len(layout['leaves'])))),('leaf_phase','FLOAT',[v['phase'] for v in layout['leaves']]),('leaf_flutter','FLOAT',[v['flutter'] for v in layout['leaves']])):attribute(points,key,kind,values)
    group=bpy.data.node_groups.new(name+'_LeafInstances','GeometryNodeTree')
    group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    nodes=group.nodes;links=group.links;source=nodes.new('NodeGroupInput');output=nodes.new('NodeGroupOutput');collection=nodes.new('GeometryNodeCollectionInfo')
    collection.inputs['Collection'].default_value=prototypes;collection.inputs['Separate Children'].default_value=True;collection.inputs['Reset Children'].default_value=True
    instance=nodes.new('GeometryNodeInstanceOnPoints');instance.inputs['Pick Instance'].default_value=True
    links.new(source.outputs['Geometry'],instance.inputs['Points']);links.new(collection.outputs['Instances'],instance.inputs['Instance']);links.new(instance.outputs['Instances'],output.inputs['Geometry'])
    for key,target,kind in (('leaf_rotation','Rotation','FLOAT_VECTOR'),('leaf_scale','Scale','FLOAT_VECTOR'),('leaf_variant','Instance Index','INT')):
        node=nodes.new('GeometryNodeInputNamedAttribute');node.data_type=kind;node.inputs['Name'].default_value=key;links.new(node.outputs['Attribute'],instance.inputs[target])
    modifier=population.modifiers.new('Botanical Leaf Instances','NODES');modifier.node_group=group
    return group


def create_component(name,col,root,model,cfg,bark,old_material=None):
    from .bridge import check_cancelled,report_progress
    layout=build_layout(model,cfg);p=layout['recipe'];roles={}
    def own(key,value):roles[key]=value;return value
    component=own('fc',bpy.data.collections.new(name+'_Foliage'));col.children.link(component)
    prototypes=own('pc',bpy.data.collections.new(name+'_LeafSources'))
    points=own('pm',bpy.data.meshes.new(name+'_LeafPoints'));points.from_pydata([v['position'] for v in layout['leaves']],[],[]);points.update()
    population=own('po',bpy.data.objects.new(name+'_Leaves',points));component.objects.link(population);population.parent=root
    leafmat=old_material or material(name+'_LeafSurface')
    for i in range(p['variants']):
        shape=foliage.variant_shape(p,i)
        mesh=own('lm'+str(i),leaf_mesh(name+'_LeafMesh'+str(i),shape,leafmat,bark))
        obj=own('lo'+str(i),bpy.data.objects.new(name+'_Leaf'+str(i),mesh));prototypes.objects.link(obj)
    own('gn',instance_population(name,population,points,prototypes,layout))
    # Shared prototypes stay unlinked from scene; shoot stems use a small mesh.
    verts=[];faces=[];branch_ids=[];lookup={v['id']:i for i,v in enumerate(model['branches'])}
    for i,shoot in enumerate(layout['shoots']):
        if i%64==0:check_cancelled();report_progress({'phase':'building foliage shoots','shoots':i,'total_shoots':len(layout['shoots'])})
        tangent=Vector(shoot['end'])-Vector(shoot['start']);x,z=frame(tangent);offset=len(verts)
        for center,radius in ((shoot['start'],.0025),(shoot['end'],.001)):
            for j in range(4):verts.append(Vector(center)+radius*(x*math.cos(j*math.pi/2)+z*math.sin(j*math.pi/2)));branch_ids.append(lookup[shoot['parent_branch_id']])
        for j in range(4):faces.append((offset+j,offset+(j+1)%4,offset+4+(j+1)%4,offset+4+j))
        faces.extend((tuple(offset+j for j in reversed(range(4))),tuple(offset+4+j for j in range(4))))
    stems=own('sm',bpy.data.meshes.new(name+'_ShootMesh'));stems.from_pydata(verts,[],faces);stems.update();stems.materials.append(bark);attribute(stems,'bot_branch_index','INT',branch_ids)
    stem_object=own('so',bpy.data.objects.new(name+'_Shoots',stems));component.objects.link(stem_object);stem_object.parent=root
    text=own('ft',bpy.data.texts.new(name+'_Foliage.json'));text.use_fake_user=False;text.use_module=False;text.write(json.dumps(foliage.compact(layout),sort_keys=True,allow_nan=False));component['mcpblender_foliage_model']=text
    # Keep the unlinked prototype collection as an explicit native dependency.
    component['mcpblender_leaf_sources']=prototypes
    result={'version':1,'roles':{k:{'type':v.bl_rna.identifier,'name':v.name} for k,v in roles.items()},'material':leafmat.name,'recipe':p,'compact_sha256':botany.digest(foliage.compact(layout)),
       'metrics':layout['metrics'],'content_sha256':None}
    bpy.context.view_layer.update();result['content_sha256']=component_signature(roles)
    return result


def resolve_roles(meta):
    collections={'Collection':bpy.data.collections,'Object':bpy.data.objects,'Mesh':bpy.data.meshes,'Text':bpy.data.texts,'GeometryNodeTree':bpy.data.node_groups}
    result={}
    for key,item in meta['roles'].items():
        collection=collections.get(item['type']);value=collection.get(item['name']) if collection is not None else None
        if value is None:raise ValueError('Foliage owned ID is missing/changed: '+item['name'])
        result[key]=value
    if len(set(result.values()))!=len(result):raise ValueError('Foliage ownership inventory repeats native IDs')
    return result


def component_signature(roles):
    records=[]
    for key,value in sorted(roles.items()):
        if isinstance(value,bpy.types.Mesh):data=realization.mesh_record(value)
        elif isinstance(value,bpy.types.Text):data=botany.digest(value.as_string())
        elif isinstance(value,bpy.types.Collection):data={'objects':sorted(o.name for o in value.objects),'children':sorted(c.name for c in value.children),'custom':assemblies.idprops(value)}
        elif isinstance(value,bpy.types.Object):
            data={'data':value.data.name,'parent':value.parent.name if value.parent else None,'basis':[list(r) for r in value.matrix_basis],'inverse':[list(r) for r in value.matrix_parent_inverse],
                  'flags':{k:getattr(value,k) for k in ('hide_viewport','hide_render','hide_select')},
                  'modifiers':[(m.name,m.type,m.show_viewport,m.show_render,assemblies.idprops(m),m.node_group.name if m.type=='NODES' and m.node_group else None) for m in value.modifiers]}
        else:data=assemblies.record(value)
        records.append((key,data))
    return botany.digest(records)


def component(col,root,meta):
    roles=resolve_roles(meta);issues=[];blockers=[];model_error=None
    if set(roles['fc'].objects)!={roles['po'],roles['so']} or roles['fc'].children or set(roles['pc'].objects)!={v for k,v in roles.items() if k.startswith('lo')} or roles['pc'].children:raise ValueError('Foliage collection membership changed')
    if roles['fc'] not in set(col.children) or any(o.parent!=root or set(o.users_collection)!={roles['fc']} for o in (roles['po'],roles['so'])):blockers.append('Foliage parent/membership changed')
    from .lod_management import parents
    if set(parents(roles['fc']))!={col}:blockers.append('Foliage collection gained external links')
    if parents(roles['pc']):blockers.append('Leaf prototype collection gained scene links')
    for k,obj in roles.items():
        if isinstance(obj,bpy.types.Object) and (obj.constraints or obj.animation_data or obj.rigid_body or obj.data.shape_keys):blockers.append('Foliage gained controls: '+obj.name)
    if component_signature(roles)!=meta['content_sha256']:issues.append('Foliage derived contents changed')
    try:
        compact=json.loads(roles['ft'].as_string())
        if compact.get('format')!=foliage.FORMAT or compact.get('generator')!=foliage.GENERATOR:raise ValueError('Unsupported foliage generator')
        if botany.digest(compact)!=meta['compact_sha256']:raise ValueError('Canonical foliage recipe changed')
    except (ValueError,TypeError):model_error='Canonical foliage model changed';issues.append(model_error)
    return roles,issues,blockers,model_error


def dispatch(command,p):
    from . import botanical_trees as trees
    if command=='inspect_foliage_material':return inspect_material(p)
    if command=='configure_foliage_material':return configure_material(p)
    if command=='plan_leaf_template':
        spec=foliage.leaf_mesh(p['leaf']);return {'leaf_sha256':botany.digest(spec),'recipe':spec['recipe'],'vertices':len(spec['vertices']),'triangles':spec['triangles'],'blade_area':spec['blade_area'],'scope':spec['scope']}
    if command=='create_leaf_template':
        from .bridge import check_cancelled
        check_cancelled();spec=foliage.leaf_mesh(p['leaf'])
        if botany.digest(spec)!=p['expected_leaf']:raise ValueError('Leaf shape fingerprint is stale')
        if p['name'] in bpy.data.objects:raise ValueError('Leaf object already exists')
        before=set(bpy.data.user_map());success=False
        try:
            leafmat=material(p['name']+'_Surface');bark=bpy.data.materials.new(p['name']+'_Petiole');bark.use_nodes=True;bark.diffuse_color=(.08,.12,.02,1)
            petiole=bark.node_tree.nodes.get('Principled BSDF');petiole.inputs['Base Color'].default_value=(.08,.12,.02,1);petiole.inputs['Roughness'].default_value=.8
            mesh=leaf_mesh(p['name']+'_Mesh',p['leaf'],leafmat,bark);obj=bpy.data.objects.new(p['name'],mesh);bpy.context.scene.collection.objects.link(obj)
            unit_scale=bpy.context.scene.unit_settings.scale_length
            if not math.isfinite(unit_scale) or unit_scale<=0:raise ValueError('Positive finite scene unit scale required')
            obj.scale=(1/unit_scale,)*3
            obj['mcpblender_leaf_template']=json.dumps(spec['recipe'],sort_keys=True)
            bpy.context.view_layer.update();points=[obj.matrix_world@v.co for v in mesh.vertices]
            result={'object':obj.name,'mesh':realization.mesh_record(mesh),'leaf_sha256':p['expected_leaf'],'recipe':spec['recipe'],
                    'scene_unit_scale':unit_scale,'world_bounds_m':{k:[fn(v[i] for v in points)*unit_scale for i in range(3)] for k,fn in (('min',min),('max',max))}}
            check_cancelled();success=True;return result
        finally:
            if not success:bpy.data.batch_remove(ids=tuple(set(bpy.data.user_map())-before))
    values=trees.inventory(p);state=values[-1];model=values[-2]
    if state['ownership_blockers'] or state['replacement_blockers'] or state['model_error']:raise ValueError('Foliage requires an owned botanical master with valid canonical models and root controls')
    if state['issues'] and command!='plan_botanical_foliage' and not (command=='configure_botanical_foliage' and p.get('discard_derived_edits')):raise ValueError('Derived edits require discard_derived_edits=true explicitly')
    if command=='inspect_botanical_coverage':
        from mcpblender import foliage_coverage
        meta=state.get('foliage');cfg=p.get('foliage') or (meta['recipe'] if meta else None)
        if cfg is None:raise ValueError('Supply a foliage recipe or configure foliage first')
        from .bridge import check_cancelled,report_progress
        result=foliage_coverage.analyze(model,build_layout(model,cfg),resolution=p['resolution'],views=p['views'],margin=p['margin'],max_projected_triangles=p['max_projected_triangles'],include_masks=p['include_masks'],progress=report_progress,cancelled=check_cancelled)
        return result|{'tree_sha256':state['tree_sha256'],'proposed_recipe':p.get('foliage') is not None}
    if command=='list_botanical_leaves':
        meta=json.loads(values[0][trees.META]).get('foliage')
        if not meta:raise ValueError('Tree has no foliage component')
        layout=build_layout(model,meta['recipe']);return {'total':len(layout['leaves']),'items':layout['leaves'][p['offset']:p['offset']+p['limit']],'offset':p['offset']}
    if command=='plan_botanical_foliage':
        layout=build_layout(model,p['foliage']);return {'foliage_sha256':botany.digest(foliage.compact(layout)),'metrics':layout['metrics'],'source_model_sha256':state['model_sha256'],'recipe':layout['recipe']}
    if state['tree_sha256']!=p['expected_tree']:raise ValueError('Botanical tree fingerprint is stale')
    cfg=False if command=='remove_botanical_foliage' else p['foliage']
    if cfg:
        layout=build_layout(model,cfg)
        if botany.digest(foliage.compact(layout))!=p['expected_foliage']:raise ValueError('Foliage plan fingerprint is stale')
    return trees.regenerate({'collection':p['collection'],'recipe':state['recipe'],'expected_model':state['model_sha256'],'expected_tree':p['expected_tree'],
        'location':[0,0,0],'radial_sides':state['geometry']['radial_sides'],'bark_tile_length':state['geometry']['bark_tile_length'],
        'preserve_placement':True,'discard_derived_edits':p.get('discard_derived_edits',False),'foliage':cfg,'secondary_uv_policy':p.get('secondary_uv_policy','PRESERVE')})
