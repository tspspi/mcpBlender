"""Portable oak-like leaf templates and deterministic shoot/leaf attachment layouts."""
import math
from . import botany as b
FORMAT='mcpblender-foliage-layout-v1'
GENERATOR='oak-leaf-shoots-1'
LEAF={'length':.12,'width':.065,'petiole':.006,'lobes':5,'lobe_depth':.28,'curl':.012,'fold':.004,'vein_ridge':.0007,'rows':24}
DEFAULTS={'seed':1,'shoots_per_bud':6,'attachment_nodes':10,'arrangement':'ALTERNATE','shoot_length':.65,
 'spread':.7,'inclination':.25,'size_variation':.2,'variants':3,'max_leaves':100000,'max_expanded_triangles':8000000,'leaf':LEAF}


def cross(a,c):return (a[1]*c[2]-a[2]*c[1],a[2]*c[0]-a[0]*c[2],a[0]*c[1]-a[1]*c[0])
def basis(tangent):
    tangent=b.unit(tangent);reference=(0,0,1) if abs(tangent[2])<.9 else (1,0,0)
    x=b.unit(cross(reference,tangent));return x,b.unit(cross(tangent,x))
def leaf_recipe(value):
    p=LEAF|value
    limits={'length':(.03,.3),'width':(.01,.2),'petiole':(.001,.03),'lobes':(3,7),'lobe_depth':(0,.7),
            'curl':(-.05,.05),'fold':(-.02,.02),'vein_ridge':(0,.003),'rows':(12,40)}
    if set(value)-set(LEAF):raise ValueError('Unknown leaf shape fields')
    for k,(lo,hi) in limits.items():
        if isinstance(p[k],bool) or not isinstance(p[k],(int,float)) or not math.isfinite(p[k]) or not lo<=p[k]<=hi:raise ValueError('Invalid leaf parameter: '+k)
        if k in {'lobes','rows'}:
            if type(p[k])!=int:raise ValueError('Leaf counts must be integers')
        else:p[k]=float(p[k])
    p['rows']=max(p['rows'],p['lobes']*4)
    if p['width']>p['length']*1.3:raise ValueError('Leaf width is too large for this blade profile')
    return p

def recipe(value):
    p=DEFAULTS|value;p['leaf']=leaf_recipe(p['leaf'])
    if set(value)-set(DEFAULTS):raise ValueError('Unknown foliage layout fields')
    limits={'seed':(0,2147483647),'shoots_per_bud':(1,12),'attachment_nodes':(2,24),'shoot_length':(.1,1.5),
      'spread':(0,1.5),'inclination':(-1,1),'size_variation':(0,.5),'variants':(1,4),'max_leaves':(1,100000),'max_expanded_triangles':(1000,30000000)}
    counts={'seed','shoots_per_bud','attachment_nodes','variants','max_leaves','max_expanded_triangles'}
    for key,(lo,hi) in limits.items():
        if isinstance(p[key],bool) or not isinstance(p[key],(int,float)) or not math.isfinite(p[key]) or not lo<=p[key]<=hi or key in counts and type(p[key])!=int:raise ValueError('Invalid foliage parameter: '+key)
        if key not in counts:p[key]=float(p[key])
    if p['arrangement'] not in {'ALTERNATE','OPPOSITE','WHORLED'}:raise ValueError('Unsupported leaf attachment pattern')
    return p

def leaf_mesh(value):
    p=leaf_recipe(value);vertices=[(0,p['petiole'],0)];uv=[(.5,0)];faces=[];parts=[];rings=[]
    for i in range(1,p['rows']):
        t=i/p['rows'];envelope=math.sin(math.pi*t)**.65*(.65+.35*t)
        lobes=1-p['lobe_depth']*(.5+.5*math.cos(2*math.pi*p['lobes']*t))
        width=p['width']*.5*envelope*lobes*(1+.2*math.exp(-((t-.09)/.06)**2));ring=[]
        for side in (-1,-.2,0,.2,1):
            z=p['curl']*t*t+p['fold']*abs(side)*math.sin(math.pi*t)+p['vein_ridge']*(1-abs(side))**6*math.sin(math.pi*t)
            ring.append(len(vertices));vertices.append((width*side,p['petiole']+p['length']*t,z));uv.append(((side+1)/2,t))
        rings.append(ring)
    tip=len(vertices);vertices.append((0,p['petiole']+p['length'],p['curl']));uv.append((.5,1))
    for k in range(4):faces.append((0,rings[0][k+1],rings[0][k]));parts.append(0)
    for a,c in zip(rings,rings[1:]):
        for k in range(4):faces.append((a[k],a[k+1],c[k+1],c[k]));parts.append(0)
    for k in range(4):faces.append((rings[-1][k],rings[-1][k+1],tip));parts.append(0)
    # Small petiole is a four-sided tapered tube in the same prototype.
    stem=[]
    for y,r in ((0,.0009),(p['petiole'],.0006)):
        ring=[]
        for i in range(4):
            ring.append(len(vertices));vertices.append((r*math.cos(i*math.pi/2),y,r*math.sin(i*math.pi/2)));uv.append((i/3,y/p['petiole']))
        stem.append(ring)
    for i in range(4):faces.append((stem[0][i],stem[1][i],stem[1][(i+1)%4],stem[0][(i+1)%4]));parts.append(1)
    faces.extend((tuple(stem[0]),tuple(reversed(stem[1]))));parts.extend((1,1))
    triangles=sum(len(f)-2 for f in faces)
    area=0.
    for f,part in zip(faces,parts):
        if part:continue
        for i in range(1,len(f)-1):area+=b.length(cross(b.sub(vertices[f[i]],vertices[f[0]]),b.sub(vertices[f[i+1]],vertices[f[0]])))/2
    return {'recipe':p,'vertices':[b.vector(v) for v in vertices],'uv':uv,'faces':faces,'parts':parts,'triangles':triangles,'blade_area':area,
            'scope':'Open curved lobed blade with raised midrib and petiole; no cutout card, detailed secondary vein texture, watertight leaf thickness or biological calibration.'}

