import asyncio
from fastmcp import Client
import pytest
from mcpblender.config import Config
from mcpblender.physics_contracts import Body, World, Samples, COMMANDS
from mcpblender.server import build_server


def test_physics_parameters_policy_and_snapshot_paths(tmp_path):
    digest="a"*64
    for changes in ({"mass":0},{"mass":float("nan")},{"restitution":2},{"collision_shape":"COMPOUND"},
                    {"type":"ACTIVE","collision_shape":"MESH"}):
        with pytest.raises(ValueError):
            Body.model_validate({"name":"Body","expected_physics":digest}|changes)
    with pytest.raises(ValueError):
        World(expected_physics=digest,frame_start=10,frame_end=1)
    with pytest.raises(ValueError):
        Samples(expected_physics=digest,objects=["A"],sample_frames=[1,1])
    config=Config();config.stdio.library_root=str(tmp_path/"library");config.bridge.socket_path=str(tmp_path/"private/bridge.sock")
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
    config.stdio.allow_scene_edit=True;config.stdio.allow_library_write=True
    _,state=build_server(config)
    for path in ("../escape.blend","bad.cache"):
        with pytest.raises(ValueError):
            state.prepare("bake_rigid_bodies",{"path":path,"expected_physics":digest})
    library=tmp_path/"library";library.mkdir(exist_ok=True)
    (library/"bad.txt").write_text("not a project or GLB")
    for command,extra in (("open_blend",{}),("save_blend",{}),("export_glb",{}),("export_objects_glb",{"objects":["Body"]})):
        with pytest.raises(ValueError,match="File must end"):
            state.prepare(command,{"path":"bad.txt"}|extra)
