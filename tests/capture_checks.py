"""Compare frozen captures by view identity, independent of camera ordering."""
import json
from pathlib import Path
from mcpblender.image_comparison import decode_png


def assert_native_png_views(reference,candidate,manifest):
    reference=Path(reference);candidate=Path(candidate)
    frozen=json.loads((reference/'manifest.json').read_text())
    views={v['view']:v for v in frozen['botanical_capture']['views']};matched=[]
    for view in manifest['botanical_capture']['views']:
        previous=views[view['view']]
        for key in ('matrix_world','ortho_scale','clip_start','clip_end'):
            assert view[key]==previous[key],(view['view'],key)
        current=next(r for r in manifest['outputs'] if r['camera']==view['camera'] and r['format']=='PNG')
        original=next(r for r in frozen['outputs'] if r['camera']==previous['camera'] and r['format']=='PNG')
        assert decode_png((reference/original['file']).read_bytes(),color_space='LINEAR',premultiply=False)==decode_png((candidate/current['file']).read_bytes(),color_space='LINEAR',premultiply=False),view['view']
        matched.append({'view':view['view'],'reference':original['file'],'candidate':current['file'],'PNG_exact':True,'camera_exact':True})
    return matched
