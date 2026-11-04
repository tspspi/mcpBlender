"""Analytic geometry, explicit edge estimates, root-normal frames and work limits."""
from array import array
import pytest
from mcpblender import depth_tiles as tiles,capture_material_fields as fields


def fixture():
    data={'width':2,'height':2,'data_window':(0,0,1,1),'channels':{'TreeCapture.Combined.A':array('f',[1]*4),'TreeCapture.Depth.Z':array('f',[5]*4),**{'TreeCapture.Normal.'+axis:array('f',[float(axis=='Z')]*4) for axis in 'XYZ'}}}
    meta={'source_root_matrix_world':[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],'scene_unit_scale':1}
    view={'view':'FRONT','matrix_world':[[1,0,0,0],[0,1,0,0],[0,0,1,5],[0,0,0,1]],'ortho_scale':2,'clip_start':.1,'clip_end':10}
    return data,meta,view


def test_independent_plane_winding_uv_and_no_depth_bridges():
    d,m,v=fixture();g=tiles.geometry(d,m,v,{'tile_pixels':2})
    assert list(g['vertices'])==[-1,-1,0,1,-1,0,1,1,0,-1,1,0]
    assert list(g['uvs'])==[0,0,1,0,1,1,0,1]
    assert g['faces']==[(0,1,2,3)] and g['report']['triangles']==2
    # Disconnected cells do not interpolate a bridge between distinct depths.
    d['channels']['TreeCapture.Depth.Z']=array('f',[4,6,4,6]);g=tiles.geometry(d,m,v,{'tile_pixels':1})
    assert g['faces']==[tuple(range(i,i+4)) for i in range(0,16,4)]
    assert list(g['vertices'][2::3])==[1]*4+[-1]*4+[1]*4+[-1]*4
    assert g['report']['estimated_edge_tiles']==0
    assert tiles.geometry(d,m,v,{'tile_pixels':1})['report']['geometry_sha256']==g['report']['geometry_sha256']


def test_rotated_scaled_translated_source_and_world_normal_conversion():
    d,m,v=fixture();expected=tiles.geometry(d,m,v,{'tile_pixels':2})
    m['source_root_matrix_world']=[[0,0,2,4],[0,2,0,-3],[-2,0,0,1],[0,0,0,1]];m['scene_unit_scale']=.001
    v.update(matrix_world=[[0,0,1,14],[0,1,0,-3],[-1,0,0,1],[0,0,0,1]],ortho_scale=4,clip_end=30)
    d['channels']['TreeCapture.Depth.Z']=array('f',[10]*4)
    assert tiles.geometry(d,m,v,{'tile_pixels':2})['vertices']==expected['vertices']
    d['channels']['TreeCapture.Normal.X']=array('f',[.5]*4);d['channels']['TreeCapture.Normal.Z']=array('f',[0]*4)
    material={'channels':{'TreeCapture.MCP_SurfaceWeight.X':array('f',[.5]*4),'TreeCapture.MCP_Roughness.X':array('f',[.3]*4)}}
    pixels=tiles.texture_map(material,d,m,v,{},'normal_roughness')
    assert list(pixels)==pytest.approx([0,0,.5,.6]*4)


def test_edge_estimates_omissions_opaque_refusal_and_bounded_search():
    d,m,v=fixture();d['channels']['TreeCapture.Combined.A'][0]=.4;d['channels']['TreeCapture.Depth.Z'][0]=1e10
    with pytest.raises(ValueError,match='explicit edge policy'):tiles.geometry(d,m,v,{'tile_pixels':1,'edge_depth_policy':'REFUSE'})
    g=tiles.geometry(d,m,v,{'tile_pixels':1,'edge_depth_policy':'OMIT'})
    assert g['report']['omitted_tiles']==1 and g['report']['patches']==3
    g=tiles.geometry(d,m,v,{'tile_pixels':1,'edge_radius_pixels':1})
    assert g['report']['estimated_edge_tiles']==1 and g['report']['measured_tiles']==3
    assert g['patch_records'][0]['estimated'] and g['patch_records'][0]['witness_pixel']==[1,0]
    assert g['patch_records'][0]['witness_distance_pixels']==1
    with pytest.raises(ValueError,match='inside edge radius'):tiles.geometry(d,m,v,{'tile_pixels':1,'edge_radius_pixels':0})
    with pytest.raises(ValueError,match='search work budget'):tiles.geometry(d,m,v,{'tile_pixels':1,'max_search_work':1})
    d['channels']['TreeCapture.Combined.A'][0]=1
    with pytest.raises(ValueError,match='Opaque capture pixels'):tiles.geometry(d,m,v,{'tile_pixels':1})


