"""Worker component shader attributes and opaque first-sample semantics."""
import os,shutil,subprocess
from pathlib import Path
from test_botanical_native import pytestmark


def test_native_component_capture_preserves_beauty_and_indices(tmp_path):
    repo=Path(__file__).resolve().parents[1]
    run=subprocess.run(['blender','--background','--factory-startup','--disable-autoexec','--threads','2','--python-exit-code','1','--python',str(Path(__file__).with_name('native_component_capture.py')),'--',str(repo),str(tmp_path)],capture_output=True,text=True,timeout=90)
    (tmp_path/'native.log').write_text(run.stdout+'\n'+run.stderr)
    assert run.returncode==0,run.stdout+'\n'+run.stderr
    assert 'COMPONENT_CAPTURE_NATIVE_OK' in run.stdout
    if destination:=os.environ.get('MCPBLENDER_COMPONENT_CAPTURE_EVIDENCE'):
        out=Path(destination);out.mkdir(parents=True,exist_ok=True)
        for file in tmp_path.iterdir():
            if file.is_file():shutil.copy2(file,out/file.name)
