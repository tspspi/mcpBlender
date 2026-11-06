"""Owned native leaf selection from guarded first-hit capture identities."""
import json
import uuid
import bpy
from mcpblender import botany,capture_data,component_ids,exr_scanline
from . import botanical_capture as capture,botanical_foliage as foliage,botanical_trees as trees,assemblies,wind_preview,depth_assets,subset_columns,subset_templates

META='mcpblender_botanical_subset';OWNER='mcpblender_botanical_subset_owner'
FORMAT='mcpblender-native-leaf-subset-v1';KEEP='mcp_subset_keep'
POINT_STORAGE='COMPACT_SOURCE_IDS_V1'
TABLES={'Collection':'collections','Object':'objects','Mesh':'meshes','GeometryNodeTree':'node_groups','Material':'materials','Image':'images'}
COMMANDS={'inspect_botanical_subset_source','create_botanical_subset','inspect_botanical_subset','remove_botanical_subset'}


def materials_state(materials):
    from .bridge import check_cancelled
    deps,_,blockers=assemblies.dependencies(set(materials),assemblies.references(),nested_leaf=False)
    if blockers:raise ValueError('Unsupported subset material dependencies: '+'; '.join(blockers))
    rows=[]
    for value in sorted(deps,key=lambda v:(type(v).__name__,v.name)):
        check_cancelled()
        if value.library or value.override_library or getattr(value,'animation_data',None):raise ValueError('Subset requires local static shader dependencies')
        if isinstance(value,bpy.types.Image):
            row,_,error=assemblies.image_record(value,check_cancelled)
            if error or row.get('storage')!='PACKED':raise ValueError(error or 'Subset requires packed images')
        else:
            row=assemblies.record(value)
            tree=value.node_tree if isinstance(value,bpy.types.Material) else value if isinstance(value,bpy.types.NodeTree) else None
            if tree:row['shader_state']=capture.shader_state(tree)
        rows.append(row)
    return botany.digest(rows)


