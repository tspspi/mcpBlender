"""Source-preserving GLB/wind interchange for native botanical LOD profiles."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import bpy
from mathutils import Matrix
from mcpblender import botany,wind,vegetation_lod,vegetation_lod_files as files,vegetation_interchange as common
from mcpblender.storage import require_space
from . import vegetation_lods,vegetation_export

COMMANDS={'export_botanical_lods','validate_botanical_lod_bundle'}


def matrix_for(where,unit):
    result=Matrix(where['rotation']).to_4x4()
    for i in range(3):
        for j in range(3):result[i][j]*=where['scale']/unit
        result[i][3]=where['translation_m'][i]/unit
    return result


def displayed(root,unit):
    m=root.matrix_world;scale=sum(m.to_3x3().col[i].length*unit for i in range(3))/3
    return wind.placement({'rotation':[[m[i][j]*unit/scale for j in range(3)] for i in range(3)],'scale':scale,'translation_m':[m[i][3]*unit for i in range(3)]})


def export(p):
    from .bridge import check_cancelled,report_progress,_bridge
    col,owned,meta,state=vegetation_lods.inspect(p)
    if p['expected_lods']!=state['lods_sha256']:raise ValueError('Botanical LOD fingerprint is stale')
    if not state['valid']:raise ValueError('Botanical LOD export requires valid unchanged owned content')
    destination=Path(p['directory'])
    if destination.exists():raise FileExistsError(destination)
    text=col.get(vegetation_lods.TEXT)
    if not text or len(text.as_string())>128*1024**2:raise ValueError('LOD semantic Text is absent or exceeds budget')
    data=json.loads(text.as_string());model=data['model'];population=data['foliage'];selection=data['selection'];source_wind=data['wind']
    root=bpy.data.objects[meta['root']];unit=bpy.context.scene.unit_settings.scale_length
    shown=displayed(root,unit);where=source_wind['placement'] if p['placement']=='SOURCE' else shown
    delivery_wind={k:v for k,v in source_wind.items() if k!='wind_sha256'}|{'placement':where};delivery_wind['wind_sha256']=botany.digest(delivery_wind)
    delivery_matrix=matrix_for(where,unit)
    inferred=[s for s in range(5,17) if vegetation_lod.wood_triangles(model,list(range(len(model['branches']))),s)==meta['levels'][0]['native_triangles'][0]]
    if len(inferred)!=1:raise ValueError('Cannot identify canonical LOD0 radial sides')
    sides=inferred[0];levels=[files.full_level(model,population,sides),*selection['levels']]
    descriptors=[{'level':i,'wood':f'lod-{i}-wood','shoots':f'lod-{i}-shoots','leaf_indices':l['leaf_indices'],'branch_indices':l['branch_indices'],'shoot_indices':l['shoot_indices']} for i,l in enumerate(levels)]
    templates=[f'leaf-{i}' for i in range(population['recipe']['variants'])]
    semantic={'format':files.FORMAT,'model':model,'foliage':population,'selection':selection,'source_radial_sides':sides,
              'source_wind':source_wind,'wind':delivery_wind,'placement_mode':p['placement'],'displayed_placement':shown,'levels':descriptors,'templates':templates,
              'coordinates':common.semantics(model,population,delivery_wind)['coordinates']}
    encoded=(json.dumps(semantic,sort_keys=True,allow_nan=False)+'\n').encode()
    if len(encoded)>p['max_bytes']:raise ValueError('LOD semantics exceed max_bytes')
    estimate=len(encoded)*2+sum(len(bpy.data.objects[n].data.loops)*256 for level in meta['levels'] for n in level['objects'][:2])+16*1024**2
    policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {}
    if _bridge and _bridge.active:_bridge.active['storage'].update(estimated_bytes=estimate,estimate_kind='lod_geometry_semantic_heuristic_excludes_embedded_material_images')
    storage=require_space(destination,estimate,reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='lod_geometry_semantic_heuristic_excludes_embedded_material_images')
    report_progress({'phase':'staging shared vegetation LOD bundle','storage':storage});check_cancelled()
    job=p.get('_export_job');stage=job.stage if job else Path(tempfile.mkdtemp(prefix='.mcpblender-vegetation-lods-',dir=destination.parent));assets=[]
    if job:stage.mkdir(mode=0o700);job.created()
    try:
        (stage/'semantics.json').write_bytes(encoded)
        prototypes=col['mcpblender_leaf_sources'];prototype_objects=sorted(prototypes.objects,key=lambda o:o.name)
        jobs=[(saved[role],role,bpy.data.objects[level['objects'][r]],delivery_matrix) for saved,level in zip(descriptors,meta['levels']) for r,role in enumerate(('wood','shoots'))]
        jobs.extend((name,name,prototype_objects[i],None) for i,name in enumerate(templates))
        for asset,role,obj,matrix in jobs:
            check_cancelled();vegetation_export.export_mesh(obj,role,model,stage/asset,max_corners=1000000,max_bytes=p['max_bytes'],unit=unit,matrix=matrix)
            assets.append(asset);inventory=common.files(stage);size=sum(row['bytes'] for row in inventory)
            if size>p['max_bytes']:raise ValueError('LOD bundle exceeds max_bytes')
            report_progress({'phase':'exported vegetation LOD component','component':asset,'completed':len(assets),'total':len(jobs),'bytes':size})
        if vegetation_lods.inspect(p)[-1]['lods_sha256']!=p['expected_lods']:raise ValueError('Native LOD profile changed during export')
        record={'placement_mode':p['placement'],'format':files.FORMAT,'profile_guard':p['expected_lods'],'assets':assets,'files':common.files(stage),
                'native_creation_readback':meta['verification'],'material_limits':'Native shared materials passed through glTF. Backlighting/vein/alpha/texture fidelity is not qualified; bake PBR separately.'}
        serialized=(json.dumps(record,sort_keys=True,allow_nan=False)+'\n').encode()
        if len(serialized)+sum(row['bytes'] for row in record['files'])>p['max_bytes']:raise ValueError('LOD manifest exceeds max_bytes')
        storage=require_space(destination,len(serialized),reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='serialized_vegetation_lod_manifest_bytes')
        (stage/'manifest.json').write_bytes(serialized)
        proof=job.verify(check_cancelled,report_progress) if job else files.validate(stage,cancelled=check_cancelled,progress=report_progress)
        report_progress({'phase':'verified vegetation LOD bundle before publication','storage':storage});check_cancelled()
        if job:
            if destination.exists() or destination.is_symlink():raise FileExistsError(destination)
            stage.rename(destination)
        else:
            destination.mkdir(mode=0o700)
            # Publication failures leave the exclusive partial directory for review.
            # Never sweep a destination another process may already be using.
            for path in list(stage.iterdir()):os.rename(path,destination/path.name)
        return {'directory':str(destination),'proof':proof,'profile_guard':p['expected_lods'],'placement':p['placement']}
    finally:
        if not job:shutil.rmtree(stage)


def dispatch(command,p):
    if command=='export_botanical_lods':return export(p)
    from .bridge import check_cancelled,report_progress
    return files.validate(p['directory'],cancelled=check_cancelled,progress=report_progress)
