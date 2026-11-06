"""Capability discovery must make unimplemented typed workflows explicit."""
import asyncio
import os
import shutil

import pytest

from mcpblender.blender.capabilities import WORKFLOWS, workflow_support
from mcpblender.commands import DOMAIN_COMMANDS
from test_asset_editing import assets_live, client_for, tool


def test_workflow_inventory_does_not_claim_unregistered_commands():
    commands = set(DOMAIN_COMMANDS) | {"run_action"}
    for methods, _ in WORKFLOWS.values():
        assert methods <= commands
    support = workflow_support(commands)
    assert "extrude_mesh_faces" in support["mesh_modeling"]["structured_commands"]
    assert "create_botanical_depth_asset" in support["botanical_directional_depth"]["structured_commands"]
    assert "capture_botanical_projected_coverage" in support["botanical_reference_capture"]["structured_commands"]
    assert "create_botanical_subset" in support["botanical_native_subsets"]["structured_commands"]
    assert support["shader_nodes"]["support"] == "structured_partial"
    assert support["geometry_nodes"]["support"] == "structured_partial"
    assert support["physics"]["support"] == "structured_partial"
    assert support["simulation_baking"]["support"] == "structured_partial"
    assert support["particles"]["support"] == "structured_partial"
    assert support["fluids"]["support"] == "structured_partial"
    assert support["compositing"]["support"] == "structured_partial"
    assert "configure_compositor_graph" in support["compositing"]["structured_commands"]
    # A missing worker command must never be advertised through a static mapping.
    assert workflow_support(set())["mesh_modeling"]["structured_commands"] == []


@pytest.mark.blender
@pytest.mark.skipif(os.environ.get("MCPBLENDER_TEST_BLENDER") != "1" or not shutil.which("blender"),
                    reason="Set MCPBLENDER_TEST_BLENDER=1 to use an installed Blender")
def test_live_capability_discovery_with_python_disabled(assets_live):
    _, path = assets_live

    async def run():
        async with client_for(path) as client:
            tools = {t.name for t in await client.list_tools()}
            assert "execute_code" not in tools
            before = (await client.call_tool("bridge_status")).data["bridge"].get("checkpoint_path")
            result = await tool(client, "get_capabilities")
            assert result["operations_protocol"] == 2
            assert set(result["domains"]) == set(result["domain_support"])
            assert "particles" not in result["python_only_domains"]
            assert "geometry_nodes" not in result["python_only_domains"]
            assert "attach_geometry_nodes" in result["domain_support"]["geometry_nodes"]["structured_commands"]
            assert "configure_shader_graph" in result["domain_support"]["shader_nodes"]["structured_commands"]
            assert "extrude_mesh_faces" in result["domain_support"]["mesh_modeling"]["structured_commands"]
            assert "create_botanical_depth_asset" in result["domain_support"]["botanical_directional_depth"]["structured_commands"]
            assert "not caller authorization" in result["discovery_note"]
            assert "not qualification" in result["discovery_note"]
            for domain in result["domain_support"].values():
                assert set(domain["structured_commands"]) <= set(result["structured_commands"])
            after = (await client.call_tool("bridge_status")).data["bridge"].get("checkpoint_path")
            assert after == before
    asyncio.run(run())