def plan(p):
    from .bridge import check_cancelled,report_progress
    if bpy.context.mode!='OBJECT':raise ValueError('Native subsets require Object mode')
    if p['selection'] not in {'OBSERVED','UNOBSERVED','COLUMN_COMPLEMENT'} or p['render_role'] not in depth_assets.RAY_ROLES:raise ValueError('Invalid subset selection/role')
    column=p['selection']=='COLUMN_COMPLEMENT'
    if column and len(p['views'])!=1:raise ValueError('COLUMN_COMPLEMENT requires exactly one capture view')
    structure_role=p.get('structure_render_role')
    if structure_role is not None and (structure_role not in depth_assets.RAY_ROLES or not p['include_structure']):raise ValueError('Valid structure_render_role requires include_structure=true')
    root,proof,meta,rows=capture_data.source({'directory':p['directory'],'views':p['views'],'max_pixels':1048576,'max_total_pixels':p['max_total_pixels']},report_progress,check_cancelled)
    contract=meta.get('component_ids')
    if not contract:raise ValueError('Subset selection requires recapture with component_ids=true')
    values,_,fresh=capture.source(meta['options'])
    binding='source_content_sha256' if meta.get('source_content_sha256') else 'source_tree_sha256'
    for key in (binding,'resource_sha256','frame','source_root_matrix_world','scene_unit_scale','component_ids'):
        if fresh[key]!=meta[key]:raise ValueError('Subset capture source changed: '+key)
    roles=foliage.resolve_roles(values[-1]['foliage']) if values[-1]['foliage'] else {}
    if not roles:raise ValueError('Subset requires native source foliage')
    if roles['pm'].attributes.get(KEEP):raise ValueError('Reserved subset selection attribute already exists')
    indices=[v.value for v in roles['pm'].attributes['leaf_index'].data]
    native_ids=roles['pm'].attributes.get('id')
    if (native_ids and (native_ids.domain!='POINT' or native_ids.data_type!='INT' or [v.value for v in native_ids.data]!=indices)) or not native_ids and indices!=list(range(len(indices))):raise ValueError('Source native IDs do not match semantic leaf indices')
    if indices and not roles['po'].visible_get():raise ValueError('Source leaf population must be visible in the viewport for native verification; source visibility was preserved')
    observed=set();reports=[];column_plan=None
    for view,row in rows:
        names=['TreeCapture.Combined.A','TreeCapture.MCP_SurfaceWeight.X',*component_ids.channels()]
        decoded=exr_scanline.decode(root/row['file'],names,expected_sha256=row['sha256'],cancelled=check_cancelled,progress=report_progress)
        channels=decoded['channels'];mask,report=component_ids.filter_mask(decoded,channels[names[1]],channels[names[2]],contract,'LEAVES',p['alpha_threshold'],cancelled=check_cancelled)
        for i,keep in enumerate(mask):
            if i%8192==0:check_cancelled()
            if keep:observed.add(round(channels[names[2]][i]/channels[names[1]][i])-1)
        if column:
            grid=[round(channels[names[2]][i]/channels[names[1]][i]) if keep else 0 for i,keep in enumerate(mask)]
            column_plan=subset_columns.plan(meta,view,row,grid)
        reports.append({'view':view['view'],'exr_sha256':row['sha256'],**report})
    selected=sorted(set(indices) if column else observed if p['selection']=='OBSERVED' else set(indices)-observed)
    if not selected and not p['include_structure']:raise ValueError('Subset would contain no geometry')
    flags={k:k in depth_assets.RAY_ROLES[p['render_role']] for k in depth_assets.RAY_FLAGS}
    mats={m for obj in [*values[2],*(v for k,v in roles.items() if k.startswith('lo') or k=='so')] for m in obj.data.materials}
    if None in mats:raise ValueError('Subset requires populated material slots')
    summary={'format':FORMAT,'capture_sha256':meta['capture_sha256'],'snapshot_sha256':proof['source_sha256'],
             'source_collection':meta['collection'],'source_tree_sha256':fresh['source_tree_sha256'],
             'capture_source_tree_sha256':meta['source_tree_sha256'],'source_content_sha256':fresh['source_content_sha256'],'source_unit_scale':meta['scene_unit_scale'],
             'source_root_matrix_world':meta['source_root_matrix_world'],'source_components_sha256':contract['components_sha256'],
             'settings':{k:p[k] for k in ('views','selection','include_structure','render_role','alpha_threshold','max_total_pixels')},
             'source_leaf_count':len(indices),'observed_leaf_count':len(observed),'observed_indices_sha256':botany.digest(sorted(observed)),
             'point_storage':POINT_STORAGE,'selected_leaf_count':len(selected),'selected_indices_sha256':botany.digest(selected),'selected_index_preview':selected[:16],
             'views':reports,'ray_visibility':flags,'materials':sorted(m.name for m in mats),'material_dependencies_sha256':materials_state(mats),
             'scope':'Static native first-hit leaf subset with semantic IDs and unchanged template geometry/poses. Observations are view/sample dependent, not full visibility. Shared guarded materials; new instancer object-dependent random values may differ. Source geometry/visibility unchanged; no automatic complementary visibility, template reduction, wind or optical equivalence.'}
    if column:
        for obj in (v for k,v in roles.items() if k.startswith('lo')):
            for slot in obj.material_slots:subset_columns.outputs(slot.material)
        summary['column_complement']=column_plan;summary['scope']=subset_columns.SCOPE
    if p.get('template_reduction') is not None:
        summary['template_reduction']=subset_templates.plan(roles,selected,p['template_reduction'])
        summary['scope']=summary['scope'].replace('unchanged template geometry/poses','unchanged instance poses').replace('template reduction, wind or optical equivalence','wind or optical equivalence')+' Optional private shared-template reduction records sampled error/area policy; no optical or wind certificate.'
    if structure_role is not None:
        summary['settings']['structure_render_role']=structure_role
        summary['structure_ray_visibility']={k:k in depth_assets.RAY_ROLES[structure_role] for k in depth_assets.RAY_FLAGS}
    return values,roles,selected,summary|{'plan_sha256':botany.digest(summary)}


def compact_points(mesh,chosen):
    """Keep selected source rows and all their semantic/wind attributes."""
    import bmesh
    from .bridge import check_cancelled,report_progress
    check_cancelled();report_progress({'phase':'compacting native subset points','source_points':len(mesh.vertices),'selected_points':len(chosen)})
    indices=[v.value for v in mesh.attributes['leaf_index'].data]
    bm=bmesh.new()
    try:
        bm.from_mesh(mesh);bm.verts.ensure_lookup_table();remove=[]
        for i,vertex in enumerate(bm.verts):
            if i%8192==0:check_cancelled()
            if indices[vertex.index] not in chosen:remove.append(vertex)
        bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(mesh)
    finally:bm.free()
    mesh.update();check_cancelled()


