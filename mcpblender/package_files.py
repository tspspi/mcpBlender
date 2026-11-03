"""Independent static scene/dependency and multi-asset package validation (stdlib)."""
import hashlib
import struct
import zlib
import json
import math
from pathlib import Path
import re
from types import SimpleNamespace

from .lod_files import read_glb,file_hash,validate as validate_lods
from .skin_glb import Accessor,IDENTITY,matrix,multiply,point,trs

MARKER='mcpblender-asset-package-v1'
SLUG=re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,47}$')
DIGEST=re.compile(r'^[0-9a-f]{64}$')


def index(value,items,label):
    if type(value)!=int or not 0<=value<len(items):raise ValueError('Invalid '+label+' index')
    return items[value]


def finite(values,count,label):
    if not isinstance(values,(list,tuple)) or len(values)!=count or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('Invalid finite '+label)
    return values


def texture_infos(material):
    if isinstance(material,dict):
        for key,value in material.items():
            if key.endswith('Texture') and isinstance(value,dict) and 'index' in value:yield value
            else:yield from texture_infos(value)
    elif isinstance(material,list):
        for value in material:yield from texture_infos(value)



def triangle_hash(triangle):
    points=[tuple(0. if v==0 else v for v in p) for p in triangle]
    # Preserve winding but ignore the starting corner and primitive ordering.
    rotations=[points[i:]+points[:i] for i in range(3)]
    values=min(rotations)
    return hashlib.sha256(struct.pack('<9f',*(v for p in values for v in p))).digest()


def surface_digest(hashes):
    result=hashlib.sha256()
    for value in sorted(hashes):result.update(value)
    return result.hexdigest()


def image_info(payload,mime):
    if mime=='image/png':
        if not payload.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Invalid PNG signature')
        position=8;compressed=bytearray();header=None;palette=False;ended=False
        while position<len(payload):
            if position+12>len(payload):raise ValueError('Truncated PNG chunk')
            size=struct.unpack_from('>I',payload,position)[0];kind=payload[position+4:position+8];start=position+8;end=start+size
            if end+4>len(payload) or zlib.crc32(payload[position+4:end])!=struct.unpack_from('>I',payload,end)[0]:raise ValueError('PNG chunk bounds/CRC failure')
            data=payload[start:end];position=end+4
            if header is None and kind!=b'IHDR':raise ValueError('PNG header must be first')
            if kind==b'IHDR':
                if header is not None or size!=13:raise ValueError('Invalid PNG header')
                width,height,depth,color,compression,filter_method,interlace=struct.unpack('>IIBBBBB',data)
                allowed={0:{1,2,4,8,16},2:{8,16},3:{1,2,4,8},4:{8,16},6:{8,16}}
                if not 1<=width<=16384 or not 1<=height<=16384 or width*height>64*1024**2 or depth not in allowed.get(color,set()) or compression or filter_method or interlace:raise ValueError('PNG dimensions/encoding outside package profile (non-interlaced only)')
                header=(width,height,depth,color)
            elif kind==b'PLTE':
                if not size or size%3 or size>768:raise ValueError('Invalid PNG palette')
                palette=True
            elif kind==b'IDAT':compressed.extend(data)
            elif kind==b'IEND':
                if size or position!=len(payload):raise ValueError('Invalid PNG end')
                ended=True;break
            elif kind[:1].isupper():raise ValueError('Unsupported critical PNG chunk')
        if not header or not ended or not compressed:raise ValueError('Incomplete PNG')
        width,height,depth,color=header
        if color==3 and not palette:raise ValueError('Indexed PNG missing palette')
        row=(width*{0:1,2:3,3:1,4:2,6:4}[color]*depth+7)//8+1;expected=row*height
        if expected>512*1024**2:raise ValueError('PNG decoded pixels exceed package limit')
        decoder=zlib.decompressobj();pixels=decoder.decompress(compressed,expected+1)
        if len(pixels)!=expected or not decoder.eof or decoder.unused_data or any(pixels[y*row]>4 for y in range(height)):raise ValueError('Invalid PNG pixel stream/filter')
        return {'mime_type':mime,'bytes':len(payload),'width':width,'height':height,'validation':'PNG chunks/CRC and decompressed scanline layout'}
    if mime=='image/jpeg':
        if not payload.startswith(b'\xff\xd8'):raise ValueError('Invalid JPEG signature')
        position=2;dimensions=None;scan=False
        while position<len(payload):
            if payload[position]!=255:raise ValueError('Invalid JPEG marker')
            while position<len(payload) and payload[position]==255:position+=1
            if position>=len(payload):raise ValueError('Truncated JPEG marker')
            kind=payload[position];position+=1
            if kind==217:
                if not dimensions or not scan or position!=len(payload):raise ValueError('Incomplete JPEG')
                return {'mime_type':mime,'bytes':len(payload),'width':dimensions[0],'height':dimensions[1],'validation':'JPEG marker/segment structure; entropy not decoded'}
            if kind in {0,216} or 208<=kind<=215:raise ValueError('Unexpected JPEG marker')
            if position+2>len(payload):raise ValueError('Truncated JPEG segment')
            size=struct.unpack_from('>H',payload,position)[0]
            if size<2 or position+size>len(payload):raise ValueError('JPEG segment outside image')
            if kind in {192,193,194}:
                if size<8:raise ValueError('Truncated JPEG frame')
                height,width=struct.unpack_from('>HH',payload,position+3)
                if not 1<=width<=16384 or not 1<=height<=16384 or width*height>64*1024**2:raise ValueError('JPEG dimensions outside limits')
                dimensions=(width,height)
            position+=size
            if kind==218:
                scan=True
                while position<len(payload):
                    if payload[position]!=255:position+=1;continue
                    if position+1>=len(payload):raise ValueError('Truncated JPEG scan')
                    if payload[position+1]==0 or 208<=payload[position+1]<=215:position+=2;continue
                    break
        raise ValueError('JPEG missing end marker')
    raise ValueError('Package texture profile supports PNG and JPEG only')

