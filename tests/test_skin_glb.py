"""Independent known-answer skin replay and malformed binary rejection."""
import json
import math
import struct
import pytest
from mcpblender.skin_glb import Document,replay_digest,check_recorded_samples
from mcpblender.lod_files import glb_report


def fixture(path,*,weights=None,joints=None,times=None,inverse=None,cubic=False,rotation=True):
    blob=bytearray();views=[];accessors=[]
    def add(rows,type,kind=5126):
        while len(blob)%4:blob.append(0)
        start=len(blob);fmt={5126:'f',5121:'B',5123:'H'}[kind]
        for row in rows:blob.extend(struct.pack('<'+fmt*len(row),*row))
        views.append({'buffer':0,'byteOffset':start,'byteLength':len(blob)-start})
        accessors.append({'bufferView':len(views)-1,'componentType':kind,'count':len(rows),'type':type})
        return len(accessors)-1
    position=add([(0,0,0),(1,0,0),(0,1,0)],'VEC3');normal=add([(0,0,1)]*3,'VEC3')
    joint=add(joints or [(0,0,0,0)]*3,'VEC4',5121);weight=add(weights or [(1,0,0,0)]*3,'VEC4')
    indices=add([(0,),(1,),(2,)],'SCALAR',5123);ibm=add([inverse or (1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)],'MAT4')
    time=add([(t,) for t in (times or [0,1])],'SCALAR')
    values=[(0,0,0),(2,0,0)] if not cubic else [(0,0,0),(0,0,0),(0,0,0),(0,0,0),(2,0,0),(0,0,0)]
    translation=add(values,'VEC3');samplers=[{'input':time,'output':translation,'interpolation':'CUBICSPLINE' if cubic else 'LINEAR'}];channels=[{'sampler':0,'target':{'node':0,'path':'translation'}}]
    if rotation:
        q=add([(0,0,0,1),(0,0,math.sqrt(.5),math.sqrt(.5))],'VEC4');samplers.append({'input':time,'output':q,'interpolation':'LINEAR'});channels.append({'sampler':1,'target':{'node':0,'path':'rotation'}})
    while len(blob)%4:blob.append(0)
    doc={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(blob)}],'bufferViews':views,'accessors':accessors,'nodes':[{'name':'Joint'},{'name':'Mesh','mesh':0,'skin':0}],
         'scenes':[{'nodes':[0,1]}],'scene':0,'skins':[{'joints':[0],'inverseBindMatrices':ibm}],
         'meshes':[{'primitives':[{'indices':indices,'attributes':{'POSITION':position,'NORMAL':normal,'JOINTS_0':joint,'WEIGHTS_0':weight}}]}],
         'animations':[{'name':'Motion','samplers':samplers,'channels':channels}]}
    encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(blob))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(blob),b'BIN\0')+blob)


def test_known_linear_quaternion_and_cubic_skin_playback(tmp_path):
    path=tmp_path/'skin.glb';fixture(path);doc=Document(path)
    result=doc.replay('Motion',.5,[(0,1)])
    assert result['points'][0]==pytest.approx([1+math.sqrt(.5),math.sqrt(.5),0],abs=1e-6)
    assert glb_report(path,skinned=True)['triangles']==1
    with pytest.raises(ValueError,match='Static LOD'):glb_report(path)
    proof={'clip':'Motion','time':.5,'point_limit':3,'replay_sha256':replay_digest(doc.replay('Motion',.5,doc.representatives(3)))}
    check_recorded_samples(doc,[proof])
    with pytest.raises(ValueError,match='replay differs'):check_recorded_samples(doc,[proof|{'replay_sha256':'0'*64}])
    fixture(path,cubic=True,rotation=False);doc=Document(path)
    assert doc.replay('Motion',.25,[(0,0)])['points'][0]==pytest.approx([.3125,0,0])


@pytest.mark.parametrize('patch,message',[
    ({'weights':[(.5,0,0,0)]*3},'influences'),
    ({'joints':[(1,0,0,0)]*3},'influences'),
    ({'times':[0,0]},'time'),
    ({'inverse':(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1)},'nondegenerate'),
    ({'weights':[(float('nan'),0,0,0)]*3},'Nonfinite'),
])
def test_skin_binary_rejects_malformed_data(tmp_path,patch,message):
    path=tmp_path/'bad.glb';fixture(path,**patch)
    with pytest.raises(ValueError,match=message):Document(path)