def verify_compact_points(mesh,plan):
    if plan.get('point_storage')!=POINT_STORAGE:raise ValueError('Unsupported subset point storage recipe')
    count=plan['selected_leaf_count'];source_count=plan['source_leaf_count']
    if type(count) is not int or type(source_count) is not int or not 0<=count<=source_count<=250000 or len(mesh.vertices)!=count:raise ValueError('Subset compact point count changed')
    def values(name,kind):
        attr=mesh.attributes.get(name)
        if attr is None or attr.domain!='POINT' or attr.data_type!=kind or len(attr.data)!=count:raise ValueError('Subset compact attribute changed: '+name)
        return [v.value for v in attr.data]
    indices=values('leaf_index','INT')
    if values('id','INT')!=indices or len(set(indices))!=count or any(not 0<=v<source_count for v in indices) or botany.digest(sorted(indices))!=plan['selected_indices_sha256']:raise ValueError('Subset compact semantic IDs changed')
    if not all(values(KEEP,'BOOLEAN')):raise ValueError('Subset compact point membership changed')


def content(owned,root):
    # Display visibility and root placement are permitted user controls.
    resources={v for v in owned if not isinstance(v,(bpy.types.Object,bpy.types.Collection))}
    objects=[];collections=[]
    for value in sorted(owned,key=lambda v:(v.bl_rna.identifier,v.name)):
        if isinstance(value,bpy.types.Collection):
            collections.append((value.name,sorted(o.name for o in value.objects),sorted(c.name for c in value.children),{k:v for k,v in assemblies.idprops(value).items() if k not in {META,OWNER}}))
        elif isinstance(value,bpy.types.Object):
            if value.animation_data or value.constraints or value.rigid_body or value.rigid_body_constraint or value.instance_type!='NONE' or value.type=='MESH' and (value.data.shape_keys or value.vertex_groups):raise ValueError('Subset gained unsupported animation/constraints/physics')
            objects.append({'name':value.name,'data':value.data.name if value.data else None,'parent':value.parent.name if value.parent else None,'parent_type':value.parent_type,
                'basis':None if value==root else [list(r) for r in value.matrix_basis],'inverse':[list(r) for r in value.matrix_parent_inverse],
                'materials':[(slot.link,slot.material.name if slot.material else None) for slot in value.material_slots],
                'flags':{k:getattr(value,k) for k in (*depth_assets.RAY_FLAGS,'is_holdout','is_shadow_catcher','hide_select','show_instancer_for_viewport','show_instancer_for_render')},
                'modifiers':[(m.name,m.type,assemblies.props(m),assemblies.pointers(m),assemblies.idprops(m)) for m in value.modifiers]})
    data={'resources':wind_preview.signature(resources,metadata_key=META,packed_images=any(isinstance(v,bpy.types.Image) for v in resources)),'objects':objects,'collections':collections}
    private_shaders={v.name:capture.shader_state(v.node_tree) for v in resources if isinstance(v,bpy.types.Material)}
    if private_shaders:data['private_shaders']=private_shaders
    return botany.digest(data)


