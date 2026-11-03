"""Guarded map/UV adoption into native shared-template botanical LOD profiles."""
import hashlib
import json
from pathlib import Path
import uuid
import bpy
from mcpblender import botany,texture_files,vegetation_adoption as schema
from mcpblender.package_files import image_info
from . import vegetation_bake as preparation,vegetation_lods as lods,vegetation_materials as materials,textures,assemblies

COMMANDS={'inspect_vegetation_bake_adoption','adopt_vegetation_bakes','inspect_vegetation_delivery'}


def bundle(directory,component,limits):
    from .bridge import check_cancelled
    root=Path(directory);rows,_=texture_files.inventory(root)
    record=texture_files.read_json(root/texture_files.MARKER);saved=texture_files.read_json(root/'manifest.json');job=texture_files.read_json(root/'job.json')
    if record.get('kind')!='mcpblender-texture-job' or record.get('version')!=1 or record.get('state')!='succeeded' or saved.get('version')!=1 or saved.get('job_id')!=record.get('job_id') or job.get('job_id')!=record.get('job_id'):raise ValueError('Successful owned texture job required')
    if saved.get('atlas') is not None or job.get('sources') or job.get('cage') or saved.get('name')!=component['name'] or job.get('name')!=component['name']:raise ValueError('Adoption requires a self-bake of this exact prepared component')
    if saved.get('source')!=component['initial_bake_sha256'] or record.get('source')!=saved['source'] or job.get('expected_bake')!=saved['source']:raise ValueError('Bake source differs from the unchanged initial preparation')
    if job.get('uv_map')!=component['inspect_texture_bake']['uv_map'] or job.get('thin_foliage_mode','REFUSE')!=component['inspect_texture_bake']['thin_foliage_mode'] or saved.get('material_adapters',[])!=component['material_adapters']:raise ValueError('Bake UV/optical adapter binding changed')
    size=sum(r['bytes'] for r in texture_files.deliverables(root))
    if size>limits['max_bytes']:raise ValueError('Adoption bundle exceeds max_bytes')
    for progress in texture_files.verify_steps(root,saved['files']):check_cancelled()
    by_path={r['path']:r for r in saved['files']};maps=[]
    for m in saved['maps']:
        kind=m['map'];relative='textures/'+kind.lower()+'.png'
        if kind not in schema.MAPS or m['path']!=relative or relative not in by_path:raise ValueError('Unexpected baked map path/kind')
        payload=(root/relative).read_bytes();info=image_info(payload,'image/png')
        if (info['width'],info['height'])!=(m['width'],m['height']) or (m['width'],m['height'])!=(job['width'],job['height']):raise ValueError('Baked map dimensions differ from job')
        maps.append({k:m[k] for k in ('map','width','height','color_space')}|{'sha256':by_path[relative]['sha256'],'bytes':len(payload)})
    if any(m['map']=='EMISSION' for m in maps) and saved.get('emission_encoding')!=texture_files.EMISSION_ENCODING:raise ValueError('Rebake emission maps with the current strength-aware worker')
    if {m['map'] for m in maps}!=set(job['maps']):raise ValueError('Baked map inventory differs from job')
    if saved.get('material_adapters',[])!=record.get('material_adapters',[]):raise ValueError('Bake job optical adapter binding changed')
    return saved,maps,size


def dependencies(mesh):
    values=set(mesh.materials)
    for mat in mesh.materials:
        for node in mat.node_tree.nodes:
            if node.type=='TEX_IMAGE' and node.image:values.add(node.image)
            if node.type=='GROUP' and node.node_tree:values.add(node.node_tree)
    return values


def unique(rows):
    return list({botany.digest(row):row for row in rows}.values())


