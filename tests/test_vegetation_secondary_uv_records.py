"""Independent secondary UV lineage, inventory and adoption-baseline guards."""
from copy import deepcopy
import json
import pytest
from mcpblender import botany,vegetation_uv as uv
from mcpblender.vegetation_lod_contracts import SecondaryUV


def bound(names,hashes):
    row={'format':uv.FORMAT,'uv_map':names[-1],'uv_channel':len(names)-1,'uv_maps':names,
         'uv_witness':hashes,'texture_size':[256,128],'source_lods_sha256':'a'*64,'instance_atlas':False}
    row['record_sha256']=botany.digest(row)
    return row


def test_secondary_lineage_preserves_channels_and_baselines(tmp_path):
    a=uv.uv_digest([(0,0),(1,0),(0,1)]);b=uv.uv_digest([(.1,.1),(.9,.1),(.1,.9)]);c=uv.uv_digest([(.2,.2),(.8,.2),(.2,.8)])
    first=bound(['LeafUV','UV2'],{'LeafUV':a,'UV2':b})
    # A new bake channel can be appended between two secondary edits.
    second=bound(['LeafUV','UV2','BakeUV','UV3'],{'LeafUV':a,'UV2':b,'BakeUV':a,'UV3':c})
    hashes=uv.verify_maps([first,second],second['uv_maps'],second['uv_witness'])
    assert len(hashes)==4
    with pytest.raises(ValueError,match='order'):
        uv.verify_maps([first],['UV2','LeafUV'],first['uv_witness'])
    with pytest.raises(ValueError,match='coordinates'):
        uv.verify_maps([first],first['uv_maps'],{'LeafUV':a,'UV2':c})
    with pytest.raises(ValueError,match='baseline'):
        uv.expected([first,bound(second['uv_maps'],second['uv_witness']|{'LeafUV':c})])
    with pytest.raises(ValueError,match='order'):uv.expected([second,first])
    # Portable records bind the actual numeric-bundle witness, not a filename.
    directory=tmp_path/'leaf-0';directory.mkdir()
    manifest={'source':{'uv_maps':first['uv_maps']},'witness':{'uvs':[[(0,0),(1,0),(0,1)],[(.1,.1),(.9,.1),(.1,.9)]]}}
    (directory/'manifest.json').write_text(json.dumps(manifest))
    uv.verify(tmp_path,{'leaf-0':[first]},['leaf-0'])
    with pytest.raises(ValueError,match='roles'):uv.verify(tmp_path,{'other':[first]},['leaf-0'])
    manifest['witness']['uvs'][0][0]=(.25,.25)
    (directory/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='coordinates'):uv.verify(tmp_path,{'leaf-0':[first]},['leaf-0'])


def test_secondary_contracts_and_record_tamper():
    base={'lod_collection':'Lods','expected_lods':'a'*64,'assets':['leaf-0']}
    assert SecondaryUV(**base).uv_map=='UV2'
    for patch in ({'assets':[]},{'assets':['leaf-0','leaf-0']},{'assets':['']},{'angle_limit_degrees':float('nan')},
                  {'texture_width':8},{'max_corners':True},{'tile_padding_pixels':-1},
                  {'texture_width':4096,'texture_height':4096,'chart_layout':{}}):
        with pytest.raises(ValueError):SecondaryUV.model_validate(base|patch)
    row=bound(['LeafUV','UV2'],{'LeafUV':'a'*64,'UV2':'b'*64})
    for patch in ({'uv_channel':0},{'uv_map':'LeafUV'},{'instance_atlas':True},{'texture_size':[0,128]},
                  {'uv_maps':['UV2','UV2']},{'uv_witness':{'LeafUV':'a'*64}},{'source_lods_sha256':'bad'}):
        changed=deepcopy(row)|patch
        changed['record_sha256']=botany.digest({k:v for k,v in changed.items() if k!='record_sha256'})
        with pytest.raises(ValueError):uv.validate(changed)
    row['uv_map']='Tampered'
    with pytest.raises(ValueError,match='binding'):uv.validate(row)
