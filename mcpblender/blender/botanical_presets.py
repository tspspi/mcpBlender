"""Create complete editable reference assets with bounded rollback and guards."""
import json
import bpy
from mcpblender import botanical_presets as presets
from . import botanical_trees as trees,botanical_surfaces as surfaces

COMMANDS={'botanical_asset_presets','plan_botanical_asset_preset','create_botanical_asset_preset'}


def plan(p):
    from .bridge import check_cancelled,report_progress
    # Bound cancellation RPCs during the pure generator's inner loops.
    ticks=[0]
    def cancel():
        ticks[0]+=1
        if ticks[0]%256==0:check_cancelled()
    check_cancelled();return presets.plan(p,cancelled=cancel,progress=report_progress)


def create(p):
    from .bridge import check_cancelled,report_progress
    info=plan(p)[-1]
    if info['preset_sha256']!=p['expected_preset']:raise ValueError('Botanical preset plan is stale')
    before=set(bpy.data.user_map());success=False
    try:
        state=trees.create({'collection':p['collection'],'recipe':info['tree_recipe'],'expected_model':info['model_sha256'],
                            'location':p['location'],'radial_sides':info['radial_sides'],'bark_tile_length':info['bark_tile_length'],'foliage':info['foliage_recipe']})
        col=bpy.data.collections[state['collection']];meta=json.loads(col[trees.META])
        bark=bpy.data.materials[state['geometry']['bark_material']];leaf=bpy.data.materials[meta['foliage']['material']]
        for mat,settings in ((bark,info['surfaces']['bark']),(leaf,info['surfaces']['leaf'])):
            check_cancelled();report_progress({'phase':'configuring botanical preset surfaces','material':mat.name})
            guard=surfaces.inspect({'material':mat.name})['material_sha256']
            result=surfaces.configure({'material':mat.name,'expected_material':guard,'settings':settings})
            if not result['detail_valid']:raise ValueError('Preset procedural surface failed verification')
        if meta['model_sha256']!=info['model_sha256'] or meta['foliage']['compact_sha256']!=info['foliage_sha256']:raise ValueError('Created preset geometry differs from plan')
        meta['asset_preset']={'name':info['preset'],'version':info['version'],'creation_plan_sha256':info['preset_sha256']}
        col[trees.META]=json.dumps(meta,sort_keys=True,allow_nan=False)
        state=trees.inspect({'collection':col.name})
        if not state['valid']:raise ValueError('Created preset failed botanical ownership verification')
        report_progress({'phase':'verified botanical preset before handoff','leaves':info['foliage_metrics']['leaves'],'triangles':info['triangles']});check_cancelled()
        success=True;return state|{'preset_plan':info}
    finally:
        if not success:
            created=set(bpy.data.user_map())-before
            if created:bpy.data.batch_remove(ids=tuple(created))


def dispatch(command,p):
    if command=='botanical_asset_presets':return presets.catalog()
    if command=='plan_botanical_asset_preset':return plan(p)[-1]
    return create(p)
