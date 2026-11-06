"""Bounds and immutable sampling request/source/output associations."""
from copy import deepcopy
import pytest
from mcpblender.render_sampling_contracts import Settings
from mcpblender import render_sampling as schema


def test_sampling_patch_bounds():
    for patch in ({},{'seed':True},{'adaptive_threshold':False},{'filter_width':float('nan')},{'sampling_pattern':'NOPE'},{'sample_subset_length':0},{'samples':65537},{'transparent_max_bounces':1025}):
        with pytest.raises(ValueError):Settings(**patch)
    assert Settings(seed=0,use_sample_subset=False).seed==0


def test_sampling_witness_digest_and_request_binding():
    settings={k:0 for k in schema.KEYS};settings.update(samples=64,sample_subset_length=64,sampling_pattern='AUTOMATIC',use_layer_samples='IGNORE')
    profile=schema.record('CYCLES',settings,[{'name':'Layer','enabled':True,'samples':0,'use_denoising':False}],[],{'device':'GPU','threads_mode':'AUTO','threads':4})
    job={'engine':'CYCLES','samples':8,'threads':2,'expected_sampling':profile['sampling_sha256']};contract={'format':'GUARDED_CYCLES_SAMPLING_V1','source':profile}
    result=schema.expected(contract,job);assert result['settings']['samples']==8 and result['execution']=={'device':'CPU','threads_mode':'FIXED','threads':2}
    assert profile['settings']['samples']==64
    bad=deepcopy(profile);bad['settings']['seed']=2
    with pytest.raises(ValueError,match='digest'):schema.validate(bad)
    with pytest.raises(ValueError,match='binding'):schema.expected(contract,job|{'expected_sampling':'0'*64})



def test_sample_windows_honor_layer_policy_and_subset_bounds():
    settings={'samples':64,'use_layer_samples':'USE','use_sample_subset':True,'sample_offset':16,'sample_subset_length':32}
    layers=[{'name':'L','enabled':True,'samples':8}]
    assert schema.windows(settings,layers)[0]['sample_ceiling']==0
    assert schema.windows(settings|{'use_layer_samples':'IGNORE'},layers)[0]['sample_ceiling']==32
    layers[0]['samples']=128
    assert schema.windows(settings|{'sample_offset':80},layers)[0]['sample_ceiling']==32
    assert schema.windows(settings|{'sample_offset':80,'use_layer_samples':'BOUNDED'},layers)[0]['sample_ceiling']==0



def test_sampling_tool_policy_is_read_only_when_edits_disabled(tmp_path):
    import asyncio
    from fastmcp import Client
    from mcpblender.config import Config
    from mcpblender.server import build_server
    cfg=Config();cfg.stdio.allow_scene_edit=False;cfg.stdio.library_root=str(tmp_path);cfg.bridge.socket_path=str(tmp_path/'socket');server,_=build_server(cfg)
    async def run():
        async with Client(server) as client:
            tools={t.name for t in await client.list_tools()}
            assert 'inspect_render_sampling' in tools and 'configure_render_sampling' not in tools
    asyncio.run(run())
