"""Verified wind interchange from owned botanical sources, retaining prototypes."""
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import bpy
from mathutils import Matrix,Vector
from mathutils.kdtree import KDTree
from mcpblender import botany,wind,vegetation_interchange as schema
from mcpblender.storage import require_space
from . import botanical_wind as motion,botanical_foliage,botanical_trees,attribute_export

COMMANDS={'inspect_botanical_export','export_botanical_bundle','validate_botanical_bundle'}


def source(p):
    values,info=motion.source(p);population=motion.layout(values)
    count=len(population['leaves']) if population else 0
    if count>p['max_instances']:raise ValueError('Botanical export instance budget exceeded')
    roles=botanical_foliage.resolve_roles(values[-1]['foliage']) if values[-1]['foliage'] else {}
    meshes=[values[2][0]]+([roles['so']] if count else [])
    corners=sum(len(obj.data.loops) for obj in meshes)+(sum(len(roles['lo'+str(i)].data.loops) for i in range(population['recipe']['variants'])) if count else 0)
    if corners>p['max_corners']:raise ValueError('Botanical export total corner budget exceeded')
    cfg={k:p[k] for k in ('collection','max_instances','max_corners')};cfg['wind']=info['wind']
    info={'format':schema.FORMAT,'wind':info,'options':cfg,'leaf_instances':count,'prototypes':population['recipe']['variants'] if count else 0,'corners':corners,
          'source_guard':values[-1]['tree_sha256'],'estimated_geometry_bytes':corners*200}
    info['export_sha256']=botany.digest(info)
    return values,population,roles,info


def inspect(p):return source(p)[-1]


def native_instances(values,population,roles,info):
    from .bridge import check_cancelled
    report={'instances':0,'max_position_error_m':0.,'max_linear_component_error':0.}
    if not population or not population['leaves']:return report
    unit=values[-1]['scene_unit_scale'];where=info['wind']['placement'];leaves=population['leaves'];tree=KDTree(len(leaves));used=set()
    for i,leaf in enumerate(leaves):tree.insert(Vector(wind.world(where,leaf['position'])),i)
    tree.balance();rotation=Matrix(where['rotation']);deps=bpy.context.evaluated_depsgraph_get()
    for j,item in enumerate(deps.object_instances):
        if j%512==0:check_cancelled()
        if j>=1000000:raise ValueError('Botanical native instance scan budget exceeded')
        if not item.is_instance or not item.parent or item.parent.original!=roles['po'] or not item.show_self:continue
        actual=item.matrix_world;center=actual.translation*unit;best=None
        for _,i,distance in tree.find_range(center,1e-4):
            leaf=leaves[i]
            if i in used or item.object.original!=roles['lo'+str(leaf['variant'])]:continue
            expected=rotation@Matrix(wind.euler_rotation(leaf['rotation']));scale=where['scale']*leaf['scale']
            error=max(abs(actual[a][b]*unit-expected[a][b]*scale)/max(1,scale) for a in range(3) for b in range(3))
            score=(error,distance,i)
            if best is None or score<best:best=score
        if best is None:raise ValueError('Botanical leaf instance missing, duplicated or outside canonical placement tolerance')
        error,distance,i=best;used.add(i);report['instances']+=1
        report['max_position_error_m']=max(report['max_position_error_m'],distance);report['max_linear_component_error']=max(report['max_linear_component_error'],error)
        if error>1e-5:raise ValueError('Botanical leaf orientation/scale differs from semantic instance')
    if len(used)!=len(leaves):raise ValueError('Botanical native leaf population differs from exported table')
    return report


def export_mesh(original,label,model,directory,*,max_corners,max_bytes,unit,matrix=None):
    from .bridge import check_cancelled
    mesh=original.data.copy();mesh.use_fake_user=False;obj=None
    try:
        obj=bpy.data.objects.new('MCP_BotanicalDelivery',mesh);bpy.context.scene.collection.objects.link(obj)
        obj.matrix_world=matrix if matrix is not None else original.matrix_world if label in {'wood','shoots'} else Matrix.Diagonal((1/unit,)*3+(1,))
        if label in {'wood','shoots'}:
            ids=[v.value for v in mesh.attributes['bot_branch_index'].data]
            fields=schema.branch_fields(model,[list(v.co) for v in mesh.vertices],ids)
            for name,kind,_ in schema.BRANCH_FIELDS:
                if mesh.attributes.get(name):raise ValueError('Reserved botanical delivery attribute collision')
                botanical_trees.attribute(mesh,name,kind,fields[name])
            bindings=[{'attribute':name,'semantic':semantic} for name,_,semantic in schema.BRANCH_FIELDS]
        else:
            botanical_trees.attribute(mesh,'template_vertex_index','INT',list(range(len(mesh.vertices))))
            bindings=[{'attribute':'template_vertex_index','semantic':'template.vertex_index'}]
        mesh.update();bpy.context.view_layer.update()
        args={'name':obj.name,'fields':bindings,'max_corners':max_corners};inspected=attribute_export.inspect(args)
        attribute_export.export(args|{'expected_export':inspected['export_sha256'],'directory':str(directory),'max_bytes':max_bytes})
    finally:
        if obj:bpy.data.objects.remove(obj,do_unlink=True)
        if mesh.users==0:bpy.data.meshes.remove(mesh)


