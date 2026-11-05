"""Read-only file comparison with no native datablock creation or image caches."""
from pathlib import Path
from mcpblender import image_comparison as images
COMMANDS={'compare_png_images','compare_exr_images'}


def dispatch(command,p):
    from .bridge import check_cancelled,report_progress
    if command=='compare_exr_images':
        from mcpblender import exr_comparison
        return exr_comparison.compare(p['reference'],p['candidate'],reference_pass=p['reference_pass'],candidate_pass=p['candidate_pass'],
            reference_alpha_mode=p['reference_alpha_mode'],candidate_alpha_mode=p['candidate_alpha_mode'],max_pixels=p['max_pixels'],
            scales=p['scales'],alpha_threshold=p['alpha_threshold'],policy=p['quality'],cancelled=check_cancelled,progress=report_progress)
    data=[]
    for key in ('reference','candidate'):
        check_cancelled();path=Path(p[key])
        with path.open('rb') as stream:
            payload=stream.read(images.MAX_BYTES+1)
        if len(payload)>images.MAX_BYTES:raise ValueError('Comparison PNG file byte budget exceeded')
        data.append(payload)
    return images.compare(*data,scales=p['scales'],alpha_threshold=p['alpha_threshold'],color_space=p['color_space'],policy=p['quality'],cancelled=check_cancelled,progress=report_progress)
