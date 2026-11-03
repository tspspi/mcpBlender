"""Small-agent structured wind planning/sampling/semantic export without Python tools."""
import asyncio
import json
import os
from pathlib import Path
import shutil
import pytest
from fastmcp.exceptions import ToolError
from mcpblender import wind,botany
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_structured_wind_samples_and_portable_sidecar(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            plan=await wait(client,'plan_botanical_tree',recipe=recipe)
            state=await wait(client,'create_botanical_tree',collection='WindFixture',recipe=recipe,expected_model=plan['model_sha256'])
            cfg={'shoots_per_bud':1,'attachment_nodes':2}
            population=await wait(client,'plan_botanical_foliage',collection='WindFixture',foliage=cfg)
            state=await wait(client,'configure_botanical_foliage',collection='WindFixture',foliage=cfg,expected_tree=state['tree_sha256'],expected_foliage=population['foliage_sha256'])
            args={'collection':'WindFixture','wind':{'steady_mps':[3,1,0],'gust_mps':1.5}}
            info=await tool(client,'inspect_botanical_wind',**args);assert 'recovery' not in info
            sampled=await tool(client,'sample_botanical_wind',**args,seconds=[-.5,.2,1.5],limit=3)
            assert 'recovery' not in sampled and all(len(s['branches'])==3 and len(s['leaves'])==3 for s in sampled['samples'])
            assert all(s['metrics']['max_segment_length_error_m']<1e-12 and s['metrics']['root_anchor_displacement_m']==0 for s in sampled['samples'])
            assert sampled['samples'][0]['leaves']!=sampled['samples'][1]['leaves']
            assert (await tool(client,'inspect_botanical_tree',collection='WindFixture'))['tree_sha256']==state['tree_sha256']
            with pytest.raises(ToolError,match='budget'):await tool(client,'sample_botanical_wind',**args,max_work=1)
            with pytest.raises(ToolError,match='stale'):await tool(client,'export_botanical_wind',**args,path='stale.json',expected_wind='0'*64)
            assert not (root/'library/stale.json').exists()
            exported=await tool(client,'export_botanical_wind',**args,path='wind.json',expected_wind=info['wind_sha256'])
            assert 'recovery' not in exported
            document=json.loads((root/'library/wind.json').read_text());botany.validate(document['model'])
            assert document['field']==info['field'] and document['foliage']['leaves']
            replay=wind.solve(document['model'],document['wind'],.2,document['placement'])
            assert replay['branches'][0]['end_world_m']==sampled['samples'][1]['branches'][0]['end_world_m']
            assert exported['bytes']==(root/'library/wind.json').stat().st_size
            with pytest.raises(ToolError,match='FileExistsError'):await tool(client,'export_botanical_wind',**args,path='wind.json',expected_wind=info['wind_sha256'])
            if target:=os.environ.get('MCPBLENDER_WIND_EVIDENCE_DIR'):
                out=Path(target);out.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'library/wind.json',out/'wind.json')
                (out/'proof.json').write_text(json.dumps({'inspection':info,'samples':sampled,'export':exported},indent=2))
    asyncio.run(run())
