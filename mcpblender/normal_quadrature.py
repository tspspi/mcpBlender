"""Bounded positive unit-sphere quadrature for first/second normal moments."""
import math

FORMAT='mcpblender-unit-normal-quadrature-v1'


def moments(atoms):
    result=[0.]*9
    for atom in atoms:
        w=atom['weight'];x,y,z=atom['direction']
        for i,v in enumerate((x,y,z,x*x,x*y,x*z,y*y,y*z,z*z)):result[i]+=w*v
    return result


def fit(values,*,tolerance=1e-5,max_rotations=64,factor_seed=0,cancelled=lambda:None):
    if len(values)!=9 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1.001 for v in values):raise ValueError('Finite bounded normal moments required')
    if type(tolerance) not in (int,float) or not math.isfinite(tolerance) or not 1e-8<=tolerance<=1e-3:raise ValueError('Invalid quadrature tolerance')
    if type(max_rotations) is not int or not 1<=max_rotations<=128:raise ValueError('Invalid quadrature rotation budget')
    if type(factor_seed) is not int or not 0<=factor_seed<64:raise ValueError('Invalid quadrature factor seed')
    x,y,z,xx,xy,xz,yy,yz,zz=values
    original=[[1.,x,y,z],[x,xx,xy,xz],[y,xy,yy,yz],[z,xz,yz,zz]]
    if abs(xx+yy+zz-1)>tolerance:raise ValueError('Normal second-moment unit trace is outside tolerance')
    a=[r[:] for r in original];v=[[float(i==j) for j in range(4)] for i in range(4)];rotations=0
    for _ in range(max_rotations):
        cancelled();p,q=max(((i,j) for i in range(4) for j in range(i+1,4)),key=lambda ij:abs(a[ij[0]][ij[1]]))
        if abs(a[p][q])<=1e-13:break
        t0=(a[q][q]-a[p][p])/(2*a[p][q]);t=math.copysign(1.,t0)/(abs(t0)+math.hypot(1.,t0));c=1/math.sqrt(1+t*t);s=t*c;off=a[p][q]
        a[p][p]-=t*off;a[q][q]+=t*off;a[p][q]=a[q][p]=0.
        for k in range(4):
            if k not in (p,q):
                ap,aq=a[k][p],a[k][q];a[k][p]=a[p][k]=c*ap-s*aq;a[k][q]=a[q][k]=s*ap+c*aq
            vp,vq=v[k][p],v[k][q];v[k][p]=c*vp-s*vq;v[k][q]=s*vp+c*vq
        rotations+=1
    if max(abs(a[i][j]) for i in range(4) for j in range(i+1,4))>1e-11:raise ValueError('Normal quadrature eigen rotation budget exhausted')
    eigen=[a[i][i] for i in range(4)]
    if min(eigen)<-tolerance:raise ValueError('Normal moment matrix is not positive semidefinite')
    factor=[[v[i][j]*math.sqrt(max(0.,eigen[j])) for j in range(4)] for i in range(4)]
    # A congruence enforces M00=trace(Q)=1 after roundoff-only PSD projection.
    mass=sum(t*t for t in factor[0]);trace=sum(factor[i][j]**2 for i in range(1,4) for j in range(4))
    if min(mass,trace)<=0:raise ValueError('Degenerate normal moment matrix')
    for i in range(4):
        scale=math.sqrt(mass if i==0 else trace)
        factor[i]=[t/scale for t in factor[i]]
    target=[[sum(factor[i][k]*factor[j][k] for k in range(4)) for j in range(4)] for i in range(4)]
    adjustment=max(abs(target[i][j]-original[i][j]) for i in range(4) for j in range(4))
    if adjustment>tolerance:raise ValueError('Normal moment numerical adjustment exceeds tolerance')
    # Orthogonal column rotations preserve factor*factor.T. Alternative bounded
    # deterministic starting orientations yield different null-cone quadratures
    # without changing the target moments. Seed zero preserves the original fit.
    if factor_seed:
        state=factor_seed
        for p,q in ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3)):
            cancelled();state=(1664525*state+1013904223)&0xffffffff
            angle=state/4294967296*2*math.pi;c=math.cos(angle);s=math.sin(angle)
            for row in factor:
                a0,b0=row[p],row[q];row[p]=c*a0+s*b0;row[q]=-s*a0+c*b0
    # Rotate factor columns onto the null cone of diag(1,-1,-1,-1).
    # Trace zero permits a zero diagonal; each null column becomes w*[1,n]
    # with ||n||=1. Subsequent rotations exclude already fixed columns.
    free=list(range(4));cone_rotations=0;bisections=0
    def dot(i,j):return factor[0][i]*factor[0][j]-sum(factor[k][i]*factor[k][j] for k in range(1,4))
    while len(free)>1:
        cancelled();positive=max(free,key=lambda k:dot(k,k));negative=min(free,key=lambda k:dot(k,k))
        p0,q0=dot(positive,positive),dot(negative,negative)
        if max(abs(p0),abs(q0))<1e-13:break
        if p0<=0 or q0>=0:raise ValueError('Normal quadrature null-cone factorization failed')
        cross=dot(positive,negative);lo=0.;hi=math.pi/2
        for step in range(52):
            if step%8==0:cancelled()
            angle=(lo+hi)/2;c=math.cos(angle);s=math.sin(angle);value=c*c*p0+2*c*s*cross+s*s*q0
            if value>0:lo=angle
            else:hi=angle
            bisections+=1
        angle=(lo+hi)/2;c=math.cos(angle);s=math.sin(angle)
        for row in factor:
            ap,aq=row[positive],row[negative];row[positive]=c*ap+s*aq;row[negative]=-s*ap+c*aq
        free.remove(positive);cone_rotations+=1
    atoms=[]
    for j in range(4):
        w=factor[0][j]**2
        if w<=1e-12:continue
        n=[factor[i][j]/factor[0][j] for i in range(1,4)];length=math.sqrt(sum(t*t for t in n))
        if length<=0:raise ValueError('Zero quadrature direction')
        atoms.append({'weight':w,'direction':[t/length for t in n]})
    mass=sum(v['weight'] for v in atoms)
    for atom in atoms:atom['weight']/=mass
    atoms.sort(key=lambda row:(-row['weight'],row['direction']))
    residual=max(abs(u-v) for u,v in zip(moments(atoms),values))
    if residual>tolerance:raise ValueError('Normal quadrature reconstruction residual exceeds tolerance')
    return {'method':FORMAT,'tolerance':tolerance,'max_eigen_rotations':max_rotations,'factor_seed':factor_seed,'atoms':atoms,'max_component_residual':residual,'max_numerical_adjustment':adjustment,
            'clipped_eigenvalues':sum(v<0 for v in eigen),'eigen_rotations':rotations,'cone_rotations':cone_rotations,'bisection_steps':bisections,
            'scope':'Positive unit directions matching observed first/second moments within the stated numerical tolerance. No unique distribution, support hemisphere, color correlation, renderer closure or optical-equivalence guarantee.'}


