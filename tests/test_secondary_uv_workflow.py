"""Code-disabled secondary UV creation with independent decoded channel delivery."""
import asyncio
import json

import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark


def test_secondary_map_preserves_primary_and_survives_export(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            await tool(client,'create_primitive',name='SecondaryBox',scale=[2,1,.5])
            await tool(client,'duplicate_object',name='SecondaryBox',new_name='SecondarySibling',linked_data=True,offset=[5,0,0])
            initial=await tool(client,'inspect_uv_layout',name='SecondaryBox',uv_map='UV2')
            assert not initial['exists'] and initial['uv_channel'] is None
            sibling=await tool(client,'inspect_uv_layout',name='SecondarySibling')
            geometry=await tool(client,'inspect_mesh_elements',name='SecondaryBox')
            params={'name':'SecondaryBox','expected_uv':initial['uv_sha256'],'texture_width':256,'texture_height':256}
            with pytest.raises(ToolError,match='shared'):
                await tool(client,'create_secondary_uv',**params)
            result=await tool(client,'create_secondary_uv',**params,make_single_user=True,
                              chart_layout={'min_area_pixels':64,'min_span_pixels':2,'gutter_pixels':4})
            assert result['uv_maps']==['UVMap','UV2'] and result['uv_channel']==1
            assert result['active_uv_map']==result['render_uv_map']=='UVMap'
            assert result['overlap']['complete'] and result['overlap']['face_pair_count']==0
            assert result['degenerate_islands']==0
            assert min(result['bounds']['min'])*256>=4
            assert min(1-v for v in result['bounds']['max'])*256>=4
            assert (await tool(client,'inspect_mesh_elements',name='SecondaryBox'))['geometry_sha256']==geometry['geometry_sha256']
            assert (await tool(client,'inspect_uv_layout',name='SecondarySibling'))['uv_sha256']==sibling['uv_sha256']
            with pytest.raises(ToolError,match='stale'):
                await tool(client,'create_secondary_uv',**params,make_single_user=True)
            with pytest.raises(ToolError,match='already exists'):
                await tool(client,'create_secondary_uv',name='SecondaryBox',expected_uv=result['uv_sha256'])
            quality=(await client.call_tool('inspect_texture_quality',{'params':{'name':'SecondaryBox','uv_map':'UV2','width':256,'height':256,'min_texels_per_meter':8,'padding_pixels':2,'mip_levels':1},'wait':True})).data
            assert quality['passed'],quality
            attrs=await tool(client,'inspect_mesh_attributes',name='SecondaryBox')
            await tool(client,'create_mesh_attribute',name='SecondaryBox',attribute='delivery_tag',data_type='FLOAT',value=.5,expected_attributes=attrs['attributes_sha256'])
            await client.call_tool('save_blend',{'path':'secondary.blend'})
            await client.call_tool('open_blend',{'path':'secondary.blend'})
            restored=await tool(client,'inspect_uv_layout',name='SecondaryBox',uv_map='UV2')
            assert restored['uv_sha256']==result['uv_sha256']
            options={'name':'SecondaryBox','fields':[{'attribute':'delivery_tag','semantic':'asset.delivery_tag'}]}
            plan=await tool(client,'inspect_attribute_export',**options)
            exported=await tool(client,'export_attribute_bundle',**options,expected_export=plan['export_sha256'],directory='secondary-delivery')
            assert exported['proof']['uv_channels']==2
            verified=await tool(client,'validate_attribute_bundle',directory='secondary-delivery')
            assert verified['proof']==exported['proof']
            manifest=json.loads((root/'library/secondary-delivery/manifest.json').read_text())
            assert manifest['source']['uv_maps']==['UVMap','UV2']
            assert manifest['witness']['uvs'][0]!=manifest['witness']['uvs'][1]
    asyncio.run(run())
