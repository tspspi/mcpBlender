"""Portable baked-map adoption witnesses and numeric-bundle UV correspondence."""
import hashlib
import re
import struct
from . import botany
from .texture_files import EMISSION_ENCODING,validate_quality_report
FORMAT='mcpblender-vegetation-baked-maps-v1'
MAPS={'NORMAL','AO','BASE_COLOR','ROUGHNESS','METALLIC','EMISSION','ALPHA'}


def uv_digest(rows):
    digest=hashlib.sha256()
    for row in rows:digest.update(struct.pack('<2f',*row))
    return digest.hexdigest()


def validate(record):
    if record.get('format')!=FORMAT or record.get('adoption_sha256')!=botany.digest({k:v for k,v in record.items() if k!='adoption_sha256'}):raise ValueError('Baked vegetation adoption binding changed')
    for key in ('preparation_sha256','bake_sha256','bundle_manifest_sha256','geometry_sha256'):
        if not re.fullmatch('[a-f0-9]{64}',str(record.get(key,''))):raise ValueError('Invalid baked vegetation source binding')
    if not 1<=len(record['maps'])<=7 or len({m['map'] for m in record['maps']})!=len(record['maps']):raise ValueError('Invalid baked vegetation map inventory')
    if record.get('emission_encoding') not in (None,EMISSION_ENCODING):raise ValueError('Unsupported vegetation emission map encoding')
    if record.get('texture_quality') is not None:
        policy=validate_quality_report(record['texture_quality'])
        if not re.fullmatch('[a-f0-9]{64}',str(record.get('preparation_bake_sha256',''))):raise ValueError('Quality adoption lacks its original preparation binding')
        if any((m['width'],m['height'])!=(policy['width'],policy['height']) for m in record['maps']):raise ValueError('Adopted maps differ from retained quality dimensions')
    total=0
    for m in record['maps']:
        if m['map'] not in MAPS or not re.fullmatch('[a-f0-9]{64}',str(m['sha256'])) or type(m['bytes'])!=int or m['bytes']<=0 or any(type(m[k])!=int or not 32<=m[k]<=4096 for k in ('width','height')) or m['width']*m['height']>4*1024**2:raise ValueError('Invalid baked vegetation map witness')
        if m['color_space']!=('sRGB' if m['map'] in {'BASE_COLOR','EMISSION'} else 'Non-Color'):raise ValueError('Baked vegetation map color space changed')
        total+=m['width']*m['height']*4
    if total!=record['rgba8_base_bytes'] or record.get('portable_optical_equivalence') is not False:raise ValueError('Invalid baked vegetation memory/optical claim')
    if not record['uv_map'] or record['uv_map'] not in record['uv_witness'] or any(not re.fullmatch('[a-f0-9]{64}',str(v)) for v in record['uv_witness'].values()):raise ValueError('Invalid baked vegetation UV witness')
    if (record['material_adapters'] or record.get('inherited_material_adapters')) and record.get('front_pbr_accepted') is not True:raise ValueError('Baked vegetation optical loss was not accepted')
    if type(record.get('revision',1))!=int or not 1<=record.get('revision',1)<=1024:raise ValueError('Invalid vegetation texture revision')
    if record.get('revision',1)>1 and record.get('previous_adoption_sha256') is None:raise ValueError('Vegetation texture revision lacks previous binding')
    if 'preparation_owner' in record and (not re.fullmatch('[a-f0-9]{32}',str(record['preparation_owner'])) or type(record.get('preparation_revision'))!=int or not 0<=record['preparation_revision']<=1024):raise ValueError('Invalid preparation revision lineage')
    owners=record.get('source_preparation_owners',[])
    if not isinstance(owners,list) or len(owners)>1024 or len(set(owners))!=len(owners) or any(not re.fullmatch('[a-f0-9]{32}',str(owner)) for owner in owners):raise ValueError('Invalid source preparation lineage')
    if record.get('previous_adoption_sha256') is not None and not re.fullmatch('[a-f0-9]{64}',str(record['previous_adoption_sha256'])):raise ValueError('Invalid previous vegetation adoption binding')
    return total