def inspect(p):
    from .bridge import check_cancelled
    if bpy.context.mode!='OBJECT':raise ValueError('Native subsets require Object mode')
    col=bpy.data.collections.get(p['subset_collection']);raw=col.get(META) if col else None
    if not isinstance(raw,str) or len(raw)>1024**2:raise ValueError('Owned native subset not found or invalid metadata')
    meta=json.loads(raw);owner=meta.get('owner');planned=meta.get('plan',{})
    if meta.get('format')!=FORMAT or not isinstance(owner,str) or len(owner)!=32 or any(v not in '0123456789abcdef' for v in owner) or not 5<=len(meta.get('owned',[]))<=128:raise ValueError('Invalid subset ownership')
    if planned.get('format')!=FORMAT or planned.get('plan_sha256')!=botany.digest({k:v for k,v in planned.items() if k!='plan_sha256'}):raise ValueError('Subset plan changed')
    owned=set()
    for row in meta['owned']:
        table=TABLES.get(row['type']);value=getattr(bpy.data,table).get(row['name']) if table else None
        if value is None or value.get(OWNER)!=owner:raise ValueError('Subset owned resource missing/renamed or ownership changed')
        owned.add(value)
    root=bpy.data.objects.get(meta['root']);population=bpy.data.objects.get(meta['population'])
    if len(owned)!=len(meta['owned']) or col not in owned or root not in owned or population not in owned:raise ValueError('Subset inventory changed')
    issues=[];blockers=[];users=bpy.data.user_map()
    for value in owned:
        check_cancelled()
        if value.library or value.override_library or value.use_fake_user:blockers.append('Linked/persistent subset resource: '+value.name)
        for user in users.get(value,set()):
            if user in owned or value==col and user==bpy.context.scene or isinstance(value,bpy.types.Object) and user==bpy.context.scene:continue
            blockers.append('External subset reference: '+value.name)
        if isinstance(value,bpy.types.Collection) and any(v not in owned for v in [*value.objects,*value.children]):blockers.append('Foreign subset member: '+value.name)
    current=None
    try:
        if root.parent or root.type!='EMPTY' or col not in bpy.context.scene.collection.children.values() or bpy.context.scene.unit_settings.scale_length!=planned['source_unit_scale']:raise ValueError('Subset placement/units changed')
        capture_data.pose([list(r) for r in root.matrix_basis])
        if 'point_storage' in planned:verify_compact_points(population.data,planned)
        current=content(owned,root)
        if current!=meta['content_sha256']:issues.append('Subset native content changed')
        mats=[bpy.data.materials.get(name) for name in planned['materials']]
        if None in mats or materials_state(mats)!=planned['material_dependencies_sha256']:issues.append('Subset shared shader dependencies changed')
    except (ValueError,TypeError,KeyError,AttributeError) as exc:issues.append(str(exc))
    fresh=None
    if bpy.data.collections.get(planned['source_collection']):
        try:fresh=capture.portable_tree(trees.inspect({'collection':planned['source_collection']}))==planned['source_content_sha256']
        except (ValueError,TypeError,KeyError):fresh=False
    guard=botany.digest({'meta':meta,'content':current,'issues':issues,'root_basis':[list(r) for r in root.matrix_basis],
                        'users':sorted((v.bl_rna.identifier,v.name,sorted((u.bl_rna.identifier,u.name) for u in users.get(v,set()))) for v in owned)})
    return col,owned,{'subset_collection':col.name,'subset_sha256':guard,'valid':not issues and not blockers,'issues':issues,'ownership_blockers':sorted(set(blockers)),
                     'root':root.name,'population':population.name,'selected_leaf_count':planned['selected_leaf_count'],'plan':planned,'source_unchanged':fresh,'capture_files_required':False}


