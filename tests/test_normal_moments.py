"""Normal-input provenance, moment bounds and coverage conditioning."""
import copy
import math
import pytest
from mcpblender import botany,normal_moments as moments
from mcpblender.botanical_capture_contracts import Source


def contract():
    rows=[{'material':'M','id':1,'model':'PRINCIPLED'}]
    binding={'node':'PBR','socket':'Normal','source':None,'default':[0.,0.,0.]}
    value={'format':moments.FORMAT,'fields':moments.FIELDS,'coordinate_space':'WORLD','normalization':'PER_HIT_UNIT_INPUT','materials':[{'material':'M','id':1,'normal':binding,'thin_normal':None}]}
    return value|{'moments_sha256':botany.digest(value)},rows


def test_normal_moment_contract_and_capture_opt_in():
    value,rows=contract();assert moments.validate(value,rows)==value
    assert len(moments.channels())==9
    with pytest.raises(ValueError,match='material_fields'):Source(collection='Tree',normal_moments=True)
    assert Source(collection='Tree',material_fields=True,normal_moments=True).normal_moments
    for change in ({'coordinate_space':'CAMERA'},{'fields':[]},{'materials':[]},{'normalization':'NONE'}):
        bad=value|change;bad['moments_sha256']=botany.digest({k:v for k,v in bad.items() if k!='moments_sha256'})
        with pytest.raises(ValueError):moments.validate(bad,rows)
    bad=copy.deepcopy(value);bad['materials'][0]['normal']['default']=[0,0,float('inf')]
    with pytest.raises(ValueError):moments.validate(bad,rows)


def geometry(normal,alpha=None):
    return {'channels':{'TreeCapture.Combined.A':alpha or [1]*len(normal),**{'TreeCapture.Normal.'+a:[n[i] for n in normal] for i,a in enumerate('XYZ')}}}


def test_first_second_moments_preserve_covariance_and_coverage():
    # Known unit +Z versus equal +/-60-degree facets; second observation is
    # half-covered. Conditioning recovers the same physical moments.
    data=[[0,0],[0,0],[1,.25],[0,.375],[0,0],[0,0],[0,0],[0,0],[1,.125]]
    result=moments.measure(geometry([(0,0,1),(0,0,.25)],[1,.5]),[1,.5],data,.01)
    assert result['input_moments_valid'] and result['covered_pixels']==2
    assert result['statistics']['unit_trace']['mean']==1
    assert result['statistics']['mean_length']['mean']==.75
    assert result['statistics']['covariance_trace']['mean']==.375
    assert data[2]==[1,.25]


def test_invalid_moments_are_reported_without_clamping():
    # Trace-one moments with impossible mean/covariance, zero-unit trace,
    # native Normal mismatch, missing weight and nonfinite data.
    data=[[0]*5,[0]*5,[2,0,1,1,float('nan')],[1,0,0,0,0],[0]*5,[0]*5,[0]*5,[0]*5,[0,0,1,1,1]]
    result=moments.measure(geometry([(0,0,2),(0,0,0),(0,0,.5),(0,0,1),(0,0,1)]),[1,1,1,0,1],data,.01)
    assert not result['input_moments_valid'] and result['covariance_psd_violations']==1 and result['unit_trace_violations']==1
    assert result['normal_pass_disagreements']==1 and result['unavailable_pixels']==1 and result['nonfinite_pixels']==1
    assert result['statistics']['covariance_trace']['min']==-3
    with pytest.raises(ValueError,match='lengths'):moments.measure(geometry([(0,0,1)]),[1],data,.01)
    def cancel():raise InterruptedError('cancel')
    with pytest.raises(InterruptedError):moments.measure(geometry([(0,0,1)]),[1],[[0] for _ in range(9)],.01,cancelled=cancel)


def test_parent_contract_requires_optional_moment_float_channels():
    from test_capture_material_fields import contract as base_contract
    from mcpblender import capture_material_fields as fields
    base=base_contract();extension,_=contract();extension['materials'][0]['material']='Surface'
    extension['moments_sha256']=botany.digest({k:v for k,v in extension.items() if k!='moments_sha256'})
    value=base|{'normal_moments':extension};value['fields_sha256']=botany.digest({k:v for k,v in value.items() if k!='fields_sha256'})
    assert fields.validate(value)==value
    header={'channels':[{'name':n,'pixel_type':2} for n in fields.channels()+moments.channels()]}
    fields.validate_header(header,value);header['channels'].pop()
    with pytest.raises(ValueError,match='float32'):fields.validate_header(header,value)


def test_valid_input_moments_are_distinct_from_renderer_normal_agreement():
    values=[[0],[0],[1],[0],[0],[0],[0],[0],[1]]
    result=moments.measure(geometry([(0,0,.8)]),[1],values,.01)
    assert result['input_moments_valid'] and not result['normal_pass_first_moment_agrees']
    assert result['normal_pass_disagreements']==1


def test_safe_unit_recipe_pins_geometry_fallback():
    value,rows=contract();value['normalization']='PER_HIT_SAFE_UNIT_INPUT';value['zero_length_fallback']='GEOMETRY_NORMAL'
    value['moments_sha256']=botany.digest({k:v for k,v in value.items() if k!='moments_sha256'})
    assert moments.validate(value,rows)==value
    value['zero_length_fallback']='ZERO';value['moments_sha256']=botany.digest({k:v for k,v in value.items() if k!='moments_sha256'})
    with pytest.raises(ValueError,match='fallback'):moments.validate(value,rows)


def test_missing_observations_cannot_establish_normal_pass_agreement():
    values=[[0,0],[0,0],[1,1],[0,0],[0,0],[0,0],[0,0],[0,0],[1,1]]
    result=moments.measure(geometry([(0,0,1),(0,0,1)]),[1,0],values,.01)
    assert result['unavailable_pixels']==1 and result['normal_pass_disagreements']==0
    assert not result['input_moments_valid'] and not result['normal_pass_first_moment_agrees']
