"""Assembly authority, bounded inputs and discoverable read-only inspection."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.assembly_contracts import Create,Place,SourceInspection,InstanceInspection
from mcpblender.config import Config
from mcpblender.server import build_server


def test_assembly_inputs():
    source={'objects':['Part'],'collection':'Asset','expected_source':'a'*64}
    assert Create.model_validate(source).origin_mode=='BOUNDS_BOTTOM'
    for patch in ({'objects':['Part','Part']},{'origin_mode':'CUSTOM'},{'origin':[1,2,3]},{'origin_mode':'CUSTOM','origin':[float('nan'),0,0]}):
        with pytest.raises(ValueError):Create.model_validate(source|patch)
    placement={'name':'One','collection':'Asset','expected_asset':'a'*64}
    assert Place.model_validate(placement|{'scale':[-1,1,1]}).scale[0]==-1
    for scale in ([0,1,1],[1e7,1,1],[1,1,float('inf')]):
        with pytest.raises(ValueError):Place.model_validate(placement|{'scale':scale})
    with pytest.raises(ValueError):SourceInspection.model_validate({'objects':['Part'],'dependency_limit':257})
    with pytest.raises(ValueError):InstanceInspection.model_validate({'name':'One','leaf_limit':129})


def test_readonly_assembly_discovery(tmp_path):
    cfg=Config();cfg.stdio.library_root=str(tmp_path);cfg.stdio.allow_scene_edit=False
    server,_=build_server(cfg)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_asset_assembly_source','inspect_asset_assembly','inspect_asset_instance'}<=names
            assert not {'create_asset_assembly','place_asset_instance','set_asset_assembly_editing','remove_asset_instance'}&names
    asyncio.run(run())
