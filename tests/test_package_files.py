"""Known-answer scene transforms, dependencies, surface proofs and package guards."""
import copy
import json
import struct
import pytest
from mcpblender.package_files import inspect_static_glb,validate,MARKER
from mcpblender.lod_files import file_hash


def fixture(path,patch=None):
    blob=struct.pack('<18f',0,0,0,1,0,0,0,1,0,*([0,0,1]*3))
    doc={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(blob)}],
         'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':36},{'buffer':0,'byteOffset':36,'byteLength':36}],
         'accessors':[{'bufferView':0,'count':3,'type':'VEC3','componentType':5126},{'bufferView':1,'count':3,'type':'VEC3','componentType':5126}],
         'meshes':[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1}}]}],
         'nodes':[{'translation':[2,0,0],'children':[1]},{'mesh':0,'scale':[2,3,1]}],'scenes':[{'nodes':[0]}],'scene':0}
    if patch:patch(doc)
    encoded=json.dumps(doc).encode();encoded+=b' '*((-len(encoded))%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(blob))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(blob),b'BIN\0')+blob)


def manifest(root):
    (root/'prop').mkdir();member=root/'prop/primary.glb';fixture(member);scene=inspect_static_glb(member)
    native={'triangles':1,'mesh_instances':1,'gltf_world_bounds':scene['world_bounds'],'surface_sha256':scene['surface_sha256']}
    document={'format':MARKER,'source_sha256':'a'*64,'assets':[{'id':'prop','members':[{'role':'PRIMARY','file':'prop/primary.glb','sha256':file_hash(member),'scene':scene,'native':native}],'lods':[]}]}
    (root/'manifest.json').write_text(json.dumps(document));return document


def test_known_hierarchy_and_surface(tmp_path):
    path=tmp_path/'scene.glb';fixture(path);report=inspect_static_glb(path)
    assert report['triangles']==1 and report['mesh_instances']==1 and report['nodes']==2
    assert report['world_bounds']=={'min':[2,0,0],'max':[4,3,0]}
    first=report['surface_sha256'];fixture(path,lambda d:d['nodes'][1].update(scale=[3,3,1]))
    assert inspect_static_glb(path)['surface_sha256']!=first


@pytest.mark.parametrize('patch',[
    lambda d:d['nodes'][1].update(children=[0]),
    lambda d:d['nodes'][0].update(children=[1,1]),
    lambda d:d['nodes'][1].update(mesh=4),
    lambda d:d['nodes'].append({}),
    lambda d:d.update(extensionsUsed=['EXT_mesh_gpu_instancing']),
    lambda d:d['nodes'][1].update(translation=[float('nan'),0,0]),
    lambda d:d['nodes'][1].update(rotation=[0,0,0,2]),
    lambda d:d.update(textures=[{'source':0}]),
    lambda d:d.update(materials=[{'pbrMetallicRoughness':{'baseColorTexture':{'index':0}}}]),
    lambda d:d.update(images=[{'uri':'outside.png'}]),
    lambda d:d['bufferViews'][0].update(byteOffset=-1),
    lambda d:d['accessors'][0].update(count=99999),
    lambda d:d['meshes'][0]['primitives'][0].update(material=0),
])
def test_bad_scene_references_and_dependencies_refused(tmp_path,patch):
    path=tmp_path/'bad.glb';fixture(path,patch)
    with pytest.raises(ValueError):inspect_static_glb(path)


def test_inventory_hash_and_native_proof(tmp_path):
    document=manifest(tmp_path);assert validate(tmp_path)['valid']
    member=document['assets'][0]['members'][0];saved=copy.deepcopy(document)
    for patch in ({'file':'../escape.glb'},{'sha256':'0'*64},{'native':member['native']|{'surface_sha256':'0'*64}},{'native':member['native']|{'gltf_world_bounds':{'min':[0,0,0],'max':[4,3,0]}}}):
        document=copy.deepcopy(saved);document['assets'][0]['members'][0].update(patch);(tmp_path/'manifest.json').write_text(json.dumps(document))
        with pytest.raises(ValueError):validate(tmp_path)
    (tmp_path/'manifest.json').write_text(json.dumps(saved));(tmp_path/'unexpected.txt').write_text('extra')
    with pytest.raises(ValueError,match='undeclared'):validate(tmp_path)
    (tmp_path/'unexpected.txt').unlink();(tmp_path/'link').symlink_to(tmp_path/'prop/primary.glb')
    with pytest.raises(ValueError,match='Symlink'):validate(tmp_path)


def test_embedded_png_and_texture_uv_dependencies(tmp_path):
    import zlib
    from mcpblender.package_files import image_info
    from mcpblender.lod_files import read_glb
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0\xff\0\0\xff'))+chunk(b'IEND',b'')
    assert image_info(png,'image/png')['width']==1
    with pytest.raises(ValueError):image_info(png[:8],'image/png')
    with pytest.raises(ValueError):image_info(png[:-1]+bytes([png[-1]^1]),'image/png')
    path=tmp_path/'texture.glb';fixture(path);doc,binary=read_glb(path);blob=bytearray(binary)
    offset=len(blob);blob.extend(struct.pack('<6f',0,0,1,0,0,1))
    doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':24});doc['accessors'].append({'bufferView':2,'count':3,'type':'VEC2','componentType':5126})
    offset=len(blob);blob.extend(png);doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(png)})
    doc.update(images=[{'bufferView':3,'mimeType':'image/png'}],textures=[{'source':0}],materials=[{'pbrMetallicRoughness':{'baseColorTexture':{'index':0}}}])
    primitive=doc['meshes'][0]['primitives'][0];primitive['attributes']['TEXCOORD_0']=2;primitive['material']=0
    doc['buffers'][0]['byteLength']=len(blob)
    while len(blob)%4:blob.append(0)
    def write():
        encoded=json.dumps(doc).encode();encoded+=b' '*((-len(encoded))%4)
        path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(blob))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(blob),b'BIN\0')+blob)
    write();assert inspect_static_glb(path)['images']==1
    doc['materials'][0]['pbrMetallicRoughness']['baseColorTexture']['texCoord']=2;write()
    with pytest.raises(ValueError,match='UV'):inspect_static_glb(path)
