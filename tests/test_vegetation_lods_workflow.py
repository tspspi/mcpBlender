"""MCP-only quality refusal, shared native LODs and fixed-camera rendering."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_structured_quality_gates_and_rendered_levels(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            p=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='SourceOak',recipe=recipe,expected_model=p['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':5};pop=await wait(client,'plan_botanical_foliage',collection='SourceOak',foliage=cfg)
            tree=await wait(client,'configure_botanical_foliage',collection='SourceOak',foliage=cfg,expected_tree=tree['tree_sha256'],expected_foliage=pop['foliage_sha256'])
            args={'collection':'SourceOak','levels':[{'leaf_budget':70,'radial_sides':6},{'leaf_budget':35,'radial_sides':5,'min_branch_radius_m':.04}]}
            failed=await wait(client,'inspect_botanical_lod_source',**args);assert not failed['valid']
            with pytest.raises(ToolError,match='quality budgets'):await wait(client,'create_botanical_lods',**args,lod_collection='RefusedLods',expected_plan=failed['plan_sha256'])
            args['levels'][1].update(max_coverage_loss=.55,max_silhouette_loss=.55)
            planned=await wait(client,'inspect_botanical_lod_source',**args);assert planned['valid']
            created=await wait(client,'create_botanical_lods',**args,lod_collection='OakLods',expected_plan=planned['plan_sha256'],display_offset_m=[8,0,0])
            assert created['valid'] and [v['leaves'] for v in created['levels']]==[140,70,35]
            assert (await tool(client,'inspect_botanical_tree',collection='SourceOak'))['tree_sha256']==tree['tree_sha256']
            hidden=['Cube',*[v['object'] for v in tree['members']],*[tree['foliage']['roles'][k]['name'] for k in ('po','so')]]
            saved_visibility={}
            for name in hidden:
                visibility=await tool(client,'inspect_render_visibility',name=name)
                saved_visibility[name]=visibility['visibility']['hide_render']
                await tool(client,'configure_render_visibility',name=name,expected_visibility=visibility['visibility_sha256'],hide_render=True)
            await tool(client,'setup_preview_stage',objects=created['levels'][0]['objects'],prefix='LodView')
            await tool(client,'configure_render',resolution_x=320,resolution_y=256,samples=8)
            current=created
            for number in range(3):
                current=await tool(client,'activate_botanical_lod',lod_collection='OakLods',expected_lods=current['lods_sha256'],level=number)
                operation=(await client.call_tool('submit_operation',{'command':'render_still','params':{'path':f'lod-{number}.png','camera':'LodView_Camera','engine':'CYCLES','width':320,'height':256}})).data
                done=(await client.call_tool('wait_operation',{'operation_id':operation['operation_id'],'timeout_seconds':90})).data
                assert done['state']=='succeeded',done
            assert len({(root/'library'/f'lod-{n}.png').read_bytes() for n in range(3)})==3
            for name,hide_render in saved_visibility.items():
                visibility=await tool(client,'inspect_render_visibility',name=name)
                await tool(client,'configure_render_visibility',name=name,expected_visibility=visibility['visibility_sha256'],hide_render=hide_render)
            assert (await tool(client,'inspect_botanical_tree',collection='SourceOak'))['tree_sha256']==tree['tree_sha256']
            await client.call_tool('save_blend',{'path':'botanical-lods.blend'})
            await client.call_tool('open_blend',{'path':'botanical-lods.blend'})
            restored=await tool(client,'inspect_botanical_lods',lod_collection='OakLods');assert restored['valid'] and restored['active_level']==2
            if directory:=os.environ.get('MCPBLENDER_VEGETATION_LOD_EVIDENCE_DIR'):
                target=Path(directory);target.mkdir(parents=True,exist_ok=True)
                for name in ['botanical-lods.blend',*[f'lod-{i}.png' for i in range(3)]]:shutil.copy2(root/'library'/name,target/name)
                (target/'proof.json').write_text(json.dumps({'failed':failed,'plan':planned,'created':created,'restored':restored},indent=2))
            await tool(client,'remove_botanical_lods',lod_collection='OakLods',expected_lods=restored['lods_sha256'])
            assert (await tool(client,'inspect_botanical_tree',collection='SourceOak'))['valid']
    asyncio.run(run())
