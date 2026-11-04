"""Owned packed card alternatives with guarded explicit camera selection."""
import hashlib
import json
import math
from pathlib import Path
import uuid
import bpy
from mathutils import Vector
from mcpblender import botany,card_family,texture_files
from . import textures,wind_preview
from .assets import mesh_object

COMMANDS={'inspect_foliage_card_family_source','create_foliage_card_family','inspect_foliage_card_family','inspect_foliage_card_family_selection','select_foliage_card_family_view','remove_foliage_card_family'}
META='mcpblender_card_family'
OWNER='mcpblender_card_family_owner'
FORMAT='mcpblender-card-family-v1'
TABLES={'Collection':'collections','Object':'objects','Mesh':'meshes','Material':'materials','Image':'images','ShaderNodeTree':'node_groups'}
RENDER_FLAGS=('visible_camera','visible_shadow','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','is_holdout','is_shadow_catcher')
OPTIONS=('accept_front_pbr','max_angle_degrees','max_total_triangles','max_texture_bytes')


def static(obj):
    if obj.library or obj.override_library or obj.animation_data or obj.constraints or obj.modifiers or obj.rigid_body or obj.rigid_body_constraint or obj.instance_type!='NONE':raise ValueError('Card family requires local static unconstrained objects')
    if obj.type=='MESH' and (obj.data.shape_keys or obj.vertex_groups):raise ValueError('Card family does not support shape keys or vertex groups')


def placement_chain(obj):
    """Freeze bounded static Object parenting, including bake placement anchors."""
    rows=[];seen=set()
    while obj is not None:
        if obj in seen or len(rows)>=32:raise ValueError('Card source parent chain is cyclic or exceeds 32 objects')
        seen.add(obj);static(obj)
        if obj.parent and obj.parent_type!='OBJECT':raise ValueError('Card source supports Object parenting only')
        matrices={key:[list(r) for r in matrix] for key,matrix in (('world',obj.matrix_world),('basis',obj.matrix_basis),('inverse',obj.matrix_parent_inverse))}
        if any(not math.isfinite(v) for matrix in matrices.values() for row in matrix for v in row) or abs(obj.matrix_world.determinant())<=1e-12:raise ValueError('Finite invertible static source placement required')
        rows.append({'name':obj.name,'parent':obj.parent.name if obj.parent else None,**matrices})
        obj=obj.parent
    return rows


