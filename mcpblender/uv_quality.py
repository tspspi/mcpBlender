"""Bounded geometric texture quality in physical metres and pixel coordinates."""
import heapq
import math
from array import array
from .uv_math import signed_area,overlaps


def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))


def directional_density(world,uv):
    a,b=sub(world[1],world[0]),sub(world[2],world[0]);u,v=sub(uv[1],uv[0]),sub(uv[2],uv[0])
    normal=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]);det=dot(normal,normal)
    if det<=1e-40:return 0.,0.
    coefficient=dot(u,u)*dot(b,b)+dot(v,v)*dot(a,a)-2*dot(u,v)*dot(a,b)
    product=cross(u,v)**2;discriminant=max(0.,coefficient*coefficient-4*det*product)
    high=max(0.,(coefficient+math.sqrt(discriminant))/(2*det));low=max(0.,product/(det*high)) if high else 0.
    return math.sqrt(low),math.sqrt(high)


def point_segment(p,a,b):
    d=sub(b,a);length=dot(d,d);t=max(0.,min(1.,dot(sub(p,a),d)/length)) if length else 0.
    return math.hypot(*(p[i]-a[i]-t*d[i] for i in (0,1)))


def segment_distance(a,b,c,d):
    ab=sub(b,a);cd=sub(d,c)
    if max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0])) and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1])):
        if cross(ab,sub(c,a))*cross(ab,sub(d,a))<=0 and cross(cd,sub(a,c))*cross(cd,sub(b,c))<=0:return 0.
    return min(point_segment(a,c,d),point_segment(b,c,d),point_segment(c,a,b),point_segment(d,a,b))


def spacing(edges,radius,budget,checkpoint):
    if radius==0:return {'complete':True,'comparisons':0,'required_gap_pixels':0,'violation_pair_count':0,'violations':[],'truncated':False}
    rows=sorted([(min(a[0],b[0]),max(a[0],b[0]),min(a[1],b[1]),max(a[1],b[1]),island,a,b) for island,a,b in edges],key=lambda r:r[0])
    count=min(256,max(1,math.ceil(math.sqrt(len(rows)))));low=min((r[2] for r in rows),default=0.);high=max((r[3] for r in rows),default=0.)
    def cell(y):return max(0,min(count-1,int((y-low)/(high-low)*count))) if high>low else 0
    bins=[set() for _ in range(count)];expiry=[];checks=0;violations={};complete=True
    for index,row in enumerate(rows):
        if index%256==0:checkpoint()
        while expiry and expiry[0][0]+radius<row[0]:
            _,old,first,last=heapq.heappop(expiry)
            for slot in range(first,last+1):bins[slot].discard(old)
        seen=set()
        for slot in range(cell(row[2]-radius),cell(row[3]+radius)+1):
            for other_index in sorted(bins[slot]):
                if other_index in seen:continue
                seen.add(other_index);other=rows[other_index]
                if checks>=budget:complete=False;break
                checks+=1
                if checks%4096==0:checkpoint()
                if other[4]==row[4]:continue
                if other[3]+radius<row[2] or row[3]+radius<other[2]:continue
                gap=segment_distance(row[5],row[6],other[5],other[6])
                if gap<radius:
                    pair=tuple(sorted((row[4],other[4])));violations[pair]=min(gap,violations.get(pair,math.inf))
            if not complete:break
        if not complete:break
        first,last=cell(row[2]),cell(row[3])
        for slot in range(first,last+1):bins[slot].add(index)
        heapq.heappush(expiry,(row[1],index,first,last))
    return {'complete':complete,'comparisons':checks,'required_gap_pixels':radius,'violation_pair_count':len(violations),'violations':[{'islands':list(pair),'gap_pixels':gap} for pair,gap in sorted(violations.items())[:128]],'truncated':len(violations)>128}


def raster(triangles,width,height,islands,budget,checkpoint):
    owner=array('i',[-1])*(width*height);counts=[0]*islands;ambiguous=array('b',[0])*(width*height);ambiguous_count=0;tests=0
    for number,triangle in enumerate(triangles):
        if number%128==0:checkpoint()
        points=[(p[0]*width,p[1]*height) for p in triangle['uv']];a,b,c=points;orientation=cross(sub(b,a),sub(c,a))
        if abs(orientation)<=1e-20:continue
        if orientation<0:b,c=c,b
        x0=max(0,math.ceil(min(p[0] for p in points)-.5));x1=min(width-1,math.floor(max(p[0] for p in points)-.5));y0=max(0,math.ceil(min(p[1] for p in points)-.5));y1=min(height-1,math.floor(max(p[1] for p in points)-.5))
        work=max(0,x1-x0+1)*max(0,y1-y0+1)
        if tests+work>budget:return {'complete':False,'pixel_tests':tests,'covered_pixels':counts,'ambiguous_pixels':ambiguous_count}
        tests+=work
        for y in range(y0,y1+1):
            if y%64==0:checkpoint()
            for x in range(x0,x1+1):
                p=(x+.5,y+.5)
                sides=[(cross(sub(v,u),sub(p,u)),v[1]-u[1],v[0]-u[0]) for u,v in ((a,b),(b,c),(c,a))]
                if all(value>0 or value==0 and (dy>0 or dy==0 and dx<0) for value,dy,dx in sides):
                    slot=y*width+x;island=triangle['island']
                    counts[island]+=1
                    if owner[slot]==-1:owner[slot]=island
                    elif owner[slot]!=island and not ambiguous[slot]:ambiguous[slot]=1;ambiguous_count+=1
    return {'complete':True,'pixel_tests':tests,'covered_pixels':counts,'ambiguous_pixels':ambiguous_count}


