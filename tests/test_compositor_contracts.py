"""Compositing input limits and ordinary scene-edit permission boundaries."""
import asyncio
import pytest
from fastmcp import Client
from mcpblender.compositor_contracts import Graph,Node,Passes,Color,Attach
from mcpblender.config import Config
from mcpblender.server import build_server


def test_graph_and_settings_contracts():
    spec={'group':'FX','nodes':[{'name':'Color','type':'CompositorNodeRGB'},{'name':'Out','type':'NodeGroupOutput'}]}
    assert Graph.model_validate(spec)
    for patch in ({'nodes':[]},{'nodes':[{'name':'Out','type':'NodeGroupOutput'}]*2},{'nodes':[{'name':'File','type':'CompositorNodeOutputFile'}]},{'replace':True},{'nodes':[{'name':'A','type':'NodeGroupOutput','inputs':[{'socket':'Image','value':[float('nan')]*4}]}]}):
        with pytest.raises(ValueError):Graph.model_validate(spec|patch)
    for spec in ({'name':'Bad','type':'CompositorNodeBlur','view_layer':'Layer'}, {'name':'Bad','type':'CompositorNodeBlur','output_value':1}):
        with pytest.raises(ValueError):Node.model_validate(spec)
    assert Passes.model_validate({'expected_settings':'a'*64,'passes':{'denoising_data':True}})
    for values in ({},{'arbitrary_rna':True}):
        with pytest.raises(ValueError):Passes.model_validate({'expected_settings':'a'*64,'passes':values})
    for patch in ({},{'gamma':None},{'gamma':0},{'exposure':float('nan')}):
        with pytest.raises(ValueError):Color.model_validate({'expected_settings':'a'*64}|patch)
    with pytest.raises(ValueError):Attach.model_validate({'expected_settings':'a'*64,'group':'FX'})


def test_compositor_readonly_discovery(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path);config.stdio.allow_scene_edit=False
    server,_=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'compositor_node_catalog','inspect_compositor_graph','inspect_render_pipeline'}<=names
            assert not {'configure_compositor_graph','configure_render_passes','configure_color_management','configure_compositing'}&names
    asyncio.run(run())
