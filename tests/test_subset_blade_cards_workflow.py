"""Python-disabled source-bound native thin/procedural blade-card subset lifecycle."""
import asyncio,json,shutil,subprocess
from pathlib import Path
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live as _assets_live,client_for,pytestmark
from test_depth_candidates import wait


@pytest.fixture
def assets_live():
    yield from _assets_live.__wrapped__()


@pytest.mark.parametrize('procedural',[False,True])
def test_native_blade_card_subset(assets_live,procedural):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {v.name for v in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            p=await wait(client,'plan_botanical_tree',recipe=recipe)
            tree=await wait(client,'create_botanical_tree',collection='Tree',recipe=recipe,expected_model=p['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':4,'variants':1,'leaf':{'rows':12}}
            pop=await wait(client,'plan_botanical_foliage',collection='Tree',foliage=cfg)
            await wait(client,'configure_botanical_foliage',collection='Tree',foliage=cfg,expected_tree=tree['tree_sha256'],expected_foliage=pop['foliage_sha256'])
            for mat in (await wait(client,'inspect_vegetation_materials',collection='Tree'))['contract']['materials']:
                if procedural and mat['model']=='MANAGED_THIN_FOLIAGE':
                    state=await wait(client,'inspect_botanical_surface',material=mat['name'])
                    await wait(client,'configure_botanical_surface',material=mat['name'],settings={'profile':'OAK_LEAF'},expected_material=state['material_sha256'])
            source=await wait(client,'inspect_botanical_tree',collection='Tree')
            prep_args={'collection':'Tree','blade_cards':{},'texture_width':64,'texture_height':128,'tile_padding_pixels':2}
            p=await wait(client,'inspect_vegetation_bake_source',**prep_args)
            prep=await wait(client,'prepare_vegetation_bake',**prep_args,bake_collection='BladePrep',expected_plan=p['plan_sha256'])
            row=prep['components']['leaf-0']
            await wait(client,'bake_textures',**(row['bake_parameters']|{'directory':'blade','samples':2,'margin':1}))
            capture={'collection':'Tree','views':['FRONT'],'resolution':32,'samples':1,'component_ids':True,'material_fields':True}
            p=await wait(client,'inspect_botanical_view_capture',**capture)
            await wait(client,'capture_botanical_views',**capture,expected_capture=p['capture_sha256'],directory='capture')
            cards={'bake_collection':'BladePrep','expected_preparation':prep['preparation_sha256'],'entries':[{'asset':'leaf-0','directory':'blade'}]}
            opts={'directory':'capture','selection':'COLUMN_COMPLEMENT','include_structure':False,'blade_cards':cards}
            p=await wait(client,'inspect_botanical_subset_source',**opts)
            assert p['blade_cards']['variants'][0]['triangles']==14
            assert p['blade_cards']['expanded_card_leaf_triangles']==p['selected_leaf_count']*14
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'inspect_botanical_subset_source',**(opts|{'blade_cards':cards|{'expected_preparation':'0'*64}}))
            with pytest.raises(ToolError,match='budget'):
                await wait(client,'inspect_botanical_subset_source',**(opts|{'blade_cards':cards|{'max_texture_bytes':1024}}))
            job=root/'library/blade/job.json';original_job=job.read_bytes();changed=json.loads(original_job);changed['min_projection_coverage']=0;job.write_text(json.dumps(changed))
            try:
                with pytest.raises(ToolError,match='coverage policy'):
                    await wait(client,'inspect_botanical_subset_source',**opts)
            finally:job.write_bytes(original_job)
            image=root/'library/blade/textures/alpha.png';original=image.read_bytes();image.write_bytes(original+b'tampered')
            try:
                with pytest.raises(ToolError):await wait(client,'inspect_botanical_subset_source',**opts)
            finally:image.write_bytes(original)
            await client.call_tool('save_blend',{'path':'before-cards.blend'})
            fault=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',str(Path(__file__).with_name('native_subset_blade_faults.py')),'--',str(root/'library/before-cards.blend'),str(root/'library')],capture_output=True,text=True,timeout=120)
            assert fault.returncode==0,fault.stdout+'\n'+fault.stderr
            assert 'NATIVE_BLADE_CARD_ROLLBACK_OK' in fault.stdout
            subset=await wait(client,'create_botanical_subset',**opts,subset_collection='Cards',expected_plan=p['plan_sha256'])
            assert subset['valid'] and subset['source_unchanged'],subset
            for mode in ('OBSERVED','UNOBSERVED'):
                whole_opts=opts|{'selection':mode};whole_plan=await wait(client,'inspect_botanical_subset_source',**whole_opts)
                whole=await wait(client,'create_botanical_subset',**whole_opts,subset_collection=mode,expected_plan=whole_plan['plan_sha256'])
                assert whole['valid'] and whole['source_unchanged'] and whole['selected_leaf_count']>0
                await wait(client,'remove_botanical_subset',subset_collection=mode,expected_subset=whole['subset_sha256'])
            assert (await wait(client,'inspect_vegetation_bake',bake_collection='BladePrep'))['preparation_sha256']==prep['preparation_sha256']
            assert (await wait(client,'inspect_botanical_tree',collection='Tree'))['tree_sha256']==source['tree_sha256']
            await wait(client,'remove_vegetation_bake',bake_collection='BladePrep',expected_preparation=prep['preparation_sha256'])
            shutil.rmtree(root/'library/blade');shutil.rmtree(root/'library/capture')
            await client.call_tool('save_blend',{'path':'native-cards.blend'})
            await client.call_tool('open_blend',{'path':'native-cards.blend'})
            subset=await wait(client,'inspect_botanical_subset',subset_collection='Cards')
            assert subset['valid'] and subset['source_unchanged'],subset
            repo=Path(__file__).resolve().parents[1];script=root/'probe.py'
            script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\nFILE='+repr(str(root/'library/native-cards.blend'))+'\n'+r'''
import bpy,hashlib,json
from mcpblender.blender import botanical_subsets as subsets,botanical_trees as trees,botanical_foliage as foliage,subset_templates,bridge
bridge.check_cancelled=lambda:None;bridge.report_progress=lambda p:None
bpy.ops.wm.open_mainfile(filepath=FILE,load_ui=False,use_scripts=False)
col,owned,state=subsets.inspect({'subset_collection':'Cards'});assert state['valid'],state
roles=foliage.resolve_roles(trees.inspect({'collection':'Tree'})['foliage']);prototypes=list(col['mcpblender_leaf_sources'].objects);assert len(prototypes)==1
obj=prototypes[0];obj.data.calc_loop_triangles();assert len(obj.data.loop_triangles)==14
assert subset_templates.protected_signature(obj.data,['LeafUV'])==subset_templates.protected_signature(roles['lo0'].data)
mat=obj.data.materials[0];nodes=mat.node_tree.nodes
if 'MCP Blade Source UV' in nodes:assert nodes['MCP Blade Source UV'].image in owned and nodes['MCP Blade Source UV'].image.packed_file
assert nodes['Leaf Surface'].inputs['Normal'].links[0].from_node.type=='NORMAL_MAP'
assert nodes['Thin Backlighting'].inputs['Normal'].links[0].from_node.type=='NORMAL_MAP'
for node in nodes:
    if node.type=='TEX_IMAGE':assert node.image.packed_file and node.image in owned
# Foreign shared image/material users refuse removal; removing that user restores it.
foreign=bpy.data.materials.new('Foreign');foreign.use_nodes=True;tex=foreign.node_tree.nodes.new('ShaderNodeTexImage');tex.image=nodes['MCP Blade NORMAL'].image
assert not subsets.inspect({'subset_collection':'Cards'})[-1]['valid']
bpy.data.materials.remove(foreign)
assert subsets.inspect({'subset_collection':'Cards'})[-1]['valid']
print('NATIVE_BLADE_CARD_PERSISTENCE_OK',flush=True)
''')
            result=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=120)
            assert result.returncode==0,result.stdout+'\n'+result.stderr
            assert 'NATIVE_BLADE_CARD_PERSISTENCE_OK' in result.stdout
            await wait(client,'remove_botanical_subset',subset_collection='Cards',expected_subset=subset['subset_sha256'])
    asyncio.run(run())
