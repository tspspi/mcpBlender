"""Deterministic coverage-scored nested leaf/skeleton LOD plans, no Blender."""
import heapq
import math
import sys
from . import botany as b,foliage,foliage_coverage as coverage

FORMAT='mcpblender-vegetation-lod-v1'


def mask_estimate(count,resolution,views):
    return count*(views*sys.getsizeof(1<<(resolution*resolution-1))+sys.getsizeof([0]*views)+16)


def mask_rows(bits,resolution):return [(bits>>(r*resolution))&((1<<resolution)-1) for r in range(resolution)]


def boundary(bits,resolution):
    rows=mask_rows(bits,resolution);limit=(1<<resolution)-1;result=0
    for r,row in enumerate(rows):
        inside=(row<<1)&(row>>1)&(rows[r-1] if r else 0)&(rows[r+1] if r+1<resolution else 0)
        result|=(row&~inside&limit)<<(r*resolution)
    return result


def masks(model,layout,resolution,views,margin,max_work,max_mask_bytes,cancelled,progress):
    empty=layout|{'leaves':[]};frame=coverage.analyze(model,empty,resolution,views,margin,max_work,True,cancelled=cancelled)
    prototypes=[]
    for i in range(layout['recipe']['variants']):
        mesh=foliage.leaf_mesh(foliage.variant_shape(layout['recipe'],i));triangles=[]
        for face,part in zip(mesh['faces'],mesh['parts']):
            if part==0:triangles.extend((face[0],face[j],face[j+1]) for j in range(1,len(face)-1))
        prototypes.append((mesh['vertices'],triangles,sorted({i for t in triangles for i in t})))
    work=sum(len(prototypes[l['variant']][1]) for l in layout['leaves'])*len(views)
    estimate=mask_estimate(len(layout['leaves']),resolution,len(views))
    if work>max_work or estimate>max_mask_bytes:raise ValueError('Vegetation LOD projected-triangle/mask memory budget exceeded')
    result=[];unions=[0]*len(views);clipped=False
    for index,leaf in enumerate(layout['leaves']):
        if index%128==0:cancelled();progress({'phase':'projecting vegetation LOD leaves','completed':index,'total':len(layout['leaves'])})
        vertices,triangles,used=prototypes[leaf['variant']];rotation=coverage.rotation(leaf['rotation'])
        transformed=[tuple(leaf['position'][a]+leaf['scale']*sum(rotation[a][j]*v[j] for j in range(3)) for a in range(3)) for v in vertices];item=[]
        for vi,view in enumerate(views):
            f=frame['views'][view];axes=f['axes'];low=f['frame_min_m'];step=f['pixel_size_m'];rows=[0]*resolution
            points=[tuple((p[a]-low[k])/step[k] for k,a in enumerate(axes)) for p in transformed]
            if any(value<0 or value>resolution for i in used for value in points[i]):clipped=True
            for triangle in triangles:coverage.raster_triangle(rows,[points[i] for i in triangle],resolution)
            bits=sum(row<<(r*resolution) for r,row in enumerate(rows));item.append(bits);unions[vi]|=bits
        result.append(item)
    return result,unions,frame,work,estimate,clipped


def wood_triangles(model,indices,sides):
    branches=model['branches'];selected=set(indices);lookup={x['id']:i for i,x in enumerate(branches)}
    starts=0;continued=set()
    for i in indices:
        branch=branches[i];parent=lookup.get(branch['parent_id'])
        if parent in selected and branches[parent]['axis_id']==branch['axis_id']:continued.add(parent)
        else:starts+=1
    return len(indices)*sides*2+(starts+len(indices)-len(continued))*(sides-2)