def analyze(triangles,edges,islands,p,*,checkpoint=lambda:None):
    width,height=p['width'],p['height']
    if not 1<=islands<=100000 or width*height>4*1024**2 or not triangles:raise ValueError('Texture quality input budget exceeded or empty geometry')
    uv_triangles=[(min(v[0] for v in t['uv']),max(v[0] for v in t['uv']),min(v[1] for v in t['uv']),max(v[1] for v in t['uv']),i,t['uv']) for i,t in enumerate(triangles)]
    checkpoint();overlap=overlaps(uv_triangles,p['max_spacing_tests'],checkpoint=checkpoint)
    if not overlap['complete'] or overlap['face_pair_count']:return {'complete':False,'passed':False,'overlap':overlap,'policy':p,'levels':[],'reason':'Overlapping or incompletely inspected UVs; further quality analysis skipped'}
    out_of_tile=any(v<0 or v>1 for t in triangles for point in t['uv'] for v in point)
    densities=[];areas=[0.]*islands;world_areas=[0.]*islands;degenerate=0
    for index,t in enumerate(triangles):
        if index%256==0:checkpoint()
        pixels=[(v[0]*width,v[1]*height) for v in t['uv']];minimum,maximum=directional_density(t['world_m'],pixels);densities.append(minimum)
        uv_area=abs(signed_area(pixels));a,b=sub(t['world_m'][1],t['world_m'][0]),sub(t['world_m'][2],t['world_m'][0]);normal=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]);area=math.sqrt(dot(normal,normal))/2
        if area<=1e-20 or uv_area<=1e-20:degenerate+=1
        areas[t['island']]+=uv_area;world_areas[t['island']]+=area
    low_density=sum(v<p['min_texels_per_meter'] for v in densities);levels=[];raster_left=p['max_raster_tests'];spacing_left=p['max_spacing_tests']
    for level in range(p['mip_levels']+1):
        checkpoint();w=max(1,width//2**level);h=max(1,height//2**level)
        coverage=raster(triangles,w,h,islands,raster_left,checkpoint);raster_left-=coverage['pixel_tests']
        boundaries=[(island,(a[0]*w,a[1]*h),(b[0]*w,b[1]*h)) for island,a,b in edges]
        gaps=spacing(boundaries,p['padding_pixels']*2,spacing_left,checkpoint);spacing_left-=gaps['comparisons']
        margin=min((min(v[0]*w,v[1]*h,(1-v[0])*w,(1-v[1])*h) for t in triangles for v in t['uv']),default=0.)
        small=[i for i,n in enumerate(coverage['covered_pixels']) if n<p['min_chart_pixels']]
        passed=coverage['complete'] and not coverage['ambiguous_pixels'] and gaps['complete'] and not small and not gaps['violation_pair_count'] and margin>=p['padding_pixels']
        coverage['minimum_covered_pixels']=min(coverage['covered_pixels'])
        coverage['covered_pixels_truncated']=islands>128
        coverage['covered_pixels']=coverage['covered_pixels'][:128]
        levels.append({'level':level,'size':[w,h],'coverage':coverage,'spacing':gaps,'edge_margin_pixels':margin,'undersized_charts':small[:128],'undersized_chart_count':len(small),'passed':passed})
        if not coverage['complete'] or not gaps['complete'] or w==h==1:break
    complete=overlap['complete'] and all(l['coverage']['complete'] and l['spacing']['complete'] for l in levels)
    return {'complete':complete,'passed':complete and not out_of_tile and not overlap['face_pair_count'] and not degenerate and not low_density and all(l['passed'] for l in levels),
            'triangles':len(triangles),'islands':islands,'overlap':overlap,'out_of_tile':out_of_tile,'degenerate_triangles':degenerate,'minimum_directional_texels_per_meter':min(densities),'low_density_triangles':low_density,
            'charts':[{'island':i,'base_pixel_area':areas[i],'world_area_m2':world_areas[i],'area_texels_per_meter':math.sqrt(areas[i]/world_areas[i]) if world_areas[i]>1e-20 else None} for i in range(min(islands,128))],
            'charts_truncated':islands>128,'levels':levels,'policy':p,'scope':'Geometric chart coverage/directional density and continuous boundary gaps. Raster samples are pixel centres; no baked image colors, actual mip/filter kernels, optical, shadow or engine validation.'}
