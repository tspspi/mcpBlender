"""Bounded PCA-oriented chart rectangles with explicit allocation floors.

Shelves are a deterministic heuristic, not an optimal packing proof. Density
and actual covered pixel centres must be checked on the resulting coordinates.
"""
import math
from array import array


def describe(points,area,rotate):
    if not points or not all(math.isfinite(v) for point in points for v in point) or not math.isfinite(area) or area<=1e-20:raise ValueError('Finite nondegenerate UV charts required')
    center=[sum(p[a] for p in points)/len(points) for a in (0,1)]
    xx=sum((p[0]-center[0])**2 for p in points);yy=sum((p[1]-center[1])**2 for p in points);xy=sum((p[0]-center[0])*(p[1]-center[1]) for p in points)
    angle=.5*math.atan2(2*xy,xx-yy) if rotate else 0.;c,s=math.cos(angle),math.sin(angle)
    local=[((p[0]-center[0])*c+(p[1]-center[1])*s,-(p[0]-center[0])*s+(p[1]-center[1])*c) for p in points]
    low=[min(p[a] for p in local) for a in (0,1)];span=[max(p[a] for p in local)-low[a] for a in (0,1)]
    if min(span)<=1e-12:raise ValueError('UV chart has no representable rectangle')
    return {'local':local,'low':low,'span':span,'area':area,'fill':min(1.,area/(span[0]*span[1]))}


def dimensions(chart,factor,p):
    x,y=chart['span'];area=chart['area'];minimum=p['min_span_pixels']
    if not p['allow_stretch']:
        scale=max(factor,math.sqrt(p['min_area_pixels']/area),minimum*max(x,y)/area)
        return [x*scale,y*scale]
    spans=[max(x*factor,minimum/chart['fill']),max(y*factor,minimum/chart['fill'])]
    current=spans[0]*spans[1]*chart['fill']
    if current<p['min_area_pixels']:
        scale=math.sqrt(p['min_area_pixels']/current);spans=[v*scale for v in spans]
    return spans


def shelf(charts,factor,width,height,border,p):
    gutter=p['gutter_pixels'];rows=[]
    # A pixel safety allowance also protects border/gap guarantees after float32.
    epsilon=2**-10
    for i,chart in enumerate(charts):
        spans=dimensions(chart,factor,p);w,h=[math.ceil(v+2*epsilon)+2*gutter for v in spans]
        if w>width-2*border or h>height-2*border:return None
        rows.append((h,w,i,spans))
    x=y=border;row_height=0;placements={}
    for h,w,i,spans in sorted(rows,key=lambda r:(-r[0],-r[1],r[2])):
        if x+w>width-border:x=border;y+=row_height;row_height=0
        if y+h>height-border:return None
        placements[i]={'origin':[x+gutter+(w-2*gutter-spans[0])/2,y+gutter+(h-2*gutter-spans[1])/2],'span':spans}
        x+=w;row_height=max(row_height,h)
    return placements


def pack(charts,width,height,border,p,*,rotate=True,checkpoint=lambda:None):
    if not 1<=len(charts)<=p['max_charts']:raise ValueError('Chart layout count exceeds max_charts')
    if width*height>4*1024**2 or min(width,height)<32 or max(width,height)>4096:raise ValueError('Chart layout texture pixel budget exceeded')
    border=math.ceil(border)
    if border*2>=min(width,height):raise ValueError('Chart layout border leaves no interior')
    described=[]
    for i,chart in enumerate(charts):
        if i%128==0:checkpoint()
        described.append(describe([(x*width,y*height) for x,y in chart['points']],chart['area']*width*height,rotate))
    checkpoint();placed=shelf(described,0,width,height,border,p)
    if placed is None:raise ValueError('Minimum chart allocations do not fit the shelf layout; change dimensions, chart seams or explicitly allow stretch')
    factor=0.;low=0.;high=1.;attempts=0
    # Retain as much original chart density as this heuristic can accommodate.
    # Floors always apply, including when original density must shrink.
    for attempt in range(25):
        checkpoint();candidate=1. if attempt==0 else (low+high)/2
        result=shelf(described,candidate,width,height,border,p);attempts+=1
        if result is not None:
            placed=result;factor=candidate;low=candidate
            if candidate==1:break
        else:high=candidate
    output=[];stretch=0;minimum_area=math.inf;minimum_span=math.inf
    for i,chart in enumerate(described):
        if i%128==0:checkpoint()
        target=placed[i];scales=[target['span'][a]/chart['span'][a] for a in (0,1)]
        if abs(scales[0]-scales[1])>1e-6*max(scales):stretch+=1
        values=[(target['origin'][a]+(point[a]-chart['low'][a])*scales[a])/(width if a==0 else height) for point in chart['local'] for a in (0,1)]
        values=list(array('f',values));points=list(zip(values[0::2],values[1::2]));output.append(points)
        if any(v<border/(width if a==0 else height) or v>1-border/(width if a==0 else height) for point in points for a,v in enumerate(point)):raise ValueError('Chart layout float32 border verification failed')
        area=chart['area']*scales[0]*scales[1];minimum_area=min(minimum_area,area);minimum_span=min(minimum_span,area/max(target['span']))
    return output,{'method':'PCA_PIXEL_SHELF_V1','charts':len(charts),'global_density_factor':factor,'search_attempts':attempts,'stretched_charts':stretch,'minimum_allocated_area_pixels':minimum_area,'minimum_mean_span_pixels':minimum_span,
                   'texture_size':[width,height],'tile_border_pixels':border,'policy':p,'scope':'Target UV chart rectangles only. Mean span is area divided by longest rectangle side; no minimum local width or actual raster/texel-density guarantee. Reinspect geometric quality and rendered filtering.'}
