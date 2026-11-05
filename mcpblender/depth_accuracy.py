"""Measured centre-depth residuals; unknown coverage is never treated as measured."""
import math
from . import capture_data


def fit_loss(hits,width,pixel_width,slope,charge):
    """Depth objective for the existing normal plane and median depth witness."""
    if not hits:return 0.,0.
    charge(len(hits)*max(1,len(hits).bit_length()))
    ordered=sorted(hits,key=lambda v:(v[0],v[1]));z,anchor,_=ordered[len(ordered)//2]
    loss=maximum=0.
    for depth,index,weight in hits:
        charge()
        predicted=z+pixel_width*(slope[0]*(index%width-anchor%width)+slope[1]*(anchor//width-index//width))
        error=abs(predicted-depth);loss+=weight*error;maximum=max(maximum,error)
    return loss,maximum


def measure(decoded,metadata,view,geometry,tolerance_m,*,charge=lambda n:None,cancelled=lambda:None,progress=lambda v:None,alpha_threshold=.001):
    from . import depth_tiles
    p=depth_tiles.options({});w,h,camera,axes,root,root_axes,squares,span,near,far=depth_tiles.frame(decoded,metadata,view,p)
    unit=metadata['scene_unit_scale'];records=geometry['patch_records'];vertices=geometry['vertices']
    if len(vertices)!=len(records)*12 or len(records)>65536:raise ValueError('Depth residual patch budget/inventory mismatch')
    if not math.isfinite(tolerance_m) or tolerance_m<=0:raise ValueError('Positive depth residual tolerance required')
    alpha=decoded['channels']['TreeCapture.Combined.A'];depth=decoded['channels']['TreeCapture.Depth.Z']
    known=unknown=misses=unmet=0;weight=loss=squared=maximum=0.;pixel_width=span/w
    for index,record in enumerate(records):
        charge(32)
        if index%256==0:cancelled();progress({'phase':'measuring float32 patch depth residuals','completed':index,'total':len(records)})
        corners=[]
        for j in range(4):
            local=vertices[index*12+j*3:index*12+j*3+3]
            delta=[root[k]+sum(root_axes[a][k]*local[a] for a in range(3))-camera[k] for k in range(3)]
            corners.append([capture_data.dot(delta,axes[0]),capture_data.dot(delta,axes[1]),-capture_data.dot(delta,axes[2])])
        triangles=[]
        for a,b,c in ((0,1,2),(0,2,3)):
            va,vb,vc=(corners[i] for i in (a,b,c));det=(vb[1]-vc[1])*(va[0]-vc[0])+(vc[0]-vb[0])*(va[1]-vc[1])
            if not math.isfinite(det) or det<=0:raise ValueError('Depth-refined float32 patch projection is degenerate')
            triangles.append((va,vb,vc,det))
        x,y,right,bottom=record['pixel_rect'];cell_error=0.
        for yy in range(y,bottom):
            for xx in range(x,right):
                charge(1);i=yy*w+xx;a=alpha[i]
                if not math.isfinite(a) or not -1e-6<=a<=1+1e-6:raise ValueError('Invalid depth residual coverage')
                if a<=alpha_threshold:continue
                if not math.isfinite(depth[i]) or not near<=depth[i]<=far:unknown+=1;continue
                u=((xx+.5)/w-.5)*span;v=(.5-(yy+.5)/h)*span;predicted=None
                for va,vb,vc,det in triangles:
                    wa=((vb[1]-vc[1])*(u-vc[0])+(vc[0]-vb[0])*(v-vc[1]))/det
                    wb=((vc[1]-va[1])*(u-vc[0])+(va[0]-vc[0])*(v-vc[1]))/det;wc=1-wa-wb
                    if min(wa,wb,wc)>=-1e-10:
                        predicted=wa*va[2]+wb*vb[2]+wc*vc[2];break
                if predicted is None:misses+=1;continue
                error=abs(predicted-depth[i])*unit;known+=1;weight+=a;loss+=a*error;squared+=a*error*error;maximum=max(maximum,error);cell_error=max(cell_error,error)
        unmet+=cell_error>tolerance_m
    return {'format':'mcpblender-measured-depth-residual-v1','depth_tolerance_m':tolerance_m,'measured_depth_pixels':known,
            'unknown_depth_pixels':unknown,'projected_sample_misses':misses,'measured_alpha_mass':weight,
            'coverage_weighted_mae_m':loss/weight if weight else None,'coverage_weighted_rmse_m':math.sqrt(squared/weight) if weight else None,
            'maximum_error_m':maximum if known else None,'tolerance_unmet_cells':unmet,'measured_tolerance_met':bool(known) and not unmet and not misses,
            'scope':'Actual source-root float32 mesh vertices, source placement, projected triangle intersections and measured covered pixel-centre depths in emitted patch domains only. Unknown depth and projection misses are counted, never estimated or included as zero error. No original-surface identity, target-placement rounding, filtered subpixel depth, optical or shadow equivalence guarantee.'}