def export(p):
    from .bridge import check_cancelled,report_progress,_bridge
    values,population,roles,plan=source(p)
    if plan['export_sha256']!=p['expected_export']:raise ValueError('Botanical export fingerprint is stale; inspect again')
    destination=Path(p['directory'])
    if destination.exists():raise FileExistsError(destination)
    data=schema.semantics(values[-2],population,plan['wind']);encoded=(json.dumps(data,sort_keys=True,allow_nan=False)+'\n').encode()
    estimate=len(encoded)*2+plan['estimated_geometry_bytes']*3+16*1024**2
    if len(encoded)>p['max_bytes']:raise ValueError('Botanical semantic data exceeds max_bytes')
    policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {}
    if _bridge and _bridge.active:_bridge.active['storage'].update(estimated_bytes=estimate,estimate_kind='botanical_geometry_semantics_heuristic_excludes_material_images')
    storage=require_space(destination,estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='botanical_geometry_semantics_heuristic_excludes_material_images')
    report_progress({'phase':'checking canonical native leaf instances','storage':storage})
    native=native_instances(values,population,roles,plan);check_cancelled()
    job=p.get('_export_job');stage=job.stage if job else Path(tempfile.mkdtemp(prefix='.mcpblender-botanical-',dir=destination.parent));assets=[]
    if job:stage.mkdir(mode=0o700);job.created()
    try:
        (stage/'semantics.json').write_bytes(encoded)
        jobs=[('wood',values[2][0])]+([('shoots',roles['so'])]+[(f'leaf-{i}',roles['lo'+str(i)]) for i in range(plan['prototypes'])] if plan['leaf_instances'] else [])
        for label,original in jobs:
            check_cancelled();export_mesh(original,label,values[-2],stage/label,max_corners=min(1000000,p['max_corners']),max_bytes=p['max_bytes'],unit=values[-1]['scene_unit_scale'])
            assets.append(label)
            inventory=schema.files(stage);size=sum(r['bytes'] for r in inventory)
            if size>p['max_bytes']:raise ValueError('Botanical bundle exceeds max_bytes')
            report_progress({'phase':'exported botanical component','component':label,'completed':len(assets),'total':len(jobs),'bytes':size})
        if botanical_trees.inspect({'collection':p['collection']})['tree_sha256']!=plan['source_guard']:raise ValueError('Botanical source changed during export')
        record={'export_sha256':plan['export_sha256'],'format':schema.FORMAT,'source':plan,'assets':assets,'files':schema.files(stage),'native_instance_readback':native,
                'material_limits':'Native materials exported through Blender glTF; thin-leaf backlighting/vein shader fidelity is not certified. Keep the editable source and bake PBR separately.'}
        serialized=(json.dumps(record,sort_keys=True,allow_nan=False)+'\n').encode()
        if sum(r['bytes'] for r in record['files'])+len(serialized)>p['max_bytes']:raise ValueError('Botanical manifest exceeds max_bytes')
        storage=require_space(destination,len(serialized),reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='serialized_botanical_manifest_bytes')
        (stage/'manifest.json').write_bytes(serialized)
        proof=job.verify(check_cancelled,report_progress) if job else schema.validate(stage,cancelled=check_cancelled)
        report_progress({'phase':'verified botanical bundle before publication','storage':storage});check_cancelled()
        if job:
            if destination.exists() or destination.is_symlink():raise FileExistsError(destination)
            stage.rename(destination)
        else:
            destination.mkdir(mode=0o700)
            try:
                for path in list(stage.iterdir()):os.rename(path,destination/path.name)
            except BaseException:
                # Destination was exclusively reserved here, and contains only owned moves.
                for path in destination.iterdir():
                    if path.is_dir():shutil.rmtree(path)
                    else:path.unlink()
                destination.rmdir();raise
        return {'directory':str(destination),'export_sha256':plan['export_sha256'],'proof':proof,'native_instance_readback':native}
    finally:
        if not job:shutil.rmtree(stage)


def dispatch(command,p):
    if command=='inspect_botanical_export':return inspect(p)
    if command=='export_botanical_bundle':return export(p)
    from .bridge import check_cancelled
    return schema.validate(p['directory'],cancelled=check_cancelled)
