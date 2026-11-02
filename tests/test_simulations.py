"""Real cloth, soft bodies, force fields and particles without MCP Python execution."""
import asyncio
import hashlib
import math
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from mcpblender.config import Config,write_config
from mcpblender.launcher import Launcher
from mcpblender.wire import call
from test_asset_editing import assets_live,client_for,tool,pytestmark


async def sim(client,command,**params):
    params.setdefault("expected_simulation",(await tool(client,"inspect_simulations"))["simulation_sha256"])
    return (await client.call_tool(command,{"params":params,"wait":True})).data


async def grid(client,name,size=2,z=3,n=8):
    vertices=[[-size/2+x*size/n,-size/2+y*size/n,z] for y in range(n+1) for x in range(n+1)]
    faces=[[y*(n+1)+x,y*(n+1)+x+1,(y+1)*(n+1)+x+1,(y+1)*(n+1)+x] for y in range(n) for x in range(n)]
    await tool(client,"create_mesh",name=name,vertices=vertices,faces=faces)


def test_cloth_collision_pins_bake_roundtrip_and_source_invalidation(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert "execute_code" not in {t.name for t in await client.list_tools()}
            await tool(client,"create_primitive",name="SimFloor",location=[0,0,-.5],scale=[4,4,.5])
            await sim(client,"configure_collision",name="SimFloor")
            await grid(client,"Fabric",size=3,z=1.5)
            await tool(client,"duplicate_object",name="Fabric",new_name="FabricShared",linked_data=True,offset=[-100,0,0])
            mesh=await tool(client,"inspect_mesh_elements",name="Fabric")
            assert mesh["data_users"]==2
            with pytest.raises(ToolError,match="topology"):
                await sim(client,"configure_deform_simulation",name="Fabric",settings={"type":"CLOTH","pins":[0,8]},expected_topology="0"*64)
            with pytest.raises(ToolError,match="shared"):
                await sim(client,"configure_deform_simulation",name="Fabric",settings={"type":"CLOTH","pins":[0,8]},expected_topology=mesh["topology_sha256"],frame_end=35,reset_unbaked=True)
            info=await sim(client,"configure_deform_simulation",name="Fabric",settings={"type":"CLOTH","pins":[0,8]},expected_topology=mesh["topology_sha256"],frame_end=35,reset_unbaked=True,make_single_user=True)
            isolated=await tool(client,"inspect_mesh_elements",name="Fabric")
            shared=await tool(client,"inspect_mesh_elements",name="FabricShared")
            assert isolated["data_users"]==shared["data_users"]==1
            assert isolated["mesh_data"]!=shared["mesh_data"]
            fingerprint=info["simulation_sha256"]
            assert info["complete"] and info["total_controllers"]==1
            sampled=await sim(client,"sample_simulation",name="Fabric",sample_frames=[1,35])
            first,last=[s["value"] for s in sampled["samples"]]
            assert first["bounds"]["min"][2]==pytest.approx(1.5)
            assert -.25<last["bounds"]["min"][2]<.25
            assert last["samples"][0]["location"][2]==pytest.approx(1.5,abs=.01)
            assert (await client.call_tool("get_scene_info")).data["frame"]==1
            with pytest.raises(ToolError,match="max_cache_bytes"):
                await sim(client,"bake_simulation",name="Fabric",path="budget-refused.blend",max_cache_bytes=100)
            assert not (root/"library/budget-refused.blend").exists()
            with pytest.raises(ToolError,match="reset_unbaked"):
                await sim(client,"configure_force_field",name="Breeze",strength=1)
            await tool(client,"apply_material_preset",material="FabricBlue",base_color=[.02,.15,.7,1])
            await tool(client,"assign_material",objects=["Fabric"],material="FabricBlue")
            await sim(client,"bake_simulation",name="Fabric",path="cloth-baked.blend")
            assert (await sim(client,"validate_simulation_bake",name="Fabric"))["validated"]
            with pytest.raises(ToolError,match="baked"):
                await sim(client,"configure_collision",name="SimFloor",reset_unbaked=True)
            await client.call_tool("open_blend",{"path":"cloth-baked.blend"})
            assert (await sim(client,"validate_simulation_bake",name="Fabric"))["validated"]
            await client.call_tool("set_object_transform",{"name":"SimFloor","location":[0,0,-1]})
            with pytest.raises(ToolError,match="matching source"):
                await sim(client,"validate_simulation_bake",name="Fabric")
            await client.call_tool("set_object_transform",{"name":"SimFloor","location":[0,0,-.5]})
            await client.call_tool("set_frame",{"frame":35})
            await client.call_tool("set_object_transform",{"name":"Cube","location":[-100,0,0]})
            await client.call_tool("run_action",{"action":"preview_setup","inputs":{"objects":["Fabric","SimFloor"],"prefix":"FabricView"},"wait":True})
            await tool(client,"configure_render",samples=12)
            q=(await client.call_tool("submit_operation",{"command":"render_still","params":{"path":"cloth.png","width":256,"height":192,"camera":"FabricView_Camera","engine":"CYCLES"}})).data
            assert (await client.call_tool("wait_operation",{"operation_id":q["operation_id"],"timeout_seconds":60})).data["state"]=="succeeded"
            snapshot=root/"library/cloth-baked.blend";before=hashlib.sha256(snapshot.read_bytes()).hexdigest()
            await sim(client,"clear_simulation_cache",name="Fabric")
            assert hashlib.sha256(snapshot.read_bytes()).hexdigest()==before
            await tool(client,"duplicate_object",name="Fabric",new_name="FabricPinnedShared",linked_data=True,offset=[-100,0,0])
            with pytest.raises(ToolError,match="shared"):
                await sim(client,"remove_simulation_controller",name="Fabric",reset_unbaked=True)
            await sim(client,"remove_simulation_controller",name="Fabric",reset_unbaked=True,make_single_user=True)
            assert not (await tool(client,"inspect_mesh",name="Fabric",evaluated=False))["modifiers"]
            preserved=await sim(client,"sample_simulation",name="FabricPinnedShared",sample_frames=[35])
            assert preserved["samples"][0]["value"]["samples"][0]["location"][2]==pytest.approx(1.5,abs=.01)
            await sim(client,"remove_simulation_controller",name="FabricPinnedShared",reset_unbaked=True)
            if dest:=os.environ.get("MCPBLENDER_SIM_EVIDENCE_DIR"):
                Path(dest).mkdir(parents=True,exist_ok=True)
                for filename in ("cloth.png","cloth-baked.blend"):shutil.copy2(root/"library"/filename,Path(dest)/filename)
    asyncio.run(run())


def test_soft_body_and_newtonian_particle_caches_with_force_helpers(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            names={obj["name"] for obj in (await client.call_tool("get_scene_info")).data["objects"]}
            if "SimFloor" not in names:await tool(client,"create_primitive",name="SimFloor",location=[0,0,-.5],scale=[4,4,.5])
            await sim(client,"configure_collision",name="SimFloor",damping_factor=.8,friction_factor=.5,reset_unbaked=True)
            await tool(client,"create_primitive",name="SoftBlob",location=[0,0,3])
            await sim(client,"configure_deform_simulation",name="SoftBlob",settings={"type":"SOFT_BODY"},frame_end=30,reset_unbaked=True)
            sampled=await sim(client,"sample_simulation",name="SoftBlob",sample_frames=[1,30])
            assert sampled["samples"][-1]["value"]["bounds"]["max"][2]<3.5
            assert sampled["samples"][-1]["value"]["bounds"]["min"][2]>-.25
            await sim(client,"bake_simulation",name="SoftBlob",path="soft-baked.blend")
            await client.call_tool("open_blend",{"path":"soft-baked.blend"})
            assert (await sim(client,"validate_simulation_bake",name="SoftBlob"))["validated"]
            await sim(client,"clear_simulation_cache",name="SoftBlob")
            await sim(client,"remove_simulation_controller",name="SoftBlob",reset_unbaked=True)
            await grid(client,"Emitter",size=1,z=3,n=1)
            await tool(client,"create_primitive",name="ParticleGlyph",location=[50,50,0])
            await tool(client,"apply_material_preset",material="ParticleOrange",base_color=[1,.2,.02,1])
            await tool(client,"assign_material",objects=["ParticleGlyph"],material="ParticleOrange")
            await sim(client,"configure_force_field",name="Breeze",type="WIND",rotation_euler=[0,math.pi/2,0],strength=1,reset_unbaked=True)
            info=await sim(client,"configure_particles",name="Emitter",count=40,frame_end=5,cache_end=30,seed=17,instance_object="ParticleGlyph",reset_unbaked=True)
            assert info["complete"]
            sampled=await sim(client,"sample_simulation",name="Emitter",modifier="Particles",sample_frames=[10,30])
            assert sampled["samples"][-1]["value"]["states"]["ALIVE"]==40
            assert sampled["samples"][0]["value"]["samples"][0]["location"]!=sampled["samples"][1]["value"]["samples"][0]["location"]
            wind_x=sum(p["location"][0] for p in sampled["samples"][-1]["value"]["samples"])/16
            await sim(client,"configure_force_field",name="Breeze",type="WIND",rotation_euler=[0,math.pi/2,0],strength=0,reset_unbaked=True)
            still=await sim(client,"sample_simulation",name="Emitter",modifier="Particles",sample_frames=[30])
            still_x=sum(p["location"][0] for p in still["samples"][-1]["value"]["samples"])/16
            assert wind_x>still_x+.01,"Wind helper must actually change the simulated motion"
            await sim(client,"configure_force_field",name="Breeze",type="WIND",rotation_euler=[0,math.pi/2,0],strength=1,reset_unbaked=True)
            await sim(client,"bake_simulation",name="Emitter",modifier="Particles",path="particles-baked.blend")
            assert (await sim(client,"validate_simulation_bake",name="Emitter",modifier="Particles"))["validated"]
            before_restore=await tool(client,"inspect_simulations")
            fresh=Config.model_validate_json(path.read_text());fresh.bridge.socket_path=str(root/"fresh-sim/bridge.sock");fresh.launch.log_path=str(root/"fresh-sim.log")
            fresh_path=root/"fresh-sim.json";write_config(fresh_path,fresh);launcher=Launcher(fresh)
            try:
                launcher.start()
                async with client_for(fresh_path) as other:
                    await other.call_tool("open_blend",{"path":"particles-baked.blend"})
                    after_restore=await tool(other,"inspect_simulations")
                    assert before_restore["simulation_sha256"]==after_restore["simulation_sha256"]
                    assert (await sim(other,"validate_simulation_bake",name="Emitter",modifier="Particles"))["validated"]
                    names={obj["name"] for obj in (await other.call_tool("get_scene_info")).data["objects"]}
                    for name in ("Cube","Fabric","SoftBlob"):
                        if name in names:await other.call_tool("set_object_transform",{"name":name,"location":[-100,0,0]})
                    await other.call_tool("set_frame",{"frame":20})
                    await other.call_tool("run_action",{"action":"preview_setup","inputs":{"objects":["Emitter","SimFloor"],"prefix":"ParticleView"},"wait":True})
                    await tool(other,"configure_render",samples=12)
                    q=(await other.call_tool("submit_operation",{"command":"render_still","params":{"path":"particles.png","width":256,"height":192,"camera":"ParticleView_Camera","engine":"CYCLES"}})).data
                    assert (await other.call_tool("wait_operation",{"operation_id":q["operation_id"],"timeout_seconds":60})).data["state"]=="succeeded"
            finally:
                if launcher.process and launcher.process.poll() is None:launcher.process.terminate();launcher.process.wait(timeout=15)
                call(fresh.bridge.socket_path,"shutdown",timeout=5)
            await sim(client,"clear_simulation_cache",name="Emitter",modifier="Particles")
            await tool(client,"duplicate_object",name="Emitter",new_name="EmitterCopy")
            with pytest.raises(ToolError,match="shared"):
                await sim(client,"configure_particles",name="EmitterCopy",count=12,reset_unbaked=True)
            isolated=await sim(client,"configure_particles",name="EmitterCopy",count=12,make_single_user=True,reset_unbaked=True)
            counts={v["name"]:v["settings"]["count"] for v in isolated["controller_settings"]}
            assert counts=={"Emitter":40,"EmitterCopy":12}
            await sim(client,"remove_simulation_controller",name="EmitterCopy",modifier="Particles",reset_unbaked=True)
            await sim(client,"remove_simulation_controller",name="Emitter",modifier="Particles",reset_unbaked=True)
            await sim(client,"remove_force_field",name="Breeze",reset_unbaked=True)
            if dest:=os.environ.get("MCPBLENDER_SIM_EVIDENCE_DIR"):
                Path(dest).mkdir(parents=True,exist_ok=True)
                for filename in ("soft-baked.blend","particles-baked.blend","particles.png"):shutil.copy2(root/"library"/filename,Path(dest)/filename)
    asyncio.run(run())


def test_static_hair_and_running_cache_operation_cancellation(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            await grid(client,"Fur",size=2,z=1,n=2)
            await sim(client,"configure_particles",name="Fur",type="HAIR",count=20,hair_length=1.5,frame_end=5,cache_end=10,reset_unbaked=True)
            sampled=await sim(client,"sample_simulation",name="Fur",modifier="Particles",sample_frames=[1])
            value=sampled["samples"][0]["value"]
            assert value["kind"]=="HAIR" and value["count"]==20
            first=value["samples"][0]
            assert first["hair_key_count"]==3
            length=math.sqrt(sum((a-b)**2 for a,b in zip(first["root"],first["tip"])))
            assert length==pytest.approx(1.5,rel=.02)
            await client.call_tool("save_blend",{"path":"static-hair.blend"})
            await client.call_tool("open_blend",{"path":"static-hair.blend"})
            restored=await sim(client,"sample_simulation",name="Fur",modifier="Particles",sample_frames=[1])
            assert restored["samples"][0]["value"]==value
            with pytest.raises(ToolError,match="Static hair"):
                await sim(client,"bake_simulation",name="Fur",modifier="Particles",path="invalid-hair.blend")
            await sim(client,"remove_simulation_controller",name="Fur",modifier="Particles",reset_unbaked=True)
            await grid(client,"CancelFabric",n=2)
            configured=await sim(client,"configure_deform_simulation",name="CancelFabric",settings={"type":"CLOTH"},frame_end=500,reset_unbaked=True)
            payload={"params":{"name":"CancelFabric","expected_simulation":configured["simulation_sha256"],"path":"cancelled-sim.blend"},"request_id":"cancelled-cloth-bake","wait":False}
            q=(await client.call_tool("bake_simulation",payload)).data
            for _ in range(100):
                status=(await client.call_tool("get_operation",{"operation_id":q["operation_id"]})).data
                if status["state"]=="running" and status.get("progress"):break
                await asyncio.sleep(.03)
            assert status["state"]=="running",status
            assert status["progress"]["storage"]["free_bytes"]>0
            assert status["progress"]["storage"]["estimated_output_bytes"]>0
            pid=(await client.call_tool("bridge_status")).data["bridge"]["pid"]
            assert (await client.call_tool("restart_bridge")).data["pid"]==pid
            await client.call_tool("cancel_operation",{"operation_id":q["operation_id"]})
            done=(await client.call_tool("wait_operation",{"operation_id":q["operation_id"],"timeout_seconds":30})).data
            assert done["state"]=="cancelled",done
            assert (await client.call_tool("get_scene_info")).data["frame"]==1
            assert not (root/"library/cancelled-sim.blend").exists()
            repeated=(await client.call_tool("bake_simulation",payload)).data
            assert repeated["operation_id"]==q["operation_id"] and repeated["state"]=="cancelled"
    asyncio.run(run())
