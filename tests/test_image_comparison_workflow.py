"""Code-disabled MCP comparisons return metrics without recovery/scene edits."""
import asyncio
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_image_comparison import png
from test_botanical_trees import wait


def test_png_comparison_mcp(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    source=png(4,4,[255,128,0,255,0,0,0,0]*8,filter=4)
    (library/'source.png').write_bytes(source)
    (library/'copy.png').write_bytes(source)
    (library/'lost.png').write_bytes(png(4,4,[0,0,0,0]*16))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            before=(await client.call_tool('get_scene_info',{})).data
            result=await wait(client,'compare_png_images',reference='source.png',candidate='copy.png')
            assert result['passed'] and 'recovery' not in result and result['levels'][0]['mask_iou']==1
            lost=await wait(client,'compare_png_images',reference='source.png',candidate='lost.png')
            assert not lost['passed'] and lost['levels'][0]['missing_fraction']==1 and 'recovery' not in lost
            with pytest.raises(ToolError):await wait(client,'compare_png_images',reference='../private.png',candidate='copy.png')
            after=(await client.call_tool('get_scene_info',{})).data
            assert {k:v for k,v in before.items() if k!='operation_id'}=={k:v for k,v in after.items() if k!='operation_id'}
    asyncio.run(run())
