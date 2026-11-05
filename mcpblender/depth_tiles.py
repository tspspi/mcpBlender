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
          'max_triangles':32768,'max_pixels':1048576,'max_texture_bytes':256*1024**2,'max_search_work':2000000,'geometry_mode':'FLAT','normal_tolerance_degrees':15.,'max_slope':16.,'max_refinement_work':8000000,'max_moment_candidates':32,'output_resolution':None}


def floats_sha(values):
    if sys.byteorder=='little':return hashlib.sha256(values.tobytes()).hexdigest()
    copy=array(values.typecode,values);copy.byteswap();return hashlib.sha256(copy.tobytes()).hexdigest()


def options(values):
    values=dict(values);depth_tolerance=values.pop('depth_tolerance_m',None)
    plane_normal_source=values.pop('plane_normal_source','SHADING_PASS')
    if plane_normal_source not in ('SHADING_PASS','GEOMETRIC_AOV'):raise ValueError('Invalid plane normal source')
    p=DEFAULTS|values
    if set(p)!=set(DEFAULTS):raise ValueError('Unknown depth patch option')
    for key,low,high in [('tile_pixels',1,64),('edge_radius_pixels',0,64),('max_triangles',2,131072),('max_pixels',1024,1048576),('max_texture_bytes',1024,512*1024**2),('max_search_work',1,8000000),('max_refinement_work',1,16000000),('max_moment_candidates',1,64)]:
        if type(p[key]) is not int or not low<=p[key]<=high:raise ValueError('Invalid depth patch option: '+key)
    if p['tile_pixels'] not in (1,2,4,8,16,32,64) or p['edge_depth_policy'] not in {'NEAREST','OMIT','REFUSE'}:raise ValueError('Invalid depth patch tile/edge policy')
    if type(p['alpha_threshold']) not in (int,float) or not math.isfinite(p['alpha_threshold']) or not 0<p['alpha_threshold']<1:raise ValueError('Invalid depth patch alpha threshold')
    if p['geometry_mode'] not in {'FLAT','ADAPTIVE_NORMAL','ADAPTIVE_DEPTH_NORMAL','MOMENT_FACETS'}:raise ValueError('Invalid depth patch geometry mode')
    for key,low,high in [('normal_tolerance_degrees',.1,90),('max_slope',.01,64)]:
        if type(p[key]) not in (int,float) or not math.isfinite(p[key]) or not low<=p[key]<=high:raise ValueError('Invalid depth patch option: '+key)
    for key in ('normal_tolerance_degrees','max_slope'):p[key]=float(p[key])
    if p['output_resolution'] is not None and (type(p['output_resolution']) is not int or not 1<=p['output_resolution']<=1024):raise ValueError('Invalid declared output resolution')
    if p['geometry_mode']=='ADAPTIVE_DEPTH_NORMAL':
        if type(depth_tolerance) not in (int,float) or not math.isfinite(depth_tolerance) or not 1e-6<=depth_tolerance<=1000:raise ValueError('ADAPTIVE_DEPTH_NORMAL requires explicit depth_tolerance_m in [1e-6,1000]')
        p['depth_tolerance_m']=float(depth_tolerance)
    elif depth_tolerance is not None:raise ValueError('depth_tolerance_m requires ADAPTIVE_DEPTH_NORMAL')
    if plane_normal_source=='GEOMETRIC_AOV':
        if p['geometry_mode'] not in {'ADAPTIVE_NORMAL','ADAPTIVE_DEPTH_NORMAL'}:raise ValueError('GEOMETRIC_AOV requires adaptive geometry')
        p['plane_normal_source']=plane_normal_source
    return p


def output_sampling(width,p):
    """Declare a matched square output grid while retaining capture data pixels."""
    output=p['output_resolution']
    if output is None:return None
    if type(width) is not int or width<1 or width%output:raise ValueError('Capture/output resolution ratio must be an integer power of two')
    ratio=width//output
    if ratio not in (1,2,4,8,16,32,64):raise ValueError('Capture/output resolution ratio must be a power of two through 64')
    tile=p['tile_pixels']*ratio
    if tile>64:raise ValueError('Output tile exceeds 64 capture pixels; reduce tile_pixels or the capture/output ratio')
    return {'format':'mcpblender-depth-output-sampling-v1','capture_resolution':width,'output_resolution':output,
            'capture_texels_per_output_pixel':ratio,'base_tile_output_pixels':p['tile_pixels'],
            'base_tile_capture_pixels':tile,'edge_radius_pixel_space':'CAPTURE_DATA',
            'scope':'Matched square source-camera frame only. Capture data and texture budgets stay at source resolution; declared output controls base grid and moment projection units. Coverage is filtered again during rendering. Density alone does not certify silhouette, PBR, lighting, other cameras or population quality.'}


