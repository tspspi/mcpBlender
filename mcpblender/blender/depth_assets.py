"""Owned directional depth approximation; native input fields, never lit sprites."""
import json
import math
from pathlib import Path
import uuid
from array import array
import bpy
from mathutils import Matrix
from mcpblender import botany,capture_data,depth_tiles,exr_scanline
from . import card_families

COMMANDS={'inspect_botanical_depth_source','create_botanical_depth_asset','inspect_botanical_depth_asset','remove_botanical_depth_asset'}
META='mcpblender_depth_asset';OWNER='mcpblender_depth_owner';FORMAT='mcpblender-directional-depth-asset-v1'
SHADER_RECIPE='CAPTURED_INPUT_PBR_V2_SIDED_NORMAL'
LEGACY_SHADER_RECIPE='CAPTURED_INPUT_PBR_V1'
TABLES={'Collection':'collections','Object':'objects','Mesh':'meshes','Material':'materials','Image':'images'}


def prepared(p):
    from .bridge import check_cancelled,report_progress
    if bpy.context.mode!='OBJECT':raise ValueError('Depth assets require Object mode')
    settings=depth_tiles.options(p['settings']);unit=bpy.context.scene.unit_settings.scale_length
    if not math.isfinite(unit) or unit<=0:raise ValueError('Positive target scene units required')
    args={'directory':p['directory'],'views':[p['view']],'max_pixels':settings['max_pixels'],'max_total_pixels':settings['max_pixels']}
    def cancelled():check_cancelled();return False
    root,proof,meta,rows=capture_data.source(args,report_progress,cancelled)
    if not meta.get('material_fields'):raise ValueError('Native material fields required; recapture with material_fields=true')
    view,row=rows[0];size=proof['botanical_capture']['options']['resolution'];texture_bytes=size*size*len(depth_tiles.MAPS)*16
    if texture_bytes>settings['max_texture_bytes']:raise ValueError('Depth asset decoded texture budget exceeded')
    names=['TreeCapture.Combined.A','TreeCapture.Depth.Z',*('TreeCapture.Normal.'+a for a in 'XYZ')]
    decoded=exr_scanline.decode(root/row['file'],names,expected_sha256=row['sha256'],cancelled=check_cancelled,progress=report_progress)
    geometry=depth_tiles.geometry(decoded,meta,view,settings,cancelled=check_cancelled,progress=report_progress);maps={};map_rows=[]
    for name,components in depth_tiles.MAPS:
        check_cancelled();report_progress({'phase':'packing directional shader-input data','map':name,'completed':len(maps),'total':len(depth_tiles.MAPS)})
        values=exr_scanline.decode(root/row['file'],depth_tiles.map_channels(name),expected_sha256=row['sha256'],cancelled=check_cancelled,progress=report_progress)
        pixels=depth_tiles.texture_map(values,decoded,meta,view,settings,name,cancelled=check_cancelled);maps[name]=pixels
        map_rows.append({'map':name,'components':list(components),'float32_sha256':depth_tiles.floats_sha(pixels),'decoded_bytes':len(pixels)*4});del values
    placement=Matrix.Scale(meta['scene_unit_scale']/unit,4)@Matrix(meta['source_root_matrix_world'])
    summary={'format':FORMAT,'shader_recipe':SHADER_RECIPE,'view':p['view'],'width':size,'height':size,'geometry':geometry['report'],'maps':map_rows,'decoded_texture_bytes':texture_bytes,
             'target_unit_scale':unit,'root_matrix_world':[list(r) for r in placement],
             'source':{'capture_sha256':meta['capture_sha256'],'frame':meta['frame'],'snapshot_sha256':proof['source_sha256'],'exr_sha256':row['sha256'],'material_fields_sha256':meta['material_fields']['fields_sha256'],'material_fields':meta['material_fields'],'source_root_matrix_world':meta['source_root_matrix_world'],'scene_unit_scale':meta['scene_unit_scale'],'bounds_root_local_m':meta['bounds_root_local_m'],'view':view},
             'optical_equivalence':False,'scope':'Single directional approximate depth layer; median measured-witness depth anchors, optional bounded normal-aligned refinement and explicitly counted edge estimates. Native view-evaluated shader-input maps, normalized raw root-local normals and artistic backlighting, with coverage applied once. Unknown physical thickness and omitted BSDF inputs; no optical/shadow/wind/interpolation/population qualification.'}
    if len(json.dumps(summary,allow_nan=False))>512*1024:raise ValueError('Depth asset source metadata exceeds budget')
    summary['plan_sha256']=botany.digest(summary)
    return summary,geometry,maps