def _legacy_plan(model,layout,levels,*,source_sides=8,resolution=128,views=('FRONT','SIDE','TOP'),margin=2.5,
         silhouette_weight=4,max_projected_triangles=60000000,max_mask_bytes=256*1024**2,max_gain_evaluations=2000000,
         cancelled=lambda:None,progress=lambda v:None):
    b.validate(model)
    if not layout or not layout['leaves']:raise ValueError('Vegetation LOD planning requires populated foliage')
    if not isinstance(levels,list) or not 1<=len(levels)<=4:raise ValueError('Choose one to four reduced vegetation LOD levels')
    if type(source_sides)!=int or not 5<=source_sides<=16 or type(silhouette_weight)!=int or not 1<=silhouette_weight<=16:raise ValueError('Invalid radial sides or silhouette weight')
    previous=(len(layout['leaves'])+1,source_sides,0.);normalized=[]
    for value in levels:
        if set(value)-{'leaf_budget','radial_sides','min_branch_radius_m','max_coverage_loss','max_silhouette_loss','triangle_budget'}:raise ValueError('Unknown vegetation LOD option')
        level={'radial_sides':5,'min_branch_radius_m':.02,'max_coverage_loss':.25,'max_silhouette_loss':.25,'triangle_budget':30000000}|value
        budget=level.get('leaf_budget');sides=level['radial_sides'];radius=level['min_branch_radius_m']
        if type(budget)!=int or not 1<=budget<=len(layout['leaves']) or budget>=previous[0]:raise ValueError('Leaf budgets must decrease and fit the source population')
        if type(sides)!=int or not 5<=sides<=previous[1] or type(radius) not in (int,float) or not math.isfinite(radius) or radius<previous[2] or radius>10:raise ValueError('Radial sides must not increase; branch radius thresholds must not decrease')
        if type(level['triangle_budget'])!=int or not 1<=level['triangle_budget']<=30000000:raise ValueError('Invalid expanded triangle budget')
        for key in ('max_coverage_loss','max_silhouette_loss'):
            if type(level[key]) not in (int,float) or not math.isfinite(level[key]) or not 0<=level[key]<=1:raise ValueError('Invalid coverage loss budget')
        for key in ('min_branch_radius_m','max_coverage_loss','max_silhouette_loss'):level[key]=float(level[key])
        previous=(budget,sides,radius);normalized.append(level)
    leaf_masks,source_masks,frame,work,mask_bytes,clipped=masks(model,layout,resolution,views,margin,max_projected_triangles,max_mask_bytes,cancelled,progress)
    edges=[boundary(bits,resolution) for bits in source_masks];union=[0]*len(views);evaluations=0
    def score(index):
        nonlocal evaluations
        evaluations+=1
        if evaluations>max_gain_evaluations:raise ValueError('Vegetation LOD coverage-gain evaluation budget exceeded')
        if evaluations%256==0:cancelled()
        return sum((bits&~current).bit_count()+(silhouette_weight-1)*(bits&edge&~current).bit_count() for bits,edge,current in zip(leaf_masks[index],edges,union))
    heap=[(-score(i),leaf['id'],i) for i,leaf in enumerate(layout['leaves'])];heapq.heapify(heap);chosen=[]
    targets={v['leaf_budget'] for v in normalized};snapshots={}
    while len(chosen)<max(targets):
        negative,stable,index=heapq.heappop(heap);gain=score(index)
        if heap and (-gain,stable,index)>heap[0]:heapq.heappush(heap,(-gain,stable,index));continue
        chosen.append(index)
        for v,bits in enumerate(leaf_masks[index]):union[v]|=bits
        if len(chosen)%128==0:progress({'phase':'selecting nested vegetation LOD leaves','completed':len(chosen),'total':max(targets),'gain_evaluations':evaluations})
        if len(chosen) in targets:snapshots[len(chosen)]=(sorted(chosen),list(union))
    branches=model['branches'];lookup={v['id']:i for i,v in enumerate(branches)};prototype_triangles=[foliage.leaf_mesh(foliage.variant_shape(layout['recipe'],i))['triangles'] for i in range(layout['recipe']['variants'])]
    reports=[]
    for level in normalized:
        cancelled();indices,bits=snapshots[level['leaf_budget']];selected={i for i,v in enumerate(branches) if v['radius_start']>=level['min_branch_radius_m']};selected.add(0)
        selected.update(layout['leaves'][i]['parent_branch_index'] for i in indices)
        for i in list(selected):
            while branches[i]['parent_id']:
                i=lookup[branches[i]['parent_id']]
                if i in selected:break
                selected.add(i)
        selected=sorted(selected);shoots=sorted({layout['leaves'][i]['shoot_index'] for i in indices});quality={}
        for view,source,outline,target in zip(views,source_masks,edges,bits):
            quality[view]={'source_pixels':source.bit_count(),'retained_pixels':target.bit_count(),
                           'coverage_loss':(source&~target).bit_count()/max(1,source.bit_count()),
                           'silhouette_loss':(outline&~target).bit_count()/max(1,outline.bit_count())}
        wood=wood_triangles(model,selected,level['radial_sides']);expanded_leaves=sum(prototype_triangles[layout['leaves'][i]['variant']] for i in indices);shoot_triangles=len(shoots)*12
        passed=not clipped and all(v['source_pixels']>0 and v['coverage_loss']<=level['max_coverage_loss'] and v['silhouette_loss']<=level['max_silhouette_loss'] for v in quality.values()) and wood+shoot_triangles+expanded_leaves<=level['triangle_budget']
        reports.append({'options':level,'leaf_indices':indices,'branch_indices':selected,'shoot_indices':shoots,'quality':quality,'passed':passed,
                        'triangles':{'wood':wood,'shoots':shoot_triangles,'expanded_leaves':expanded_leaves,'expanded_total':wood+shoot_triangles+expanded_leaves},
                        'selection_sha256':b.digest([layout['leaves'][i]['id'] for i in indices])})
    result={'format':FORMAT,'model_sha256':b.digest(model),'foliage_sha256':b.digest(foliage.compact(layout)),'levels':reports,
            'resolution':resolution,'views':list(views),'margin':float(margin),'silhouette_weight':silhouette_weight,'frame':{k:{a:v for a,v in f.items() if a in {'axes','frame_min_m','frame_max_m','pixel_size_m'}} for k,f in frame['views'].items()},
            'projected_triangles':work,'mask_payload_estimated_bytes':mask_bytes,'gain_evaluations':evaluations,'source_frame_clipped':clipped,
            'valid':all(r['passed'] for r in reports),'scope':'Nested greedy opaque blade pixel coverage in fixed root-local views. Retains ancestor-closed wood and canonical attachment IDs; no optical/lighting/perspective, collision, cards/impostors or runtime performance proof.'}
    return result|{'plan_sha256':b.digest(result)}