def frame(decoded,metadata,view,p):
    w,h=decoded['width'],decoded['height']
    if type(w) is not int or type(h) is not int or w!=h or not 1<=w<=2048 or w*h>p['max_pixels'] or tuple(decoded['data_window'])!=(0,0,w-1,h-1):raise ValueError('Depth patches require bounded square full-frame pixels')
    camera,axes,_=capture_data.pose(view['matrix_world'],unit=True)
    root,root_axes,squares=capture_data.pose(metadata['source_root_matrix_world'])
    unit=metadata['scene_unit_scale'];span=view['ortho_scale'];near=view['clip_start'];far=view['clip_end']
    if not all(math.isfinite(v) for v in (unit,span,near,far)) or unit<=0 or span<=0 or not 0<near<far:raise ValueError('Invalid depth patch units/camera clipping')
    return w,h,camera,axes,root,root_axes,squares,span,near,far


def nearest_depth_pixel(cx,cy,radius,w,h,eligible,charge,cancelled):
    """Exact bounded Euclidean nearest witness; ties use row-major pixel ID.

    Visit expanding integer squares and stop only when every unseen pixel is
    strictly farther than the best witness. Each candidate is charged once.
    """
    from itertools import chain
    previous=None;nearest=None
    for ring in range(math.ceil(radius)+1):
        cancelled();left=max(0,math.ceil(cx-ring));right=min(w-1,math.floor(cx+ring));top=max(0,math.ceil(cy-ring));bottom=min(h-1,math.floor(cy+ring))
        if left>right or top>bottom:continue
        for y in range(top,bottom+1):
            xs=range(left,right+1) if previous is None or not previous[2]<=y<=previous[3] else chain(range(left,previous[0]),range(previous[1]+1,right+1))
            for x in xs:
                charge();d=(x-cx)**2+(y-cy)**2;i=y*w+x
                if d<=radius*radius and eligible(i) and (nearest is None or (d,i)<nearest):nearest=(d,i)
        previous=(left,right,top,bottom)
        unseen=[distance*distance for exists,distance in ((left>0,cx-left+1),(right<w-1,right+1-cx),(top>0,cy-top+1),(bottom<h-1,bottom+1-cy)) if exists]
        if nearest is not None and nearest[0]<min(unseen,default=math.inf):break
    return nearest


def geometry(decoded,metadata,view,values,*,cancelled=lambda:None,progress=lambda v:None):
    original=options(values);sampling=output_sampling(decoded['width'],original)
    normal_contract=None
    if original.get('plane_normal_source')=='GEOMETRIC_AOV':
        from . import geometric_normals
        fields=metadata.get('material_fields',{});normal_contract=fields.get('geometric_normals')
        if not normal_contract:raise ValueError('Geometric plane normals require recapture with geometric_normals=true')
        geometric_normals.validate(normal_contract,fields['materials'])
        if any(n not in decoded['channels'] for n in geometric_normals.channels()):raise ValueError('Missing captured geometric-normal channels')
        # Only this private geometry view changes. The caller retains its raw
        # native Normal pass for all material maps and later source inspection.
        decoded=decoded|{'channels':decoded['channels']|dict(zip(('TreeCapture.Normal.'+a for a in 'XYZ'),(decoded['channels'][n] for n in geometric_normals.channels())))}
    p=original|({'tile_pixels':sampling['base_tile_capture_pixels']} if sampling else {})
    if p['geometry_mode'] in {'ADAPTIVE_NORMAL','ADAPTIVE_DEPTH_NORMAL'}:
        from . import adaptive_depth
        result=adaptive_depth.geometry(decoded,metadata,view,p,cancelled=cancelled,progress=progress)
    elif p['geometry_mode']=='MOMENT_FACETS':
        from . import moment_depth
        result=moment_depth.geometry(decoded,metadata,view,p,cancelled=cancelled,progress=progress)
    else:result=_geometry(decoded,metadata,view,p,cancelled=cancelled,progress=progress)
    if sampling or normal_contract:
        report=result['report'];report['options']=original
        if sampling:report['output_sampling']=sampling
        if normal_contract:report['plane_normal_source']={'source':'GEOMETRIC_AOV','normals_sha256':normal_contract['normals_sha256'],
            'scope':'Adaptive plane slopes and angular residuals use captured geometric-normal means. Shader maps retain the original native Normal pass. Filtered geometric normals do not identify the surface producing a centre depth.'}
        report['geometry_sha256']=botany.digest({k:v for k,v in report.items() if k!='geometry_sha256'}|{'patch_records':result['patch_records']})
    return result


