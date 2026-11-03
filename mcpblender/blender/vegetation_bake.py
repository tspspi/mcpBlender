"""Independent vegetation mesh/material copies with pinned sampling and bake UVs."""
import json
import math
import uuid
import bpy
from mathutils import Matrix
from mcpblender import botany
from . import vegetation_materials,vegetation_lods,botanical_trees,botanical_foliage,textures,uv,wind_preview,assemblies
from .assets import active_object,finished,require_static

META='mcpblender_vegetation_bake'
OWNER='mcpblender_vegetation_bake_owner'
FORMAT='mcpblender-vegetation-bake-v1'
TABLES={'Collection':'collections','Object':'objects','Mesh':'meshes','Material':'materials','Image':'images','ShaderNodeTree':'node_groups'}
COMMANDS={'inspect_vegetation_bake_source','prepare_vegetation_bake','inspect_vegetation_bake','remove_vegetation_bake','refresh_vegetation_bake'}


def objects(p):
    if p.get('lod_collection'):
        col,owned,meta,state=vegetation_lods.inspect(p)
        if not state['valid']:raise ValueError('Valid unchanged native LOD profile required')
        return vegetation_materials.lod_objects(col,meta),state['lods_sha256']
    values=botanical_trees.inventory(p)
    if not values[-1]['valid']:raise ValueError('Valid unchanged botanical tree required')
    result={'wood':values[2][0]};foliage=values[-1]['foliage']
    if foliage and foliage['metrics']['leaves']:
        roles=botanical_foliage.resolve_roles(foliage);result['shoots']=roles['so']
        result.update({f'leaf-{i}':roles['lo'+str(i)] for i in range(foliage['recipe']['variants'])})
    return result,values[-1]['tree_sha256']


def static_matrix(obj,depth=0):
    # Hidden objects may have an unevaluated matrix_world immediately after load.
    # Canonical bake sources use static object parenting; compose their channels.
    if depth>64:raise ValueError('Bake source parent depth exceeds 64')
    require_static(obj)
    if not obj.parent:return obj.matrix_basis.copy()
    if obj.parent_type!='OBJECT':raise ValueError('Static object parenting required for bake placement')
    return static_matrix(obj.parent,depth+1) @ obj.matrix_parent_inverse @ obj.matrix_basis


def sampling(obj):
    """Enumerate named and implicit UV consumers before the worker changes active UV."""
    original=next((l.name for l in obj.data.uv_layers if l.active_render),None)
    if original is None and obj.data.uv_layers:original=obj.data.uv_layers.active.name
    rows=[]
    for mat in obj.data.materials:
        if mat is None or not mat.use_nodes:raise ValueError('Every source material slot requires a supported node material')
        for node in mat.node_tree.nodes:
            if getattr(node,'from_instancer',False) or node.type=='NEW_GEOMETRY' and node.outputs['Tangent'].is_linked:raise ValueError('Instancer UVs and implicit geometry tangents cannot be preserved on independent bake copies')
            kind=None;name=None
            if node.type=='UVMAP':kind='NAMED';name=node.uv_map or original
            elif node.type=='NORMAL_MAP' and node.space=='TANGENT':kind='NAMED';name=node.uv_map or original
            elif node.type=='TANGENT' and node.direction_type=='UV_MAP':kind='NAMED';name=node.uv_map or original
            elif node.type=='TEX_IMAGE' and not node.inputs['Vector'].is_linked:kind='IMPLICIT';name=original
            elif node.type=='TEX_COORD' and node.outputs['UV'].is_linked:kind='IMPLICIT';name=original
            if kind:rows.append({'material':mat.name,'node':node.name,'kind':kind,'uv_map':name,'missing':not name or name not in obj.data.uv_layers})
    return original,rows


