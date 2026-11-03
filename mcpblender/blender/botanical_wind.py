"""Guarded portable motion data over unchanged managed botanical masters."""
import json
import math
import os
from pathlib import Path
import tempfile
import bpy
from mcpblender import wind,botany,foliage
from mcpblender.storage import require_space
from . import botanical_trees as trees,botanical_foliage

COMMANDS={'inspect_botanical_wind','sample_botanical_wind','export_botanical_wind'}


def source(p):
    bpy.context.view_layer.update()
    values=trees.inventory(p);state=values[-1];model=values[-2];root=values[1]
    if not state['valid'] or state['model_error'] or state['replacement_blockers']:raise ValueError('Wind requires a valid botanical master and an uncontrolled root')
    unit=state['scene_unit_scale'];matrix=root.matrix_world
    scales=[matrix.to_3x3().col[i].length*unit for i in range(3)];scale=sum(scales)/3
    if not math.isfinite(scale) or scale<=0 or max(abs(s-scale) for s in scales)>max(1e-8,scale*1e-6):raise ValueError('Wind placement requires positive uniform physical scale')
    placement=wind.placement({'rotation':[[matrix[i][j]*unit/scale for j in range(3)] for i in range(3)],
                              'translation_m':[matrix[i][3]*unit for i in range(3)],'scale':scale})
    cfg=wind.recipe(p['wind']);compiled=wind.field(cfg)
    info={'format':wind.FORMAT,'solver':wind.SOLVER,'wind':cfg,'field':compiled,'placement':placement,
          'placement_rotation_fit_error':max(abs(matrix[i][j]*unit/scale-placement['rotation'][i][j]) for i in range(3) for j in range(3)),
          'tree_sha256':state['tree_sha256'],'model_sha256':state['model_sha256'],
          'foliage_sha256':state['foliage']['compact_sha256'] if state['foliage'] else None}
    return values,info|{'wind_sha256':botany.digest(info)}


def layout(values):
    meta=values[-1]['foliage']
    return botanical_foliage.build_layout(values[-2],meta['recipe']) if meta else None


def inspect(p):
    values,info=source(p)
    return info|{'branches':len(values[-2]['branches']),'leaves':values[-1]['foliage']['metrics']['leaves'] if values[-1]['foliage'] else 0,
                'all_time_rotation_bound':wind.rotation_bound(values[-2],info['wind'],info['placement']),
                'scope':'Portable artistic kinematics, frozen evaluated placement in world metres. Root anchoring and segment length are exact in the model; sleeve-surface strain, native animation, shader/export attribute retention and collision are not certified.'}


def sample(p):
    from .bridge import check_cancelled,report_progress
    values,info=source(p);model=values[-2];meta=values[-1]['foliage'];count=meta['metrics']['leaves'] if meta else 0
    work=len(p['seconds'])*(len(model['branches'])+min(p['limit'],max(0,count-p['leaf_offset'])))
    if work>p['max_work']:raise ValueError('Wind sampling work budget exceeded')
    population=layout(values);selected=population['leaves'][p['leaf_offset']:p['leaf_offset']+p['limit']] if population else []
    samples=[]
    for seconds in p['seconds']:
        result=wind.solve(model,info['wind'],seconds,info['placement'],cancelled=check_cancelled,progress=report_progress)
        leaves=[wind.leaf_pose(leaf,model['branches'][leaf['parent_branch_index']],result['branches'][leaf['parent_branch_index']],info['wind'],seconds,info['placement']) for leaf in selected]
        samples.append({'seconds':seconds,'branches':result['branches'][p['offset']:p['offset']+p['limit']],
                        'leaves':leaves,'metrics':result['metrics']})
    return {'wind_sha256':info['wind_sha256'],'samples':samples,'branches':len(model['branches']),'leaves':count,
            'offset':p['offset'],'leaf_offset':p['leaf_offset'],'work':work,'placement':info['placement'],
            'scope':'All-branch centerline metrics; paged leaf rigid poses only. No native mesh deformation, tube-surface strain, optical or engine qualification.'}


def export(p):
    from .bridge import check_cancelled,report_progress,_bridge
    values,info=source(p)
    if info['wind_sha256']!=p['expected_wind']:raise ValueError('Botanical wind fingerprint is stale; inspect again')
    path=Path(p['path'])
    if path.exists() and not p['overwrite']:raise FileExistsError(path)
    population=layout(values)
    document=info|{'model':values[-2],'foliage':population,
       'rules':{'branch_pivot':'segment start; parent-first rotations attach child start to posed parent end',
                'field_sampling':'Evaluate the common field at each undeformed segment start mapped to world metres; no deformation feedback or aeroelastic iteration.',
                'response':'clamped degrees_per_mps * perpendicular field speed * (1 - .9 * stiffness) * min(1, world segment length m) * (.85 + .15*sin(2*pi*frequency_hz*seconds + branch phase + phase_offset))',
                'leaf_flutter':'branch-rigid leaf placement; intrinsic local X rotation by flutter_degrees * leaf flutter * min(1, length(steady_mps)+gust_mps) * sin(2*pi*flutter_hz*seconds + leaf phase + phase_offset)',
                'coordinates':'canonical right-handed Z-up metres; placement maps to world metres; Euler leaf sources are XYZ; sampled rotations are matrices',
                'limitations':'Artistic kinematic model. No mesh buffers, GPU packing, native animation, sleeve strain, aeroelasticity, collision or engine shader supplied.'}}
    encoded=(json.dumps(document,sort_keys=True,allow_nan=False)+'\n').encode()
    if len(encoded)>p['max_bytes']:raise ValueError('Wind semantic sidecar exceeds max_bytes')
    policy=_bridge.active.get('storage',{}) if _bridge and _bridge.active else {}
    if _bridge and _bridge.active:_bridge.active['storage'].update(estimated_bytes=len(encoded),estimate_kind='serialized_wind_semantics_bytes')
    require_space(path,len(encoded),reserve_bytes=policy.get('reserve_bytes',256*1024**2),estimate_kind='serialized_wind_semantics_bytes')
    report_progress({'phase':'publishing portable wind semantics','bytes':len(encoded),'native_call_interruptible':False});temporary=None
    try:
        check_cancelled()
        with tempfile.NamedTemporaryFile(prefix='.mcpblender-wind-',dir=path.parent,delete=False) as stream:
            temporary=Path(stream.name);stream.write(encoded);stream.flush();os.fsync(stream.fileno())
        check_cancelled()
        if p['overwrite']:temporary.replace(path);temporary=None
        else:os.link(temporary,path)
    finally:
        if temporary is not None:temporary.unlink()
    return {'path':str(path),'bytes':len(encoded),'wind_sha256':info['wind_sha256'],'format':wind.FORMAT,'scope':document['rules']['limitations']}


def dispatch(command,p):return {'inspect_botanical_wind':inspect,'sample_botanical_wind':sample,'export_botanical_wind':export}[command](p)
