"""Small 2D polygon helpers for positive-area UV overlap inspection."""


def signed_area(points):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))/2


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


def overlaps(triangles,budget):
    """Exact overlap tests after an X sweep and conservative Y-bin broad phase."""
    import heapq
    import math
    rows=sorted(triangles,key=lambda t:t[0]);pairs=set();comparisons=0;complete=True
    size=min(256,max(1,math.ceil(math.sqrt(len(rows)))))
    low=min((t[2] for t in rows),default=0);high=max((t[3] for t in rows),default=0)
    def cell(y):return max(0,min(size-1,int((y-low)/(high-low)*size))) if high>low else 0
    bins=[set() for _ in range(size)];expiry=[]
    for index,tri in enumerate(rows):
        while expiry and expiry[0][0]<=tri[0]:
            _,old,a,b=heapq.heappop(expiry)
            for slot in range(a,b+1):bins[slot].discard(old)
        first,last=cell(tri[2]),cell(tri[3]);seen=set()
        for slot in range(first,last+1):
            for other_index in sorted(bins[slot]):
                if other_index in seen:continue
                if comparisons>=budget:complete=False;break
                seen.add(other_index);comparisons+=1;other=rows[other_index]
                if other[3]<=tri[2] or tri[3]<=other[2]:continue
                if triangle_overlap(tri[5],other[5])>1e-12:pairs.add(tuple(sorted((tri[4],other[4]))))
            if not complete:break
        if not complete:break
        for slot in range(first,last+1):bins[slot].add(index)
        heapq.heappush(expiry,(tri[1],index,first,last))
    return {'complete':complete,'comparisons':comparisons,'face_pair_count':len(pairs),'face_pairs':[list(v) for v in sorted(pairs)[:128]],'pairs_truncated':len(pairs)>128}
