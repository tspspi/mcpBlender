"""Atlas placement invariants, memory known answers and API boundaries."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.atlas_layout import pack
from mcpblender.atlas_contracts import Plan
from mcpblender.config import Config
from mcpblender.server import build_server,State

def test_nonrotating_layout_memory_and_refusal():
    entries=[{'id':'b','width':32,'height':32,'maps':['BASE_COLOR','NORMAL']},{'id':'a','width':32,'height':64,'maps':['BASE_COLOR','NORMAL']}]
    plan=pack(entries,128,128,4)
    assert plan==pack(list(reversed(entries)),128,128,4)
    assert plan['base_rgba8_bytes']==128*128*8
    assert plan['full_mip_rgba8_bytes']==sum((2**i)**2*8 for i in range(8))
    assert plan['tiles'][0]['pixel_rect']==[4,4,32,64]
    assert plan['tiles'][1]['pixel_rect']==[44,4,32,32]
    for patch in ({'width':32,'height':32},{'max_texture_bytes':1024},{'gutter':65}):
        with pytest.raises(ValueError):pack(entries,**patch)
    with pytest.raises(ValueError):pack(entries+[entries[0]])
    with pytest.raises(ValueError):pack([entries[0],entries[1]|{'maps':['BASE_COLOR']}])

def test_atlas_contracts_paths_and_permissions(tmp_path):
    for patch in ({'entries':[]},{'width':4096,'height':4096},{'entries':[{'id':'../a','directory':'source'}]}):
        with pytest.raises(ValueError):Plan.model_validate({'entries':[{'id':'a','directory':'source'}]}|patch)
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False
    source=tmp_path/'library/source';source.mkdir(parents=True)
    server,state=build_server(config)
    args={'entries':[{'id':'a','directory':'source'}]}
    prepared=state.prepare('inspect_texture_atlas',args)
    assert State.input_paths('inspect_texture_atlas',prepared)==[str(source)]
    with pytest.raises(ValueError,match='inside'):state.prepare('inspect_texture_atlas',{'entries':[{'id':'a','directory':'../outside'}]})
    with pytest.raises(ValueError,match='distinct'):state.prepare('inspect_texture_atlas',{'entries':[{'id':'a','directory':'source'},{'id':'b','directory':'./source'}]})
    with pytest.raises(ValueError,match='outside source'):state.prepare('build_texture_atlas',args|{'expected_atlas':'a'*64,'directory':'source/deep/output'})
    assert not (source/'deep').exists()
    async def run():
        async with Client(server) as client:
            names={v.name for v in await client.list_tools()}
            assert 'inspect_texture_atlas' in names and 'build_texture_atlas' not in names
    asyncio.run(run())
