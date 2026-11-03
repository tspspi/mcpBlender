"""Bounded orthographic blade-triangle coverage, independent of Blender/rendering."""
import math
from . import botany as b,foliage
VIEWS={'FRONT':(0,2),'SIDE':(1,2),'TOP':(0,1)}


def rotation(euler):
    x,y,z=euler;cx,sx=math.cos(x),math.sin(x);cy,sy=math.cos(y),math.sin(y);cz,sz=math.cos(z),math.sin(z)
    return ((cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx),(sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx),(-sy,cy*sx,cy*cx))


def raster_triangle(rows,points,size):
    """Union pixel centers inside a projected triangle; horizontal edges are half-open."""
    a,c,d=points
    if abs((c[0]-a[0])*(d[1]-a[1])-(c[1]-a[1])*(d[0]-a[0]))<1e-12:return
    low=max(0,math.ceil(min(p[1] for p in points)-.5));high=min(size-1,math.floor(max(p[1] for p in points)-.5))
    for row in range(low,high+1):
        y=row+.5;crossings=[]
        for a,c in ((points[0],points[1]),(points[1],points[2]),(points[2],points[0])):
            if min(a[1],c[1])<=y<max(a[1],c[1]):crossings.append(a[0]+(y-a[1])*(c[0]-a[0])/(c[1]-a[1]))
        if len(crossings)<2:continue
        lo=max(0,math.ceil(min(crossings)-.5));hi=min(size-1,math.floor(max(crossings)-.5))
        if hi>=lo:rows[row]|=((1<<(hi-lo+1))-1)<<lo


def analyze(model,layout,resolution=128,views=('FRONT','SIDE','TOP'),margin=2.5,max_projected_triangles=60000000,include_masks=False,progress=lambda v:None,cancelled=lambda:None):
    if type(resolution)!=int or not 32<=resolution<=256:raise ValueError('Coverage resolution must be an integer from 32 to 256')
    if not views or len(views)>3 or len(set(views))!=len(views) or any(v not in VIEWS for v in views):raise ValueError('Choose distinct FRONT/SIDE/TOP views')
    if not math.isfinite(margin) or not 0<=margin<=5:raise ValueError('Coverage margin must be from zero to five metres')
    if type(max_projected_triangles)!=int or not 1<=max_projected_triangles<=100000000:raise ValueError('Invalid coverage triangle budget')
    if layout['source_model_sha256']!=b.digest(model):raise ValueError('Foliage source model does not match coverage model')
    p=layout['recipe'];prototypes=[]
    for i in range(p['variants']):
        mesh=foliage.leaf_mesh(foliage.variant_shape(p,i));triangles=[]
        for face,part in zip(mesh['faces'],mesh['parts']):
            if not part:triangles.extend((face[0],face[j],face[j+1]) for j in range(1,len(face)-1))
        used=sorted({i for triangle in triangles for i in triangle});remap={old:new for new,old in enumerate(used)}
        prototypes.append(([mesh['vertices'][i] for i in used],[tuple(remap[i] for i in triangle) for triangle in triangles]))
    work=sum(len(prototypes[v['variant']][1]) for v in layout['leaves'])*len(views)
    if work>max_projected_triangles:raise ValueError('Projected triangle work budget exceeded; reduce views/density or explicitly raise budget')
    crown=model['crown'];center=crown['center'];radii=crown['radii'];states={}
    for view in views:
        axes=VIEWS[view];low=[center[a]-radii[a]-margin for a in axes];width=[2*(radii[a]+margin) for a in axes]
        states[view]={'axes':axes,'low':low,'width':width,'rows':[0]*resolution,'clipped':False}
    for index,leaf in enumerate(layout['leaves']):
        if index%256==0:cancelled();progress({'phase':'projecting botanical foliage','leaves':index,'total_leaves':len(layout['leaves']),'projected_triangles':work})
        matrix=rotation(leaf['rotation']);vertices,triangles=prototypes[leaf['variant']];scale=leaf['scale'];position=leaf['position']
        transformed=[tuple(position[a]+scale*sum(matrix[a][j]*v[j] for j in range(3)) for a in range(3)) for v in vertices]
        for state in states.values():
            projected=[tuple((v[a]-state['low'][k])*resolution/state['width'][k] for k,a in enumerate(state['axes'])) for v in transformed]
            if any(v<0 or v>resolution for point in projected for v in point):state['clipped']=True
            for triangle in triangles:raster_triangle(state['rows'],[projected[i] for i in triangle],resolution)
    result={}
    for view,state in states.items():
        rows=state['rows'];ellipse=[];ax,ay=state['axes'];dx,dy=(w/resolution for w in state['width'])
        for row in range(resolution):
            y=state['low'][1]+(row+.5)*dy;mask=0
            for col in range(resolution):
                x=state['low'][0]+(col+.5)*dx
                if ((x-center[ax])/radii[ax])**2+((y-center[ay])/radii[ay])**2<=1:mask|=1<<col
            ellipse.append(mask)
        total=sum(v.bit_count() for v in rows);inside=sum((a&c).bit_count() for a,c in zip(rows,ellipse));envelope=sum(v.bit_count() for v in ellipse)
        reflected=[int(format(v,f'0{resolution}b')[::-1],2) for v in rows];union=sum((a|c).bit_count() for a,c in zip(rows,reflected))
        item={'axes':list(state['axes']),'frame_min_m':state['low'],'frame_max_m':[a+c for a,c in zip(state['low'],state['width'])],
              'pixel_size_m':[dx,dy],'covered_pixels':total,'crown_pixels':envelope,'covered_crown_pixels':inside,
              'crown_coverage_fraction':inside/max(1,envelope),'projected_leaf_area_m2':total*dx*dy,'outside_crown_area_m2':(total-inside)*dx*dy,
              'mirror_asymmetry_fraction':sum((a^c).bit_count() for a,c in zip(rows,reflected))/max(1,union),'frame_clipped':state['clipped']}
        if include_masks:item['mask_rows_hex']=[format(v,'x') for v in rows]
        result[view]=item
    cancelled()
    return {'method':'ORTHOGRAPHIC_BLADE_TRIANGLE_PIXEL_CENTERS_V1','resolution':resolution,'projected_triangles':work,'views':result,
            'source_model_sha256':layout['source_model_sha256'],'foliage_sha256':b.digest(foliage.compact(layout)),
            'scope':'Opaque blade geometry only in root-local metres; excludes wood/petioles, material alpha/translucency, lighting and perspective. Pixel-center estimate may miss subpixel blades; compare fixed resolution/frame and inspect higher resolution. Not optical leaf-area index, biological validation or render overdraw.'}
