"""Native capture-derived complementary subsets through Python-disabled MCP."""
import asyncio,json,os,shutil,subprocess
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,pytestmark
from test_botanical_capture_workflow import drain_captures
from test_depth_candidates import wait


def test_native_subset_capture_selection_persistence_and_source_preservation(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='SubsetTree',recipe=recipe,expected_model=plan['model_sha256'],location=[4,3,1])
            cfg={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection='SubsetTree',foliage=cfg)
            await wait(client,'configure_botanical_foliage',collection='SubsetTree',foliage=cfg,expected_tree=tree['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection='SubsetTree')
            args={'collection':'SubsetTree','views':['FRONT','BACK'],'resolution':32,'samples':1,'material_fields':True,'component_ids':True}
            capture=await wait(client,'inspect_botanical_view_capture',**args)
            await wait(client,'capture_botanical_views',**args,directory='subset-input',expected_capture=capture['capture_sha256'])
            source={'directory':'subset-input','views':['FRONT'],'include_structure':False}
            states=[];plans=[]
            for mode,name in [('OBSERVED','ObservedLeaves'),('UNOBSERVED','OtherLeaves')]:
                opts=source|{'selection':mode}
                plan=await wait(client,'inspect_botanical_subset_source',**opts)
                assert plan['observed_leaf_count']>0 and plan['selected_leaf_count']>0
                with pytest.raises(ToolError,match='stale'):
                    await wait(client,'create_botanical_subset',**opts,subset_collection=name,expected_plan='0'*64)
                state=await wait(client,'create_botanical_subset',**opts,subset_collection=name,expected_plan=plan['plan_sha256'])
                assert state['valid'] and state['source_unchanged'];states.append(state);plans.append(plan)
            assert sum(v['selected_leaf_count'] for v in plans)==before['foliage']['metrics']['leaves']
            with pytest.raises(ToolError,match='budget'):
                await wait(client,'inspect_botanical_subset_source',**(source|{'views':['FRONT','BACK'],'max_total_pixels':1024}))
            union=await wait(client,'inspect_botanical_subset_source',**(source|{'views':['FRONT','BACK'],'selection':'OBSERVED'}))
            assert union['observed_leaf_count']>=plans[0]['observed_leaf_count']
            structure_opts=source|{'include_structure':True,'selection':'UNOBSERVED','render_role':'SECONDARY'}
            structure=await wait(client,'inspect_botanical_subset_source',**structure_opts)
            copied=await wait(client,'create_botanical_subset',**structure_opts,subset_collection='StructureAndOtherLeaves',expected_plan=structure['plan_sha256'])
            states.append(copied)
            assert (await wait(client,'inspect_botanical_tree',collection='SubsetTree'))['tree_sha256']==before['tree_sha256']
            target=states[0]
            await wait(client,'configure_modifier',name=target['population'],modifier='UnownedEdit',settings={'type':'BEVEL','width':.02,'segments':1})
            edited=await wait(client,'inspect_botanical_subset',subset_collection=target['subset_collection'])
            assert not edited['valid']
            with pytest.raises(ToolError,match='edited'):
                await wait(client,'remove_botanical_subset',subset_collection=target['subset_collection'],expected_subset=edited['subset_sha256'])
            await wait(client,'remove_modifier',name=target['population'],modifier='UnownedEdit')
            assert (await wait(client,'inspect_botanical_subset',subset_collection=target['subset_collection']))['valid']
            await client.call_tool('save_blend',{'path':'native-subsets.blend'})
            await client.call_tool('open_blend',{'path':'native-subsets.blend'})
            reopened_plan=await wait(client,'inspect_botanical_subset_source',**(source|{'selection':'OBSERVED'}))
            assert reopened_plan['source_content_sha256']==plans[0]['source_content_sha256']
            assert reopened_plan['selected_indices_sha256']==plans[0]['selected_indices_sha256']
            if dest:=os.environ.get('MCPBLENDER_SUBSET_EVIDENCE'):
                out=Path(dest);out.mkdir(parents=True,exist_ok=True);shutil.copytree(root/'library/subset-input',out/'capture',dirs_exist_ok=True);shutil.copy2(root/'library/native-subsets.blend',out/'native-subsets.blend')
            probe=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1',
                '--python',str(Path(__file__).with_name('native_botanical_subset.py')),'--',str(Path(__file__).resolve().parents[1]),str(root/'library/native-subsets.blend'),str(root/'library/subset-input')],capture_output=True,text=True,timeout=45)
            if dest:(Path(dest)/'refusal-probe.log').write_text(probe.stdout+probe.stderr)
            assert probe.returncode==0,probe.stdout+probe.stderr
            shutil.rmtree(root/'library/subset-input')
            removed=[]
            for old in states:
                state=await wait(client,'inspect_botanical_subset',subset_collection=old['subset_collection'])
                assert state['valid'] and state['subset_sha256']==old['subset_sha256'] and not state['capture_files_required']
                with pytest.raises(ToolError,match='stale'):
                    await wait(client,'remove_botanical_subset',subset_collection=state['subset_collection'],expected_subset='0'*64)
                removed.append(await wait(client,'remove_botanical_subset',subset_collection=state['subset_collection'],expected_subset=state['subset_sha256']))
            after=await wait(client,'inspect_botanical_tree',collection='SubsetTree')
            portable=lambda value:{k:v for k,v in value.items() if k not in {'tree_sha256','recovery','operation_id'}}
            assert portable(after)==portable(before)
            return {'plans':plans,'union':union,'structure':structure,'states':states,'removed':removed}
    proof=asyncio.run(run())
    if dest:=os.environ.get('MCPBLENDER_SUBSET_EVIDENCE'):(Path(dest)/'proof.json').write_text(json.dumps(proof,indent=2))