def plan(p):
    from .bridge import check_cancelled
    if bpy.context.mode!='OBJECT':raise ValueError('Object mode required for bake preparation')
    bpy.context.view_layer.update();available,guard=objects(p)
    chosen=p.get('assets') or list(available)
    if any(key not in available for key in chosen):raise ValueError('Unknown asset role; inspect without assets for the available roles')
    selected={key:available[key] for key in chosen};corners=sum(len(o.data.loops) for o in selected.values())
    if corners>p['max_corners']:raise ValueError('Vegetation bake preparation corner budget exceeded')
    rows={};reasons=[];changes=[]
    for role,obj in selected.items():
        check_cancelled();require_static(obj);mesh=obj.data;uv.check_size(mesh)
        if obj.library or mesh.library or obj.override_library or mesh.override_library or obj.modifiers or mesh.shape_keys or mesh.animation_data or not mesh.polygons:raise ValueError('Preparation requires local static base meshes without modifiers or shape keys')
        if obj.parent:require_static(obj.parent)
        if p.get('uv_strategy','NEW')=='NEW':
            if p['uv_map'] in mesh.uv_layers:raise ValueError('Target bake UV already exists on '+role+'; choose EXISTING or a new name')
            if len(mesh.uv_layers)>=8:raise ValueError('Source has no free UV channel for '+role)
        elif p['uv_map'] not in mesh.uv_layers:raise ValueError('Existing target bake UV missing on '+role)
        original,consumers=sampling(obj)
        missing=[r for r in consumers if r['missing']]
        if missing and p['missing_uv_policy']=='REFUSE':reasons.append(role+': source UVs missing; explicitly choose BAKE_LAYOUT to generate copy-only sampling coordinates')
        if missing:changes.append({'asset':role,'consumers':missing,'policy':p['missing_uv_policy'],'scope':'Missing source coordinates replaced by the new bake layout on copies only; appearance may change.'})
        witness=textures.mesh_signature(obj,mesh);witness['matrix']=[list(row) for row in static_matrix(obj)]
        rows[role]={'source_object':obj.name,'mesh':witness,'attributes':[v for v in assemblies.attribute_records(mesh) if not v['name'].startswith('.')],'original_render_uv':original,'uv_consumers':consumers}
    contract=vegetation_materials.contract(selected)
    options={k:p[k] for k in ('uv_map','margin','missing_uv_policy','max_corners')};options['uv_strategy']=p.get('uv_strategy','NEW');options['max_uv_repairs']=p.get('max_uv_repairs',64)
    if p.get('tile_padding_pixels',0):options.update({k:p[k] for k in ('tile_padding_pixels','texture_width','texture_height')})
    images={n.image for obj in selected.values() for mat in obj.data.materials for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.get(vegetation_lods.OWNER)}
    result={'format':FORMAT,'source_guard':guard,'source_materials':contract,'assets':rows,'available_assets':list(available),'options':options,'corners':corners,
            'private_images_copied':len(images),'estimated_copy_bytes':corners*128+sum(i.size[0]*i.size[1]*4+(i.packed_file.size if i.packed_file else 0) for i in images),'source_sampling_changes':changes,'can_prepare':not reasons,'unsupported_reasons':reasons,
            'scope':'Owned static base meshes and private materials, preserved original UVs and a new or reused verified bake map. No image baking, material adoption or optical equivalence.'}
    result['plan_sha256']=botany.digest(result)
    return selected,result


def pin(material,original,target,missing_policy,mesh):
    tree=material.node_tree;changed=False
    def uvnode(name):
        nonlocal changed
        if not name or name not in mesh.uv_layers:
            if missing_policy!='BAKE_LAYOUT':raise ValueError('Missing source sampling UV')
            name=target
        node=tree.nodes.new('ShaderNodeUVMap');node.uv_map=name;changed=True
        return node.outputs['UV']
    for node in list(tree.nodes):
        if node.type=='TEX_IMAGE' and not node.inputs['Vector'].is_linked:tree.links.new(uvnode(original),node.inputs['Vector'])
        elif node.type=='TEX_COORD':
            for link in list(node.outputs['UV'].links):tree.links.new(uvnode(original),link.to_socket)
        elif node.type=='UVMAP' or node.type=='NORMAL_MAP' and node.space=='TANGENT' or node.type=='TANGENT' and node.direction_type=='UV_MAP':
            name=node.uv_map or original
            if not name or name not in mesh.uv_layers:
                if missing_policy!='BAKE_LAYOUT':raise ValueError('Missing named source sampling UV')
                name=target
            if node.uv_map!=name:node.uv_map=name;changed=True
    # A changed graph is no longer an editable managed procedural recipe. The
    # original settings remain in the source witness, while the thin-leaf adapter
    # marker stays intact for explicit FRONT_PBR conversion.
    if changed and material.get('mcpblender_botanical_surface'):del material['mcpblender_botanical_surface']


