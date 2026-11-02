import asyncio
from pathlib import Path
import pytest
from fastmcp import Client
from mcpblender.config import Config
from mcpblender.server import build_server
from mcpblender.fluid_contracts import Domain,Flow,Bake,COMMANDS
from mcpblender.fluid_files import inventory,manifest,verify,write_json,read_json


def test_fluid_contracts_policy_paths_and_manifest_safety(tmp_path):
    guard={"expected_fluid":"a"*64,"name":"Domain"}
    for changes in ({"resolution":256},{"frame_start":3,"frame_end":2},{"frame_end":501}):
        with pytest.raises(ValueError):Domain(**guard,**changes)
    with pytest.raises(ValueError):Flow(**guard,velocity=[float("nan"),0,0])
    with pytest.raises(ValueError):Bake(**guard,directory="job",threads=0)
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
    for command in ("bake_fluid","validate_fluid_bake","cleanup_fluid_job"):
        with pytest.raises(ValueError):state.prepare(command,guard|{"directory":"../escape"} if command=="bake_fluid" else {"directory":"../escape"})
    bundle=tmp_path/"bundle";(bundle/"cache/data").mkdir(parents=True)
    (bundle/"asset.blend").write_bytes(b"fixture");cache=bundle/"cache/data/density_0001.uni";cache.write_bytes(b"data")
    rows=manifest(bundle);assert verify(bundle,rows)==11
    cache.write_bytes(b"edit")
    with pytest.raises(ValueError,match="changed"):verify(bundle,rows)
    (bundle/"cache/data/link").symlink_to(tmp_path)
    with pytest.raises(ValueError,match="symlinks"):inventory(bundle)
    (bundle/"cache/data/link").unlink();(bundle/"unknown").touch()
    with pytest.raises(ValueError,match="Unknown"):inventory(bundle)
