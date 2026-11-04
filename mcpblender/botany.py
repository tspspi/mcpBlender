"""Versioned, deterministic botanical branch graphs; Python standard library only."""
import hashlib
import json
import math
from collections import defaultdict

FORMAT='mcpblender-botanical-model-v1'
GENERATOR='oak-scaffold-colonization-1'
DEFAULTS={'species':'QUERCUS_ROBUR','seed':1,'height':14.,'crown_width':13.,'crown_base':.23,
 'trunk_radius':.36,'age_years':45.,'primary_branches':9,'attractors':640,'iterations':40,
 'node_budget':1600,'segment_length':.55,'persistence':.45,'light_direction':[0.,0.,1.],
 'light_weight':.12,'gravity':.08,'avoidance':.12,'randomness':.2,'crown_offset':[0.,0.],
 'pipe_exponent':2.,'root_flare':1.5}
REFERENCES=['https://landscapeplants.oregonstate.edu/plants/quercus-robur',
 'https://www.algorithmicbotany.org/papers/colonization.egwnp2007.html']


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def digest_sequence(values):
    """Hash the exact canonical JSON array while retaining only one entry."""
    digest=hashlib.sha256();digest.update(b'[');first=True
    for value in values:
        if not first:digest.update(b',')
        first=False
        digest.update(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode())
        del value
    digest.update(b']')
    return digest.hexdigest()


def uid(seed,key):return hashlib.sha256((GENERATOR+':'+str(seed)+':'+key).encode()).hexdigest()[:20]
def rnd(seed,key,n=0):return int(hashlib.sha256((str(seed)+':'+key+':'+str(n)).encode()).hexdigest()[:16],16)/2**64
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def mul(a,k):return tuple(x*k for x in a)
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def length(a):return math.sqrt(dot(a,a))
def unit(a):
    size=length(a)
    if size<1e-12:raise ValueError('Degenerate botanical direction')
    return mul(a,1/size)
def vector(a):return [round(float(x),8) for x in a]


def recipe(value):
    p=DEFAULTS|value
    if p['species']!='QUERCUS_ROBUR':raise ValueError('Unsupported botanical species profile')
    limits={'seed':(0,2147483647),'height':(1,40),'crown_width':(1,40),'crown_base':(.1,.6),
      'trunk_radius':(.02,1),'age_years':(1,500),'primary_branches':(3,16),'attractors':(32,2048),
      'iterations':(1,80),'node_budget':(128,4000),'segment_length':(.1,2),'persistence':(0,1),
      'light_weight':(0,1),'gravity':(0,1),'avoidance':(0,1),'randomness':(0,1),
      'pipe_exponent':(1.5,3),'root_flare':(1,2)}
    for key,(low,high) in limits.items():
        v=p[key]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not low<=v<=high:raise ValueError('Invalid botanical parameter: '+key)
    for key in ('seed','primary_branches','attractors','iterations','node_budget'):
        if type(p[key])!=int:raise ValueError('Botanical count/seed must be an integer: '+key)
    for key in limits:
        if key not in {'seed','primary_branches','attractors','iterations','node_budget'}:p[key]=float(p[key])
    for key,size in (('light_direction',3),('crown_offset',2)):
        if not isinstance(p[key],(list,tuple)) or len(p[key])!=size or any(not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>40 for v in p[key]):raise ValueError('Invalid botanical vector: '+key)
        p[key]=[float(v) for v in p[key]]
    if length(p['light_direction'])<1e-9:raise ValueError('Light direction must be nonzero')
    if p['trunk_radius']*p['root_flare']>p['height']*.2:raise ValueError('Root radius/flare is too large for tree height')
    if set(value)-set(DEFAULTS):raise ValueError('Unknown botanical recipe fields')
    return p


def species_catalog():
    return {'generator':GENERATOR,'format':FORMAT,'species':[{'id':'QUERCUS_ROBUR','name':'English oak',
        'habit':'Broad rounded crown and stout trunk; alternate bud attachment convention.',
        'defaults':recipe({}),'references':list(REFERENCES)}],
        'scope':'Art-directed scaffold/space-colonization model, not a calibrated botanical or mechanical simulation. Leaves, wind motion, junction unions and species generalization are separate.'}


