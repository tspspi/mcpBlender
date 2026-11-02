"""Real parameterized buildings, vegetation scattering and generated-asset refinement."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import struct

import pytest
from fastmcp.exceptions import ToolError

from test_asset_editing import assets_live, client_for, tool, pytestmark
from test_shaders import png


def glb(path):
    data = path.read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    return json.loads(data[20:20+length])


def test_textured_building_and_shared_preset_roundtrip(assets_live):
    root, path = assets_live
    library = root / "library";library.mkdir(exist_ok=True)
    png(library / "brick.png", lambda x,y: (155, 100, 65) if y%4 and (x+(4 if y//4%2 else 0))%8 else (215,210,190))
    async def run():
        async with client_for(path) as client:
            assert "execute_code" not in {t.name for t in await client.list_tools()}
            await tool(client,"apply_material_preset", material="Brick", preset="TEXTURED_PBR",base_color_texture="brick.png",texture_scale=[4,4,4])
            await tool(client,"apply_material_preset", material="Windows", base_color=[.04,.13,.2,1],metallic=.6,roughness=.2)
            await tool(client,"apply_material_preset", material="Roof", base_color=[.12,.14,.16,1])
            graph = await tool(client,"create_geometry_preset", group="BuildingRecipe", settings={"type":"BUILDING","floors":2,
                "wall_material":"Brick","window_material":"Windows","roof_material":"Roof"})
            assert graph["preset"] == {"type":"BUILDING","version":1}
            floors = next(s for s in graph["inputs_outputs"] if s["name"]=="Floors")
            assert (floors["minimum"],floors["maximum"]) == (1,32)
            with pytest.raises(ToolError,match="Material not found"):
                await tool(client,"create_geometry_preset",group="BuildingRecipe",replace=True,expected_graph=graph["graph_sha256"],
                           settings={"type":"BUILDING","wall_material":"MissingMaterial"})
            assert (await tool(client,"inspect_geometry_graph",group="BuildingRecipe"))["graph_sha256"]==graph["graph_sha256"]
            for name,x in (("BuildingA",10),("BuildingB",20)):
                await tool(client,"create_primitive", name=name, location=[x,0,0])
                await tool(client,"attach_geometry_nodes", name=name,group="BuildingRecipe")
            before = await tool(client,"inspect_mesh",name="BuildingA")
            assert before["world_bounds"]["max"][2] == pytest.approx(6.2)
            assert before["vertices"] == 8*(2+2*2*3)
            assert before["uv_layers"] and before["uv_layers"][0]["zero_area_faces"] == 0
            await tool(client,"configure_geometry_inputs",name="BuildingA",expected_graph=graph["graph_sha256"],values=[{"socket":"Floors","value":3}])
            after = await tool(client,"inspect_mesh",name="BuildingA")
            assert after["world_bounds"]["max"][2] == pytest.approx(9.2)
            assert (await tool(client,"inspect_mesh",name="BuildingB"))["world_bounds"]["max"][2] == pytest.approx(6.2)
            for value in (0,33):
                with pytest.raises(ToolError,match="minimum/maximum"):
                    await tool(client,"configure_geometry_inputs",name="BuildingA",expected_graph=graph["graph_sha256"],values=[{"socket":"Floors","value":value}])
            assert (await tool(client,"inspect_mesh",name="BuildingA"))["geometry_sha256"] == after["geometry_sha256"]
            await client.call_tool("set_object_transform",{"name":"Cube","location":[-100,0,0]})
            await client.call_tool("run_action",{"action":"preview_setup","inputs":{"objects":["BuildingA","BuildingB"],"prefix":"Buildings"},"wait":True})
            await tool(client,"configure_render",resolution_x=320,resolution_y=240,samples=12)
            queued = (await client.call_tool("submit_operation",{"command":"render_still","params":{"path":"buildings.png","width":320,"height":240,"camera":"Buildings_Camera","engine":"CYCLES"}})).data
            done = (await client.call_tool("wait_operation",{"operation_id":queued["operation_id"],"timeout_seconds":60})).data
            assert done["state"]=="succeeded",done
            await tool(client,"export_objects_glb",objects=["BuildingA"],path="building.glb",apply_modifiers=True)
            model = glb(library / "building.glb")
            assert len(model["materials"]) == 3 and model["textures"]
            assert any("baseColorTexture" in m.get("pbrMetallicRoughness",{}) for m in model["materials"])
            assert {n["name"] for n in model["nodes"]} == {"BuildingA"}
            await client.call_tool("save_blend",{"path":"buildings.blend"})
            await client.call_tool("open_blend",{"path":"buildings.blend"})
            restored = await tool(client,"inspect_geometry_graph",group="BuildingRecipe")
            assert restored["graph_sha256"]==graph["graph_sha256"]
            assert (await tool(client,"inspect_mesh",name="BuildingA"))["geometry_sha256"]==after["geometry_sha256"]
            with pytest.raises(ToolError,match="minimum/maximum"):
                await tool(client,"configure_geometry_inputs",name="BuildingA",expected_graph=restored["graph_sha256"],values=[{"socket":"Floors","value":100}])
            if directory:=os.environ.get("MCPBLENDER_PRESET_EVIDENCE_DIR"):
                dest=Path(directory);dest.mkdir(parents=True,exist_ok=True)
                for filename in ("buildings.png","buildings.blend","building.glb"):
                    shutil.copy2(library/filename,dest/filename)
    asyncio.run(run())


def test_trees_seeded_surface_scatter_and_candidate_budget(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            await tool(client,"apply_material_preset",material="Bark",base_color=[.22,.09,.025,1])
            await tool(client,"apply_material_preset",material="Leaves",base_color=[.035,.25,.06,1])
            settings={"trunk_material":"Bark","leaf_material":"Leaves"}
            tree=await tool(client,"create_geometry_preset",group="Pine",settings={"type":"VEGETATION"}|settings)
            await tool(client,"create_primitive",name="Tree",location=[10,10,0])
            await tool(client,"attach_geometry_nodes",name="Tree",group="Pine")
            original=await tool(client,"inspect_mesh",name="Tree")
            assert original["world_bounds"]["min"][2] == pytest.approx(0)
            assert original["world_bounds"]["max"][2] == pytest.approx(3)
            assert original["uv_layers"]
            scatter=await tool(client,"create_geometry_preset",group="Forest",settings={"type":"SCATTER_VEGETATION","density":2,"spacing":.4,"max_points":5,"seed":17}|settings)
            await tool(client,"create_mesh",name="Ground",vertices=[[-4,-4,0],[4,-4,0],[4,4,0],[-4,4,0]],faces=[[0,1,2,3]])
            attached=await tool(client,"attach_geometry_nodes",name="Ground",group="Forest")
            assert attached["workload"]["candidate_estimate"]==128
            assert attached["workload"]["max_points"]==5
            forest=await tool(client,"inspect_mesh",name="Ground")
            assert forest["vertices"]==4+5*original["vertices"]
            await tool(client,"configure_geometry_inputs",name="Ground",expected_graph=scatter["graph_sha256"],values=[{"socket":"MaxPoints","value":2}])
            assert (await tool(client,"inspect_mesh",name="Ground"))["vertices"]==4+2*original["vertices"]
            await tool(client,"configure_geometry_inputs",name="Ground",expected_graph=scatter["graph_sha256"],values=[{"socket":"MaxPoints","value":5}])
            await tool(client,"configure_geometry_inputs",name="Ground",expected_graph=scatter["graph_sha256"],values=[{"socket":"Seed","value":18}])
            changed=await tool(client,"inspect_mesh",name="Ground")
            assert changed["vertices"]==forest["vertices"] and changed["geometry_sha256"]!=forest["geometry_sha256"]
            await tool(client,"configure_geometry_inputs",name="Ground",expected_graph=scatter["graph_sha256"],values=[{"socket":"Seed","value":17}])
            assert (await tool(client,"inspect_mesh",name="Ground"))["geometry_sha256"]==forest["geometry_sha256"]
            await tool(client,"create_mesh",name="WallSurface",vertices=[[-4,0,-4],[-4,0,4],[4,0,4],[4,0,-4]],faces=[[0,1,2,3]])
            await tool(client,"attach_geometry_nodes",name="WallSurface",group="Forest")
            wall=await tool(client,"inspect_mesh",name="WallSurface")
            assert wall["world_bounds"]["min"][1]==pytest.approx(0,abs=1e-6)
            assert wall["world_bounds"]["max"][1]==pytest.approx(3,abs=1e-6), "Tree axis must follow the surface normal"
            await tool(client,"create_mesh",name="HugeGround",vertices=[[-100,-100,0],[100,-100,0],[100,100,0],[-100,100,0]],faces=[[0,1,2,3]])
            with pytest.raises(ToolError,match="candidate estimate"):
                await tool(client,"attach_geometry_nodes",name="HugeGround",group="Forest")
            assert not (await tool(client,"inspect_mesh",name="HugeGround",evaluated=False))["modifiers"]
            await tool(client,"create_mesh",name="MidGround",vertices=[[-20,-20,0],[20,-20,0],[20,20,0],[-20,20,0]],faces=[[0,1,2,3]])
            await tool(client,"attach_geometry_nodes",name="MidGround",group="Forest")
            before=await tool(client,"inspect_mesh",name="MidGround")
            with pytest.raises(ToolError,match="candidate estimate"):
                await tool(client,"configure_geometry_inputs",name="MidGround",expected_graph=scatter["graph_sha256"],values=[{"socket":"Height","value":4},{"socket":"Density","value":50}])
            assert (await tool(client,"inspect_mesh",name="MidGround"))["geometry_sha256"]==before["geometry_sha256"]
            # Do not include the large budget-test surfaces in this preview.
            scene=(await client.call_tool("get_scene_info")).data
            for i,obj in enumerate(scene["objects"]):
                if obj["type"]=="MESH" and obj["name"] not in {"Ground","Tree"}:
                    await client.call_tool("set_object_transform",{"name":obj["name"],"location":[1000+200*i,0,0]})
            await client.call_tool("run_action",{"action":"preview_setup","inputs":{"objects":["Ground","Tree"],"prefix":"ForestView"},"wait":True})
            await tool(client,"configure_render",resolution_x=320,resolution_y=240,samples=12)
            queued=(await client.call_tool("submit_operation",{"command":"render_still","params":{"path":"forest.png","width":320,"height":240,"camera":"ForestView_Camera","engine":"CYCLES"}})).data
            done=(await client.call_tool("wait_operation",{"operation_id":queued["operation_id"],"timeout_seconds":60})).data
            assert done["state"]=="succeeded",done
            await client.call_tool("save_blend",{"path":"forest.blend"})
            await client.call_tool("open_blend",{"path":"forest.blend"})
            assert (await tool(client,"inspect_mesh",name="Ground"))["geometry_sha256"]==forest["geometry_sha256"]
            await tool(client,"export_objects_glb",objects=["Ground"],path="forest.glb",apply_modifiers=True)
            assert len(glb(root/"library/forest.glb")["materials"])==2
            if directory:=os.environ.get("MCPBLENDER_PRESET_EVIDENCE_DIR"):
                dest=Path(directory);dest.mkdir(parents=True,exist_ok=True)
                for filename in ("forest.png","forest.blend","forest.glb"):
                    shutil.copy2(root/"library"/filename,dest/filename)
    asyncio.run(run())


def test_generated_mesh_refinement_and_preserved_source(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            graph=await tool(client,"create_geometry_preset",group="Refine",settings={"type":"REFINE_MESH","levels":1})
            await tool(client,"create_primitive",name="GeneratedAsset")
            base=await tool(client,"inspect_mesh",name="GeneratedAsset",evaluated=False)
            await tool(client,"attach_geometry_nodes",name="GeneratedAsset",group="Refine")
            assert (await tool(client,"inspect_mesh",name="GeneratedAsset"))["polygons"]==24
            await tool(client,"configure_geometry_inputs",name="GeneratedAsset",expected_graph=graph["graph_sha256"],values=[{"socket":"Levels","value":2}])
            assert (await tool(client,"inspect_mesh",name="GeneratedAsset"))["polygons"]==96
            assert (await tool(client,"inspect_mesh",name="GeneratedAsset",evaluated=False))["geometry_sha256"]==base["geometry_sha256"]
            with pytest.raises(ToolError,match="minimum/maximum"):
                await tool(client,"configure_geometry_inputs",name="GeneratedAsset",expected_graph=graph["graph_sha256"],values=[{"socket":"Levels","value":4}])
            await tool(client,"create_shape_key",name="GeneratedAsset",key="Smile")
            with pytest.raises(ToolError,match="static meshes"):
                await tool(client,"configure_geometry_inputs",name="GeneratedAsset",expected_graph=graph["graph_sha256"],values=[{"socket":"Levels","value":1}])
            await tool(client,"create_geometry_preset",group="BudgetRefine",settings={"type":"REFINE_MESH","levels":3})
            vertices=[[x,y,0] for y in range(65) for x in range(65)]
            faces=[[y*65+x,y*65+x+1,(y+1)*65+x+1,(y+1)*65+x] for y in range(64) for x in range(64)]
            await tool(client,"create_mesh",name="DenseGenerated",vertices=vertices,faces=faces)
            with pytest.raises(ToolError,match="face estimate"):
                await tool(client,"attach_geometry_nodes",name="DenseGenerated",group="BudgetRefine")
            assert not (await tool(client,"inspect_mesh",name="DenseGenerated",evaluated=False))["modifiers"]
            await tool(client,"create_primitive",name="Upstream")
            await tool(client,"configure_modifier",name="Upstream",modifier="Bevel",settings={"type":"BEVEL"})
            with pytest.raises(ToolError,match="first modifier"):
                await tool(client,"attach_geometry_nodes",name="Upstream",group="Refine")
            assert len((await tool(client,"inspect_mesh",name="Upstream",evaluated=False))["modifiers"])==1
    asyncio.run(run())
