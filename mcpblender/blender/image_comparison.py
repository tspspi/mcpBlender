"""Read-only file comparison with no native datablock creation or image caches."""
from pathlib import Path
from mcpblender import image_comparison as images
COMMANDS={'compare_png_images'}


def dispatch(command,p):
    from .bridge import check_cancelled,report_progress
    data=[]
    for key in ('reference','candidate'):
        check_cancelled();path=Path(p[key])
        with path.open('rb') as stream:
            payload=stream.read(images.MAX_BYTES+1)
        if len(payload)>images.MAX_BYTES:raise ValueError('Comparison PNG file byte budget exceeded')
        data.append(payload)
    return images.compare(*data,scales=p['scales'],alpha_threshold=p['alpha_threshold'],color_space=p['color_space'],policy=p['quality'],cancelled=check_cancelled,progress=report_progress)
