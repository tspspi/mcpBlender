"""Bounded, independent validation of our static GLB LOD delivery bundles."""
import hashlib
import json
import math
from pathlib import Path
import struct

MARKER='mcpblender-static-lod-v1'
SKIN_MARKER='mcpblender-animated-lod-v1'


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def read_glb(path):
    path=Path(path)
    if path.stat().st_size>512*1024**2:raise ValueError('GLB exceeds 512 MiB validation limit')
    data=path.read_bytes()
    if len(data)<20 or struct.unpack_from('<4sII',data)!=(b'glTF',2,len(data)):raise ValueError('Invalid GLB header')
    cursor=12;doc=None;binary=None
    while cursor<len(data):
        if cursor+8>len(data):raise ValueError('Truncated GLB chunk')
        size,kind=struct.unpack_from('<II',data,cursor);cursor+=8
        if cursor+size>len(data) or size%4:raise ValueError('Invalid GLB chunk bounds')
        payload=data[cursor:cursor+size];cursor+=size
        if kind==0x4e4f534a:
            if doc is not None or size>16*1024**2:raise ValueError('Duplicate/oversized GLB JSON')
            doc=json.loads(payload)
        elif kind==0x004e4942:
            if binary is not None:raise ValueError('Duplicate GLB binary')
            binary=payload
    if doc is None or binary is None:raise ValueError('GLB needs JSON and embedded binary')
    buffers=doc.get('buffers',[])
    if len(buffers)!=1 or 'uri' in buffers[0] or buffers[0]['byteLength']>len(binary):raise ValueError('External or invalid GLB buffer')
    for image in doc.get('images',[]):
        if 'uri' in image or 'bufferView' not in image:raise ValueError('Texture images must be embedded in GLB')
        view=doc['bufferViews'][image['bufferView']]
        if view.get('buffer',0)!=0 or view.get('byteOffset',0)+view['byteLength']>len(binary):raise ValueError('Invalid embedded image bounds')
    return doc,binary


def glb_report(path,skinned=False,morphs=False):
    doc,binary=read_glb(path)
    if not skinned and (doc.get('skins') or doc.get('animations')):raise ValueError('Static LOD bundle cannot contain skins/animations')
    def attribute(index,components):
        accessor=doc['accessors'][index]
        if accessor.get('sparse') or accessor.get('normalized') or accessor.get('componentType')!=5126 or accessor.get('type')!=f'VEC{components}':raise ValueError('Expected dense float GLB attribute')
        count=accessor['count']
        if not 0<count<=2000000:raise ValueError('GLB attribute count outside limits')
        view=doc['bufferViews'][accessor['bufferView']];stride=view.get('byteStride',components*4);start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
        end=start+(count-1)*stride+components*4
        if view.get('buffer',0)!=0 or start<0 or view.get('byteOffset',0)<0 or accessor.get('byteOffset',0)<0 or stride<components*4 or end>len(binary) or end>view.get('byteOffset',0)+view['byteLength']:raise ValueError('GLB attribute bounds invalid')
        low=[math.inf]*components;high=[-math.inf]*components
        for i in range(count):
            values=struct.unpack_from('<'+'f'*components,binary,start+i*stride)
            if not all(math.isfinite(v) for v in values):raise ValueError('Nonfinite GLB attribute')
            if components==3 and index==current_normal and abs(sum(v*v for v in values)-1)>.02:raise ValueError('GLB normals must be unit vectors')
            low=[min(a,b) for a,b in zip(low,values)];high=[max(a,b) for a,b in zip(high,values)]
        return {'count':count,'min':low,'max':high}
    triangles=0;primitives=[]
    for mesh in doc.get('meshes',[]):
        for prim in mesh.get('primitives',[]):
            if prim.get('mode',4)!=4 or (prim.get('targets') and not morphs):raise ValueError('Triangle primitives required; morph targets need explicit morph validation')
            attrs=prim.get('attributes',{});current_normal=attrs.get('NORMAL')
            if 'POSITION' not in attrs or current_normal is None:raise ValueError('GLB requires positions and normals')
            position=attribute(attrs['POSITION'],3);normal=attribute(current_normal,3)
            if position['count']!=normal['count']:raise ValueError('GLB normal count mismatch')
            uv={k:attribute(v,2) for k,v in attrs.items() if k.startswith('TEXCOORD_')}
            if any(a['count']!=position['count'] for a in uv.values()):raise ValueError('GLB UV count mismatch')
            if 'indices' in prim:
                accessor=doc['accessors'][prim['indices']];kind=accessor.get('componentType');count=accessor['count']
                if not 0<count<=1500000 or kind not in {5121,5123,5125} or accessor.get('type')!='SCALAR' or accessor.get('sparse'):raise ValueError('Invalid GLB indices')
                view=doc['bufferViews'][accessor['bufferView']];size,fmt={5121:(1,'B'),5123:(2,'H'),5125:(4,'I')}[kind];start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
                if start<0 or view.get('byteOffset',0)<0 or accessor.get('byteOffset',0)<0 or view.get('buffer',0)!=0 or view.get('byteStride',size)!=size or start+count*size>min(len(binary),view.get('byteOffset',0)+view['byteLength']):raise ValueError('Invalid index bounds')
                if any(struct.unpack_from('<'+fmt,binary,start+i*size)[0]>=position['count'] for i in range(count)):raise ValueError('GLB index references missing vertex')
            else:count=position['count']
            if count%3:raise ValueError('GLB triangle index count is not divisible by three')
            if 'material' in prim and not 0<=prim['material']<len(doc.get('materials',[])):raise ValueError('Invalid primitive material')
            triangles+=count//3;primitives.append({'triangles':count//3,'position':position,'normals':True,'uv_sets':sorted(uv),'material':prim.get('material')})
    if not triangles:raise ValueError('GLB contains no triangle geometry')
    bounds={key:[f(p['position'][key][i] for p in primitives) for i in range(3)] for key,f in (('min',min),('max',max))}
    return {'position_bounds':bounds,'triangles':triangles,'primitives':primitives,'meshes':len(doc.get('meshes',[])),'materials':len(doc.get('materials',[])),'images':len(doc.get('images',[])),'embedded_dependencies':True}


