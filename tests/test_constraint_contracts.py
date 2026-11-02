"""Typed constraint boundaries and object/bone graph controls."""
import asyncio

from fastmcp import Client
import pytest

from mcpblender.animation_graph import validate_graph
from mcpblender.constraint_contracts import ConfigureConstraint,ConstraintSampling
from mcpblender.config import Config
from mcpblender.server import build_server


def test_constraint_values_and_readonly_discovery(tmp_path):
    base={'name':'Rig','bone':'Tip','constraint':'IK','expected_constraints':'a'*64}
    for settings in ({'type':'IK','target':{'name':'Control'},'chain_count':0},
                     {'type':'IK','target':{'name':'Control'},'pole_angle_degrees':181},
                     {'type':'COPY_LOCATION','target':{'name':'Control'},'influence':float('nan')},
                     {'type':'LIMIT_LOCATION','minimum':[2,0,0],'maximum':[1,1,1]},
                     {'type':'COPY_ROTATION','target':{'name':'Control'},'arbitrary':'code'},
                     {'type':'PYTHON','target':{'name':'Control'}}):
        with pytest.raises(ValueError):ConfigureConstraint.model_validate(base|{'settings':settings})
    with pytest.raises(ValueError):ConstraintSampling(name='Rig',frames=[1,1])
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_animation_constraints','sample_constraint_animation'}<=names
            assert not names & {'create_animation_control','configure_animation_constraint','remove_animation_constraint','move_animation_constraint','bake_constraint_animation'}
    asyncio.run(run())


def test_component_cycles_distinguish_rig_transform_and_ik_ancestors():
    rig={'name':'Rig','bones':{'Base':None,'Tip':'Base','Control':None},'constraints':[{'bone':'Tip','type':'IK','chain_count':2,'targets':[('Target',None)]}]}
    # A helper can safely inherit the rig object's transform.
    helper={'name':'Target','parent':('Rig',None)}
    validate_graph([rig,helper],[('Rig','Tip')])
    # Depending on any solved chain bone creates a cycle.
    for bone in ('Base','Tip'):
        with pytest.raises(ValueError,match='cycle'):
            validate_graph([rig,helper|{'parent':('Rig',bone)}],[('Rig','Tip')])
    # An independent control bone in the same rig is also valid.
    same=rig|{'constraints':[{'bone':'Tip','type':'IK','chain_count':2,'targets':[('Rig','Control')]}]}
    validate_graph([same],[('Rig','Tip')])
    # An unrelated bad/unsupported graph must not block the supported closure.
    unrelated={'name':'Other','constraints':[{'type':'SCRIPT','targets':[]}]}
    validate_graph([rig,helper,unrelated],[('Rig','Tip')])
    with pytest.raises(ValueError,match='Unsupported'):
        validate_graph([rig,helper|{'constraints':[{'type':'SCRIPT','targets':[]}]}],[('Rig','Tip')])


def test_graph_handles_diamonds_deep_chains_and_missing_targets():
    records=[{'name':'Root','constraints':[{'type':'COPY_LOCATION','targets':[('A',None),('B',None)]}]},
             {'name':'A','parent':('C',None)},{'name':'B','parent':('C',None)},{'name':'C'}]
    validate_graph(records,[('Root',None)])
    deep=[{'name':str(i),'parent':(str(i+1),None)} for i in range(1500)]+[{'name':'1500'}]
    validate_graph(deep,[('0',None)])
    with pytest.raises(ValueError,match='Missing'):validate_graph([{'name':'Root','parent':('Absent',None)}],[('Root',None)])


def test_visual_bake_range_and_names():
    from mcpblender.constraint_contracts import BakeAnimation
    base = {'name':'Rig','output_rig':'Baked','clip':'Motion','frame_start':1,'frame_end':9}
    assert BakeAnimation.model_validate(base).tolerance == .0001
    for changes in ({'frame_end':501}, {'frame_end':0}, {'frame_start':True}, {'tolerance':float('nan')},
                    {'meshes':[{'source':'Skin','output':'Baked'}]},
                    {'meshes':[{'source':'Skin','output':'A'},{'source':'Skin','output':'B'}]}):
        with pytest.raises(ValueError): BakeAnimation.model_validate(base|changes)