from . import vegetation_sampling as sampling


def quality(source,target,resolution):
    edge=boundary(source,resolution)
    return {'source_pixels':source.bit_count(),'retained_pixels':target.bit_count(),
            'coverage_loss':(source&~target).bit_count()/max(1,source.bit_count()),
            'silhouette_loss':(edge&~target).bit_count()/max(1,edge.bit_count())}


def plan(model,layout,levels,*,source_sides=8,resolution=128,views=('FRONT','SIDE','TOP'),margin=2.5,
         silhouette_weight=4,max_projected_triangles=60000000,max_mask_bytes=256*1024**2,max_gain_evaluations=2000000,
         sampling_method=sampling.METHOD,cancelled=lambda:None,progress=lambda v:None):
    options=dict(source_sides=source_sides,resolution=resolution,views=views,margin=margin,silhouette_weight=silhouette_weight,
                 max_projected_triangles=max_projected_triangles,max_mask_bytes=max_mask_bytes,max_gain_evaluations=max_gain_evaluations,cancelled=cancelled,progress=progress)
    if sampling_method==sampling.LEGACY:return _legacy_plan(model,layout,levels,**options)
    if sampling_method!=sampling.METHOD:raise ValueError('Unsupported vegetation LOD sampling method')
    # Reuse the legacy normalization/ancestry/triangle accounting, with projection
    # supplied from a bounded streaming pass; no legacy greedy selection is run.
    b.validate(model)
    if type(max_projected_triangles)!=int or not 1<=max_projected_triangles<=400000000:raise ValueError('Invalid vegetation LOD projected-triangle budget')
    if type(resolution)!=int or not 32<=resolution<=256 or not views or len(views)>3 or len(set(views))!=len(views) or any(v not in coverage.VIEWS for v in views):raise ValueError('Invalid vegetation LOD quality grids')
    if not math.isfinite(margin) or not 0<=margin<=5:raise ValueError('Invalid vegetation LOD margin')
    # Validate levels before any population projection. This shares the exact
    # normalization rules with old bundles through the helper below.
    normalized=normalize_levels(layout,levels,source_sides,silhouette_weight)
    indices,buffers,grids,frame,work,estimate,clipped=sampling.masks(model,layout,normalized,resolution,views,margin,max_projected_triangles,max_mask_bytes,max_gain_evaluations,cancelled,progress)
    branches=model['branches'];lookup={v['id']:i for i,v in enumerate(branches)}
    template_triangles=[foliage.leaf_mesh(foliage.variant_shape(layout['recipe'],i))['triangles'] for i in range(layout['recipe']['variants'])];reports=[]
    for number,(level,chosen) in enumerate(zip(normalized,indices)):
        cancelled();selected={i for i,v in enumerate(branches) if v['radius_start']>=level['min_branch_radius_m']};selected.add(0)
        selected.update(layout['leaves'][i]['parent_branch_index'] for i in chosen)
        for index in list(selected):
            while branches[index]['parent_id']:
                index=lookup[branches[index]['parent_id']]
                if index in selected:break
                selected.add(index)
        selected=sorted(selected);shoots=sorted({layout['leaves'][i]['shoot_index'] for i in chosen})
        all_quality={g['name']:{view:quality(buffers[gi][vi][0],buffers[gi][vi][number+1],g['resolution']) for vi,view in enumerate(views)} for gi,g in enumerate(grids)}
        wood=wood_triangles(model,selected,level['radial_sides']);leaf_triangles=sum(template_triangles[layout['leaves'][i]['variant']] for i in chosen);shoot_triangles=len(shoots)*12
        passed=not clipped and all(q['source_pixels']>0 and q['coverage_loss']<=level['max_coverage_loss'] and q['silhouette_loss']<=level['max_silhouette_loss'] for grid in all_quality.values() for q in grid.values()) and wood+shoot_triangles+leaf_triangles<=level['triangle_budget']
        reports.append({'options':level,'leaf_indices':chosen,'branch_indices':selected,'shoot_indices':shoots,'quality':all_quality['BASE'],
                        'validation_quality':{k:v for k,v in all_quality.items() if k!='BASE'},'passed':passed,
                        'triangles':{'wood':wood,'shoots':shoot_triangles,'expanded_leaves':leaf_triangles,'expanded_total':wood+shoot_triangles+leaf_triangles},
                        'selection_sha256':b.digest([layout['leaves'][i]['id'] for i in chosen])})
    result={'format':FORMAT,'sampling_method':sampling.METHOD,'quality_grids':grids,'model_sha256':b.digest(model),'foliage_sha256':b.digest(foliage.compact(layout)),
            'levels':reports,'resolution':resolution,'views':list(views),'margin':float(margin),'silhouette_weight':silhouette_weight,
            'frame':{k:{a:v for a,v in f.items() if a in {'axes','frame_min_m','frame_max_m','pixel_size_m'}} for k,f in frame['views'].items()},
            'projected_triangles':work,'mask_payload_estimated_bytes':estimate,'gain_evaluations':len(layout['leaves']),'source_frame_clipped':clipped,
            'valid':all(r['passed'] for r in reports),'scope':'Nested projected-area/hash priorities independent of raster grids. All base/finer/shifted opaque-blade pixel quality gates enforced; ancestor-closed canonical attachments. No optical, perspective, cards/impostors, animation or runtime performance certification.'}
    return result|{'plan_sha256':b.digest(result)}


