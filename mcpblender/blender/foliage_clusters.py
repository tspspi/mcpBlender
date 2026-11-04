"""Bounded semantic foliage planning and guarded independent native sources."""
import json
import math
import uuid
import bpy
from mathutils import Euler,Vector
from mcpblender import botany,foliage_clusters as clusters
from . import botanical_trees as trees,botanical_foliage as foliage,wind_preview,textures

COMMANDS={'inspect_botanical_foliage_clusters','create_botanical_foliage_cluster','inspect_botanical_foliage_cluster','remove_botanical_foliage_cluster'}
META='mcpblender_foliage_cluster'
OWNER='mcpblender_foliage_cluster_owner'
FORMAT='mcpblender-foliage-cluster-v1'
TABLES={'Collection':'collections','Object':'objects','Mesh':'meshes'}
SETTINGS=('anchor_order','max_leaves','max_triangles','max_clusters')


def prepare(p):
    from .bridge import check_cancelled,report_progress
    if bpy.context.mode!='OBJECT':raise ValueError('Foliage cluster planning requires Object mode')
    bpy.context.view_layer.update();check_cancelled()
    values=trees.inventory({'collection':p['collection']});state=values[-1];model=values[-2]
    if not state['valid'] or state['model_error'] or state['replacement_blockers'] or not state['foliage']:
        raise ValueError('Foliage clusters require a valid uncontrolled botanical master with foliage')
    roles=foliage.resolve_roles(state['foliage']);counts=[]
    for i in range(state['foliage']['recipe']['variants']):
        check_cancelled();mesh=roles['lo'+str(i)].data
        if len(mesh.polygons)>250000:raise ValueError('Foliage cluster template geometry budget exceeded')
        # Polygon triangulation count is exact for these validated native leaf
        # templates; no calc_loop_triangles cache mutation is needed for a plan.
        count=sum(len(face.vertices)-2 for face in mesh.polygons)
        counts.append(count)
    layout=foliage.build_layout(model,state['foliage']['recipe'])
    partition=clusters.partition(model,layout,counts,**{k:p[k] for k in SETTINGS},cancelled=check_cancelled,progress=report_progress)
    # Full tree guard includes native template geometry/UV/material bindings,
    # and placement. Pagination does not alter this guard.
    guard={'source_tree_sha256':state['tree_sha256'],'partition_sha256':partition['partition_sha256']}
    return values,roles,layout,partition,guard


def plan(p):
    values,roles,layout,partition,guard=prepare(p)
    offset=p['offset'];limit=p['limit']
    rows=[{k:v for k,v in row.items() if k!='leaf_indices'} for row in partition['clusters'][offset:offset+limit]]
    from .bridge import check_cancelled
    check_cancelled()
    return {k:v for k,v in partition.items() if k!='clusters'}|guard|{'collection':p['collection'],'plan_sha256':botany.digest(guard),
           'offset':offset,'limit':limit,'clusters':rows}


def sampling(material):
    """Admit only graphs whose sampling survives disconnected leaf merging."""
    record=textures.material_signature(material,thin_foliage_mode='FRONT_PBR')
    for node in material.node_tree.nodes:
        if node.type in {'UVMAP','TEX_COORD'} and getattr(node,'from_instancer',False):raise ValueError('Cluster merging does not support instancer UV sampling')
        if node.type=='TEX_IMAGE' and node.projection!='FLAT':raise ValueError('Cluster image textures require flat UV projection')
        if node.type=='OUTPUT_MATERIAL' and node.inputs['Displacement'].is_linked:raise ValueError('Cluster merging does not support shader displacement')
        if node.type=='GROUP':raise ValueError('Cluster merging does not support shader groups')
        if node.type=='TEX_COORD' and any(s.is_linked and s.name!='UV' for s in node.outputs):
            raise ValueError('Cluster merging requires UV texture coordinates, not object/generated coordinates')
        if node.type=='NEW_GEOMETRY' and any(s.is_linked and s.name!='Backfacing' for s in node.outputs):
            raise ValueError('Cluster merging supports only Backfacing geometry sampling')
        if node.bl_idname in {'ShaderNodeTexNoise','ShaderNodeTexVoronoi','ShaderNodeTexChecker'} and not node.inputs['Vector'].is_linked:
            raise ValueError('Cluster procedural textures require explicit UV-derived vectors')
        if node.type=='NORMAL_MAP' and node.space!='TANGENT':raise ValueError('Cluster normal maps require tangent space')
    return {'material':material.name,'sampling_sha256':botany.digest(record)}


