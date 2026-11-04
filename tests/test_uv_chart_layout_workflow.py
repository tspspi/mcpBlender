"""Code-disabled chart allocation separates overlapping source charts."""
import asyncio
from fastmcp.exceptions import ToolError
import pytest
from test_asset_editing import assets_live,client_for,tool,pytestmark


def test_pixel_layout_guarded_publish_and_mip_readback(assets_live):
    _,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_mesh',name='Charts',vertices=[[0,0,0],[1,0,0],[0,1,0],[0,0,.1],[1,0,.1],[0,1,.1]],faces=[[0,1,2],[3,4,5]])
            await tool(client,'generate_uv',name='Charts',method='CUBE')
            before=await tool(client,'inspect_uv_layout',name='Charts')
            assert before['overlap']['face_pair_count']==1
            geometry=await tool(client,'inspect_mesh',name='Charts',evaluated=False)
            await tool(client,'duplicate_object',name='Charts',new_name='Sibling',linked_data=True,offset=[2,0,0])
            args={'name':'Charts','expected_uv':before['uv_sha256'],'texture_width':128,'texture_height':128,'tile_padding_pixels':8,'make_single_user':True}
            with pytest.raises(ToolError,match='Minimum chart'):
                await tool(client,'pack_uv_islands',**args,chart_layout={'min_area_pixels':1048576})
            assert (await tool(client,'inspect_uv_layout',name='Charts'))['uv_sha256']==before['uv_sha256']
            with pytest.raises(ToolError,match='shared'):
                await tool(client,'pack_uv_islands',**(args|{'make_single_user':False}),chart_layout={})
            sibling=await tool(client,'inspect_uv_layout',name='Sibling')
            result=await tool(client,'pack_uv_islands',**args,chart_layout={'min_area_pixels':64,'min_span_pixels':2,'gutter_pixels':4})
            assert result['chart_layout']['method']=='PCA_PIXEL_SHELF_V1' and result['island_count']==2
            assert result['overlap']['complete'] and result['overlap']['face_pair_count']==0
            assert (await tool(client,'inspect_mesh',name='Charts',evaluated=False))['geometry_sha256']==geometry['geometry_sha256']
            assert (await tool(client,'inspect_uv_layout',name='Sibling'))['uv_sha256']==sibling['uv_sha256']
            report=(await client.call_tool('inspect_texture_quality',{'params':{'name':'Charts','width':128,'height':128,'min_texels_per_meter':32,'min_chart_pixels':4,'padding_pixels':2,'mip_levels':1},'wait':True})).data
            assert report['passed'],report
            await client.call_tool('save_blend',{'path':'pixel-charts.blend'})
            await client.call_tool('open_blend',{'path':'pixel-charts.blend'})
            assert (await tool(client,'inspect_uv_layout',name='Charts'))['uv_sha256']==result['uv_sha256']
    asyncio.run(run())
