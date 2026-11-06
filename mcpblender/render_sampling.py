"""Portable sampling witnesses for owned render bundles (no bpy)."""
from copy import deepcopy
from . import botany
FORMAT='mcpblender-cycles-sampling-v1'
KEYS=('samples','sampling_pattern','seed','use_animated_seed','use_adaptive_sampling','adaptive_threshold','adaptive_min_samples','use_denoising','use_layer_samples','pixel_filter_type','filter_width','use_sample_subset','sample_offset','sample_subset_length','time_limit','max_bounces','diffuse_bounces','glossy_bounces','transmission_bounces','volume_bounces','transparent_max_bounces')


def record(engine,settings,layers,animated,execution):
    body={'format':FORMAT,'engine':engine,'settings':settings,'layers':layers,'animated_fields':animated,'execution':execution}
    return body|{'sampling_sha256':botany.digest(body)}


def validate(value):
    if not isinstance(value,dict) or value.get('format')!=FORMAT or value.get('sampling_sha256')!=botany.digest({k:v for k,v in value.items() if k!='sampling_sha256'}):raise ValueError('Render sampling witness digest mismatch')
    if set(value)!= {'format','engine','settings','layers','animated_fields','execution','sampling_sha256'} or set(value.get('settings',{}))!=set(KEYS) or not isinstance(value.get('layers'),list) or not 1<=len(value['layers'])<=4096:raise ValueError('Invalid render sampling witness fields')
    if any(set(row)!={'name','enabled','samples','use_denoising'} or not isinstance(row['name'],str) or type(row['enabled']) is not bool or type(row['use_denoising']) is not bool or type(row['samples']) is not int or row['samples']<0 for row in value['layers']):raise ValueError('Invalid render sampling layer witness')
    if set(value['execution'])!={'device','threads_mode','threads'} or type(value['execution']['threads']) is not int or value['execution']['threads']<1:raise ValueError('Invalid render execution witness')
    return value


def windows(settings,layers):
    rows=[]
    for layer in layers:
        if not layer['enabled']:continue
        maximum=settings['samples'];override=layer['samples'];mode=settings['use_layer_samples']
        if override and mode=='USE':maximum=override
        elif override and mode=='BOUNDED':maximum=min(maximum,override)
        count=max(0,min(settings['sample_subset_length'],maximum-settings['sample_offset'])) if settings['use_sample_subset'] else maximum
        rows.append({'layer':layer['name'],'master_samples':maximum,'sample_ceiling':count})
    return rows


def expected(contract,job):
    if contract.get('format')!='GUARDED_CYCLES_SAMPLING_V1':raise ValueError('Unknown guarded sampling contract')
    source=validate(contract['source'])
    if job.get('expected_sampling')!=source['sampling_sha256']:raise ValueError('Render sampling request/source binding mismatch')
    if source['animated_fields'] or source['engine']!='CYCLES' or job['engine']!='CYCLES':raise ValueError('Guarded sampling requires static Cycles settings')
    body=deepcopy(source);body['settings']['samples']=job['samples'];body['execution'].update(device='CPU',threads_mode='FIXED',threads=job['threads'])
    active=windows(body['settings'],body['layers'])
    if not active:raise ValueError('Guarded render needs an enabled render layer')
    if any(row['sample_ceiling']<=0 for row in active):raise ValueError('Render job sample subset has no samples in an enabled layer')
    return record(body['engine'],body['settings'],body['layers'],body['animated_fields'],body['execution'])
