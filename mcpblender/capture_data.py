"""Numerical readback of immutable native tree reference captures (no bpy)."""
import math
from pathlib import Path
from . import botany,render_jobs,exr_scanline

CHANNELS=['Combined.A','Depth.Z',*[key+'.'+axis for key in ('Position','Normal') for axis in 'XYZ']]


def dot(a,b):return sum(x*y for x,y in zip(a,b))


def pose(matrix,*,unit=False):
    if len(matrix)!=4 or any(len(row)!=4 for row in matrix) or any(not math.isfinite(v) for row in matrix for v in row) or any(abs(a-b)>1e-6 for a,b in zip(matrix[3],[0,0,0,1])):raise ValueError('Invalid capture affine pose')
    axes=[[matrix[r][c] for r in range(3)] for c in range(3)];sizes=[dot(v,v) for v in axes]
    if not all(math.isfinite(v) for v in sizes) or min(sizes)<=1e-16 or max(sizes)-min(sizes)>max(sizes)*1e-5:raise ValueError('Capture pose requires uniform positive scale')
    if any(abs(dot(axes[a],axes[b]))>max(sizes)*1e-5 for a,b in ((0,1),(0,2),(1,2))):raise ValueError('Capture pose is not orthogonal')
    cross=[axes[0][1]*axes[1][2]-axes[0][2]*axes[1][1],axes[0][2]*axes[1][0]-axes[0][0]*axes[1][2],axes[0][0]*axes[1][1]-axes[0][1]*axes[1][0]]
    if dot(cross,axes[2])<=0 or unit and max(abs(s-1) for s in sizes)>1e-5:raise ValueError('Capture pose handedness/camera scale mismatch')
    return [matrix[i][3] for i in range(3)],axes,sizes


def distribution(values,sampled):
    if not values['count']:return {'count':0,'mean':None,'rmse':None,'max':None,'sampled_percentiles':None}
    sampled.sort()
    return {'count':values['count'],'mean':values['sum']/values['count'],'rmse':math.sqrt(values['squared']/values['count']),'max':values['max'],
            'sampled_percentiles':{'sample_count':len(sampled),'p50':sampled[int((len(sampled)-1)*.5)] if sampled else None,'p95':sampled[int((len(sampled)-1)*.95)] if sampled else None,'p99':sampled[int((len(sampled)-1)*.99)] if sampled else None}}