def generate(value,progress=lambda v:None,cancelled=lambda:None):
    p=recipe(value);seed=p['seed'];h=p['height'];w=p['crown_width'];step=p['segment_length']
    center=(p['crown_offset'][0],p['crown_offset'][1],h*(1+p['crown_base'])/2)
    radii=(w/2,w*.46,h*(1-p['crown_base'])/2)
    nodes=[];children=defaultdict(list);grid=defaultdict(list);cell=max(step*2,w*.16)
    def cell_key(point):return tuple(math.floor(v/cell) for v in point)
    def inside(point,margin=1.):return sum(((point[i]-center[i])/radii[i])**2 for i in range(3))<=margin**2
    def neighbors(point):
        key=cell_key(point)
        for x in range(key[0]-1,key[0]+2):
            for y in range(key[1]-1,key[1]+2):
                for z in range(key[2]-1,key[2]+2):yield from grid.get((x,y,z),())
    def append(parent,start,end,key,order,axis):
        if len(nodes)>=p['node_budget']:return None
        i=len(nodes);node={'id':uid(seed,key),'parent_index':parent,'start':tuple(start),'end':tuple(end),
                          'axis_id':axis,'order':order,'birth_step':0,'length':length(sub(end,start))}
        if node['length']<1e-6:raise ValueError('Degenerate botanical segment')
        nodes.append(node);grid[cell_key(end)].append(i)
        if parent is not None:children[parent].append(i)
        return i
    # A crooked leader/scaffold specifies architecture before crown filling.
    trunk=[];trunk_steps=max(4,math.ceil(h*.65/step));previous=None
    if trunk_steps>=p['node_budget']:raise ValueError('Node budget cannot fit trunk scaffold; increase budget or segment length')
    for i in range(trunk_steps):
        cancelled();t=(i+1)/trunk_steps
        end=(math.sin(t*4+seed)*h*.018*t,math.sin(t*5+seed*.7)*h*.015*t,h*.65*t)
        previous=append(previous,nodes[previous]['end'] if previous is not None else (0.,0.,0.),end,'trunk:'+str(i),0,uid(seed,'axis:trunk'));trunk.append(previous)
    for limb in range(p['primary_branches']):
        cancelled();fraction=(limb+.5)/p['primary_branches'];parent=trunk[min(len(trunk)-1,int((p['crown_base']/.65+(1-p['crown_base']/.65)*fraction*.85)*len(trunk)))]
        start=nodes[parent]['end'];angle=limb*math.pi*(3-math.sqrt(5))+rnd(seed,'primary',limb)*.45
        target=(center[0]+math.cos(angle)*radii[0]*(.72+.18*rnd(seed,'reach',limb)),
                center[1]+math.sin(angle)*radii[1]*(.72+.18*rnd(seed,'reachy',limb)),h*(p['crown_base']+(1-p['crown_base'])*(.35+.5*fraction)))
        count=max(3,math.ceil(length(sub(target,start))/step));origin=start;axis=uid(seed,'axis:primary:'+str(limb))
        for j in range(count):
            t=(j+1)/count
            end=add(add(mul(origin,1-t),mul(target,t)),(0,0,-h*.05*math.sin(t*math.pi)))
            index=append(parent,start,end,f'primary:{limb}:{j}',1,axis)
            if index is None:raise ValueError('Node budget cannot fit primary scaffold; increase budget or segment length')
            parent=index;start=end
    points=[];attempt=0
    while len(points)<p['attractors']:
        cancelled();sample=[2*rnd(seed,'attractor:'+str(attempt),i)-1 for i in range(3)];attempt+=1
        if dot(sample,sample)<=1:
            point=add(center,tuple(sample[i]*radii[i] for i in range(3)));points.append(point)
    initial_points=len(points);light=unit(p['light_direction']);reached=0;iterations=0
    for iteration in range(p['iterations']):
        cancelled();targets=defaultdict(list);remaining=[]
        for ai,point in enumerate(points):
            if ai%128==0:cancelled()
            near=list(neighbors(point))
            if not near:remaining.append(point);continue
            closest=min(near,key=lambda i:dot(sub(point,nodes[i]['end']),sub(point,nodes[i]['end'])))
            delta=sub(point,nodes[closest]['end']);distance=length(delta)
            if distance<step*.85:reached+=1;continue
            remaining.append(point)
            if distance<cell and len(children[closest])<3:targets[closest].append(unit(delta))
        points=remaining;added=0
        for parent,directions in sorted(targets.items()):
            cancelled();node=nodes[parent];old_direction=unit(sub(node['end'],node['start']))
            toward=unit(tuple(sum(d[i] for d in directions) for i in range(3)))
            direction=add(mul(toward,1-p['persistence']),mul(old_direction,p['persistence']))
            direction=add(direction,add(mul(light,p['light_weight']),(0,0,-p['gravity']*min(1,node['order']/3))))
            jitter=tuple((rnd(seed,node['id']+':jitter:'+str(iteration),i)-.5)*p['randomness'] for i in range(3))
            direction=unit(add(direction,jitter));tip=add(node['end'],mul(direction,step))
            # Repel near competing wood while preserving the parent attachment.
            repel=(0.,0.,0.)
            for other in neighbors(tip):
                if other==parent or other in children[parent]:continue
                delta=sub(tip,nodes[other]['end']);distance=length(delta)
                if 1e-8<distance<step:repel=add(repel,mul(unit(delta),(1-distance/step)*p['avoidance']))
            direction=unit(add(direction,repel));tip=add(node['end'],mul(direction,step))
            if not inside(tip,1.02):continue
            if any(dot(direction,unit(sub(nodes[c]['end'],node['end'])))>math.cos(math.radians(25)) for c in children[parent]):continue
            if any(length(sub(tip,nodes[i]['end']))<step*.35 for i in neighbors(tip)):continue
            slot=len(children[parent]);axis=node['axis_id'] if slot==0 else uid(seed,node['id']+':axis:'+str(slot))
            index=append(parent,node['end'],tip,node['id']+':child:'+str(slot),node['order']+(slot>0),axis)
            if index is None:break
            nodes[index]['birth_step']=iteration+1;added+=1
        iterations=iteration+1
        progress({'phase':'growing botanical crown','iteration':iterations,'nodes':len(nodes),'remaining_attractors':len(points),'reached_attractors':reached})
        if not added or not points or len(nodes)>=p['node_budget']:break
    # Declared height is the final centerline height. The rounded crown envelope
    # is guidance, not a promise that wood or eventual leaves fill that volume.
    scale=h/max(n['end'][2] for n in nodes)
    for n in nodes:
        n['start']=(n['start'][0],n['start'][1],n['start'][2]*scale);n['end']=(n['end'][0],n['end'][1],n['end'][2]*scale)
        n['length']=length(sub(n['end'],n['start']))
    demand={}
    for i in reversed(range(len(nodes))):demand[i]=sum(demand[c] for c in children[i])+(1 if not children[i] else .03)+nodes[i]['length']*.08
    factor=p['trunk_radius']/demand[0]**(1/p['pipe_exponent']);branches=[];buds=[];axis_anchor={}
    for i,n in enumerate(nodes):
        cancelled();parent=n['parent_index'];axis_anchor.setdefault(n['axis_id'],n['start'])
        start_radius=factor*demand[i]**(1/p['pipe_exponent'])
        end_radius=min(start_radius,factor*(sum(demand[c] for c in children[i])+.03)**(1/p['pipe_exponent']))
        age=p['age_years']*max(.01,1-.65*n['end'][2]/h-.25*n['birth_step']/max(1,p['iterations']))
        if parent is not None:age=min(age,branches[parent]['age_years'])
        branches.append({'id':n['id'],'parent_id':nodes[parent]['id'] if parent is not None else None,'axis_id':n['axis_id'],
            'order':n['order'],'birth_step':n['birth_step'],'age_years':round(age,6),'start':vector(n['start']),'end':vector(n['end']),
            'radius_start':round(start_radius*(p['root_flare'] if parent is None else 1),8),'radius_end':round(end_radius,8),
            'anchor':vector(axis_anchor[n['axis_id']]),'stiffness':round(min(1,max(.02,(start_radius/p['trunk_radius'])**.7)),8),
            'phase':round(rnd(seed,n['id']+':phase')*2*math.pi,8)})
        if not children[i]:
            buds.append({'id':uid(seed,n['id']+':bud'),'parent_id':n['id'],'kind':'TERMINAL_BUD','position':vector(n['end']),
                         'direction':vector(unit(sub(n['end'],n['start']))),'phyllotaxis':'ALTERNATE','age_years':round(min(age,1.),6)})
    result={'format':FORMAT,'units':'METRE','coordinate_system':'RIGHT_HANDED_Z_UP','generator':GENERATOR,'recipe':p,'species':{'id':p['species'],'profile_version':1},
      'crown':{'shape':'ELLIPSOID','center':vector((center[0],center[1],center[2]*scale)),'radii':vector((radii[0],radii[1],radii[2]*scale))},
      'branches':branches,'organs':buds,'growth':{'iterations':iterations,'attractors':initial_points,'reached':reached,'remaining':len(points),'node_budget_reached':len(nodes)>=p['node_budget']},
      'scope':'Phenomenological woody scaffold and space-colonization growth. Age, stiffness and radii are artist-controlled structural approximations. Bud anchors are semantic organs, not leaf meshes. No biological, mechanical, foliage-coverage or wind-motion certification.'}
    validate(result);return result


