"""Supported dense mask-role creation reproduces the actual ray-role control."""
import os,json,shutil,subprocess
from pathlib import Path
import pytest
from test_botanical_native import pytestmark


@pytest.mark.skipif(not all(os.environ.get('MCPBLENDER_SECONDARY_DENSE_'+key) for key in ('CAPTURE','BASE','CONTROL')),reason='Retained dense capture/baseline/ray-role control required')
def test_guarded_dense_masked_secondary_roles(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    paths=[str(Path(os.environ['MCPBLENDER_SECONDARY_DENSE_'+key]).resolve()) for key in ('CAPTURE','BASE','CONTROL')]
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1',
        '--python',str(Path(__file__).with_name('native_depth_secondary.py')),'--',str(repo),*paths,str(tmp_path)],capture_output=True,text=True,timeout=900)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'SECONDARY_DENSE_NATIVE_OK' in run.stdout
    proof=json.loads((tmp_path/'proof.json').read_text())
    for role,row in proof['roles'].items():
        assert row['created']['valid'] and row['reopened']['asset_sha256']==row['created']['asset_sha256']
        assert row['created']['render_role']==role
        for lighting,result in row['comparisons'].items():
            assert not result['passed']
            assert all(r['failures']==['max_abs_overlap_luminance_relative_bias'] for r in result['levels'])
            assert row['control_checks'][lighting]['passed']
    assert proof['roles']['SECONDARY']['comparisons']['world']['levels'][0]['overlap_luminance_relative_bias']<.3
    if destination:=os.environ.get('MCPBLENDER_SECONDARY_DENSE_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        for path in [tmp_path/'proof.json',*tmp_path.glob('*.exr'),*tmp_path.glob('*.blend')]:shutil.copy2(path,out/path.name)
