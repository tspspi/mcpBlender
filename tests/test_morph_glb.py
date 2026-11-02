"""Independent known-answer glTF morph interpolation and morph-before-skin replay."""
import json
import math
import struct
import pytest
from mcpblender.skin_glb import Document,replay_digest


def fixture(path,*,skinned=False,mode='LINEAR',weight_values=None,defaults=None):
    binary=bytearray();views=[];arrays=[]
    def add(rows,type,kind=5126):
        while len(binary)%4:binary.append(0)
        start=len(binary);fmt={5126:'f',5121:'B',5123:'H'}[kind]
        for row in rows:binary.extend(struct.pack('<'+fmt*len(row),*row))
        views.append({'buffer':0,'byteOffset':start,'byteLength':len(binary)-start});arrays.append({'bufferView':len(views)-1,'componentType':kind,'count':len(rows),'type':type});return len(arrays)-1
    p=add([(0,0,0),(1,0,0),(0,1,0)],'VEC3');n=add([(0,0,1)]*3,'VEC3');i=add([(0,),(1,),(2,)],'SCALAR',5123)
    up=add([(0,0,2)]*3,'VEC3');right=add([(4,0,0)]*3,'VEC3');time=add([(0,),(1,)],'SCALAR')
    rows=weight_values if weight_values is not None else ([0,0,1,.5] if mode!='CUBICSPLINE' else [0,0,0,0,0,0,0,0,1,.5,0,0])
    values=add([(v,) for v in rows],'SCALAR');attrs={'POSITION':p,'NORMAL':n};nodes=[{'name':'Mesh','mesh':0,'translation':[3,0,0]}]
    skins=[]
    if skinned:
        attrs.update(JOINTS_0=add([(0,0,0,0)]*3,'VEC4',5121),WEIGHTS_0=add([(1,0,0,0)]*3,'VEC4'))
        inverse=add([(1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1)],'MAT4');nodes[0]['skin']=0;nodes.append({'name':'Joint','translation':[3,0,0]});skins=[{'joints':[1],'inverseBindMatrices':inverse}]
    doc={'asset':{'version':'2.0'},'nodes':nodes,'scenes':[{'nodes':list(range(len(nodes)))}],'scene':0,
         'meshes':[{'weights':[.25,.125] if defaults is None else defaults,'extras':{'targetNames':['Up','Right']},'primitives':[{'indices':i,'attributes':attrs,'targets':[{'POSITION':up},{'POSITION':right}]}]}],
         'animations':[{'name':'Morph','samplers':[{'input':time,'output':values,'interpolation':mode}],'channels':[{'sampler':0,'target':{'node':0,'path':'weights'}}]}],
         'accessors':arrays,'bufferViews':views,'buffers':[{'byteLength':len(binary)}]}
    if skins:doc['skins']=skins
    save(path,doc,binary)


def save(path,doc,binary):
    binary=bytes(binary)+b'\0'*((-len(binary))%4)
    encoded=json.dumps(doc,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary)


@pytest.mark.parametrize('skinned',[False,True])
def test_morph_defaults_linear_and_pre_skin_order(tmp_path,skinned):
    path=tmp_path/'morph.glb';fixture(path,skinned=skinned);doc=Document(path,morphs=True)
    assert doc.replay(None,0,[(0,0)])['points'][0]==pytest.approx([3.5,0,.5])
    assert doc.replay('Morph',.5,[(0,0)])['points'][0]==pytest.approx([4,0,1])
    assert doc.replay('Morph',1,[(0,1)])['points'][0]==pytest.approx([6,0,2])
    assert doc.replay(None,0,[(0,0)],morph_weights=[0,1])['points'][0]==pytest.approx([7,0,0])
    assert doc.report()['morph_targets']==['Up','Right']
    assert len(doc.representatives(1))>=1
    if skinned:
        # A 90 degree joint rotation must rotate the morph offset as well.
        doc.nodes[1]['rotation']=[0,math.sqrt(.5),0,math.sqrt(.5)]
        assert doc.replay('Morph',1,[(0,0)])['points'][0]==pytest.approx([5,0,-2])
        with pytest.raises(ValueError,match='morph-enabled'):Document(path)


