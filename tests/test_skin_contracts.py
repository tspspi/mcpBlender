"""Skin contracts, policy visibility and locked influence math."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.skin_contracts import SetWeights, RepairSettings, MirrorWeights
from mcpblender.skin_math import clean_weights


def test_contracts_and_locked_budget():
    base={'name':'Skin','expected_weights':'a'*64}
    assert SetWeights.model_validate(base|{'weights':[{'vertex':0,'weights':{}}]}).respect_locks
    for weights in ([{'vertex':True,'weights':{'Root':1}}], [{'vertex':0,'weights':{'Root':float('nan')}}],
                    [{'vertex':0,'weights':{}},{'vertex':0,'weights':{}}]):
        with pytest.raises(ValueError):SetWeights.model_validate(base|{'weights':weights})
    for patch in ({'vertices':[1,1]},{'unweighted':'FALLBACK'},{'fallback_bone':'Root'},{'max_influences':0}):
        with pytest.raises(ValueError):RepairSettings.model_validate(base|patch)
    with pytest.raises(ValueError):MirrorWeights.model_validate(base|{'bone_pairs':[{'left':'A','right':'A'}]})
    assert clean_weights({'Locked':.25,'A':.2,'B':.1},{'Locked'},maximum=2)==pytest.approx({'Locked':.25,'A':.75})
    assert clean_weights({'A':float('nan'),'B':-.2},set(),unweighted='NEAREST',fallback='C')=={'C':1}
    assert clean_weights({},set(),unweighted='KEEP')=={}
    assert clean_weights({'A':1},set(),unweighted='NEAREST',fallback=lambda:pytest.fail('Unexpected nearest search'))=={'A':1}
    with pytest.raises(ValueError):clean_weights({'A':.7,'B':.7},{'A','B'})
    with pytest.raises(ValueError):clean_weights({'A':.3},{'A'},maximum=1,unweighted='FALLBACK',fallback='B')


def test_readonly_visibility(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert 'inspect_skin_weights' in names
            assert not {'set_skin_weights','repair_skin_weights','smooth_skin_weights','mirror_skin_weights','configure_skin_binding'} & names
    asyncio.run(run())
