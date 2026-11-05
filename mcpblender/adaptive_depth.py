"""Coverage-weighted normal alignment with deterministic bounded refinement.

Normals are observations used to estimate patch orientation, not replacements for
capture data. The tolerance is an equivalent angle from weighted mean cosine,
not a maximum pixel angle. A triangle budget can stop refinement above tolerance.
"""
from array import array
import heapq
import math
from . import botany,capture_data,depth_tiles
FORMAT='mcpblender-adaptive-depth-patches-v1'


def geometry(decoded,metadata,view,p,*,cancelled=lambda:None,progress=lambda v:None):
    w,h,_,axes,_,_,_,_,near,far=depth_tiles.frame(decoded,metadata,view,p)
    ch=decoded['channels'];alpha=ch['TreeCapture.Combined.A'];depth=ch['TreeCapture.Depth.Z'];raw=[ch['TreeCapture.Normal.'+a] for a in 'XYZ']
    if any(len(v)!=w*h for v in (alpha,depth,*raw)):raise ValueError('Adaptive depth channel length mismatch')
    normals=array('f',[0.])*(w*h*3);work=0;backward=0
    def charge(n=1):
        nonlocal work
        work+=n
        if work>p['max_refinement_work']:raise ValueError('Adaptive depth refinement work budget exceeded')
    for i,a in enumerate(alpha):
        charge()
        if i%4096==0:cancelled();progress({'phase':'reading adaptive patch normals','completed':i,'total':w*h})
        if not math.isfinite(a) or not -1e-6<=a<=1+1e-6:raise ValueError('Invalid depth patch coverage')
        if a>=1-1e-6 and not (math.isfinite(depth[i]) and near<=depth[i]<=far):raise ValueError('Opaque capture pixels lack measured centre depth; edge estimation cannot repair them')
        if a<=p['alpha_threshold']:continue
        n=[v[i] for v in raw];length=math.sqrt(sum(v*v for v in n))
        if not math.isfinite(length) or length<1e-8:raise ValueError('Covered native normal is nonfinite or zero; no inferred replacement')
        camera=[capture_data.dot(n,axis)/length for axis in axes];normals[i*3:i*3+3]=array('f',camera);backward+=camera[2]<0
    tolerance=1-math.cos(math.radians(p['normal_tolerance_degrees']))
    def fit(rect):
        x,y,r,b=rect;weight=0.;moment=[0.,0.,0.]
        for yy in range(y,b):
            for xx in range(x,r):
                charge();i=yy*w+xx;a=alpha[i]
                if a<=p['alpha_threshold']:continue
                weight+=a
                for j in range(3):moment[j]+=a*normals[3*i+j]
        if not weight:return None
        unsupported=moment[2]<=1e-8*weight
        slope=(0.,0.) if unsupported else (moment[0]/moment[2],moment[1]/moment[2]);size=math.hypot(*slope);limited=size>p['max_slope']
        if limited:slope=tuple(v*p['max_slope']/size for v in slope)
        normal=[*slope,1.];size=math.sqrt(sum(v*v for v in normal));normal=[v/size for v in normal]
        loss=max(0.,weight-capture_data.dot(moment,normal))
        return {'rect':rect,'weight':weight,'moment':moment,'slope':slope,'loss':loss,'unsupported':unsupported,'slope_limited':limited}
    step=p['tile_pixels'];leaves={};heap=[];candidate_count=0
    def candidate(cell):
        nonlocal candidate_count
        if cell['loss']<=cell['weight']*tolerance:return
        x,y,r,b=cell['rect']
        if r-x==1 and b-y==1:return
        xs=[(x,r)] if r-x==1 else [(x,(x+r)//2),((x+r)//2,r)]
        ys=[(y,b)] if b-y==1 else [(y,(y+b)//2),((y+b)//2,b)]
        children=[fit((a,c,d,e)) for c,e in ys for a,d in xs];children=[c for c in children if c is not None]
        extra=len(children)-1;gain=cell['loss']-sum(c['loss'] for c in children)
        if gain<=1e-12*cell['weight']:return
        # A one-child split costs no triangles; deterministic score and rectangle
        # ordering make budget decisions reproducible across repeated plans.
        score=math.inf if extra==0 else gain/extra
        heapq.heappush(heap,(-score,cell['rect'],children));candidate_count+=1
    for y in range(0,h,step):
        cancelled()
        for x in range(0,w,step):
            cell=fit((x,y,min(w,x+step),min(h,y+step)))
            if cell is not None:
                leaves[cell['rect']]=cell
                if len(leaves)*2>p['max_triangles']:raise ValueError('Depth patch triangle budget exceeded')
    if not leaves:raise ValueError('No active depth patches')
    if len(leaves)*2>p['max_triangles']:raise ValueError('Depth patch triangle budget exceeded')
    initial_patches=len(leaves);initial_cells={(r[0]//step,r[1]//step):c for r,c in leaves.items()}
    for cell in list(leaves.values()):cancelled();candidate(cell)
    splits=0;blocked=0
    while heap:
        cancelled();_,rect,children=heapq.heappop(heap)
        if rect not in leaves:continue
        if 2*(len(leaves)+len(children)-1)>p['max_triangles']:blocked+=1;continue
        del leaves[rect]
        for cell in children:leaves[cell['rect']]=cell
        splits+=1
        if splits%64==0:progress({'phase':'refining normal-aligned depth patches','splits':splits,'patches':len(leaves),'triangle_budget':p['max_triangles'],'refinement_work':work})
        for cell in children:candidate(cell)
    rectangles=sorted(leaves,key=lambda r:(r[1],r[0],r[3],r[2]));slopes={r:leaves[r]['slope'] for r in rectangles}
    result=depth_tiles._geometry(decoded,metadata,view,p,rectangles=rectangles,slopes=slopes,cancelled=cancelled,progress=progress)
    loss=weight=represented=initial_loss=flat_loss=0.;unmet=unoriented=limited=clip_limited=bounds_limited=0
    for index,record in enumerate(result['patch_records']):
        if index%1024==0:cancelled()
        rect=tuple(record['pixel_rect']);cell=leaves[rect];normal=[*record['slope_camera'],1.];length=math.sqrt(sum(v*v for v in normal));normal=[v/length for v in normal]
        original=initial_cells[(rect[0]//step,rect[1]//step)];coarse=[*original['slope'],1.];size=math.sqrt(sum(v*v for v in coarse));coarse=[v/size for v in coarse]
        initial_loss+=max(0.,cell['weight']-capture_data.dot(cell['moment'],coarse));flat_loss+=max(0.,cell['weight']-cell['moment'][2])
        value=max(0.,cell['weight']-capture_data.dot(cell['moment'],normal));loss+=value;weight+=cell['weight'];unmet+=value>cell['weight']*tolerance;unoriented+=cell['unsupported'];limited+=cell['slope_limited'];clip_limited+=record['clip_limited'];bounds_limited+=record['source_bounds_limited']
        x,y,r,b=rect;represented+=sum(alpha[yy*w+xx] for yy in range(y,b) for xx in range(x,r))
    def angle(value,total):return math.degrees(math.acos(max(-1.,min(1.,1-value/total)))) if total else None
    report=result['report'];report.update(format=FORMAT,depth_anchor='WITNESS_PIXEL_CENTRE',initial_patches=initial_patches,refinement_splits=splits,refinement_work=work,candidates=candidate_count,budget_blocked_candidates=blocked,
        backward_normal_pixels=backward,unoriented_cells=unoriented,slope_limited_cells=limited,clip_limited_cells=clip_limited,source_bounds_limited_cells=bounds_limited,normal_tolerance_unmet_cells=unmet,
        flat_equivalent_normal_error_degrees=angle(flat_loss,weight),initial_equivalent_normal_error_degrees=angle(initial_loss,weight),equivalent_normal_error_degrees=angle(loss,weight),
        input_alpha_mass=sum(alpha),represented_input_alpha_mass=represented,omitted_input_alpha_mass=max(0.,sum(alpha)-represented),
        scope='Independent normal-aligned directional patches with deterministic coverage-weighted mean-cosine refinement. Median centre-depth anchors and explicit bounded partial-edge estimates; slopes and camera clipping limited. Budget/tolerance residuals reported. No depth bridges, native surface recovery, hidden layers, optical/shadow/wind/angular guarantee.')
    report['geometry_sha256']=botany.digest({k:v for k,v in report.items() if k!='geometry_sha256'}|{'patch_records':result['patch_records']})
    return result