def test_weight_step_and_cubic_grouping(tmp_path):
    path=tmp_path/'morph.glb';fixture(path,mode='STEP');doc=Document(path,morphs=True)
    assert doc.replay('Morph',.9,[(0,0)])['points'][0]==pytest.approx([3,0,0])
    fixture(path,mode='CUBICSPLINE');doc=Document(path,morphs=True)
    assert doc.replay('Morph',.25,[(0,0)])['points'][0]==pytest.approx([3.3125,0,.3125])
    assert doc.replay('Morph',1,[(0,0)])['points'][0]==pytest.approx([5,0,2])


@pytest.mark.parametrize('patch,message',[
    ({'weight_values':[0,0,1]},'layout'),
    ({'defaults':[0]},'default morph'),
    ({'defaults':[float('nan'),0]},'default morph'),
    ({'weight_values':[0,0,float('inf'),0]},'Nonfinite'),
])
def test_morph_rejects_bad_counts_and_nonfinite_weights(tmp_path,patch,message):
    path=tmp_path/'morph.glb';fixture(path,**patch)
    with pytest.raises(ValueError,match=message):Document(path,morphs=True)


def test_morph_names_vertex_count_node_defaults_and_proofs(tmp_path):
    from mcpblender.lod_files import read_glb
    path=tmp_path/'morph.glb';fixture(path);doc,binary=read_glb(path)
    doc['nodes'][0]['weights']=[0,1];save(path,doc,binary);decoded=Document(path,morphs=True)
    assert decoded.replay(None,0,[(0,0)])['points'][0]==pytest.approx([7,0,0])
    proof=replay_digest(decoded.replay('Morph',.5,decoded.representatives(3)))
    assert proof==replay_digest(decoded.replay('Morph',.5,decoded.representatives(3)))
    doc['meshes'][0]['extras']['targetNames']=['Up','Up'];save(path,doc,binary)
    with pytest.raises(ValueError,match='names'):Document(path,morphs=True)
    doc['meshes'][0]['extras']['targetNames']=['Up','Right'];target=doc['meshes'][0]['primitives'][0]['targets'][0]['POSITION'];doc['accessors'][target]['count']=2;save(path,doc,binary)
    with pytest.raises(ValueError,match='layout'):Document(path,morphs=True)


def test_morph_inspection_pagination_cancel_and_changed_file(tmp_path):
    from mcpblender.skin_glb import inspect_file
    path=tmp_path/'morph.glb';fixture(path)
    report=inspect_file({'path':str(path),'limit':1,'animation_samples':3,'sample_limit':1})
    assert len(report['samples'])==4 and report['samples'][2]['time']==.5
    assert all(len(s['vertex_samples'])==1 for s in report['samples'])
    assert report['samples'][2]['sampled_world_bounds']['max']==pytest.approx([5,1,1])
    assert report['next_offset'] is None
    assert len(inspect_file({'path':str(path),'offset':1})['samples'])==1
    with pytest.raises(ValueError,match='clip not found'):inspect_file({'path':str(path),'clip':'Absent'})
    phases=[]
    class Cancelled(Exception):pass
    def progress(value):phases.append(value['phase'])
    def cancel():
        if 'sampled GLB deformation' in phases:raise Cancelled()
    before=path.read_bytes()
    with pytest.raises(Cancelled):inspect_file({'path':str(path)},check_cancelled=cancel,progress=progress)
    assert path.read_bytes()==before
    def replace(value):
        if value['phase']=='sampled GLB deformation':path.write_bytes(before+b'changed')
    with pytest.raises(ValueError,match='changed during'):inspect_file({'path':str(path)},progress=replace)


