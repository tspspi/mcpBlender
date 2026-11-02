"""Numeric driver expression and property/evaluated-transform graph controls."""
import asyncio

from fastmcp import Client
import pytest

from mcpblender.config import Config
from mcpblender.driver_contracts import DriverSettings, ScalarProperty
from mcpblender.driver_graph import validate_drivers
from mcpblender.server import build_server


def test_native_numeric_expression_boundary():
    variable={'kind':'PROPERTY','name':'bend','object':'Rig','property':'Bend'}
    for expression in ('sin(bend)*pi','clamp(bend,0,1)','bend if bend>0 else 0','min(bend,2)+cos(frame/10)'):
        assert DriverSettings(expression=expression,variables=[variable]).expression==expression
    for expression in ('__import__("os")','bend.__class__','[bend][0]','(x for x in [])','unknown+1','open(1)','sin(x=1)','"text"'):
        with pytest.raises(ValueError):DriverSettings(expression=expression,variables=[variable])
    with pytest.raises(ValueError):DriverSettings(expression='1'+' '*255)
    with pytest.raises(ValueError):DriverSettings(expression='9'*255)
    with pytest.raises(ValueError):DriverSettings(expression='1',variables=[variable,variable])
    with pytest.raises(ValueError):DriverSettings(expression='1',variables=[variable|{'name':'if'}])
    with pytest.raises(ValueError):ScalarProperty(name='Rig',property='mcpblender_internal',value=0)
    with pytest.raises(ValueError):ScalarProperty(name='Rig',property='Bend',value=2)


def test_property_graph_distinguishes_raw_controls_and_feedback():
    objects=[{'name':'Rig','bones':{'Tip':None}}]
    control=('RAW','OBJECT','Rig','["Bend"]',0)
    rotation=('RAW','OBJECT','Rig','pose.bones["Tip"].rotation_euler',0)
    rows=[{'node':rotation,'inputs':[control],'affects':[('Rig','Tip')]}]
    validate_drivers(objects,rows,rotation)
    rows.append({'node':control,'inputs':[('EVAL','Rig','Tip')],'affects':[]})
    with pytest.raises(ValueError,match='cycle'):validate_drivers(objects,rows,control)
    bad={'node':control,'inputs':[],'blocked':'unsupported','affects':[]}
    with pytest.raises(ValueError,match='unsupported'):validate_drivers(objects,[rows[0],bad],rotation)
    validate_drivers(objects,[{'node':rotation,'inputs':[],'affects':[]},bad],rotation)


def test_readonly_driver_inspection_only(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_animation_drivers' in names
            assert not {'configure_animation_driver','remove_animation_driver','set_animation_property'}&names
    asyncio.run(run())
