"""Typed quality budgets, long-operation discovery and read-only policy."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.vegetation_lod_contracts import Source


def test_typed_lod_contracts_and_readonly_policy(tmp_path):
    for patch in ({'levels':[]},{'levels':[{'leaf_budget':True}]},{'levels':[{'leaf_budget':20},{'leaf_budget':30}]},{'levels':[{'leaf_budget':20,'max_coverage_loss':float('nan')}]},{'views':['TOP','TOP']}):
        with pytest.raises(ValueError):Source.model_validate({'collection':'Oak','levels':[{'leaf_budget':20}]}|patch)
    cfg=Config();cfg.stdio.library_root=str(tmp_path);cfg.stdio.allow_scene_edit=False;cfg.stdio.allow_library_write=False;cfg.stdio.allow_code_execution=False
    server,_=build_server(cfg)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_botanical_lod_source','inspect_botanical_lods','validate_botanical_lod_bundle'}<=names
            assert 'export_botanical_lods' not in names
            assert not {'create_botanical_lods','activate_botanical_lod','remove_botanical_lods'}&names
    asyncio.run(run())
