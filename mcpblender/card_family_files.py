"""Independent bounded portable card-family validation and selector coordinates."""
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
from . import attribute_glb,botany,card_family,lod_files,card_views
from .skin_glb import Accessor,point,IDENTITY,multiply,matrix,trs
from .package_files import image_info

LEGACY_FORMAT='mcpblender-card-family-bundle-v1'
FORMAT='mcpblender-card-family-bundle-v2'
VIEW_FIELD='_MCP_CARD_VIEW'
COORDINATES='GLTF_WORLD_Y_UP_METRES'


def gltf(v):return [v[0],v[2],-v[1]]


def placement(matrix,unit):
    if type(unit) not in (float,int) or not math.isfinite(unit) or unit<=0 or len(matrix)!=4 or any(len(row)!=4 or any(type(v) not in (int,float) or not math.isfinite(v) for v in row) for row in matrix):raise ValueError('Invalid family native placement')
    if matrix[3]!=[0,0,0,1]:raise ValueError('Affine family placement required')
    axes=[[matrix[r][c] for r in range(3)] for c in range(3)]
    lengths=[math.sqrt(sum(v*v for v in axis)) for axis in axes]
    determinant=sum(axes[0][i]*(axes[1][(i+1)%3]*axes[2][(i+2)%3]-axes[1][(i+2)%3]*axes[2][(i+1)%3]) for i in range(3))
    if determinant<=1e-12 or max(lengths)-min(lengths)>max(lengths)*1e-6 or any(abs(sum(x*y for x,y in zip(axes[a],axes[b])))/(lengths[a]*lengths[b])>1e-6 for a,b in ((0,1),(0,2),(1,2))):raise ValueError('Positive uniform family placement without shear required')
    normals={view:gltf(card_family.unit([sum(matrix[r][c]*n[c] for c in range(3)) for r in range(3)])) for view,n in card_family.DIRECTIONS.items()}
    origin=gltf([matrix[r][3]*unit for r in range(3)])
    if any(not math.isfinite(v) for v in origin):raise ValueError('Finite metre-space family origin required')
    return {'origin_world_m':origin,'normals_world':normals}


def inventory(root,cancelled=lambda:None):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('Family bundle requires a regular local directory')
    rows=[];total=0;allowed={'manifest.json','asset.blend',*(v.lower()+'.glb' for v in card_views.DIRECTIONS)}
    for path in root.iterdir():
        cancelled()
        if path.name not in allowed or path.is_symlink() or not path.is_file():raise ValueError('Unknown/nonregular family bundle member')
        size=path.stat().st_size;total+=size
        if total>512*1024**2:raise ValueError('Family bundle exceeds 512 MiB')
        if path.name=='manifest.json':continue
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024**2),b''):cancelled();digest.update(block)
        rows.append({'path':path.name,'bytes':size,'sha256':digest.hexdigest()})
    return sorted(rows,key=lambda r:r['path'])


