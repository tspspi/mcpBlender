import asyncio

from fastmcp import Client
import pytest

from mcpblender.config import Config
from mcpblender.geometry_contracts import GeometryGraph, GeometryNode, GeometryValues, COMMANDS
from mcpblender.server import build_server


def test_geometry_contracts_and_readonly_policy(tmp_path):
    for node in ({"name": "Script", "type": "GeometryNodeGroup"},
                 {"name": "Cube", "type": "GeometryNodeMeshCube", "material": "Paint"},
                 {"name": "Cube", "type": "GeometryNodeMeshCube", "python": "anything"},
                 {"name": "Cube", "type": "GeometryNodeMeshCube", "inputs": [{"socket": -1, "value": 1}]},
                 {"name": "Cube", "type": "GeometryNodeMeshCube", "inputs": [{"socket": "Size", "value": float("nan")}] }):
        with pytest.raises(ValueError):
            GeometryNode.model_validate(node)
    valid = {"group": "G", "nodes": [{"name": "Out", "type": "NodeGroupOutput"}]}
    for extra in ({"replace": True}, {"inputs": [{"name": "Geometry", "type": "INT", "default": 1}]},
                  {"nodes": valid["nodes"] * 2}):
        with pytest.raises(ValueError):
            GeometryGraph.model_validate(valid | extra)
    with pytest.raises(ValueError):
        GeometryValues(name="Cube", expected_graph="bad", values=[{"socket": "Count", "value": 1}])
    config = Config()
    config.bridge.socket_path = str(tmp_path / "private/bridge.sock")
    config.stdio.library_root = str(tmp_path / "library")
    config.stdio.allow_scene_edit = False
    config.stdio.allow_code_execution = False
    server, state = build_server(config)
    async def run():
        async with Client(server) as client:
            names = {t.name for t in await client.list_tools()}
            for command, (_, permissions, _) in COMMANDS.items():
                assert (command in names) == (not permissions)
                if permissions:
                    with pytest.raises(PermissionError):
                        state.check(command)
    asyncio.run(run())