def repair_charts(obj,uv_map,margin,budget):
    from .bridge import check_cancelled,report_progress
    repaired=set()
    for attempt in range(3):
        layer=obj.data.uv_layers[uv_map]
        _,_,triangles=uv.layout(obj.data,layer,obj.matrix_world,1024,1024)
        result=uv.overlaps(triangles,200000)
        if not result['complete']:raise ValueError('Bake UV overlap validation exceeded its comparison budget')
        if not result['face_pair_count']:return sorted(repaired)
        faces={face for pair in result['face_pairs'] for face in pair}
        if result['pairs_truncated'] or len(repaired|faces)>budget or attempt==2:raise ValueError('Bake UV chart repair budget exceeded; no overlapping layout accepted')
        check_cancelled();report_progress({'phase':'repairing generated bake UV charts','faces':len(faces),'attempt':attempt+1})
        areas=dict.fromkeys(faces,0.)
        for triangle in triangles:
            if triangle[4] in areas:areas[triangle[4]]+=abs(uv.signed_area(triangle[5]))
        for index,face in enumerate(sorted(faces)):
            loops=list(obj.data.polygons[face].loop_indices)
            radius=max(1e-5,math.sqrt(areas[face]/(len(loops)*.5*math.sin(2*math.pi/len(loops)))))
            for corner,loop in enumerate(loops):
                angle=2*math.pi*corner/len(loops)
                layer.data[loop].uv=(1.25+index/1024+radius*math.cos(angle),.5+index/65536+radius*math.sin(angle))
        # Separate charts sit outside the original tile until packing, so they
        # cannot accidentally join an existing island through matching UV edges.
        obj.data.uv_layers.active=layer
        with active_object(obj):
            finished(bpy.ops.object.mode_set(mode='EDIT'));finished(bpy.ops.mesh.select_all(action='SELECT'));finished(bpy.ops.uv.select_all(action='SELECT'))
            finished(bpy.ops.uv.pack_islands(rotate=True,scale=True,margin=margin,margin_method='SCALED'))
            finished(bpy.ops.object.mode_set(mode='OBJECT'))
        repaired.update(faces)


def content(owned):
    return botany.digest({'native':wind_preview.signature(owned,metadata_key=META),
        'materials':{m.name:textures.material_signature(m,thin_foliage_mode='FRONT_PBR') for m in owned if isinstance(m,bpy.types.Material)}})


def inspect(p):
    col=bpy.data.collections.get(p['bake_collection'])
    if not col or not isinstance(col.get(META),str) or len(col[META])>4*1024**2:raise ValueError('Owned vegetation bake preparation not found')
    meta=json.loads(col[META]);owned=set()
    if meta.get('format')!=FORMAT or not 1<=len(meta.get('owned',[]))<=512 or len(meta.get('owner',''))!=32:raise ValueError('Invalid vegetation bake ownership')
    for entry in meta['owned']:
        table=TABLES.get(entry['type']);value=getattr(bpy.data,table).get(entry['name']) if table else None
        if value is None or value.get(OWNER)!=meta['owner']:raise ValueError('Owned bake ID missing/renamed or owner changed')
        owned.add(value)
    if col not in owned or len(owned)!=len(meta['owned']):raise ValueError('Duplicate bake ownership')
    users=bpy.data.user_map();blockers=[];embedded={v.node_tree for v in owned if isinstance(v,bpy.types.Material) and v.node_tree}
    for value in owned:
        if value.library or value.override_library or value.use_fake_user:blockers.append('Linked/persistent owned ID: '+value.name)
        for user in users.get(value,set()):
            if user in owned or user in embedded or value==col and isinstance(user,(bpy.types.Scene,bpy.types.Collection)) or isinstance(value,bpy.types.Object) and isinstance(user,bpy.types.Scene):continue
            blockers.append('External reference: '+value.name)
        if isinstance(value,bpy.types.Collection) and any(v not in owned for v in [*value.objects,*value.children]):blockers.append('Foreign collection member: '+value.name)
    current=content(owned)
    guard=botany.digest({'meta':meta,'content':current,'users':sorted((v.bl_rna.identifier,v.name,sorted((u.bl_rna.identifier,u.name) for u in users.get(v,set()))) for v in owned)})
    return col,owned,meta,{'bake_collection':col.name,'preparation_sha256':guard,'valid':current==meta['content_sha256'] and not blockers,'content_changed':current!=meta['content_sha256'],
            'ownership_blockers':sorted(set(blockers)),'components':meta['components'],'source':meta['source'],'source_sampling_changes':meta['source']['source_sampling_changes'],'revision':meta.get('revision',0),'scope':meta['source']['scope']}


