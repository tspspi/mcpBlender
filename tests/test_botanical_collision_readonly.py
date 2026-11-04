"""Collision inspections must not create recovery checkpoints."""
import asyncio
from test_asset_editing import assets_live,client_for,tool,pytestmark
from test_botanical_trees import wait


def test_collision_inspection_checkpoint_classification(assets_live):
    root,path=assets_live
    async def run():
        async with client_for(path) as client:
            recipe={'height':5,'crown_width':5,'attractors':32,'iterations':3,'node_budget':128,'segment_length':1}
            model=await wait(client,'plan_botanical_tree',recipe=recipe)
            source=await wait(client,'create_botanical_tree',collection='ReadOnlyCollision',recipe=recipe,expected_model=model['model_sha256'])
            args={'collection':'ReadOnlyCollision','min_radius_m':0,'max_branch_order':0}
            planned=await tool(client,'inspect_botanical_collision_source',**args)
            assert 'recovery' not in planned
            collision=await tool(client,'create_botanical_collisions',**args,collision_collection='ReadOnlyPieces',expected_plan=planned['plan_sha256'])
            checked=await tool(client,'inspect_botanical_collisions',collision_collection='ReadOnlyPieces')
            assert checked['valid'] and 'recovery' not in checked
            await tool(client,'remove_botanical_collisions',collision_collection='ReadOnlyPieces',expected_collision=checked['collision_sha256'])
            source=await tool(client,'inspect_botanical_tree',collection='ReadOnlyCollision')
            await tool(client,'remove_botanical_tree',collection='ReadOnlyCollision',expected_tree=source['tree_sha256'])
    asyncio.run(run())
