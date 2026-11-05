"""Portable metadata contract for native tree reference/data captures."""
from . import botany,card_views

FORMAT='mcpblender-botanical-view-capture-v1'
PASSES={'z':'Depth','normal':'Normal','position':'Position','diffuse_color':'Diffuse Color',
        'glossy_color':'Glossy Color','transmission_color':'Transmission Color'}


def validate(metadata,job):
    if not isinstance(metadata,dict) or metadata.get('format')!=FORMAT:raise ValueError('Invalid botanical capture format')
    body={k:v for k,v in metadata.items() if k!='capture_sha256'}
    if botany.digest(body)!=metadata.get('capture_sha256'):raise ValueError('Botanical capture metadata digest mismatch')
    views=metadata.get('views',[])
    if not 1<=len(views)<=10 or len({v['view'] for v in views})!=len(views) or any(v['view'] not in card_views.DIRECTIONS for v in views):raise ValueError('Invalid botanical capture views')
    if [v['camera'] for v in views]!=job['cameras'] or job['formats']!=['PNG','OPEN_EXR_MULTILAYER'] or job['engine']!='CYCLES' or job['frame_start']!=job['frame_end'] or job['frame_start']!=metadata['frame']:raise ValueError('Botanical capture camera/frame/format binding mismatch')
    if job['width']!=metadata['options']['resolution'] or job['height']!=job['width'] or job['samples']!=metadata['options']['samples']:raise ValueError('Botanical capture render settings binding mismatch')
    fields=metadata.get('material_fields')
    if bool(fields)!=bool(metadata['options'].get('material_fields',False)):raise ValueError('Capture material field option/contract mismatch')
    if bool(fields and fields.get('normal_moments'))!=bool(metadata['options'].get('normal_moments',False)):raise ValueError('Capture normal-moment option/contract mismatch')
    if fields is not None:
        from . import capture_material_fields
        capture_material_fields.validate(fields)
    return metadata


def validate_header(header):
    channels={v['name']:v for v in header['channels']}
    expected={'Combined.R','Combined.G','Combined.B','Combined.A','Depth.Z',
              *(p+'.'+axis for p in ('Normal','Position') for axis in 'XYZ'),
              *(p+'.'+axis for p in ('Diffuse Color','Glossy Color','Transmission Color') for axis in 'RGB')}
    for suffix in expected:
        if not any(name=='TreeCapture.'+suffix and row['pixel_type']==2 for name,row in channels.items()):raise ValueError('Botanical capture EXR lacks required float32 channel: '+suffix)
