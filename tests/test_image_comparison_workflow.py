"""Code-disabled MCP comparisons return metrics without recovery/scene edits."""
import asyncio
import os
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
    (library/'soft.png').write_bytes(png(4,4,[255,128,0,64]*16))
    (library/'lost.png').write_bytes(png(4,4,[0,0,0,0]*16))
    (library/'dark.png').write_bytes(png(2,2,[10,10,10,255]*4))
    (library/'bright.png').write_bytes(png(2,2,[20,20,20,255]*4))
    (library/'dim.png').write_bytes(png(2,2,[5,5,5,255]*4))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            before=(await client.call_tool('get_scene_info',{})).data
            result=await wait(client,'compare_png_images',reference='source.png',candidate='copy.png')
            assert result['passed'] and 'recovery' not in result and result['levels'][0]['mask_iou']==1
            lost=await wait(client,'compare_png_images',reference='source.png',candidate='lost.png')
            assert not lost['passed'] and lost['levels'][0]['missing_fraction']==1 and 'recovery' not in lost
            soft=await wait(client,'compare_png_images',reference='soft.png',candidate='soft.png',quality={'min_mask_iou':None,'max_overlap_rgb_rmse':.01})
            assert soft['passed'] and soft['policy']['min_mask_iou'] is None and soft['levels'][0]['overlap_rgb_rmse']==0
            with pytest.raises(ToolError):await wait(client,'compare_png_images',reference='../private.png',candidate='copy.png')
            for candidate in ('bright.png','dim.png'):
                default=await wait(client,'compare_png_images',reference='dark.png',candidate=candidate)
                assert default['passed']
                strict=await wait(client,'compare_png_images',reference='dark.png',candidate=candidate,quality={'max_abs_overlap_luminance_relative_bias':.1})
                assert not strict['passed'] and 'max_abs_overlap_luminance_relative_bias' in strict['levels'][0]['failures']
            disabled=await wait(client,'compare_png_images',reference='dark.png',candidate='bright.png',quality={'max_abs_overlap_luminance_relative_bias':None})
            assert disabled['passed'] and disabled['policy']['max_abs_overlap_luminance_relative_bias'] is None
            after=(await client.call_tool('get_scene_info',{})).data
            assert {k:v for k,v in before.items() if k!='operation_id'}=={k:v for k,v in after.items() if k!='operation_id'}
    asyncio.run(run())


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_OPTICS_EVIDENCE'),reason='Retained paired canopy lighting controls required')
def test_relative_gate_rejects_real_lighting_controls(assets_live):
    import json,shutil
    from pathlib import Path
    source=Path(os.environ['MCPBLENDER_OPTICS_EVIDENCE']);root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    modes=('baseline','primary_only','sun_front','sun_back')
    for mode in modes:
        for kind in ('native','far'):shutil.copy2(source/(kind+'-'+mode+'.png'),library/(kind+'-'+mode+'.png'))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            before=(await client.call_tool('get_scene_info',{})).data;reports={}
            for mode in modes:
                result=await wait(client,'compare_png_images',reference='native-'+mode+'.png',candidate='far-'+mode+'.png',quality={'max_overlap_rgb_rmse':.05,'max_abs_overlap_luminance_relative_bias':.1})
                assert not result['passed'] and 'recovery' not in result
                for row in result['levels']:
                    assert row['mask_iou']>.9 and row['overlap_rgb_rmse']<.05
                    assert row['abs_overlap_luminance_relative_bias']>.1
                    assert row['failures']==['max_abs_overlap_luminance_relative_bias']
                reports[mode]=result
            assert reports['primary_only']['levels'][0]['overlap_luminance_relative_bias']<0
            assert reports['sun_back']['levels'][0]['overlap_luminance_relative_bias']>0
            after=(await client.call_tool('get_scene_info',{})).data
            assert {k:v for k,v in before.items() if k!='operation_id'}=={k:v for k,v in after.items() if k!='operation_id'}
            return reports
    result=asyncio.run(run());(source/'relative-mcp-proof.json').write_text(json.dumps(result,indent=2))