def content_signature(owned):
    # The general native mesh record does not include UV active/render flags.
    # Bind these and explicit shading/edge flags as part of the snapshot too.
    return botany.digest({'native':wind_preview.signature(owned,metadata_key=META),
        'mesh_flags':[(m.name,{'uv':[(l.name,l.active_render) for l in m.uv_layers],
                              'active_uv':m.uv_layers.active_index,
                              'smooth':botany.digest_sequence(f.use_smooth for f in m.polygons),
                              'edges':botany.digest_sequence((e.use_seam,e.use_edge_sharp) for e in m.edges)})
                      for m in sorted((v for v in owned if isinstance(v,bpy.types.Mesh)),key=lambda m:m.name)]})


def portable(state):return {k:v for k,v in state.items() if k not in {'tree_sha256','recovery','operation_id'}}


def inspect(p):
    if bpy.context.mode!='OBJECT':raise ValueError('Foliage cluster inspection/removal requires Object mode')
    bpy.context.view_layer.update();col=bpy.data.collections.get(p['cluster_collection']);raw=col.get(META) if col else None
    if not isinstance(raw,str) or len(raw)>2*1024**2:raise ValueError('Owned foliage cluster not found or metadata exceeds budget')
    meta=json.loads(raw);owned=set();owner=meta.get('owner')
    if meta.get('format')!=FORMAT or not isinstance(owner,str) or len(owner)!=32 or any(c not in '0123456789abcdef' for c in owner) or len(meta.get('owned',[]))!=4:raise ValueError('Invalid foliage cluster inventory')
    for row in meta['owned']:
        table=TABLES.get(row['type']);value=getattr(bpy.data,table).get(row['name']) if table else None
        if value is None or value.get(OWNER)!=owner:raise ValueError('Foliage cluster owned ID missing/renamed or ownership changed')
        owned.add(value)
    if col not in owned or len(owned)!=4:raise ValueError('Invalid foliage cluster ownership')
    users=bpy.data.user_map();blockers=[];issues=[]
    for value in owned:
        if value.library or value.override_library or value.use_fake_user:blockers.append('Cluster ID became linked/persistent: '+value.name)
        for user in users.get(value,set()):
            if user in owned or value==col and isinstance(user,(bpy.types.Scene,bpy.types.Collection)) or isinstance(value,bpy.types.Object) and isinstance(user,bpy.types.Scene):continue
            blockers.append('External cluster reference: '+value.name)
        if isinstance(value,bpy.types.Collection) and (value.children or any(o not in owned for o in value.objects)):blockers.append('Foreign cluster collection membership')
        if isinstance(value,bpy.types.Object) and value.type=='MESH' and value.data.shape_keys:blockers.append('Remove cluster shape keys before owned deletion: '+value.name)
        if isinstance(value,bpy.types.Object) and (value.rigid_body or value.rigid_body_constraint):blockers.append('Remove cluster physics before owned deletion: '+value.name)
    current=content_signature(owned)
    if current!=meta['content_sha256']:issues.append('Foliage cluster native contents changed')
    if bpy.context.scene.unit_settings.scale_length!=meta['unit_scale']:issues.append('Scene unit scale differs from cluster snapshot')
    source=bpy.data.collections.get(meta['source_collection']);fresh=None;source_error=None
    if source:
        try:fresh=botany.digest(portable(trees.inspect({'collection':source.name})))==meta['source_content_sha256']
        except (ValueError,TypeError,KeyError) as exc:source_error=str(exc);fresh=False
    guard=botany.digest({'content':current,'meta':meta,'unit_scale':bpy.context.scene.unit_settings.scale_length,
                         'users':sorted((v.name,sorted((u.bl_rna.identifier,u.name) for u in users.get(v,set()))) for v in owned)})
    return col,owned,meta,{'cluster_collection':col.name,'cluster_sha256':guard,'valid':not issues and not blockers,'issues':issues,'ownership_blockers':sorted(set(blockers)),
        'object':meta['object'],'root':meta['root'],'cluster':meta['cluster'],'leaf_mapping':meta['leaf_mapping'],
        'normal_verification':meta['normal_verification'],'source_present':source is not None,'source_unchanged':fresh,'source_error':source_error,'uv_schema':meta['uv_schema'],
        'material_sampling_at_creation':meta['material_sampling'],'materials_shared':True,'display_offset_m':meta['display_offset_m'],
        'scope':'Independent static selected leaf mesh, including petioles; native corner UVs, material bindings and smoothing retained. Shared materials remain editable. No woody sleeves/shoots, wind animation, card, bake or optical/far-LOD equivalence.'}


