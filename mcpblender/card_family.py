"""Deterministic one-sided alternative selection; no interpolation or synthesis."""
import math

DIRECTIONS={'TOP':(0.,0.,1.),'FRONT':(0.,-1.,0.),'SIDE':(1.,0.,0.)}


def unit(value):
    if len(value)!=3 or any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) for v in value):raise ValueError('Finite three-component direction required')
    scale=max(abs(v) for v in value)
    if not scale:raise ValueError('Nonzero direction required')
    scaled=[v/scale for v in value];length=math.sqrt(sum(v*v for v in scaled))
    return [v/length for v in scaled]


def choose(normals,directions,max_angle_degrees):
    if not normals or len(normals)>3 or any(v not in DIRECTIONS for v in normals):raise ValueError('One to three named canonical views required')
    if not directions or len(directions)>9:raise ValueError('One to nine viewer directions required')
    if isinstance(max_angle_degrees,bool) or not isinstance(max_angle_degrees,(int,float)) or not math.isfinite(max_angle_degrees) or not 0<max_angle_degrees<=80:raise ValueError('Invalid family angular limit')
    rays=[unit(v) for v in directions];rows=[]
    for view in DIRECTIONS: # Tie order is canonical, independent of entry order.
        if view not in normals:continue
        n=unit(normals[view]);angles=[math.degrees(math.acos(max(-1.,min(1.,sum(a*b for a,b in zip(n,ray)))))) for ray in rays]
        rows.append({'view':view,'centre_angle_degrees':angles[0],'max_angle_degrees':max(angles),'normal_world':n})
    # Pick the closest centre direction. A perspective edge outside its cone
    # refuses that candidate; do not silently substitute a farther centre view.
    selected=min(rows,key=lambda r:r['centre_angle_degrees'])
    supported=selected['max_angle_degrees']<=max_angle_degrees+1e-9
    return {'method':'NEAREST_ONE_SIDED_CARD_V1','supported':supported,'selected_view':selected['view'] if supported else None,
            'nearest_view':selected['view'],'max_angle_degrees':max_angle_degrees,'candidates':rows,
            'checked_directions':len(rays),'scope':'Explicit static nearest alternative; no blending, back-view synthesis, automatic camera following or optical equivalence.'}
