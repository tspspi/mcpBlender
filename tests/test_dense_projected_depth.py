"""Opt-in dense occupancy-to-PBR alpha consumer with independent buffer checks."""
import asyncio,json,os,shutil,subprocess
from pathlib import Path
import pytest
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait

source=os.environ.get('MCPBLENDER_PROJECTED_DEPTH_SOURCE')
reference=os.environ.get('MCPBLENDER_PROJECTED_DEPTH_REFERENCE')
coverage=os.environ.get('MCPBLENDER_PROJECTED_DEPTH_COVERAGE')
pytestmark=pytestmark+[pytest.mark.skipif(not source or not reference or not coverage,reason='Requires retained dense project, reference and measured coverage')]


def test_dense_measured_coverage_changes_only_packed_alpha(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(source,library/'source.blend');shutil.copytree(reference,library/'reference');shutil.copytree(coverage,library/'coverage')
    async def run():
        async with client_for(path) as client:
            await client.call_tool('open_blend',{'path':'source.blend'})
            before=await wait(client,'inspect_botanical_tree',collection='Canopy3')
            base={'directory':'reference','view':'FRONT','component_filter':'LEAVES','settings':{'geometry_mode':'ADAPTIVE_NORMAL','plane_normal_source':'GEOMETRIC_AOV','tile_pixels':1,'max_slope':64.,'max_triangles':131072}}
            options=[base,base|{'projected_coverage_directory':'coverage'}];plans=[];assets=[]
            for name,args in zip(['RawDepth','WeightedDepth'],options):
                plan=await wait(client,'inspect_botanical_depth_source',**args);plans.append(plan)
                assets.append(await wait(client,'create_botanical_depth_asset',**args,collection=name,expected_plan=plan['plan_sha256'],accept_approximate_optics=True))
            assert plans[0]['geometry']==plans[1]['geometry'] and plans[0]['maps'][1:]==plans[1]['maps'][1:]
            measured=plans[1]['projected_coverage']
            assert measured['target_pixels']==54882 and measured['zero_target_pixels']>=1
            assert plans[1]['geometry']['triangles']==109764
            assert (await wait(client,'inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==before['tree_sha256']
            await client.call_tool('save_blend',{'path':'weighted.blend'})
            helper=Path(__file__).with_name('native_projected_depth.py')
            probe=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(helper),'--',str(helper.resolve().parents[1]),str(library/'weighted.blend'),str(library/'coverage')],capture_output=True,text=True,timeout=90)
            if destination:=os.environ.get('MCPBLENDER_PROJECTED_DEPTH_EVIDENCE'):
                out=Path(destination);out.mkdir(parents=True,exist_ok=True);(out/'native-readback.log').write_text(probe.stdout+probe.stderr)
            assert probe.returncode==0,probe.stdout+probe.stderr
            if destination:
                shutil.copy2(library/'weighted.blend',out/'weighted.blend');(out/'plans.json').write_text(json.dumps(plans,indent=2))
            shutil.rmtree(library/'reference');shutil.rmtree(library/'coverage')
            await client.call_tool('open_blend',{'path':'weighted.blend'})
            before=await wait(client,'inspect_botanical_tree',collection='Canopy3')
            for asset in assets:
                state=await wait(client,'inspect_botanical_depth_asset',collection=asset['collection']);assert state['valid'] and not state['source_files_required']
                await wait(client,'remove_botanical_depth_asset',collection=asset['collection'],expected_asset=state['asset_sha256'])
            assert (await wait(client,'inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==before['tree_sha256']
    asyncio.run(run())
