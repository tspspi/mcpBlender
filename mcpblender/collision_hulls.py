"""Small deterministic double-precision convex hulls for native woody sleeves.

At most 32 points. Incrementally extend an oriented tetrahedron across its visible
faces; the retained interior witness orients every new face. No native IDs or
third-party numerical dependencies are needed. All input points are rechecked.
"""
import collections
import math


def subtract(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def hull(points):
    if not 4<=len(points)<=32 or any(len(p)!=3 or any(type(v) not in (float,int) or not math.isfinite(v) for v in p) for p in points):raise ValueError('Collision hull requires 4..32 finite 3D points')
    # Work near zero to avoid volume/plane cancellation at large placements.
    points=sorted(set(tuple(float(v) for v in p) for p in points))
    if len(points)<4:raise ValueError('Collision hull has fewer than four distinct points')
    origin=points[0];local=[subtract(p,origin) for p in points]
    diagonal=math.sqrt(sum((max(p[a] for p in local)-min(p[a] for p in local))**2 for a in range(3)))
    epsilon=max(1e-12,diagonal*1e-10)
    a=0;b=max(range(1,len(local)),key=lambda i:dot(local[i],local[i]))
    c=max(range(len(local)),key=lambda i:dot(cross(local[b],local[i]),cross(local[b],local[i])))
    normal=cross(local[b],local[c]);length=math.sqrt(dot(normal,normal))
    if length<=epsilon**2:raise ValueError('Collision hull input is collinear')
    d=max(range(len(local)),key=lambda i:abs(dot(local[i],normal)))
    if abs(dot(local[d],normal))/length<=epsilon:raise ValueError('Collision hull input is coplanar')
    center=tuple(sum(local[i][k] for i in (a,b,c,d))/4 for k in range(3))
    def face(i,j,k):
        vector=cross(subtract(local[j],local[i]),subtract(local[k],local[i]));size=math.sqrt(dot(vector,vector))
        if size<=epsilon**2:raise ValueError('Collision hull encountered a degenerate face')
        if dot(subtract(center,local[i]),vector)>0:j,k=k,j;vector=tuple(-v for v in vector)
        return (i,j,k),tuple(v/size for v in vector)
    faces=[face(a,b,c),face(a,d,b),face(a,c,d),face(b,d,c)];pending=set(range(len(local)))-{a,b,c,d}
    def distance(index,f):return dot(subtract(local[index],local[f[0][0]]),f[1])
    while pending:
        index=max(sorted(pending),key=lambda i:max(distance(i,f) for f in faces))
        if max(distance(index,f) for f in faces)<=epsilon:break
        visible=[f for f in faces if distance(index,f)>epsilon];horizon={}
        for triangle,_ in visible:
            for j in range(3):
                edge=(triangle[j],triangle[(j+1)%3]);key=tuple(sorted(edge))
                if key in horizon:del horizon[key]
                else:horizon[key]=edge
        if not horizon:raise ValueError('Collision hull has no closed visible horizon')
        faces=[f for f in faces if f not in visible]+[face(i,j,index) for _,(i,j) in sorted(horizon.items())]
        pending.remove(index)
    edges=collections.Counter(tuple(sorted((f[j],f[(j+1)%3]))) for f,_ in faces for j in range(3))
    oriented=collections.Counter((f[j],f[(j+1)%3]) for f,_ in faces for j in range(3))
    if set(edges.values())!={2} or any(oriented[(b,a)]!=n for (a,b),n in oriented.items()):raise ValueError('Collision hull is not a closed oriented manifold')
    outside=max(0.,max(distance(i,f) for i in range(len(local)) for f in faces))
    if outside>epsilon*4:raise ValueError('Collision hull failed exhaustive vertex containment/convexity')
    used=sorted({i for f,_ in faces for i in f});mapping={v:i for i,v in enumerate(used)}
    triangles=[tuple(mapping[i] for i in f) for f,_ in faces]
    volume=sum(dot(subtract(local[f[0]],center),cross(subtract(local[f[1]],center),subtract(local[f[2]],center))) for f,_ in faces)/6
    if not math.isfinite(volume) or volume<=max(1e-18,epsilon**3):raise ValueError('Collision hull volume is degenerate')
    return {'vertices':[points[i] for i in used],'faces':triangles,'triangles':len(triangles),'volume_local_m3':volume,
            'max_outside_local_m':outside,'containment_tolerance_local_m':epsilon*4,'source_vertices_checked':len(points)}
