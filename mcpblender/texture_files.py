"""Bounded and symlink-refusing texture bundle files."""
import hashlib
import os
import stat
from pathlib import Path

from .fluid_files import write_json, read_json, file_hash

MARKER='.mcpblender-texture-job.json'
EMISSION_ENCODING='COLOR_TIMES_STRENGTH_PNG8'
ROOT_FILES={MARKER,'source.blend','asset.blend','job.json','worker.log','result.json','manifest.json','source.blend@','asset.blend@'}
MAPS={'normal','ao','base_color','roughness','metallic','emission','alpha','coverage','uv_mask'}



def projected_map_policy(job):
    """Projected opacity is silhouette data; padding may extend other maps only."""
    if job.get('_texture_pipeline')=='ATLAS' or not job.get('sources') or 'ALPHA' not in job.get('maps',[]):return None
    margin=job.get('margin')
    if type(margin)!=int or not 0<=margin<=64:raise ValueError('Invalid projected map margin')
    return {'method':'PROJECTED_ALPHA_NO_EXTEND_V1','alpha_margin':0,'other_map_margin':margin}


def validate_map_policy(record,saved,job):
    """Keep legacy bundles readable; bind an explicit policy in all new witnesses."""
    import json
    policies=[v.get('map_policy') for v in (record,saved,job)]
    if all(v is None for v in policies):return None
    expected=projected_map_policy(job)
    canonical=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
    if expected is None or any(canonical(v)!=canonical(expected) for v in policies):raise ValueError('Texture map padding policy binding mismatch')
    maps=saved.get('maps',[])
    if not maps or len(maps)!=len(job['maps']) or {m.get('map') for m in maps}!=set(job['maps']):raise ValueError('Texture map padding inventory mismatch')
    for row in maps:
        margin=0 if row['map']=='ALPHA' else expected['other_map_margin']
        if type(row.get('bake_margin'))!=int or row['bake_margin']!=margin:raise ValueError('Texture map padding differs from declared policy')
    return expected

def bake_content(info,*,without_quality=False):
    """Canonical source content; preserve the original bake fingerprint recipe."""
    import copy
    result={k:copy.deepcopy(info[k]) for k in ('objects','uv_map','frame','subframe')}
    if 'thin_foliage_mode' in info:result['thin_foliage_mode']=info['thin_foliage_mode']
    if without_quality:
        for obj in result['objects']:obj.pop('texture_quality',None)
    return result


def bake_fingerprint(info,*,without_quality=False):
    import json
    return hashlib.sha256(json.dumps(bake_content(info,without_quality=without_quality),sort_keys=True,allow_nan=False).encode()).hexdigest()


def quality_binding(saved,job,initial_source):
    """Bind a policy-bearing bake to its unchanged preparation without replay."""
    if not job.get('quality'):
        if saved.get('texture_quality') is not None:raise ValueError('Unexpected texture quality report without a job policy')
        return initial_source,None
    content=saved.get('source_inspection');report=saved.get('texture_quality')
    if not isinstance(content,dict) or not isinstance(report,dict):raise ValueError('Quality bake lacks its source inspection witness; rebake')
    try:
        validate_quality_report(report)
        if bake_fingerprint(content,without_quality=True)!=initial_source:raise ValueError('Quality bake source differs from the unchanged preparation')
        if len(content['objects'])!=1 or content['objects'][0].get('role')!='target' or content['objects'][0].get('texture_quality')!=report:raise ValueError('Quality report differs from the guarded source witness')
        if report.get('policy')!=job['quality'] or report.get('complete') is not True or report.get('passed') is not True:raise ValueError('Complete passed job-bound texture quality required')
        if (report['policy']['width'],report['policy']['height'])!=(job['width'],job['height']) or job['margin']>report['policy']['padding_pixels']:raise ValueError('Texture quality dimensions or bake margin changed')
        return bake_fingerprint(content),report
    except (KeyError,TypeError) as e:raise ValueError('Invalid texture quality source witness') from e


