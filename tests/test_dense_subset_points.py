"""Opt-in public MCP regression for the large observed-leaf selection."""
import asyncio,json,os,shutil,subprocess
from pathlib import Path
import pytest
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait

source=os.environ.get('MCPBLENDER_COMPACT_SUBSET_SOURCE')
capture=os.environ.get('MCPBLENDER_COMPACT_SUBSET_CAPTURE')
pytestmark=pytestmark+[pytest.mark.skipif(not source or not capture,reason='Requires retained dense project and matching public capture')]


def test_full_density_compact_subsets_keep_every_selected_native_instance(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    shutil.copy2(source,library/'source.blend');shutil.copytree(capture,library/'capture')
    evidence=Path(os.environ['MCPBLENDER_COMPACT_SUBSET_EVIDENCE']) if os.environ.get('MCPBLENDER_COMPACT_SUBSET_EVIDENCE') else None
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            await client.call_tool('open_blend',{'path':'source.blend'})
            before=await wait(client,'inspect_botanical_tree',collection='Canopy3');states=[]
            for mode,name in [('OBSERVED','CompactObserved'),('UNOBSERVED','CompactUnobserved')]:
                opts={'directory':'capture','views':['FRONT'],'selection':mode,'include_structure':False,'render_role':'SECONDARY'}
                plan=await wait(client,'inspect_botanical_subset_source',**opts)
                assert plan['point_storage']=='COMPACT_SOURCE_IDS_V1'
                state=await wait(client,'create_botanical_subset',**opts,subset_collection=name,expected_plan=plan['plan_sha256'])
                assert state['valid'] and state['source_unchanged'];states.append(state)
            assert [s['selected_leaf_count'] for s in states]==[35514,53190]
            assert (await wait(client,'inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==before['tree_sha256']
            await client.call_tool('save_blend',{'path':'compact-subsets.blend'})
            await client.call_tool('open_blend',{'path':'compact-subsets.blend'})
            if evidence:
                evidence.mkdir(parents=True,exist_ok=True);shutil.copy2(library/'compact-subsets.blend',evidence/'compact-subsets.blend')
            helper=Path(__file__).with_name('native_dense_subset_points.py')
            probe=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(helper),'--',str(Path(__file__).resolve().parents[1]),str(library/'compact-subsets.blend')],capture_output=True,text=True,timeout=60)
            if evidence:(evidence/'native-readback.log').write_text(probe.stdout+probe.stderr)
            assert probe.returncode==0,probe.stdout+probe.stderr
            shutil.rmtree(library/'capture');removed=[]
            current=await wait(client,'inspect_botanical_tree',collection='Canopy3')
            for state in states:
                read=await wait(client,'inspect_botanical_subset',subset_collection=state['subset_collection']);assert read['valid'] and read['source_unchanged']
                removed.append(await wait(client,'remove_botanical_subset',subset_collection=read['subset_collection'],expected_subset=read['subset_sha256']))
            assert (await wait(client,'inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==current['tree_sha256']
            return {'states':states,'removed':removed}
    result=asyncio.run(run())
    if evidence:(evidence/'proof.json').write_text(json.dumps(result,indent=2))