def _geometry(decoded,metadata,view,values,*,rectangles=None,slopes=None,cancelled=lambda:None,progress=lambda v:None):
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
    rects=rectangles if rectangles is not None else ((x,y,min(w,x+step),min(h,y+step)) for y in range(0,h,step) for x in range(0,w,step))
    total=len(rectangles) if rectangles is not None else ((w+step-1)//step)*((h+step-1)//step)
    for index,(x,y,right,bottom) in enumerate(rects):
        if index%64==0:cancelled();progress({'phase':'reconstructing directional depth patches','completed':index,'total':total})
        pixels=[yy*w+xx for yy in range(y,bottom) for xx in range(x,right)]
        active=[i for i in pixels if alpha[i]>p['alpha_threshold']]
        if not active:continue
        hits=[i for i in active if hit(i)];is_estimate=not hits;distance=0.
        if not hits:
            if p['edge_depth_policy']=='REFUSE':raise ValueError('Partial-coverage tile lacks centre depth; choose an explicit edge policy')
            if p['edge_depth_policy']=='OMIT':omitted+=1;continue
            def charge_search():
                nonlocal search_work
                search_work+=1
                if search_work>p['max_search_work']:raise ValueError('Depth patch edge search work budget exceeded')
            cx=(x+right-1)/2;cy=(y+bottom-1)/2
            nearest=nearest_depth_pixel(cx,cy,p['edge_radius_pixels'],w,h,lambda i:alpha[i]>p['alpha_threshold'] and hit(i),charge_search,cancelled)
            if nearest is None:raise ValueError('No measured depth witness inside edge radius; increase radius or explicitly omit tiles')
            distance=math.sqrt(nearest[0]);hits=[nearest[1]];estimated+=1;max_distance=max(max_distance,distance)
        selected=sorted(hits,key=lambda i:(depth[i],i));witness=selected[len(selected)//2];z=depth[witness];spread=depth[selected[-1]]-depth[selected[0]];max_spread=max(max_spread,spread)
        if 2*(len(faces)+1)>p['max_triangles']:raise ValueError('Depth patch triangle budget exceeded')
        slope=slopes.get((x,y,right,bottom),(0.,0.)) if slopes else (0.,0.)
        anchor_u=((witness%w+.5)/w-.5)*span;anchor_v=(.5-(witness//w+.5)/h)*span
        delta=max(abs(slope[0]*((a/w-.5)*span-anchor_u)+slope[1]*((.5-b/h)*span-anchor_v)) for a,b in ((x,bottom),(right,bottom),(right,y),(x,y)))
        room=max(0.,min(z-near,far-z))*(1-1e-6);clip_limited=delta>room
        if clip_limited and delta:slope=tuple(v*room/delta for v in slope)
        base_points=[]
        for a,b in ((x,bottom),(right,bottom),(right,y),(x,y)):
            u=(a/w-.5)*span;v=(.5-b/h)*span
            world=[camera[k]+axes[0][k]*u+axes[1][k]*v-axes[2][k]*z for k in range(3)]
            local=[capture_data.dot([world[k]-root[k] for k in range(3)],root_axes[j])/squares[j] for j in range(3)]
            base_points.append((u,v,local,a/w,1-b/h))
        direction=[-capture_data.dot(axes[2],root_axes[j])/squares[j] for j in range(3)]
        bounds=metadata.get('bounds_root_local_m') if slopes is not None else None;bound_scale=1.
        if bounds:
            if any(len(bounds[key])!=3 or any(not math.isfinite(v) for v in bounds[key]) for key in ('min','max')) or any(bounds['min'][j]>bounds['max'][j] for j in range(3)):raise ValueError('Invalid source bounds for normal-aligned patches')
            for u,v,local,_,_ in base_points:
                delta=slope[0]*(u-anchor_u)+slope[1]*(v-anchor_v)
                for j in range(3):
                    change=direction[j]*delta
                    # Never increase an existing flat-patch bounds overshoot.
                    if change>0:bound_scale=min(bound_scale,(max(local[j],bounds['max'][j])-local[j])/change)
                    elif change<0:bound_scale=min(bound_scale,(min(local[j],bounds['min'][j])-local[j])/change)
            if bound_scale<1:slope=tuple(v*max(0.,bound_scale) for v in slope)
        base=len(vertices)//3
        for u,v,original,uu,vv in base_points:
            delta=slope[0]*(u-anchor_u)+slope[1]*(v-anchor_v)
            local=[original[j]+direction[j]*delta for j in range(3)] if delta else original
            if any(not math.isfinite(v) or abs(v)>1e20 for v in local):raise ValueError('Depth patch coordinates exceed finite native range')
            vertices.extend(local);uvs.extend((uu,vv))
            for j in range(3):low[j]=min(low[j],local[j]);high[j]=max(high[j],local[j])
        faces.append((base,base+1,base+2,base+3));records.append({'pixel_rect':[x,y,right,bottom],'depth_scene_units':z,'witness_pixel':[witness%w,witness//w],'estimated':is_estimate,'witness_distance_pixels':distance,'measured_depth_spread_scene_units':spread,**({'slope_camera':list(slope),'plane_anchor_pixel':[witness%w+.5,witness//w+.5],'clip_limited':clip_limited,'source_bounds_limited':bound_scale<1} if slopes is not None else {})})
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
