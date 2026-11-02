"""Real reusable procedural geometry via MCP with arbitrary Python disabled."""
import asyncio
import copy
import json
import os
from pathlib import Path
import shutil
import struct

import pytest
from fastmcp.exceptions import ToolError
from mcpblender.geometry_contracts import NODE_TYPES

from test_asset_editing import assets_live, client_for, tool, pytestmark


def graph_spec(group="Floors"):
    def value(socket, value):
        return {"socket": socket, "value": value}
    def link(source, output, target, input):
        return {"from_node": source, "from_socket": output, "to_node": target, "to_socket": input}
    return {"group": group,
            "inputs": [{"name": "Floors", "type": "INT", "default": 3}],
            "nodes": [{"name": "Params", "type": "NodeGroupInput"},
                      {"name": "Levels", "type": "GeometryNodeMeshLine", "inputs": [value("Offset", [0,0,2]), value("Start Location", [0,0,.5])]},
                      {"name": "Floor", "type": "GeometryNodeMeshCube", "inputs": [value("Size", [3,2,1])]},
                      {"name": "Instances", "type": "GeometryNodeInstanceOnPoints"},
                      {"name": "Mesh", "type": "GeometryNodeRealizeInstances"},
                      {"name": "Out", "type": "NodeGroupOutput"}],
            "links": [link("Params", "Floors", "Levels", "Count"),
                      link("Levels", "Mesh", "Instances", "Points"),
                      link("Floor", "Mesh", "Instances", "Instance"),
                      link("Instances", "Instances", "Mesh", "Geometry"),
                      link("Mesh", "Geometry", "Out", "Geometry")]}


