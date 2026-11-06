"""Source-bound packed native blade cards for guarded botanical subsets."""
import hashlib
import math
from pathlib import Path
import bpy,bmesh
from mathutils import Matrix,Vector
from mcpblender import botany,texture_files
from mcpblender.package_files import image_info
from . import vegetation_bake as preparation,leaf_card_preparation,textures,assemblies,lods,subset_templates

RECIPE='NATIVE_THIN_BLADE_CARD_SUBSET_V1'


def bundle(directory,row,limits):
    from .bridge import check_cancelled
    root=Path(directory);texture_files.inventory(root)
    record=texture_files.read_json(root/texture_files.MARKER);saved=texture_files.read_json(root/'manifest.json');job=texture_files.read_json(root/'job.json')
    if record.get('kind')!='mcpblender-texture-job' or record.get('version')!=1 or record.get('state')!='succeeded' or saved.get('version')!=1 or saved.get('job_id')!=record.get('job_id') or job.get('job_id')!=record.get('job_id'):raise ValueError('Successful owned blade texture job required')
    size=sum(v['bytes'] for v in texture_files.deliverables(root))
    if size>limits['max_bytes']:raise ValueError('Blade bundle exceeds max_bytes')
    inputs=row['inspect_texture_bake']
    if saved.get('atlas') is not None or job.get('cage') or job.get('name')!=row['name'] or saved.get('name')!=row['name'] or job.get('sources')!=inputs['sources'] or job.get('uv_map')!=inputs['uv_map'] or job.get('thin_foliage_mode')!=inputs['thin_foliage_mode']:raise ValueError('Blade bundle does not project this exact prepared source/target')
    if job.get('quality'):raise ValueError('Blade adoption requires the recorded preparation bake without an additional quality policy')
    if any(job.get(k)!=row['bake_parameters'][k] for k in ('cage_extrusion','max_ray_distance')):raise ValueError('Blade projection ray range differs from preparation')
    minimum=job.get('min_projection_coverage');projection=saved.get('projection')
    if type(minimum) not in (int,float) or not math.isfinite(minimum) or not row['bake_parameters']['min_projection_coverage']<=minimum<=1:raise ValueError('Blade projection coverage policy was relaxed')
    if not isinstance(projection,dict) or projection.get('threshold')!=minimum or type(projection.get('target_pixels'))!=int or type(projection.get('hit_pixels'))!=int or not 0<projection['hit_pixels']<=projection['target_pixels']<=job['width']*job['height'] or projection.get('fraction')!=projection['hit_pixels']/projection['target_pixels'] or not projection['fraction']>=minimum:raise ValueError('Blade projection coverage witness failed')
    initial=row['initial_bake_sha256']
    if any(value!=initial for value in (saved.get('source'),record.get('source'),job.get('expected_bake'))):raise ValueError('Blade bake source differs from preparation')
    if saved.get('material_adapters')!=row['material_adapters'] or record.get('material_adapters')!=row['material_adapters']:raise ValueError('Blade optical adapter binding changed')
    if texture_files.validate_map_policy(record,saved,job) is None:raise ValueError('Blade projected opacity padding policy required')
    for step in texture_files.verify_steps(root,saved['files']):check_cancelled()
    by_path={v['path']:v for v in saved['files']};maps={}
    if {m['map'] for m in saved['maps']}!=set(job['maps']) or not {'NORMAL','ALPHA'}<=set(job['maps']):raise ValueError('Blade bake requires NORMAL and ALPHA maps')
    for kind in ('NORMAL','ALPHA'):
        matches=[m for m in saved['maps'] if m['map']==kind]
        if len(matches)!=1:raise ValueError('Duplicate blade map')
        m=matches[0];relative='textures/'+kind.lower()+'.png'
        if m['path']!=relative or relative not in by_path or m['color_space']!='Non-Color':raise ValueError('Blade data map path/color space mismatch')
        payload=(root/relative).read_bytes();info=image_info(payload,'image/png');expected=row['bake_parameters']
        if (info['width'],info['height'])!=(m['width'],m['height']) or (job['width'],job['height'])!=(expected['width'],expected['height']) or (m['width'],m['height'])!=(job['width'],job['height']):raise ValueError('Blade bake dimensions differ from preparation')
        maps[kind]={'path':relative,'sha256':by_path[relative]['sha256'],'bytes':len(payload),'width':m['width'],'height':m['height'],'color_space':m['color_space']}
    return {'manifest_sha256':botany.digest(saved),'source':initial,'maps':maps,'bundle_bytes':size}