def plan(p):
    from .bridge import check_cancelled
    bpy.context.view_layer.update()
    col,owned,meta,state=lods.inspect(p)
    if not state['valid']:raise ValueError('Valid unchanged native LOD profile required')
    pc,po,pm,ps=preparation.inspect(p)
    if not ps['valid']:raise ValueError('Valid unchanged owned bake preparation required')
    targets=materials.lod_objects(col,meta);entries={};total=0;encoded=0;source_bytes=0
    for entry in p['entries']:
        check_cancelled();role=entry['asset']
        previous=meta.get('baked_materials',{}).get(role)
        if previous:schema.validate(previous)
        if previous and not p.get('replace_existing',False):raise ValueError('This LOD asset already has adopted maps; use explicit replace_existing')
        if role not in targets or role not in pm['components']:raise ValueError('Asset is not a prepared LOD component')
        target=targets[role];w=pm['source']['assets'][role]
        actual=textures.mesh_signature(target,target.data);actual['matrix']=[list(row) for row in preparation.static_matrix(target)];changed=[k for k in w['mesh'] if botany.digest(actual[k])!=botany.digest(w['mesh'][k])]
        retained=previous and (previous['preparation_sha256']==ps['preparation_sha256'] or pm['owner'] in set(previous.get('source_preparation_owners',[])+([previous['preparation_owner']] if previous.get('preparation_owner') else [])))
        if retained:
            # A retained, guardedly refreshed original source may precede adoption's
            # intentional material-index and target-UV additions on the LOD mesh.
            expected_uvs=previous['uv_witness'];source=bpy.data.objects[pm['components'][role]['name']]
            current_uvs={l.name:schema.uv_digest([list(v.uv) for v in l.data]) for l in target.data.uv_layers}
            prepared_uvs={l.name:schema.uv_digest([list(v.uv) for v in l.data]) for l in source.data.uv_layers}
            if current_uvs!=expected_uvs or prepared_uvs!=expected_uvs or previous['geometry_sha256']!=actual['geometry']:raise ValueError('Retained preparation no longer matches adopted geometry/UVs')
            changed=[k for k in changed if k not in {'uv','render_uv','materials'}]
        else:
            current=materials.contract({role:target});original=pm['source']['source_materials'];names=set(original['slots'][role])
            if current['materials']!=[m for m in original['materials'] if m['name'] in names]:raise ValueError('Prepared component source materials changed')
        if target.name!=w['source_object'] or changed:raise ValueError('Prepared component no longer matches this LOD mesh/placement: '+role+' '+', '.join(changed))
        saved,maps,size=bundle(entry['directory'],pm['components'][role],p);source_bytes+=size
        if source_bytes>p['max_bytes']:raise ValueError('Adoption source files exceed max_bytes')
        inherited=unique((previous.get('inherited_material_adapters',[])+previous.get('material_adapters',[])) if previous else [])
        if (saved.get('material_adapters') or inherited) and not p['accept_front_pbr']:raise ValueError('Explicit accept_front_pbr is required for lossy leaf maps')
        source=bpy.data.objects[pm['components'][role]['name']];uvs={layer.name:schema.uv_digest([list(v.uv) for v in layer.data]) for layer in source.data.uv_layers}
        item={'format':schema.FORMAT,'preparation_sha256':ps['preparation_sha256'],'bake_sha256':saved['source'],'bundle_manifest_sha256':botany.digest(saved),
              'preparation_owner':pm['owner'],'preparation_revision':pm.get('revision',0),'source_preparation_owners':sorted(set(previous.get('source_preparation_owners',[])+([previous['preparation_owner']] if previous.get('preparation_owner') else []))-{pm['owner']}) if previous else [],'revision':previous.get('revision',1)+1 if previous else 1,'previous_adoption_sha256':previous['adoption_sha256'] if previous else None,
              'inherited_material_adapters':inherited,'inherited_sampling_changes':unique(previous.get('inherited_sampling_changes',[])+previous.get('source_sampling_changes',[])) if previous else [],
              'geometry_sha256':w['mesh']['geometry'],'uv_map':pm['components'][role]['inspect_texture_bake']['uv_map'],'uv_witness':uvs,'maps':maps,
              'material_adapters':saved.get('material_adapters',[]),'front_pbr_accepted':p['accept_front_pbr'],'source_sampling_changes':[v for v in ps['source_sampling_changes'] if v['asset']==role],
              'emission_encoding':saved.get('emission_encoding'),'rgba8_base_bytes':sum(m['width']*m['height']*4 for m in maps),'portable_optical_equivalence':False}
        item['adoption_sha256']=botany.digest(item);schema.validate(item);total+=item['rgba8_base_bytes'];encoded+=sum(m['bytes'] for m in maps);entries[role]=item
    total+=sum(schema.validate(r) for role,r in meta.get('baked_materials',{}).items() if role not in entries)
    if total>p['max_texture_bytes']:raise ValueError('Adoption exceeds the profile base RGBA8 texture budget')
    if encoded>p['max_bytes']:raise ValueError('Adopted map bytes exceed max_bytes')
    result={'lods_sha256':state['lods_sha256'],'preparation_sha256':ps['preparation_sha256'],'entries':entries,'rgba8_base_bytes':total,
            'source_bytes_verified':source_bytes,'replaced_assets':sorted(set(entries)&set(meta.get('baked_materials',{}))),'peak_rgba8_base_bytes':sum(r['rgba8_base_bytes'] for r in meta.get('baked_materials',{}).values())+sum(r['rgba8_base_bytes'] for r in entries.values()),'options':{k:p.get(k,False) if k=='replace_existing' else p[k] for k in ('accept_front_pbr','replace_existing','max_bytes','max_texture_bytes')},'scope':'Verified source-bound PNG maps, prepared UVs and packed private native PBR materials. No native asset import, mipmap/GPU budget or optical equivalence.'}
    result['plan_sha256']=botany.digest(result)
    return col,owned,meta,targets,pm,result


