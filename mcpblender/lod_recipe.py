"""Dependency-free generation defaults for native suggestions and MCP contracts."""
from copy import deepcopy
import math

DEFAULTS={'transfer_normals':True,'max_relative_error':.1,'error_samples':512,'skin_max_influences':4,
          'skin_joint_importance':10,'pose_frames':None,'max_pose_error':.1}
LEVEL_DEFAULTS={'method':'COLLAPSE','angle_degrees':5,'iterations':1}


def suggested_recipe(value):
    """Normalize recorded settings; frontend contracts validate submitted edits."""
    result=deepcopy(DEFAULTS);result.update(value)
    if not isinstance(result.get('levels'),list) or not 1<=len(result['levels'])<=7:raise ValueError('Invalid recorded LOD level recipe')
    result['levels']=[dict(LEVEL_DEFAULTS,**level) for level in result['levels']]
    budgets=[level.get('triangle_budget') for level in result['levels']]
    if any(type(n)!=int or not 4<=n<=500000 for n in budgets) or any(a<=b for a,b in zip(budgets,budgets[1:])):raise ValueError('Invalid recorded LOD budgets')
    for level in result['levels']:
        if level['method'] not in {'COLLAPSE','PLANAR','UNSUBDIVIDE'}:raise ValueError('Invalid recorded reduction method')
        if type(level['iterations'])!=int or not 1<=level['iterations']<=6:raise ValueError('Invalid recorded reduction iterations')
        angle=level['angle_degrees']
        if not isinstance(angle,(int,float)) or not math.isfinite(angle) or not 0<=angle<=180:raise ValueError('Invalid recorded reduction angle')
    ranges={'max_relative_error':(0,1),'error_samples':(16,4096),'skin_max_influences':(1,4),'skin_joint_importance':(0,1000),'max_pose_error':(0,1)}
    for key,(low,high) in ranges.items():
        number=result[key]
        if not isinstance(number,(int,float)) or not math.isfinite(number) or not low<=number<=high:raise ValueError('Invalid recorded LOD option: '+key)
    frames=result.get('pose_frames')
    if frames is not None and (not isinstance(frames,list) or not 1<=len(frames)<=16 or any(not isinstance(f,(int,float)) or not math.isfinite(f) or abs(f)>1048574 for f in frames) or len(set(frames))!=len(frames)):raise ValueError('Invalid recorded pose frames')
    return {k:v for k,v in result.items() if v is not None}
