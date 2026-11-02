"""Real isolated fluid bundles through structured MCP tools, Python disabled."""
import asyncio
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from mcpblender.config import Config,write_config
from mcpblender.launcher import Launcher
from mcpblender.wire import call
from mcpblender.fluid_files import read_json,write_json,MARKER
from test_asset_editing import assets_live,client_for,tool,pytestmark


async def fluid(client,command,**params):
    info=await tool(client,"inspect_fluids")
    assert info["complete"],info["unsupported_reasons"]
    params.setdefault("expected_fluid",info["fluid_sha256"])
    return (await client.call_tool(command,{"params":params,"wait":True})).data


async def liquid_scene(client):
    await tool(client,"create_primitive",name="LiquidDomain",location=[0,0,2],scale=[1,1,2])
    await tool(client,"apply_transforms",name="LiquidDomain")
    await fluid(client,"configure_fluid_domain",name="LiquidDomain",resolution=24,frame_end=24)
    await tool(client,"create_primitive",name="LiquidSource",kind="UV_SPHERE",location=[0,0,3],scale=[.45,.45,.45])
    await tool(client,"apply_transforms",name="LiquidSource")
    await fluid(client,"configure_fluid_flow",name="LiquidSource")
    await tool(client,"create_primitive",name="FluidShelf",location=[0,0,1],scale=[.9,.9,.2])
    await tool(client,"apply_transforms",name="FluidShelf")
    return await fluid(client,"configure_fluid_effector",name="FluidShelf")


