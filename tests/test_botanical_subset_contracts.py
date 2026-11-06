"""Strict capture selection, policy discovery and contained source reads."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.botanical_subset_contracts import Source,Create
from mcpblender.server import build_server,State


def test_subset_selection_limits():
    assert Source(directory='capture').structure_render_role is None
    assert Source(directory='capture',render_role='SECONDARY',structure_render_role='ALL_RAYS').structure_render_role=='ALL_RAYS'
    with pytest.raises(ValueError,match='include_structure'):Source(directory='capture',include_structure=False,structure_render_role='ALL_RAYS')
    assert Source(directory='capture').selection=='UNOBSERVED'
    for patch in ({'views':['FRONT','FRONT']},{'views':[]},{'selection':'HIDDEN'},{'max_total_pixels':True},{'alpha_threshold':0},{'render_role':'CAMERA'}):
        with pytest.raises(ValueError):Source(directory='capture',**patch)
    with pytest.raises(ValueError):Create(directory='capture',subset_collection='Copy')


def test_subset_policy_and_paths(tmp_path):
    cfg=Config();cfg.bridge.socket_path=str(tmp_path/'sock');cfg.stdio.library_root=str(tmp_path/'library');cfg.stdio.allow_scene_edit=False
    server,state=build_server(cfg);(tmp_path/'library/capture').mkdir(parents=True)
    args=Source(directory='capture').model_dump()
    prepared=state.prepare('inspect_botanical_subset_source',args)
    assert prepared['directory']==str(tmp_path/'library/capture')
    assert State.input_paths('inspect_botanical_subset_source',prepared)==[prepared['directory']]
    with pytest.raises(ValueError):state.prepare('inspect_botanical_subset_source',args|{'directory':'../escape'})
    async def run():
        async with Client(server) as client:
            tools={t.name:t for t in await client.list_tools()}
            assert {'inspect_botanical_subset_source','inspect_botanical_subset'}<=tools.keys()
            assert 'create_botanical_subset' not in tools and 'remove_botanical_subset' not in tools
            assert tools['inspect_botanical_subset_source'].input_schema['properties']['wait']['default'] is False
    asyncio.run(run())


def test_optional_template_reduction_has_explicit_bounded_policy():
    assert Source(directory='capture').template_reduction is None
    policy=Source(directory='capture',template_reduction={}).template_reduction
    assert policy.triangle_budget==32 and policy.max_relative_error==.02
    for patch in ({'triangle_budget':True},{'triangle_budget':15},{'triangle_budget':513},{'max_relative_error':0},{'max_relative_error':float('nan')},{'max_area_relative_error':-1},{'error_samples':4097},{'transfer_normals':False}):
        with pytest.raises(ValueError):Source(directory='capture',template_reduction=patch)


def test_blade_card_policy_and_nested_library_paths(tmp_path):
    cards={'bake_collection':'Bake','expected_preparation':'a'*64,'entries':[{'asset':'leaf-0','directory':'blade'}]}
    assert Source(directory='capture').blade_cards is None
    assert Source(directory='capture',blade_cards=cards).blade_cards.entries[0].asset=='leaf-0'
    with pytest.raises(ValueError,match='Choose blade_cards'):
        Source(directory='capture',blade_cards=cards,template_reduction={})
    for patch in ({'max_bytes':True},{'entries':cards['entries']*2},{'max_texture_bytes':0}):
        with pytest.raises(ValueError):Source(directory='capture',blade_cards=cards|patch)
    cfg=Config();cfg.stdio.library_root=str(tmp_path/'library');_,state=build_server(cfg)
    for name in ('capture','blade'):(tmp_path/'library'/name).mkdir(parents=True)
    params=state.prepare('inspect_botanical_subset_source',Source(directory='capture',blade_cards=cards).model_dump())
    assert State.input_paths('inspect_botanical_subset_source',params)==[str(tmp_path/'library/capture'),str(tmp_path/'library/blade')]
    with pytest.raises(ValueError):state.prepare('inspect_botanical_subset_source',Source(directory='capture',blade_cards=cards|{'entries':[{'asset':'leaf-0','directory':'../escape'}]}).model_dump())
    aliases=cards|{'entries':[{'asset':'leaf-0','directory':'blade'},{'asset':'leaf-1','directory':'blade/.'}]}
    with pytest.raises(ValueError,match='distinctly'):
        state.prepare('inspect_botanical_subset_source',Source(directory='capture',blade_cards=aliases).model_dump())