def source(p):
    from .bridge import check_cancelled
    if bpy.context.mode!='OBJECT':raise ValueError('Card families require Object mode')
    bpy.context.view_layer.update();root=Path(p['directory'])
    yield from textures.validate({'directory':str(root)})
    saved=texture_files.read_json(root/'manifest.json');names=saved.get('objects',[saved['name']])
    if not {e['object'] for e in p['entries']}<=set(names):raise ValueError('Family entries must name validated bundle objects')
    if saved.get('material_adapters') and not p['accept_front_pbr']:raise ValueError('Explicit accept_front_pbr required for lossy leaf PBR maps')
    maps={row['map']:row for row in saved['maps']}
    if not {'BASE_COLOR','ALPHA'}<=maps.keys():raise ValueError('Foliage card families require BASE_COLOR and ALPHA maps')
    texture_bytes=sum(r['width']*r['height']*4 for r in maps.values())
    if texture_bytes>p['max_texture_bytes']:raise ValueError('Card family texture budget exceeded')
    unit=bpy.context.scene.unit_settings.scale_length
    if not math.isfinite(unit) or unit<=0:raise ValueError('Positive scene unit scale required')
    entries=[];total=0;all_points=[]
    for entry in sorted(p['entries'],key=lambda e:list(card_family.DIRECTIONS).index(e['view'])):
        check_cancelled();obj=mesh_object(entry['object']);static(obj);mesh=obj.data
        chain=placement_chain(obj)
        if len(mesh.materials)!=1 or any(s.link!='DATA' for s in obj.material_slots):raise ValueError('Single-material baked targets required')
        if not mesh.polygons or len(mesh.vertices)>8192 or len(mesh.loops)>32768:raise ValueError('Card family geometry budget exceeded or empty target')
        if obj.matrix_world.determinant()<=1e-12:raise ValueError('Positive invertible card placement required')
        points=[obj.matrix_world@v.co for v in mesh.vertices]
        if any(not math.isfinite(x) for v in points for x in v):raise ValueError('Finite card geometry required')
        n=Vector(card_family.DIRECTIONS[entry['view']]);origin=points[mesh.polygons[0].vertices[0]]
        diagonal=math.sqrt(sum((max(v[a] for v in points)-min(v[a] for v in points))**2 for a in range(3)))
        deviation=max(abs((v-origin).dot(n)) for v in points)
        if deviation>max(1e-12,diagonal*1e-6):raise ValueError('Card target is not planar in its declared canonical view')
        transform=obj.matrix_world.to_3x3().inverted().transposed()
        for face in mesh.polygons:
            normal=transform@face.normal
            if normal.length<1e-12 or normal.normalized().dot(n)<math.cos(math.radians(.1)):raise ValueError('Card winding does not face its declared canonical view')
        triangles=sum(len(face.vertices)-2 for face in mesh.polygons);total+=triangles
        if total>p['max_total_triangles']:raise ValueError('Card family total triangle budget exceeded')
        if not obj.visible_camera or obj.is_holdout or obj.is_shadow_catcher:raise ValueError('Card family sources must be ordinary camera-visible surfaces')
        entries.append(entry|{'triangles':triangles,'asset_sha256':textures.output_signature(obj.name),
                              'render_flags':{k:getattr(obj,k) for k in RENDER_FLAGS},'placement_chain':chain})
        all_points.extend(points)
    bounds={key:[fn(v[a] for v in all_points) for a in range(3)] for key,fn in (('min',min),('max',max))}
    provenance={'job_id':saved['job_id'],'source_sha256':saved['source'],'manifest_sha256':botany.digest(saved),
                'files':saved['files'],'maps':saved['maps'],'material_adapters':saved.get('material_adapters',[]),
                'portable_optical_equivalence':False,
                'source_placements':[{k:row[k] for k in ('view','object','placement_chain')} for row in entries]}
    result={'format':FORMAT,'entries':entries,'total_triangles':total,'rgba8_base_bytes':texture_bytes,
            'bounds_world':bounds,'scene_unit_scale':unit,'provenance':provenance,
            'options':{k:p[k] for k in OPTIONS},'scope':'Static independent packed alternatives; originals preserved. Creation starts hidden. Explicit one-sided nearest selection, no interpolation, wind or optical equivalence.'}
    return result|{'plan_sha256':botany.digest(result)}


def world_matrix(obj,root):
    # Globally hidden objects may retain stale/identity matrix_world after load.
    # Families are static Object-parented children; compose their guarded data.
    if obj.parent!=root or obj.parent_type!='OBJECT':raise ValueError('Static family root parenting required')
    return root.matrix_world@obj.matrix_parent_inverse@obj.matrix_basis


def world_bounds(root,entries):
    points=[]
    for entry in entries:
        obj=bpy.data.objects[entry['object']];matrix=world_matrix(obj,root)
        points.extend(matrix@v.co for v in obj.data.vertices)
    return {key:[fn(v[a] for v in points) for a in range(3)] for key,fn in (('min',min),('max',max))}


def content(owned,root):
    resources={v for v in owned if not isinstance(v,(bpy.types.Object,bpy.types.Collection))}
    objects=[]
    for obj in sorted((v for v in owned if isinstance(v,bpy.types.Object)),key=lambda v:v.name):
        static(obj)
        objects.append({'name':obj.name,'data':obj.data.name if obj.data else None,'parent':obj.parent.name if obj.parent else None,
                        'basis':None if obj==root else [list(r) for r in obj.matrix_basis],
                        'inverse':[list(r) for r in obj.matrix_parent_inverse],
                        'materials':[(s.link,s.material.name if s.material else None) for s in obj.material_slots],
                        'flags':{k:getattr(obj,k) for k in ('hide_select','visible_camera','visible_shadow','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','is_holdout','is_shadow_catcher','show_instancer_for_viewport','show_instancer_for_render') if hasattr(obj,k)}})
    return botany.digest({'resources':wind_preview.signature(resources,metadata_key=META,packed_images=True),'objects':objects})