def verify_variant(path,witness,*,cancelled=lambda:None):
    count=len(witness.get('positions',[]));normals=witness.get('normals',[])
    if not count<=32768 or len(normals)!=count or any(len(n)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in n) or abs(sum(v*v for v in n)-1)>.02 for n in normals):raise ValueError('Bounded unit corner-normal witness required')
    proof=attribute_glb.verify(path,witness,cancelled=cancelled)
    doc,binary=lod_files.read_glb(path);document=SimpleNamespace(doc=doc,binary=binary,allow_sparse=False,check_cancelled=cancelled)
    checked=0
    for primitive in doc['meshes'][0]['primitives']:
        attrs=primitive['attributes']
        if 'NORMAL' not in attrs:raise ValueError('Family GLB dropped shading normals')
        ids=Accessor(document,attrs[attribute_glb.CORNER]);encoded=Accessor(document,attrs['NORMAL'])
        if encoded.kind!=5126 or encoded.type!='VEC3' or encoded.count!=ids.count:raise ValueError('Invalid family normal accessor')
        for i in range(ids.count):
            if i%256==0:cancelled()
            index=int(ids.row(i)[0])
            if not attribute_glb.close(encoded.row(i),gltf(normals[index]),2e-5):raise ValueError('Decoded shading normal differs from family corner')
            checked+=1
    nodes=doc['nodes'];origins=[i for i,n in enumerate(nodes) if n.get('name')==witness['origin_node'] and 'mesh' not in n]
    if len(origins)!=1:raise ValueError('Unique encoded family origin required')
    parents={child:i for i,n in enumerate(nodes) for child in n.get('children',[])}
    current=next(i for i,n in enumerate(nodes) if 'mesh' in n);chain=[]
    while True:
        chain.append(current)
        if current not in parents:break
        current=parents[current]
    if origins[0] not in chain:raise ValueError('Family origin must parent the encoded alternative')
    world=IDENTITY
    for index in reversed(chain[chain.index(origins[0]):]):
        n=nodes[index];local=matrix(n['matrix']) if 'matrix' in n else trs(n.get('translation',[0,0,0]),n.get('rotation',[0,0,0,1]),n.get('scale',[1,1,1]))
        world=multiply(world,local)
    for p in ((0,0,0),(1,0,0),(0,1,0),(0,0,1)):
        expected=gltf([v*witness['scene_unit_scale'] for v in point(witness['root_matrix_native'],p)])
        if not attribute_glb.close(point(world,gltf(p)),expected,2e-6):raise ValueError('Encoded family origin differs from selector placement')
    if len(doc.get('materials',[]))!=1:raise ValueError('One family material required per alternative')
    mat=doc['materials'][0];pbr=mat.get('pbrMetallicRoughness',{})
    required={'BASE_COLOR':pbr.get('baseColorTexture'),'NORMAL':mat.get('normalTexture'),'ROUGHNESS':pbr.get('metallicRoughnessTexture'),'METALLIC':pbr.get('metallicRoughnessTexture'),'AO':mat.get('occlusionTexture'),'EMISSION':mat.get('emissiveTexture')}
    maps=witness['required_maps']
    if not {'BASE_COLOR','ALPHA'}<=set(maps) or len(set(maps))!=len(maps):raise ValueError('Invalid family map witness')
    bindings={}
    for name in maps:
        if name=='ALPHA':
            if mat.get('alphaMode','OPAQUE') not in {'MASK','BLEND'}:raise ValueError('Family GLB lost alpha semantics')
            continue
        texture=required.get(name)
        if not isinstance(texture,dict) or texture.get('texCoord',0)!=0:raise ValueError('Family GLB dropped PBR map or changed UV binding: '+name)
        index=texture.get('index');textures=doc.get('textures',[])
        if type(index)!=int or not 0<=index<len(textures):raise ValueError('Invalid family PBR texture index')
        image=textures[index].get('source')
        if type(image)!=int or not 0<=image<len(doc.get('images',[])):raise ValueError('Invalid family PBR image index')
        bindings[name]=image
    images=[]
    for image in doc.get('images',[]):
        cancelled();view=doc['bufferViews'][image['bufferView']];start=view.get('byteOffset',0);size=view['byteLength'];payload=binary[start:start+size]
        info=image_info(payload,image.get('mimeType',''))
        images.append({'sha256':hashlib.sha256(payload).hexdigest(),'bytes':size,'width':info['width'],'height':info['height'],'mime_type':image.get('mimeType')})
    return {'geometry':proof,'checked_normal_rows':checked,'map_bindings':bindings,'alpha_mode':mat.get('alphaMode','OPAQUE'),'images':images}


def bounds(rows,unit):
    points=[gltf([v*unit for v in point(row['matrix_world'],p)]) for row in rows for p in row['positions']]
    return {k:[fn(v[a] for v in points) for a in range(3)] for k,fn in (('min',min),('max',max))}


