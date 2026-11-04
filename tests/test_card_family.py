"""One-sided deterministic angular policy and public typed workflow admission."""
import asyncio
import math
import pytest
from fastmcp import Client
from mcpblender import card_family as api
from mcpblender.card_family_contracts import Source,Direction
from mcpblender.config import Config
from mcpblender.server import build_server


def test_canonical_nearest_and_reverse_refusal():
    normals=api.DIRECTIONS
    for name,normal in normals.items():
        result=api.choose(normals,[normal],30)
        assert result['supported'] and result['selected_view']==name
    assert not api.choose(normals,[(0,0,-1)],30)['supported']
    assert not api.choose(normals,[(-1,1,-1)],80)['supported']
    assert api.choose(dict(reversed(list(normals.items()))),[(1,0,1)],60)['selected_view']=='TOP'
    assert not api.choose(normals,[(1,0,1)],30)['supported']
    assert api.unit([1e308,1e308,0])==pytest.approx([2**-.5,2**-.5,0])


def test_perspective_edges_must_fit_same_cone():
    normal={'TOP':(0,0,1)}
    angle=math.radians(35)
    result=api.choose(normal,[(0,0,1),(math.sin(angle),0,math.cos(angle))],30)
    assert result['nearest_view']=='TOP' and result['selected_view'] is None
    assert result['candidates'][0]['max_angle_degrees']==pytest.approx(35)
    for directions,limit in (([],30),([(0,0,0)],30),([(0,0,float('nan'))],30),([(0,0,1)],90)):
        with pytest.raises(ValueError):api.choose(normal,directions,limit)


def test_contracts_paths_and_readonly_discovery(tmp_path):
    entries=[{'view':'TOP','object':'top'}]
    assert Source(directory='bundle',entries=entries).max_angle_degrees==30
    for extra in ({'entries':entries*2},{'max_angle_degrees':90},{'max_texture_bytes':0},{'max_total_triangles':10000}):
        with pytest.raises(ValueError):Source.model_validate({'directory':'bundle','entries':entries}|extra)
    for extra in ({},{'camera':'Camera','view_direction':[0,0,1]},{'view_direction':[0,0,0]}):
        with pytest.raises(ValueError):Direction(family_collection='Family',**extra)
    config=Config();config.stdio.library_root=str(tmp_path);config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False
    server,state=build_server(config)
    with pytest.raises(ValueError,match='library_root'):state.prepare('inspect_foliage_card_family_source',{'directory':'../outside','entries':entries})
    assert state.input_paths('create_foliage_card_family',{'directory':'bundle'})==['bundle']
    assert state.input_paths('validate_foliage_card_family_bundle',{'directory':'bundle'})==['bundle']
    with pytest.raises(ValueError,match='library_root'):state.prepare('validate_foliage_card_family_bundle',{'directory':'../outside'})
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_foliage_card_family_source','inspect_foliage_card_family','inspect_foliage_card_family_selection','validate_foliage_card_family_bundle'}<=names
            assert not names&{'create_foliage_card_family','select_foliage_card_family_view','remove_foliage_card_family','export_foliage_card_family'}
    asyncio.run(run())