def validate(directory):
    root=Path(directory);manifest=root/'manifest.json'
    if manifest.is_symlink() or not manifest.is_file() or manifest.stat().st_size>8*1024**2:raise ValueError('Missing/oversized LOD manifest')
    doc=json.loads(manifest.read_text())
    if doc.get('format') not in {MARKER,SKIN_MARKER} or not 2<=len(doc.get('levels',[]))<=8:raise ValueError('Invalid LOD manifest')
    files=[]
    for i,level in enumerate(doc['levels']):
        if level.get('file')!=f'level_{i:02}.glb':raise ValueError('Unexpected LOD member path')
        path=root/level['file']
        if path.is_symlink() or not path.is_file() or path.stat().st_size>512*1024**2 or file_hash(path)!=level['sha256']:raise ValueError('LOD member missing or hash mismatch')
        skinned=doc['format']==SKIN_MARKER
        report=glb_report(path,skinned=skinned)
        if skinned:
            from .skin_glb import Document
            skin=Document(path)
            if skin.report()!=level['skin']:raise ValueError('Skin/animation inventory differs from manifest')
        if report['triangles']!=level['triangles'] or report['triangles']>level['triangle_budget']:raise ValueError('GLB triangle count/budget mismatch')
        if any(abs(a-b)>1e-5+abs(b)*1e-7 for key in ('min','max') for a,b in zip(report['position_bounds'][key],level['position_bounds'][key])):raise ValueError('Exported position bounds differ from native LOD')
        if level['uv_required'] and any('TEXCOORD_0' not in p['uv_sets'] for p in report['primitives']):raise ValueError('Expected exported UV coordinates')
        if skinned:
            from .skin_glb import check_recorded_samples
            check_recorded_samples(skin,level['playback'])
            report['skin']=skin.report()
        files.append({'file':level['file'],**report})
    return {'valid':True,'levels':files,'chain':doc['chain'],'chain_sha256':doc['chain_sha256'],'note':'Binary attributes/dependencies and declared budgets checked; no target-engine switching, rendered silhouette or material appearance certification.'}
