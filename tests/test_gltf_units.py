"""Scene-unit wrappers preserve buffers, shared roots, hierarchy and legacy units."""
import copy
import json
import struct
import pytest
from mcpblender.gltf_units import normalize_document,normalize_file,validate_document,native_comparison


def test_scene_shared_roots_no_double_scaling_and_strict_validation():
    doc={'asset':{'version':'2.0'},'nodes':[{'name':'A','children':[1]},{'name':'Child'},{'name':'B'}],'scenes':[{'nodes':[0,2]},{'nodes':[0]}]}
    before=copy.deepcopy(doc);assert not normalize_document(doc,1) and doc==before
    assert normalize_document(doc,.01) and validate_document(doc,.01)==.01
    assert len(doc['nodes'])==5 and doc['nodes'][:3]==before['nodes']
    assert doc['scenes'][0]['nodes'][0]==doc['scenes'][1]['nodes'][0]
    for mutation in ('scale','bypass','parent','metadata'):
        bad=copy.deepcopy(doc);root=bad['asset']['extras']['mcpblender_units']['roots'][0]['node']
        if mutation=='scale':bad['nodes'][root]['scale']=[.1]*3
        if mutation=='bypass':bad['scenes'][0]['nodes']=[0]
        if mutation=='parent':bad['nodes'][2]['children']=[root]
        if mutation=='metadata':bad['asset']['extras']['mcpblender_units']['scene_unit_scale']=.1
        with pytest.raises(ValueError):validate_document(bad,.01)
    comparison=copy.deepcopy(doc);native_comparison(comparison,.01)
    assert comparison['nodes'][3]['scale']==[1]*3
    with pytest.raises(ValueError):validate_document(doc,1)
    with pytest.raises(ValueError):normalize_document(doc,.01)
    with pytest.raises(ValueError):validate_document(before,.01)


def test_glb_binary_is_byte_identical_and_unit_one_does_not_touch_file(tmp_path):
    doc={'asset':{'version':'2.0'},'nodes':[{}],'scenes':[{'nodes':[0]}]}
    encoded=json.dumps(doc).encode();encoded+=b' '*((-len(encoded))%4);binary=b'unchanged bytes!'
    binary+=b'\0'*((-len(binary))%4)
    raw=struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\0')+binary
    path=tmp_path/'scene.glb';path.write_bytes(raw);stamp=path.stat().st_mtime_ns
    assert not normalize_file(path,1) and path.read_bytes()==raw and path.stat().st_mtime_ns==stamp
    normalize_file(path,.01);result=path.read_bytes();size=struct.unpack_from('<I',result,12)[0]
    assert result[20+size:]==raw[20+len(encoded):]
    assert validate_document(json.loads(result[20:20+size]),.01)==.01
