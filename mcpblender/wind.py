"""Portable deterministic world wind and anchored botanical segment rotations."""
import math
from . import botany as b,foliage
from .foliage_coverage import rotation as euler_rotation

FORMAT='mcpblender-hierarchical-wind-v1'
SOLVER='ANCHORED_SEGMENT_ROTATIONS_V1'
IDENTITY=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
DEFAULTS={'seed':1,'steady_mps':[2.,0.,0.],'gust_mps':1.,'waves':3,'wavelength_m':12.,'frequency_hz':.2,
          'bend_degrees_per_mps':.5,'max_segment_degrees':3.,'max_accumulated_degrees':60.,
          'flutter_degrees':4.,'flutter_hz':2.,'phase_offset':0.}


def mv(m,v):return tuple(b.dot(row,v) for row in m)
def transpose(m):return tuple(zip(*m))
def mm(a,c):return tuple(tuple(b.dot(row,col) for col in zip(*c)) for row in a)
def finite_vector(v,n=3):return isinstance(v,(list,tuple)) and len(v)==n and all(type(x) in (int,float) and math.isfinite(x) for x in v)


def recipe(value):
    if set(value)-set(DEFAULTS):raise ValueError('Unknown wind settings')
    p=DEFAULTS|value
    limits={'seed':(0,2147483647),'gust_mps':(0,30),'waves':(1,8),'wavelength_m':(.1,10000),'frequency_hz':(.001,10),
            'bend_degrees_per_mps':(0,10),'max_segment_degrees':(0,10),'max_accumulated_degrees':(1,170),
            'flutter_degrees':(0,30),'flutter_hz':(.01,20),'phase_offset':(-10000,10000)}
    for key,(low,high) in limits.items():
        if type(p[key]) not in (int,float) or not math.isfinite(p[key]) or not low<=p[key]<=high:raise ValueError('Invalid wind setting: '+key)
        if key in {'seed','waves'}:
            if type(p[key])!=int:raise ValueError('Wind counts/seed must be integers')
        else:p[key]=float(p[key])
    if not finite_vector(p['steady_mps']) or any(abs(x)>100 for x in p['steady_mps']):raise ValueError('Finite bounded steady wind vector required')
    p['steady_mps']=[float(x) for x in p['steady_mps']]
    return p


def field(p):
    p=recipe(p);waves=[]
    for i in range(p['waves']):
        angle=2*math.pi*b.rnd(p['seed'],'wind:direction',i)
        kdir=b.unit((math.cos(angle),math.sin(angle),.3*(b.rnd(p['seed'],'wind:height',i)-.5)))
        frequency=p['frequency_hz']*(.65+.7*b.rnd(p['seed'],'wind:frequency',i))
        wavelength=p['wavelength_m']*(.6+.8*b.rnd(p['seed'],'wind:wavelength',i))
        direction=(math.cos(angle+.4),math.sin(angle+.4),0.)
        waves.append({'wave_vector_rad_per_m':list(b.mul(kdir,2*math.pi/wavelength)),
                      'amplitude_mps':list(b.mul(direction,p['gust_mps']/math.sqrt(p['waves']))),
                      'angular_frequency_rad_per_s':2*math.pi*frequency,'phase_rad':2*math.pi*b.rnd(p['seed'],'wind:phase',i)})
    return {'steady_mps':p['steady_mps'],'waves':waves,'formula':'steady + sum(amplitude * sin(dot(wave_vector, world_position_m) - angular_frequency * seconds + phase))'}


def velocity(compiled,position_m,seconds):
    if not finite_vector(position_m) or type(seconds) not in (int,float) or not math.isfinite(seconds) or abs(seconds)>1e6:raise ValueError('Finite wind position/time required; time limit is 1e6 seconds')
    result=tuple(compiled['steady_mps'])
    for wave in compiled['waves']:
        phase=b.dot(wave['wave_vector_rad_per_m'],position_m)-wave['angular_frequency_rad_per_s']*seconds+wave['phase_rad']
        result=b.add(result,b.mul(wave['amplitude_mps'],math.sin(phase)))
    return result


def placement(value=None):
    if value is not None and set(value)-{'rotation','translation_m','scale'}:raise ValueError('Unknown wind placement fields')
    p={'rotation':IDENTITY,'translation_m':(0.,0.,0.),'scale':1.}|(value or {})
    r=p['rotation'];scale=p['scale']
    if not isinstance(r,(list,tuple)) or len(r)!=3 or not all(finite_vector(row) for row in r) or not finite_vector(p['translation_m']) or type(scale) not in (int,float) or not math.isfinite(scale) or scale<=0:raise ValueError('Finite positive similarity placement required')
    product=mm(transpose(r),r);det=b.dot(r[0],foliage.cross(r[1],r[2]))
    if any(abs(product[i][j]-(i==j))>1e-6 for i in range(3) for j in range(3)) or abs(det-1)>1e-6:raise ValueError('Wind placement requires a proper rotation without shear/reflection')
    # Native matrices use float32. Remove admitted roundoff before treating this
    # as a rigid placement; genuine shear/nonuniform scale was refused above.
    columns=list(zip(*r));x=b.unit(columns[0]);y=b.unit(b.sub(columns[1],b.mul(x,b.dot(x,columns[1]))));z=foliage.cross(x,y)
    r=transpose((x,y,z))
    return {'rotation':[list(row) for row in r],'translation_m':list(p['translation_m']),'scale':float(scale)}


def world(p,point):return b.add(p['translation_m'],b.mul(mv(p['rotation'],point),p['scale']))


