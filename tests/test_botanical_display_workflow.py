"""Source/depth/native switching through MCP without arbitrary Python."""
import asyncio,json,os,shutil,subprocess
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait


def test_guarded_display_batch_source_preservation_and_saved_switch(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            planned=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='DisplayTree',recipe=recipe,expected_model=planned['model_sha256'],location=[4,3,1])
            foliage={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection='DisplayTree',foliage=foliage)
            await wait(client,'configure_botanical_foliage',collection='DisplayTree',foliage=foliage,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            source=await wait(client,'inspect_botanical_tree',collection='DisplayTree')
            args={'collection':'DisplayTree','views':['FRONT'],'resolution':32,'samples':1,'material_fields':True,'component_ids':True}
            capture=await wait(client,'inspect_botanical_view_capture',**args)
            await wait(client,'capture_botanical_views',**args,directory='reference',expected_capture=capture['capture_sha256'])
            depth={'directory':'reference','view':'FRONT','component_filter':'LEAVES','settings':{'tile_pixels':1}}
            planned=await wait(client,'inspect_botanical_depth_source',**depth)
            made=await wait(client,'create_botanical_depth_asset',**depth,collection='DisplayDepth',expected_plan=planned['plan_sha256'],accept_approximate_optics=True)
            subset={'directory':'reference','selection':'COLUMN_COMPLEMENT','views':['FRONT']}
            planned=await wait(client,'inspect_botanical_subset_source',**subset)
            await wait(client,'create_botanical_subset',**subset,subset_collection='DisplaySubset',expected_plan=planned['plan_sha256'])
            refs=[{'kind':'SOURCE','collection':'DisplayTree'},{'kind':'DEPTH','collection':'DisplayDepth'},{'kind':'SUBSET','collection':'DisplaySubset'}]
            display=await wait(client,'inspect_botanical_display',targets=refs)
            assert display['valid'] and [r['visibility']['hide_render'] for r in display['targets']]==[False,True,True]
            changes=[ref|{'hide_render':i==0,'hide_viewport':i==0} for i,ref in enumerate(refs)]
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'configure_botanical_display',targets=changes,expected_display='0'*64)
            # Invalid later target must refuse before changing the first source.
            visibility=await wait(client,'inspect_render_visibility',name=made['object'])
            bad=await wait(client,'configure_render_visibility',name=made['object'],expected_visibility=visibility['visibility_sha256'],visible_camera=False)
            invalid=await wait(client,'inspect_botanical_display',targets=refs);assert not invalid['valid']
            with pytest.raises(ToolError,match='invalid'):
                await wait(client,'configure_botanical_display',targets=changes,expected_display=invalid['display_sha256'])
            assert (await wait(client,'inspect_botanical_display',targets=refs))['targets'][0]['visibility']==display['targets'][0]['visibility']
            await wait(client,'configure_render_visibility',name=made['object'],expected_visibility=bad['visibility_sha256'],visible_camera=True)
            display=await wait(client,'inspect_botanical_display',targets=refs)
            await client.call_tool('save_blend',{'path':'before.blend'})
            switched=await wait(client,'configure_botanical_display',targets=changes,expected_display=display['display_sha256'])
            assert switched['valid'] and [r['visibility']['hide_render'] for r in switched['targets']]==[True,False,False]
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'configure_botanical_display',targets=changes,expected_display=display['display_sha256'])
            assert (await wait(client,'inspect_botanical_tree',collection='DisplayTree'))['model_sha256']==source['model_sha256']
            await client.call_tool('save_blend',{'path':'switched.blend'})
            helper=Path(__file__).with_name('native_botanical_display.py')
            native=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(helper),'--',str(helper.resolve().parents[1]),str(root/'library/before.blend'),str(root/'library/switched.blend')],capture_output=True,text=True,timeout=90)
            if destination:=os.environ.get('MCPBLENDER_DISPLAY_EVIDENCE'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True);(out/'native.log').write_text(native.stdout+native.stderr)
            assert native.returncode==0,native.stdout+native.stderr
            if destination:
                for name in ['before.blend','switched.blend']:
                    shutil.copy2(root/'library'/name,out/name);assert (out/name).read_bytes()==(root/'library'/name).read_bytes()
                (out/'proof.json').write_text(json.dumps({'before':display,'switched':switched},indent=2))
            shutil.rmtree(root/'library/reference')
            await client.call_tool('open_blend',{'path':'switched.blend'})
            current=await wait(client,'inspect_botanical_display',targets=refs);assert current['valid']
            restored=await wait(client,'configure_botanical_display',targets=[ref|display['targets'][i]['visibility'] for i,ref in enumerate(refs)],expected_display=current['display_sha256'])
            assert restored['valid'] and [r['visibility'] for r in restored['targets']]==[r['visibility'] for r in display['targets']]
            assert (await wait(client,'inspect_botanical_subset',subset_collection='DisplaySubset'))['source_unchanged']
    asyncio.run(run())
