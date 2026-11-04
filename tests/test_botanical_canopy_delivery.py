"""Large shared-template geometry/semantic export from the canopy fixture."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import time
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark

source=Path(os.environ['MCPBLENDER_CANOPY_SOURCE']) if os.environ.get('MCPBLENDER_CANOPY_SOURCE') else None
pytestmark=pytestmark+[pytest.mark.skipif(source is None or not source.is_file(),reason='Set MCPBLENDER_CANOPY_SOURCE to retained Canopy1.blend from the canopy study fixture')]


@pytest.mark.parametrize("seed",[1,2,3])
def test_dense_canopy_shared_geometry_semantic_delivery(assets_live,seed):
    root,path=assets_live;library=root/'library';library.mkdir(exist_ok=True)
    selected=source.with_name(f'Canopy{seed}.blend')
    if not selected.is_file():pytest.skip('Retained seeded canopy source is missing')
    filename=f'source-{seed}.blend';directory=f'delivery-{seed}';name=f'Canopy{seed}';expected={1:92136,2:90288,3:88704}[seed]
    shutil.copy2(selected,library/filename)
    evidence=Path(os.environ['MCPBLENDER_CANOPY_DELIVERY_EVIDENCE_DIR']) if os.environ.get('MCPBLENDER_CANOPY_DELIVERY_EVIDENCE_DIR') else None
    if evidence:
        evidence=evidence/f'seed-{seed}';evidence.mkdir(parents=True,exist_ok=True)
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            async def operation(command,**params):
                queued=(await client.call_tool('submit_operation',{'command':command,'params':params})).data;deadline=time.monotonic()+3600
                while True:
                    try:state=(await client.call_tool('wait_operation',{'operation_id':queued['operation_id'],'timeout_seconds':15})).data
                    except ToolError as exc:
                        if not any(v in str(exc) for v in ('Bridge timed out;','Bridge disconnected before a complete response')):raise
                        assert time.monotonic()<deadline;continue
                    trace={'command':command,'operation_id':queued['operation_id'],'state':state['state'],'progress':state.get('progress'),'storage':state.get('storage'),'error':state.get('error')}
                    if evidence:
                        (evidence/'latest-operation.json').write_text(json.dumps(trace,indent=2))
                        with (evidence/'operations.jsonl').open('a') as f:f.write(json.dumps(trace)+'\n')
                    assert state['state'] not in {'failed','cancelled','interrupted','outcome_unknown'},state
                    if state['state']=='succeeded':return state['result']
                    assert time.monotonic()<deadline
            await client.call_tool('open_blend',{'path':filename})
            tree=await operation('inspect_botanical_tree',collection=name);assert tree['valid']
            assert tree['foliage']['metrics']['leaves']==expected and tree['foliage']['metrics']['prototypes']==3
            args={'collection':name,'max_instances':expected}
            plan=await operation('inspect_botanical_export',**args)
            assert plan['leaf_instances']==expected and plan['prototypes']==3
            exported=await operation('export_botanical_bundle',**args,expected_export=plan['export_sha256'],directory=directory)
            assert exported['native_instance_readback']['instances']==expected and len(exported['proof']['assets'])==5
            assert (await operation('inspect_botanical_tree',collection=name))['tree_sha256']==tree['tree_sha256']
            semantics=json.loads((library/directory/'semantics.json').read_text())
            assert len(semantics['foliage']['leaves'])==expected and semantics['foliage']['recipe']['variants']==3
            await operation('remove_botanical_tree',collection=name,expected_tree=tree['tree_sha256'])
            verified=await operation('validate_botanical_bundle',directory=directory)
            assert verified['semantic_sha256']==exported['proof']['semantic_sha256']
            if evidence:(evidence/'export-proof.json').write_text(json.dumps(exported,indent=2))
    try:asyncio.run(run())
    finally:
        if evidence and library.exists():
            (evidence/'library').mkdir(exist_ok=True)
            shutil.copy2(library/filename,evidence/'library'/filename)
            if (library/directory).exists():shutil.copytree(library/directory,evidence/'library'/directory,dirs_exist_ok=True)
        if evidence:
            for file in ('blender.log','bridge/broker.log'):
                source_file=root/file
                if source_file.exists():shutil.copy2(source_file,evidence/source_file.name)