def test_reusable_geometry_inputs_delivery_render_and_roundtrip(assets_live):
    root, path = assets_live
    async def run():
        async with client_for(path) as client:
            assert "execute_code" not in {t.name for t in await client.list_tools()}
            catalog = await tool(client, "geometry_node_catalog")
            assert catalog["node_types"] == list(NODE_TYPES)
            assert "GeometryNodeInstanceOnPoints" in catalog["node_types"]
            for node_type in catalog["node_types"]:
                entry = await tool(client, "geometry_node_catalog", node_type=node_type)
                assert entry["type"] == node_type
            await tool(client, "apply_material_preset", material="TowerPaint", base_color=[.2,.5,.7,1])
            spec = graph_spec()
            spec["nodes"].append({"name":"Paint", "type":"GeometryNodeSetMaterial", "material":"TowerPaint"})
            spec["links"][-1]["to_node"] = "Paint"
            spec["links"].append({"from_node":"Paint", "from_socket":"Geometry", "to_node":"Out", "to_socket":"Geometry"})
            graph = await tool(client, "configure_geometry_graph", **spec)
            assert graph["complete"] and len(graph["graph_sha256"]) == 64
            digest = graph["graph_sha256"]
            for name, x in (("TowerA", 10), ("TowerB", 15)):
                await tool(client, "create_primitive", name=name, location=[x,0,0])
                attached = await tool(client, "attach_geometry_nodes", name=name, group="Floors")
                assert attached["values"][0]["value"] == 3
            await tool(client, "configure_geometry_inputs", name="TowerA", expected_graph=digest,
                       values=[{"socket": "Floors", "value": 5}])
            a = await tool(client, "inspect_mesh", name="TowerA")
            b = await tool(client, "inspect_mesh", name="TowerB")
            assert (a["vertices"], b["vertices"]) == (40,24)
            assert a["world_bounds"] == {"min": [8.5,-1,0], "max": [11.5,1,9]}
            assert b["world_bounds"]["max"][2] == 5
            users = (await tool(client, "inspect_geometry_graph", group="Floors"))["modifier_users"]
            assert {u["name"]:u["values"][0]["value"] for u in users} == {"TowerA":5, "TowerB":3}
            original = await tool(client, "inspect_mesh", name="TowerA", evaluated=False)
            assert original["vertices"] == 8
            # Neither a stale guard nor a later bad input may partly apply the first value.
            for params in ({"expected_graph": "f"*64, "values": [{"socket": "Floors", "value": 1}]},
                           {"expected_graph": digest, "values": [{"socket": "Floors", "value": 1}, {"socket": "Missing", "value": 2}]},
                           {"expected_graph": digest, "values": [{"socket": "Floors", "value": 1.5}]}):
                with pytest.raises(ToolError):
                    await tool(client, "configure_geometry_inputs", name="TowerA", **params)
                assert (await tool(client, "inspect_mesh", name="TowerA"))["geometry_sha256"] == a["geometry_sha256"]
            with pytest.raises(ToolError, match="Detach"):
                await tool(client, "configure_geometry_graph", **(graph_spec() | {"replace": True, "expected_graph": digest}))
            # Reattaching the same graph preserves custom values; a conflicting group is refused.
            again = await tool(client, "attach_geometry_nodes", name="TowerA", group="Floors")
            assert again["values"][0]["value"] == 5
            await tool(client, "configure_geometry_graph", **graph_spec("OtherFloors"))
            with pytest.raises(ToolError, match="different"):
                await tool(client, "attach_geometry_nodes", name="TowerA", group="OtherFloors")
            await client.call_tool("set_object_transform", {"name":"Cube", "location":[-100,0,0]})
            await client.call_tool("run_action", {"action": "preview_setup", "inputs": {"objects": ["TowerA","TowerB"], "prefix": "NodeStage"}, "wait": True})
            await tool(client, "configure_render", resolution_x=192, resolution_y=144, samples=4)
            queued = (await client.call_tool("submit_operation", {"command": "render_still", "params": {"path": "procedural-towers.png", "width":192, "height":144, "camera":"NodeStage_Camera", "engine":"CYCLES"}})).data
            render = (await client.call_tool("wait_operation", {"operation_id": queued["operation_id"], "timeout_seconds":60})).data
            assert render["state"] == "succeeded", render
            await tool(client, "export_objects_glb", objects=["TowerA"], path="procedural-tower.glb", apply_modifiers=True)
            data = (root / "library/procedural-tower.glb").read_bytes()
            length = struct.unpack_from("<I", data, 12)[0]
            payload = json.loads(data[20:20+length])
            assert {node["name"] for node in payload["nodes"]} == {"TowerA"}
            assert payload["materials"][0]["name"] == "TowerPaint"
            position = payload["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
            assert payload["accessors"][position]["count"] >= 40
            assert payload["accessors"][position]["min"][1] == pytest.approx(0)
            assert payload["accessors"][position]["max"][1] == pytest.approx(9)
            await client.call_tool("save_blend", {"path": "procedural-towers.blend"})
            await client.call_tool("open_blend", {"path": "procedural-towers.blend"})
            assert (await tool(client, "inspect_geometry_graph", group="Floors"))["graph_sha256"] == digest
            assert (await tool(client, "inspect_mesh", name="TowerA"))["geometry_sha256"] == a["geometry_sha256"]
            assert (await tool(client, "inspect_mesh", name="TowerB"))["geometry_sha256"] == b["geometry_sha256"]
            await tool(client, "remove_modifier", name="TowerA", modifier="GeometryNodes")
            assert (await tool(client, "inspect_mesh", name="TowerA"))["vertices"] == 8
            assert (await tool(client, "inspect_mesh", name="TowerB"))["vertices"] == 24
            if directory := os.environ.get("MCPBLENDER_GEOMETRY_EVIDENCE_DIR"):
                dest = Path(directory);dest.mkdir(parents=True, exist_ok=True)
                for filename in ("procedural-towers.png", "procedural-towers.blend", "procedural-tower.glb"):
                    shutil.copy2(root / "library" / filename, dest / filename)
    asyncio.run(run())


def test_graph_preflight_refuses_invalid_edits_and_allows_unused_replacement(assets_live):
    _, path = assets_live
    async def run():
        async with client_for(path) as client:
            spec = graph_spec("PreflightGraph")
            created = await tool(client, "configure_geometry_graph", **spec)
            digest = created["graph_sha256"]
            invalid = []
            bad = copy.deepcopy(spec);bad["nodes"][1]["inputs"].append({"socket":"Missing", "value":1});invalid.append(bad)
            bad = copy.deepcopy(spec);bad["nodes"][1]["properties"] = {"operation":"ADD"};invalid.append(bad)
            bad = copy.deepcopy(spec);bad["links"][0]["from_socket"] = "Geometry";invalid.append(bad)
            bad = copy.deepcopy(spec);bad["links"] = [l for l in bad["links"] if l["from_node"] != "Floor"];bad["links"].append({"from_node":"Mesh", "from_socket":"Geometry", "to_node":"Instances", "to_socket":"Instance"});invalid.append(bad)
            bad = copy.deepcopy(spec);bad["nodes"][2]["inputs"].append({"socket":"Vertices X", "value":10000});invalid.append(bad)
            for bad in invalid:
                with pytest.raises(ToolError):
                    await tool(client, "configure_geometry_graph", **(bad | {"replace":True, "expected_graph":digest}))
                assert (await tool(client, "inspect_geometry_graph", group=spec["group"]))["graph_sha256"] == digest
            with pytest.raises(ToolError, match="stale"):
                await tool(client, "configure_geometry_graph", **(spec | {"replace":True, "expected_graph":"a"*64}))
            spec["inputs"][0]["default"] = 4
            replaced = await tool(client, "configure_geometry_graph", **(spec | {"replace":True, "expected_graph":digest}))
            assert replaced["graph_sha256"] != digest
            assert replaced["modifier_users"] == []
    asyncio.run(run())


def test_typed_interfaces_rotation_and_multi_input_join(assets_live):
    _, path = assets_live
    async def run():
        async with client_for(path) as client:
            def link(a, sa, b, sb):
                return {"from_node":a, "from_socket":sa, "to_node":b, "to_socket":sb}
            graph = await tool(client, "configure_geometry_graph", group="TypedInterfaces",
                inputs=[{"name":"Size", "type":"VECTOR", "default":[4,2,2]},
                        {"name":"Lift", "type":"FLOAT", "default":2.0},
                        {"name":"Move", "type":"BOOLEAN", "default":True}],
                nodes=[{"name":"In", "type":"NodeGroupInput"},
                       {"name":"Cube", "type":"GeometryNodeMeshCube"},
                       {"name":"XYZ", "type":"ShaderNodeCombineXYZ"},
                       {"name":"Lifted", "type":"GeometryNodeSetPosition"},
                       {"name":"Rotated", "type":"GeometryNodeTransform", "inputs":[{"socket":"Rotation", "value":[0,0,1.5707963267948966]}]},
                       {"name":"Joined", "type":"GeometryNodeJoinGeometry"},
                       {"name":"Out", "type":"NodeGroupOutput"}],
                links=[link("In","Size","Cube","Size"), link("In","Lift","XYZ","Z"),
                       link("In","Move","Lifted","Selection"), link("XYZ","Vector","Lifted","Offset"),
                       link("Cube","Mesh","Lifted","Geometry"), link("Lifted","Geometry","Rotated","Geometry"),
                       link("Rotated","Geometry","Joined","Geometry"), link("Cube","Mesh","Joined","Geometry"),
                       link("Joined","Geometry","Out","Geometry")])
            await tool(client,"create_primitive",name="TypedBox")
            await tool(client,"attach_geometry_nodes",name="TypedBox",group="TypedInterfaces")
            before = await tool(client,"inspect_mesh",name="TypedBox")
            assert before["vertices"] == 16
            assert before["world_bounds"]["max"][2] == pytest.approx(3)
            assert before["world_bounds"]["max"][1] == pytest.approx(2)
            changed = await tool(client,"configure_geometry_inputs",name="TypedBox",expected_graph=graph["graph_sha256"],
                values=[{"socket":"Move", "value":False}, {"socket":"Lift", "value":1.5}, {"socket":"Size", "value":[2,2,4]}])
            assert [v["value"] for v in changed["values"]] == [[2,2,4],1.5,False]
            after = await tool(client,"inspect_mesh",name="TypedBox")
            assert after["world_bounds"]["max"][2] == pytest.approx(2)
            for item in ({"socket":"Move", "value":1}, {"socket":"Size", "value":2}, {"socket":"Lift", "value":True}):
                with pytest.raises(ToolError):
                    await tool(client,"configure_geometry_inputs",name="TypedBox",expected_graph=graph["graph_sha256"],values=[item])
            assert (await tool(client,"inspect_mesh",name="TypedBox"))["geometry_sha256"] == after["geometry_sha256"]
            await tool(client,"create_shape_key",name="TypedBox",key="LiftCorner",vertices=[{"vertex":0,"value":[0,0,.25]}])
            with pytest.raises(ToolError, match="static meshes"):
                await tool(client,"export_objects_glb",objects=["TypedBox"],path="refused-morph.glb",apply_modifiers=True)
            # Normal export retains morphs and ignores Geometry Nodes by default.
            await tool(client,"export_objects_glb",objects=["TypedBox"],path="base-morph.glb")
            data = (path.parent / "library/base-morph.glb").read_bytes()
            length = struct.unpack_from("<I", data, 12)[0]
            payload = json.loads(data[20:20+length])
            assert len(payload["meshes"][0]["primitives"][0]["targets"]) == 1
    asyncio.run(run())
