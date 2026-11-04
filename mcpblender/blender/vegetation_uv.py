"""Transactional secondary layout authoring on owned native LOD delivery meshes."""
import json
import uuid
import bpy
from mcpblender import botany,vegetation_uv as schema
from . import uv,vegetation_lods as lods,vegetation_materials as materials,vegetation_bake as preparation
from .mesh_edit import geometry_digest

COMMANDS={'create_vegetation_secondary_uv'}


def hashes(mesh):
    return {layer.name:schema.uv_digest((tuple(v.uv) for v in layer.data)) for layer in mesh.uv_layers}


def verify(col,meta,objects=None):
    records=meta.get('secondary_uv',{})
    if not isinstance(records,dict):raise ValueError('Invalid owned secondary UV records')
    objects=objects if objects is not None else materials.lod_objects(col,meta)
    if not set(records)<=set(objects):raise ValueError('Secondary UV records refer to absent owned roles')
    for role,entries in records.items():
        mesh=objects[role].data
        schema.verify_maps(entries,[l.name for l in mesh.uv_layers],hashes(mesh))


def create(p):
    from .bridge import check_cancelled,report_progress
    col,owned,meta,state=lods.inspect(p)
    if state['lods_sha256']!=p['expected_lods']:raise ValueError('Botanical LOD fingerprint is stale')
    if not state['valid']:raise ValueError('Secondary UV authoring requires a valid unchanged owned LOD profile')
    objects=materials.lod_objects(col,meta);roles=p['assets'];target=p['uv_map']
    if not roles or len(set(roles))!=len(roles) or not set(roles)<=set(objects):raise ValueError('Choose distinct existing vegetation mesh asset roles')
    total=0;selected=set()
    for role in roles:
        obj=objects[role];mesh=obj.data;uv.check_size(mesh);total+=len(mesh.loops)
        if mesh not in owned or mesh in selected or mesh.users!=1:raise ValueError('Secondary UV targets must have distinct exclusively owned mesh data')
        selected.add(mesh)
        if not mesh.uv_layers or target in mesh.uv_layers or len(mesh.uv_layers)>=8:raise ValueError('Each secondary UV target needs a primary map, an absent target and a free channel: '+role)
        if obj.modifiers or obj.constraints or obj.animation_data or mesh.animation_data or mesh.shape_keys:raise ValueError('Secondary vegetation UV authoring needs static base delivery meshes')
    if total>p['max_corners']:raise ValueError('Secondary vegetation UV corner budget exceeded before staging')
    options={k:v for k,v in p.items() if k not in {'lod_collection','expected_lods','assets','max_corners'}}
    staged=set();scratch=[];swaps=[];old_meta=col[lods.META];success=False
    try:
        replacements={};records=json.loads(json.dumps(meta.get('secondary_uv',{})))
        for role in roles:
            check_cancelled();obj=objects[role];mesh=obj.data.copy();staged.add(mesh);mesh.use_fake_user=False
            owner_tags={k:mesh[k] for k in mesh.keys() if k.startswith('mcpblender_') and 'owner' in k}
            for k in owner_tags:del mesh[k]
            copy=bpy.data.objects.new('MCP_SecondaryUV_Stage',mesh);scratch.append(copy);bpy.context.scene.collection.objects.link(copy)
            copy.matrix_world=preparation.static_matrix(obj);bpy.context.view_layer.update()
            before=hashes(mesh);geometry=geometry_digest(mesh)
            report_progress({'phase':'authoring vegetation secondary UV','asset':role,'completed':len(replacements),'total':len(roles),'corners':len(mesh.loops)})
            args=options|{'name':copy.name,'expected_uv':uv.fingerprint(copy,target),'scale':True,'make_single_user':False,'island_limit':128,'overlap_budget':200000}
            result=uv.dispatch('create_secondary_uv',args)
            for k,value in owner_tags.items():mesh[k]=value
            current=hashes(mesh)
            if geometry_digest(mesh)!=geometry or any(current.get(n)!=h for n,h in before.items()):raise ValueError('Secondary UV staging changed source geometry or texture coordinates')
            record={'format':schema.FORMAT,'uv_map':target,'uv_channel':result['uv_channel'],'uv_maps':result['uv_maps'],
                    'uv_witness':current,'texture_size':[p['texture_width'],p['texture_height']],
                    'source_lods_sha256':p['expected_lods'],'options':options,'instance_atlas':False}
            record['record_sha256']=botany.digest(record);schema.validate(record)
            records.setdefault(role,[]).append(record);replacements[role]=mesh
        # Scratch meshes reference owned materials, so ignore only these known
        # temporary users while rechecking the pre-edit guard.
        current=lods.inspect(p,ignore_users=staged|set(scratch))[-1]
        if not current['valid'] or current['lods_sha256']!=p['expected_lods']:raise ValueError('Botanical LOD profile changed while staging secondary UVs')
        check_cancelled();new_owned=set(owned);new_meta=dict(meta);new_meta['secondary_uv']=records;new_meta['content_signature_version']=2
        for role,mesh in replacements.items():
            obj=objects[role];old=obj.data;name=old.name;swaps.append((obj,old,mesh,name))
            old.name='MCP_SecondaryUVOld_'+uuid.uuid4().hex;mesh.name=name;obj.data=mesh;mesh[lods.OWNER]=meta['owner'];new_owned.remove(old);new_owned.add(mesh)
        # Remove scratch object references before verifying the new ownership graph.
        for obj in scratch:bpy.data.objects.remove(obj,do_unlink=True)
        scratch.clear()
        new_meta['owned']=[{'type':v.bl_rna.identifier,'name':v.name} for v in sorted(new_owned,key=lambda v:(v.bl_rna.identifier,v.name))]
        bpy.context.view_layer.update();verify(col,new_meta,objects)
        new_meta['content_sha256']=lods.signature(new_owned,version=2);col[lods.META]=json.dumps(new_meta,sort_keys=True,allow_nan=False)
        result=lods.inspect(p,ignore_users={old for _,old,_,_ in swaps})[-1]
        if not result['valid']:raise ValueError('Secondary UV ownership verification failed')
        report_progress({'phase':'verified vegetation secondary UV batch','completed':len(replacements),'total':len(roles)});check_cancelled()
        success=True;bpy.data.batch_remove(ids=tuple(old for _,old,_,_ in swaps));return result
    finally:
        for obj in scratch:bpy.data.objects.remove(obj,do_unlink=True)
        if not success:
            for obj,old,mesh,name in reversed(swaps):
                obj.data=old;mesh.name='MCP_SecondaryUVRollback_'+uuid.uuid4().hex;old.name=name
            col[lods.META]=old_meta
            if staged:bpy.data.batch_remove(ids=tuple(staged))
        bpy.context.view_layer.update()


def dispatch(command,p):return create(p)