def measure(decoded,metadata,view,threshold,cancelled=lambda:None,progress=lambda value:None):
    width,height=decoded['width'],decoded['height'];pixels=width*height
    if tuple(decoded['data_window'])!=(0,0,width-1,height-1):raise ValueError('Capture requires a zero-origin full-frame data window')
    channels={name:decoded['channels']['TreeCapture.'+name] for name in CHANNELS}
    camera,axes,_=pose(view['matrix_world'],unit=True);root,rootaxes,squares=pose(metadata['source_root_matrix_world']);unit=metadata['scene_unit_scale'];span=view['ortho_scale']
    if not math.isfinite(unit) or unit<=0 or not math.isfinite(span) or span<=0 or not all(math.isfinite(view[k]) for k in ('clip_start','clip_end')) or not 0<view['clip_start']<view['clip_end']:raise ValueError('Invalid capture units/camera span/clipping')
    counts={k:0 for k in ('covered_pixels','opaque_pixels','depth_hit_pixels','covered_without_depth','opaque_without_depth','uncovered_with_depth','nonfinite_covered','invalid_alpha','zero_covered_normal','nonunit_covered_normal','reconstructed_outside_bounds','position_projection_over_half_pixel','position_projection_over_pixel','opaque_position_projection_over_half_pixel')}
    names=('depth_position_error_m','position_projection_error_px','opaque_depth_position_error_m','opaque_position_projection_error_px','covered_normal_length_error','depth_bounds_overshoot_m')
    stats={k:{'count':0,'sum':0.,'squared':0.,'max':0.} for k in names};samples={k:[] for k in names};step=max(1,(pixels+65535)//65536)
    def add(key,value,i):
        row=stats[key];row['count']+=1;row['sum']+=value;row['squared']+=value*value;row['max']=max(row['max'],value)
        if i%step==0:samples[key].append(value)
    depth_low=math.inf;depth_high=-math.inf;bounds=metadata['bounds_root_local_m'];world_pixel=span/width;root_scale=math.sqrt(squares[0]);tolerance=2*world_pixel/root_scale+1e-5
    for i in range(pixels):
        if i%4096==0:cancelled();progress({'phase':'measuring capture geometry passes','completed':i,'total':pixels})
        a=channels['Combined.A'][i];depth=channels['Depth.Z'][i];covered=math.isfinite(a) and a>threshold
        if not math.isfinite(a) or not -1e-6<=a<=1+1e-6:counts['invalid_alpha']+=1
        hit=math.isfinite(depth) and view['clip_start']<=depth<=view['clip_end'];counts['depth_hit_pixels']+=hit
        if not covered:
            counts['uncovered_with_depth']+=hit;continue
        counts['covered_pixels']+=1;opaque=a>=1-1e-6;counts['opaque_pixels']+=opaque
        if not hit:
            counts['covered_without_depth']+=1;counts['opaque_without_depth']+=opaque;continue
        position=[channels['Position.'+v][i] for v in 'XYZ'];normal=[channels['Normal.'+v][i] for v in 'XYZ']
        if not all(math.isfinite(v) for v in position+normal):counts['nonfinite_covered']+=1;continue
        depth_low=min(depth_low,depth);depth_high=max(depth_high,depth)
        delta=[position[k]-camera[k] for k in range(3)];distance=-dot(delta,axes[2]);error=abs(depth-distance)*unit
        x=i%width;y=i//width
        px=(dot(delta,axes[0])/span+.5)*width-.5;py=(.5-dot(delta,axes[1])/span)*height-.5;projection=math.hypot(px-x,py-y)
        counts['position_projection_over_half_pixel']+=projection>.5;counts['position_projection_over_pixel']+=projection>1;counts['opaque_position_projection_over_half_pixel']+=opaque and projection>.5
        add('depth_position_error_m',error,i);add('position_projection_error_px',projection,i)
        if opaque:add('opaque_depth_position_error_m',error,i);add('opaque_position_projection_error_px',projection,i)
        length=math.sqrt(dot(normal,normal));counts['zero_covered_normal']+=length<1e-6;counts['nonunit_covered_normal']+=abs(length-1)>.01;add('covered_normal_length_error',abs(length-1),i)
        u=((x+.5)/width-.5)*span;v=(.5-(y+.5)/height)*span
        world=[camera[k]+axes[0][k]*u+axes[1][k]*v-axes[2][k]*depth for k in range(3)]
        local=[dot([world[k]-root[k] for k in range(3)],rootaxes[j])/squares[j] for j in range(3)]
        overshoot=max(0.,*(bounds['min'][j]-local[j] for j in range(3)),*(local[j]-bounds['max'][j] for j in range(3)))
        counts['reconstructed_outside_bounds']+=overshoot>tolerance;add('depth_bounds_overshoot_m',overshoot*root_scale*unit,i)
    return {'view':view['view'],'camera':view['camera'],'width':width,'height':height,'alpha_threshold':threshold,**counts,
            'depth_range_scene_units':[depth_low,depth_high] if depth_low<math.inf else None,'world_pixel_m':world_pixel*unit,
            'statistics':{k:distribution(row,samples[k]) for k,row in stats.items()},
            'interpretation':'Rows top-to-bottom; depth backprojects the orthographic pixel centre. Position and normals are measured independently, never silently substituted for depth. Opaque means alpha >= 1-1e-6; filtered/nearest-surface discrepancies are reported, not corrected.'}


def source(p,progress=lambda value:None,cancelled=lambda:False):
    root=Path(p['directory']);job=render_jobs.read_json(root/'job.json')
    proof=render_jobs.validate_contents(root,job['job_id'],progress,cancelled)
    metadata=proof.get('botanical_capture')
    if metadata is None:raise ValueError('Native botanical reference capture required')
    chosen=p.get('views') or [v['view'] for v in metadata['views']];lookup={v['view']:v for v in metadata['views']}
    if not set(chosen)<=lookup.keys():raise ValueError('Requested capture view is absent')
    count=len(chosen)*job['width']*job['height']
    if job['width']*job['height']>p['max_pixels'] or count>p['max_total_pixels']:raise ValueError('Capture inspection pixel budget exceeded')
    rows=[]
    for name in chosen:
        view=lookup[name];row=next(v for v in proof['outputs'] if v['camera']==view['camera'] and v['format']=='OPEN_EXR_MULTILAYER')
        rows.append((view,row))
    return root,proof,metadata,rows


def inspect(p,progress=lambda value:None,cancelled=lambda:False):
    def checkpoint():
        if cancelled():raise InterruptedError('Capture data inspection cancelled')
    root,proof,metadata,rows=source(p,progress,cancelled);reports=[]
    if p.get('material_inputs') and not metadata.get('material_fields'):raise ValueError('Capture lacks native material fields; recapture with material_fields=true')
    for view,row in rows:
        checkpoint();progress({'phase':'reading native capture data','view':view['view'],'completed_views':len(reports),'total_views':len(rows)})
        def view_progress(value):progress(value|{'view':view['view'],'completed_views':len(reports),'total_views':len(rows)})
        data=exr_scanline.decode(root/row['file'],['TreeCapture.'+v for v in CHANNELS],expected_sha256=row['sha256'],cancelled=checkpoint,progress=view_progress)
        report=measure(data,metadata,view,p['alpha_threshold'],checkpoint,view_progress)
        if p.get('material_inputs'):
            from . import capture_material_fields
            report['material_inputs']=capture_material_fields.inspect_view(root/row['file'],row['sha256'],data,p['alpha_threshold'],metadata['material_fields'],cancelled=checkpoint,progress=view_progress)
        reports.append(report)
    report={'method':'NATIVE_ORTHOGRAPHIC_CAPTURE_DATA_V1','capture_sha256':metadata['capture_sha256'],'source_sha256':proof['source_sha256'],
            'files':[{'file':r['file'],'sha256':r['sha256']} for _,r in rows],'options':{k:p.get(k) for k in ('views','alpha_threshold','max_pixels','max_total_pixels','material_inputs')},'views':reports,
            'scope':'Read-only decoded reference-pass statistics, no native scene or file mutation. Copied archives use immutable content validation, not job ownership/adoption. Values are not a completed far mesh, PBR/thickness bake, optical-equivalence or wind qualification.'}
    checkpoint();return report|{'data_sha256':botany.digest(report)}