def inspect(p):
    if bpy.context.mode!='OBJECT':raise ValueError('Card families require Object mode')
    bpy.context.view_layer.update();col=bpy.data.collections.get(p['family_collection']);raw=col.get(META) if col else None
    if not isinstance(raw,str) or len(raw)>1024**2:raise ValueError('Owned card family not found or metadata exceeds budget')
    meta=json.loads(raw);owner=meta.get('owner');owned=set()
    if meta.get('format')!=FORMAT or not isinstance(owner,str) or len(owner)!=32 or any(c not in '0123456789abcdef' for c in owner) or not 4<=len(meta.get('owned',[]))<=64:raise ValueError('Invalid card family ownership metadata')
    for row in meta['owned']:
        table=TABLES.get(row['type']);value=getattr(bpy.data,table).get(row['name']) if table else None
        if value is None or value.get(OWNER)!=owner:raise ValueError('Card family ID missing/renamed or ownership changed')
        owned.add(value)
    if col not in owned or len(owned)!=len(meta['owned']):raise ValueError('Invalid card family inventory')
    root=bpy.data.objects.get(meta['root']);objects={v for v in owned if isinstance(v,bpy.types.Object)}
    if root not in objects:raise ValueError('Card family root missing')
    issues=[];blockers=[];users=bpy.data.user_map()
    layer=bpy.context.view_layer.layer_collection.children.get(col.name)
    if col.name not in bpy.context.scene.collection.children or layer is None or layer.exclude or layer.hide_viewport or bpy.context.view_layer.objects.get(root.name)!=root:issues.append('Family must remain a direct visible collection in the current scene/view layer')
    if root.hide_get():issues.append('Family root is locally hidden')
    if set(col.objects)!=objects or col.children:blockers.append('Foreign or missing family collection membership')
    if root.parent or root.type!='EMPTY' or any(o.parent!=root or o.parent_type!='OBJECT' for o in objects if o!=root):issues.append('Family root/child hierarchy changed')
    if col.hide_render or col.hide_viewport or root.hide_render or root.hide_viewport:issues.append('Family collection or root is hidden')
    if bpy.context.scene.unit_settings.scale_length!=meta['unit_scale']:issues.append('Family scene unit scale changed')
    matrix=root.matrix_world
    if any(not math.isfinite(v) for r in matrix for v in r) or matrix.determinant()<=1e-12:issues.append('Family root needs finite positive invertible placement')
    else:
        axes=[matrix.to_3x3().col[i] for i in range(3)];sizes=[v.length for v in axes]
        if max(sizes)-min(sizes)>max(sizes)*1e-6 or any(abs(axes[a].normalized().dot(axes[b].normalized()))>1e-6 for a,b in ((0,1),(0,2),(1,2))):issues.append('Family root requires uniform scale without shear')
    if {e['object'] for e in meta['entries']}!={o.name for o in objects if o!=root}:issues.append('Family view object inventory differs')
    for entry in meta['entries']:
        obj=bpy.data.objects.get(entry['object'])
        if obj not in objects:continue
        visible=entry['view']==meta['selected_view']
        if obj.hide_render==visible or obj.hide_viewport==visible or obj.hide_get():issues.append('Family managed visibility changed: '+obj.name)
    for value in owned:
        if value.library or value.override_library or value.use_fake_user:blockers.append('Persistent/linked family ID: '+value.name)
        for user in users.get(value,set()):
            if user in owned or value==col and isinstance(user,(bpy.types.Scene,bpy.types.Collection)) or isinstance(value,bpy.types.Object) and isinstance(user,bpy.types.Scene):continue
            blockers.append('External family reference: '+value.name)
        if isinstance(value,bpy.types.Object) and value.type=='MESH' and value.data.shape_keys:blockers.append('Remove family shape keys before deletion')
        if isinstance(value,bpy.types.Object) and (value.rigid_body or value.rigid_body_constraint):blockers.append('Remove family physics before deletion')
    try:current=content(owned,root)
    except (ValueError,TypeError) as exc:current=None;issues.append(str(exc))
    if current!=meta['content_sha256']:issues.append('Family native content changed')
    placement=[list(r) for r in matrix]
    state={'family_collection':col.name,'root':root.name,'valid':not issues and not blockers,'issues':issues,'ownership_blockers':sorted(set(blockers)),
           'entries':meta['entries'],'selected_view':meta['selected_view'],'max_angle_degrees':meta['max_angle_degrees'],
           'total_triangles':meta['total_triangles'],'rgba8_base_bytes':meta['rgba8_base_bytes'],'packed_images':len([v for v in owned if isinstance(v,bpy.types.Image)]),
           'provenance':meta['provenance'],'source_files_required':False,
           'scope':'Static packed alternatives. Explicit selection only; original bake objects may still be visible. No interpolation, automatic following, wind or native optical equivalence.'}
    guard={'content':current,'meta':meta,'placement':placement,'unit_scale':bpy.context.scene.unit_settings.scale_length,
           'issues':issues,'users':sorted((v.bl_rna.identifier,v.name,sorted((u.bl_rna.identifier,u.name) for u in users.get(v,set()))) for v in owned)}
    return col,owned,meta,state|{'family_sha256':botany.digest(guard)}


