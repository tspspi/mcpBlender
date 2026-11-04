"""Deterministic metre-space orthographic card fitting and sampled occupancy."""
import math
from .foliage_coverage import raster_triangle
from .card_views import DIRECTIONS,FRAMES

# U cross V points toward the source from the fitted backing plane.
BASES={'TOP':(0,1,2,1),'FRONT':(0,2,1,-1),'SIDE':(1,2,0,1)}


def hull(points):
    points=sorted(set(points))
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def half(seq):
        result=[]
        for p in seq:
            while len(result)>1 and cross(result[-2],result[-1],p)<=0:result.pop()
            result.append(p)
        return result
    return half(points)[:-1]+half(reversed(points))[:-1]


def area(points):
    origin=points[0];local=[(p[0]-origin[0],p[1]-origin[1]) for p in points]
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(local,local[1:]+local[:1])))/2


def fit(triangles,*,view='TOP',outline='CONVEX_HULL',padding=.02,standoff_m=.005,
        resolution=128,max_vertices=64,max_triangles=100000,cancelled=lambda:None,progress=lambda v:None):
    if view not in DIRECTIONS or outline not in {'RECTANGLE','CONVEX_HULL'}:raise ValueError('Unknown card view/outline')
    if not math.isfinite(padding) or not 0<=padding<=.25 or not math.isfinite(standoff_m) or standoff_m<=0:raise ValueError('Invalid card padding/standoff')
    if type(resolution)!=int or not 32<=resolution<=256 or type(max_vertices)!=int or not 4<=max_vertices<=256:raise ValueError('Invalid card resolution/vertex budget')
    if type(max_triangles)!=int or not 1<=max_triangles<=250000 or not 1<=len(triangles)<=max_triangles:raise ValueError('Card triangle budget exceeded or empty source')
    if any(len(t)!=3 or any(len(p)!=3 or any(not math.isfinite(v) for v in p) for p in t) for t in triangles):raise ValueError('Finite source triangles required')
    legacy=view in BASES
    if legacy:
        u,v,n,sign=BASES[view]
        def project(p):return (p[u],p[v])
        def depth_at(p):return sign*p[n]
    else:
        axis_u,axis_v=FRAMES[view];normal=DIRECTIONS[view]
        def project(p):return (sum(a*b for a,b in zip(p,axis_u)),sum(a*b for a,b in zip(p,axis_v)))
        def depth_at(p):return sum(a*b for a,b in zip(p,normal))
    points=[project(p) for t in triangles for p in t]
    low=[min(p[a] for p in points) for a in range(2)];high=[max(p[a] for p in points) for a in range(2)]
    width=[high[a]-low[a] for a in range(2)]
    if min(width)<=1e-10:raise ValueError('Source is edge-on or too small for this card view')
    pad=[w*padding for w in width];low=[low[a]-pad[a] for a in range(2)];high=[high[a]+pad[a] for a in range(2)]
    width=[high[a]-low[a] for a in range(2)]
    if outline=='RECTANGLE':polygon=[tuple(low),(high[0],low[1]),tuple(high),(low[0],high[1])]
    else:
        # Minkowski sum with a padding rectangle encloses the source hull.
        polygon=hull([(x+sx*pad[0],y+sy*pad[1]) for x,y in hull(points) for sx in (-1,1) for sy in (-1,1)])
    if len(polygon)<3 or area(polygon)<=1e-20:raise ValueError('Degenerate projected card')
    if len(polygon)>max_vertices:raise ValueError('Fitted outline exceeds max_vertices; raise budget or choose RECTANGLE')
    depth=[depth_at(p) for t in triangles for p in t];plane=min(depth)-standoff_m
    vertices=[]
    for x,y in polygon:
        if legacy:
            p=[0.,0.,0.];p[u]=x;p[v]=y;p[n]=sign*plane
        else:p=[axis_u[a]*x+axis_v[a]*y+normal[a]*plane for a in range(3)]
        vertices.append(p)
    source_rows=[0]*resolution;target_rows=[0]*resolution
    def pixel(p):return ((p[0]-low[0])*resolution/width[0],(p[1]-low[1])*resolution/width[1])
    for i,t in enumerate(triangles):
        if i%128==0:cancelled()
        if i%256==0:progress({'phase':'rasterizing fitted card coverage','triangles':i,'total_triangles':len(triangles)})
        raster_triangle(source_rows,[pixel(project(p)) for p in t],resolution)
    for i in range(1,len(polygon)-1):raster_triangle(target_rows,[pixel(polygon[j]) for j in (0,i,i+1)],resolution)
    source_pixels=sum(r.bit_count() for r in source_rows);target_pixels=sum(r.bit_count() for r in target_rows)
    if not source_pixels or not target_pixels:raise ValueError('Projection has no sampled surface; change view or increase resolution')
    cancelled();fraction=source_pixels/target_pixels
    return {'method':'ORTHOGRAPHIC_FITTED_CARD_V1','view':view,'outline':outline,'vertices_m':vertices,
            'uv':[((p[0]-low[0])/width[0],(p[1]-low[1])/width[1]) for p in polygon],
            'triangles':len(polygon)-2,'source_triangles':len(triangles),'card_area_m2':area(polygon),
            'rectangle_area_m2':width[0]*width[1],'source_depth_m':max(depth)-min(depth),
            'projection':{'resolution':resolution,'source_pixels':source_pixels,'target_pixels':target_pixels,
                          'geometry_coverage_fraction':fraction,'empty_fraction':1-fraction,
                          'area_amplification':target_pixels/source_pixels},
            'bake_ray_length_m':max(depth)-plane+standoff_m,
            'scope':'Single-view static convex envelope or rectangle; opaque triangle pixel-center estimate only. Holes and overlapping depth remain flattened. Not shader-alpha coverage, runtime overdraw, atlas packing or wind.'}
