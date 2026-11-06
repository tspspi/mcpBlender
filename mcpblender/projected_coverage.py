"""Immutable projected-coverage recipe and numerical readback (no bpy)."""
import math
from . import botany,exr_scanline,tree_capture

FORMAT='mcpblender-projected-component-coverage-v1'
IMAGE='MCP Projected Coverage Reference IDs'
LAYER='ProjectedCoverage'
SCOPE='Monte Carlo projected union coverage of the reference leaf component per cell, ignoring other components. Static captured view and geometry; not first-visible area, face identity, self-occlusion classification, optical equivalence, wind or angular certification. No albedo or lighting adjustment.'


def sampling(samples):
    if type(samples) is not int or not 64<=samples<=4096:raise ValueError('Invalid projected coverage sample budget')
    return {'effective_samples':samples,'master_samples':samples+1,'use_sample_subset':True,'sample_offset':1,'sample_subset_length':samples,'sampling_pattern':'AUTOMATIC','seed':0,'use_animated_seed':False,'use_adaptive_sampling':False,'use_denoising':False,'pixel_filter_type':'BOX','filter_width':1.,'transparent_max_bounces':1024}


def validate(value,job):
    if value.get('format')!=FORMAT or value.get('plan_sha256')!=botany.digest({k:v for k,v in value.items() if k!='plan_sha256'}):raise ValueError('Projected coverage plan binding mismatch')
    profile=value['sampling'];size=value['resolution'];ref=value['reference']
    tree_capture.validate(ref,{'cameras':[v['camera'] for v in ref['views']],'formats':['PNG','OPEN_EXR_MULTILAYER'],'engine':'CYCLES','frame_start':ref['frame'],'frame_end':ref['frame'],'width':ref['options']['resolution'],'height':ref['options']['resolution'],'samples':ref['options']['samples']})
    if value['view'] not in ref['views']:raise ValueError('Projected coverage reference camera changed')
    if profile!=sampling(profile['effective_samples']):raise ValueError('Projected coverage sampling recipe changed')
    if type(size) is not int or not 32<=size<=1024 or ref['options']['resolution']!=size or not ref.get('component_ids') or ref['options']['samples']!=1:raise ValueError('Projected coverage reference profile mismatch')
    if value['image']!=IMAGE or not 0<value['target_pixels']<=size*size or value['scope']!=SCOPE:raise ValueError('Projected coverage grid profile mismatch')
    if job['engine']!='CYCLES' or job['samples']!=profile['master_samples'] or job['width']!=size or job['height']!=size or job['formats']!=['OPEN_EXR_MULTILAYER'] or job['cameras']!=[value['view']['camera']] or job['frame_start']!=ref['frame'] or job['frame_end']!=ref['frame'] or job['frame_step']!=1:raise ValueError('Projected coverage job profile mismatch')


def measure(path,sha256,size,progress=lambda value:None,cancelled=lambda:None):
    names=[LAYER+'.Combined.'+c for c in 'RGBA']
    decoded=exr_scanline.decode(path,names,expected_sha256=sha256,cancelled=cancelled,progress=progress)
    if decoded['width']!=size or decoded['height']!=size or tuple(decoded['data_window'])!=(0,0,size-1,size-1):raise ValueError('Projected coverage dimensions changed')
    channels=decoded['channels'];mass=0.;zeros=0;error=0.
    for i,a in enumerate(channels[names[3]]):
        if i%8192==0:cancelled()
        if not math.isfinite(a) or not 0<=a<=1:raise ValueError('Invalid projected coverage alpha')
        rgb=[channels[n][i] for n in names[:3]]
        if not all(math.isfinite(v) for v in rgb):raise ValueError('Nonfinite projected coverage matte')
        error=max(error,*(abs(v-a) for v in rgb));mass+=a;zeros+=a==0
    if error>1e-6:raise ValueError('Projected coverage white-alpha disagreement; traversal or data profile invalid')
    return {'coverage_mass_pixels':mass,'zero_pixels':zeros,'white_alpha_max_error':error,'scope':SCOPE}



def consume(directory,reference,proof,view,row,grid,mask,*,progress=lambda value:None,cancelled=lambda:None):
    """Read a hash-bound coverage alpha grid; preserve the reference leaf domain."""
    from pathlib import Path
    from array import array
    from . import render_jobs,depth_tiles
    root=Path(directory);job=render_jobs.read_json(root/'job.json')
    def cancel_requested():cancelled();return False
    validated=render_jobs.validate_contents(root,job['job_id'],progress,cancel_requested)
    value=validated.get('projected_coverage')
    if value is None:raise ValueError('Projected coverage bundle required')
    if value['reference']!=reference or value['reference_snapshot_sha256']!=proof['source_sha256'] or value['reference_exr_sha256']!=row['sha256'] or value['view']!=view:raise ValueError('Projected coverage reference capture/view binding mismatch')
    if value['grid_sha256']!=botany.digest(grid) or value['target_pixels']!=sum(mask):raise ValueError('Projected coverage reference ID grid mismatch')
    output=validated['outputs'][0];name=LAYER+'.Combined.A'
    decoded=exr_scanline.decode(root/output['file'],[name],expected_sha256=output['sha256'],cancelled=cancelled,progress=progress)
    pixels=decoded['channels'][name];alpha=array('f');mass=0.;outside=0.;zeros=0
    for i,(a,keep) in enumerate(zip(pixels,mask)):
        if i%8192==0:cancelled()
        alpha.append(a if keep else 0.)
        if keep:mass+=a;zeros+=a==0
        else:outside+=a
    return alpha,{'format':FORMAT,'plan_sha256':value['plan_sha256'],'snapshot_sha256':validated['source_sha256'],'exr_sha256':output['sha256'],
                  'grid_sha256':value['grid_sha256'],'sampling':value['sampling'],'target_pixels':sum(mask),'target_coverage_mass_pixels':mass,'zero_target_pixels':zeros,
                  'excluded_outside_target_mass_pixels':outside,'alpha_float32_sha256':depth_tiles.floats_sha(alpha),'decoded_source_pixels':len(alpha),'scope':SCOPE}
