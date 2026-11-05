"""Native depth-refined dense asset and explicit optical rejection measurements."""
import json,os,shutil,subprocess
from pathlib import Path
import pytest
from test_botanical_native import pytestmark


@pytest.mark.skipif(not all(os.environ.get('MCPBLENDER_DEPTH_REFINEMENT_'+k) for k in ('CAPTURE','BASE')),reason='Retained dense capture and frozen source render baseline required')
def test_native_dense_depth_refinement_and_hybrid_control(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    inputs=[str(Path(os.environ['MCPBLENDER_DEPTH_REFINEMENT_'+k]).resolve()) for k in ('CAPTURE','BASE')]
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1',
        '--python',str(Path(__file__).with_name('native_depth_refinement.py')),'--',str(repo),*inputs,str(tmp_path)],capture_output=True,text=True,timeout=900)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'DEPTH_REFINEMENT_NATIVE_OK' in run.stdout
    proof=json.loads((tmp_path/'proof.json').read_text());asset=proof['assets']['primary'];depth=asset['plan']['geometry']['depth_residuals']
    assert asset['valid'] and asset['triangles']==131072
    assert depth['coverage_weighted_mae_m']<.2 and not depth['measured_tolerance_met']
    assert depth['unknown_depth_pixels']>0 and depth['tolerance_unmet_cells']>0
    assert all(row['passed'] for row in proof['baseline_checks'].values())
    if destination:=os.environ.get('MCPBLENDER_DEPTH_REFINEMENT_NATIVE_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        for path in [tmp_path/'proof.json',tmp_path/'refined.blend',*tmp_path.glob('*.exr')]:shutil.copy2(path,out/path.name)
