"""Engine-independent botanical mesh/instance semantic correspondence."""
import json
from pathlib import Path
from . import botany,foliage,wind,attribute_glb
from .lod_files import file_hash

FORMAT='mcpblender-botanical-wind-bundle-v1'
BRANCH_FIELDS=(('wind_branch_index','INT','wind.branch_index'),
 ('wind_parent_index','INT','wind.parent_branch_index'),
 ('wind_axis_anchor','FLOAT_VECTOR','wind.axis_anchor_local_m'),
 ('wind_segment_pivot','FLOAT_VECTOR','wind.segment_pivot_local_m'),
 ('wind_phase','FLOAT','wind.phase_radians'),('wind_stiffness','FLOAT','wind.stiffness'),
 ('wind_weight','FLOAT','wind.bend_weight'))


def branch_fields(model,positions,indices):
    if len(positions)!=len(indices):raise ValueError('Branch field cardinality mismatch')
    branches=model['branches'];lookup={v['id']:i for i,v in enumerate(branches)};result={name:[] for name,_,_ in BRANCH_FIELDS}
    for position,index in zip(positions,indices):
        if type(index)!=int or not 0<=index<len(branches):raise ValueError('Invalid botanical branch index')
        b=branches[index];row=(index,lookup[b['parent_id']] if b['parent_id'] else -1,b['anchor'],b['start'],b['phase'],b['stiffness'],min(1,max(0,position[2]/model['recipe']['height'])))
        for (name,_,_),value in zip(BRANCH_FIELDS,row):result[name].append(value)
    return result


def semantics(model,population,info,materials=None,secondary_uv=None):
    result={'format':FORMAT,'model':model,'foliage':population,'wind':info,
            'coordinates':{'canonical':'right-handed Z-up metres','mesh_vectors':'raw canonical root-local metre vectors; no glTF axis conversion in custom lanes',
             'mesh_geometry':'GLB +Y-up local positions; GLB world transforms include metre normalization',
             'instances':'leaf position/root-local metre, rotation XYZ radians, positive scalar scale, zero-based template variant; apply wind.placement after local instance transform',
             'axis_anchor':'first segment attachment of the branch axis','segment_pivot':'individual segment start; this is the hierarchical solver pivot',
             'leaf_flutter':'rigid template local X rotation after branch attachment rotation; phase/flutter are per-instance, not per-template'},
            'scope':'Shared static template GLBs plus branch-field GLBs and full semantic hierarchy/leaf attachment table. No engine shader, EXT_mesh_gpu_instancing, continuous native animation or optical equivalence.'}

    if materials is not None:result['materials']=materials
    if secondary_uv is not None:result['secondary_uv']=secondary_uv
    return result


def files(root):
    root=Path(root);rows=[]
    if root.is_symlink() or not root.is_dir():raise ValueError('Botanical bundle must be a local directory')
    total=0
    for scanned,path in enumerate(root.rglob('*')):
        if scanned>=64:raise ValueError('Botanical member traversal budget exceeded')
        if path.is_symlink():raise ValueError('Symlinks are not botanical bundle members')
        if path.is_dir():continue
        if not path.is_file():raise ValueError('Nonregular botanical bundle member')
        if path.relative_to(root).as_posix()=='manifest.json':continue
        if len(rows)>=32:raise ValueError('Botanical bundle file budget exceeded')
        size=path.stat().st_size;total+=size
        if total>512*1024**2:raise ValueError('Botanical bundle exceeds byte budget')
        rows.append({'path':path.relative_to(root).as_posix(),'bytes':size,'sha256':file_hash(path)})
    return sorted(rows,key=lambda r:r['path'])


def read(path,limit=256*1024**2):
    if path.stat().st_size>limit:raise ValueError('Botanical JSON exceeds validation budget')
    return json.loads(path.read_text())


