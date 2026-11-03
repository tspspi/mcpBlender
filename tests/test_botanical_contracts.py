"""Botanical permissions, bounded element inspection and file boundary."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.botanical_contracts import Inspect,Recipe


def test_botanical_permissions_and_source_boundaries(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False
    server,state=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'botanical_species_catalog','plan_botanical_tree','inspect_botanical_tree','list_botanical_elements'}<=names
            assert not {'create_botanical_tree','regenerate_botanical_tree','remove_botanical_tree','export_botanical_model'}&names
    asyncio.run(run())
    with pytest.raises(ValueError):Inspect.model_validate({'collection':'Oak','limit':129})
    with pytest.raises(ValueError):Recipe.model_validate({'light_direction':[0,0,0]})
    with pytest.raises(ValueError,match='inside'):state.prepare('export_botanical_model',{'collection':'Oak','expected_tree':'a'*64,'path':'../outside.json'})
    with pytest.raises(ValueError,match='json'):state.prepare('export_botanical_model',{'collection':'Oak','expected_tree':'a'*64,'path':'model.blend'})
