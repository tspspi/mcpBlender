"""Independent shared-template vegetation LOD bundle validation (no bpy)."""
from pathlib import Path
from . import botany,foliage,wind,vegetation_lod as lod,vegetation_interchange as common,attribute_glb
from .skin_glb import point

FORMAT='mcpblender-vegetation-lod-bundle-v1'


def full_level(model,population,sides):
    return {'leaf_indices':list(range(len(population['leaves']))),'branch_indices':list(range(len(model['branches']))),
            'shoot_indices':list(range(len(population['shoots']))),'options':{'radial_sides':sides}}


def check_wind(info,model,population):
    if info.get('format')!=wind.FORMAT or info.get('solver')!=wind.SOLVER or info.get('wind_sha256')!=botany.digest({k:v for k,v in info.items() if k!='wind_sha256'}):raise ValueError('LOD wind solver/version/guard binding mismatch')
    if info['model_sha256']!=botany.digest(model) or info['foliage_sha256']!=botany.digest(foliage.compact(population)) or info['field']!=wind.field(wind.recipe(info['wind'])):raise ValueError('LOD model/foliage/wind binding mismatch')
    return wind.placement(info['placement'])


def validate(root,*,cancelled=None,progress=None):
    cancel=cancelled or (lambda:None);report=progress or (lambda v:None);root=Path(root)
    inventory=common.files(root);record=common.read(root/'manifest.json')
    if record.get('format')!=FORMAT or inventory!=record.get('files'):raise ValueError('LOD bundle inventory/hash mismatch')
    if sum(r['bytes'] for r in inventory)+(root/'manifest.json').stat().st_size>512*1024**2:raise ValueError('LOD bundle exceeds total byte budget')
    data=common.read(root/'semantics.json')
    if record.get('placement_mode',data['placement_mode'])!=data['placement_mode']:raise ValueError('LOD placement binding differs from job manifest')
    model=data['model'];population=data['foliage'];selection=data['selection'];botany.validate(model)
    if data.get('format')!=FORMAT or selection.get('format')!=lod.FORMAT:raise ValueError('Unsupported LOD semantic format')
    if selection['plan_sha256']!=botany.digest({k:v for k,v in selection.items() if k!='plan_sha256'}):raise ValueError('LOD selection content guard changed')
    regenerated=foliage.generate(model,population['recipe'],cancelled=cancel)
    if botany.digest(regenerated)!=botany.digest(population):raise ValueError('LOD canonical attachment table changed')
    source_where=check_wind(data['source_wind'],model,population);where=check_wind(data['wind'],model,population)
    if data['placement_mode'] not in {'SOURCE','DISPLAYED'}:raise ValueError('Invalid LOD placement mode')
    desired=source_where if data['placement_mode']=='SOURCE' else wind.placement(data['displayed_placement'])
    for p in ((0,0,0),(1,0,0),(0,1,0),(0,0,1)):
        if not attribute_glb.close(wind.world(where,p),wind.world(desired,p),2e-6):raise ValueError('LOD delivery placement does not match declared mode')
    sides=data['source_radial_sides']
    if type(sides)!=int or not 5<=sides<=16:raise ValueError('Invalid LOD0 radial sides')
    canonical=lod.plan(model,population,[v['options'] for v in selection['levels']],source_sides=sides,
        resolution=selection['resolution'],views=selection['views'],margin=selection['margin'],silhouette_weight=selection['silhouette_weight'],
        max_projected_triangles=100000000,max_mask_bytes=1024**3,max_gain_evaluations=5000000,cancelled=cancel,progress=report)
    # Host-specific memory accounting is not a semantic selection difference.
    omitted={'mask_payload_estimated_bytes','plan_sha256'}
    if {k:v for k,v in canonical.items() if k not in omitted}!={k:v for k,v in selection.items() if k not in omitted} or not canonical['valid']:raise ValueError('LOD selection/coverage plan differs from canonical recomputation')
    levels=[full_level(model,population,sides),*selection['levels']]
    if len(data['levels'])!=len(levels):raise ValueError('LOD level inventory changed')
    assets=[];proofs=[];reports=[]
    template_triangles=[foliage.leaf_mesh(foliage.variant_shape(population['recipe'],i))['triangles'] for i in range(population['recipe']['variants'])]
    def placement(witness,template=False):
        unit=witness['scene_unit_scale'];matrix=witness['matrix_world']
        for p in ((0,0,0),(1,0,0),(0,1,0),(0,0,1)):
            actual=[v*unit for v in point(matrix,p)];expected=p if template else wind.world(where,p)
            if not attribute_glb.close(actual,expected,2e-6):raise ValueError('Encoded LOD asset placement differs from semantic metre placement')
    for number,(saved,level) in enumerate(zip(data['levels'],levels)):
        cancel()
        if saved!={'level':number,'wood':f'lod-{number}-wood','shoots':f'lod-{number}-shoots','leaf_indices':level['leaf_indices'],'branch_indices':level['branch_indices'],'shoot_indices':level['shoot_indices']}:raise ValueError('LOD retained leaf/branch/shoot identity mapping changed')
        branches=set(level['branch_indices']);lookup={v['id']:i for i,v in enumerate(model['branches'])}
        if any(model['branches'][i]['parent_id'] and lookup[model['branches'][i]['parent_id']] not in branches for i in branches):raise ValueError('LOD branch ancestry is not closed')
        for role in ('wood','shoots'):
            asset=saved[role];assets.append(asset);result=common.verify_asset(root/asset,model,population,role,cancelled=cancel);placement(result['witness'])
            expected=branches if role=='wood' else {lookup[population['shoots'][i]['parent_branch_id']] for i in level['shoot_indices']}
            if set(result['branch_indices'])!=expected:raise ValueError('Encoded LOD branch indices differ from retained hierarchy')
            triangles=lod.wood_triangles(model,level['branch_indices'],level['options']['radial_sides']) if role=='wood' else 12*len(level['shoot_indices'])
            if result['proof']['triangles']!=triangles:raise ValueError('Encoded LOD triangle budget/count differs from plan')
            proofs.append({'asset':asset,'proof':result['proof']})
        reports.append({'level':number,'leaf_instances':len(level['leaf_indices']),'branches':len(branches),
                        'expanded_triangles':lod.wood_triangles(model,level['branch_indices'],level['options']['radial_sides'])+12*len(level['shoot_indices'])+sum(template_triangles[population['leaves'][i]['variant']] for i in level['leaf_indices'])})
        report({'phase':'validated LOD branch geometry','level':number})
    templates=[f'leaf-{i}' for i in range(population['recipe']['variants'])]
    if data['templates']!=templates:raise ValueError('Shared LOD template inventory changed')
    for asset in templates:
        cancel();assets.append(asset);result=common.verify_asset(root/asset,model,population,asset,cancelled=cancel);placement(result['witness'],True);proofs.append({'asset':asset,'proof':result['proof']})
    if record.get('assets')!=assets or {r['path'] for r in inventory}!={'semantics.json'}|{a+'/'+n for a in assets for n in ('asset.glb','manifest.json')}:raise ValueError('Unexpected/missing LOD bundle assets')
    if data['coordinates']!=common.semantics(model,population,data['wind'])['coordinates']:raise ValueError('LOD coordinate contract changed')
    if data.get('materials'):
        from . import vegetation_materials
        vegetation_materials.validate(data['materials'])
        if record.get('materials_sha256')!=data['materials']['materials_sha256']:raise ValueError('LOD material source binding changed')
        if record.get('material_delivery')!={a:vegetation_materials.delivery(root/a/'asset.glb',data['materials'],a) for a in assets}:raise ValueError('Encoded LOD material delivery changed')
    if data.get('baked_materials'):
        from . import vegetation_adoption
        vegetation_adoption.verify(root,data['baked_materials'],assets,secondary_uv=data.get('secondary_uv',{}))
    if 'secondary_uv' in data:
        from . import vegetation_uv
        vegetation_uv.verify(root,data['secondary_uv'],assets)
    return {'format':FORMAT,'levels':reports,'shared_leaf_templates':len(templates),'assets':proofs,'placement_mode':data['placement_mode'],
            'semantic_sha256':botany.digest(data),'scope':'Independent mesh/field/UV/metre placement, canonical hierarchy/selection/instance correspondence. No engine shader, animated LOD/optical or GPU runtime qualification.'}
