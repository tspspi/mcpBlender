"""Renderer execution checks; image measurements are not optical certification."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from test_botanical_native import pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_MOMENT_CANOPY_SOURCE'),reason='Retained native moment capture required')
def test_native_canopy_candidate_creation_and_multilight_measurement(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    source=Path(os.environ['MCPBLENDER_MOMENT_CANOPY_SOURCE']).resolve()
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2',
        '--python-exit-code','1','--python',str(Path(__file__).with_name('native_depth_candidates.py')),
        '--',str(repo),str(source),str(tmp_path)],capture_output=True,text=True,timeout=180)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    proof=json.loads((tmp_path/'proof.json').read_text())
    assert proof['created']['valid'] and proof['plan']['geometry']['max_component_residual']<=1e-5
    assert set(proof['comparisons'])=={'world','sun_front','sun_back'}
    for row in proof['comparisons'].values():
        assert row['overlap_alpha_area_pixels']>0
        assert all(math.isfinite(row[key]) for key in ('overlap_luminance_relative_bias','mask_iou','soft_alpha_iou'))
    # Measurements are deliberately not asserted optically equivalent. The
    # retained control currently fails rear-lighting and silhouette gates.
    if destination:=os.environ.get('MCPBLENDER_CANDIDATE_NATIVE_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        for path in [tmp_path/'proof.json',tmp_path/'canopy-moment.blend',*tmp_path.glob('*.exr')]:
            shutil.copy2(path,out/path.name)
