"""Analytic decoded delivery correspondence, selector binding and journal recovery."""
import copy
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import pytest
from mcpblender import attribute_glb,card_family,card_family_files as api
from mcpblender.skin_glb import IDENTITY
from mcpblender.export_jobs import inspect,recover,job_root
from test_image_comparison import png


def fixture(root,patch=None):
    root=Path(root);root.mkdir(exist_ok=True)
    arrays=[('VEC3',[0,0,0,1,0,0,0,0,-1]),('VEC3',[0,1,0]*3),('VEC2',[0,1,1,1,0,0]),('SCALAR',[0,1,2]),('SCALAR',[0,0,0])]
    views=[];accessors=[];blob=bytearray()
    for kind,values in arrays:
        part=struct.pack('<'+str(len(values))+'f',*values);views.append({'buffer':0,'byteOffset':len(blob),'byteLength':len(part)});blob.extend(part)
        accessors.append({'bufferView':len(views)-1,'count':3,'type':kind,'componentType':5126})
    image=png(1,1,[60,150,20,128]);views.append({'buffer':0,'byteOffset':len(blob),'byteLength':len(image)});blob.extend(image);blob.extend(b'\0'*((-len(blob))%4))
    doc={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':accessors,
         'meshes':[{'primitives':[{'attributes':{'POSITION':0,'NORMAL':1,'TEXCOORD_0':2,attribute_glb.CORNER:3,api.VIEW_FIELD:4},'material':0}]}],
         'materials':[{'pbrMetallicRoughness':{'baseColorTexture':{'index':0}},'alphaMode':'BLEND','doubleSided':True}],
         'textures':[{'source':0}],'images':[{'bufferView':5,'mimeType':'image/png'}],
         'nodes':[{'name':'Origin','children':[1]},{'name':'Card','mesh':0}],'scenes':[{'nodes':[0]}],'scene':0}
    if patch:patch(doc,blob)
    encoded=json.dumps(doc).encode();encoded+=b' '*((-len(encoded))%4)
    (root/'top.glb').write_bytes(struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(blob))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(blob),b'BIN\0')+blob)
    witness={'format':attribute_glb.FORMAT,'matrix_world':[list(r) for r in IDENTITY],'scene_unit_scale':1,
             'positions':[[0,0,0],[1,0,0],[0,1,0]],'normals':[[0,0,1]]*3,'uvs':[[[0,0],[1,0],[0,1]]],'triangles':[[0,1,2]],
             'fields':[{'semantic':api.VIEW_FIELD,'components':1,'values':[[0.]]*3}],'required_maps':['BASE_COLOR','ALPHA'],'root_matrix_native':[list(r) for r in IDENTITY],'origin_node':'Origin'}
    return witness


def bundle(root):
    root=Path(root);witness=fixture(root);(root/'asset.blend').write_bytes(b'Hash-only editable-file fixture')
    pose=api.placement(witness['root_matrix_native'],1);pose['normals_world']={'TOP':pose['normals_world']['TOP']}
    result={'format':api.FORMAT,'family_guard':'a'*64,'scene_unit_scale':1,'root_matrix_native':witness['root_matrix_native'],'max_angle_degrees':30,
            'optical_equivalence':False,'provenance':{'maps':[{'map':m} for m in witness['required_maps']]},
            'selector':{'method':'NEAREST_ONE_SIDED_CARD_V1','coordinates':api.COORDINATES,'tie_order':list(card_family.DIRECTIONS),'max_angle_degrees':30,'perspective':'NEAREST_CENTRE_THEN_ALL_EIGHT_WORLD_AABB_CORNERS','automatic_playback':False,**pose},
            'variants':[{'view':'TOP','file':'top.glb','triangles':1,'witness':witness,'proof':api.verify_variant(root/'top.glb',witness)}],
            'bounds_world_m':api.bounds([witness],1),'files':api.inventory(root)}
    (root/'manifest.json').write_text(json.dumps(result));return result


def test_known_binary_family_bundle_and_manifest_consistency(tmp_path):
    saved=bundle(tmp_path);result=api.validate(tmp_path)
    assert result['valid'] and result['bounds_world_m']=={'min':[0,0,-1],'max':[1,0,0]}
    assert result['variants'][0]['proof']['checked_normal_rows']==3
    for mutate in (lambda d:d['selector']['normals_world'].update(TOP=[0,0,1]),lambda d:d.update(optical_equivalence=True),lambda d:d['variants'][0].update(view='SIDE'),lambda d:d.update(bounds_world_m={'min':[0,0,0],'max':[1,1,1]})):
        bad=copy.deepcopy(saved);mutate(bad);(tmp_path/'manifest.json').write_text(json.dumps(bad))
        with pytest.raises(ValueError):api.validate(tmp_path)
    (tmp_path/'manifest.json').write_text(json.dumps(saved));(tmp_path/'extra').write_text('keep')
    with pytest.raises(ValueError,match='Unknown'):api.validate(tmp_path)
    (tmp_path/'extra').unlink();(tmp_path/'side.glb').symlink_to(tmp_path/'top.glb')
    with pytest.raises(ValueError,match='nonregular'):api.validate(tmp_path)


@pytest.mark.parametrize('mutation,error',[
    (lambda d,b:struct.pack_into('<3f',b,36,0,-1,0),'normal'),
    (lambda d,b:struct.pack_into('<2f',b,72,.3,.7),'UV'),
    (lambda d,b:d['materials'][0]['pbrMetallicRoughness']['baseColorTexture'].update(texCoord=1),'UV binding'),
    (lambda d,b:d['materials'][0].update(alphaMode='OPAQUE'),'alpha'),
])
def test_tampered_binary_normals_uvs_and_pbr_binding(tmp_path,mutation,error):
    witness=fixture(tmp_path,mutation)
    with pytest.raises(ValueError,match=error):api.verify_variant(tmp_path/'top.glb',witness)


def test_selector_origin_checked_against_encoded_parent(tmp_path):
    witness=fixture(tmp_path,lambda d,b:d['nodes'][0].update(translation=[1,0,0]))
    witness['matrix_world'][0][3]=1 # Keep mesh placement correspondence valid.
    with pytest.raises(ValueError,match='origin differs'):api.verify_variant(tmp_path/'top.glb',witness)
    for matrix in ([[1,0,0,0],[0,2,0,0],[0,0,1,0],[0,0,0,1]],[[1,0,0,0],[0,1,0,0],[0,0,-1,0],[0,0,0,1]]):
        with pytest.raises(ValueError,match='uniform'):api.placement(matrix,1)


def test_dead_writer_completed_family_stage_recovers_without_blender(tmp_path):
    target=tmp_path/'delivery'
    script='''
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tests'))
from test_card_family_files import bundle
from mcpblender.export_jobs import ExportJob
with ExportJob(sys.argv[1],'test-owner','CARD_FAMILY',{'family_guard':'a'*64}) as job:
    job.stage.mkdir();job.created();bundle(job.stage);job.verify();os._exit(23)
'''
    done=subprocess.run([sys.executable,'-c',script,str(target)],capture_output=True,text=True,timeout=30)
    assert done.returncode==23,done.stderr
    current=inspect(target,'test-owner');assert not current['writer_active'] and current['record']['state']=='verified'
    result=recover(target,'test-owner',current['job_sha256'],publish=True)
    assert result['record']['state']=='published' and not result['replayed'] and api.validate(target)['valid']