def create(p):
    from .bridge import check_cancelled,report_progress,_bridge
    values,roles,layout,partition,guard=prepare(p)
    if p['expected_plan']!=botany.digest(guard):raise ValueError('Foliage cluster plan is stale; inspect again')
    if p['cluster_index']>=len(partition['clusters']):raise ValueError('Foliage cluster index not found')
    name=p['cluster_collection']
    if name in bpy.data.collections:raise ValueError('Foliage cluster collection already exists')
    row=partition['clusters'][p['cluster_index']];leaves=layout['leaves'];variants=sorted({leaves[i]['variant'] for i in row['leaf_indices']})
    schemas=[];meshes={};materials=[];material_records=[]
    for variant in variants:
        check_cancelled();mesh=roles['lo'+str(variant)].data;meshes[variant]=mesh
        if mesh.has_custom_normals:raise ValueError('Foliage cluster custom split normals are not supported')
        schemas.append({'names':[l.name for l in mesh.uv_layers],'active':mesh.uv_layers.active_index,'render':next((l.name for l in mesh.uv_layers if l.active_render),None)})
        for mat in mesh.materials:
            if mat not in materials:materials.append(mat);material_records.append(sampling(mat))
    if any(s!=schemas[0] for s in schemas[1:]):raise ValueError('Foliage cluster variants require identical UV names/order/active/render schema')
    schema=schemas[0];nv=sum(len(meshes[leaves[i]['variant']].vertices) for i in row['leaf_indices']);nl=sum(len(meshes[leaves[i]['variant']].loops) for i in row['leaf_indices'])
    if nv>250000 or nl>1000000:raise ValueError('Foliage cluster vertex/corner bake geometry budget exceeded')
    matrix=values[1].matrix_world.copy();unit=bpy.context.scene.unit_settings.scale_length;det=matrix.determinant()
    if any(not math.isfinite(v) for r in matrix for v in r) or not math.isfinite(det) or det<=1e-12 or not math.isfinite(unit) or unit<=0:raise ValueError('Cluster placement requires finite positive invertible scale')
    estimate=4*1024**2+nv*128+nl*(64+len(schema['names'])*16)
    if _bridge and _bridge.active:
        from mcpblender.storage import require_space
        policy=_bridge.active['storage'];policy.update(estimated_bytes=estimate,estimate_kind='foliage_cluster_checkpoint_size_heuristic')
        require_space(policy.get('path',_bridge.path.parent),estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind=policy['estimate_kind'])
    vertices=[];faces=[];smooth=[];slots=[];normals=[];uvs={n:[] for n in schema['names']};leaf_indices=[];branches=[];variant_indices=[];edge_flags={}
    for number,index in enumerate(row['leaf_indices']):
        check_cancelled();leaf=leaves[index];template=meshes[leaf['variant']];rotation=Euler(leaf['rotation'],'XYZ').to_matrix();offset=len(vertices)
        vertices.extend(Vector(leaf['position'])+leaf['scale']*(rotation@v.co) for v in template.vertices)
        leaf_indices.extend([index]*len(template.vertices));branches.extend([leaf['parent_branch_index']]*len(template.vertices));variant_indices.extend([leaf['variant']]*len(template.vertices))
        for face in template.polygons:
            faces.append(tuple(offset+i for i in face.vertices));smooth.append(face.use_smooth);slots.append(materials.index(template.materials[face.material_index]))
        normals.extend((rotation@n.vector).normalized() for n in template.corner_normals)
        for n in uvs:uvs[n].extend(tuple(item.uv) for item in template.uv_layers[n].data)
        for edge in template.edges:
            if edge.use_seam or edge.use_edge_sharp:edge_flags[tuple(sorted(offset+i for i in edge.vertices))]=(edge.use_seam,edge.use_edge_sharp)
        report_progress({'phase':'preparing bounded foliage cluster geometry','completed':number+1,'total':len(row['leaf_indices']),'estimated_bytes':estimate})
    before=set(bpy.data.user_map());success=False
    try:
        check_cancelled();col=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(col)
        root=bpy.data.objects.new(name+'_Root',None);col.objects.link(root);matrix.translation+=Vector(p['display_offset_m'])/unit;root.matrix_world=matrix
        mesh=bpy.data.meshes.new(name+'_Mesh');mesh.from_pydata(vertices,[],faces);mesh.update()
        for mat in materials:mesh.materials.append(mat)
        for face,slot,shading in zip(mesh.polygons,slots,smooth):face.material_index=slot;face.use_smooth=shading
        for n,coords in uvs.items():
            layer=mesh.uv_layers.new(name=n);layer.data.foreach_set('uv',[v for co in coords for v in co])
        if schema['names']:
            mesh.uv_layers.active_index=schema['active']
            if schema['render']:mesh.uv_layers[schema['render']].active_render=True
        for edge in mesh.edges:
            flags=edge_flags.get(tuple(sorted(edge.vertices)))
            if flags:edge.use_seam,edge.use_edge_sharp=flags
        mesh.normals_split_custom_set(normals);mesh.update()
        trees.attribute(mesh,'leaf_index','INT',leaf_indices);trees.attribute(mesh,'bot_branch_index','INT',branches);trees.attribute(mesh,'leaf_variant','INT',variant_indices)
        obj=bpy.data.objects.new(name+'_Leaves',mesh);col.objects.link(obj);obj.parent=root;bpy.context.view_layer.update();mesh.calc_loop_triangles()
        normal_matrix=matrix.to_3x3().inverted().transposed();normal_error=0.
        for i,(wanted,current) in enumerate(zip(normals,mesh.corner_normals)):
            if i%4096==0:check_cancelled()
            expected=(normal_matrix@wanted).normalized();actual=(normal_matrix@current.vector).normalized()
            error=(expected-actual).length
            if not math.isfinite(error):raise ValueError('Nonfinite foliage cluster native normal')
            normal_error=max(normal_error,error)
        # Blender stores custom normals in a quantized corner-space encoding.
        # Check every corner in world orientation rather than relying on flags.
        normal_limit=2*math.sin(math.radians(.05)/2)
        if normal_error>normal_limit:raise ValueError(f'Foliage cluster normal encoding exceeds 0.05 degree world-orientation tolerance: {math.degrees(2*math.asin(min(1,normal_error/2))):.6g} degrees')
        normal_verification={'corners':len(normals),'max_world_normal_chord_error':normal_error,'max_allowed_world_normal_chord_error':normal_limit,'max_world_normal_error_degrees':math.degrees(2*math.asin(min(1,normal_error/2))),'max_allowed_world_normal_error_degrees':.05,
                             'scope':'Every transformed template corner normal compared with native encoded readback; chord distance of unit world vectors, not optical equivalence.'}
        if len(mesh.loop_triangles)!=row['source_triangles']:raise ValueError('Foliage cluster native triangle count differs from plan')
        if any(abs(root.matrix_world[i][j]-matrix[i][j])>max(1e-5,abs(matrix[i][j])*1e-6) for i in range(4) for j in range(4)):raise ValueError('Foliage cluster native placement differs from source')
        # Adding material users is intentional; source geometry/ownership remains untouched.
        fresh=trees.inspect({'collection':p['collection']})
        if fresh['tree_sha256']!=guard['source_tree_sha256']:raise ValueError('Source changed during foliage cluster staging')
        if material_records!=[sampling(m) for m in materials]:raise ValueError('Foliage cluster material sampling changed during staging')
        owner=uuid.uuid4().hex;owned=set(bpy.data.user_map())-before
        if len(owned)!=4:raise ValueError('Unexpected foliage cluster native inventory')
        for value in owned:value[OWNER]=owner
        meta={'format':FORMAT,'owner':owner,'owned':[{'type':v.bl_rna.identifier,'name':v.name} for v in sorted(owned,key=lambda v:(v.bl_rna.identifier,v.name))],
              'source_collection':p['collection'],'source_content_sha256':botany.digest(portable(fresh)),'source_plan':botany.digest(guard),
              'unit_scale':unit,'root':root.name,'object':obj.name,'display_offset_m':p['display_offset_m'],
              'cluster':{k:v for k,v in row.items() if k!='leaf_indices'},'leaf_mapping':[{'index':i,'id':leaves[i]['id'],'branch_index':leaves[i]['parent_branch_index'],'variant':leaves[i]['variant']} for i in row['leaf_indices']],
              'uv_schema':schema,'normal_verification':normal_verification,'material_sampling':material_records,'content_sha256':content_signature(owned)}
        col[META]=json.dumps(meta,sort_keys=True,allow_nan=False);result=inspect({'cluster_collection':name})[-1]
        if not result['valid'] or not result['source_unchanged']:raise ValueError('Foliage cluster publication failed verification')
        report_progress({'phase':'verified foliage cluster before handoff'});check_cancelled();success=True;return result
    finally:
        if not success:bpy.data.batch_remove(ids=tuple(set(bpy.data.user_map())-before))


def dispatch(command,p):
    if command=='inspect_botanical_foliage_clusters':return plan(p)
    if command=='create_botanical_foliage_cluster':return create(p)
    col,owned,meta,result=inspect(p)
    if command=='inspect_botanical_foliage_cluster':return result
    if p['expected_cluster']!=result['cluster_sha256']:raise ValueError('Foliage cluster fingerprint is stale; inspect again')
    if result['ownership_blockers']:raise ValueError('; '.join(result['ownership_blockers']))
    if result['issues'] and not p.get('discard_derived_edits',False):raise ValueError('Edited foliage clusters require discard_derived_edits')
    from .bridge import check_cancelled
    check_cancelled();bpy.data.batch_remove(ids=tuple(owned));return {'removed':p['cluster_collection'],'source_preserved':True}
