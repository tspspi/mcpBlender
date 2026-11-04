"""Small 2D polygon helpers for positive-area UV overlap inspection."""


def signed_area(points):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))/2


def affine_triangle_edges(points,linear,unit=1.):
    """Transform local edge differences in float64 without global translation."""
    import math
    origin=points[0];edges=[]
    for point in points[1:]:
        x,y,z=(float(point[i])-float(origin[i]) for i in (0,1,2))
        edge=[(row[0]*x+row[1]*y+row[2]*z)*unit for row in linear]
        if not all(math.isfinite(v) for v in edge):raise ValueError('Finite transformed triangle edges required')
        edges.append(edge)
    return edges


def triangle_edge_area(a,b):
    import math
    area=math.hypot(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])/2
    if not math.isfinite(area):raise ValueError('Finite transformed triangle area required')
    return area


def inset_tile(values,width,height,pixels,scale):
    """Uniformly fit or translate a layout into a float32-safe pixel border."""
    import math
    from array import array
    if not pixels:return values
    if not values or len(values)%2 or not all(math.isfinite(v) for v in values):raise ValueError('Finite nonempty UV coordinates required')
    pad=[pixels/width,pixels/height];epsilon=2**-22
    available=[1-2*(v+epsilon) for v in pad]
    if min(available)<=0:raise ValueError('Tile padding leaves no representable texture interior')
    bounds=[(min(values[axis::2]),max(values[axis::2])) for axis in (0,1)]
    spans=[hi-lo for lo,hi in bounds]
    if not scale and any(span>space for span,space in zip(spans,available)):raise ValueError('UV layout cannot fit tile padding without scaling; enable scale or lower density')
    factor=min([1.]+[space/span for span,space in zip(spans,available) if span>0]) if scale else 1.
    centers=[(lo+hi)/2 for lo,hi in bounds]
    result=list(array('f',(.5+(v-centers[i%2])*factor for i,v in enumerate(values))))
    if any(v<pad[i%2] or v>1-pad[i%2] for i,v in enumerate(result)):raise ValueError('Packed UV border failed float32 verification')
    return result


def triangle_overlap(a,b):
    """Convex clipping: touching edges/vertices have zero area."""
    if abs(signed_area(list(a)))<=1e-20 or abs(signed_area(list(b)))<=1e-20:
        return 0
    polygon=list(a)
    sign=1 if signed_area(list(b))>=0 else -1
    for start,end in zip(b,b[1:]+b[:1]):
        def side(point):
            return sign*((end[0]-start[0])*(point[1]-start[1])-(end[1]-start[1])*(point[0]-start[0]))
        source,polygon=polygon,[]
        if not source:break
        previous=source[-1];dp=side(previous)
        for current in source:
            dc=side(current)
            if (dc>=0)!=(dp>=0):
                t=dp/(dp-dc)
                polygon.append((previous[0]+t*(current[0]-previous[0]),previous[1]+t*(current[1]-previous[1])))
            if dc>=0:polygon.append(current)
            previous,dp=current,dc
    return abs(signed_area(polygon)) if len(polygon)>=3 else 0


def overlaps(triangles,budget,*,checkpoint=lambda:None):
    """Exact overlap tests after an X sweep and conservative Y-bin broad phase."""
    import heapq
    import math
    rows=sorted(triangles,key=lambda t:t[0]);pairs=set();comparisons=0;complete=True
    size=min(256,max(1,math.ceil(math.sqrt(len(rows)))))
    low=min((t[2] for t in rows),default=0);high=max((t[3] for t in rows),default=0)
    def cell(y):return max(0,min(size-1,int((y-low)/(high-low)*size))) if high>low else 0
    bins=[set() for _ in range(size)];expiry=[]
    for index,tri in enumerate(rows):
        if index%256==0:checkpoint()
        while expiry and expiry[0][0]<=tri[0]:
            _,old,a,b=heapq.heappop(expiry)
            for slot in range(a,b+1):bins[slot].discard(old)
        first,last=cell(tri[2]),cell(tri[3]);seen=set()
        for slot in range(first,last+1):
            for other_index in sorted(bins[slot]):
                if other_index in seen:continue
                if comparisons>=budget:complete=False;break
                seen.add(other_index);comparisons+=1;other=rows[other_index]
                if comparisons%4096==0:checkpoint()
                if other[3]<=tri[2] or tri[3]<=other[2]:continue
                if triangle_overlap(tri[5],other[5])>1e-12:pairs.add(tuple(sorted((tri[4],other[4]))))
            if not complete:break
        if not complete:break
        for slot in range(first,last+1):bins[slot].add(index)
        heapq.heappush(expiry,(tri[1],index,first,last))
    return {'complete':complete,'comparisons':comparisons,'face_pair_count':len(pairs),'face_pairs':[list(v) for v in sorted(pairs)[:128]],'pairs_truncated':len(pairs)>128}
