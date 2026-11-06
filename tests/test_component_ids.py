"""Explicit first-sample component provenance and bounded integer diagnostics."""
from copy import deepcopy
import pytest
from mcpblender import botany,component_ids as ids,tree_capture
from mcpblender.botanical_capture_contracts import Source
from test_capture_material_fields import contract as material_contract


def fields():
    value=material_contract();value['materials'][0]['bindings']['alpha']={'constant':1.}
    value['fields_sha256']=botany.digest({k:v for k,v in value.items() if k!='fields_sha256'});return value


def test_source_opt_in_requires_one_sample_fields_and_part_budget():
    assert not Source(collection='Tree').component_ids
    for args in ({},{'material_fields':True},{'samples':1}):
        with pytest.raises(ValueError,match='samples=1'):Source(collection='Tree',component_ids=True,**args)
    assert Source(collection='Tree',component_ids=True,material_fields=True,samples=1).component_ids
    with pytest.raises(ValueError,match='32-part'):Source(collection='Tree',component_ids=True,material_fields=True,samples=1,normal_moments=True,geometric_normals=True)


def test_contract_opaque_admission_inventory_hash_and_headers():
    f=fields();value=ids.contract(f,2,'Points','Instancer',botany.digest([0,1]))
    assert ids.validate(value,f)==value
    for key,change in [('offset',0),('structural_value',-1),('attribute_type','GEOMETRY'),('source_attribute','material_id'),('samples',8),('materials',[]),('leaf_count',True)]:
        bad=value|{key:change};bad['components_sha256']=botany.digest({k:v for k,v in bad.items() if k!='components_sha256'})
        with pytest.raises(ValueError):ids.validate(bad,f)
    for count,mesh,obj,sha in [(-1,'P','O','a'*64),(250001,'P','O','a'*64),(1,None,None,'a'*64),(1,'P',None,'a'*64),(1,'P','O','bad')]:
        with pytest.raises(ValueError):ids.contract(f,count,mesh,obj,sha)
    assert ids.validate(ids.contract(f,0,None,None,botany.digest([])),f)
    for key,binding in [('alpha',{'constant':.5}),('alpha',{'node':'P','socket':'Alpha','source':{'node':'Value','socket':'Value'},'default':1.}),('transmission_weight',{'constant':.1}),('cull_weight',{'constant':1.})]:
        bad=deepcopy(f);bad['materials'][0]['bindings'][key]=binding;bad['fields_sha256']=botany.digest({k:v for k,v in bad.items() if k!='fields_sha256'})
        with pytest.raises(ValueError,match='opaque'):ids.contract(bad,2,'P','O','a'*64)
    ids.validate_header({'channels':[{'name':ids.channels()[0],'pixel_type':2}]},value,f)
    with pytest.raises(ValueError,match='float32'):ids.validate_header({'channels':[]},value,f)
    with pytest.raises(ValueError,match='float32'):ids.validate_header({'channels':[{'name':ids.channels()[0],'pixel_type':1}]},value,f)


def test_capture_metadata_requires_component_option_and_one_sample():
    f=fields();component=ids.contract(f,2,'P','O',botany.digest([0,1]))
    meta={'format':tree_capture.FORMAT,'views':[{'view':'FRONT','camera':'C'}],'frame':1,'options':{'resolution':32,'samples':1,'material_fields':True},'material_fields':f,'component_ids':component}
    job={'cameras':['C'],'formats':['PNG','OPEN_EXR_MULTILAYER'],'engine':'CYCLES','frame_start':1,'frame_end':1,'width':32,'height':32,'samples':1}
    def seal():return meta|{'capture_sha256':botany.digest(meta)}
    with pytest.raises(ValueError,match='option'):tree_capture.validate(seal(),job)
    meta['options']['component_ids']=True;assert tree_capture.validate(seal(),job)
    meta['source_content_sha256']='a'*64;assert tree_capture.validate(seal(),job)
    meta['source_content_sha256']='bad'
    with pytest.raises(ValueError,match='source digest'):tree_capture.validate(seal(),job)
    del meta['source_content_sha256']
    meta['options']['samples']=2;job['samples']=2
    with pytest.raises(ValueError,match='one sample'):tree_capture.validate(seal(),job)


def test_component_measurement_distinguishes_structure_leaves_and_invalid_observations():
    geometry={'channels':{'TreeCapture.Combined.A':[1,1,1,0]}}
    result=ids.measure(geometry,[1,1,1,0],[0,2,2,999],10,.01)
    assert result['integer_ids_valid'] and result['structural_pixels']==1 and result['leaf_pixels']==2
    assert result['distinct_leaf_count']==1 and result['leaf_index_preview']==[1]
    assert result['observed_leaf_indices_sha256']==botany.digest([1])
    a=[1]*7+[float('nan'),.5];g={'channels':{'TreeCapture.Combined.A':a}}
    result=ids.measure(g,[1,1,1,1,0,float('inf'),.5,1,1],[1.2,-1,11,float('nan'),1,1,1,1,1],10,.01)
    assert not result['integer_ids_valid'] and result['noninteger_ids']==1 and result['out_of_range_ids']==2
    assert result['nonfinite_ids']==1 and result['invalid_surface_weight']==3 and result['invalid_alpha']==1 and result['nonbinary_alpha']==1
    with pytest.raises(ValueError,match='lengths'):ids.measure(geometry,[],[],10,.01)
    def stop():raise InterruptedError('cancel')
    with pytest.raises(InterruptedError):ids.measure(geometry,[1]*4,[0]*4,10,.01,cancelled=stop)
    preview=ids.measure({'channels':{'TreeCapture.Combined.A':[1]*32}},[1]*32,list(range(1,33)),32,.01)
    assert preview['distinct_leaf_count']==32 and len(preview['leaf_index_preview'])==16
