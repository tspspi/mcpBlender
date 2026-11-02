"""Native rigid dynamics and embedded-cache delivery with Python tools disabled."""
import asyncio
import hashlib
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from mcpblender.config import Config,write_config
from mcpblender.launcher import Launcher
from mcpblender.wire import call


async def physics(client,command,**params):
    if command!="inspect_physics" and "expected_physics" not in params:
        params["expected_physics"]=(await tool(client,"inspect_physics"))["physics_sha256"]
    return (await client.call_tool(command,{"params":params,"wait":True})).data


def test_drop_collisions_snapshot_binding_reopen_and_render(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert "execute_code" not in {t.name for t in await client.list_tools()}
            initial=await tool(client,"inspect_physics")
            assert initial["complete"] and initial["world"] is None
            world=await physics(client,"configure_rigid_world",frame_end=60)
            await tool(client,"create_primitive",name="RigidFloor",location=[10,0,-.5],scale=[5,5,.5])
            await physics(client,"configure_rigid_body",name="RigidFloor",type="PASSIVE",collision_shape="BOX",reset_unbaked=True)
            await tool(client,"create_primitive",name="Drop",location=[10,0,6])
            configured=await physics(client,"configure_rigid_body",name="Drop",collision_shape="BOX",mass=2,reset_unbaked=True)
            assert configured["total_bodies"]==2
            with pytest.raises(ToolError,match="stale"):
                await physics(client,"configure_rigid_world",expected_physics=world["physics_sha256"])
            sampled=await physics(client,"sample_rigid_bodies",objects=["Drop"],sample_frames=[1,24,60])
            z=[s["poses"]["Drop"][2][3] for s in sampled["samples"]]
            assert z[0]==pytest.approx(6) and z[1]<z[0] and z[-1]==pytest.approx(1,abs=.05)
            assert (await client.call_tool("get_scene_info")).data["frame"]==1
            with pytest.raises(ToolError,match="reset_unbaked"):
                await physics(client,"configure_rigid_body",name="Drop",mass=3)
            await physics(client,"configure_rigid_body",name="Drop",mass=2,collision_shape="BOX",reset_unbaked=True)
            before=(await client.call_tool("bridge_status")).data["bridge"]["filepath"]
            fingerprint=(await tool(client,"inspect_physics"))["physics_sha256"]
            payload={"params":{"expected_physics":fingerprint,"path":"rigid-baked.blend"},"request_id":"drop-bake","wait":True}
            baked=(await client.call_tool("bake_rigid_bodies",payload)).data
            assert baked["cache"]["is_baked"] and baked["bytes"]>0
            assert (await client.call_tool("bridge_status")).data["bridge"]["filepath"]==before
            operation=(await client.call_tool("get_operation",{"operation_id":baked["operation_id"]})).data
            assert operation["progress"]["storage"]["estimated_output_bytes"]>=16*1024**2
            assert operation["progress"]["storage"]["free_bytes"]>0
            valid=await physics(client,"validate_rigid_bake")
            assert valid["validated"] and valid["checkpoint_frames"]==[1,30,60]
            with pytest.raises(ToolError,match="baked"):
                await physics(client,"configure_rigid_body",name="Drop",mass=5,reset_unbaked=True)
            duplicate=(await client.call_tool("bake_rigid_bodies",payload)).data
            assert duplicate["operation_id"]==baked["operation_id"]
            restored=Config.model_validate_json(path.read_text())
            restored.bridge.socket_path=str(root/"fresh/bridge.sock")
            restored.launch.log_path=str(root/"fresh-blender.log")
            restored_path=root/"fresh-config.json";write_config(restored_path,restored)
            launcher=Launcher(restored)
            try:
                launcher.start()
                async with client_for(restored_path) as fresh:
                    await fresh.call_tool("open_blend",{"path":"rigid-baked.blend"})
                    assert (await physics(fresh,"validate_rigid_bake"))["validated"]
                    assert (await tool(fresh,"inspect_physics"))["physics_sha256"]==fingerprint
            finally:
                if launcher.process and launcher.process.poll() is None:
                    launcher.process.terminate();launcher.process.wait(timeout=15)
                call(restored.bridge.socket_path,"shutdown",timeout=5)
            await client.call_tool("open_blend",{"path":"rigid-baked.blend"})
            valid=await physics(client,"validate_rigid_bake")
            assert valid["validated"]
            await client.call_tool("set_object_transform",{"name":"Drop","location":[10,0,7]})
            changed=await tool(client,"inspect_physics")
            assert changed["bake_binding"]["source_matches"] is False
            with pytest.raises(ToolError,match="matching source"):
                await physics(client,"validate_rigid_bake")
            await client.call_tool("set_object_transform",{"name":"Drop","location":[10,0,6]})
            assert (await physics(client,"validate_rigid_bake"))["validated"]
            await client.call_tool("set_frame",{"frame":60})
            await tool(client,"apply_material_preset",material="DropPaint",base_color=[.8,.15,.03,1])
            await tool(client,"assign_material",objects=["Drop"],material="DropPaint")
            await client.call_tool("set_object_transform",{"name":"Cube","location":[-100,0,0]})
            await client.call_tool("run_action",{"action":"preview_setup","inputs":{"objects":["RigidFloor","Drop"],"prefix":"RigidView"},"wait":True})
            await tool(client,"configure_render",samples=8)
            queued=(await client.call_tool("submit_operation",{"command":"render_still","params":{"path":"rigid-drop.png","width":256,"height":192,"camera":"RigidView_Camera","engine":"CYCLES"}})).data
            done=(await client.call_tool("wait_operation",{"operation_id":queued["operation_id"],"timeout_seconds":60})).data
            assert done["state"]=="succeeded",done
            snapshot=root/"library/rigid-baked.blend"
            saved_hash=hashlib.sha256(snapshot.read_bytes()).hexdigest()
            cleared=await physics(client,"clear_rigid_bake")
            assert not cleared["cache"]["is_baked"] and not cleared["bake_binding"]["present"]
            assert hashlib.sha256(snapshot.read_bytes()).hexdigest()==saved_hash
            await physics(client,"remove_rigid_body",name="Drop",reset_unbaked=True)
            assert (await tool(client,"inspect_mesh",name="Drop",evaluated=False))["vertices"]==8
            if directory:=os.environ.get("MCPBLENDER_PHYSICS_EVIDENCE_DIR"):
                dest=Path(directory);dest.mkdir(parents=True,exist_ok=True)
                for filename in ("rigid-drop.png","rigid-baked.blend"):
                    shutil.copy2(root/"library"/filename,dest/filename)
    asyncio.run(run())


def test_running_simulation_broker_restart_cancellation_and_stable_id(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            await physics(client,"configure_rigid_world",frame_end=1000,reset_unbaked=True)
            await tool(client,"create_primitive",name="CancelDrop",location=[10,0,10])
            info=await physics(client,"configure_rigid_body",name="CancelDrop",reset_unbaked=True)
            payload={"params":{"objects":["CancelDrop"],"sample_frames":[1000],"expected_physics":info["physics_sha256"]},"wait":False,"request_id":"cancel-rigid-sim"}
            queued=(await client.call_tool("sample_rigid_bodies",payload)).data
            for _ in range(100):
                status=(await client.call_tool("get_operation",{"operation_id":queued["operation_id"]})).data
                if status["state"]=="running" and status.get("progress"):break
                await asyncio.sleep(.03)
            assert status["state"]=="running",status
            pid=(await client.call_tool("bridge_status")).data["bridge"]["pid"]
            assert (await client.call_tool("restart_bridge")).data["pid"]==pid
            await client.call_tool("cancel_operation",{"operation_id":queued["operation_id"]})
            done=(await client.call_tool("wait_operation",{"operation_id":queued["operation_id"],"timeout_seconds":30})).data
            assert done["state"]=="cancelled",done
            assert (await client.call_tool("get_scene_info")).data["frame"]==1
            repeated=(await client.call_tool("sample_rigid_bodies",payload)).data
            assert repeated["operation_id"]==queued["operation_id"] and repeated["state"]=="cancelled"
    asyncio.run(run())
