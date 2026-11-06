"""Packed first-hit UV correspondence for independent blade-card preparation."""
from array import array
from collections import deque
import hashlib
import math
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

RECIPE='BLADE_FIRST_HIT_SOURCE_UV_V1'


def create(high,target,source_uv,target_uv,width,height,ray_length,own):
    """Build a data image; all new IDs are immediately assigned to the caller."""
    from .bridge import check_cancelled,report_progress
    mesh=high.data;mesh.calc_loop_triangles();triangles=list(mesh.loop_triangles)
    if not triangles or len(triangles)>250000 or width*height>4*1024**2:raise ValueError('Blade UV lookup budget exceeded')
    layer=mesh.uv_layers.get(source_uv)
    if layer is None:raise ValueError('Blade source UV map missing: '+source_uv)
    coords=[high.matrix_world@v.co for v in mesh.vertices]
    bvh=BVHTree.FromPolygons(coords,[t.vertices for t in triangles],all_triangles=True)
    if len(target.data.polygons)!=1 or len(target.data.polygons[0].vertices)!=4:raise ValueError('Blade UV lookup requires one rectangular target')
    face=target.data.polygons[0];corners=[target.matrix_world@target.data.vertices[j].co for j in face.vertices];origin=corners[0];u=corners[1]-origin;v=corners[3]-origin
    normal=u.cross(v).normalized();uv=[target.data.uv_layers[target_uv].data[j].uv for j in face.loop_indices];lo=uv[0];span=uv[2]-lo
    if min(span)<=0 or abs(u.normalized().dot(v.normalized()))>1e-5:raise ValueError('Blade UV lookup requires positive rectangular UV axes')
    pixels=array('f',[0.])*(width*height*4);valid=bytearray(width*height);epsilon=max(1e-12,ray_length*1e-6)
    for y in range(height):
        if y%8==0:
            check_cancelled();report_progress({'phase':'projecting blade source UV correspondence','completed_rows':y,'total_rows':height,'source_uv':source_uv})
        for x in range(width):
            s=((x+.5)/width-lo.x)/span.x;t=((y+.5)/height-lo.y)/span.y
            if not 0<=s<=1 or not 0<=t<=1:continue
            hit,_,index,_=bvh.ray_cast(origin+u*s+v*t-normal*epsilon,normal,ray_length+epsilon)
            if hit is None:continue
            tri=triangles[index];a,b,c=(coords[j] for j in tri.vertices);e=b-a;f=c-a;d=hit-a;ee=e.dot(e);ef=e.dot(f);ff=f.dot(f);den=ee*ff-ef*ef
            if den<=0:raise ValueError('Degenerate blade source UV triangle')
            s=(d.dot(e)*ff-d.dot(f)*ef)/den;t=(d.dot(f)*ee-d.dot(e)*ef)/den
            source=[layer.data[j].uv for j in tri.loops];value=source[0]*(1-s-t)+source[1]*s+source[2]*t
            if not all(math.isfinite(k) for k in value):raise ValueError('Nonfinite blade UV correspondence')
            p=y*width+x;valid[p]=1;pixels[4*p:4*p+4]=array('f',[value.x,value.y,0.,1.])
    covered=sum(valid)
    if not covered:raise ValueError('Blade UV lookup has no projected source pixels')
    frontier=deque(i for i,filled in enumerate(valid) if filled);filled=bytearray(valid);completed=0
    while frontier:
        p=frontier.popleft();x=p%width;y=p//width
        if completed%8192==0:check_cancelled()
        completed+=1
        for q in ([p-1] if x else [])+([p+1] if x+1<width else [])+([p-width] if y else [])+([p+width] if y+1<height else []):
            if filled[q]:continue
            filled[q]=1;pixels[4*q:4*q+4]=pixels[4*p:4*p+4];frontier.append(q)
    check_cancelled();image=own(bpy.data.images.new(target.name+'_SourceUV',width=width,height=height,alpha=True,float_buffer=True));image.colorspace_settings.name='Non-Color';image.pixels.foreach_set(pixels);image.file_format='OPEN_EXR';image.pack()
    return image,{'recipe':RECIPE,'image':image.name,'source_uv':source_uv,'target_uv':target_uv,'width':width,'height':height,'covered_pixels':covered,'coverage_sha256':hashlib.sha256(valid).hexdigest(),
                  'pixel_sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),'packed_sha256':hashlib.sha256(image.packed_file.data).hexdigest(),
                  'projection':'Nearest first hit along target normal from backing rectangle; source loop UV barycentric interpolation.',
                  'padding':'Nearest four-neighbour Manhattan propagation from covered pixels; coverage mask hashed before padding.',
                  'scope':'Float source-UV data for later native shader adaptation. Linear texture sampling and finite resolution are approximate; not an all-pixel UV error or optical/wind/far-LOD certificate.'}
