"""Versioned optional unit normal-input moments; no fitted shader distribution."""
import math
from . import botany

FORMAT='mcpblender-native-normal-moments-v1'
KEYS=('X','Y','Z','XX','XY','XZ','YY','YZ','ZZ')
FIELDS=[{'key':k,'name':'MCP_Normal'+k,'type':'VALUE'} for k in KEYS]


def channels():return ['TreeCapture.'+f['name']+'.X' for f in FIELDS]


def validate(value,materials):
    if not isinstance(value,dict) or value.get('format')!=FORMAT or value.get('fields')!=FIELDS or value.get('coordinate_space')!='WORLD' or value.get('normalization') not in {'PER_HIT_UNIT_INPUT','PER_HIT_SAFE_UNIT_INPUT'}:raise ValueError('Invalid normal-moment contract')
    if value.get('moments_sha256')!=botany.digest({k:v for k,v in value.items() if k!='moments_sha256'}):raise ValueError('Normal-moment contract digest changed')
    expected_fallback='GEOMETRY_NORMAL' if value['normalization']=='PER_HIT_SAFE_UNIT_INPUT' else None
    if value.get('zero_length_fallback')!=expected_fallback:raise ValueError('Normal-moment zero-length fallback changed')
    rows=value.get('materials',[])
    if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows):raise ValueError('Invalid normal-moment material rows')
    if [(r.get('material'),r.get('id')) for r in rows]!=[(r['material'],r['id']) for r in materials]:raise ValueError('Normal-moment material inventory changed')
    def binding(b):
        if not isinstance(b,dict) or set(b)!={'node','socket','source','default'} or not all(isinstance(b[k],str) and b[k] for k in ('node','socket')):raise ValueError('Invalid normal-input binding')
        if not isinstance(b['default'],list) or len(b['default'])!=3 or any(type(v) not in (int,float) or not math.isfinite(v) for v in b['default']):raise ValueError('Invalid normal-input default')
        src=b['source']
        if src is not None and (not isinstance(src,dict) or set(src)!={'node','socket'} or not all(isinstance(v,str) and v for v in src.values())):raise ValueError('Invalid normal-input source')
    for row,mat in zip(rows,materials):
        binding(row['normal']);thin=row.get('thin_normal')
        if mat['model']=='MANAGED_THIN_FOLIAGE':
            binding(thin)
            if thin['source']!=row['normal']['source']:raise ValueError('Managed normal moments require shared closure normal inputs')
        elif thin is not None:raise ValueError('Unexpected thin normal binding')
    return value


def measure(geometry,weight,values,threshold,*,cancelled=lambda:None):
    alpha=geometry['channels']['TreeCapture.Combined.A'];normal=[geometry['channels']['TreeCapture.Normal.'+a] for a in 'XYZ']
    if len(values)!=9 or any(len(v)!=len(alpha) for v in [weight,*values,*normal]):raise ValueError('Normal-moment channel lengths differ')
    counts={k:0 for k in ('covered_pixels','unavailable_pixels','nonfinite_pixels','unit_trace_violations','normal_pass_disagreements','covariance_psd_violations','mean_length_violations','invalid_alpha')};max_error=0.
    accum={k:[0,math.inf,-math.inf,0.] for k in ('unit_trace','mean_length','covariance_trace')}
    for i,a in enumerate(alpha):
        if i%8192==0:cancelled()
        if not math.isfinite(a) or not -1e-6<=a<=1+1e-6:counts['invalid_alpha']+=1;continue
        if a<=threshold:continue
        counts['covered_pixels']+=1;w=weight[i]
        if not math.isfinite(w) or not 1e-6<w<=1+1e-5:counts['unavailable_pixels']+=1;continue
        data=[v[i]/w for v in values];n=[v[i]/w for v in normal]
        if not all(math.isfinite(v) for v in data+n):counts['nonfinite_pixels']+=1;continue
        x,y,z,xx,xy,xz,yy,yz,zz=data;trace=xx+yy+zz;length2=x*x+y*y+z*z
        counts['mean_length_violations']+=length2>(1+1e-4)**2
        error=max(abs(v-u) for v,u in zip((x,y,z),n));max_error=max(max_error,error);counts['normal_pass_disagreements']+=error>1e-4;counts['unit_trace_violations']+=abs(trace-1)>1e-4
        a0,b,c,d,e,f=xx-x*x,xy-x*y,xz-x*z,yy-y*y,yz-y*z,zz-z*z
        det=a0*d*f+2*b*c*e-a0*e*e-d*c*c-f*b*b
        counts['covariance_psd_violations']+=min(a0,d,f,a0*d-b*b,a0*f-c*c,d*f-e*e,det)<-1e-4
        for key,value in (('unit_trace',trace),('mean_length',math.sqrt(length2)),('covariance_trace',trace-length2)):
            r=accum[key];r[0]+=1;r[1]=min(r[1],value);r[2]=max(r[2],value);r[3]+=value
    stats={k:{'count':r[0],'min':r[1] if r[0] else None,'max':r[2] if r[0] else None,'mean':r[3]/r[0] if r[0] else None} for k,r in accum.items()}
    return {'method':FORMAT,**counts,'input_moments_valid':stats['unit_trace']['count']>0 and not any(v for k,v in counts.items() if k not in {'covered_pixels','normal_pass_disagreements'}),
            'normal_pass_first_moment_agrees':stats['unit_trace']['count']==counts['covered_pixels']>0 and counts['invalid_alpha']==0 and counts['normal_pass_disagreements']==0,
            'normal_pass_max_component_error':max_error,'statistics':stats,
            'scope':'Coverage-conditioned first and second unit normal-input moments. Validate unit trace/covariance separately from first-moment agreement with native Normal. Renderer closure normals can differ from the shared input, including specular correction; agreement of means does not prove an equivalent distribution. No clamping, fitted distribution, complete BSDF or optical equivalence.'}


def inspect_view(path,sha,geometry,threshold,*,cancelled=lambda:None,progress=lambda value:None,quadrature_pixels=0):
    from . import exr_scanline
    names=['TreeCapture.MCP_SurfaceWeight.X',*channels()];data=exr_scanline.decode(path,names,expected_sha256=sha,cancelled=cancelled,progress=progress)['channels']
    result=measure(geometry,data[names[0]],[data[n] for n in names[1:]],threshold,cancelled=cancelled)
    if quadrature_pixels:
        from . import normal_quadrature
        result['quadrature']=normal_quadrature.inspect_values(geometry,data[names[0]],[data[n] for n in names[1:]],threshold,quadrature_pixels,cancelled=cancelled,progress=progress)
    return result
