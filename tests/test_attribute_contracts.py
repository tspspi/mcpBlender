"""Numeric value/selection contracts and discovery permissions."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.attribute_contracts import Create,Update,Ramp
from mcpblender.attribute_values import row,safe_name

def test_numeric_storage_limits_and_selection_contracts():
    assert row('FLOAT_VECTOR',[1,-2,3])==[1.,-2.,3.]
    assert row('INT',-2147483648)==-2147483648 and row('BOOLEAN',False) is False
    for kind,value in [('INT',2147483648),('INT',1.),('INT',True),('BOOLEAN',1),('FLOAT',float('nan')),('FLOAT',1e39),('FLOAT_VECTOR',[0,1]),('FLOAT_COLOR',[-1,0,0,1])]:
        with pytest.raises(ValueError):row(kind,value)
    for name in ('.position','a'*64,'bad\nname',' name'):
        with pytest.raises(ValueError):safe_name(name)
    base={'name':'Mesh','attribute':'weight','expected_attributes':'a'*64}
    assert Create.model_validate(base|{'data_type':'FLOAT','value':0}).domain=='POINT'
    for patch in ({},{'value':0,'values':[1]},{'value':0,'indices':[1,1]},{'values':[1],'indices':[0,1]},{'value':0,'offset':1}):
        with pytest.raises(ValueError):Update.model_validate(base|patch)
    with pytest.raises(ValueError):Ramp.model_validate(base|{'input_min':0})
    with pytest.raises(ValueError):Create.model_validate(base|{'attribute':'.hidden','data_type':'FLOAT','value':0})

def test_readonly_attribute_discovery(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path);config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_mesh_attributes','inspect_attribute_export','validate_attribute_bundle'}<=names
            assert 'export_attribute_bundle' not in names
            assert 'inspect_mesh_attributes' in names
            assert not {'create_mesh_attribute','set_mesh_attribute_values','ramp_mesh_attribute','remove_mesh_attribute'}&names
    asyncio.run(run())
