"""Portable baked-map adoption witnesses and numeric-bundle UV correspondence."""
import hashlib
import re
import struct
from . import botany
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
    total=0
    for m in record['maps']:
        if m['map'] not in MAPS or not re.fullmatch('[a-f0-9]{64}',str(m['sha256'])) or type(m['bytes'])!=int or m['bytes']<=0 or any(type(m[k])!=int or not 32<=m[k]<=4096 for k in ('width','height')) or m['width']*m['height']>4*1024**2:raise ValueError('Invalid baked vegetation map witness')
        if m['color_space']!=('sRGB' if m['map'] in {'BASE_COLOR','EMISSION'} else 'Non-Color'):raise ValueError('Baked vegetation map color space changed')
        total+=m['width']*m['height']*4
    if total!=record['rgba8_base_bytes'] or record.get('portable_optical_equivalence') is not False:raise ValueError('Invalid baked vegetation memory/optical claim')
    if not record['uv_map'] or record['uv_map'] not in record['uv_witness'] or any(not re.fullmatch('[a-f0-9]{64}',str(v)) for v in record['uv_witness'].values()):raise ValueError('Invalid baked vegetation UV witness')
    if record['material_adapters'] and record.get('front_pbr_accepted') is not True:raise ValueError('Baked vegetation optical loss was not accepted')
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
