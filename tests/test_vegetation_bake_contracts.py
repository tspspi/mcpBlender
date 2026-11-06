"""Structured source selection and policy-controlled discovery."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.vegetation_bake_contracts import Source


def test_source_selection_and_limits():
    with pytest.raises(ValueError):Source()
    with pytest.raises(ValueError):Source(collection='Tree',lod_collection='Lods')
    with pytest.raises(ValueError):Source(collection='Tree',assets=['wood','wood'])
    with pytest.raises(ValueError):Source(collection='Tree',margin=0)
    assert Source(collection='Tree').missing_uv_policy=='REFUSE'
    assert Source(collection='Tree').uv_strategy=='NEW'
    with pytest.raises(ValueError):Source(collection='Tree',uv_strategy='OVERWRITE')


def test_readonly_discovery(tmp_path):
    config=Config();config.stdio.allow_scene_edit=False;config.stdio.library_root=str(tmp_path)
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_vegetation_bake_source','inspect_vegetation_bake'}<=names
            assert not {'prepare_vegetation_bake','remove_vegetation_bake','refresh_vegetation_bake'}&names
    asyncio.run(run())


def test_blade_card_policy():
    assert Source(collection='Tree').blade_cards is None
    p=Source(collection='Tree',blade_cards={})
    assert p.blade_cards.resolution==128 and p.blade_cards.padding==.02
    for policy in ({'resolution':True},{'resolution':31},{'resolution':257},
                   {'padding':-.01},{'padding':.26},{'standoff_m':0},
                   {'standoff_m':float('nan')},{'extra':True}):
        with pytest.raises(ValueError):Source(collection='Tree',blade_cards=policy)
    with pytest.raises(ValueError,match='NEW'):
        Source(collection='Tree',blade_cards={},uv_strategy='EXISTING')
    with pytest.raises(ValueError,match='chart_layout'):
        Source(collection='Tree',blade_cards={},chart_layout={'allow_stretch':True})
