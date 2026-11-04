"""Bounded directional depth patches and packed native input data, without bpy.

A directional approximation, not closed geometry or a recovered native BSDF.
Pixel rows are top-down; textures returned here retain that order. Geometry never
joins adjacent patches across depth jumps. Edge estimates have explicit policy,
work limits and counters, separate from measured centre-depth hits.
"""
from array import array
import hashlib
import math
import sys
from . import capture_data,botany

FORMAT='mcpblender-depth-patches-v1'
MAPS=[('base_coverage',('base_color.R','base_color.G','base_color.B','coverage')),
      ('normal_roughness',('normal.X','normal.Y','normal.Z','roughness')),
      ('emission',('emission_color.R','emission_color.G','emission_color.B','emission_strength')),
      ('thin',('thin_color.R','thin_color.G','thin_color.B','thin_weight')),
      ('surface',('metallic','ior','transmission_weight','alpha')),
      ('witness',('thin_mode','cull_weight','material_id','surface_weight'))]
DEFAULTS={'tile_pixels':4,'alpha_threshold':.001,'edge_depth_policy':'NEAREST','edge_radius_pixels':16,
          'max_triangles':32768,'max_pixels':1048576,'max_texture_bytes':256*1024**2,'max_search_work':2000000}


def floats_sha(values):
    if sys.byteorder=='little':return hashlib.sha256(values.tobytes()).hexdigest()
    copy=array(values.typecode,values);copy.byteswap();return hashlib.sha256(copy.tobytes()).hexdigest()


def options(values):
    p=DEFAULTS|values
    if set(p)!=set(DEFAULTS):raise ValueError('Unknown depth patch option')
    for key,low,high in [('tile_pixels',1,64),('edge_radius_pixels',0,64),('max_triangles',2,131072),('max_pixels',1024,1048576),('max_texture_bytes',1024,512*1024**2),('max_search_work',1,8000000)]:
        if type(p[key]) is not int or not low<=p[key]<=high:raise ValueError('Invalid depth patch option: '+key)
    if p['tile_pixels'] not in (1,2,4,8,16,32,64) or p['edge_depth_policy'] not in {'NEAREST','OMIT','REFUSE'}:raise ValueError('Invalid depth patch tile/edge policy')
    if type(p['alpha_threshold']) not in (int,float) or not math.isfinite(p['alpha_threshold']) or not 0<p['alpha_threshold']<1:raise ValueError('Invalid depth patch alpha threshold')
    return p


def frame(decoded,metadata,view,p):
    w,h=decoded['width'],decoded['height']
    if type(w) is not int or type(h) is not int or w!=h or not 1<=w<=2048 or w*h>p['max_pixels'] or tuple(decoded['data_window'])!=(0,0,w-1,h-1):raise ValueError('Depth patches require bounded square full-frame pixels')
    camera,axes,_=capture_data.pose(view['matrix_world'],unit=True)
    root,root_axes,squares=capture_data.pose(metadata['source_root_matrix_world'])
    unit=metadata['scene_unit_scale'];span=view['ortho_scale'];near=view['clip_start'];far=view['clip_end']
    if not all(math.isfinite(v) for v in (unit,span,near,far)) or unit<=0 or span<=0 or not 0<near<far:raise ValueError('Invalid depth patch units/camera clipping')
    return w,h,camera,axes,root,root_axes,squares,span,near,far