def plan(roles,selected,settings):
    from .bridge import check_cancelled
    col,owned,meta,state=preparation.inspect({'bake_collection':settings['bake_collection']})
    if state['preparation_sha256']!=settings['expected_preparation']:raise ValueError('Blade preparation guard is stale')
    if not state['valid'] or meta['source']['options'].get('blade_cards') is None:raise ValueError('Unchanged blade-card preparation required')
    if meta['source']['scene_unit_scale']!=bpy.context.scene.unit_settings.scale_length:raise ValueError('Blade preparation units changed')
    variants=sorted((int(k[2:]),obj) for k,obj in roles.items() if k.startswith('lo'));entries={e['asset']:e for e in settings['entries']}
    if set(entries)!={f'leaf-{i}' for i,obj in variants}:raise ValueError('Blade bundles required for every shared leaf variant')
    indices=[v.value for v in roles['pm'].attributes['leaf_index'].data];types=[v.value for v in roles['pm'].attributes['leaf_variant'].data];chosen=set(selected);counts={i:0 for i,obj in variants}
    for index,variant in zip(indices,types):
        if index in chosen:counts[variant]+=1
    rows=[];encoded=0;decoded=0
    for i,obj in variants:
        check_cancelled();role=f'leaf-{i}';row=meta['components'].get(role);w=meta['source']['assets'].get(role)
        if row is None or w is None or row['source_object']!=obj.name or botany.digest(textures.mesh_signature(obj,obj.data))!=botany.digest(w['mesh']) or lods.summary(obj.data)['mesh_sha256']!=w['source_mesh_sha256']:raise ValueError('Blade preparation differs from source template: '+role)
        source_uv=leaf_card_preparation.material(obj.data.materials[0])
        if botany.digest(assemblies.record(obj.data.materials[0]))!=w['source_leaf_material_sha256']:raise ValueError('Blade source shader changed')
        witness=bundle(entries[role]['directory'],row,settings);encoded+=witness['bundle_bytes'];decoded+=sum(m['width']*m['height']*4 for m in witness['maps'].values())
        lookup=row.get('source_uv_lookup')
        if bool(source_uv)!=bool(lookup):raise ValueError('Blade procedural source UV correspondence missing')
        if lookup:
            image=bpy.data.images.get(lookup['image'])
            if image not in owned or lookup['source_uv']!=source_uv or not image.packed_file or image.is_dirty or hashlib.sha256(image.packed_file.data).hexdigest()!=lookup['packed_sha256']:raise ValueError('Blade source UV lookup changed')
            decoded+=lookup['width']*lookup['height']*16
        if encoded>settings['max_bytes'] or decoded>settings['max_texture_bytes']:raise ValueError('Blade source file/decoded texture budget exceeded')
        if len(obj.data.uv_layers)>=8:raise ValueError('Blade card needs a free UV channel')
        obj.data.calc_loop_triangles();stem=sum(t.material_index==1 for t in obj.data.loop_triangles);name='MCPBladeCardUV'
        while name in obj.data.uv_layers:name+='x'
        rows.append({'variant':i,'instances':counts[i],'source_mesh_sha256':w['source_mesh_sha256'],'source_triangles':len(obj.data.loop_triangles),'triangles':stem+2,'petiole_triangles':stem,'petiole_geometry_uv_sha256':subset_templates.protected_signature(obj.data),
                     'card_uv_map':name,'source_uv_lookup':lookup,'bake':witness})
    return {'recipe':RECIPE,'bake_collection':col.name,'policy':{k:settings[k] for k in ('max_bytes','max_texture_bytes')},'preparation_sha256':state['preparation_sha256'],'variants':rows,'bundle_bytes':encoded,'decoded_texture_bytes':decoded,
            'expanded_source_leaf_triangles':sum(r['instances']*r['source_triangles'] for r in rows),'expanded_card_leaf_triangles':sum(r['instances']*r['triangles'] for r in rows),
            'scope':'Approximate backing-to-midplane rectangular blades with packed projected normal/alpha and optional source-UV correspondence; native thin/back shader retained, normal inputs intentionally replaced. Original petiole geometry/source UVs and selected instance IDs/poses retained. No optical, wind, far-budget or runtime certificate.'}


