"""Versioned reference recipes; artistic study assets, not biological calibration."""
from . import botany,foliage,vegetation_lod

NAME='OAK_CANOPY_STUDY'
VERSION=1
BARK={'profile':'OAK_BARK','uv_map':'BarkUV','cross_scale':24.,'length_scale':2.,
      'dark_color':[.035,.023,.014,1.],'light_color':[.23,.16,.095,1.],'bump_distance':.012,'bump_strength':.5}
LEAF={'profile':'OAK_LEAF','uv_map':'LeafUV','vein_pairs':6,'vein_slope':1.5,'vein_width':.1,'midrib_width':.025,
      'vein_color':[.18,.29,.045,1.],'color_strength':.35,'bump_distance':.0004,'bump_strength':.35}


def catalog():
    return {'presets':[{'name':NAME,'version':VERSION,'species':'QUERCUS_ROBUR','woody_height_m':14.,'crown_width_m':13.,
                        'reference_seeds':[1,2,3],'description':'Dense shared-template canopy study with procedural bark/leaf detail.',
                        'scope':'Artistic reference recipe; mature habit, physical optics, collisions, LOD transitions and runtime performance need separate qualification.'}]}


def plan(p,*,cancelled=None,progress=None):
    cancel=cancelled or (lambda:None);report=progress or (lambda v:None)
    if p['preset']!=NAME:raise ValueError('Unknown botanical asset preset')
    model=botany.generate({'seed':p['seed']},cancelled=cancel,progress=report)
    options={'seed':p['seed'],'shoots_per_bud':12,'attachment_nodes':22,'shoot_length':1.1,'spread':1.,
             'max_leaves':p['max_leaves'],'max_expanded_triangles':p['max_expanded_triangles']}
    # Validate counts before creating leaf records; explicit caller budgets are never raised.
    cfg=foliage.recipe(options);count=len(model['organs'])*cfg['shoots_per_bud']*cfg['attachment_nodes']
    triangles=foliage.leaf_mesh(cfg['leaf'])['triangles']
    wood=vegetation_lod.wood_triangles(model,list(range(len(model['branches']))),8)
    shoots=12*len(model['organs'])*cfg['shoots_per_bud']
    if count>cfg['max_leaves'] or wood+shoots+count*triangles>cfg['max_expanded_triangles']:raise ValueError('Canopy study exceeds leaf/total expanded-triangle budget; choose a different seed or explicitly larger allowed budget')
    layout=foliage.generate(model,cfg,cancelled=cancel,progress=report)
    info={'preset':NAME,'version':VERSION,'tree_recipe':model['recipe'],'foliage_recipe':cfg,'radial_sides':8,'bark_tile_length':1.,
          'model_sha256':botany.digest(model),'foliage_sha256':botany.digest(foliage.compact(layout)),
          'tree_metrics':botany.metrics(model),'foliage_metrics':layout['metrics'],'surfaces':{'bark':BARK,'leaf':LEAF},
          'triangles':{'wood':wood,'shoots':shoots,'stored_with_shared_templates':wood+shoots+cfg['variants']*triangles,
                       'expanded_with_leaves':wood+shoots+count*triangles},
          'export_hint':{'max_instances':count,'note':'Use explicit instance budget for botanical GLB/semantic export; preserve shared templates.'},
          'lod_mask_estimates':{str(resolution):vegetation_lod.mask_estimate(count,resolution,3) for resolution in (64,128)},
          'scope':'Fourteen-metre artistic oak canopy study. Explicit source counts/budgets, shared leaf geometry and procedural native surfaces. No realized population, lighting atlas, PBR bake, LOD/collision, wind-animation or biological/engine qualification.'}
    info['preset_sha256']=botany.digest(info)
    return model,layout,info