def geometry(decoded,metadata,view,values,*,cancelled=lambda:None,progress=lambda v:None):
    p=options(values);w,h,camera,axes,root,root_axes,squares,span,near,far=frame(decoded,metadata,view,p)
    ch=decoded['channels'];alpha=ch['TreeCapture.Combined.A'];depth=ch['TreeCapture.Depth.Z']
    if len(alpha)!=w*h or len(depth)!=w*h:raise ValueError('Depth patch channel length mismatch')
    vertices=array('f');uvs=array('f');faces=[];records=[];search_work=estimated=omitted=0;max_distance=0.;max_spread=0.;opaque_missing=0
    low=[math.inf]*3;high=[-math.inf]*3
    def hit(i):return math.isfinite(depth[i]) and near<=depth[i]<=far
    for i,a in enumerate(alpha):
        if i%8192==0:cancelled()
        if not math.isfinite(a) or not -1e-6<=a<=1+1e-6:raise ValueError('Invalid depth patch coverage')
        opaque_missing+=a>=1-1e-6 and not hit(i)
    if opaque_missing:raise ValueError('Opaque capture pixels lack measured centre depth; edge estimation cannot repair them')
    step=p['tile_pixels']
    for y in range(0,h,step):
        cancelled();progress({'phase':'reconstructing directional depth patches','completed':y,'total':h})
        for x in range(0,w,step):
            right=min(w,x+step);bottom=min(h,y+step);pixels=[yy*w+xx for yy in range(y,bottom) for xx in range(x,right)]
            active=[i for i in pixels if alpha[i]>p['alpha_threshold']]
            if not active:continue
            hits=[i for i in active if hit(i)];is_estimate=not hits;distance=0.
            if not hits:
                if p['edge_depth_policy']=='REFUSE':raise ValueError('Partial-coverage tile lacks centre depth; choose an explicit edge policy')
                if p['edge_depth_policy']=='OMIT':omitted+=1;continue
                cx=(x+right-1)/2;cy=(y+bottom-1)/2;radius=p['edge_radius_pixels'];nearest=None
                for yy in range(max(0,math.ceil(cy-radius)),min(h,math.floor(cy+radius)+1)):
                    cancelled()
                    for xx in range(max(0,math.ceil(cx-radius)),min(w,math.floor(cx+radius)+1)):
                        search_work+=1
                        if search_work>p['max_search_work']:raise ValueError('Depth patch edge search work budget exceeded')
                        d=(xx-cx)**2+(yy-cy)**2;i=yy*w+xx
                        if d<=radius*radius and alpha[i]>p['alpha_threshold'] and hit(i) and (nearest is None or (d,i)<nearest):nearest=(d,i)
                if nearest is None:raise ValueError('No measured depth witness inside edge radius; increase radius or explicitly omit tiles')
                distance=math.sqrt(nearest[0]);hits=[nearest[1]];estimated+=1;max_distance=max(max_distance,distance)
            selected=sorted(hits,key=lambda i:(depth[i],i));witness=selected[len(selected)//2];z=depth[witness];spread=depth[selected[-1]]-depth[selected[0]];max_spread=max(max_spread,spread)
            if 2*(len(faces)+1)>p['max_triangles']:raise ValueError('Depth patch triangle budget exceeded')
            base=len(vertices)//3
            for a,b in ((x,bottom),(right,bottom),(right,y),(x,y)):
                u=(a/w-.5)*span;v=(.5-b/h)*span
                world=[camera[k]+axes[0][k]*u+axes[1][k]*v-axes[2][k]*z for k in range(3)]
                local=[capture_data.dot([world[k]-root[k] for k in range(3)],root_axes[j])/squares[j] for j in range(3)]
                if any(not math.isfinite(v) or abs(v)>1e20 for v in local):raise ValueError('Depth patch coordinates exceed finite native range')
                vertices.extend(local);uvs.extend((a/w,1-b/h))
                for j in range(3):low[j]=min(low[j],local[j]);high[j]=max(high[j],local[j])
            faces.append((base,base+1,base+2,base+3));records.append({'pixel_rect':[x,y,right,bottom],'depth_scene_units':z,'witness_pixel':[witness%w,witness//w],'estimated':is_estimate,'witness_distance_pixels':distance,'measured_depth_spread_scene_units':spread})
    if not faces:raise ValueError('No active depth patches')
    report={'format':FORMAT,'view':view['view'],'width':w,'height':h,'patches':len(faces),'triangles':2*len(faces),
            'measured_tiles':len(faces)-estimated,'estimated_edge_tiles':estimated,'omitted_tiles':omitted,'edge_search_work':search_work,
            'max_estimate_distance_pixels':max_distance,'max_tile_depth_spread_scene_units':max_spread,
            'bounds_root_local':{'min':low,'max':high},'vertices_sha256':floats_sha(vertices),'uv_sha256':floats_sha(uvs),'options':p,
            'normal_policy':'Store raw native normals in source-root rotation coordinates; explicitly normalize and transform as normals when shading.',
            'scope':'Independent flat projected patches at median measured tile depth; bounded nearest measured witness only for explicitly estimated partial edges. No depth bridges, hidden layers, optical equivalence, shadow/wind or angular guarantee.'}
    report['geometry_sha256']=botany.digest(report|{'patch_records':records})
    return {'vertices':vertices,'uvs':uvs,'faces':faces,'patch_records':records,'report':report}


def texture_map(decoded,geometry_decoded,metadata,view,values,name,*,cancelled=lambda:None):
    """Pack one four-channel data image, preserving signed normals and all fields.

    Callers decode only channels for this map plus surface_weight. Six maps use
    24 float components/pixel; the witness map retains fields unused by shading.
    """
    from . import capture_material_fields
    p=options(values);w,h,_,_,_,root_axes,squares,_,_,_=frame(geometry_decoded,metadata,view,p)
    size=w*h*len(MAPS)*16
    if size>p['max_texture_bytes']:raise ValueError('Depth patch decoded texture budget exceeded')
    mapping=dict(MAPS)
    if name not in mapping:raise ValueError('Unknown depth patch texture map')
    fields={f['key']:f for f in capture_material_fields.FIELDS};ch=decoded['channels'];alpha=geometry_decoded['channels']['TreeCapture.Combined.A'];weight=ch['TreeCapture.MCP_SurfaceWeight.X'];norms=[geometry_decoded['channels']['TreeCapture.Normal.'+axis] for axis in 'XYZ'] if name=='normal_roughness' else None
    if any(len(v)!=w*h for v in [weight,alpha,*ch.values(),*(norms or [])]):raise ValueError('Depth patch texture channel length mismatch')
    result=array('f');normal_axes=[[v/math.sqrt(squares[j]) for v in axis] for j,axis in enumerate(root_axes)]
    for i,a in enumerate(alpha):
        if i%8192==0:cancelled()
        surface=weight[i];active=a>p['alpha_threshold']
        if norms and active and (not all(math.isfinite(row[i]) for row in norms) or sum(row[i]*row[i] for row in norms)<1e-16):raise ValueError('Covered native normal is nonfinite or zero; no inferred replacement')
        if not math.isfinite(surface) or surface<0 or surface>1+1e-5 or active and surface<=1e-6:raise ValueError('Invalid or absent native material surface weight')
        for component in mapping[name]:
            key,_,axis=component.partition('.')
            if key=='coverage':v=a
            elif key=='surface_weight':v=surface
            elif key=='normal':v=capture_data.dot([row[i] for row in norms],normal_axes['XYZ'.index(axis)]) if active else 0.
            else:
                field=fields[key];channel='TreeCapture.'+field['name']+'.'+(axis or 'X');v=ch[channel][i]/surface if active else 0.
            if not math.isfinite(v) or abs(v)>1e20:raise ValueError('Nonfinite/out-of-range native material input')
            if key=='alpha' and active and abs(v-1)>1e-5:raise ValueError('Directional reconstruction currently requires opaque intrinsic shader alpha; coverage remains separate')
            result.append(v)
    return result


def map_channels(name):
    from . import capture_material_fields
    fields={f['key']:f for f in capture_material_fields.FIELDS};names={'TreeCapture.MCP_SurfaceWeight.X'}
    for component in dict(MAPS)[name]:
        key,_,axis=component.partition('.')
        if key not in {'normal','coverage'}:names.add('TreeCapture.'+fields[key]['name']+'.'+(axis or 'X'))
    return sorted(names)
