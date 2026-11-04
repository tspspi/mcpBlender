"""Field provenance, explicit coverage witnesses and legacy capture distinction."""
import copy
import pytest
from mcpblender import botany,capture_material_fields as fields,tree_capture


def contract():
    bindings={f['key']:{'constant':[.2,.3,.4,1.] if f['type']=='COLOR' else 0.} for f in fields.FIELDS}
    bindings['surface_weight']={'constant':1.};bindings['material_id']={'constant':1.}
    value={'format':fields.FORMAT,'fields':fields.FIELDS,'materials':[{'material':'Surface','id':1,'model':'PRINCIPLED','bindings':bindings,'thickness_m':None}]}
    return value|{'fields_sha256':botany.digest(value)}


def test_frozen_field_contract_headers_and_memory_groups():
    value=contract();assert fields.validate(value)==value
    header={'channels':[{'name':name,'pixel_type':2} for name in fields.channels()]};fields.validate_header(header,value)
    header['channels'].pop()
    with pytest.raises(ValueError,match='float32'):fields.validate_header(header,value)
    assert {v['key'] for group in fields.groups() for v in group}=={v['key'] for v in fields.FIELDS}-{'surface_weight'}
    assert all(1+sum(3 if v['type']=='COLOR' else 1 for v in group)<=12 for group in fields.groups())
    for key,change in [('base_color',{'constant':[1.,0.]}),('roughness',{'constant':True}),('surface_weight',{'constant':.5}),('thin_mode',{'constant':1.})]:
        bad=copy.deepcopy(value);bad['materials'][0]['bindings'][key]=change;bad['fields_sha256']=botany.digest({k:v for k,v in bad.items() if k!='fields_sha256'})
        with pytest.raises(ValueError):fields.validate(bad)
    bad=copy.deepcopy(value);bad['materials'][0]['thickness_m']=.001;bad['fields_sha256']=botany.digest({k:v for k,v in bad.items() if k!='fields_sha256'})
    with pytest.raises(ValueError,match='thickness'):fields.validate(bad)


def test_capture_option_and_material_contract_must_agree():
    meta={'format':tree_capture.FORMAT,'views':[{'view':'FRONT','camera':'C'}],'frame':1,'options':{'resolution':32,'samples':1}}
    job={'cameras':['C'],'formats':['PNG','OPEN_EXR_MULTILAYER'],'engine':'CYCLES','frame_start':1,'frame_end':1,'width':32,'height':32,'samples':1}
    def seal(value):return value|{'capture_sha256':botany.digest({k:v for k,v in value.items() if k!='capture_sha256'})}
    assert tree_capture.validate(seal(meta),job)
    meta['options']['material_fields']=True
    with pytest.raises(ValueError,match='option'):tree_capture.validate(seal(meta),job)
    meta['material_fields']=contract();assert tree_capture.validate(seal(meta),job)
