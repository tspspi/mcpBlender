"""Canopy silhouette qualification at 4x data density, separate from relighting."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from test_botanical_native import pytestmark


@pytest.mark.skipif(not os.environ.get('MCPBLENDER_SAMPLING_CAPTURES'),reason='Retained capture-32/capture-128 sampling workflow required')
def test_native_canopy_output_grid_silhouette(tmp_path):
    repo=Path(__file__).resolve().parents[1];source=Path(os.environ['MCPBLENDER_SAMPLING_CAPTURES']).resolve()
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2',
        '--python-exit-code','1','--python',str(Path(__file__).with_name('native_depth_sampling.py')),
        '--',str(repo),str(source/'capture-32'),str(source/'capture-128'),str(tmp_path)],capture_output=True,text=True,timeout=180)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    proof=json.loads((tmp_path/'proof.json').read_text());low,high=proof['32'],proof['128']
    assert low['created']['valid'] and high['created']['valid']
    assert low['plan']['geometry']['triangles']==high['plan']['geometry']['triangles']
    assert high['plan']['geometry']['output_sampling']['capture_texels_per_output_pixel']==4
    assert low['metrics']['soft_alpha_iou']<.8
    assert high['metrics']['mask_iou']>=.8 and high['metrics']['soft_alpha_iou']>=.8
    assert high['metrics']['alpha_mae']<=.05
    assert high['metrics']['soft_alpha_iou']>low['metrics']['soft_alpha_iou']
    # RGB metrics are recorded independently. Passing alpha gates cannot turn
    # these directional PBR patches into an optically qualified reconstruction.
    assert high['plan']['optical_equivalence'] is False
    if destination:=os.environ.get('MCPBLENDER_SAMPLING_NATIVE_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        for path in [tmp_path/'proof.json',*tmp_path.glob('*.exr')]:shutil.copy2(path,out/path.name)
