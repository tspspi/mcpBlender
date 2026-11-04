"""Grid-independent leaf priorities and streaming multigrid quality checks."""
import hashlib
import math
import sys
from . import botany,foliage,foliage_coverage as coverage

METHOD='AREA_PRIORITY_MULTIGRID_V2'
LEGACY='PIXEL_CENTER_GREEDY_V1'


def grids(resolution):
    fine=min(256,resolution*2)
    result=[{'name':'BASE','resolution':resolution,'sample_shift':[0.,0.]}]
    if fine!=resolution:result.append({'name':'FINE','resolution':fine,'sample_shift':[0.,0.]})
    return result+[{'name':'SHIFTED','resolution':fine,'sample_shift':[.25,-.25]}]


def mask_estimate(levels,resolution,views):
    configs=grids(resolution)
    return ((levels+1)*views*sum(sys.getsizeof(1<<(g['resolution']**2-1)) for g in configs)
            +2*sys.getsizeof(1<<(max(g['resolution'] for g in configs)**2-1))
            +sys.getsizeof([0]*256)+256*sys.getsizeof(1<<255)+4096)


def prototypes(layout):
    result=[]
    for index in range(layout['recipe']['variants']):
        mesh=foliage.leaf_mesh(foliage.variant_shape(layout['recipe'],index));triangles=[]
        for face,part in zip(mesh['faces'],mesh['parts']):
            if part==0:triangles.extend((face[0],face[j],face[j+1]) for j in range(1,len(face)-1))
        used=sorted({i for t in triangles for i in t});remap={old:new for new,old in enumerate(used)};area=[0.,0.,0.]
        for a,b,c in triangles:
            p,q,r=[mesh['vertices'][i] for i in (a,b,c)];u=[q[i]-p[i] for i in range(3)];v=[r[i]-p[i] for i in range(3)]
            vector=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
            for i in range(3):area[i]+=vector[i]/2
        result.append({'vertices':[mesh['vertices'][i] for i in used],
                       'triangles':[tuple(remap[i] for i in t) for t in triangles],'area_vector':area})
    return result


def order(layout,views,shapes,max_evaluations,cancelled,progress):
    leaves=layout['leaves']
    if len(leaves)>max_evaluations:raise ValueError('Vegetation LOD selection evaluation budget exceeded')
    ranked=[];normals=[next(i for i in range(3) if i not in coverage.VIEWS[v]) for v in views]
    for index,leaf in enumerate(leaves):
        if index%256==0:cancelled();progress({'phase':'ranking vegetation leaves by geometric area','completed':index,'total':len(leaves)})
        rotation=coverage.rotation(leaf['rotation']);area=shapes[leaf['variant']]['area_vector']
        # Signed blade-area vector is a ranking heuristic, not the quality proof.
        importance=leaf['scale']**2*sum(abs(sum(rotation[i][j]*area[j] for j in range(3))) for i in normals)
        quantum=max(1,round(importance*10**12))
        ticket=int.from_bytes(hashlib.blake2b(leaf['id'].encode(),digest_size=8,person=b'mcpbl-lod-v2').digest(),'big')
        ranked.append(((ticket<<32)//quantum,leaf['id'],index))
    if len({v[1] for v in ranked})!=len(leaves):raise ValueError('Vegetation LOD needs distinct leaf IDs')
    ranked.sort();return [v[2] for v in ranked]


def masks(model,layout,levels,resolution,views,margin,max_work,max_bytes,max_evaluations,cancelled,progress):
    shapes=prototypes(layout);configs=grids(resolution);count=len(layout['leaves'])
    work=sum(len(shapes[l['variant']]['triangles']) for l in layout['leaves'])*len(views)*len(configs)
    estimate=mask_estimate(len(levels),resolution,len(views))
    if work>max_work or estimate>max_bytes:raise ValueError('Vegetation LOD multigrid projected-triangle/mask memory budget exceeded')
    ranked=order(layout,views,shapes,max_evaluations,cancelled,progress);rank={i:r for r,i in enumerate(ranked)}
    budgets=[l['leaf_budget'] for l in levels];selected=[sorted(ranked[:n]) for n in budgets]
    frame=coverage.analyze(model,layout|{'leaves':[]},resolution,views,margin,min(max_work,100000000),True,cancelled=cancelled)
    buffers=[[[0]*(len(levels)+1) for _ in views] for _ in configs];clipped=False
    for index,leaf in enumerate(layout['leaves']):
        if index%128==0:cancelled();progress({'phase':'projecting independent vegetation quality grids','completed':index,'total':count,'grids':configs,'projected_triangles':work})
        shape=shapes[leaf['variant']];rotation=coverage.rotation(leaf['rotation'])
        transformed=[tuple(leaf['position'][a]+leaf['scale']*sum(rotation[a][j]*v[j] for j in range(3)) for a in range(3)) for v in shape['vertices']]
        members=[i+1 for i,n in enumerate(budgets) if rank[index]<n]
        for vi,view in enumerate(views):
            f=frame['views'][view];axes=f['axes'];low=f['frame_min_m'];width=[a-b for a,b in zip(f['frame_max_m'],low)]
            normalized=[tuple((p[a]-low[k])/width[k] for k,a in enumerate(axes)) for p in transformed]
            if any(value<0 or value>1 for p in normalized for value in p):clipped=True
            bounds=[(min(p[k] for p in normalized),max(p[k] for p in normalized)) for k in range(2)]
            for gi,g in enumerate(configs):
                size=g['resolution'];shift=g['sample_shift']
                # If even the whole blade box contains no grid sample, none of
                # its triangles can contribute. This is an exact broad phase.
                if any(max(0,math.ceil(lo*size-shift[k]-.5))>min(size-1,math.floor(hi*size-shift[k]-.5)) for k,(lo,hi) in enumerate(bounds)):continue
                points=[tuple(p[k]*size-shift[k] for k in range(2)) for p in normalized];rows=[0]*size
                for triangle in shape['triangles']:coverage.raster_triangle(rows,[points[i] for i in triangle],size)
                bits=sum(row<<(r*size) for r,row in enumerate(rows));buffers[gi][vi][0]|=bits
                for member in members:buffers[gi][vi][member]|=bits
    return selected,buffers,configs,frame,work,estimate,clipped