def inspect_static_glb(path,check_cancelled=lambda:None,expected_scene_unit_scale=None):
    try:return _inspect_static_glb(path,check_cancelled,expected_scene_unit_scale)
    except (KeyError,TypeError,IndexError,OverflowError,AttributeError,zlib.error) as exc:raise ValueError('Malformed static GLB scene/dependencies: '+str(exc)) from exc




def finite_json(document):
    pending=[(document,0)];count=0
    while pending:
        value,depth=pending.pop();count+=1
        if count>1000000 or depth>128:raise ValueError('JSON structure exceeds package limits')
        if isinstance(value,float) and not math.isfinite(value):raise ValueError('Nonfinite JSON value')
        if isinstance(value,dict):pending.extend((v,depth+1) for v in value.values())
        elif isinstance(value,list):pending.extend((v,depth+1) for v in value)

def embedded_dependencies(doc,binary):
    finite_json(doc)
    length=doc['buffers'][0]['byteLength']
    if type(length)!=int or not 0<=len(binary)-length<=3:raise ValueError('Invalid embedded buffer length')
    views=doc.get('bufferViews',[])
    for view in views:
        start=view.get('byteOffset',0);size=view['byteLength']
        if type(start)!=int or type(size)!=int or min(start,size)<0 or start+size>length or view.get('buffer',0)!=0:raise ValueError('Invalid embedded buffer view')
    images=doc.get('images',[]);image_records=[]
    for image in images:
        view=index(image['bufferView'],views,'image view');start=view.get('byteOffset',0);payload=binary[start:start+view['byteLength']];mime=image.get('mimeType')
        image_records.append(image_info(payload,mime))
    textures=doc.get('textures',[]);materials=doc.get('materials',[])
    for texture in textures:
        sources=[texture['source']] if 'source' in texture else []
        sources.extend(v['source'] for k,v in texture.get('extensions',{}).items() if k=='EXT_texture_webp')
        if not sources:raise ValueError('Texture has no embedded image source')
        for source in sources:index(source,images,'texture image')
        if 'sampler' in texture:index(texture['sampler'],doc.get('samplers',[]),'texture sampler')
    for material in materials:
        for info in texture_infos(material):index(info['index'],textures,'material texture')
    for mesh in doc.get('meshes',[]):
        for primitive in mesh.get('primitives',[]):
            if 'material' not in primitive:continue
            material=index(primitive['material'],materials,'primitive material')
            for info in texture_infos(material):
                coordinate=info.get('extensions',{}).get('KHR_texture_transform',{}).get('texCoord',info.get('texCoord',0))
                if type(coordinate)!=int or coordinate<0 or f'TEXCOORD_{coordinate}' not in primitive.get('attributes',{}):raise ValueError('Material texture references missing UV set')
    return image_records

