"""Owned master secondary layouts, guarded publication and regeneration policy."""
import json
import uuid
import bpy
from mcpblender import botany,vegetation_uv as schema
from . import botanical_trees as trees,botanical_foliage as foliage,vegetation_uv as layouts
from .mesh_edit import geometry_digest
from .assembly_realization import mesh_record

COMMANDS={'create_botanical_secondary_uv'}


def objects(meta):
    result={'wood':bpy.data.objects[next(v['object'] for v in meta['members'] if v['role']=='WOOD')]}
    if meta.get('foliage'):
        roles=foliage.resolve_roles(meta['foliage'])
        result.update({f'leaf-{i}':roles['lo'+str(i)] for i in range(meta['foliage']['recipe']['variants'])})
    return result


def verify(meta):
    records=meta.get('secondary_uv',{})
    if not isinstance(records,dict):raise ValueError('Invalid botanical secondary UV records')
    targets=objects(meta)
    if not set(records)<=set(targets):raise ValueError('Botanical secondary UV target disappeared')
    for role,entries in records.items():
        mesh=targets[role].data
        schema.verify_maps(entries,[l.name for l in mesh.uv_layers],layouts.hashes(mesh))


def refresh(meta):
    for entry in meta['members']:
        entry['mesh_sha256']=botany.digest(mesh_record(bpy.data.objects[entry['object']].data))
    if meta.get('foliage'):meta['foliage']['content_sha256']=foliage.component_signature(foliage.resolve_roles(meta['foliage']))


def create(p):
    from .bridge import check_cancelled,report_progress
    col,root,members,text,owned,links,model,state=trees.guarded(p)
    if not state['valid'] or state['replacement_blockers']:raise ValueError('Secondary UV authoring requires a valid static botanical master')
    original=col[trees.META];meta=json.loads(original);targets=objects(meta);roles=p['assets'];name=p['uv_map']
    if not roles or len(set(roles))!=len(roles) or not set(roles)<=set(targets):raise ValueError('Choose distinct wood or shared leaf-template roles')
    total=0;meshes=set()
    for role in roles:
        mesh=targets[role].data;layouts.uv.check_size(mesh);total+=len(mesh.loops)
        if mesh.users!=1 or mesh in meshes:raise ValueError('Botanical UV targets require exclusive mesh ownership')
        if not mesh.uv_layers or name in mesh.uv_layers or len(mesh.uv_layers)>=8:raise ValueError('Botanical secondary UV needs a primary map, absent target and free channel')
        meshes.add(mesh)
    if total>p['max_corners']:raise ValueError('Botanical secondary UV corner budget exceeded before staging')
    options={k:v for k,v in p.items() if k not in {'collection','expected_tree','assets','max_corners'}}
    staged=[];swaps=[];success=False
    try:
        replacements={};records=meta.setdefault('secondary_uv',{})
        for role in roles:
            check_cancelled();report_progress({'phase':'authoring botanical secondary UV','asset':role,'completed':len(replacements),'total':len(roles)})
            mesh,record=layouts.stage(targets[role],options,p['expected_tree'],master=True)
            staged.append(mesh);replacements[role]=mesh;records.setdefault(role,[]).append(record)
        if trees.inspect(p)['tree_sha256']!=p['expected_tree']:raise ValueError('Botanical master changed while staging UVs')
        check_cancelled()
        for role,mesh in replacements.items():
            obj=targets[role];old=obj.data;public=old.name;swaps.append((obj,old,mesh,public))
            old.name='BotanicalUVOld_'+uuid.uuid4().hex;mesh.name=public;obj.data=mesh
        refresh(meta);verify(meta);col[trees.META]=json.dumps(meta,sort_keys=True,allow_nan=False);bpy.context.view_layer.update()
        result=trees.inspect(p)
        if not result['valid']:raise ValueError('Botanical secondary UV ownership validation failed')
        report_progress({'phase':'verified botanical secondary UV batch','completed':len(roles),'total':len(roles)});check_cancelled()
        bpy.data.batch_remove(ids=tuple(old for _,old,_,_ in swaps));success=True;return result
    finally:
        if not success:
            for obj,old,mesh,public in reversed(swaps):
                obj.data=old;mesh.name='BotanicalUVRollback_'+uuid.uuid4().hex;old.name=public
            col[trees.META]=original
            if staged:bpy.data.batch_remove(ids=tuple(staged))
        bpy.context.view_layer.update()


def copy_maps(source,target,entries):
    if geometry_digest(source.data)!=geometry_digest(target.data):raise ValueError('Secondary UV preservation requires identical geometry; choose REPROJECT or DISCARD explicitly')
    for entry in entries:
        name=entry['uv_map'];layer=target.data.uv_layers.get(name)
        if layer:raise ValueError('Secondary UV preservation target already exists')
        layer=target.data.uv_layers.new(name=name)
        layer.data.foreach_set('uv',[v for item in source.data.uv_layers[name].data for v in item.uv])
    schema.verify_maps(entries,[l.name for l in target.data.uv_layers],layouts.hashes(target.data))
    if source.data.uv_layers.active:target.data.uv_layers.active=target.data.uv_layers[source.data.uv_layers.active.name]
    rendered=next((l.name for l in source.data.uv_layers if l.active_render),None)
    if rendered:target.data.uv_layers[rendered].active_render=True


def regenerate(old_meta,new_col,policy,source_guard):
    """Edit only the disposable regenerated master; source handoff owns rollback."""
    records=old_meta.get('secondary_uv',{})
    if not records or policy=='DISCARD':return
    if policy not in {'PRESERVE','REPROJECT'}:raise ValueError('Unknown secondary UV regeneration policy')
    source=objects(old_meta);meta=json.loads(new_col[trees.META]);targets=objects(meta);new_records={}
    if not set(records)<=set(targets):raise ValueError('Regeneration removes a secondary UV role; choose DISCARD explicitly')
    for role,entries in records.items():
        if policy=='PRESERVE':
            copy_maps(source[role],targets[role],entries);new_records[role]=entries
        else:
            new_records[role]=[]
            for entry in entries:
                mesh,record=layouts.stage(targets[role],entry['options'],source_guard,master=True)
                obj=targets[role];old=obj.data;name=old.name;old.name='BotanicalUVReprojectOld_'+uuid.uuid4().hex;mesh.name=name;obj.data=mesh;bpy.data.meshes.remove(old)
                new_records[role].append(record)
    meta['secondary_uv']=new_records;refresh(meta);verify(meta);new_col[trees.META]=json.dumps(meta,sort_keys=True,allow_nan=False)


def dispatch(command,p):return create(p)
