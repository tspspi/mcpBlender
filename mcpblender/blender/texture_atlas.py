"""Verified texture-bake inputs and guarded atlas plans."""
from pathlib import Path
from mcpblender import atlas_layout,botany,atlas_pixels
from mcpblender.texture_files import inventory,verify_steps,read_json,MARKER,validate_map_policy
from mcpblender.package_files import image_info

COMMANDS={'inspect_texture_atlas','build_texture_atlas'}
MAPS={'BASE_COLOR','NORMAL','ROUGHNESS','METALLIC','AO','ALPHA','EMISSION'}


def inspect(p,*,cancelled=None,progress=None):
    from .bridge import check_cancelled as native_cancel,report_progress as native_progress
    check_cancelled=cancelled or native_cancel;report_progress=progress or native_progress
    entries=[];bindings=[];total=0
    for entry in p['entries']:
        check_cancelled();root=Path(entry['directory']);rows,_=inventory(root);total+=sum(r['bytes'] for r in rows)
        if total>p['max_input_bytes']:raise ValueError('Atlas source bundles exceed max_input_bytes')
        record=read_json(root/MARKER);saved=read_json(root/'manifest.json')
        if record.get('kind')!='mcpblender-texture-job' or record.get('version')!=1 or record.get('state')!='succeeded' or saved.get('atlas') is not None:raise ValueError('Atlas inputs require successful original texture-bake bundles')
        if any(saved.get(k)!=record.get(k) for k in ('job_id','source')) or saved.get('material_adapters',[])!=record.get('material_adapters',[]):raise ValueError('Atlas source manifest binding mismatch')
        map_policy=validate_map_policy(record,saved,read_json(root/'job.json'))
        for progress in verify_steps(root,saved['files']):check_cancelled();report_progress(progress|{'input':entry['id']})
        maps=sorted(saved['maps'],key=lambda m:m['map'])
        if not maps or len(maps)>7 or len({m['map'] for m in maps})!=len(maps):raise ValueError('Invalid atlas source map inventory')
        dims=set()
        for m in maps:
            kind=m['map']
            if kind not in MAPS or m['path']!='textures/'+kind.lower()+'.png' or m['color_space']!=('sRGB' if kind in {'BASE_COLOR','EMISSION'} else 'Non-Color'):raise ValueError('Atlas source map profile differs from baked PBR')
            if type(m['width'])!=int or type(m['height'])!=int or not 32<=m['width']<=4096 or not 32<=m['height']<=4096 or m['width']*m['height']>4*1024**2 or (root/m['path']).stat().st_size>128*1024**2:raise ValueError('Atlas source map exceeds pixel/file budget')
            payload=(root/m['path']).read_bytes();info=image_info(payload,'image/png')
            if payload[24]!=8:raise ValueError('Atlas requires RGBA8 bake-map precision')
            if (info['width'],info['height'])!=(m['width'],m['height']):raise ValueError('Atlas source PNG dimensions differ from manifest')
            dims.add((m['width'],m['height']))
        if len(dims)!=1:raise ValueError('Each atlas entry needs matching map dimensions')
        w,h=next(iter(dims));entries.append({'id':entry['id'],'width':w,'height':h,'maps':[m['map'] for m in maps]})
        bindings.append({'id':entry['id'],'directory':str(root),'job_id':record['job_id'],'source':record['source'],
                         'asset_sha256':saved['asset_sha256'],'files':saved['files'],'material_adapters':saved.get('material_adapters',[])})
        if map_policy is not None:bindings[-1]['map_policy']=map_policy
    layout=atlas_layout.pack(entries,p['width'],p['height'],p['gutter'],p['max_texture_bytes'])
    plan={'layout':layout,'inputs':sorted(bindings,key=lambda e:e['id']),'pixel_copy_method':atlas_pixels.METHOD};signature=botany.digest(plan)
    return {'complete':True,'bake_sha256':signature,'atlas_sha256':signature,'atlas':plan,'input_bytes':total,
            'estimated_output_bytes':total+layout['base_rgba8_bytes']*3+16*1024**2,
            'material_adapters':[a for e in bindings for a in e['material_adapters']],
            'scope':'File/hash/map/layout inspection. The isolated worker also checks actual native asset bindings, single UVs, positive transforms and matching untextured PBR constants before assembly.'}


def guard(p,**callbacks):
    result=inspect(p,**callbacks)
    if result['atlas_sha256']!=p['expected_bake']:raise ValueError('Texture atlas fingerprint is stale; inspect_texture_atlas again')
    return result


def dispatch(command,p):
    if command=='inspect_texture_atlas':return inspect(p)
    if any(Path(p['directory']).resolve().is_relative_to(Path(e['directory']).resolve()) for e in p['entries']):raise ValueError('Atlas output must be outside source bundles')
    from .textures import bake
    return bake(p|{'_texture_pipeline':'ATLAS','expected_bake':p['expected_atlas']})
