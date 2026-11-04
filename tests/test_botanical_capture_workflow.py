"""Native tree-only captures through MCP with arbitrary Python disabled."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


@pytest.fixture(autouse=True)
def drain_captures(assets_live):
    yield
    async def run():
        async with client_for(assets_live[1]) as client:
            for row in (await client.call_tool('list_operations')).data['operations']:
                if row['command']=='capture_botanical_views' and row['state'] in {'queued','running'}:
                    await client.call_tool('cancel_operation',{'operation_id':row['operation_id']})
                    await client.call_tool('wait_operation',{'operation_id':row['operation_id'],'timeout_seconds':30})
    asyncio.run(run())


def test_native_tree_multiview_reference_capture(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'attractors':64,'iterations':4,'node_budget':128}
            model=await wait(client,'plan_botanical_tree',recipe=recipe)
            state=await wait(client,'create_botanical_tree',collection='CaptureTree',recipe=recipe,expected_model=model['model_sha256'],location=[4,3,1])
            cfg={'shoots_per_bud':2,'attachment_nodes':4,'leaf':{'rows':12}}
            layout=await wait(client,'plan_botanical_foliage',collection='CaptureTree',foliage=cfg)
            state=await wait(client,'configure_botanical_foliage',collection='CaptureTree',foliage=cfg,expected_tree=state['tree_sha256'],expected_foliage=layout['foliage_sha256'])
            before=await wait(client,'inspect_botanical_tree',collection='CaptureTree')
            args={'collection':'CaptureTree','views':['FRONT','BACK_RIGHT','TOP'],'resolution':64,'samples':4}
            plan=await wait(client,'inspect_botanical_view_capture',**args)
            assert plan['leaf_instances']==state['foliage']['metrics']['leaves']
            assert plan['root_pivot_world_m']==[4,3,1]
            with pytest.raises(ToolError,match='leaf budget'):
                await wait(client,'inspect_botanical_view_capture',**args,max_leaves=0)
            with pytest.raises(ToolError,match='stale'):
                await wait(client,'capture_botanical_views',**args,directory='stale-capture',expected_capture='0'*64)
            assert not (root/'library/stale-capture').exists()
            queued=(await client.call_tool('capture_botanical_views',{'params':args|{'directory':'tree-capture','expected_capture':plan['capture_sha256']}})).data
            assert queued['state'] in {'queued','running'}
            done=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':90})).data
            assert done['state']=='succeeded',done
            proof=await tool(client,'validate_render_job',directory='tree-capture')
            assert len(proof['outputs'])==6 and proof['botanical_capture']['leaf_instances']==plan['leaf_instances']
            assert (await wait(client,'inspect_botanical_tree',collection='CaptureTree'))['tree_sha256']==before['tree_sha256']
            data=await wait(client,'inspect_botanical_capture_data',directory='tree-capture',views=['FRONT'])
            measured=data['views'][0]
            assert measured['covered_pixels']>0 and measured['nonfinite_covered']==0 and measured['reconstructed_outside_bounds']==0
            assert measured['statistics']['depth_position_error_m']['max']<.001
            assert measured['statistics']['position_projection_error_px']['max']<.01
            bundle=root/'library/tree-capture'
            # Immutable content inspection remains available after copying, while
            # owner/inode-scoped recovery validation continues to reject copies.
            shutil.copytree(bundle,root/'library/copied-capture')
            copied=await wait(client,'inspect_botanical_capture_data',directory='copied-capture',views=['FRONT'])
            assert copied['data_sha256']==data['data_sha256']
            with pytest.raises(ToolError,match='identity'):await tool(client,'validate_render_job',directory='copied-capture')
            code="import bpy,json\nbpy.ops.wm.open_mainfile(filepath="+repr(str(bundle/'source.blend'))+",use_scripts=False)\nassert len(bpy.data.scenes)==1\nassert bpy.data.objects.get('Cube') is None and bpy.data.objects.get('Light') is None\ns=bpy.data.scenes[0]\nassert len(s.collection.children)==1\nassert any(n.bl_idname=='GeometryNodeInstanceOnPoints' for g in bpy.data.node_groups for n in g.nodes)\nassert not any(n.bl_idname=='GeometryNodeRealizeInstances' for g in bpy.data.node_groups for n in g.nodes)\n"
            probe=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python-expr',code],capture_output=True,text=True,timeout=30)
            assert probe.returncode==0,probe.stdout+probe.stderr
            manifest=json.loads((bundle/'manifest.json').read_text());manifest['botanical_capture']['root_pivot_world_m'][0]+=1
            original=(bundle/'manifest.json').read_bytes();(bundle/'manifest.json').write_text(json.dumps(manifest))
            try:
                with pytest.raises(ToolError,match='binding'):await tool(client,'validate_render_job',directory='tree-capture')
            finally:(bundle/'manifest.json').write_bytes(original)
            if dest:=os.environ.get('MCPBLENDER_TREE_CAPTURE_EVIDENCE_DIR'):
                out=Path(dest);out.mkdir(parents=True,exist_ok=True);shutil.copytree(bundle,out/'small-bundle',dirs_exist_ok=True)
                (out/'small-proof.json').write_text(json.dumps(proof,indent=2))
    asyncio.run(run())