def inspect_values(geometry,weight,values,threshold,max_pixels,*,cancelled=lambda:None,progress=lambda value:None):
    if type(max_pixels) is not int or not 1<=max_pixels<=4096:raise ValueError('Quadrature pixel budget must be 1..4096')
    alpha=geometry['channels']['TreeCapture.Combined.A']
    if len(values)!=9 or any(len(v)!=len(alpha) for v in [weight,*values]):raise ValueError('Quadrature channel lengths differ')
    def eligible(i):return math.isfinite(alpha[i]) and threshold<alpha[i]<=1+1e-6 and math.isfinite(weight[i]) and 1e-6<weight[i]<=1+1e-5
    count=0
    for i in range(len(alpha)):
        if i%8192==0:cancelled()
        count+=eligible(i)
    stride=max(1,math.ceil(count/max_pixels));ordinal=sampled=success=failed=clipped=rotations=bisections=0;max_error=max_adjustment=0.;max_atoms=0;examples=[];errors={}
    for i in range(len(alpha)):
        if i%8192==0:cancelled()
        if not eligible(i):continue
        selected=ordinal%stride==0;ordinal+=1
        if not selected:continue
        cancelled();sampled+=1
        if sampled%32==1:progress({'phase':'reconstructing sampled unit normal moments','completed':sampled-1,'total':min(max_pixels,count)})
        try:result=fit([v[i]/weight[i] for v in values],cancelled=cancelled)
        except ValueError as exc:
            failed+=1;message=str(exc);errors[message]=errors.get(message,0)+1;continue
        success+=1;max_error=max(max_error,result['max_component_residual']);max_adjustment=max(max_adjustment,result['max_numerical_adjustment']);max_atoms=max(max_atoms,len(result['atoms']));clipped+=result['clipped_eigenvalues']>0;rotations+=result['eigen_rotations'];bisections+=result['bisection_steps']
        if len(examples)<3:examples.append({'pixel_index':i,**result})
    return {'method':FORMAT,'tolerance':1e-5,'requested_max_pixels':max_pixels,'candidate_pixels':count,'sample_stride':stride,'sampled_pixels':sampled,'successful_pixels':success,'failed_pixels':failed,
            'failure_reasons':errors,'max_atoms':max_atoms,'max_component_residual':max_error if success else None,'max_numerical_adjustment':max_adjustment if success else None,
            'eigenvalue_clipping_pixels':clipped,'eigen_rotations':rotations,'bisection_steps':bisections,'examples':examples,
            'scope':'Deterministic every-stride covered-pixel sample, bounded by requested_max_pixels; weights condition on the surface AOV. Numerical roundoff adjustment is reported; source buffers are unchanged. This is moment reconstruction, not an all-pixel, hemisphere-support, color-correlation, renderer-closure or optical-quality qualification.'}
