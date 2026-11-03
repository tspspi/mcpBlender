"""Axis anchors and solver pivots retain distinct canonical meanings."""
import pytest
from mcpblender import botany,vegetation_interchange as schema


def test_branch_semantic_mapping_retains_hierarchy_and_two_anchor_meanings():
    model=botany.generate({'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1})
    index=next(i for i,b in enumerate(model['branches']) if b['anchor']!=b['start'])
    branch=model['branches'][index];fields=schema.branch_fields(model,[branch['start']],[index])
    assert fields['wind_axis_anchor']==[branch['anchor']]
    assert fields['wind_segment_pivot']==[branch['start']]
    assert model['branches'][fields['wind_parent_index'][0]]['id']==branch['parent_id']
    assert fields['wind_phase']==[branch['phase']] and fields['wind_stiffness']==[branch['stiffness']]
    assert fields['wind_weight']==[min(1,max(0,branch['start'][2]/model['recipe']['height']))]
    with pytest.raises(ValueError):schema.branch_fields(model,[],[0])
    with pytest.raises(ValueError):schema.branch_fields(model,[[0,0,0]],[-1])
