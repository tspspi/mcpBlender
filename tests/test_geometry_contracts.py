import asyncio

from fastmcp import Client
import pytest

from mcpblender.config import Config
from mcpblender.geometry_contracts import GeometryGraph, GeometryNode, GeometryValues, GeometryPreset, InterfaceInput, COMMANDS
from mcpblender.blender.geometry_presets import compile_preset
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


def test_presets_compile_to_typed_graphs_and_bound_parameters():
    for kind in ("BUILDING","VEGETATION","SCATTER_VEGETATION","REFINE_MESH"):
        params=GeometryPreset(group="Recipe",settings={"type":kind}).model_dump(exclude_none=True)
        spec=compile_preset(params)
        assert spec.pop("_preset")=={"type":kind,"version":1}
        graph=GeometryGraph.model_validate(spec)
        assert graph.inputs and all(i.minimum is not None and i.maximum is not None for i in graph.inputs)
    for settings in ({"type":"BUILDING","floors":33},{"type":"BUILDING","columns":True},
                     {"type":"VEGETATION","segments":100},{"type":"VEGETATION","height":float("nan")},
                     {"type":"SCATTER_VEGETATION","max_points":2001},{"type":"SCATTER_VEGETATION","density":-1},
                     {"type":"REFINE_MESH","levels":4}):
        with pytest.raises(ValueError):
            GeometryPreset(group="Recipe",settings=settings)
    for params in ({"name":"Value","type":"FLOAT","default":0,"minimum":2,"maximum":1},
                   {"name":"Flag","type":"BOOLEAN","default":False,"maximum":1}):
        with pytest.raises(ValueError):
            InterfaceInput.model_validate(params)
