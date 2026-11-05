"""Independent native coverage and directional-light counterexample."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from test_botanical_native import pytestmark


def test_native_normal_accumulation_and_lighting_counterexample(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(Path(__file__).with_name('native_normal_filtering.py')),'--',str(repo),str(tmp_path)],capture_output=True,text=True,timeout=120)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'NORMAL_CALIBRATION_COMPLETE' in run.stdout
    proof=json.loads((tmp_path/'proof.json').read_text())
    for filter_name in ('box','default'):
        rows=proof['controls']
        flat=rows[filter_name+'-flat-world'];mixed=rows[filter_name+'-mixed-world']
        assert abs(flat['mean_rgb_on_central_16px']-mixed['mean_rgb_on_central_16px'])<1e-5
        sun_flat=rows[filter_name+'-flat-sun'];sun_mixed=rows[filter_name+'-mixed-sun']
        assert abs(sun_mixed['mean_rgb_on_central_16px']/sun_flat['mean_rgb_on_central_16px']-.5)<1e-5
        assert .49<mixed['filtering']['groups']['opaque']['conditional_length']['mean']<.51
        assert abs(flat['filtering']['groups']['opaque']['conditional_length']['mean']-1)<1e-5
        for shape,nz in (('edge',1),('mixed_edge',.5)):
            for lighting in ('world','sun'):
                row=rows[filter_name+'-'+shape+'-'+lighting];w=row['Calibration.Probe_W.X']
                assert .4<w<.6
                assert abs(row['Calibration.Normal.Z']/w-nz)<1e-5
                assert abs(sum(row['Calibration.Probe_'+a+'.X'] for a in ('XX','YY','ZZ'))/w-1)<1e-5
                assert row['filtering']['groups']['partial']['conditional_length']['count']>0
        assert all(row['filtering']['conditional_length_over_one']==0 for key,row in rows.items() if key.startswith(filter_name+'-'))
    if destination:=os.environ.get('MCPBLENDER_NORMAL_FILTERING_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True);shutil.copy2(tmp_path/'proof.json',out/'native-proof.json')
