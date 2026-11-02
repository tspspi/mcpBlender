"""Cached smoke/fire renders through typed materials with MCP Python disabled."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_fluids import fluid


def image_stats(path):
    raw=subprocess.run(["ffmpeg","-v","error","-i",str(path),"-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True,check=True,timeout=20).stdout
    pixels=list(zip(raw[0::3],raw[1::3],raw[2::3]))
    return {"mean":sum(sum(p)/3 for p in pixels)/len(pixels),
            "warm_pixels":sum(r>110 and r>1.2*b and r>1.05*g for r,g,b in pixels)}


def test_cached_smoke_fire_graphs_and_rendered_controls(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert "execute_code" not in {t.name for t in await client.list_tools()}
            for kind in ("ShaderNodeVolumePrincipled","ShaderNodeVolumeInfo","ShaderNodeAttribute"):
                assert (await tool(client,"shader_node_catalog",node_type=kind))["type"]==kind
            await client.call_tool("set_object_transform",{"name":"Cube","location":[-100,0,0]})
            await tool(client,"create_primitive",name="GasDomain",location=[0,0,1.5],scale=[1.5,1.5,1.5])
            await tool(client,"apply_transforms",name="GasDomain")
            await fluid(client,"configure_fluid_domain",name="GasDomain",type="GAS",resolution=32,frame_end=20)
            await tool(client,"create_primitive",name="Burner",kind="UV_SPHERE",location=[0,0,.4],scale=[.3,.3,.3])
            await tool(client,"apply_transforms",name="Burner")
            await fluid(client,"configure_fluid_flow",name="Burner",type="BOTH",behavior="INFLOW",density=.5,temperature=2,fuel_amount=1)
            await tool(client,"apply_material_preset",material="EmitterInvisible",preset="VOLUME",volume_density=0)
            await tool(client,"assign_material",objects=["Burner"],material="EmitterInvisible")
            smoke=await tool(client,"apply_material_preset",material="Smoke",preset="SMOKE",base_color=[.35,.45,.65,1],volume_density=3)
            with pytest.raises(ToolError,match="number"):
                await tool(client,"configure_shader_node",material="Smoke",node={"name":"Volume","type":"ShaderNodeVolumePrincipled","inputs":[{"socket":"Density","value":"invalid"}]})
            after=await tool(client,"inspect_shader_graph",material="Smoke")
            assert after["nodes"]==smoke["nodes"] and after["links"]==smoke["links"]
            await tool(client,"assign_material",objects=["Cube"],material="Smoke")
            fire=await tool(client,"apply_material_preset",material="Fire",preset="FIRE",base_color=[.2,.2,.2,1],volume_density=.5,blackbody_intensity=1)
            assert len(fire["nodes"])==4 and len(fire["links"])==3
            await tool(client,"assign_material",objects=["GasDomain"],material="Fire")
            await tool(client,"create_primitive",name="Floor",kind="PLANE",scale=[4,4,4])
            await client.call_tool("run_action",{"action":"preview_setup","inputs":{"objects":["GasDomain"],"prefix":"GasView"},"wait":True})
            await tool(client,"configure_render",samples=16)
            await fluid(client,"bake_fluid",name="GasDomain",directory="fire-bundle")
            await client.call_tool("open_blend",{"path":"fire-bundle/asset.blend"})
            assert (await tool(client,"validate_fluid_bake",directory="fire-bundle"))["validated"]
            await client.call_tool("set_frame",{"frame":20})
            assert any(v["code"]=="volume_material" for v in (await tool(client,"asset_report",objects=["GasDomain"]))["warnings"])
            async def render(name):
                q=(await client.call_tool("submit_operation",{"command":"render_still","params":{"path":name,"width":256,"height":192,"camera":"GasView_Camera","engine":"CYCLES"}})).data
                done=(await client.call_tool("wait_operation",{"operation_id":q["operation_id"],"timeout_seconds":60})).data
                assert done["state"]=="succeeded",done
            await render("fire.png")
            await tool(client,"configure_shader_node",material="Fire",node={"name":"FlameIntensity","type":"ShaderNodeMath","inputs":[{"socket":1,"value":0}]})
            await render("fire-off.png")
            await tool(client,"assign_material",objects=["GasDomain"],material="Smoke")
            await render("smoke.png")
            stats={name:image_stats(root/"library"/name) for name in ("fire.png","fire-off.png","smoke.png")}
            if dest:=os.environ.get("MCPBLENDER_VOLUME_EVIDENCE_DIR"):
                target=Path(dest);target.mkdir(parents=True,exist_ok=True)
                shutil.copytree(root/"library/fire-bundle",target/"fire-bundle",dirs_exist_ok=True)
                for name in ("fire.png","fire-off.png","smoke.png"):shutil.copy2(root/"library"/name,target/name)
                (target/"stats.json").write_text(json.dumps(stats,indent=2))
            await tool(client,"configure_shader_node",material="Fire",node={"name":"FlameIntensity","type":"ShaderNodeMath","inputs":[{"socket":1,"value":1}]})
            await tool(client,"assign_material",objects=["GasDomain"],material="Fire")
            await client.call_tool("save_blend",{"path":"fire-lookdev.blend"})
            await client.call_tool("open_blend",{"path":"fire-lookdev.blend"})
            assert (await tool(client,"validate_fluid_bake",directory="fire-bundle"))["validated"]
            restored=await tool(client,"inspect_shader_graph",material="Fire")
            assert len(restored["nodes"])==4 and len(restored["links"])==3
            if dest:=os.environ.get("MCPBLENDER_VOLUME_EVIDENCE_DIR"):
                target=Path(dest);target.mkdir(parents=True,exist_ok=True)
                shutil.copytree(root/"library/fire-bundle",target/"fire-bundle",dirs_exist_ok=True)
                for name in ("fire.png","fire-off.png","smoke.png"):shutil.copy2(root/"library"/name,target/name)
                (target/"stats.json").write_text(json.dumps(stats,indent=2))
            visible = stats["fire.png"]["warm_pixels"] > stats["fire-off.png"]["warm_pixels"] + 30
            if not visible and os.environ.get("MCPBLENDER_EXPECT_EMPTY_CACHED_VOLUMES") == "1":
                pytest.xfail("Explicit host diagnostic: cached volume render is empty; verify Blender NanoVDB build support")
            assert visible, stats
    asyncio.run(run())


def test_homogeneous_volume_render_and_shader_roundtrip(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,"create_primitive",name="VolumeBox",location=[15,0,1])
            preset=await tool(client,"apply_material_preset",material="WarmVolume",preset="VOLUME",
                              volume_density=.5,volume_emission_strength=2,emission_color=[1,.03,.001,1])
            assert len(preset["nodes"])==2 and len(preset["links"])==1
            await tool(client,"assign_material",objects=["VolumeBox"],material="WarmVolume")
            await client.call_tool("run_action",{"action":"preview_setup","inputs":{"objects":["VolumeBox"],"prefix":"VolumeView"},"wait":True})
            await tool(client,"configure_render",samples=8)
            async def render(name):
                q=(await client.call_tool("submit_operation",{"command":"render_still","params":{"path":name,"width":192,"height":144,"camera":"VolumeView_Camera","engine":"CYCLES"}})).data
                done=(await client.call_tool("wait_operation",{"operation_id":q["operation_id"],"timeout_seconds":60})).data
                assert done["state"]=="succeeded",done
            await render("volume-on.png")
            await tool(client,"configure_shader_node",material="WarmVolume",node={"name":"Volume","type":"ShaderNodeVolumePrincipled","inputs":[{"socket":"Emission Strength","value":0}]})
            await render("volume-off.png")
            on,off=(image_stats(root/"library"/name) for name in ("volume-on.png","volume-off.png"))
            assert on["warm_pixels"]>off["warm_pixels"]+100,(on,off)
            await tool(client,"configure_shader_node",material="WarmVolume",node={"name":"SourceAttribute","type":"ShaderNodeAttribute","properties":{"attribute_name":"density","attribute_type":"GEOMETRY"}})
            await client.call_tool("save_blend",{"path":"volume-materials.blend"})
            await client.call_tool("open_blend",{"path":"volume-materials.blend"})
            graph=await tool(client,"inspect_shader_graph",material="WarmVolume")
            attribute=next(n for n in graph["nodes"] if n["name"]=="SourceAttribute")
            assert attribute["properties"]=={"attribute_name":"density","attribute_type":"GEOMETRY"}
            volume=next(n for n in graph["nodes"] if n["name"]=="Volume")
            assert next(i for i in volume["inputs"] if i["name"]=="Density Attribute")["default"]==""
            if dest:=os.environ.get("MCPBLENDER_VOLUME_EVIDENCE_DIR"):
                target=Path(dest);target.mkdir(parents=True,exist_ok=True)
                for name in ("volume-on.png","volume-off.png","volume-materials.blend"):
                    shutil.copy2(root/"library"/name,target/name)
    asyncio.run(run())
