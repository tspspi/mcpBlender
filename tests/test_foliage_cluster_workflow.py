"""Code-disabled typed MCP cluster plans preserve the editable native source."""
import asyncio
import pytest
from fastmcp.exceptions import ToolError
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_cluster_planning_mcp_pagination_budgets_and_source_preservation(assets_live):
    root,config=assets_live
    async def run():
        async with client_for(config) as client:
            assert 'execute_code' not in {t.name for t in await client.list_tools()}
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            planned=await wait(client,'plan_botanical_tree',recipe=recipe)
            state=await wait(client,'create_botanical_tree',collection='ClusterMaster',recipe=recipe,expected_model=planned['model_sha256'])
            cfg={'shoots_per_bud':2,'attachment_nodes':5}
            pop=await wait(client,'plan_botanical_foliage',collection='ClusterMaster',foliage=cfg)
            state=await wait(client,'configure_botanical_foliage',collection='ClusterMaster',foliage=cfg,expected_tree=state['tree_sha256'],expected_foliage=pop['foliage_sha256'])
            args={'collection':'ClusterMaster','max_leaves':17,'limit':1}
            first=await wait(client,'inspect_botanical_foliage_clusters',**args)
            allrows=[]
            for offset in range(first['cluster_count']):
                page=await wait(client,'inspect_botanical_foliage_clusters',**(args|{'offset':offset}))
                assert page['plan_sha256']==first['plan_sha256'] and len(page['clusters'])==1
                allrows.extend(page['clusters'])
            assert sum(r['leaf_count'] for r in allrows)==first['source_leaves']
            assert sum(r['source_triangles'] for r in allrows)==first['source_triangles']
            assert all(r['leaf_count']<=17 and 'leaf_indices' not in r for r in allrows)
            with pytest.raises(ToolError,match='count budget'):
                await wait(client,'inspect_botanical_foliage_clusters',**(args|{'max_clusters':1}))
            unchanged=await tool(client,'inspect_botanical_tree',collection='ClusterMaster')
            assert unchanged['tree_sha256']==state['tree_sha256']
            await tool(client,'remove_botanical_tree',collection='ClusterMaster',expected_tree=state['tree_sha256'])
    asyncio.run(run())