def test_liquid_worker_bundle_reopen_collision_render_and_invalidation(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert "execute_code" not in {t.name for t in await client.list_tools()}
            configured=await liquid_scene(client);assert configured["complete"]
            with pytest.raises(ToolError,match="stale"):
                await client.call_tool("configure_fluid_flow",{"params":{"name":"LiquidSource","expected_fluid":"0"*64}})
            with pytest.raises(ToolError,match="estimate"):
                await fluid(client,"bake_fluid",name="LiquidDomain",directory="too-small",max_bytes=1024**2)
            assert not (root/"library/too-small").exists()
            await client.call_tool("set_frame",{"frame":7})
            before_scene=(await client.call_tool("get_scene_info")).data
            result=await fluid(client,"bake_fluid",name="LiquidDomain",directory="liquid-bundle")
            assert result["live_scene_unchanged"] and (await client.call_tool("get_scene_info")).data["frame"]==7
            assert (await client.call_tool("get_scene_info")).data["filepath"]==before_scene["filepath"]
            bundle=root/"library/liquid-bundle";m=read_json(bundle/"manifest.json")
            samples=[c["value"] for c in m["checkpoints"]]
            assert all(s["vertices"]>0 for s in samples)
            assert samples[-1]["bounds"]["min"][2]>1.2-4/24-.01,"Surface must stay within one domain cell of the shelf top"
            assert samples[-1]["bounds"]["max"][2]<samples[0]["bounds"]["max"][2]-.5
            before_gravity=(await tool(client,"inspect_fluids"))["fluid_sha256"]
            no_gravity=await fluid(client,"configure_fluid_domain",name="LiquidDomain",resolution=24,frame_end=24,gravity_weight=0)
            assert no_gravity["fluid_sha256"]!=before_gravity
            await fluid(client,"bake_fluid",name="LiquidDomain",directory="zero-gravity-liquid")
            floating=read_json(root/"library/zero-gravity-liquid/manifest.json")
            assert floating["checkpoints"][-1]["value"]["bounds"]["min"][2]>2.2
            restored=await fluid(client,"configure_fluid_domain",name="LiquidDomain",resolution=24,frame_end=24)
            assert restored["fluid_sha256"]==before_gravity
            with pytest.raises(ToolError,match="exist"):
                await fluid(client,"bake_fluid",name="LiquidDomain",directory="liquid-bundle")
            fresh=Config.model_validate_json(path.read_text());fresh.bridge.socket_path=str(root/"fresh-fluid/bridge.sock");fresh.launch.log_path=str(root/"fresh-fluid.log")
            fresh_path=root/"fresh-fluid.json";write_config(fresh_path,fresh);launcher=Launcher(fresh)
            try:
                launcher.start()
                async with client_for(fresh_path) as other:
                    await other.call_tool("open_blend",{"path":"liquid-bundle/asset.blend"})
                    validated=await tool(other,"validate_fluid_bake",directory="liquid-bundle")
                    assert validated["validated"] and validated["files"]>24
                    relocated=root/"library/relocated-liquid";shutil.copytree(bundle,relocated)
                    record=read_json(relocated/MARKER);record["state"]="running";write_json(relocated/MARKER,record)
                    with pytest.raises(ToolError,match="alive"):
                        await tool(other,"recover_fluid_job",directory="relocated-liquid")
                    # Model the narrow post-worker/pre-parent-publication crash
                    # window using a genuine complete bundle and a departed PID.
                    record["parent_pid"]=record["worker_pid"];write_json(relocated/MARKER,record)
                    adopted=await tool(other,"recover_fluid_job",directory="relocated-liquid")
                    assert adopted["reconciled"] and not adopted["replayed"] and adopted["native_validation_required"]
                    await other.call_tool("open_blend",{"path":"relocated-liquid/asset.blend"})
                    assert (await tool(other,"validate_fluid_bake",directory="relocated-liquid"))["validated"]
                    with pytest.raises(ToolError,match="immutable"):
                        await fluid(other,"configure_fluid_domain",name="LiquidDomain",resolution=32)
                    await other.call_tool("set_object_transform",{"name":"FluidShelf","location":[0,0,.8]})
                    with pytest.raises(ToolError,match="source binding"):
                        await tool(other,"validate_fluid_bake",directory="liquid-bundle")
                    await other.call_tool("set_object_transform",{"name":"FluidShelf","location":[0,0,1]})
                    await other.call_tool("set_frame",{"frame":24})
                    for name in ("LiquidSource","Cube"):
                        await other.call_tool("set_object_transform",{"name":name,"location":[-100,0,0]})
                    await tool(other,"apply_material_preset",material="WaterBlue",base_color=[.02,.15,.6,1],roughness=.2)
                    await tool(other,"assign_material",objects=["LiquidDomain"],material="WaterBlue")
                    await other.call_tool("run_action",{"action":"preview_setup","inputs":{"objects":["LiquidDomain","FluidShelf"],"prefix":"LiquidView"},"wait":True})
                    q=(await other.call_tool("submit_operation",{"command":"render_still","params":{"path":"liquid.png","width":256,"height":192,"camera":"LiquidView_Camera","engine":"CYCLES"}})).data
                    assert (await other.call_tool("wait_operation",{"operation_id":q["operation_id"],"timeout_seconds":60})).data["state"]=="succeeded"
            finally:
                if launcher.process and launcher.process.poll() is None:launcher.process.terminate();launcher.process.wait(timeout=15)
                call(fresh.bridge.socket_path,"shutdown",timeout=5)
            with pytest.raises(ToolError,match="protected"):
                await tool(client,"cleanup_fluid_job",directory="liquid-bundle",dry_run=False)
            cache=next((bundle/"cache/data").iterdir());before=cache.read_bytes();cache.write_bytes(b"corrupt")
            await client.call_tool("open_blend",{"path":"liquid-bundle/asset.blend"})
            with pytest.raises(ToolError,match="changed"):
                await tool(client,"validate_fluid_bake",directory="liquid-bundle")
            cache.write_bytes(before)
            if dest:=os.environ.get("MCPBLENDER_FLUID_EVIDENCE_DIR"):
                Path(dest).mkdir(parents=True,exist_ok=True);shutil.copytree(bundle,Path(dest)/"liquid-bundle",dirs_exist_ok=True);shutil.copy2(root/"library/liquid.png",Path(dest)/"liquid.png")
    asyncio.run(run())


def test_gas_density_bundle_and_cancelled_worker_cleanup(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            if (root/"library/liquid-bundle/source.blend").exists():
                await client.call_tool("open_blend",{"path":"liquid-bundle/source.blend"})
            else:await liquid_scene(client)
            await fluid(client,"remove_fluid_controller",name="LiquidSource")
            await fluid(client,"configure_fluid_domain",name="LiquidDomain",type="GAS",resolution=24,frame_end=12)
            await fluid(client,"configure_fluid_flow",name="LiquidSource",type="SMOKE",behavior="INFLOW")
            await fluid(client,"bake_fluid",name="LiquidDomain",directory="smoke-bundle")
            bundle=root/"library/smoke-bundle";saved=read_json(bundle/"manifest.json")
            assert all(c["value"]["grid_values"]>0 for c in saved["checkpoints"])
            assert saved["checkpoints"][-1]["value"]["sampled_density_sum"]>saved["checkpoints"][0]["value"]["sampled_density_sum"]
            await client.call_tool("open_blend",{"path":"smoke-bundle/asset.blend"})
            assert (await tool(client,"validate_fluid_bake",directory="smoke-bundle"))["validated"]
            await client.call_tool("open_blend",{"path":"smoke-bundle/source.blend"})
            configured=await fluid(client,"configure_fluid_domain",name="LiquidDomain",type="GAS",resolution=32,frame_end=240)
            payload={"params":{"name":"LiquidDomain","expected_fluid":configured["fluid_sha256"],"directory":"cancelled-fluid"},"request_id":"cancelled-fluid-worker","wait":False}
            q=(await client.call_tool("bake_fluid",payload)).data
            for _ in range(400):
                status=(await client.call_tool("get_operation",{"operation_id":q["operation_id"]})).data
                if status["state"]!="running" and status["state"]!="queued":pytest.fail(str(status))
                progress=status.get("progress") or {}
                if progress.get("phase")=="baking native fluid data":break
                await asyncio.sleep(.03)
            assert progress["phase"]=="baking native fluid data"
            assert progress["storage"]["free_bytes"]>0 and progress["storage"]["estimated_output_bytes"]>0
            worker_pid=progress["worker_pid"];os.kill(worker_pid,0)
            pid=(await client.call_tool("bridge_status")).data["bridge"]["pid"]
            assert (await client.call_tool("restart_bridge")).data["pid"]==pid
            await client.call_tool("cancel_operation",{"operation_id":q["operation_id"]})
            done=(await client.call_tool("wait_operation",{"operation_id":q["operation_id"],"timeout_seconds":30})).data
            assert done["state"]=="cancelled",done
            with pytest.raises(ProcessLookupError):os.kill(worker_pid,0)
            job=await tool(client,"inspect_fluid_job",directory="cancelled-fluid")
            assert job["record"]["state"]=="cancelled" and not job["worker_alive"]
            repeated=(await client.call_tool("bake_fluid",payload)).data
            assert repeated["operation_id"]==q["operation_id"] and repeated["state"]=="cancelled"
            preview=await tool(client,"cleanup_fluid_job",directory="cancelled-fluid")
            assert preview["dry_run"] and preview["bytes"]>0
            assert (root/"library/cancelled-fluid").is_dir()
            await client.call_tool("open_blend",{"path":"cancelled-fluid/source.blend"})
            with pytest.raises(ToolError,match="references"):
                await tool(client,"cleanup_fluid_job",directory="cancelled-fluid",dry_run=False)
            await client.call_tool("open_blend",{"path":"smoke-bundle/source.blend"})
            unknown=root/"library/cancelled-fluid/preserve.txt";unknown.write_text("user data")
            with pytest.raises(ToolError,match="Unknown"):
                await tool(client,"cleanup_fluid_job",directory="cancelled-fluid",dry_run=False)
            assert unknown.read_text()=="user data";unknown.unlink()
            await tool(client,"cleanup_fluid_job",directory="cancelled-fluid",dry_run=False)
            assert not (root/"library/cancelled-fluid").exists()
            if dest:=os.environ.get("MCPBLENDER_FLUID_EVIDENCE_DIR"):
                shutil.copytree(bundle,Path(dest)/"smoke-bundle",dirs_exist_ok=True)
    asyncio.run(run())


def test_parent_crash_stops_fluid_worker_and_reconciles_without_replay(assets_live):
    import signal
    from mcpblender.broker import process_alive
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            if not (root/"library/smoke-bundle/source.blend").exists():
                if (root/"library/liquid-bundle/source.blend").exists():
                    await client.call_tool("open_blend",{"path":"liquid-bundle/source.blend"})
                else:await liquid_scene(client)
                await fluid(client,"remove_fluid_controller",name="LiquidSource")
                await fluid(client,"configure_fluid_domain",name="LiquidDomain",type="GAS",resolution=32,frame_end=240)
                await fluid(client,"configure_fluid_flow",name="LiquidSource",type="SMOKE",behavior="INFLOW")
            else:
                await client.call_tool("open_blend",{"path":"smoke-bundle/source.blend"})
                await fluid(client,"configure_fluid_domain",name="LiquidDomain",type="GAS",resolution=32,frame_end=240)
            info=await tool(client,"inspect_fluids")
            payload={"params":{"name":"LiquidDomain","expected_fluid":info["fluid_sha256"],"directory":"interrupted-fluid"},"request_id":"interrupted-fluid-worker","wait":False}
            q=(await client.call_tool("bake_fluid",payload)).data
            for _ in range(400):
                status=(await client.call_tool("get_operation",{"operation_id":q["operation_id"]})).data
                assert status["state"] in {"queued","running"},status
                progress=status.get("progress") or {}
                if progress.get("phase")=="baking native fluid data":break
                await asyncio.sleep(.03)
            assert progress["phase"]=="baking native fluid data"
            worker_pid=progress["worker_pid"]
            parent_pid=(await client.call_tool("bridge_status")).data["bridge"]["pid"]
            os.kill(parent_pid,signal.SIGKILL)
            for _ in range(300):
                status=(await client.call_tool("get_operation",{"operation_id":q["operation_id"]})).data
                if status["state"]=="interrupted" and not process_alive(worker_pid):break
                await asyncio.sleep(.05)
            assert status["state"]=="interrupted" and status["outcome_unknown"],status
            assert not process_alive(worker_pid),"Owned native worker must stop when its parent crashes"
            assert read_json(root/"library/interrupted-fluid"/MARKER)["state"]=="running"
            repeated=(await client.call_tool("get_operation",{"operation_id":q["operation_id"]})).data
            assert repeated["state"]=="interrupted"
        fresh=Config.model_validate_json(path.read_text());fresh.bridge.socket_path=str(root/"recovery-fluid/bridge.sock");fresh.launch.log_path=str(root/"recovery-fluid.log")
        fresh_path=root/"recovery-fluid.json";write_config(fresh_path,fresh);launcher=Launcher(fresh)
        try:
            launcher.start()
            async with client_for(fresh_path) as other:
                recovered=await tool(other,"recover_fluid_job",directory="interrupted-fluid")
                assert recovered["reconciled"] and not recovered["replayed"]
                assert recovered["record"]["state"]=="interrupted"
                with pytest.raises(ToolError,match="interrupted"):
                    await tool(other,"cleanup_fluid_job",directory="interrupted-fluid",dry_run=False)
                preview=await tool(other,"cleanup_fluid_job",directory="interrupted-fluid",include_interrupted=True)
                assert preview["dry_run"] and preview["bytes"]>0
                await tool(other,"cleanup_fluid_job",directory="interrupted-fluid",dry_run=False,include_interrupted=True)
                assert not (root/"library/interrupted-fluid").exists()
        finally:
            if launcher.process and launcher.process.poll() is None:launcher.process.terminate();launcher.process.wait(timeout=15)
            call(fresh.bridge.socket_path,"shutdown",timeout=5)
    asyncio.run(run())
