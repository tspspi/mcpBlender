"""Python-disabled HDR comparisons: synthetic encoding and actual canopy renders."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait
from test_exr_comparison import hdr_files


def test_hdr_comparison_readonly_mcp(assets_live,hdr_files):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    for name in ('premult','straight','bright','nan'):shutil.copy2(hdr_files/(name+'.exr'),library/(name+'.exr'))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            before=(await client.call_tool('get_scene_info',{})).data
            args={'reference':'premult.exr','candidate':'straight.exr','reference_pass':'Layer.Combined','candidate_pass':'Layer.Combined','candidate_alpha_mode':'STRAIGHT'}
            result=await wait(client,'compare_exr_images',**args)
            assert result['passed'] and all(r['overlap_rgb_rmse']==0 for r in result['levels']) and 'recovery' not in result
            wrong=await wait(client,'compare_exr_images',**(args|{'candidate_alpha_mode':'PREMULTIPLIED'}))
            assert not wrong['passed']
            bright=await wait(client,'compare_exr_images',**(args|{'candidate':'bright.exr','candidate_alpha_mode':'PREMULTIPLIED','quality':{'max_abs_overlap_luminance_relative_bias':.1}}))
            assert not bright['passed'] and bright['levels'][0]['overlap_luminance_relative_bias']==pytest.approx(1)
            disabled=await wait(client,'compare_exr_images',**(args|{'candidate':'bright.exr','candidate_alpha_mode':'PREMULTIPLIED','quality':{'max_premultiplied_rgb_rmse':5,'max_overlap_rgb_rmse':5,'max_abs_overlap_luminance_relative_bias':None}}))
            assert disabled['passed'] and disabled['policy']['max_abs_overlap_luminance_relative_bias'] is None
            for patch in ({'reference':'../escape.exr'},{'max_pixels':1},{'candidate':'nan.exr'}):
                with pytest.raises(ToolError):await wait(client,'compare_exr_images',**(args|patch))
            after=(await client.call_tool('get_scene_info',{})).data
            assert {k:v for k,v in before.items() if k!='operation_id'}=={k:v for k,v in after.items() if k!='operation_id'}
    asyncio.run(run())


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_DENSE_SHADOW_RENDERS'),reason='Retained actual dense-canopy native comparison required')
def test_structured_exr_gates_reject_actual_dense_canopy(assets_live):
    source=Path(os.environ['MCPBLENDER_DENSE_SHADOW_RENDERS']);native=json.loads((source/'proof.json').read_text())
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    for lighting in ('world','sun_front','sun_back'):
        for kind in ('source','primary','masked'):shutil.copy2(source/(lighting+'-'+kind+'.exr'),library/(lighting+'-'+kind+'.exr'))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            before=(await client.call_tool('get_scene_info',{})).data;reports={}
            for lighting in ('world','sun_front','sun_back'):
                for kind in ('primary','masked'):
                    result=await wait(client,'compare_exr_images',reference=lighting+'-source.exr',candidate=lighting+'-'+kind+'.exr',reference_pass='Occlusion.Combined',candidate_pass='Occlusion.Combined',quality={'max_overlap_rgb_rmse':.05,'max_abs_overlap_luminance_relative_bias':.1})
                    assert not result['passed'] and 'recovery' not in result
                    actual=result['levels'][0];expected=native['comparisons'][lighting+'-'+kind]
                    for metric in ('mask_iou','soft_alpha_iou','alpha_mae','overlap_rgb_rmse','overlap_luminance_relative_bias'):
                        assert actual[metric]==pytest.approx(expected[metric]),(lighting,kind,metric)
                    assert actual['abs_overlap_luminance_relative_bias']>.1
                    assert 'max_abs_overlap_luminance_relative_bias' in actual['failures']
                    reports[lighting+'-'+kind]=result
            identical=await wait(client,'compare_exr_images',reference='world-source.exr',candidate='world-source.exr',reference_pass='Occlusion.Combined',candidate_pass='Occlusion.Combined',quality={'max_overlap_rgb_rmse':.05,'max_abs_overlap_luminance_relative_bias':.1})
            assert identical['passed'] and all(r['premultiplied_rgb_rmse']==0 for r in identical['levels'])
            after=(await client.call_tool('get_scene_info',{})).data
            assert {k:v for k,v in before.items() if k!='operation_id'}=={k:v for k,v in after.items() if k!='operation_id'}
            return reports
    reports=asyncio.run(run())
    if destination:=os.environ.get('MCPBLENDER_EXR_COMPARISON_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True);(out/'dense-mcp-comparisons.json').write_text(json.dumps(reports,indent=2))
