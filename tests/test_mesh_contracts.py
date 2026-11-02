import asyncio

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from mcpblender.commands import COMMANDS
from mcpblender.config import Config
from mcpblender.mesh_contracts import Elements, ExtrudeFaces, LoopCut
from mcpblender.server import build_server


@pytest.mark.parametrize("elements", [{}, {"indices": []}, {"indices": [0, 0]},
    {"indices": [-1]}, {"indices": [True]}, {"indices": [1.5]},
    {"indices": [0], "selection": "Roof"}])
def test_element_targets_are_explicit_and_unambiguous(elements):
    with pytest.raises(ValueError):
        Elements.model_validate(elements)


def test_edits_require_valid_fingerprints_and_bounded_parameters():
    valid = {"name": "Building", "expected_topology": "a" * 64}
    assert ExtrudeFaces(**valid, faces={"indices": [0]}, offset=[0, 0, 1])
    for changes in ({"expected_topology": "bad"}, {"offset": [0, 0, 0]},
                    {"offset": [0, 0, float("nan")]}, {"expected_geometry": "bad"}):
        params = valid | {"faces": {"indices": [0]}, "offset": [0, 0, 1]} | changes
        with pytest.raises(ValueError):
            ExtrudeFaces.model_validate(params)
    with pytest.raises(ValueError):
        LoopCut(**valid, edge=0, cuts=33)
    with pytest.raises(ValueError):
        COMMANDS["configure_modifier"][0].model_validate({"name": "A", "modifier": "Cut", "settings": {"type": "BOOLEAN", "object": "B", "solver": "arbitrary"}})


def test_mesh_inspection_remains_visible_and_mesh_edits_are_denied(tmp_path):
    config = Config()
    config.bridge.socket_path = str(tmp_path / "bridge.sock")
    config.stdio.library_root = str(tmp_path / "library")
    config.stdio.allow_scene_edit = False
    config.stdio.allow_code_execution = False
    server, state = build_server(config)
    async def run():
        async with Client(server) as client:
            names = {t.name for t in await client.list_tools()}
            assert "inspect_mesh_elements" in names
            for command in ("select_mesh_elements", "extrude_mesh_faces", "inset_mesh_faces",
                            "loop_cut_mesh", "merge_mesh_vertices", "cleanup_mesh", "repair_mesh_normals", "remove_mesh_selection"):
                assert command not in names
                with pytest.raises(PermissionError):
                    state.check(command)
            with pytest.raises(ToolError):
                await client.call_tool("submit_operation", {"command": "cleanup_mesh", "params": {"name": "Cube", "expected_topology": "a" * 64}})
    asyncio.run(run())