def verify(root,records,assets):
    from pathlib import Path
    from .lod_files import read_glb
    from .package_files import texture_infos
    import json
    root=Path(root)
    if not records or not set(records)<=set(assets):raise ValueError('Unexpected baked vegetation asset roles')
    for asset,record in records.items():
        validate(record)
        sub=json.loads((root/asset/'manifest.json').read_text());names=sub['source']['uv_maps'];uvs=sub['witness']['uvs']
        if len(names)!=len(uvs) or len(set(names))!=len(names):raise ValueError('Baked vegetation UV channel inventory changed')
        actual={name:uv_digest(rows) for name,rows in zip(names,uvs)}
        if actual!=record['uv_witness']:raise ValueError('Baked vegetation UVs differ from adopted layout')
        doc,_=read_glb(root/asset/'asset.glb');channel=names.index(record['uv_map'])
        used={p['material'] for mesh in doc['meshes'] for p in mesh['primitives'] if 'material' in p}
        infos=[spec for i in used for spec in texture_infos(doc['materials'][i])]
        if not infos or any(spec.get('extensions',{}).get('KHR_texture_transform',{}).get('texCoord',spec.get('texCoord',0))!=channel for spec in infos):raise ValueError('Encoded baked vegetation textures do not use the adopted UV channel')


def mip_bytes(width,height):
    total=0
    while True:
        total+=width*height*4
        if width==height==1:return total
        width=max(1,width//2);height=max(1,height//2)


def delivery(records,assets,required_maps,min_texture_size,max_texture_bytes,max_mip_bytes,*,require_quality=False,scene_unit_scale=None):
    if not assets or len(set(assets))!=len(assets) or not set(records)<=set(assets):raise ValueError('Invalid vegetation delivery component inventory')
    if not required_maps or len(set(required_maps))!=len(required_maps) or not set(required_maps)<=MAPS:raise ValueError('Invalid vegetation delivery required maps')
    missing=[asset for asset in assets if asset not in records];map_gaps={};resolution_gaps={};encoding_gaps={};base=0;mips=0;losses=set();sampling=[]
    for asset,record in records.items():
        base+=validate(record);mips+=sum(mip_bytes(m['width'],m['height']) for m in record['maps'])
        if any(m['map']=='EMISSION' for m in record['maps']) and record.get('emission_encoding')!=EMISSION_ENCODING:encoding_gaps[asset]=['EMISSION_RADIANCE_CONVENTION']
        gaps=sorted(set(required_maps)-{m['map'] for m in record['maps']})
        if gaps:map_gaps[asset]=gaps
        small=[{'map':m['map'],'size':[m['width'],m['height']]} for m in record['maps'] if m['map'] in required_maps and min(m['width'],m['height'])<min_texture_size]
        if small:resolution_gaps[asset]=small
        for adapter in record['material_adapters']+record.get('inherited_material_adapters',[]):losses.update(adapter.get('omitted_features',[]))
        if record.get('source_sampling_changes') or record.get('inherited_sampling_changes'):sampling.append(asset)
    budget={'rgba8_base_bytes':base,'rgba8_full_mip_bytes':mips,'max_texture_bytes':max_texture_bytes,'max_mip_bytes':max_mip_bytes,'passed':base<=max_texture_bytes and mips<=max_mip_bytes,
            'scope':'All adopted source map inputs counted separately per component, with a full floor-halved mip chain to 1x1. No cross-component deduplication, encoded-channel packing, compression, Blender cache or GPU allocation model.'}
    unchecked=[asset for asset in assets if not records.get(asset,{}).get('texture_quality')]
    unit_gaps=[asset for asset,r in records.items() if r.get('texture_quality') and scene_unit_scale is not None and r['texture_quality'].get('scene_unit_scale')!=scene_unit_scale]
    return {'complete':not missing and not map_gaps and not resolution_gaps and not encoding_gaps and budget['passed'] and (not require_quality or not unchecked and not unit_gaps),'expected_assets':assets,'adopted_assets':sorted(records),'missing_assets':missing,'missing_maps':map_gaps,'resolution_gaps':resolution_gaps,'map_encoding_gaps':encoding_gaps,
            'quality_scene_unit_gaps':unit_gaps,
            'quality_required':require_quality,'assets_without_quality_reports':unchecked,'quality_policies':{asset:r['texture_quality']['policy'] for asset,r in records.items() if r.get('texture_quality')},
            'required_maps':required_maps,'min_texture_size':min_texture_size,'budget':budget,'optical_omissions':sorted(losses),'sampling_changed_assets':sorted(sampling),
            'scope':'Adopted input-map coverage, resolution/memory criteria and optional retained source-bound geometric quality under each recorded policy. No new geometric measurement, visual quality, physical optics, shadow/filtering, receiving-engine or animated LOD qualification.'}
