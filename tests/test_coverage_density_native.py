"""Native opacity reuse counterexample and denser source sampling control."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from test_botanical_native import pytestmark


def test_thin_opaque_geometry_needs_denser_coverage_for_matched_render(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2',
        '--python-exit-code','1','--python',str(Path(__file__).with_name('native_coverage_density.py')),
        '--',str(repo),str(tmp_path)],capture_output=True,text=True,timeout=180)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    proof=json.loads((tmp_path/'proof.json').read_text());slats=proof['slats']
    assert slats['1']['mask_iou']<.1 and slats['1']['soft_alpha_iou']<.8
    assert slats['4']['mask_iou']>.9 and slats['4']['soft_alpha_iou']>.9
    assert slats['4']['alpha_mae']<.015
    assert slats['1']['soft_alpha_iou']<slats['2']['soft_alpha_iou']<slats['4']['soft_alpha_iou']
    assert proof['edge']['1']['soft_alpha_iou']>.95 and proof['edge']['4']['soft_alpha_iou']>.95
    # A large edge can conceal the thin-detail failure; 2x capture is not a
    # general qualification of all structures or all rendered metrics either.
    assert slats['2']['mask_iou']<.8
    if destination:=os.environ.get('MCPBLENDER_COVERAGE_DENSITY_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        for path in [tmp_path/'proof.json',*tmp_path.glob('*.exr')]:shutil.copy2(path,out/path.name)
