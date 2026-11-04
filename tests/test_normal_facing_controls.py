"""Read actual shader-control PNGs through the foreground comparison MCP surface."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_trees import wait


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_NORMAL_CONTROLS'),reason='Retained normal-control PNGs required')
def test_foreground_metrics_on_normal_controls(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    controls=Path(os.environ['MCPBLENDER_NORMAL_CONTROLS']);native=Path(os.environ['MCPBLENDER_NORMAL_REFERENCE'])
    for view in ('front','side'):
        shutil.copy2(native/(view+'-native.png'),library/(view+'-native.png'))
        for mode in ('original','flat','flip','mirror_z'):shutil.copy2(controls/(view+'-'+mode+'.png'),library/(view+'-'+mode+'.png'))
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            reports={}
            for view in ('front','side'):
                reports[view]={}
                for mode in ('original','flat','flip','mirror_z'):
                    result=await wait(client,'compare_png_images',reference=view+'-native.png',candidate=view+'-'+mode+'.png',scales=[1],quality={'max_overlap_rgb_rmse':.03})
                    assert 'recovery' not in result
                    reports[view][mode]=result
                rows={k:v['levels'][0] for k,v in reports[view].items()}
                assert rows['original']['premultiplied_rgb_rmse']<.1 and not reports[view]['original']['passed']
                assert rows['flat']['overlap_rgb_rmse']<rows['flip']['overlap_rgb_rmse']<rows['original']['overlap_rgb_rmse']
                assert 'max_overlap_rgb_rmse' in reports[view]['original']['failures'][0]
            # This .03 criterion is a diagnostic example, not a native-optics
            # acceptance threshold: even the flat SIDE control still rejects it.
            assert reports['front']['flat']['passed'] and not reports['side']['flat']['passed']
            if directory:=os.environ.get('MCPBLENDER_NORMAL_METRICS_EVIDENCE'):
                out=Path(directory);out.mkdir(parents=True,exist_ok=True);(out/'mcp-metrics.json').write_text(json.dumps(reports,indent=2))
    asyncio.run(run())
