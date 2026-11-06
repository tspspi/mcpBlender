"""Component selection uses validated identity, not averaged material IDs."""
from copy import deepcopy
import hashlib
import pytest
from mcpblender import component_ids as ids,botany,depth_tiles
from mcpblender.depth_asset_contracts import Source,Layer
from test_component_ids import fields
from test_depth_tiles import fixture


def contract():return ids.contract(fields(),2,'Points','Instances',botany.digest([0,1]))


def test_component_filter_contracts_are_explicit_and_default_to_all():
    assert Source(directory='capture',view='FRONT').component_filter=='ALL'
    assert Source(directory='capture',view='FRONT',component_filter='LEAVES').component_filter=='LEAVES'
    assert Layer(view='BACK',component_filter='STRUCTURE').component_filter=='STRUCTURE'
    with pytest.raises(ValueError):Source(directory='capture',view='FRONT',component_filter='MATERIAL')


@pytest.mark.parametrize('mode,expected',[('LEAVES',[0,1,1,0]),('STRUCTURE',[1,0,0,1])])
def test_native_components_partition_geometry_without_changing_source_data(mode,expected):
    d,m,v=fixture();before=deepcopy(d)
    mask,report=ids.filter_mask(d,[1]*4,[0,1,2,0],contract(),mode,.001)
    assert list(mask)==expected and report['selected_pixels']==2 and report['excluded_covered_pixels']==2
    assert report['source_components_sha256']==contract()['components_sha256']
    assert report['mask_sha256']==hashlib.sha256(bytes(expected)).hexdigest()
    selected=d|{'channels':d['channels']|{'TreeCapture.Combined.A':[a*b for a,b in zip(d['channels']['TreeCapture.Combined.A'],mask)]}}
    g=depth_tiles.geometry(selected,m,v,{'tile_pixels':1})
    assert g['report']['triangles']==4 and d==before


@pytest.mark.parametrize('alpha,weights,values,message',[
    ([1,1,1,-.1],[1]*4,[0,1,2,0],'coverage'),
    ([1,1,1,.5],[1]*4,[0,1,2,0],'one-sample'),
    ([1]*4,[1,1,0,1],[0,1,2,0],'weight'),
    ([1]*4,[1]*4,[0,1,2.5,0],'integer'),
    ([1]*4,[1]*4,[0,1,3,0],'range'),
    ([1]*4,[1]*4,[0,1,float('nan'),0],'finite'),
])
def test_component_filter_refuses_uncertain_covered_observations(alpha,weights,values,message):
    d,_,_=fixture();d['channels']['TreeCapture.Combined.A']=alpha
    with pytest.raises(ValueError,match=message):ids.filter_mask(d,weights,values,contract(),'LEAVES',.001)


def test_component_filter_ignores_background_but_pins_contract_and_cancellation():
    d,_,_=fixture();d['channels']['TreeCapture.Combined.A'][3]=0
    mask,report=ids.filter_mask(d,[1,1,1,0],[0,1,2,float('nan')],contract(),'LEAVES',.001)
    assert list(mask)==[0,1,1,0] and report['excluded_covered_pixels']==1
    bad=contract()|{'leaf_count':1}
    with pytest.raises(ValueError,match='contract'):ids.filter_mask(d,[1]*4,[0,1,2,0],bad,'LEAVES',.001)
    with pytest.raises(ValueError,match='lengths'):ids.filter_mask(d,[],[],contract(),'LEAVES',.001)
    def stop():raise InterruptedError('cancel')
    with pytest.raises(InterruptedError):ids.filter_mask(d,[1]*4,[0,1,2,0],contract(),'LEAVES',.001,cancelled=stop)
