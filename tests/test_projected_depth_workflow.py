"""Measured occupancy reaches packed depth alpha through Python-disabled MCP."""
import asyncio,json,os,shutil,subprocess
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait


def test_projected_depth_alpha_preserves_inputs_geometry_and_persistence(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='WeightedTree',recipe=recipe,expected_model=plan['model_sha256'],location=[4,3,1])
            foliage={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection='WeightedTree',foliage=foliage)
            await wait(client,'configure_botanical_foliage',collection='WeightedTree',foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection='WeightedTree')
            args={'collection':'WeightedTree','views':['FRONT','BACK'],'resolution':32,'samples':1,'material_fields':True,'component_ids':True}
            plan=await wait(client,'inspect_botanical_view_capture',**args)
            await wait(client,'capture_botanical_views',**args,directory='reference',expected_capture=plan['capture_sha256'])
            coverage={'reference_directory':'reference','view':'FRONT','samples':64}
            plan=await wait(client,'inspect_botanical_projected_coverage',**coverage)
            await wait(client,'capture_botanical_projected_coverage',**coverage,directory='coverage',expected_plan=plan['plan_sha256'])
            base={'directory':'reference','view':'FRONT','component_filter':'LEAVES','settings':{'tile_pixels':1}}
            weighted=base|{'projected_coverage_directory':'coverage'}
            raw=await wait(client,'inspect_botanical_depth_source',**base)
            plan=await wait(client,'inspect_botanical_depth_source',**weighted)
            assert plan['geometry']==raw['geometry'] and plan['maps'][1:]==raw['maps'][1:]
            assert plan['maps'][0]!=raw['maps'][0] and plan['projected_coverage']['excluded_outside_target_mass_pixels']>=0
            with pytest.raises(ToolError,match='binding'):
                await wait(client,'inspect_botanical_depth_source',**(weighted|{'view':'BACK'}))
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'create_botanical_depth_asset',**weighted,collection='StaleWeighted',expected_plan=raw['plan_sha256'],accept_approximate_optics=True)
            # Damaged occupancy inputs refuse before any owned resources exist.
            output=root/'library/coverage/outputs/c00_f0000.exr';original=output.read_bytes();output.write_bytes(original[:-1]+bytes([original[-1]^1]))
            try:
                with pytest.raises(ToolError,match='hash'):
                    await wait(client,'inspect_botanical_depth_source',**weighted)
            finally:output.write_bytes(original)
            assets=[]
            for name,options,planned in [('RawDepth',base,raw),('WeightedDepth',weighted,plan)]:
                assets.append(await wait(client,'create_botanical_depth_asset',**options,collection=name,expected_plan=planned['plan_sha256'],accept_approximate_optics=True))
            batch={'directory':'reference','prefix':'WeightedBatch','layers':[{'view':'FRONT','component_filter':'LEAVES','projected_coverage_directory':'coverage','settings':{'tile_pixels':1}}]}
            with pytest.raises(ToolError,match='pixel budget'):
                await wait(client,'inspect_botanical_depth_layers',**batch,limits={'max_total_pixels':1024})
            stacked=await wait(client,'inspect_botanical_depth_layers',**batch)
            assert stacked['totals']['pixels']==2048 and stacked['layers'][0]['projected_coverage']==plan['projected_coverage']
            made=await wait(client,'create_botanical_depth_layers',**batch,expected_plan=stacked['plan_sha256'],accept_approximate_optics=True)
            assets+=made['assets']
            assert (await wait(client,'inspect_botanical_tree',collection='WeightedTree'))['tree_sha256']==before['tree_sha256']
            await client.call_tool('save_blend',{'path':'weighted.blend'})
            helper=Path(__file__).with_name('native_projected_depth.py')
            probe=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(helper),'--',str(helper.resolve().parents[1]),str(root/'library/weighted.blend'),str(root/'library/coverage')],capture_output=True,text=True,timeout=45)
            assert probe.returncode==0,probe.stdout+probe.stderr
            if destination:=os.environ.get('MCPBLENDER_PROJECTED_DEPTH_EVIDENCE'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'library/weighted.blend',out/'weighted.blend');(out/'native-readback.log').write_text(probe.stdout+probe.stderr);(out/'plans.json').write_text(json.dumps({'raw':raw,'weighted':plan,'batch':stacked},indent=2))
            shutil.rmtree(root/'library/reference');shutil.rmtree(root/'library/coverage')
            await client.call_tool('open_blend',{'path':'weighted.blend'})
            before=await wait(client,'inspect_botanical_tree',collection='WeightedTree')
            for asset in assets:
                state=await wait(client,'inspect_botanical_depth_asset',collection=asset['collection'])
                assert state['valid'] and not state['source_files_required']
                removed=await wait(client,'remove_botanical_depth_asset',collection=asset['collection'],expected_asset=state['asset_sha256'])
                assert removed['private_datablocks']==11
            assert (await wait(client,'inspect_botanical_tree',collection='WeightedTree'))['tree_sha256']==before['tree_sha256']
    asyncio.run(run())
