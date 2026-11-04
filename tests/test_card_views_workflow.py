"""Typed readonly family plans feed existing guarded creation without Python."""
import asyncio
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_trees import wait


def test_view_plan_mcp_budgets_and_creation(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            before=(await client.call_tool('get_scene_info')).data
            plan=await wait(client,'inspect_foliage_card_views',sources=['Cube'])
            assert 'recovery' not in plan and plan['projected_triangles']==36
            after=(await client.call_tool('get_scene_info')).data
            assert {k:v for k,v in before.items() if k!='operation_id'}=={k:v for k,v in after.items() if k!='operation_id'}
            with pytest.raises(ToolError,match='projected triangle'):
                await wait(client,'inspect_foliage_card_views',sources=['Cube'],max_projected_triangles=35)
            for row in plan['views']:
                result=await wait(client,'create_foliage_card',**row['create_parameters'],name='Family_'+row['view'])
                assert result['card']['card_sha256']==row['card']['card_sha256'] and result['bake_inspection']['complete']
    asyncio.run(run())
