"""Canopy recipe budgets, determinism, frontend permissions and surface defaults."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender import botanical_presets as presets,foliage
from mcpblender.botanical_preset_contracts import Plan,Create
from mcpblender.botanical_surface_contracts import Bark,Leaf
from mcpblender.config import Config
from mcpblender.server import build_server


def test_reference_canopy_recipe_and_geometry_sharing():
    assert presets.catalog()['presets'][0]['reference_seeds']==[1,2,3]
    assert presets.BARK==Bark().model_dump() and presets.LEAF==Leaf().model_dump()
    first=presets.plan(Plan().model_dump())[-1]
    second=presets.plan(Plan().model_dump())[-1]
    assert first['preset_sha256']==second['preset_sha256']
    assert first['tree_metrics']['height']==14 and first['foliage_metrics']['leaves']==92136
    assert first['foliage_metrics']['prototypes']==3
    assert first['triangles']['stored_with_shared_templates']==75048
    assert first['triangles']['expanded_with_leaves']==18133116
    assert first['lod_mask_estimates']['64']<256*1024**2<first['lod_mask_estimates']['128']
    assert first['export_hint']['max_instances']==92136


def test_budget_refuses_before_leaf_record_allocation(monkeypatch):
    def unexpected(*args,**kwargs):raise AssertionError('Budget refusal allocated leaf records')
    monkeypatch.setattr(foliage,'generate',unexpected)
    for patch in ({'max_leaves':1000},{'max_expanded_triangles':1000},{'max_expanded_triangles':18100000}):
        with pytest.raises(ValueError,match='budget'):presets.plan(Plan(**patch).model_dump())
    with pytest.raises(ValueError,match='Unknown'):presets.plan(Plan().model_dump()|{'preset':'Unknown'})


def test_preset_typed_limits_and_readonly_discovery(tmp_path):
    for patch in ({'seed':True},{'seed':-1},{'max_leaves':100001},{'max_expanded_triangles':30000001}):
        with pytest.raises(ValueError):Plan(**patch)
    with pytest.raises(ValueError):Create(collection='Tree',expected_preset='stale')
    cfg=Config();cfg.stdio.library_root=str(tmp_path);cfg.stdio.allow_scene_edit=False;cfg.stdio.allow_code_execution=False
    server,_=build_server(cfg)
    # Catalog is a Blender operation; avoid startup here and inspect discovery only.
    async def discover():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'botanical_asset_presets','plan_botanical_asset_preset'}<=names
            assert 'create_botanical_asset_preset' not in names
            definitions={t.name:(getattr(t,'input_schema',None) or t.inputSchema) for t in await client.list_tools()}
            assert definitions['plan_botanical_asset_preset']['properties']['wait']['default'] is False
    asyncio.run(discover())
    cfg.stdio.allow_scene_edit=True
    editable,_=build_server(cfg)
    async def edit_discovery():
        async with Client(editable) as client:
            definitions={t.name:(getattr(t,'input_schema',None) or t.inputSchema) for t in await client.list_tools()}
            assert definitions['create_botanical_asset_preset']['properties']['wait']['default'] is False
    asyncio.run(edit_discovery())
