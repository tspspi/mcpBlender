"""Real base-mesh editing through typed MCP tools, with Python disabled."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import struct

import pytest
from fastmcp.exceptions import ToolError

from test_asset_editing import assets_live as base_assets_live, client_for, tool, pytestmark


@pytest.fixture(scope="module")
def assets_live():
    fixture = base_assets_live.__wrapped__()
    root, path = next(fixture)
    try:
        yield root, path
    finally:
        if directory := os.environ.get("MCPBLENDER_MESH_EVIDENCE_DIR"):
            dest = Path(directory);dest.mkdir(parents=True, exist_ok=True)
            if (root / "blender.log").exists():
                shutil.copy2(root / "blender.log", dest / "blender.log")
        fixture.close()


def guard(info, **extra):
    return {"name": info["name"], "expected_topology": info["topology_sha256"],
            "expected_geometry": info["geometry_sha256"]} | extra


def test_named_roof_extrusion_inset_render_and_roundtrip(assets_live):
    root, path = assets_live
    async def run():
        async with client_for(path) as c:
            names = {t.name for t in await c.list_tools()}
            assert "extrude_mesh_faces" in names and "execute_code" not in names
            await tool(c, "create_primitive", name="EditBuilding", location=[12,0,1])
            base = await tool(c, "inspect_mesh_elements", name="EditBuilding")
            assert base["signed_local_volume"] == pytest.approx(8)
            top = max(base["elements"], key=lambda f: f["center"][2])["index"]
            selected = await tool(c, "select_mesh_elements", **guard(base), domain="FACE",
                                  elements={"indices": [top]}, selection_name="Roof")
            assert selected["named_selections"][0]["valid"]
            extrusion = {"params": guard(base) | {"faces": {"selection": "Roof"}, "offset": [0, 0, 1]}, "request_id": "building-roof-extension"}
            raised = (await c.call_tool("extrude_mesh_faces", extrusion)).data
            assert raised["signed_local_volume"] == pytest.approx(12)
            assert not raised["named_selections"][0]["valid"]
            with pytest.raises(ToolError, match="topology"):
                await tool(c, "extrude_mesh_faces", **guard(base), faces={"indices": [top]}, offset=[0, 0, 1])
            with pytest.raises(ToolError, match="stale"):
                await tool(c, "inset_mesh_faces", **guard(raised), faces={"selection": "Roof"}, thickness=.2)
            top = max(raised["elements"], key=lambda f: f["center"][2])["index"]
            inset = await tool(c, "inset_mesh_faces", **guard(raised), faces={"indices": [top]}, thickness=.2)
            assert inset["vertices"] > raised["vertices"] and inset["signed_local_volume"] == pytest.approx(12)
            mesh = await tool(c, "inspect_mesh", name="EditBuilding", evaluated=False)
            assert mesh["topology"]["non_manifold_edges"] == 0
            assert mesh["uv_layers"], "Existing UV data must survive edits"
            before_restart = (await c.call_tool("bridge_status")).data["bridge"]
            restarted = (await c.call_tool("restart_bridge")).data
            assert restarted["pid"] == before_restart["pid"]
            deduplicated = (await c.call_tool("extrude_mesh_faces", extrusion)).data
            assert deduplicated["operation_id"] == raised["operation_id"]
            assert (await tool(c, "inspect_mesh_elements", name="EditBuilding"))["geometry_sha256"] == inset["geometry_sha256"]
            await tool(c, "apply_material_preset", material="EditPaint", preset="PBR", base_color=[.12, .45, .65, 1])
            await tool(c, "assign_material", objects=["EditBuilding"], material="EditPaint")
            await tool(c, "configure_render", resolution_x=192, resolution_y=144, samples=4)
            stage = (await c.call_tool("run_action", {"action": "preview_setup", "inputs": {"objects": ["EditBuilding"], "prefix": "EditStage"}, "wait": True})).data
            assert stage["state"] == "succeeded"
            q = (await c.call_tool("submit_operation", {"command": "render_still", "params": {"path": "edited-building.png", "width": 192, "height": 144, "camera": "EditStage_Camera", "engine": "CYCLES"}})).data
            done = (await c.call_tool("wait_operation", {"operation_id": q["operation_id"], "timeout_seconds": 60})).data
            assert done["state"] == "succeeded", done
            await c.call_tool("save_blend", {"path": "edited-building.blend"})
            await c.call_tool("open_blend", {"path": "edited-building.blend"})
            restored = await tool(c, "inspect_mesh_elements", name="EditBuilding")
            assert restored["topology_sha256"] == inset["topology_sha256"]
            assert restored["geometry_sha256"] == inset["geometry_sha256"]
            assert restored["named_selections"][0]["valid"] is False
            removed = await tool(c, "remove_mesh_selection", name="EditBuilding", selection_name="Roof")
            assert not removed["named_selections"] and removed["geometry_sha256"] == restored["geometry_sha256"]
            if directory := os.environ.get("MCPBLENDER_MESH_EVIDENCE_DIR"):
                dest = Path(directory);dest.mkdir(parents=True, exist_ok=True)
                for filename in ("edited-building.png", "edited-building.blend"):
                    shutil.copy2(root / "library" / filename, dest / filename)
    asyncio.run(run())


def test_loop_cuts_shared_data_guards_and_normal_repair(assets_live):
    _, path = assets_live
    async def run():
        async with client_for(path) as c:
            await tool(c, "create_primitive", name="LoopBox")
            await tool(c, "duplicate_object", name="LoopBox", new_name="LoopTwin", linked_data=True)
            before = await tool(c, "inspect_mesh_elements", name="LoopBox", domain="EDGE", limit=2)
            assert before["next_offset"] == 2 and before["data_users"] == 2
            with pytest.raises(ToolError, match="shared"):
                await tool(c, "loop_cut_mesh", **guard(before), edge=0)
            with pytest.raises(ToolError, match="range"):
                await tool(c, "loop_cut_mesh", **guard(before), edge=10000, make_single_user=True)
            unchanged = await tool(c, "inspect_mesh_elements", name="LoopBox")
            assert unchanged["data_users"] == 2 and unchanged["mesh_data"] == before["mesh_data"]
            cut = await tool(c, "loop_cut_mesh", **guard(before), edge=0, cuts=2, make_single_user=True)
            assert cut["data_users"] == 1 and cut["vertices"] == 16
            assert cut["signed_local_volume"] == pytest.approx(8)
            twin = await tool(c, "inspect_mesh_elements", name="LoopTwin")
            assert twin["vertices"] == 8 and twin["topology_sha256"] == before["topology_sha256"]
            inside = await tool(c, "repair_mesh_normals", **guard(cut), direction="INSIDE")
            assert inside["signed_local_volume"] == pytest.approx(-8)
            outside = await tool(c, "repair_mesh_normals", **guard(inside), direction="OUTSIDE")
            assert outside["signed_local_volume"] == pytest.approx(8)
            with pytest.raises(ToolError, match="geometry"):
                await tool(c, "cleanup_mesh", **(guard(outside) | {"expected_geometry": "0" * 64}))
            await tool(c, "create_mesh", name="TriangleCut", vertices=[[0,0,0],[1,0,0],[0,1,0]], faces=[[0,1,2]])
            triangle = await tool(c, "inspect_mesh_elements", name="TriangleCut")
            with pytest.raises(ToolError, match="non-quad"):
                await tool(c, "loop_cut_mesh", **guard(triangle), edge=0)
            assert (await tool(c, "inspect_mesh_elements", name="TriangleCut"))["geometry_sha256"] == triangle["geometry_sha256"]
            await tool(c, "create_shape_key", name="TriangleCut", key="Flex")
            with pytest.raises(ToolError, match="shape keys"):
                await tool(c, "cleanup_mesh", **guard(triangle))
    asyncio.run(run())


def test_vertex_merge_cleanup_and_boolean_delivery(assets_live):
    root, path = assets_live
    async def run():
        async with client_for(path) as c:
            await tool(c, "create_mesh", name="DirtyPanel", vertices=[[0,0,0],[2,0,0],[2,2,0],[0,2,0],[0,0,0],[9,9,9]], faces=[[0,1,2,3],[4,3,2]])
            before = await tool(c, "inspect_mesh_elements", name="DirtyPanel", domain="VERTEX")
            await tool(c, "select_mesh_elements", **guard(before), domain="VERTEX", elements={"indices": [0,4]}, selection_name="Seam")
            merged = await tool(c, "merge_mesh_vertices", **guard(before), vertices={"selection": "Seam"})
            assert merged["vertices"] == 5
            clean = await tool(c, "cleanup_mesh", **guard(merged))
            assert clean["vertices"] == 4
            assert (await tool(c, "inspect_mesh", name="DirtyPanel", evaluated=False))["topology"]["loose_vertices"] == 0
            await tool(c, "create_primitive", name="BoolShell")
            await tool(c, "create_primitive", name="BoolCutter", scale=[.5,.5,2])
            await tool(c, "configure_modifier", name="BoolShell", modifier="Hole", settings={"type":"BOOLEAN","object":"BoolCutter"})
            with pytest.raises(ToolError, match="cycle"):
                await tool(c, "configure_modifier", name="BoolCutter", modifier="Cycle", settings={"type":"BOOLEAN","object":"BoolShell"})
            evaluated = await tool(c, "inspect_mesh", name="BoolShell")
            assert evaluated["topology"]["non_manifold_edges"] == 0
            assert evaluated["polygons"] > 6
            await tool(c, "apply_modifier", name="BoolShell", modifier="Hole")
            applied = await tool(c, "inspect_mesh", name="BoolShell", evaluated=False)
            assert applied["polygons"] == evaluated["polygons"]
            solid = await tool(c, "inspect_mesh_elements", name="BoolShell")
            assert solid["signed_local_volume"] == pytest.approx(6)
            for operation, volume in (("UNION", 10), ("INTERSECT", 2)):
                name = "Bool" + operation
                await tool(c, "create_primitive", name=name)
                await tool(c, "configure_modifier", name=name, modifier="Combine", settings={"type":"BOOLEAN", "object":"BoolCutter", "operation":operation})
                await tool(c, "apply_modifier", name=name, modifier="Combine")
                assert (await tool(c, "inspect_mesh_elements", name=name))["signed_local_volume"] == pytest.approx(volume)
            await tool(c, "export_objects_glb", objects=["BoolShell"], path="boolean-shell.glb")
            data = (root / "library/boolean-shell.glb").read_bytes()
            size = struct.unpack_from("<I", data, 12)[0]
            gltf = json.loads(data[20:20 + size])
            assert [n["name"] for n in gltf["nodes"]] == ["BoolShell"]
    asyncio.run(run())
