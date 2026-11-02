"""Rest planning, hierarchy safety and typed capability visibility."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.rest_contracts import EditRest
from mcpblender.rest_math import plan_rest


def row(name,head,tail,parent=None,connected=False):
    return {'name':name,'head':head,'tail':tail,'parent':parent,'connected':connected,'roll_degrees':0,'deform':True,'inherit_scale':'FULL','inherit_rotation':True,'local_location':True}


def test_plan_connections_hierarchy_and_contract_guards():
    original={'Root':row('Root',[0,0,0],[0,0,1]),'Arm':row('Arm',[0,0,1],[0,0,3],'Root',True)}
    result,order=plan_rest(original,[{'name':'Root','tail':[0,0,2]}],[])
    assert order==['Root','Arm'] and result['Arm']['head']==[0,0,2] and original['Arm']['head']==[0,0,1]
    for patches in ([{'name':'Root','parent':'Arm'}],[{'name':'Arm','parent':''}],[{'name':'Missing','deform':False}],
                    [{'name':'Root','tail':[0,0,3]}],[{'name':'Arm','head':[1,0,1]}]):
        with pytest.raises(ValueError):plan_rest(original,patches,[])
    assert plan_rest(original,[{'name':'Arm','parent':'','connected':False}],[])[0]['Arm']['parent'] is None
    for head,tail in (([1e8,0,0],[1e8+.01,0,0]),([1e308,0,0],[1e308,1,0])):
        with pytest.raises(ValueError):plan_rest(original,[{'name':'Root','head':head,'tail':tail}],[])
    assert plan_rest(original,[{'name':'Root','roll_degrees':450}],[])[0]['Root']['roll_degrees']==90
    base={'name':'Rig','expected_rest':'a'*64}
    for patch in ({},{'add_bones':[{'name':'ä'*32,'head':[0,0,0],'tail':[0,0,1]}]},{'bones':[{'name':'Root'}]},{'bones':[{'name':'Root','head':[float('nan'),0,0]}]},
                  {'bones':[{'name':'Root','deform':False}],'add_bones':[{'name':'Root','head':[0,0,0],'tail':[0,0,1]}]}):
        with pytest.raises(ValueError):EditRest.model_validate(base|patch)


def test_readonly_rest_visibility(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_armature_rest' in names and 'edit_armature_rest' not in names
    asyncio.run(run())
