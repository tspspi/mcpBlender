"""Real small-canopy optical gates are separate from broader qualification."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from test_botanical_native import pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_SHADOW_CAPTURE'),reason='Retained 128px FRONT/BACK material-input capture required')
def test_guarded_paired_shadow_canopy_three_lights(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2',
        '--python-exit-code','1','--python',str(Path(__file__).with_name('native_depth_shadow.py')),
        '--',str(repo),str(Path(os.environ['MCPBLENDER_SHADOW_CAPTURE']).resolve()),str(tmp_path)],capture_output=True,text=True,timeout=240)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'PAIRED_SHADOW_NATIVE_OK' in run.stdout
    proof=json.loads((tmp_path/'proof.json').read_text())
    for light in ('world','sun_front','sun_back'):
        row=proof['comparisons'][light+'-masked']
        assert row['overlap_rgb_rmse']<=.05 and row['premultiplied_rgb_rmse']<=.05,(light,row)
        assert abs(row['overlap_luminance_relative_bias'])<=.1,(light,row)
        assert row['mask_iou']>=.8 and row['soft_alpha_iou']>=.8 and row['alpha_mae']<=.05,(light,row)
    assert proof['comparisons']['sun_back-primary']['overlap_luminance_relative_bias']>1
    assert abs(proof['comparisons']['sun_back-masked']['overlap_luminance_relative_bias'])<abs(proof['comparisons']['sun_back-unmasked']['overlap_luminance_relative_bias'])
    if destination:=os.environ.get('MCPBLENDER_SHADOW_NATIVE_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        for path in [tmp_path/'proof.json',tmp_path/'layers.blend',*tmp_path.glob('*.exr')]:shutil.copy2(path,out/path.name)
