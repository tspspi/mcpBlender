"""Explicit geometric plane fitting with unchanged native shading maps."""
from array import array
from copy import deepcopy
import math
import pytest
from mcpblender import geometric_normals,depth_tiles as tiles,depth_accuracy
from mcpblender.depth_asset_contracts import Settings
from test_depth_tiles import fixture


def source():
    d,m,v=fixture();materials=[{'material':'Surface','id':1}]
    m['material_fields']={'materials':materials,'geometric_normals':geometric_normals.contract(materials)}
    length=math.sqrt(1+.3**2+.2**2)
    for name,value in zip(geometric_normals.channels(),(.3,.2,1)):
        d['channels'][name]=array('f',[value/length]*4)
    d['channels']['TreeCapture.Depth.Z']=array('f',[5+.3*x+.2*y for y in (.5,-.5) for x in (-.5,.5)])
    return d,m,v


def test_selector_changes_planes_preserves_raw_normal_maps_and_pins_contract():
    d,m,v=source();before=deepcopy((d,m,v));settings={'geometry_mode':'ADAPTIVE_NORMAL','tile_pixels':2,'max_triangles':2}
    legacy=tiles.geometry(d,m,v,settings)
    assert tiles.geometry(d,m,v,settings|{'plane_normal_source':'SHADING_PASS'})==legacy
    material={'channels':{'TreeCapture.MCP_SurfaceWeight.X':array('f',[1]*4),'TreeCapture.MCP_Roughness.X':array('f',[.5]*4)}}
    old_map=tiles.texture_map(material,d,m,v,{},'normal_roughness')
    new=tiles.geometry(d,m,v,settings|{'plane_normal_source':'GEOMETRIC_AOV'})
    assert depth_accuracy.measure(d,m,v,legacy,.001)['maximum_error_m']>.1
    assert depth_accuracy.measure(d,m,v,new,.001)['maximum_error_m']<1e-5
    assert new['report']['geometry_sha256']!=legacy['report']['geometry_sha256']
    assert new['report']['plane_normal_source']['normals_sha256']==m['material_fields']['geometric_normals']['normals_sha256']
    assert tiles.texture_map(material,d,m,v,{},'normal_roughness')==old_map
    assert (d,m,v)==before
    joint=tiles.geometry(d,m,v,settings|{'geometry_mode':'ADAPTIVE_DEPTH_NORMAL','depth_tolerance_m':.001,'plane_normal_source':'GEOMETRIC_AOV'})
    assert joint['report']['depth_residuals']['measured_tolerance_met']


def test_legacy_option_dicts_and_unsupported_geometry_refusals():
    default=tiles.options({});assert 'plane_normal_source' not in default
    assert tiles.options({'plane_normal_source':'SHADING_PASS'})==default
    assert tiles.options(Settings().model_dump())==default
    for mode in ('FLAT','MOMENT_FACETS'):
        with pytest.raises(ValueError,match='adaptive'):Settings(geometry_mode=mode,plane_normal_source='GEOMETRIC_AOV')
        with pytest.raises(ValueError,match='adaptive'):tiles.options({'geometry_mode':mode,'plane_normal_source':'GEOMETRIC_AOV'})
    with pytest.raises(ValueError,match='source'):tiles.options({'plane_normal_source':'AUTO'})


def test_missing_changed_nonfinite_or_mismatched_captured_normals_refuse():
    settings={'geometry_mode':'ADAPTIVE_NORMAL','plane_normal_source':'GEOMETRIC_AOV'}
    d,m,v=fixture()
    with pytest.raises(ValueError,match='recapture'):tiles.geometry(d,m,v,settings)
    d,m,v=source();m['material_fields']['geometric_normals']['normals_sha256']='0'*64
    with pytest.raises(ValueError,match='contract'):tiles.geometry(d,m,v,settings)
    d,m,v=source();d['channels'].pop(geometric_normals.channels()[0])
    with pytest.raises(ValueError,match='Missing'):tiles.geometry(d,m,v,settings)
    d,m,v=source();d['channels'][geometric_normals.channels()[0]]=array('f',[0])
    with pytest.raises(ValueError,match='length'):tiles.geometry(d,m,v,settings)
    d,m,v=source();d['channels'][geometric_normals.channels()[0]][0]=float('nan')
    with pytest.raises(ValueError,match='nonfinite'):tiles.geometry(d,m,v,settings)
    d,m,v=source()
    for name in geometric_normals.channels():d['channels'][name][0]=0
    with pytest.raises(ValueError,match='zero'):tiles.geometry(d,m,v,settings)
    def cancel():raise InterruptedError('cancelled')
    d,m,v=source()
    with pytest.raises(InterruptedError):tiles.geometry(d,m,v,settings,cancelled=cancel)
