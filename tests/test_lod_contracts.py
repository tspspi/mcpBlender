"""LOD contracts, policy boundaries and bundle traversal refusal."""
import asyncio
import json
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server,State
from mcpblender.lod_contracts import Generate
from mcpblender.lod_files import validate,MARKER,glb_report


def test_budgets_and_bundle_paths(tmp_path):
    base={'name':'Source','chain':'Asset','expected_source':'a'*64,'levels':[{'triangle_budget':200},{'triangle_budget':50}]}
    assert Generate.model_validate(base).transfer_normals
    for patch in ({'levels':[]},{'levels':[{'triangle_budget':50},{'triangle_budget':100}]},{'chain':'ä'*21},{'max_relative_error':float('nan')},{'pose_frames':[1,1]},{'pose_frames':[1048575]},{'skin_max_influences':5},{'skin_joint_importance':-1}):
        with pytest.raises(ValueError):Generate.model_validate(base|patch)
    (tmp_path/'manifest.json').write_text(json.dumps({'format':MARKER,'levels':[{'file':'../outside.glb'},{}]}))
    with pytest.raises(ValueError,match='member path'):validate(tmp_path)
    (tmp_path/'bad.glb').write_bytes(b'invalid')
    with pytest.raises(ValueError):glb_report(tmp_path/'bad.glb')


def test_readonly_lod_visibility_and_output_boundary(tmp_path):
    config=Config();config.stdio.library_root=str(tmp_path/'library');config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False
    server,state=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            assert {'inspect_lod_source','inspect_lod_chain','validate_lod_export','sample_lod_chain'}<=names
            assert not {'generate_lod_chain','activate_lod_level','export_lod_chain'}&names
    asyncio.run(run())
    with pytest.raises(ValueError,match='inside'):
        state.prepare('export_lod_chain',{'chain':'Asset','expected_chain':'a'*64,'directory':'../outside'})