def validate_quality_report(report):
    """Check a retained successful geometric report, without claiming a rerun."""
    import math
    try:
        policy=report['policy']
        if 'scene_unit_scale' in report and (type(report['scene_unit_scale']) not in (int,float) or not math.isfinite(report['scene_unit_scale']) or report['scene_unit_scale']<=0):raise ValueError('Invalid retained texture quality unit scale')
        integers={'width':(32,4096),'height':(32,4096),'mip_levels':(0,8),'min_chart_pixels':(1,1000000),'max_raster_tests':(1,200000000),'max_spacing_tests':(1,5000000)}
        for key,(low,high) in integers.items():
            if type(policy[key])!=int or not low<=policy[key]<=high:raise ValueError('Invalid retained texture quality policy')
        for key,high in (('min_texels_per_meter',1000000),('padding_pixels',64)):
            value=policy[key]
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=high:raise ValueError('Invalid retained texture quality threshold')
        if policy['width']*policy['height']>4*1024**2:raise ValueError('Invalid retained texture quality resolution')
        if report['complete'] is not True or report['passed'] is not True or report['out_of_tile'] is not False or report['degenerate_triangles']!=0 or report['low_density_triangles']!=0:raise ValueError('Successful geometric texture quality required')
        if not math.isfinite(report['minimum_directional_texels_per_meter']) or report['minimum_directional_texels_per_meter']<policy['min_texels_per_meter']:raise ValueError('Retained texture density did not pass')
        if report['overlap']['complete'] is not True or report['overlap']['face_pair_count']!=0:raise ValueError('Retained texture overlap did not pass')
        expected=[]
        for level in range(policy['mip_levels']+1):
            size=[max(1,policy['width']//2**level),max(1,policy['height']//2**level)];expected.append(size)
            if size==[1,1]:break
        if len(report['levels'])!=len(expected):raise ValueError('Retained texture mip footprint inventory changed')
        for i,(row,size) in enumerate(zip(report['levels'],expected)):
            coverage=row['coverage'];gap=row['spacing']
            if row['level']!=i or row['size']!=size or row['passed'] is not True or row['undersized_chart_count']!=0:raise ValueError('Retained texture mip footprint did not pass')
            if coverage['complete'] is not True or coverage['ambiguous_pixels']!=0 or coverage['minimum_covered_pixels']<policy['min_chart_pixels']:raise ValueError('Retained texture chart coverage did not pass')
            if gap['complete'] is not True or gap['violation_pair_count']!=0 or gap['required_gap_pixels']!=2*policy['padding_pixels'] or row['edge_margin_pixels']<policy['padding_pixels']:raise ValueError('Retained texture padding did not pass')
        return policy
    except (KeyError,TypeError,OverflowError) as e:raise ValueError('Invalid retained texture quality report') from e


def inventory(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('Expected a real texture job directory')
    rows=[];directories=[]
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            path=Path(parent)/name;rel=path.relative_to(root);parts=rel.parts
            try:entry=path.lstat()
            except FileNotFoundError:continue  # Atomic native/JSON rename during progress inspection.
            if stat.S_ISLNK(entry.st_mode):raise ValueError('Texture jobs must not contain symlinks')
            allowed=(len(parts)==1 and (name in ROOT_FILES or name in {v+'.tmp' for v in ROOT_FILES} or name=='textures')) or (len(parts)==2 and parts[0]=='textures' and parts[1] in {m+'.png'+suffix for m in MAPS for suffix in ('','@')})
            if not allowed:raise ValueError(f'Unknown texture job entry: {rel}')
            if stat.S_ISDIR(entry.st_mode):
                if parts!=('textures',):raise ValueError('Unexpected texture job directory')
                directories.append(path)
            elif stat.S_ISREG(entry.st_mode):rows.append({'path':rel.as_posix(),'bytes':entry.st_size})
            else:raise ValueError('Nonregular texture job entry')
            if len(rows)+len(directories)>64:raise ValueError('Texture job inventory limit exceeded')
    return sorted(rows,key=lambda r:r['path']),directories


def deliverables(root):
    return [r for r in inventory(root)[0] if r['path'] in {'source.blend','asset.blend'} or r['path'].endswith('.png')]


def manifest(root):
    return [r|{'sha256':file_hash(Path(root)/r['path'])} for r in deliverables(root)]


def verify_steps(root,expected):
    rows=deliverables(root)
    if rows!=[{'path':r['path'],'bytes':r['bytes']} for r in expected]:raise ValueError('Texture bundle files are missing, changed or unexpected')
    total=sum(r['bytes'] for r in rows);done=0;last=0
    for row in expected:
        digest=hashlib.sha256()
        with (Path(root)/row['path']).open('rb') as stream:
            for block in iter(lambda:stream.read(1024**2),b''):
                digest.update(block);done+=len(block)
                if done-last>=16*1024**2:
                    yield {'phase':'verifying texture bundle','bytes_verified':done,'total_bytes':total};last=done
        if digest.hexdigest()!=row['sha256']:raise ValueError('Texture bundle files are missing, changed or unexpected')
    yield {'phase':'verifying texture bundle','bytes_verified':done,'total_bytes':total}
    return total