def material(name,maps,created):
    mat=bpy.data.materials.new(name);created.append(mat);mat.use_nodes=True;tree=mat.node_tree;tree.nodes.clear();links=tree.links
    def node(kind):return tree.nodes.new(kind)
    outputs={}
    for key,image in maps.items():
        tex=node('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest';tex.extension='CLIP'
        separate=node('ShaderNodeSeparateXYZ');links.new(tex.outputs['Color'],separate.inputs[0])
        outputs[key]=(tex.outputs['Color'],*separate.outputs,tex.outputs['Alpha'])
    base=outputs['base_coverage'];normal=outputs['normal_roughness'];emission=outputs['emission'];thin=outputs['thin'];surface=outputs['surface']
    bs=node('ShaderNodeBsdfPrincipled')
    for source,key in [(base[0],'Base Color'),(normal[4],'Roughness'),(surface[1],'Metallic'),(surface[2],'IOR'),(surface[3],'Transmission Weight'),(emission[0],'Emission Color'),(emission[4],'Emission Strength')]:links.new(source,bs.inputs[key])
    transform=node('ShaderNodeVectorTransform');transform.vector_type='NORMAL';transform.convert_from='OBJECT';transform.convert_to='WORLD';links.new(normal[0],transform.inputs[0])
    normalized=node('ShaderNodeVectorMath');normalized.operation='NORMALIZE';links.new(transform.outputs[0],normalized.inputs[0])
    # Captured normals describe the front side of the projected patch. Unlike
    # implicit shader normals, an explicit vector is not reversed by Cycles on
    # a back face. Use geometric sidedness, never a guessed normal/camera dot.
    geometry=node('ShaderNodeNewGeometry');sign=node('ShaderNodeMath');sign.operation='MULTIPLY_ADD';sign.inputs[1].default_value=-2;sign.inputs[2].default_value=1;links.new(geometry.outputs['Backfacing'],sign.inputs[0])
    sided=node('ShaderNodeVectorMath');sided.operation='SCALE';links.new(normalized.outputs[0],sided.inputs[0]);links.new(sign.outputs[0],sided.inputs['Scale']);links.new(sided.outputs[0],bs.inputs['Normal'])
    backlight=node('ShaderNodeBsdfTranslucent');links.new(thin[0],backlight.inputs['Color']);links.new(sided.outputs[0],backlight.inputs['Normal'])
    blend=node('ShaderNodeMixShader');links.new(thin[4],blend.inputs[0]);links.new(bs.outputs[0],blend.inputs[1]);links.new(backlight.outputs[0],blend.inputs[2])
    transparent=node('ShaderNodeBsdfTransparent');coverage=node('ShaderNodeMixShader');links.new(base[4],coverage.inputs[0]);links.new(transparent.outputs[0],coverage.inputs[1]);links.new(blend.outputs[0],coverage.inputs[2])
    output=node('ShaderNodeOutputMaterial');links.new(coverage.outputs[0],output.inputs['Surface'])
    return mat


def native_content(owned,root):
    # Reuse the existing static-object and packed-resource content recorder. Root
    # placement/visibility are guarded separately so the asset can be moved/shown.
    return card_families.content(owned,root)


def verify_buffers(obj,owned,meta):
    """Verify actual native float buffers against the immutable numerical plan."""
    from .bridge import check_cancelled,report_progress
    info=meta['plan'];mesh=obj.data
    if obj.type!='MESH' or not 4<=len(mesh.vertices)<=262144 or len(mesh.polygons)>65536 or len(mesh.loops)>262144:raise ValueError('Depth asset mesh exceeds bounded profile')
    if 2*len(mesh.polygons)!=info['geometry']['triangles'] or any(len(f.vertices)!=4 for f in mesh.polygons):raise ValueError('Depth asset patch counts changed')
    vertices=array('f',[0.])*(len(mesh.vertices)*3);mesh.vertices.foreach_get('co',vertices)
    if depth_tiles.floats_sha(vertices)!=info['geometry']['vertices_sha256']:raise ValueError('Depth asset vertex buffer changed')
    if len(mesh.uv_layers)!=1:raise ValueError('Depth asset UV inventory changed')
    uv=array('f')
    for vertex in range(len(mesh.vertices)):
        # Every patch has private corners; recover the associated corner UV.
        if vertex%4096==0:check_cancelled()
        uv.extend(mesh.uv_layers[0].data[vertex].uv)
    if any(loop.vertex_index!=i for i,loop in enumerate(mesh.loops)) or depth_tiles.floats_sha(uv)!=info['geometry']['uv_sha256']:raise ValueError('Depth asset UV/corner buffer changed')
    if set(meta.get('images',{}))!={key for key,_ in depth_tiles.MAPS}:raise ValueError('Depth asset image inventory changed')
    for row in info['maps']:
        check_cancelled();report_progress({'phase':'verifying packed directional float buffers','map':row['map']})
        image=bpy.data.images.get(meta['images'][row['map']])
        if image not in owned or tuple(image.size)!=(info['width'],info['height']) or not 1<=info['width']<=1024 or not 1<=info['height']<=1024:raise ValueError('Depth asset packed image dimensions changed')
        values=array('f',[0.])*(info['width']*info['height']*4);image.pixels.foreach_get(values);topdown=array('f');stride=info['width']*4
        for y in range(info['height']-1,-1,-1):topdown.extend(values[y*stride:(y+1)*stride])
        if depth_tiles.floats_sha(topdown)!=row['float32_sha256']:raise ValueError('Depth asset packed image float buffer changed: '+row['map'])


def inspect(p):
    if bpy.context.mode!='OBJECT':raise ValueError('Depth assets require Object mode')
    col=bpy.data.collections.get(p['collection']);raw=col.get(META) if col else None
    if not isinstance(raw,str) or len(raw)>1024**2:raise ValueError('Owned directional depth asset not found')
    meta=json.loads(raw);owner=meta.get('owner');owned=set()
    plan=meta.get('plan',{})
    if plan.get('format')!=FORMAT or plan.get('plan_sha256')!=botany.digest({k:v for k,v in plan.items() if k!='plan_sha256'}):raise ValueError('Depth asset source plan metadata changed')
    if meta.get('format')!=FORMAT or not isinstance(owner,str) or len(owner)!=32 or any(c not in '0123456789abcdef' for c in owner) or len(meta.get('owned',[]))!=11:raise ValueError('Invalid depth asset ownership metadata')
    for row in meta['owned']:
        table=TABLES.get(row['type']);value=getattr(bpy.data,table).get(row['name']) if table else None
        if value is None or value.get(OWNER)!=owner:raise ValueError('Depth asset resource missing/renamed or ownership changed')
        owned.add(value)
    root=bpy.data.objects.get(meta['root']);obj=bpy.data.objects.get(meta['object'])
    if col not in owned or root not in owned or obj not in owned or len(owned)!=11 or {kind:sum(v.bl_rna.identifier==kind for v in owned) for kind in TABLES}!={'Collection':1,'Object':2,'Mesh':1,'Material':1,'Image':6}:raise ValueError('Depth asset inventory changed')
    issues=[];blockers=[];users=bpy.data.user_map()
    if root.type!='EMPTY' or obj.type!='MESH' or obj.data not in owned or root.parent or obj.parent!=root or obj.parent_type!='OBJECT' or set(col.objects)!={root,obj} or col.children:issues.append('Depth asset hierarchy/membership changed')
    if bpy.context.scene.collection.children.get(col.name)!=col:issues.append('Depth asset must be a direct collection in the current scene')
    if bpy.context.scene.unit_settings.scale_length!=meta['plan']['target_unit_scale']:issues.append('Target scene unit scale changed')
    try:
        verify_buffers(obj,owned,meta)
        capture_data.pose([list(r) for r in root.matrix_basis]);current=native_content(owned,root)
    except (ValueError,TypeError) as exc:current=None;issues.append(str(exc))
    if current!=meta['content_sha256']:issues.append('Depth asset native content changed')
    for value in owned:
        if value.library or value.override_library or value.use_fake_user:blockers.append('Linked/persistent depth resource: '+value.name)
        for user in users.get(value,set()):
            if user in owned or value==col and user==bpy.context.scene or isinstance(value,bpy.types.Object) and user==bpy.context.scene:continue
            blockers.append('External depth resource reference: '+value.name)
    guard={'meta':meta,'content':current,'root_basis':[list(r) for r in root.matrix_basis],'visibility':[(o.name,o.hide_viewport,o.hide_render,o.hide_get()) for o in (root,obj)],'collection_visibility':[col.hide_viewport,col.hide_render],
           'unit':bpy.context.scene.unit_settings.scale_length,'issues':issues,'users':sorted((v.bl_rna.identifier,v.name,sorted((u.bl_rna.identifier,u.name) for u in users.get(v,set()))) for v in owned)}
    state={'collection':col.name,'root':root.name,'object':obj.name,'valid':not issues and not blockers,'issues':issues,'ownership_blockers':sorted(set(blockers)),'source_files_required':False,'shader_recipe':meta['plan'].get('shader_recipe',LEGACY_SHADER_RECIPE),
           'triangles':meta['plan']['geometry']['triangles'],'packed_images':6,'decoded_texture_bytes':meta['plan']['decoded_texture_bytes'],'plan':meta['plan'],'optical_equivalence':False,'asset_sha256':botany.digest(guard)}
    return col,owned,meta,state


def erase(owned):
    # Partition before deletion: removed RNA handles cannot be inspected again.
    groups={kind:[] for kind in TABLES}
    for value in owned:groups[value.bl_rna.identifier].append(value)
    for kind in ('Object','Mesh','Material','Image','Collection'):
        for value in groups[kind]:getattr(bpy.data,TABLES[kind]).remove(value,do_unlink=True)


def create(p):
    from .bridge import check_cancelled,report_progress,_bridge
    if not p['accept_approximate_optics']:raise ValueError('Explicit accept_approximate_optics=true required; directional depth assets are not optically qualified')
    if p['collection'] in bpy.data.collections:raise ValueError('Depth asset collection already exists')
    info,geometry,maps=prepared(p)
    if info['plan_sha256']!=p['expected_plan']:raise ValueError('Depth asset source plan is stale')
    estimate=info['decoded_texture_bytes']*2+16*1024**2
    if _bridge and _bridge.active:
        from mcpblender.storage import require_space
        policy=_bridge.active['storage'];policy.update(estimated_bytes=estimate,estimate_kind='packed_depth_asset_checkpoint_heuristic')
        require_space(policy.get('path',_bridge.path.parent),estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind=policy['estimate_kind'])
    owner=uuid.uuid4().hex;prefix='MCPDepth-'+owner[:12];made=[];success=False
    try:
        col=bpy.data.collections.new(p['collection']);made.append(col)
        if col.name!=p['collection']:raise ValueError('Depth asset collection name exceeds native naming limits')
        bpy.context.scene.collection.children.link(col);col.hide_render=True;col.hide_viewport=True
        root=bpy.data.objects.new(prefix+'-Root',None);made.append(root);col.objects.link(root);root.matrix_basis=Matrix(info['root_matrix_world'])
        mesh=bpy.data.meshes.new(prefix+'-Mesh');made.append(mesh)
        vertices=geometry['vertices'];mesh.from_pydata([vertices[i:i+3] for i in range(0,len(vertices),3)],[],geometry['faces'])
        uv=mesh.uv_layers.new(name='CaptureUV');values=array('f')
        for loop in mesh.loops:values.extend(geometry['uvs'][loop.vertex_index*2:loop.vertex_index*2+2])
        uv.data.foreach_set('uv',values)
        obj=bpy.data.objects.new(prefix+'-'+p['view'],mesh);made.append(obj);obj.parent=root;col.objects.link(obj)
        images={};w=info['width'];h=info['height']
        for key,pixels in maps.items():
            check_cancelled();report_progress({'phase':'creating packed directional data images','map':key,'completed':len(images),'total':len(maps)})
            image=bpy.data.images.new(prefix+'-'+key,width=w,height=h,alpha=True,float_buffer=True);made.append(image);image.colorspace_settings.name='Non-Color';image.alpha_mode='CHANNEL_PACKED'
            flipped=array('f')
            for y in range(h-1,-1,-1):flipped.extend(pixels[y*w*4:(y+1)*w*4])
            image.pixels.foreach_set(flipped);image.pack();images[key]=image
        mat=material(prefix+'-Material',images,made);mesh.materials.append(mat)
        for value in made:value[OWNER]=owner
        meta={'format':FORMAT,'owner':owner,'root':root.name,'object':obj.name,'owned':[{'type':v.bl_rna.identifier,'name':v.name} for v in made],'images':{key:image.name for key,image in images.items()},'plan':info}
        # Creation/checkpoint content includes packed data and original view data;
        # no external capture path is needed after this point.
        meta['content_sha256']=native_content(set(made),root);col[META]=json.dumps(meta,sort_keys=True,allow_nan=False)
        result=inspect({'collection':col.name})[-1]
        if not result['valid']:raise ValueError('Created depth asset failed inspection: '+str(result['issues']+result['ownership_blockers']))
        check_cancelled();success=True;return result
    finally:
        if not success:erase(set(made))


def remove(p):
    col,owned,meta,state=inspect(p)
    if state['asset_sha256']!=p['expected_asset']:raise ValueError('Depth asset guard is stale')
    if not state['valid']:raise ValueError('Depth asset has changed content or ownership blockers')
    name=col.name;erase(owned);return {'removed':name,'private_datablocks':len(owned)}


def dispatch(command,p):
    if command=='inspect_botanical_depth_source':return prepared(p)[0]
    if command=='create_botanical_depth_asset':return create(p)
    if command=='remove_botanical_depth_asset':return remove(p)
    return inspect(p)[-1]