def _inspect_static_glb(path,check_cancelled,expected_scene_unit_scale):
    doc,binary=read_glb(path)
    from .gltf_units import validate_document
    unit_scale=validate_document(doc,expected_scene_unit_scale)
    if doc.get('asset',{}).get('version')!='2.0' or doc.get('skins') or doc.get('animations'):raise ValueError('Static GLB 2.0 scene required')
    permitted={'KHR_texture_transform','KHR_materials_clearcoat','KHR_materials_transmission','KHR_materials_volume',
               'KHR_materials_ior','KHR_materials_specular','KHR_materials_sheen','KHR_materials_emissive_strength',
               'KHR_materials_anisotropy','KHR_materials_unlit'}
    if set(doc.get('extensionsUsed',[])) - permitted or set(doc.get('extensionsRequired',[]))-permitted:
        raise ValueError('Unsupported GLB extension in package profile')
    document=SimpleNamespace(doc=doc,binary=binary,allow_sparse=False,check_cancelled=check_cancelled)
    image_records=embedded_dependencies(doc,binary)
    materials=doc.get('materials',[]);images=doc.get('images',[]);textures=doc.get('textures',[])
    meshes=doc.get('meshes',[]);mesh_records=[]
    if not 1<=len(meshes)<=2048:raise ValueError('GLB mesh count outside package limits')
    for mesh in meshes:
        primitives=[]
        for primitive in mesh['primitives']:
            check_cancelled()
            if primitive.get('mode',4)!=4 or primitive.get('targets') or primitive.get('extensions'):raise ValueError('Static uncompressed triangles required')
            attrs=primitive['attributes'];positions=Accessor(document,attrs['POSITION']);normals=Accessor(document,attrs['NORMAL'])
            if positions.type!='VEC3' or positions.kind!=5126 or normals.type!='VEC3' or normals.kind!=5126 or positions.count!=normals.count:raise ValueError('Invalid static positions/normals')
            points=[positions.row(i) for i in range(positions.count)]
            for i in range(normals.count):
                if i%32768==0:check_cancelled()
                if abs(sum(v*v for v in normals.row(i))-1)>.02:raise ValueError('GLB normals must be unit vectors')
            uv_sets=set()
            for key,value in attrs.items():
                if key.startswith('TEXCOORD_'):
                    uv=Accessor(document,value)
                    if uv.type!='VEC2' or uv.kind!=5126 or uv.count!=positions.count:raise ValueError('Invalid static UV attribute')
                    for i in range(uv.count):uv.row(i)
                    uv_sets.add(key)
            if 'indices' in primitive:
                indices=Accessor(document,primitive['indices'])
                if indices.type!='SCALAR' or indices.kind not in {5121,5123,5125}:raise ValueError('Invalid triangle indices')
                used=[indices.row(i)[0] for i in range(indices.count)]
            else:used=list(range(positions.count))
            if not used or len(used)%3 or any(v<0 or v>=positions.count for v in used):raise ValueError('Invalid static triangle references')
            if 'material' in primitive:
                material=index(primitive['material'],materials,'primitive material')
                for info in texture_infos(material):
                    coordinate=info.get('extensions',{}).get('KHR_texture_transform',{}).get('texCoord',info.get('texCoord',0))
                    if type(coordinate)!=int or coordinate<0 or f'TEXCOORD_{coordinate}' not in uv_sets:raise ValueError('Material texture references missing UV set')
            primitives.append({'points':points,'indices':used,'triangles':len(used)//3,'uv_sets':sorted(uv_sets)})
        if not primitives:raise ValueError('GLB mesh has no triangle primitives')
        mesh_records.append(primitives)
    nodes=doc.get('nodes',[]);scenes=doc.get('scenes',[])
    if not 1<=len(nodes)<=4096 or len(scenes)!=1 or doc.get('scene',0)!=0:raise ValueError('Package GLB requires one bounded scene')
    parents={};local=[]
    for i,node in enumerate(nodes):
        if 'skin' in node or 'camera' in node or node.get('extensions'):raise ValueError('Static mesh hierarchy required')
        if 'matrix' in node:
            if any(k in node for k in ('translation','rotation','scale')):raise ValueError('Matrix and TRS cannot mix')
            value=matrix(finite(node['matrix'],16,'node matrix'))
            if any(abs(value[3][j]-(1 if j==3 else 0))>1e-8 for j in range(4)):raise ValueError('Affine node matrix required')
        else:value=trs(finite(node.get('translation',[0,0,0]),3,'translation'),finite(node.get('rotation',[0,0,0,1]),4,'rotation'),finite(node.get('scale',[1,1,1]),3,'scale'))
        local.append(value)
        for child in node.get('children',[]):
            index(child,nodes,'child node')
            if child in parents:raise ValueError('Node has multiple parents')
            parents[child]=i
    roots=scenes[0].get('nodes',[])
    if len(set(roots))!=len(roots):raise ValueError('Duplicate scene roots')
    visited=set();used_meshes=set();world_points=[];triangles=0;instances=0;surface_hashes=[];node_records=[]
    def walk(i,parent,depth):
        nonlocal triangles,instances
        node=index(i,nodes,'scene node')
        if depth>64 or i in visited:raise ValueError('Scene node cycle or excessive depth')
        if depth==0 and i in parents:raise ValueError('Scene root is also a child')
        visited.add(i);world=multiply(parent,local[i])
        if 'mesh' in node:
            index(node['mesh'],meshes,'node mesh');used_meshes.add(node['mesh']);instances+=1
            first_point=len(world_points);first_hash=len(surface_hashes);first_triangle=triangles
            for primitive in mesh_records[node['mesh']]:
                triangles+=primitive['triangles']
                if triangles>4000000:raise ValueError('Package scene exceeds four million triangles')
                transformed=[point(world,p) for p in primitive['points']]
                used=primitive['indices'];world_points.extend(transformed[i] for i in set(used))
                for offset in range(0,len(used),3):
                    if offset%24576==0:check_cancelled()
                    surface_hashes.append(triangle_hash([transformed[used[offset+j]] for j in range(3)]))
            node_points=world_points[first_point:]
            node_records.append({'name':node.get('name',f'node_{i}'),'triangles':triangles-first_triangle,
                                 'surface_sha256':surface_digest(surface_hashes[first_hash:]),
                                 'world_bounds':{key:[fn(p[a] for p in node_points) for a in range(3)] for key,fn in (('min',min),('max',max))}})
        for child in node.get('children',[]):walk(child,world,depth+1)
    for root in roots:walk(root,IDENTITY,0)
    if len(visited)!=len(nodes) or len(used_meshes)!=len(meshes) or not world_points:raise ValueError('GLB contains unreachable/unused nodes or meshes')
    if any(not math.isfinite(v) for p in world_points for v in p):raise ValueError('Nonfinite transformed positions')
    bounds={key:[fn(p[a] for p in world_points) for a in range(3)] for key,fn in (('min',min),('max',max))}
    return ({'scene_unit_scale':unit_scale,'world_units':'METRES'} if unit_scale!=1 else {})|{'surface_sha256':surface_digest(surface_hashes),'triangles':triangles,'mesh_instances':instances,'meshes':len(meshes),'nodes':len(nodes),
            'world_bounds':bounds,'mesh_nodes':node_records,'materials':len(materials),'images':len(images),'textures':len(textures),
            'embedded_dependencies':True,'image_records':image_records}


def safe_file(root,relative):
    if not isinstance(relative,str) or not relative or relative.startswith('/') or any(p in {'','..','.'} for p in relative.split('/')) or '\\' in relative:raise ValueError('Unsafe package member path')
    path=root
    for part in relative.split('/'):
        path=path/part
        if path.is_symlink():raise ValueError('Symlink package member refused')
    if not path.is_file() or path.stat().st_size>512*1024**2:raise ValueError('Missing/oversized package member')
    return path


def validate(directory,check_cancelled=lambda:None):
    try:return _validate(Path(directory),check_cancelled)
    except (KeyError,TypeError,IndexError,AttributeError) as exc:raise ValueError('Malformed asset package: '+str(exc)) from exc


def _validate(root,check_cancelled):
    if root.is_symlink():raise ValueError('Symlink package root refused')
    manifest=safe_file(root,'manifest.json')
    if manifest.stat().st_size>8*1024**2:raise ValueError('Oversized package manifest')
    doc=json.loads(manifest.read_text());finite_json(doc)
    if doc.get('format')!=MARKER or not isinstance(doc.get('assets'),list) or not 1<=len(doc['assets'])<=32:raise ValueError('Invalid asset package manifest')
    if not DIGEST.fullmatch(doc.get('source_sha256','')):raise ValueError('Invalid package source guard')
    declared={'manifest.json'};ids=set();reports=[]
    for asset in doc['assets']:
        if not SLUG.fullmatch(asset['id']) or asset['id'].casefold() in ids:raise ValueError('Invalid/duplicate package asset ID')
        ids.add(asset['id'].casefold());members=asset['members'];roles=[m['role'] for m in members]
        if not 1<=len(members)<=17 or roles.count('PRIMARY')!=1 or roles.count('COLLISION')>8 or roles.count('SHADOW')>8 or any(r not in {'PRIMARY','COLLISION','SHADOW'} for r in roles):raise ValueError('Invalid asset member roles')
        for member in members:
            check_cancelled();relative=member['file'];path=safe_file(root,relative)
            if not relative.startswith(asset['id']+'/') or not relative.endswith('.glb') or relative in declared:raise ValueError('Invalid/duplicate asset member')
            declared.add(relative)
            if not DIGEST.fullmatch(member['sha256']) or file_hash(path)!=member['sha256']:raise ValueError('Package member hash mismatch')
            report=inspect_static_glb(path,check_cancelled,expected_scene_unit_scale=doc.get('scene_unit_scale',1))
            if report!=member['scene']:raise ValueError('Package scene/dependency proof differs')
            proof=member['native']
            if proof.get('surface_sha256')!=report['surface_sha256'] or type(proof['triangles'])!=int or proof['triangles']!=report['triangles'] or proof['mesh_instances']!=report['mesh_instances']:raise ValueError('Native/file geometry count differs')
            for key in ('min','max'):
                expected=finite(proof['gltf_world_bounds'][key],3,'native bounds')
                if any(abs(a-b)>1e-5+abs(b)*1e-7 for a,b in zip(report['world_bounds'][key],expected)):raise ValueError('Native/file world bounds differ')
            if member['role']!='PRIMARY':
                if member.get('for_asset')!=asset['id'] or not DIGEST.fullmatch(member.get('proxy_sha256','')) or not member.get('source_objects') or not set(member['source_objects'])<=set(asset['objects']):raise ValueError('Invalid proxy association')
            if member['role']!='PRIMARY':
                mapping=member.get('proxy_nodes',[]);nodes={n['name']:n for n in report['mesh_nodes']}
                method=member.get('proxy_method')
                if method not in ({'BOX','CONVEX_HULL'} if member['role']=='COLLISION' else {'DECIMATE'}):raise ValueError('Proxy method differs from role')
                if not mapping or len(mapping)!=len(nodes) or {n['node'] for n in mapping}!=set(nodes):raise ValueError('Proxy node association differs')
                for entry in mapping:
                    node=nodes[entry['node']];proof=entry['native']
                    if proof['surface_sha256']!=node['surface_sha256'] or proof['triangles']!=node['triangles']:raise ValueError('Proxy node geometry proof differs')
                    if member['role']=='COLLISION' and entry.get('suggested_collision_shape')!=method:raise ValueError('Collision shape association differs')
            reports.append({'asset':asset['id'],'role':member['role'],'file':relative,'scene':report})
        if len(asset.get('lods',[]))>4:raise ValueError('Too many associated LOD bundles')
        for entry in asset.get('lods',[]):
            relative=entry['directory']
            if not isinstance(relative,str) or not relative.startswith(asset['id']+'/') or not SLUG.fullmatch(relative.split('/')[-1]) or len(relative.split('/'))!=2:raise ValueError('Unsafe LOD association directory')
            lod_manifest=safe_file(root,relative+'/manifest.json');validate_lods(root/relative)
            lod_doc=json.loads(lod_manifest.read_text())
            if lod_doc.get('scene_unit_scale',1)!=doc.get('scene_unit_scale',1):raise ValueError('Associated LOD scene unit scale differs from package')
            if any(lod_doc.get(k)!=entry.get(k) for k in ('chain','chain_sha256','source_sha256','animation_sha256')):raise ValueError('LOD association guards differ')
            for file in (root/relative).iterdir():
                member_relative=relative+'/'+file.name;path=safe_file(root,member_relative)
                if member_relative in declared or entry['files'].get(file.name)!=file_hash(path):raise ValueError('LOD dependency hash/inventory differs')
                if path.suffix.lower()=='.glb':
                    lod_document,lod_binary=read_glb(path);embedded_dependencies(lod_document,lod_binary)
                declared.add(member_relative)
            if set(entry['files'])!={f.name for f in (root/relative).iterdir()}:raise ValueError('LOD file inventory differs')
    actual=set()
    for file in root.rglob('*'):
        if file.is_symlink():raise ValueError('Symlink package content refused')
        if file.is_file():actual.add(file.relative_to(root).as_posix())
        if len(actual)>2048:raise ValueError('Package exceeds 2048 files')
    if actual!=declared:raise ValueError('Package has missing or undeclared files')
    return {'valid':True,'format':MARKER,'assets':len(ids),'members':reports,'files':sorted(declared),'source_sha256':doc['source_sha256']}