def axis_rotation(axis,angle):
    if abs(angle)<1e-15:return IDENTITY
    x,y,z=b.unit(axis);c=math.cos(angle);s=math.sin(angle);v=1-c
    return ((c+x*x*v,x*y*v-z*s,x*z*v+y*s),(y*x*v+z*s,c+y*y*v,y*z*v-x*s),(z*x*v-y*s,z*y*v+x*s,c+z*z*v))


def rotation_degrees(r):return math.degrees(math.acos(max(-1.,min(1.,(sum(r[i][i] for i in range(3))-1)/2))))


def rotation_bound(model,settings,where=None):
    """Triangle-inequality upper bound, independent of time and wave cancellation."""
    p=recipe(settings);where=placement(where);speed=b.length(p['steady_mps'])+p['gust_mps']*math.sqrt(p['waves']);bounds={}
    for branch in model['branches']:
        angle=min(p['max_segment_degrees'],p['bend_degrees_per_mps']*speed*(1-.9*branch['stiffness'])*min(1.,b.length(b.sub(branch['end'],branch['start']))*where['scale']))
        bounds[branch['id']]=bounds.get(branch['parent_id'],0.)+angle
    bound=max(bounds.values())
    return {'field_speed_upper_bound_mps':speed,'accumulated_angle_upper_bound_degrees':bound,
            'rotation_budget_proven_for_all_times':bound<=p['max_accumulated_degrees'],
            'scope':'Conservative summed-angle bound; exceeding it does not prove a sampled pose violates the configured rotation limit.'}


def solve(model,settings,seconds,where=None,*,cancelled=lambda:None,progress=lambda v:None):
    b.validate(model);p=recipe(settings);where=placement(where);compiled=field(p)
    records=[];lookup={};max_length_error=max_joint_error=max_rotation=0.
    for i,branch in enumerate(model['branches']):
        if i%64==0:cancelled();progress({'phase':'sampling hierarchical wind','branches':i,'total_branches':len(model['branches'])})
        parent=lookup.get(branch['parent_id']);parent_rotation=parent['rotation_local'] if parent else IDENTITY
        start=tuple(parent['end_local_m']) if parent else tuple(branch['start'])
        v=velocity(compiled,world(where,branch['start']),seconds);local_wind=mv(transpose(where['rotation']),v)
        direction=mv(parent_rotation,b.sub(branch['end'],branch['start']));axis=foliage.cross(direction,local_wind)
        phase=.85+.15*math.sin(2*math.pi*p['frequency_hz']*seconds+branch['phase']+p['phase_offset'])
        excitation=b.length(axis)/b.length(direction)
        angle=math.radians(min(p['max_segment_degrees'],p['bend_degrees_per_mps']*excitation*(1-.9*branch['stiffness'])*min(1.,b.length(direction)*where['scale'])*phase))
        r=mm(axis_rotation(axis,angle) if b.length(axis)>1e-12 else IDENTITY,parent_rotation)
        cumulative=rotation_degrees(r)
        if cumulative>p['max_accumulated_degrees']+1e-7:raise ValueError('Wind accumulated rotation budget exceeded; reduce response or explicitly raise its bound')
        end=b.add(start,mv(r,b.sub(branch['end'],branch['start'])))
        record={'id':branch['id'],'index':i,'parent_id':branch['parent_id'],'start_local_m':list(start),'end_local_m':list(end),
                'rotation_local':[list(row) for row in r],'parent_relative_rotation': [list(row) for row in mm(transpose(parent_rotation),r)],
                'start_world_m':list(world(where,start)),'end_world_m':list(world(where,end)),'field_mps':list(v)}
        length_error=abs(b.length(b.sub(end,start))-b.length(b.sub(branch['end'],branch['start'])))*where['scale']
        joint_error=b.length(b.sub(start,parent['end_local_m']))*where['scale'] if parent else 0.
        max_length_error=max(max_length_error,length_error);max_joint_error=max(max_joint_error,joint_error);max_rotation=max(max_rotation,cumulative)
        records.append(record);lookup[branch['id']]=record
    cancelled()
    displacement=max(b.length(b.sub(row['end_world_m'],world(where,branch['end']))) for row,branch in zip(records,model['branches']))
    return {'seconds':float(seconds),'branches':records,'metrics':{'branches':len(records),'max_segment_length_error_m':max_length_error,
            'max_junction_error_m':max_joint_error,'max_accumulated_rotation_degrees':max_rotation,'max_endpoint_displacement_m':displacement,
            'root_anchor_displacement_m':b.length(b.sub(records[0]['start_world_m'],world(where,model['branches'][0]['start'])) )},'placement':where}


def transform_point(branch,pose,point):return b.add(pose['start_local_m'],mv(pose['rotation_local'],b.sub(point,branch['start'])))


def leaf_pose(leaf,branch,pose,settings,seconds,where=None):
    p=recipe(settings);where=placement(where)
    angle=math.radians(p['flutter_degrees'])*leaf['flutter']*min(1.,b.length(p['steady_mps'])+p['gust_mps'])*math.sin(2*math.pi*p['flutter_hz']*seconds+leaf['phase']+p['phase_offset'])
    r=mm(mm(pose['rotation_local'],euler_rotation(leaf['rotation'])),axis_rotation((1,0,0),angle))
    position=transform_point(branch,pose,leaf['position'])
    return {'id':leaf['id'],'parent_branch_id':branch['id'],'position_local_m':list(position),'position_world_m':list(world(where,position)),
            'rotation_local':[list(row) for row in r],'scale':leaf['scale'],'variant':leaf['variant'],'flutter_angle_degrees':math.degrees(angle)}
