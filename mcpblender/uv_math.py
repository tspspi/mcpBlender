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
