"""Opt-in dense native complement creation, shader readback and saved ownership."""
import asyncio,json,os,shutil,subprocess
from pathlib import Path
import pytest
from test_asset_editing import assets_live,client_for,pytestmark
from test_depth_candidates import wait

source=os.environ.get('MCPBLENDER_COLUMN_SOURCE');reference=os.environ.get('MCPBLENDER_COLUMN_REFERENCE')
pytestmark=pytestmark+[pytest.mark.skipif(not source or not reference,reason='Requires dense source and matching public component capture')]


def test_dense_column_shader_follows_owned_root_and_retains_all_instances(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True);shutil.copy2(source,library/'source.blend');shutil.copytree(reference,library/'reference')
    async def run():
        async with client_for(path) as client:
            await client.call_tool('open_blend',{'path':'source.blend'})
            before=await wait(client,'inspect_botanical_tree',collection='Canopy3')
            args={'directory':'reference','selection':'COLUMN_COMPLEMENT','views':['FRONT']}
            plan=await wait(client,'inspect_botanical_subset_source',**args)
            assert plan['selected_leaf_count']==88704 and plan['column_complement']['target_pixels']==54882
            made=await wait(client,'create_botanical_subset',**args,subset_collection='ColumnComplement',expected_plan=plan['plan_sha256']);assert made['valid'] and made['source_unchanged']
            assert (await wait(client,'inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==before['tree_sha256']
            await client.call_tool('save_blend',{'path':'column.blend'})
            helper=Path(__file__).with_name('native_column_complement.py');destination=os.environ.get('MCPBLENDER_COLUMN_EVIDENCE');out=Path(destination) if destination else None
            probe=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(helper),'--',str(helper.resolve().parents[1]),str(library/'column.blend'),str(library/'reference'),str(root/'native-check')],capture_output=True,text=True,timeout=180)
            if out:out.mkdir(parents=True,exist_ok=True);(out/'native.log').write_text(probe.stdout+probe.stderr)
            assert probe.returncode==0,probe.stdout+probe.stderr
            if out:
                shutil.copy2(library/'column.blend',out/'column.blend');assert (library/'column.blend').read_bytes()==(out/'column.blend').read_bytes();shutil.copytree(root/'native-check',out/'native-check',dirs_exist_ok=True);(out/'plan.json').write_text(json.dumps(plan,indent=2))
            shutil.rmtree(library/'reference');await client.call_tool('open_blend',{'path':'column.blend'})
            state=await wait(client,'inspect_botanical_subset',subset_collection='ColumnComplement');assert state['valid'] and state['source_unchanged'] and not state['capture_files_required']
            before=await wait(client,'inspect_botanical_tree',collection='Canopy3')
            removed=await wait(client,'remove_botanical_subset',subset_collection='ColumnComplement',expected_subset=state['subset_sha256'])
            assert (await wait(client,'inspect_botanical_tree',collection='Canopy3'))['tree_sha256']==before['tree_sha256']
            if out:(out/'proof.json').write_text(json.dumps({'created':made,'removed':removed},indent=2))
    asyncio.run(run())