def normalize_levels(layout,levels,source_sides,silhouette_weight):
    if not layout or not layout['leaves']:raise ValueError('Vegetation LOD planning requires populated foliage')
    if not isinstance(levels,list) or not 1<=len(levels)<=4:raise ValueError('Choose one to four reduced vegetation LOD levels')
    if type(source_sides)!=int or not 5<=source_sides<=16 or type(silhouette_weight)!=int or not 1<=silhouette_weight<=16:raise ValueError('Invalid radial sides or silhouette weight')
    previous=(len(layout['leaves'])+1,source_sides,0.);normalized=[]
    for value in levels:
        if set(value)-{'leaf_budget','radial_sides','min_branch_radius_m','max_coverage_loss','max_silhouette_loss','triangle_budget'}:raise ValueError('Unknown vegetation LOD option')
        level={'radial_sides':5,'min_branch_radius_m':.02,'max_coverage_loss':.25,'max_silhouette_loss':.25,'triangle_budget':30000000}|value
        budget=level.get('leaf_budget');sides=level['radial_sides'];radius=level['min_branch_radius_m']
        if type(budget)!=int or not 1<=budget<=len(layout['leaves']) or budget>=previous[0]:raise ValueError('Leaf budgets must decrease and fit the source population')
        if type(sides)!=int or not 5<=sides<=previous[1] or type(radius) not in (int,float) or not math.isfinite(radius) or radius<previous[2] or radius>10:raise ValueError('Radial sides must not increase; branch radius thresholds must not decrease')
        if type(level['triangle_budget'])!=int or not 1<=level['triangle_budget']<=30000000:raise ValueError('Invalid expanded triangle budget')
        for key in ('max_coverage_loss','max_silhouette_loss'):
            if type(level[key]) not in (int,float) or not math.isfinite(level[key]) or not 0<=level[key]<=1:raise ValueError('Invalid coverage loss budget')
        for key in ('min_branch_radius_m','max_coverage_loss','max_silhouette_loss'):level[key]=float(level[key])
        previous=(budget,sides,radius);normalized.append(level)
    return normalized