def build(base,row,component,directory):
    """Return a private mesh; subset creation owns rollback for all allocated IDs."""
    from .bridge import check_cancelled
    check_cancelled();target=bpy.data.objects[component['name']];recipe=component['card_recipe'];unit=bpy.context.scene.unit_settings.scale_length
    mesh=target.data.copy();mesh.transform(Matrix(recipe['alignment_matrix']).inverted()@target.matrix_world)
    offset=Vector(recipe['mean_normal_local'])*(recipe['midplane_offset_m']/unit)
    for vertex in mesh.vertices:vertex.co+=offset
    # Keep target sampling separate from every original source UV, including petioles.
    layer=mesh.uv_layers[component['inspect_texture_bake']['uv_map']];layer.name=row['card_uv_map']
    for original in base.uv_layers:
        new=mesh.uv_layers.new(name=original.name);new.active_render=original.active_render
    mesh.uv_layers.active=mesh.uv_layers[row['card_uv_map']]
    material=base.materials[0].copy();material.use_fake_user=False;nodes=material.node_tree.nodes;links=material.node_tree.links;output=nodes['Output'];original=output.inputs['Surface'].links[0].from_socket
    coords=nodes.new('ShaderNodeUVMap');coords.uv_map=row['card_uv_map'];images={}
    for kind,m in row['bake']['maps'].items():
        check_cancelled();path=Path(directory)/m['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('Blade map changed during adoption')
        image=bpy.data.images.load(str(path),check_existing=False);image.colorspace_settings.name='Non-Color';image.pack();image.use_fake_user=False
        if not image.packed_file or hashlib.sha256(image.packed_file.data).hexdigest()!=m['sha256']:raise ValueError('Packed blade image differs from verified map')
        image.filepath='';image.name=material.name+'_'+kind
        tex=nodes.new('ShaderNodeTexImage');tex.name='MCP Blade '+kind;tex.image=image;tex.extension='CLIP' if kind=='ALPHA' else 'EXTEND';links.new(coords.outputs['UV'],tex.inputs['Vector']);images[kind]=tex
    normal=nodes.new('ShaderNodeNormalMap');normal.space='TANGENT';normal.uv_map=row['card_uv_map'];links.new(images['NORMAL'].outputs['Color'],normal.inputs['Color'])
    for name in ('Leaf Surface','Thin Backlighting'):links.new(normal.outputs['Normal'],nodes[name].inputs['Normal'])
    lookup=row['source_uv_lookup']
    if lookup:
        image=bpy.data.images[lookup['image']].copy();image.use_fake_user=False;image.use_half_precision=False;image.filepath=''
        if not image.packed_file or hashlib.sha256(image.packed_file.data).hexdigest()!=lookup['packed_sha256']:raise ValueError('Copied blade UV lookup differs from preparation')
        tex=nodes.new('ShaderNodeTexImage');tex.name='MCP Blade Source UV';tex.image=image;tex.interpolation='Linear';tex.extension='EXTEND';links.new(coords.outputs['UV'],tex.inputs['Vector']);consumers=0
        for node in list(nodes):
            if node.type=='UVMAP' and node.uv_map==lookup['source_uv']:
                for link in list(node.outputs['UV'].links):links.new(tex.outputs['Color'],link.to_socket);consumers+=1
        if not consumers:raise ValueError('Blade procedural source UV has no consumers')
    transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');links.new(images['ALPHA'].outputs['Color'],mix.inputs[0]);links.new(transparent.outputs[0],mix.inputs[1]);links.new(original,mix.inputs[2]);links.new(mix.outputs[0],output.inputs['Surface'])
    mesh.materials.clear();mesh.materials.append(material);mesh.materials.append(base.materials[1]);stem=base.copy();bm=bmesh.new()
    try:
        bm.from_mesh(stem);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=1],context='FACES');loose=[v for v in bm.verts if not v.link_faces]
        if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
        bm.to_mesh(stem);bm.clear();bm.from_mesh(mesh);bm.from_mesh(stem);bm.to_mesh(mesh)
    finally:bm.free();bpy.data.meshes.remove(stem)
    mesh.use_auto_texspace=False;mesh.texspace_location=base.texspace_location;mesh.texspace_size=base.texspace_size;mesh.update();mesh.calc_loop_triangles()
    if len(mesh.loop_triangles)!=row['triangles'] or subset_templates.protected_signature(mesh,[l.name for l in base.uv_layers])!=row['petiole_geometry_uv_sha256']:raise ValueError('Blade card changed protected petiole geometry/UVs or triangle count')
    check_cancelled();return mesh
