"""Necessary unit-normal slope-cap bounds; passing is not feasibility proof."""
import json
import math

FORMAT='mcpblender-normal-direction-cap-v1'


class DirectionCapError(ValueError):
    def __init__(self,pixel_rect,diagnostic):
        self.diagnostic=diagnostic
        self.pixel_rect=list(pixel_rect)
        super().__init__('Moment facet direction cap ruled out: '+json.dumps(
            {'pixel_rect':self.pixel_rect,'direction_cap':diagnostic},sort_keys=True,allow_nan=False))


def check(values,max_slope,*,fit_tolerance=1e-5,omission_tolerance=1e-6):
    """Bound necessary cap inequalities with componentwise moment roundoff.

    For unit n and z>=c, E[z-c]>=||E[(z-c)n]|| by triangle inequality;
    E[(z-c)(1-z)]>=0 also holds. Neither condition suffices for a supported
    distribution. Fit error and renormalization after bounded omission are
    included before declaring a violation. No observations are changed.
    """
    def finite(v):return type(v) in (int,float) and math.isfinite(v)
    if len(values)!=9 or not all(finite(v) and abs(v)<=1.001 for v in values):raise ValueError('Finite bounded normal moments required')
    if not finite(max_slope) or not .01<=max_slope<=64:raise ValueError('Direction cap slope must be in .01..64')
    if not finite(fit_tolerance) or not 1e-8<=fit_tolerance<=1e-3:raise ValueError('Invalid direction cap fit tolerance')
    if not finite(omission_tolerance) or not 0<=omission_tolerance<=1e-6:raise ValueError('Invalid direction cap omission tolerance')
    if abs(values[3]+values[6]+values[8]-1)>fit_tolerance:raise ValueError('Normal second-moment unit trace is outside tolerance')
    x,y,z,_,_,xz,_,yz,zz=values
    error=fit_tolerance+2*omission_tolerance/(1-omission_tolerance)
    def at(slope):
        c=1/math.hypot(1,slope)
        constraints=[
            {'constraint':'MEAN_FORWARD_COSINE','slack':z-c,'error_bound':error},
            {'constraint':'WEIGHTED_DIRECTION_NORM','slack':z-c-math.hypot(xz-c*x,yz-c*y,zz-c*z),
             'error_bound':(1+math.sqrt(3)*(1+c))*error},
            {'constraint':'BOUNDED_FORWARD_COSINE','slack':(1+c)*z-zz-c,'error_bound':(2+c)*error}]
        failed=[r['constraint'] for r in constraints if r['slack'] < -r['error_bound']]
        return {'max_slope':float(slope),'minimum_direction_z':c,'constraints':constraints,
                'verdict':'RULED_OUT' if failed else 'NOT_RULED_OUT','failed_constraints':failed}
    result=at(max_slope)
    alternatives=[at(s) for s in (16.,32.,64.) if s>max_slope] if result['verdict']=='RULED_OUT' else []
    return {'format':FORMAT,**result,'fit_tolerance':fit_tolerance,'omission_tolerance':omission_tolerance,
            'component_error_bound':error,'higher_cap_bounds':alternatives,
            'next_not_ruled_out_max_slope':next((r['max_slope'] for r in alternatives if r['verdict']=='NOT_RULED_OUT'),None),
            'scope':'Necessary direction-cap bounds only. Not unit-moment matrix validation, feasible decomposition, geometric/clip/precision/budget admission or optical equivalence. No automatic setting change.'}
