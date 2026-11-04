"""Opt-in projected foliage opacity rebake from a retained native snapshot."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import time
import pytest
from fastmcp.exceptions import ToolError
from mcpblender.texture_contracts import TextureSources
from test_asset_editing import assets_live,client_for,tool,pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_ALPHA_FIXTURE'),reason='Retained projection fixture required')
def test_projected_opacity_rebake(assets_live):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    fixture=Path(os.environ['MCPBLENDER_ALPHA_FIXTURE']);proof=json.loads((fixture/'proof.json').read_text())
    bundle=next(p for p in fixture.iterdir() if p.is_dir() and (p/'source.blend').is_file());job=json.loads((bundle/'job.json').read_text())
    shutil.copy2(bundle/'source.blend',library/'input.blend')
    shutil.copytree(bundle,library/'legacy')
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data;deadline=time.monotonic()+600
                while True:
                    state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':10})).data
                    assert state['state'] not in {'failed','cancelled','interrupted'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline,('Still live; do not replay',queued['operation_id'])
            await client.call_tool('open_blend',{'path':'legacy/asset.blend'})
            assert (await operation('validate_texture_bake',directory='legacy'))['map_policy'] is None
            await client.call_tool('open_blend',{'path':'input.blend'})
            sources={k:v for k,v in job.items() if k in TextureSources.model_fields}
            inspected=await operation('inspect_texture_bake',**sources);assert inspected['complete']
            settings={k:job[k] for k in ('maps','width','height','samples','cage_extrusion','max_ray_distance','min_projection_coverage','threads','timeout_seconds')}
            margin=int(os.environ.get('MCPBLENDER_ALPHA_PROBE_MARGIN','2'))
            baked=await operation('bake_textures',**(sources|settings|{'expected_bake':inspected['bake_sha256'],'directory':'rebaked-card','margin':margin}))
            assert baked['live_scene_unchanged']
            assert baked['map_policy']=={'method':'PROJECTED_ALPHA_NO_EXTEND_V1','alpha_margin':0,'other_map_margin':margin}
            assert all(m['bake_margin']==(0 if m['map']=='ALPHA' else margin) for m in baked['maps'])
            await client.call_tool('open_blend',{'path':'rebaked-card/asset.blend'})
            assert (await operation('validate_texture_bake',directory='rebaked-card'))['validated']
            # Finished-file recovery remains policy-bound and never replays baking.
            marker=library/'rebaked-card/.mcpblender-texture-job.json'
            record=json.loads(marker.read_text());record.update(state='running',parent_pid=None,worker_pid=None)
            original_policy=dict(record['map_policy']);record['map_policy']['alpha_margin']=1
            marker.write_text(json.dumps(record))
            with pytest.raises(ToolError):
                await client.call_tool('recover_texture_job',{'params':{'directory':'rebaked-card'},'wait':True})
            assert json.loads(marker.read_text())['state']=='running'
            record['map_policy']=original_policy;marker.write_text(json.dumps(record))
            recovered=await operation('recover_texture_job',directory='rebaked-card')
            assert recovered['reconciled'] and recovered['replayed'] is False
            assert (await operation('validate_texture_bake',directory='rebaked-card'))['validated']

            await operation('export_objects_glb',objects=[sources['name']],path='rebaked-card.glb')
            if directory:=os.environ.get('MCPBLENDER_ALPHA_REBAKE_EVIDENCE'):
                out=Path(directory);out.mkdir(parents=True,exist_ok=True)
                shutil.copytree(library/'rebaked-card',out/'rebaked-card',dirs_exist_ok=True)
                shutil.copy2(library/'rebaked-card.glb',out/'rebaked-card.glb')
                (out/'proof.json').write_text(json.dumps(proof|{'bake':baked,'margin':margin},indent=2))
    asyncio.run(run())
