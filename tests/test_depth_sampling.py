"""Declared output grids preserve capture data and world geometry."""
import copy
import pytest
from mcpblender import depth_tiles
from mcpblender.depth_asset_contracts import Settings
from test_moment_depth import source


@pytest.mark.parametrize('mode',['FLAT','ADAPTIVE_NORMAL','MOMENT_FACETS'])
def test_output_grid_equals_explicit_capture_grid(mode):
    d,m,v=source();before=copy.deepcopy(d)
    manual=depth_tiles.geometry(d,m,v,{'geometry_mode':mode,'tile_pixels':2})
    declared=depth_tiles.geometry(d,m,v,{'geometry_mode':mode,'tile_pixels':1,'output_resolution':1})
    assert d==before
    for field in ('vertices','uvs','faces'):assert declared[field]==manual[field]
    report=declared['report'];sampling=report['output_sampling']
    assert sampling['capture_resolution']==2 and sampling['output_resolution']==1
    assert sampling['capture_texels_per_output_pixel']==2
    assert sampling['base_tile_output_pixels']==1 and sampling['base_tile_capture_pixels']==2
    assert report['options']['tile_pixels']==1 and report['options']['output_resolution']==1
    assert report['geometry_sha256']!=manual['report']['geometry_sha256']
    if mode=='MOMENT_FACETS':assert report['projection_reference_resolution']==1


def test_sampling_budget_does_not_shrink_with_declared_output():
    p=depth_tiles.options({'output_resolution':64,'tile_pixels':4})
    report=depth_tiles.output_sampling(256,p)
    assert report['base_tile_capture_pixels']==16 and p['tile_pixels']==4
    assert report['capture_resolution']**2==65536
    assert report['edge_radius_pixel_space']=='CAPTURE_DATA'
    assert depth_tiles.output_sampling(256,depth_tiles.options({})) is None


@pytest.mark.parametrize('width,output,tile',[(128,256,4),(128,48,4),(96,32,4),(128,1,1),(128,2,4)])
def test_unsupported_ratios_or_effective_tiles_refuse(width,output,tile):
    with pytest.raises(ValueError):depth_tiles.output_sampling(width,depth_tiles.options({'output_resolution':output,'tile_pixels':tile}))


@pytest.mark.parametrize('value',[0,1025,True,32.5])
def test_invalid_output_contract(value):
    with pytest.raises(ValueError):Settings(output_resolution=value)
    with pytest.raises(ValueError):depth_tiles.options({'output_resolution':value})