def verify_asset(folder,model,population,asset,*,cancelled=None):
    cancel=cancelled or (lambda:None);folder=Path(folder)
    cancel();manifest=read(folder/'manifest.json');witness=manifest['witness']
    if manifest.get('format')!=attribute_glb.FORMAT:raise ValueError('Invalid botanical numeric sub-bundle')
    proof=attribute_glb.verify(folder/'asset.glb',witness,cancelled=cancel)
    if proof!=manifest['proof']:raise ValueError('Botanical mesh proof changed')
    mapping=manifest['source']['mapping'];by_name={m['semantic']:m for m in mapping};lanes={f['semantic']:f['values'] for f in witness['fields']}
    def row(semantic,index):return [lanes[lane][index][0] for lane in by_name[semantic]['lanes']]
    if asset in {'wood','shoots'}:
        if set(by_name)!={v[2] for v in BRANCH_FIELDS}:raise ValueError('Botanical branch mapping inventory changed')
        indices=[]
        for i in range(len(witness['positions'])):
            v=row('wind.branch_index',i)[0]
            if v!=int(v):raise ValueError('Noninteger encoded branch index')
            indices.append(int(v))
        expected=branch_fields(model,witness['positions'],indices)
        for name,kind,semantic in BRANCH_FIELDS:
            for i,value in enumerate(expected[name]):
                if i%1024==0:cancel()
                wanted=value if kind=='FLOAT_VECTOR' else [value]
                if not attribute_glb.close(row(semantic,i),wanted,1e-7):raise ValueError('Encoded botanical semantic differs from hierarchy: '+semantic)
    else:
        if set(by_name)!={'template.vertex_index'}:raise ValueError('Leaf template mapping changed')
        variant=int(asset.split('-')[1]);spec=foliage.leaf_mesh(foliage.variant_shape(population['recipe'],variant))
        for i,p in enumerate(witness['positions']):
            index=row('template.vertex_index',i)[0]
            if index!=int(index) or not 0<=index<len(spec['vertices']) or not attribute_glb.close(p,spec['vertices'][int(index)],1e-7):raise ValueError('Leaf template differs from canonical prototype')
    return {'proof':proof,'branch_indices':sorted(set(indices)) if asset in {'wood','shoots'} else None,'witness':witness,'mapping':mapping}


def validate(root,*,cancelled=None):
    cancel=cancelled or (lambda:None);root=Path(root)
    if (root/'manifest.json').is_symlink():raise ValueError('Symlinked botanical manifest refused')
    inventory=files(root);record=read(root/'manifest.json')
    if record.get('format')!=FORMAT or record.get('files')!=inventory:raise ValueError('Botanical bundle inventory/hash mismatch')
    if sum(r['bytes'] for r in inventory)>512*1024**2:raise ValueError('Botanical bundle exceeds validation byte budget')
    data=read(root/'semantics.json');model=data['model'];botany.validate(model)
    if data.get('format')!=FORMAT:raise ValueError('Unsupported botanical semantic format')
    info=data['wind'];cfg=wind.recipe(info['wind']);where=wind.placement(info['placement'])
    if info.get('format')!=wind.FORMAT or info.get('solver')!=wind.SOLVER or info.get('wind_sha256')!=botany.digest({k:v for k,v in info.items() if k!='wind_sha256'}):raise ValueError('Wind semantic solver/version/guard binding mismatch')
    source=record['source']
    if source.get('wind')!=info or source.get('source_guard')!=info['tree_sha256'] or source.get('export_sha256')!=botany.digest({k:v for k,v in source.items() if k!='export_sha256'}):raise ValueError('Botanical source/plan binding mismatch')
    if info['field']!=wind.field(cfg) or info['model_sha256']!=botany.digest(model):raise ValueError('Wind field/model binding mismatch')
    population=data['foliage']
    if info['foliage_sha256']!=(botany.digest(foliage.compact(population)) if population else None):raise ValueError('Foliage compact binding mismatch')
    if population:
        expected=foliage.generate(model,population['recipe'],cancelled=cancel)
        if botany.digest(population)!=botany.digest(expected):raise ValueError('Foliage instance attachments differ from the canonical seeded layout')
    if data!=semantics(model,population,info,data.get('materials'),data.get('secondary_uv')):raise ValueError('Botanical semantic coordinate contract changed')
    if source.get('secondary_uv')!=data.get('secondary_uv'):raise ValueError('Botanical secondary UV source binding changed')
    expected_assets=['wood']+(['shoots']+[f'leaf-{i}' for i in range(population['recipe']['variants'])] if population and population['leaves'] else [])
    if record.get('assets')!=expected_assets:raise ValueError('Botanical asset inventory differs from semantic population')
    expected_paths={'semantics.json'}|{a+'/'+name for a in expected_assets for name in ('asset.glb','manifest.json')}
    if {r['path'] for r in inventory}!=expected_paths:raise ValueError('Unexpected botanical bundle members')
    if data.get('materials'):
        from . import vegetation_materials
        vegetation_materials.validate(data['materials'])
        if source.get('materials')!=data['materials']:raise ValueError('Material contract differs from botanical export binding')
        delivery={a:vegetation_materials.delivery(root/a/'asset.glb',data['materials'],a) for a in expected_assets}
        if record.get('material_delivery')!=delivery:raise ValueError('Encoded botanical material delivery changed')
    proofs=[{'asset':asset,'proof':verify_asset(root/asset,model,population,asset,cancelled=cancel)['proof']} for asset in expected_assets]
    if 'secondary_uv' in data:
        from . import vegetation_uv
        vegetation_uv.verify(root,data['secondary_uv'],expected_assets)
    return {'format':FORMAT,'assets':proofs,'branches':len(model['branches']),'leaf_instances':len(population['leaves']) if population else 0,
            'shared_leaf_templates':population['recipe']['variants'] if population and population['leaves'] else 0,
            'semantic_sha256':botany.digest(data),'scope':data['scope']}