def test_packing_preserves_data_channels_without_beauty_alpha_unweighting():
    d,m,v=fixture();d['channels']['TreeCapture.Combined.A']=array('f',[.2]*4)
    channels={name:array('f',[0]*4) for name in fields.channels()}
    channels['TreeCapture.MCP_SurfaceWeight.X']=array('f',[.5]*4)
    channels['TreeCapture.MCP_BaseColor.R']=array('f',[.1]*4)
    channels['TreeCapture.MCP_BaseColor.G']=array('f',[.15]*4)
    channels['TreeCapture.MCP_BaseColor.B']=array('f',[.2]*4)
    channels['TreeCapture.MCP_Alpha.X']=array('f',[.5]*4)
    material={'channels':channels}
    pixels=tiles.texture_map(material,d,m,v,{},'base_coverage')
    assert list(pixels)==pytest.approx([.2,.3,.4,.2]*4)
    all_components=[c for _,row in tiles.MAPS for c in row]
    assert len(all_components)==len(set(all_components))==24
    assert all(set(tiles.map_channels(name))<=set(fields.channels()) for name,_ in tiles.MAPS)
    assert len(tiles.map_channels('base_coverage'))==4
    for name,_ in tiles.MAPS:assert len(tiles.texture_map(material,d,m,v,{},name))==16
    channels['TreeCapture.MCP_Alpha.X'][0]=.25
    with pytest.raises(ValueError,match='opaque intrinsic shader alpha'):tiles.texture_map(material,d,m,v,{},'surface')
    channels['TreeCapture.MCP_SurfaceWeight.X'][0]=0
    with pytest.raises(ValueError,match='surface weight'):tiles.texture_map(material,d,m,v,{},'base_coverage')


def test_refusals_budgets_and_cancellation():
    d,m,v=fixture()
    for options in [{'tile_pixels':3},{'tile_pixels':True},{'alpha_threshold':float('nan')},{'max_search_work':0},{'extra':1}]:
        with pytest.raises(ValueError):tiles.geometry(d,m,v,options)
    with pytest.raises(ValueError,match='triangle budget'):tiles.geometry(d,m,v,{'tile_pixels':1,'max_triangles':2})
    d['channels']['TreeCapture.Combined.A'][0]=float('nan')
    with pytest.raises(ValueError,match='coverage'):tiles.geometry(d,m,v,{})
    d,m,v=fixture()
    material={'channels':{'TreeCapture.MCP_SurfaceWeight.X':array('f',[1]*4),'TreeCapture.MCP_Roughness.X':array('f',[.5]*4)}}
    for bad in (0.,float('nan')):
        d['channels']['TreeCapture.Normal.Z'][0]=bad
        with pytest.raises(ValueError,match='native normal'):tiles.texture_map(material,d,m,v,{},'normal_roughness')
    d,m,v=fixture();v['matrix_world'][0][0]=2
    with pytest.raises(ValueError,match='scale'):tiles.geometry(d,m,v,{})
    d,m,v=fixture()
    def stop():raise InterruptedError('cancelled')
    with pytest.raises(InterruptedError):tiles.geometry(d,m,v,{},cancelled=stop)
    d['width']=d['height']=1024;d['data_window']=(0,0,1023,1023)
    with pytest.raises(ValueError,match='texture budget'):tiles.texture_map({'channels':{}},d,m,v,{'max_texture_bytes':1024},'surface')
