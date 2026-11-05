"""Face-normal provenance and bounded read-only diagnostic semantics."""
import copy
import math
import pytest
from mcpblender import botany,geometric_normals as normals,capture_material_fields as fields,tree_capture
from mcpblender.botanical_capture_contracts import Source
from test_capture_material_fields import contract as material_contract


def test_optional_contract_headers_metadata_and_legacy():
    base=material_contract();frozen=copy.deepcopy(base)
    assert not Source(collection='Tree').geometric_normals
    with pytest.raises(ValueError,match='material_fields'):Source(collection='Tree',geometric_normals=True)
    assert Source(collection='Tree',material_fields=True,geometric_normals=True).geometric_normals
    extension=normals.contract(base['materials']);assert normals.validate(extension,base['materials'])==extension
    value=base|{'geometric_normals':extension};value['fields_sha256']=botany.digest({k:v for k,v in value.items() if k!='fields_sha256'})
    assert fields.validate(value)==value
    for key,change in [('orientation','UNFLIPPED'),('coordinate_space','OBJECT'),('materials',[]),('fields',[])]:
        bad=extension|{key:change};bad['normals_sha256']=botany.digest({k:v for k,v in bad.items() if k!='normals_sha256'})
        with pytest.raises(ValueError,match='contract'):normals.validate(bad,base['materials'])
    header={'channels':[{'name':n,'pixel_type':2} for n in fields.channels()+normals.channels()]}
    fields.validate_header(header,value);header['channels'][-1]['pixel_type']=1
    with pytest.raises(ValueError,match='float32'):fields.validate_header(header,value)
    meta={'format':tree_capture.FORMAT,'views':[{'view':'FRONT','camera':'C'}],'frame':1,'options':{'resolution':32,'samples':1,'material_fields':True},'material_fields':value}
    job={'cameras':['C'],'formats':['PNG','OPEN_EXR_MULTILAYER'],'engine':'CYCLES','frame_start':1,'frame_end':1,'width':32,'height':32,'samples':1}
    def seal():return meta|{'capture_sha256':botany.digest(meta)}
    with pytest.raises(ValueError,match='option'):tree_capture.validate(seal(),job)
    meta['options']['geometric_normals']=True;assert tree_capture.validate(seal(),job)
    assert fields.validate(base)==frozen


def geometry(normals,alpha):
    return {'channels':{'TreeCapture.Combined.A':alpha,**{'TreeCapture.Normal.'+a:[n[j] for n in normals] for j,a in enumerate('XYZ')}}}


def test_coverage_conditioning_negative_components_and_distinct_normals():
    # Same 60-degree difference at full and half surface weight. Beauty alpha
    # deliberately differs, and raw negative components must remain untouched.
    g=geometry([(0,0,1),(0,0,.5)],[1,.75]);values=[[-math.sqrt(.75),-.5*math.sqrt(.75)],[0,0],[.5,.25]];original=copy.deepcopy(values)
    result=normals.measure(g,[1,.5],values,.01)
    assert result['covered_pixels']==result['different_direction_pixels']==2
    assert result['statistics']['conditional_length']['mean']==pytest.approx(1)
    assert result['statistics']['shading_angle_degrees']['mean']==pytest.approx(60)
    assert values==original


def test_unavailable_nonfinite_above_unit_zero_and_cancellation():
    g=geometry([(0,0,1)]*7,[1,1,1,1,1,1,float('nan')])
    values=[[0]*7,[0]*7,[2,0,1,float('nan'),1,1,1]]
    result=normals.measure(g,[1,1,0,1,float('inf'),-1,1],values,.01)
    assert result['conditional_length_over_one']==1 and result['zero_geometric_normals']==1
    assert result['unavailable_pixels']==3 and result['nonfinite_pixels']==1 and result['invalid_alpha']==1
    assert result['statistics']['conditional_length']['max']==2
    with pytest.raises(ValueError,match='lengths'):normals.measure(g,[],values,.01)
    def stop():raise InterruptedError('cancelled')
    with pytest.raises(InterruptedError):normals.measure(g,[1]*7,values,.01,cancelled=stop)
    zero=normals.measure(geometry([(0,0,0)],[1]),[1],[[0],[0],[1]],.01)
    assert zero['zero_shading_normals']==1 and zero['statistics']['shading_angle_degrees']['count']==0