def create(p):
    from .bridge import check_cancelled,report_progress,_bridge
    info=yield from source(p)
    if info['plan_sha256']!=p['expected_plan']:raise ValueError('Card family source plan is stale')
    if p['family_collection'] in bpy.data.collections:raise ValueError('Card family collection already exists')
    estimate=info['rgba8_base_bytes']*2+16*1024**2
    if _bridge and _bridge.active:
        from mcpblender.storage import require_space
        policy=_bridge.active['storage'];policy.update(estimated_bytes=estimate,estimate_kind='packed_card_family_checkpoint_heuristic')
        require_space(policy.get('path',_bridge.path.parent),estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind=policy['estimate_kind'])
    before=set(bpy.data.user_map());success=False
    try:
        owner=uuid.uuid4().hex;col=bpy.data.collections.new(p['family_collection']);bpy.context.scene.collection.children.link(col)
        root=bpy.data.objects.new(col.name+'_Root',None);col.objects.link(root)
        root.location=[(a+b)/2 for a,b in zip(info['bounds_world']['min'],info['bounds_world']['max'])];bpy.context.view_layer.update()
        images={};materials={};groups={};entries=[]
        expected={r['path']:r['sha256'] for r in info['provenance']['files']}
        for row in info['entries']:
            check_cancelled();report_progress({'phase':'copying packed card alternatives','view':row['view'],'completed':len(entries),'total':len(info['entries'])})
            original=mesh_object(row['object']);material=original.data.materials[0]
            if material not in materials:
                mat=material.copy();mat.name=col.name+'_PBR';mat.use_fake_user=False;materials[material]=mat
                for node in mat.node_tree.nodes:
                    if node.type=='TEX_IMAGE':
                        old=node.image
                        if old not in images:
                            path=Path(bpy.path.abspath(old.filepath));relative=path.relative_to(Path(p['directory'])).as_posix()
                            if relative not in expected:raise ValueError('Family image not in validated bundle inventory')
                            image=bpy.data.images.load(str(path),check_existing=False);image.name=col.name+'_'+node.name;image.colorspace_settings.name=old.colorspace_settings.name;image.pack();image.filepath='';image.use_fake_user=False
                            if not image.packed_file or hashlib.sha256(image.packed_file.data).hexdigest()!=expected[relative]:raise ValueError('Packed family image changed from validated PNG')
                            images[old]=image
                        node.image=images[old]
                    elif node.type=='GROUP':
                        old=node.node_tree
                        if old not in groups:groups[old]=old.copy();groups[old].name='glTF Material Output_'+col.name;groups[old].use_fake_user=False
                        node.node_tree=groups[old]
            mesh=original.data.copy();mesh.name=col.name+'_'+row['view']+'_Mesh';mesh.use_fake_user=False;mesh.materials.clear();mesh.materials.append(materials[material])
            obj=bpy.data.objects.new(col.name+'_'+row['view'],mesh);col.objects.link(obj);obj.parent=root;obj.matrix_world=original.matrix_world.copy();obj.hide_render=True;obj.hide_viewport=True
            for key,value in row['render_flags'].items():setattr(obj,key,value)
            entries.append({'view':row['view'],'object':obj.name,'triangles':row['triangles']})
        # Recheck files and original native content after packing, before handoff.
        check=yield from source(p)
        if check['plan_sha256']!=p['expected_plan']:raise ValueError('Card family source changed while copying')
        check_cancelled();owned=set(bpy.data.user_map())-before
        owned={v for v in owned if not getattr(v,'is_embedded_data',False)}
        for value in owned:value[OWNER]=owner;value.use_fake_user=False
        meta={'format':FORMAT,'owner':owner,'root':root.name,'entries':entries,'unit_scale':info['scene_unit_scale'],
              'selected_view':None,'max_angle_degrees':p['max_angle_degrees'],'total_triangles':info['total_triangles'],
              'rgba8_base_bytes':info['rgba8_base_bytes'],'provenance':info['provenance'],
              'owned':[{'type':v.bl_rna.identifier,'name':v.name} for v in sorted(owned,key=lambda v:(v.bl_rna.identifier,v.name))]}
        bpy.context.view_layer.update();meta['content_sha256']=content(owned,root);col[META]=json.dumps(meta,sort_keys=True,allow_nan=False)
        result=inspect(p)[-1]
        if not result['valid']:raise ValueError('New card family verification failed: '+str(result['issues']+result['ownership_blockers']))
        success=True;return result
    finally:
        if not success:bpy.data.batch_remove(ids=tuple(v for v in set(bpy.data.user_map())-before if not getattr(v,'is_embedded_data',False)))