def create(p):
    from .bridge import check_cancelled,report_progress,_bridge
    values,roles,selected,planned=plan(p)
    if p['expected_plan']!=planned['plan_sha256']:raise ValueError('Subset source plan is stale')
    if p['subset_collection'] in bpy.data.collections:raise ValueError('Subset collection already exists')
    if _bridge and _bridge.active:
        from mcpblender.storage import require_space
        meshes=[v.data for k,v in roles.items() if k.startswith('lo')]
        if p['include_structure']:meshes += [v.data for v in [*values[2],roles['so']]]
        estimate=2*planned.get('column_complement',{}).get('decoded_image_bytes',0)+16*1024**2+len(roles['pm'].vertices)*512+sum(len(m.vertices)*128+len(m.loops)*64 for m in meshes)
        policy=_bridge.active['storage'];policy.update(estimated_bytes=estimate,estimate_kind='native_subset_checkpoint_heuristic')
        require_space(policy.get('path',_bridge.path.parent),estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind=policy['estimate_kind'])
    before=set(bpy.data.user_map());success=False
    try:
        col=bpy.data.collections.new(p['subset_collection']);bpy.context.scene.collection.children.link(col)
        prefix='MCPSubset-'+uuid.uuid4().hex[:12]
        root=bpy.data.objects.new(prefix+'-Root',None);col.objects.link(root);root.matrix_world=values[1].matrix_world.copy()
        prototypes=bpy.data.collections.new(prefix+'-Sources');col['mcpblender_leaf_sources']=prototypes
        mapping={}
        for i in range(values[-1]['foliage']['recipe']['variants']):
            source=roles['lo'+str(i)]
            if 'template_reduction' in planned:
                mesh,report=subset_templates.build(source.data,p['template_reduction'])
                expected={k:v for k,v in planned['template_reduction']['variants'][i].items() if k not in {'variant','instances'}}
                if report!=expected:raise ValueError('Template reduction differs from pinned plan')
            else:mesh=source.data.copy()
            obj=source.copy();obj.name=prefix+'-Leaf'+str(i);obj.data=mesh;prototypes.objects.link(obj);mapping[source.name]=obj.name
        population=roles['po'].copy();population.name=prefix+'-Leaves';population.data=roles['pm'].copy();population.parent=root;col.objects.link(population)
        group=roles['gn'].copy();population.modifiers[0].node_group=group
        for node in group.nodes:
            if node.bl_idname=='GeometryNodeCollectionInfo' and node.inputs['Collection'].default_value==roles['pc']:node.inputs['Collection'].default_value=prototypes
        indices=[v.value for v in population.data.attributes['leaf_index'].data]
        if population.data.attributes.get('id'):population.data.attributes.remove(population.data.attributes['id'])
        trees.attribute(population.data,'id','INT',indices)
        chosen=set(selected);trees.attribute(population.data,KEEP,'BOOLEAN',[v in chosen for v in indices])
        compact_points(population.data,chosen)
        verify_compact_points(population.data,planned)
        instance=next(n for n in group.nodes if n.bl_idname=='GeometryNodeInstanceOnPoints')
        for link in list(instance.inputs['Selection'].links):group.links.remove(link)
        instance.inputs['Selection'].default_value=True
        if 'column_complement' in planned:subset_columns.install(p['directory'],prefix,root,prototypes,population,planned)
        objects=[population]
        if p['include_structure']:
            for i,source in enumerate([*values[2],roles['so']]):
                check_cancelled();obj=source.copy();obj.name=prefix+'-Structure'+str(i);obj.data=source.data.copy();obj.parent=root;col.objects.link(obj);objects.append(obj)
        for obj in objects:
            flags=planned['ray_visibility'] if obj==population else planned.get('structure_ray_visibility',planned['ray_visibility'])
            for key,value in flags.items():setattr(obj,key,value)
        bpy.context.view_layer.update()
        expected={}
        for number,item in enumerate(bpy.context.evaluated_depsgraph_get().object_instances):
            if number%2048==0:check_cancelled();report_progress({'phase':'verifying native subset instances','scene_instances_scanned':number})
            if number>=4000000:raise ValueError('Subset native verification scene-instance budget exceeded')
            if item.is_instance and item.parent and item.parent.original==roles['po']:
                expected[tuple(item.persistent_id)]=(mapping[item.object.original.name],tuple(v for r in item.matrix_world for v in r))
        actual={}
        for number,item in enumerate(bpy.context.evaluated_depsgraph_get().object_instances):
            if number%2048==0:check_cancelled();report_progress({'phase':'verifying native subset instances','scene_instances_scanned':number})
            if number>=4000000:raise ValueError('Subset native verification scene-instance budget exceeded')
            if item.is_instance and item.parent and item.parent.original==population:
                key=tuple(item.persistent_id)
                if key in actual:raise ValueError('Duplicate subset native instance identity')
                actual[key]=(item.object.original.name,tuple(v for r in item.matrix_world for v in r))
        if len(expected)!=len(indices) or {key[0] for key in expected}!=set(indices) or len(actual)!=len(selected) or {key[0] for key in actual}!=chosen or any(key not in expected or value!=expected[key] for key,value in actual.items()):raise ValueError('Subset native identity/pose differs from source')
        if trees.inspect({'collection':planned['source_collection']})['tree_sha256']!=planned['source_tree_sha256']:raise ValueError('Source changed during subset staging')
        col.hide_render=True;col.hide_viewport=True
        owned=set(bpy.data.user_map())-before;owner=uuid.uuid4().hex
        if any(v.bl_rna.identifier not in TABLES for v in owned):raise ValueError('Unsupported subset ownership type')
        for value in owned:value[OWNER]=owner
        meta={'format':FORMAT,'owner':owner,'root':root.name,'population':population.name,'plan':planned,
              'owned':[{'type':v.bl_rna.identifier,'name':v.name} for v in sorted(owned,key=lambda v:(v.bl_rna.identifier,v.name))],
              'content_sha256':content(owned,root)}
        col[META]=json.dumps(meta,sort_keys=True,allow_nan=False);result=inspect(p)[-1]
        if not result['valid'] or not result['source_unchanged']:raise ValueError('Subset publication verification failed: '+str(result['issues']+result['ownership_blockers']))
        check_cancelled();report_progress({'phase':'verified native leaf subset','selected_leaves':len(selected)});success=True;return result
    finally:
        if not success:bpy.data.batch_remove(ids=tuple(set(bpy.data.user_map())-before))


def dispatch(command,p):
    if command=='inspect_botanical_subset_source':return plan(p)[-1]
    if command=='create_botanical_subset':return create(p)
    col,owned,result=inspect(p)
    if command=='inspect_botanical_subset':return result
    if p['expected_subset']!=result['subset_sha256']:raise ValueError('Subset guard is stale')
    if not result['valid']:raise ValueError('Subset edited or externally referenced; restore before removal')
    from .bridge import check_cancelled
    check_cancelled();count=len(owned);bpy.data.batch_remove(ids=tuple(owned));return {'removed':p['subset_collection'],'private_datablocks':count,'source_preserved':True}
