"""Optional raw face-normal capture, distinct from shading and closure normals."""
import math
from . import botany

FORMAT='mcpblender-native-geometric-normals-v1'
FIELDS=[{'key':'geometric_normal','name':'MCP_GeometricNormal','type':'COLOR'}]


def channels():return ['TreeCapture.MCP_GeometricNormal.'+a for a in 'RGB']


def contract(materials):
    value={'format':FORMAT,'fields':FIELDS,'coordinate_space':'WORLD',
           'source':'ShaderNodeNewGeometry.TrueNormal','orientation':'RENDERER_FACE_FORWARD',
           'weighting':'RAW_FILTERED_SURFACE_AOV',
           'materials':[{'material':m['material'],'id':m['id']} for m in materials]}
    return value|{'normals_sha256':botany.digest(value)}


def validate(value,materials):
    if not isinstance(value,dict) or value!=contract(materials):raise ValueError('Geometric-normal contract changed')
    return value


def measure(geometry,weight,values,threshold,*,cancelled=lambda:None):
    alpha=geometry['channels']['TreeCapture.Combined.A']
    normal=[geometry['channels']['TreeCapture.Normal.'+a] for a in 'XYZ']
    if len(values)!=3 or any(len(v)!=len(alpha) for v in [weight,*values,*normal]):raise ValueError('Geometric-normal channel lengths differ')
    counts={k:0 for k in ('covered_pixels','invalid_alpha','unavailable_pixels','nonfinite_pixels',
                         'conditional_length_over_one','zero_geometric_normals','zero_shading_normals','different_direction_pixels')}
    accum={k:[0,math.inf,-math.inf,0.] for k in ('conditional_length','shading_angle_degrees')}
    for i,a in enumerate(alpha):
        if i%8192==0:cancelled()
        if not math.isfinite(a) or not -1e-6<=a<=1+1e-6:counts['invalid_alpha']+=1;continue
        if a<=threshold:continue
        counts['covered_pixels']+=1;w=weight[i]
        if not math.isfinite(w) or not 1e-6<w<=1+1e-5:counts['unavailable_pixels']+=1;continue
        g=[v[i]/w for v in values];n=[v[i]/w for v in normal]
        if not all(math.isfinite(v) for v in g+n):counts['nonfinite_pixels']+=1;continue
        length=math.sqrt(sum(v*v for v in g));nl=math.sqrt(sum(v*v for v in n))
        counts['conditional_length_over_one']+=length>1+1e-4
        observations={'conditional_length':length}
        if length<=1e-6:counts['zero_geometric_normals']+=1
        elif nl<=1e-6:counts['zero_shading_normals']+=1
        else:
            # Bound only the computed cosine for floating-point acos roundoff;
            # captured vectors and above-unit violations remain unmodified.
            angle=math.degrees(math.acos(max(-1.,min(1.,sum(x*y for x,y in zip(g,n))/(length*nl)))))
            counts['different_direction_pixels']+=angle>.01
            observations['shading_angle_degrees']=angle
        for key,value in observations.items():
            row=accum[key];row[0]+=1;row[1]=min(row[1],value);row[2]=max(row[2],value);row[3]+=value
    stats={k:{'count':r[0],'min':r[1] if r[0] else None,'max':r[2] if r[0] else None,'mean':r[3]/r[0] if r[0] else None} for k,r in accum.items()}
    return {'method':FORMAT,**counts,'statistics':stats,
            'scope':'World-space renderer-face-forward geometric normal, filtered as a raw COLOR AOV. Divide by the constant-one surface weight, never beauty alpha. Shading angles compare directions of filtered means, not matched per-hit samples. Smooth shading, bump and closure correction can differ from face normals. No recovered surface correspondence or optical equivalence.'}


def inspect_view(path,sha,geometry,threshold,*,cancelled=lambda:None,progress=lambda value:None):
    from . import exr_scanline
    names=['TreeCapture.MCP_SurfaceWeight.X',*channels()]
    data=exr_scanline.decode(path,names,expected_sha256=sha,cancelled=cancelled,progress=progress)['channels']
    return measure(geometry,data[names[0]],[data[n] for n in names[1:]],threshold,cancelled=cancelled)