def create(p):
    from .bridge import check_cancelled,report_progress
    selected,source=plan(p)
    if source['plan_sha256']!=p['expected_plan']:raise ValueError('Vegetation bake source plan is stale')
    if not source['can_prepare']:raise ValueError('; '.join(source['unsupported_reasons']))
    if bpy.data.collections.get(p['bake_collection']):raise ValueError('Bake collection already exists')
    owned=set();owner=uuid.uuid4().hex;success=False;components={};image_copies={};group_copies={}
    settings=bpy.context.scene.tool_settings;mode=tuple(settings.mesh_select_mode);sync=settings.use_uv_select_sync
    def own(value):owned.add(value);value[OWNER]=owner;value.use_fake_user=False;return value
    try:
        col=own(bpy.data.collections.new(p['bake_collection']));bpy.context.scene.collection.children.link(col)
        anchor=own(bpy.data.objects.new(col.name+'_Placement',None));col.objects.link(anchor)
        for role,obj in selected.items():
            check_cancelled();report_progress({'phase':'preparing vegetation bake UVs','asset':role,'native_call_interruptible':False,'completed_assets':len(components),'total_assets':len(selected)})
            mesh=own(obj.data.copy());target=own(bpy.data.objects.new(col.name+'_'+role,mesh));col.objects.link(target)
            # Parent inverse stores the full affine matrix without decomposing
            # shear into object transform channels; this anchor stays independent.
            target.parent=anchor;target.matrix_parent_inverse=static_matrix(obj);target.matrix_basis=Matrix.Identity(4)
            # Keep source maps/attributes/order; isolate every slot to pin its own
            # source mesh's render coordinates without changing shared originals.
            materials={}
            for i,mat in enumerate(list(mesh.materials)):
                if mat not in materials:
                    copied=own(mat.copy());materials[mat]=copied
                    for node in copied.node_tree.nodes:
                        if node.type=='TEX_IMAGE' and node.image and node.image.get(vegetation_lods.OWNER):
                            original=node.image
                            if original not in image_copies:image_copies[original]=own(original.copy())
                            node.image=image_copies[original]
                        if node.type=='GROUP' and node.node_tree and node.node_tree.get(vegetation_lods.OWNER):
                            original=node.node_tree
                            if original not in group_copies:group_copies[original]=own(original.copy())
                            node.node_tree=group_copies[original]
                mesh.materials[i]=materials[mat]
            layer=mesh.uv_layers.get(p['uv_map']) if p.get('uv_strategy','NEW')=='EXISTING' else mesh.uv_layers.new(name=p['uv_map']);mesh.uv_layers.active=layer
            for mat in materials.values():pin(mat,source['assets'][role]['original_render_uv'],p['uv_map'],p['missing_uv_policy'],mesh)
            if p.get('uv_strategy','NEW')=='NEW':
                with active_object(target):
                    settings.mesh_select_mode=(False,False,True);settings.use_uv_select_sync=False
                    finished(bpy.ops.object.mode_set(mode='EDIT'));finished(bpy.ops.mesh.select_all(action='SELECT'))
                    finished(bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=p['margin'],correct_aspect=False,scale_to_bounds=True))
                    finished(bpy.ops.object.mode_set(mode='OBJECT'))
            repairs=repair_charts(target,p['uv_map'],p['margin'],p.get('max_uv_repairs',64)) if p.get('uv_strategy','NEW')=='NEW' else []
            # Edit-mode operators rebuild CustomData; reacquire the RNA layer
            # instead of writing through a pre-edit UV wrapper.
            layer=mesh.uv_layers[p['uv_map']]
            if p.get('tile_padding_pixels',0):
                from mcpblender.uv_math import inset_tile
                values=[v for item in layer.data for v in item.uv]
                layer.data.foreach_set('uv',inset_tile(values,p['texture_width'],p['texture_height'],p['tile_padding_pixels'],True))
            mesh.uv_layers.active=layer;layer.active_render=True;mesh.update();bpy.context.view_layer.update()
            # BMesh omits all-false built-in sharp layers. Restore their dense
            # representation before comparing every original public attribute.
            for name in ('sharp_face','sharp_edge'):
                attr=obj.data.attributes.get(name)
                if attr and name not in mesh.attributes and not any(v.value for v in attr.data):mesh.attributes.new(name=name,type=attr.data_type,domain=attr.domain)
            mesh.update()
            witness=source['assets'][role];copied=textures.mesh_signature(target,mesh)
            if any(copied[k]!=witness['mesh'][k] for k in ('geometry','matrix','corner_normals','materials','texspace')):raise ValueError('Bake UV generation changed source geometry, normals or affine placement')
            if any(dict(copied['uv']).get(name)!=digest for name,digest in witness['mesh']['uv']):raise ValueError('Bake UV generation changed original UV coordinates')
            attributes={a['name']:a for a in assemblies.attribute_records(mesh)}
            changed=[a['name'] for a in witness['attributes'] if attributes.get(a['name'])!=a]
            if changed:raise ValueError('Bake UV generation changed source numeric attributes: '+', '.join(changed))
            thin=any(textures.bake_surface_node(m,'FRONT_PBR')[1] for m in mesh.materials)
            inputs={'name':target.name,'sources':[],'cage':None,'uv_map':p['uv_map'],'thin_foliage_mode':'FRONT_PBR' if thin else 'REFUSE'}
            info=textures.inspect(inputs)
            if not info['complete']:raise ValueError('Prepared bake UVs did not qualify: '+'; '.join(info['unsupported_reasons']))
            target.hide_render=True
            components[role]={'name':target.name,'source_object':obj.name,'inspect_texture_bake':inputs,'initial_bake_sha256':info['bake_sha256'],'material_adapters':info['material_adapters'],'repaired_uv_faces':repairs,'prepared_mesh':copied,'prepared_attributes':[v for v in attributes.values() if not v['name'].startswith('.')]}
        check_cancelled()
        if plan(p)[-1]['plan_sha256']!=p['expected_plan']:raise ValueError('Source changed during bake preparation')
        meta={'format':FORMAT,'revision':0,'owner':owner,'source':source,'components':components,'owned':[{'type':v.bl_rna.identifier,'name':v.name} for v in sorted(owned,key=lambda v:(v.bl_rna.identifier,v.name))]}
        meta['content_sha256']=content(owned);col[META]=json.dumps(meta,sort_keys=True,allow_nan=False)
        result=inspect({'bake_collection':col.name})[-1]
        if not result['valid']:raise ValueError('Created bake preparation failed owned content verification')
        success=True;return result
    finally:
        settings.mesh_select_mode=mode;settings.use_uv_select_sync=sync
        if not success and owned:bpy.data.batch_remove(ids=tuple(owned))
        bpy.context.view_layer.update()


