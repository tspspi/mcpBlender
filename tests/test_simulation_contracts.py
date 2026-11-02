import asyncio
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.simulation_contracts import ConfigureDeform,ConfigureParticles,Force,COMMANDS


def test_simulation_contracts_permissions_and_paths(tmp_path):
    guard={"expected_simulation":"a"*64}
    for settings in ({"type":"CLOTH","pins":[0]}, {"type":"CLOTH","mass":float("nan")},
                     {"type":"SOFT_BODY","step_min":30,"step_max":5}):
        with pytest.raises(ValueError):ConfigureDeform(name="Mesh",settings=settings,**guard)
    for changes in ({"count":10001},{"frame_start":20,"frame_end":1},{"type":"HAIR","instance_object":"Glyph"}):
        with pytest.raises(ValueError):ConfigureParticles(name="Emitter",**guard,**changes)
    with pytest.raises(ValueError):Force(name="Field",type="TEXTURE",**guard)
    config=Config();config.bridge.socket_path=str(tmp_path/"bridge/bridge.sock");config.stdio.library_root=str(tmp_path/"library")
    config.stdio.allow_scene_edit=False;config.stdio.allow_library_write=False
    server,state=build_server(config)
    async def run():
        async with Client(server) as client:
            names={t.name for t in await client.list_tools()}
            for command,(_,permissions,_) in COMMANDS.items():
                assert (command in names)==(not permissions)
                if permissions:
                    with pytest.raises(PermissionError):state.check(command)
    asyncio.run(run())
    for path in ("../escape.blend","bad.cache"):
        with pytest.raises(ValueError):state.prepare("bake_simulation",guard|{"name":"Mesh","path":path})