def validate(model):
    if model.get('format')!=FORMAT or model.get('generator')!=GENERATOR or model.get('units')!='METRE' or model.get('coordinate_system')!='RIGHT_HANDED_Z_UP':raise ValueError('Unsupported botanical model version')
    p=recipe(model['recipe']);branches=model.get('branches');organs=model.get('organs')
    if not isinstance(branches,list) or not 1<=len(branches)<=p['node_budget'] or not isinstance(organs,list) or len(organs)>p['node_budget']:raise ValueError('Botanical model inventory limits')
    if model.get('species')!={'id':p['species'],'profile_version':1}:raise ValueError('Botanical species profile mismatch')
    crown=model.get('crown',{})
    if crown.get('shape')!='ELLIPSOID' or any(not isinstance(crown.get(k),list) or len(crown[k])!=3 or any(not math.isfinite(v) for v in crown[k]) for k in ('center','radii')) or any(v<=0 for v in crown['radii']):raise ValueError('Invalid botanical crown envelope')
    growth=model.get('growth',{})
    if any(type(growth.get(k))!=int or growth[k]<0 for k in ('iterations','attractors','reached','remaining')) or not 1<=growth['iterations']<=p['iterations'] or growth['attractors']!=p['attractors'] or growth['reached']+growth['remaining']!=p['attractors'] or growth.get('node_budget_reached')!=(len(branches)>=p['node_budget']):raise ValueError('Invalid botanical growth inventory')
    seen={};axes={}
    for b in branches:
        if not isinstance(b['id'],str) or len(b['id'])!=20 or b['id'] in seen:raise ValueError('Invalid/duplicate botanical branch ID')
        if not isinstance(b['axis_id'],str) or len(b['axis_id'])!=20 or type(b['birth_step'])!=int or not 0<=b['birth_step']<=p['iterations']:raise ValueError('Invalid botanical axis/birth step')
        parent=seen.get(b['parent_id'])
        if b['parent_id'] is not None and parent is None:raise ValueError('Botanical parent must precede child')
        for key in ('start','end','anchor'):
            if len(b[key])!=3 or any(not math.isfinite(v) for v in b[key]):raise ValueError('Invalid botanical coordinates')
        if any(not isinstance(b[k],(int,float)) or not math.isfinite(b[k]) for k in ('radius_start','radius_end','stiffness','age_years','phase')) or type(b['order'])!=int or not 0<=b['order']<=100 or not 0<=b['phase']<=2*math.pi+1e-8:raise ValueError('Invalid botanical scalar/order')
        if length(sub(b['end'],b['start']))<1e-6 or not 0<b['radius_end']<=b['radius_start'] or not 0<=b['stiffness']<=1 or not math.isfinite(b['age_years']) or b['age_years']<0:raise ValueError('Invalid botanical radii/age/stiffness')
        if parent and (b['age_years']>parent['age_years']+1e-6 or b['birth_step']<parent['birth_step'] or length(sub(b['start'],parent['end']))>1e-6 or b['order']<parent['order'] or b['radius_start']>parent['radius_end']+1e-5):raise ValueError('Invalid botanical junction/order/radius')
        if not parent and seen:raise ValueError('Botanical graph must have one root')
        if b['axis_id'] not in axes and length(sub(b['anchor'],b['start']))>1e-6:raise ValueError('Axis anchor must be its first segment attachment')
        if b['axis_id'] in axes and (parent is None or parent['axis_id']!=b['axis_id']):raise ValueError('Botanical axis must continue through its parent')
        axes.setdefault(b['axis_id'],b['anchor'])
        if axes[b['axis_id']]!=b['anchor']:raise ValueError('Botanical axis anchor changed')
        seen[b['id']]=b
    if length(branches[0]['start'])>1e-8:raise ValueError('Botanical root must start at the local origin')
    children=defaultdict(list)
    for b in branches:
        if b['parent_id']:children[b['parent_id']].append(b)
    for b in branches:
        if sum(c['radius_start']**p['pipe_exponent'] for c in children[b['id']])>b['radius_end']**p['pipe_exponent']+1e-8+1e-5*b['radius_end']**p['pipe_exponent']:raise ValueError('Botanical child radius budget exceeds parent support')
    used=set();organ_parents=set()
    for organ in organs:
        if not isinstance(organ['id'],str) or len(organ['id'])!=20 or organ['id'] in seen or len(organ['position'])!=3 or len(organ['direction'])!=3 or any(not math.isfinite(v) for v in organ['position']+organ['direction']) or abs(length(organ['direction'])-1)>1e-6 or not math.isfinite(organ['age_years']) or not 0<=organ['age_years']<=1:raise ValueError('Invalid botanical organ coordinates/age/ID')
        if organ['id'] in used or organ['parent_id'] not in seen or organ['kind']!='TERMINAL_BUD' or length(sub(organ['position'],seen[organ['parent_id']]['end']))>1e-6:raise ValueError('Invalid botanical organ attachment')
        if organ.get('phyllotaxis')!='ALTERNATE' or organ['parent_id'] in organ_parents or children[organ['parent_id']]:raise ValueError('Terminal bud must attach once to a terminal segment')
        used.add(organ['id']);organ_parents.add(organ['parent_id'])
    if organ_parents!={b['id'] for b in branches if not children[b['id']]}:raise ValueError('Terminal bud inventory is incomplete')
    return True