def validate(directory,*,cancelled=lambda:None,progress=lambda v:None):
    root=Path(directory);listed=inventory(root,cancelled);manifest=root/'manifest.json'
    if not manifest.is_file() or manifest.stat().st_size>16*1024**2:raise ValueError('Missing/oversized family manifest')
    data=json.loads(manifest.read_text())
    if data.get('format') not in {FORMAT,LEGACY_FORMAT} or data.get('files')!=listed:raise ValueError('Family file inventory/hash mismatch')
    rows=data.get('variants',[]);catalog=card_views.LEGACY if data['format']==LEGACY_FORMAT else tuple(card_views.DIRECTIONS)
    if not isinstance(rows,list) or not 1<=len(rows)<=len(catalog) or [r.get('view') for r in rows]!=[v for v in catalog if any(r.get('view')==v for r in rows)]:raise ValueError('Canonical unique family view order required')
    expected={'asset.blend',*(row['view'].lower()+'.glb' for row in rows)}
    if {r['path'] for r in listed}!=expected:raise ValueError('Family member inventory differs from alternatives')
    unit=data['scene_unit_scale'];pose=placement(data['root_matrix_native'],unit)
    pose['normals_world']={row['view']:pose['normals_world'][row['view']] for row in rows}
    if not isinstance(data.get('family_guard'),str) or len(data['family_guard'])!=64 or any(c not in '0123456789abcdef' for c in data['family_guard']):raise ValueError('Invalid source family guard')
    selector={'method':'NEAREST_ONE_SIDED_CARD_V1','coordinates':COORDINATES,'tie_order':list(catalog),'max_angle_degrees':data['max_angle_degrees'],'perspective':'NEAREST_CENTRE_THEN_ALL_EIGHT_WORLD_AABB_CORNERS','automatic_playback':False,**pose}
    if data.get('selector')!=selector or data.get('optical_equivalence') is not False:raise ValueError('Family selector/optical metadata differs from declared contract')
    # Exercise policy admission even when there are no consumer camera samples.
    card_family.choose({r['view']:pose['normals_world'][r['view']] for r in rows},[pose['normals_world'][rows[0]['view']]],data['max_angle_degrees'])
    proofs=[]
    for row in rows:
        cancelled();view=row['view'];witness=row['witness'];index=list(card_family.DIRECTIONS).index(view)
        if row.get('file')!=view.lower()+'.glb' or witness.get('scene_unit_scale')!=unit or witness.get('root_matrix_native')!=data['root_matrix_native'] or witness.get('required_maps')!=[m['map'] for m in data['provenance']['maps']]:raise ValueError('Family alternative path/units changed')
        fields=witness.get('fields',[])
        if fields!=[{'semantic':VIEW_FIELD,'components':1,'values':[[float(index)]]*len(witness['positions'])}]:raise ValueError('Family view identity field differs from alternative')
        expected_normal=pose['normals_world'][view];checked_faces=0
        for triangle in witness['triangles']:
            points=[gltf(point(witness['matrix_world'],witness['positions'][i])) for i in triangle]
            a=[points[1][i]-points[0][i] for i in range(3)];b=[points[2][i]-points[0][i] for i in range(3)]
            normal=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
            if max(abs(v) for v in normal)<1e-20:continue
            if sum(x*y for x,y in zip(card_family.unit(normal),expected_normal))<math.cos(math.radians(.1)):raise ValueError('Family view direction differs from encoded face orientation: '+view)
            checked_faces+=1
        if not checked_faces:raise ValueError('Family alternative has no nondegenerate faces')
        proof=verify_variant(root/row['file'],witness,cancelled=cancelled)
        if proof!=row.get('proof') or proof['geometry']['triangles']!=row.get('triangles'):raise ValueError('Family binary proof/count mismatch')
        proofs.append({'view':view,'proof':proof});progress({'phase':'validated portable card alternative','view':view,'completed':len(proofs),'total':len(rows)})
    physical=bounds([r['witness'] for r in rows],unit)
    if data.get('bounds_world_m')!=physical:raise ValueError('Family world bounds differ from decoded correspondence witness')
    return {'valid':True,'format':data['format'],'variants':proofs,'family_guard':data['family_guard'],'selector':selector,'bounds_world_m':physical,
            'scope':'File inventory/hashes; decoded static local geometry, oriented triangles, corner normals, UVs and metre placement; embedded PBR binding/image headers; selection metadata. Editable blend hash only. No native blend reopen, texture pixel equivalence, angular quality or engine playback proof.'}