def refresh(p):
    from .bridge import check_cancelled
    bpy.context.view_layer.update();col,owned,meta,state=inspect(p)
    if state['preparation_sha256']!=p['expected_preparation']:raise ValueError('Bake preparation guard is stale')
    if state['ownership_blockers']:raise ValueError('; '.join(state['ownership_blockers']))
    if meta.get('revision',0)>=1024:raise ValueError('Recreate preparation after 1024 source revisions')
    updated={}
    for role,row in meta['components'].items():
        check_cancelled();obj=bpy.data.objects[row['name']]
        if 'prepared_mesh' not in row or 'prepared_attributes' not in row:raise ValueError('Recreate this older preparation to refresh material sources')
        if any(m not in owned for m in obj.data.materials):raise ValueError('Preparation needs its original private material slots')
        actual=textures.mesh_signature(obj,obj.data);actual['matrix']=[list(r) for r in static_matrix(obj)]
        if botany.digest(actual)!=botany.digest(row['prepared_mesh']):raise ValueError('Refresh cannot accept geometry, UV, normal, material-index or placement edits')
        attrs=[v for v in assemblies.attribute_records(obj.data) if not v['name'].startswith('.')]
        if botany.digest(attrs)!=botany.digest(row['prepared_attributes']):raise ValueError('Refresh cannot accept numeric attribute edits')
        info=textures.inspect(row['inspect_texture_bake'])
        if not info['complete']:raise ValueError('Refreshed material source is unsupported: '+'; '.join(info['unsupported_reasons']))
        updated[role]=dict(row)|{'initial_bake_sha256':info['bake_sha256'],'material_adapters':info['material_adapters']}
    check_cancelled();previous=col[META]
    try:
        meta['components']=updated;meta['revision']=meta.get('revision',0)+1;meta['content_sha256']=content(owned);col[META]=json.dumps(meta,sort_keys=True,allow_nan=False)
        result=inspect(p)[-1]
        if not result['valid']:raise ValueError('Refreshed preparation failed native verification')
        return result
    except BaseException:
        col[META]=previous;raise


def remove(p):
    from .bridge import check_cancelled
    col,owned,meta,result=inspect(p)
    if result['preparation_sha256']!=p['expected_preparation']:raise ValueError('Bake preparation guard is stale')
    if result['ownership_blockers']:raise ValueError('; '.join(result['ownership_blockers']))
    check_cancelled();bpy.data.batch_remove(ids=tuple(owned))
    return {'removed':p['bake_collection'],'source_preserved':True,'file_bundles_preserved':True}


def dispatch(command,p):
    if command=='inspect_vegetation_bake_source':return plan(p)[-1]
    if command=='prepare_vegetation_bake':return create(p)
    if command=='refresh_vegetation_bake':return refresh(p)
    if command=='remove_vegetation_bake':return remove(p)
    return inspect(p)[-1]