def adopt(p):
    from .bridge import check_cancelled,report_progress
    col,owned,meta,targets,pm,info=plan(p)
    if info['plan_sha256']!=p['expected_plan']:raise ValueError('Bake adoption plan is stale')
    staged=set();swaps=[];old_meta=col[lods.META];success=False;obsolete=set()
    entries={e['asset']:e for e in p['entries']}
    try:
        replacements={}
        for role,record in info['entries'].items():
            check_cancelled();report_progress({'phase':'packing vegetation PBR maps','asset':role,'completed':len(replacements),'total':len(entries)})
            images={};root=Path(entries[role]['directory'])
            for m in record['maps']:
                check_cancelled();report_progress({'phase':'packing vegetation PBR image','asset':role,'map':m['map'],'completed_maps':len(images),'total_maps':len(record['maps'])})
                image=bpy.data.images.load(str(root/'textures'/(m['map'].lower()+'.png')),check_existing=False);staged.add(image)
                image.colorspace_settings.name=m['color_space'];image.pack();image.use_fake_user=False
                if not image.packed_file or hashlib.sha256(image.packed_file.data).hexdigest()!=m['sha256']:raise ValueError('Packed image differs from verified bake')
                image.name=col.name+'_'+role+'_'+m['map'];image.filepath='';images[m['map']]=image
            before=set(bpy.data.user_map())
            try:mat=textures.baked_material(images,record['uv_map'])
            finally:staged.update(v for v in set(bpy.data.user_map())-before if not getattr(v,'is_embedded_data',False))
            mat.name=col.name+'_'+role+'_PBR'
            mesh=bpy.data.objects[pm['components'][role]['name']].data.copy();staged.add(mesh);mesh.use_fake_user=False
            mesh.materials.clear();mesh.materials.append(mat)
            for face in mesh.polygons:face.material_index=0
            replacements[role]=mesh
        # Revalidate external files and both native guards before the atomic swap.
        if plan(p)[-1]['plan_sha256']!=p['expected_plan']:raise ValueError('Bake adoption inputs changed while packing maps')
        check_cancelled()
        old_resources=set().union(*(dependencies(targets[role].data) for role in replacements))
        kept=set().union(*(dependencies(mesh) for mesh in replacements.values()),*(dependencies(obj.data) for role,obj in targets.items() if role not in replacements))
        obsolete.update((old_resources-kept)&owned)
        new_owned=(owned|staged)-obsolete
        new_meta=dict(meta);new_meta['baked_materials']=dict(meta.get('baked_materials',{}))|info['entries']
        for role,mesh in replacements.items():
            obj=targets[role];old=obj.data;name=old.name;swaps.append((obj,old,mesh,name));obsolete.add(old);new_owned.remove(old)
            old.name='MCP_AdoptionOld_'+uuid.uuid4().hex;mesh.name=name;obj.data=mesh
        for value in staged:value[lods.OWNER]=meta['owner'];value.use_fake_user=False
        new_meta['owned']=[{'type':v.bl_rna.identifier,'name':v.name} for v in sorted(new_owned,key=lambda v:(v.bl_rna.identifier,v.name))]
        bpy.context.view_layer.update();new_meta['content_sha256']=lods.signature(new_owned);col[lods.META]=json.dumps(new_meta,sort_keys=True,allow_nan=False)
        result=lods.inspect(p,ignore_users=obsolete)[-1]
        if not result['valid']:raise ValueError('Adopted LOD content/ownership verification failed')
        success=True;bpy.data.batch_remove(ids=tuple(obsolete));return result
    finally:
        if not success:
            for obj,old,mesh,name in reversed(swaps):obj.data=old;mesh.name='MCP_AdoptionRollback_'+uuid.uuid4().hex;old.name=name
            col[lods.META]=old_meta
            if staged:bpy.data.batch_remove(ids=tuple(staged))
        bpy.context.view_layer.update()


def dispatch(command,p):
    if command=='inspect_vegetation_delivery':
        col,owned,meta,state=lods.inspect(p)
        if not state['valid']:raise ValueError('Valid unchanged native LOD profile required')
        report=schema.delivery(meta.get('baked_materials',{}),list(materials.lod_objects(col,meta)),p['required_maps'],p['min_texture_size'],p['max_texture_bytes'],p['max_mip_bytes'])
        return report|{'lod_collection':col.name,'lods_sha256':state['lods_sha256'],'levels':len(meta['levels']),'shared_leaf_templates':meta['prototypes']}
    return plan(p)[-1] if command=='inspect_vegetation_bake_adoption' else adopt(p)
