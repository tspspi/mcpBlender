"""Code-disabled native diagnostics over relocated, real retained foliage bakes."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_trees import wait


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_CARD_VIEWS_EVIDENCE'),reason='Retained three-view bake bundles required')
def test_retained_projected_normal_diagnostics(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    source=Path(os.environ['MCPBLENDER_CARD_VIEWS_EVIDENCE'])
    for view in ('top','front','side'):shutil.copytree(source/view,library/view)
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            reports={}
            for view in ('top','front','side'):
                await client.call_tool('open_blend',{'path':view+'/asset.blend'})
                before=(await client.call_tool('get_scene_info')).data;before.pop('operation_id',None)
                report=await wait(client,'inspect_projected_normal_transfer',directory=view)
                assert 'recovery' not in report and 'passed' not in report
                assert {k:v for k,v in (await client.call_tool('get_scene_info')).data.items() if k!='operation_id'}==before
                assert report['coverage_kind']=='ALPHA_RED'
                assert report['target_geometry']['planar'] and not report['target_geometry']['smooth_faces']
                assert report['covered_pixels']>1000 and report['invalid_direction_pixels']==0
                assert report['backward_fraction']<.001 if view=='top' else .4<report['backward_fraction']<.5
                reports[view]=report
            # Reject the wrong opened target even though every file is intact.
            with pytest.raises(ToolError):await wait(client,'inspect_projected_normal_transfer',directory='top')
            image=library/'side/textures/normal.png';original=image.read_bytes();image.write_bytes(original+b'changed')
            with pytest.raises(ToolError,match='changed'):await wait(client,'inspect_projected_normal_transfer',directory='side')
            image.write_bytes(original)
            if dest:=os.environ.get('MCPBLENDER_NORMAL_TRANSFER_EVIDENCE'):
                out=Path(dest);out.mkdir(parents=True,exist_ok=True);(out/'mcp-diagnostics.json').write_text(json.dumps(reports,indent=2))
    asyncio.run(run())


def test_projected_normal_without_alpha_uses_hit_mask(assets_live):
    from test_texture_baking import source_scene,inspect as inspect_bake
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            await source_scene(client)
            info=await inspect_bake(client)
            await wait(client,'bake_textures',name='BakeLow',sources=['BakeHigh'],expected_bake=info['bake_sha256'],directory='normal-only',width=32,height=32,samples=1,margin=0,cage_extrusion=.8,max_ray_distance=2,maps=['NORMAL'])
            await client.call_tool('open_blend',{'path':'normal-only/asset.blend'})
            before=(await client.call_tool('get_scene_info')).data;before.pop('operation_id',None)
            report=await wait(client,'inspect_projected_normal_transfer',directory='normal-only')
            assert report['coverage_kind']=='PROJECTION_HIT_RED'
            assert report['covered_pixels']==1024 and report['valid_direction_pixels']==1024
            assert report['backward_fraction']==0 and report['target_geometry']['planar']
            assert {k:v for k,v in (await client.call_tool('get_scene_info')).data.items() if k!='operation_id'}==before
            # A successful self-bake is outside projected-transfer semantics.
            await wait(client,'apply_material_preset',material='SelfSource',base_color=[.2,.4,.1,1])
            await wait(client,'assign_material',objects=['BakeLow'],material='SelfSource')
            info=await wait(client,'inspect_texture_bake',name='BakeLow')
            assert info['complete'],info
            await wait(client,'bake_textures',name='BakeLow',expected_bake=info['bake_sha256'],directory='self-normal',width=32,height=32,samples=1,margin=0,maps=['NORMAL'])
            await client.call_tool('open_blend',{'path':'self-normal/asset.blend'})
            with pytest.raises(ToolError,match='projected bake'):await wait(client,'inspect_projected_normal_transfer',directory='self-normal')
    asyncio.run(run())