def selection(p):
    col,owned,meta,state=inspect(p)
    if not state['valid']:raise ValueError('Valid unchanged card family required: '+str(state['issues']+state['ownership_blockers']))
    root=bpy.data.objects[meta['root']];matrix=root.matrix_world;camera=None;witness=None;bounds=None
    if p.get('camera'):
        camera=bpy.data.objects.get(p['camera'])
        if camera is None or camera.library or camera.override_library or camera.type!='CAMERA' or camera.data.type not in {'ORTHO','PERSP'}:raise ValueError('Local ORTHO/PERSP camera required')
        witness={'name':camera.name,'type':camera.data.type,'matrix':[list(r) for r in camera.matrix_world]}
        if camera.data.type=='ORTHO':directions=[list(camera.matrix_world.to_3x3()@Vector((0,0,1)))];projection='ORTHOGRAPHIC_CAMERA'
        else:
            eye=camera.matrix_world.translation;origin=matrix.translation;directions=[list(eye-origin)]
            # Native bounds of every alternative cover the family envelope.
            bounds=world_bounds(root,meta['entries']);low=bounds['min'];high=bounds['max']
            directions.extend(list(eye-Vector((x,y,z))) for x in (low[0],high[0]) for y in (low[1],high[1]) for z in (low[2],high[2]));projection='PERSPECTIVE_ENVELOPE'
            if all(low[a]<=eye[a]<=high[a] for a in range(3)):raise ValueError('Perspective camera is inside family bounds')
    else:directions=[p['view_direction']];projection='PARALLEL_WORLD_DIRECTION'
    normals={e['view']:list(matrix.to_3x3()@Vector(card_family.DIRECTIONS[e['view']])) for e in meta['entries']}
    result=card_family.choose(normals,directions,meta['max_angle_degrees'])
    selected=next((e['object'] for e in meta['entries'] if e['view']==result['selected_view']),None)
    info=result|{'family_collection':col.name,'family_sha256':state['family_sha256'],'object':selected,'projection':projection,'camera':witness,'view_direction':p.get('view_direction'),'bounds_world_native':bounds}
    return col,owned,meta,info|{'selection_sha256':botany.digest(info)}


def select(p):
    from .bridge import check_cancelled
    col,owned,meta,info=selection(p)
    if info['selection_sha256']!=p['expected_selection']:raise ValueError('Card family selection is stale; inspect again')
    if not info['supported']:raise ValueError('Viewer is outside the supported family angular limit; no view selected')
    old_meta=col[META];flags=[];success=False
    try:
        check_cancelled()
        for entry in meta['entries']:
            obj=bpy.data.objects[entry['object']];flags.append((obj,obj.hide_render,obj.hide_viewport))
            obj.hide_render=obj.hide_viewport=entry['view']!=info['selected_view']
        meta=dict(meta);meta['selected_view']=info['selected_view'];col[META]=json.dumps(meta,sort_keys=True,allow_nan=False)
        result=inspect(p)[-1]
        if not result['valid']:raise ValueError('Selected card family verification failed')
        check_cancelled();success=True;return result|{'selection':info}
    finally:
        if not success:
            for obj,render,viewport in flags:obj.hide_render=render;obj.hide_viewport=viewport
            col[META]=old_meta


def remove(p):
    from .bridge import check_cancelled
    col,owned,meta,state=inspect(p)
    if p['expected_family']!=state['family_sha256']:raise ValueError('Card family removal guard is stale')
    if not state['valid']:raise ValueError('Refuse removal of changed or externally referenced card family')
    check_cancelled();bpy.data.batch_remove(ids=tuple(owned))
    return {'removed':True,'family_collection':p['family_collection'],'source_files_preserved':True}


def dispatch(command,p):
    if command=='inspect_foliage_card_family_source':return source(p)
    if command=='create_foliage_card_family':return create(p)
    if command=='inspect_foliage_card_family_selection':return selection(p)[-1]
    if command=='select_foliage_card_family_view':return select(p)
    if command=='remove_foliage_card_family':return remove(p)
    return inspect(p)[-1]