def test_matrix_node_weights_and_changed_target_fingerprint(tmp_path):
    from mcpblender.lod_files import read_glb
    path=tmp_path/'morph.glb';fixture(path);doc,binary=read_glb(path)
    doc['nodes'][0].pop('translation');doc['nodes'][0]['matrix']=[1,0,0,0,0,1,0,0,0,0,1,0,3,0,0,1];save(path,doc,binary)
    decoded=Document(path,morphs=True);indices=decoded.representatives(3);before=replay_digest(decoded.replay('Morph',.5,indices))
    array=doc['accessors'][doc['meshes'][0]['primitives'][0]['targets'][0]['POSITION']];view=doc['bufferViews'][array['bufferView']]
    changed=bytearray(binary);struct.pack_into('<f',changed,view.get('byteOffset',0)+8,3.);save(path,doc,changed)
    decoded=Document(path,morphs=True);assert replay_digest(decoded.replay('Morph',.5,indices))!=before
    doc['nodes'][0]['extensions']={'EXT_mesh_gpu_instancing':{'attributes':{}}};save(path,doc,changed)
    with pytest.raises(ValueError,match='instanced'):Document(path,morphs=True)


def sparse_fixture(path,*,indices=(1,),base=False,kind=5121):
    from mcpblender.lod_files import read_glb
    fixture(path);doc,binary=read_glb(path);blob=bytearray(binary)
    def view(payload):
        while len(blob)%4:blob.append(0)
        start=len(blob);blob.extend(payload);doc['bufferViews'].append({'buffer':0,'byteOffset':start,'byteLength':len(payload)});return len(doc['bufferViews'])-1
    iv=view(struct.pack('<'+{5121:'B',5123:'H',5125:'I'}[kind]*len(indices),*indices));vv=view(struct.pack('<'+'3f'*len(indices),*([0,0,4]*len(indices))))
    a=doc['accessors'][doc['meshes'][0]['primitives'][0]['targets'][0]['POSITION']]
    if not base:a.pop('bufferView')
    a['sparse']={'count':len(indices),'indices':{'bufferView':iv,'componentType':kind},'values':{'bufferView':vv}}
    doc['buffers'][0]['byteLength']=len(blob);save(path,doc,blob)


@pytest.mark.parametrize('base',[False,True])
def test_sparse_morph_zero_base_and_dense_overlays(tmp_path,base):
    path=tmp_path/'sparse.glb';sparse_fixture(path,base=base);doc=Document(path,morphs=True)
    result=doc.replay('Morph',1,[(0,0),(0,1)])['points']
    assert result[0]==pytest.approx([5,0,2 if base else 0])
    assert result[1]==pytest.approx([6,0,4])


@pytest.mark.parametrize('indices',[(1,1),(2,1),(3,)])
def test_sparse_morph_rejects_duplicate_unsorted_and_out_of_range_indices(tmp_path,indices):
    path=tmp_path/'sparse.glb';sparse_fixture(path,indices=indices)
    with pytest.raises(ValueError,match='Sparse indices'):Document(path,morphs=True)


@pytest.mark.parametrize('kind',[5123,5125])
def test_sparse_wide_index_components_and_truncated_values(tmp_path,kind):
    from mcpblender.lod_files import read_glb
    path=tmp_path/'sparse.glb';sparse_fixture(path,kind=kind)
    assert Document(path,morphs=True).replay('Morph',1,[(0,1)])['points'][0]==pytest.approx([6,0,4])
    doc,binary=read_glb(path);a=doc['accessors'][doc['meshes'][0]['primitives'][0]['targets'][0]['POSITION']]
    doc['bufferViews'][a['sparse']['values']['bufferView']]['byteLength']=4;save(path,doc,binary)
    with pytest.raises(ValueError,match='buffer view'):Document(path,morphs=True)
