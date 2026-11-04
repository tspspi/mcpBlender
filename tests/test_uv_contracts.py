"""UV geometry controls and guarded/read-only MCP contract checks."""
import asyncio

from fastmcp import Client
import pytest

from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.uv_contracts import UVLayout, UVUnwrap, UVSeams, UVDensity, UVPack, UVSecondary
from mcpblender.uv_math import triangle_overlap,inset_tile


def test_overlap_positive_area_and_boundary_contacts():
    tri=[(0,0),(1,0),(0,1)]
    assert triangle_overlap(tri,tri)==pytest.approx(.5)
    assert triangle_overlap(tri,list(reversed(tri)))==pytest.approx(.5)
    assert triangle_overlap(tri,[(1,0),(1,1),(0,1)])==pytest.approx(0)
    assert triangle_overlap(tri,[(.5,0),(1.5,0),(.5,1)])==pytest.approx(.125)
    assert triangle_overlap(tri,[(2,0),(3,0),(2,1)])==0
    assert triangle_overlap(tri,[(.2,.2)]*3)==0
    assert triangle_overlap(tri,[(.1,.1),(.2,.2),(.3,.3)])==0


def test_uv_guards_limits_and_readonly_discovery(tmp_path):
    base={'name':'Box','expected_uv':'a'*64}
    for cls,values in ((UVLayout,{'texture_width':0}), (UVUnwrap,{'margin':float('nan')}),
                       (UVDensity,{'pixels_per_unit':0}), (UVSeams,{'edges':{'indices':[0,0]}})):
        with pytest.raises(ValueError):cls.model_validate(({'name':'Box'} if cls is UVLayout else base)|values)
    with pytest.raises(ValueError):UVUnwrap(name='Box',expected_uv='stale')
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False
    config.bridge.socket_path=str(tmp_path/'private/socket')
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_uv_layout' in names
            assert not names & {'unwrap_uv_mesh','pack_uv_islands','set_uv_seams','normalize_uv_density','activate_uv_map','create_secondary_uv'}
    asyncio.run(run())
    assert not (tmp_path/'private/socket').exists()


def test_secondary_projection_limits():
    base={'name':'Box','expected_uv':'a'*64}
    assert UVSecondary(**base).uv_map=='UV2'
    for extra in ({'angle_limit_degrees':0},{'angle_limit_degrees':90},{'angle_limit_degrees':float('nan')},
                  {'scale':False},{'texture_width':8},{'tile_padding_pixels':-1}):
        with pytest.raises(ValueError):UVSecondary(**base,**extra)


def test_tile_border_uniform_fit_translation_and_refusal():
    from mcpblender.vegetation_bake_contracts import Source
    base={'name':'Box','expected_uv':'a'*64}
    for extra in ({'tile_padding_pixels':-1},{'tile_padding_pixels':float('nan')},{'texture_width':16,'tile_padding_pixels':8}):
        with pytest.raises(ValueError):UVPack(**base,**extra)
    values=[0,0,1,0,1,1,0,1]
    padded=inset_tile(values,128,64,8,True)
    assert min(padded[0::2])*128>=8 and min(padded[1::2])*64>=8
    assert (1-max(padded[0::2]))*128>=8 and (1-max(padded[1::2]))*64>=8
    assert padded[2]-padded[0]==pytest.approx(padded[5]-padded[1])
    assert values==[0,0,1,0,1,1,0,1]
    with pytest.raises(ValueError,match='without scaling'):inset_tile(values,128,64,8,False)
    translated=inset_tile([10,20,10.25,20,10.25,20.25],128,64,8,False)
    assert translated[2]-translated[0]==.25 and translated[5]-translated[1]==.25
    assert inset_tile(values,128,64,0,False)==values
    with pytest.raises(ValueError,match='NEW'):Source(collection='Tree',uv_strategy='EXISTING',tile_padding_pixels=4)
    with pytest.raises(ValueError,match='interior'):Source(collection='Tree',texture_width=32,tile_padding_pixels=16)
