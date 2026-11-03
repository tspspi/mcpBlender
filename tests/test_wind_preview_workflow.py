"""Structured sampled native wind rendering, reopening and owned cleanup."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_structured_wind_preview_render_and_reopen(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            source=await wait(client,'create_botanical_tree',collection='WindSource',recipe=recipe,expected_model=plan['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':5}
            population=await wait(client,'plan_botanical_foliage',collection='WindSource',foliage=cfg)
            source=await wait(client,'configure_botanical_foliage',collection='WindSource',foliage=cfg,expected_tree=source['tree_sha256'],expected_foliage=population['foliage_sha256'])
            args={'collection':'WindSource','wind':{'steady_mps':[3,1,0],'gust_mps':4,'bend_degrees_per_mps':2},'frame_end':13,'display_offset_m':[8,0,0]}
            planned=await tool(client,'inspect_botanical_wind_preview_source',**args);assert 'recovery' not in planned
            with pytest.raises(ToolError,match='budget'):await tool(client,'inspect_botanical_wind_preview_source',**args,max_coordinate_bytes=1024)
            with pytest.raises(ToolError,match='eight samples'):await tool(client,'inspect_botanical_wind_preview_source',**args,frame_step=4)
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_wind_preview',**args,preview_collection='StalePreview',expected_plan='0'*64)
            created=await wait(client,'create_botanical_wind_preview',**args,preview_collection='WindPreview',expected_plan=planned['plan_sha256'])
            assert created['valid'] and created['leaf_instances']==population['metrics']['leaves']
            assert (await tool(client,'inspect_botanical_tree',collection='WindSource'))['tree_sha256']==source['tree_sha256']
            cube=await tool(client,'inspect_render_visibility',name='Cube')
            await tool(client,'configure_render_visibility',name='Cube',expected_visibility=cube['visibility_sha256'],hide_render=True)
            await tool(client,'setup_preview_stage',objects=created['objects'],prefix='WindStage')
            await tool(client,'configure_render',resolution_x=320,resolution_y=256,samples=8)
            paths=[]
            for frame in (1,7,13):
                await client.call_tool('set_frame',{'frame':frame})
                checked=await tool(client,'inspect_botanical_wind_preview',preview_collection='WindPreview');assert checked['valid']
                name=f'wind-{frame:02}.png';paths.append(name)
                queued=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':name,'camera':'WindStage_Camera','engine':'CYCLES','width':320,'height':256}})).data
                done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data
                assert done['state']=='succeeded',done
            assert len({(root/'library'/p).read_bytes() for p in paths})==3
            await client.call_tool('save_blend',{'path':'wind-preview.blend'})
            await client.call_tool('open_blend',{'path':'wind-preview.blend'})
            restored=await tool(client,'inspect_botanical_wind_preview',preview_collection='WindPreview');assert restored['valid']
            if directory:=os.environ.get('MCPBLENDER_WIND_PREVIEW_EVIDENCE_DIR'):
                out=Path(directory);out.mkdir(parents=True,exist_ok=True)
                for name in [*paths,'wind-preview.blend']:shutil.copy2(root/'library'/name,out/name)
                (out/'proof.json').write_text(json.dumps({'plan':planned,'created':created,'restored':restored},indent=2))
            removed=await tool(client,'remove_botanical_wind_preview',preview_collection='WindPreview',expected_preview=restored['preview_sha256'])
            assert removed['materials_preserved'] and (await tool(client,'inspect_botanical_tree',collection='WindSource'))['valid']
    asyncio.run(run())