def metrics(model):
    validate(model);branches=model['branches'];children=defaultdict(list);lookup={b['id']:b for b in branches};angles=[]
    for b in branches:
        if b['parent_id']:
            parent=lookup[b['parent_id']];children[parent['id']].append(b)
            angles.append(math.degrees(math.acos(max(-1,min(1,dot(unit(sub(b['end'],b['start'])),unit(sub(parent['end'],parent['start']))))))))
    coords=[v for b in branches for v in (b['start'],b['end'])];bounds={'min':[min(v[i] for v in coords) for i in range(3)],'max':[max(v[i] for v in coords) for i in range(3)]}
    return {'branches':len(branches),'axes':len({b['axis_id'] for b in branches}),'organs':len(model['organs']),
            'max_order':max(b['order'] for b in branches),'branch_orders':{str(i):sum(b['order']==i for b in branches) for i in sorted({b['order'] for b in branches})},
            'centerline_bounds':bounds,'height':bounds['max'][2]-bounds['min'][2],
            'width_x':bounds['max'][0]-bounds['min'][0],'width_y':bounds['max'][1]-bounds['min'][1],
            'total_branch_length':sum(length(sub(b['end'],b['start'])) for b in branches),
            'branch_angles_degrees':{'min':min(angles,default=0),'max':max(angles,default=0),'mean':sum(angles)/max(1,len(angles)),
               'histogram':[{'min':lo,'max':lo+15,'count':sum(lo<=a<lo+15 or lo==165 and a==180 for a in angles)} for lo in range(0,180,15)]},
            'woody_asymmetry':[(bounds['max'][i]+bounds['min'][i])/max(1e-9,bounds['max'][i]-bounds['min'][i]) for i in range(2)],
            'growth':model['growth'],'scope':'Centerlines and semantic buds. These are not leaf-area, projected foliage coverage, crown silhouette or branch intersection measurements.'}