def variant_shape(p,index):
    return p['leaf']|{'curl':max(-.05,min(.05,p['leaf']['curl']*(.8+index*.2)))}


def euler(columns):
    x,y,z=columns;pitch=math.asin(max(-1,min(1,-x[2])))
    if abs(math.cos(pitch))>1e-7:return (math.atan2(y[2],z[2]),pitch,math.atan2(x[1],x[0]))
    return (0,pitch,math.atan2(-y[0],y[1]))

def generate(model,value,progress=lambda v:None,cancelled=lambda:None):
    b.validate(model);p=recipe(value);leaf=leaf_mesh(p['leaf']);per_node={'ALTERNATE':1,'OPPOSITE':2,'WHORLED':3}[p['arrangement']]
    count=len(model['organs'])*p['shoots_per_bud']*p['attachment_nodes']*per_node
    if count>p['max_leaves'] or count*leaf['triangles']>p['max_expanded_triangles']:raise ValueError('Foliage leaf/expanded-triangle budget exceeded; reduce density or leaf rows')
    areas=[leaf_mesh(variant_shape(p,i))['blade_area'] for i in range(p['variants'])]
    leaves=[];shoots=[];lookup={v['id']:i for i,v in enumerate(model['branches'])};seed=p['seed']
    for bi,bud in enumerate(model['organs']):
        cancelled();tangent=bud['direction'];bx,bz=basis(tangent)
        for si in range(p['shoots_per_bud']):
            key=bud['id']+':shoot:'+str(si);phi=si*2.399963229728653+b.rnd(seed,key)*.6
            radial=b.add(b.mul(bx,math.cos(phi)),b.mul(bz,math.sin(phi)))
            direction=b.unit(b.add(b.mul(tangent,.65),b.add(b.mul(radial,p['spread']),(0,0,.25))))
            extent=p['shoot_length']*(.8+.4*b.rnd(seed,key,1));end=b.add(bud['position'],b.mul(direction,extent))
            shoot_index=len(shoots);shoots.append({'id':b.uid(seed,GENERATOR+key),'parent_branch_id':bud['parent_id'],'bud_id':bud['id'],'start':bud['position'],'end':b.vector(end)})
            sx,sz=basis(direction)
            for ni in range(p['attachment_nodes']):
                t=.12+.86*(ni+.5)/p['attachment_nodes'];position=b.add(bud['position'],b.mul(direction,extent*t))
                base_phi=(ni*math.pi if p['arrangement']=='ALTERNATE' else ni*.35)+phi
                for pi in range(per_node):
                    angle=base_phi+pi*2*math.pi/per_node;radial=b.add(b.mul(sx,math.cos(angle)),b.mul(sz,math.sin(angle)))
                    forward=b.unit(b.add(radial,b.add(b.mul(direction,.15),(0,0,p['inclination']))))
                    normal=b.sub((0,0,1),b.mul(forward,forward[2]))
                    if b.length(normal)<1e-6:normal=basis(forward)[1]
                    # Seeded surface roll makes each thin surface visible across views.
                    normal=b.unit(b.add(normal,b.mul(direction,(b.rnd(seed,key+':roll',ni*3+pi)-.5)*.7)))
                    x=b.unit(cross(forward,normal));normal=b.unit(cross(x,forward))
                    leaf_key=key+f':leaf:{ni}:{pi}';scale=1+p['size_variation']*(2*b.rnd(seed,leaf_key)-1)
                    leaves.append({'id':b.uid(seed,GENERATOR+leaf_key),'parent_branch_index':lookup[bud['parent_id']],
                        'shoot_index':shoot_index,'node':ni,'position':b.vector(position),'rotation':b.vector(euler((x,forward,normal))),
                        'scale':round(scale,8),'variant':min(p['variants']-1,int(b.rnd(seed,leaf_key,1)*p['variants'])),
                        'phase':round(2*math.pi*b.rnd(seed,leaf_key,2),8),'flutter':round(.5+.5*b.rnd(seed,leaf_key,3),8)})
        if bi%16==0:progress({'phase':'planning botanical foliage','buds':bi,'total_buds':len(model['organs']),'leaves':len(leaves)})
    return {'format':FORMAT,'generator':GENERATOR,'source_model_sha256':b.digest(model),'recipe':p,'leaves':leaves,'shoots':shoots,
            'metrics':{'leaves':len(leaves),'shoots':len(shoots),'prototypes':p['variants'],'prototype_triangles':leaf['triangles'],
                       'expanded_triangles':count*leaf['triangles'],'blade_area_sum':sum(areas[v['variant']]*v['scale']**2 for v in leaves),
                       'scope':'Instanced leaf counts, summed blade area and expanded geometry estimate; not projected coverage, overdraw, draw calls or GPU performance.'}}

def compact(layout):
    return {key:layout[key] for key in ('format','generator','source_model_sha256','recipe','metrics')}|{'attachments_sha256':b.digest(layout['leaves']),'shoots_sha256':b.digest(layout['shoots'])}
