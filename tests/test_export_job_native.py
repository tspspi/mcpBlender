"""Kill real native exporters before/after validation; reconcile files without replay."""
import os
from pathlib import Path
import shutil
import subprocess
import time
import pytest
from mcpblender.export_jobs import inspect,recover,cleanup
from mcpblender.lod_files import validate

pytestmark=[pytest.mark.blender,pytest.mark.skipif(os.environ.get('MCPBLENDER_TEST_BLENDER')!='1' or not shutil.which('blender'),reason='Installed Blender opt-in required')]


@pytest.mark.parametrize('boundary',['partial','verified'])
def test_killed_blender_export_recovers_or_cleans_owned_stage(tmp_path,boundary):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'probe.py';directory=tmp_path/'delivery';marker=tmp_path/'kill-ready'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy,time
from pathlib import Path
from types import SimpleNamespace
from mcpblender.blender import lods,bridge,domains
from mcpblender.lod_contracts import Generate,Export
from mcpblender.export_jobs import ExportJob
root=Path(__file__).parent;boundary=sys.argv[-1]
bridge._bridge=SimpleNamespace(active={'owner':'native-test','operation_id':'killed-native-export','storage':{}},cancel_requested=False)
bridge.check_cancelled=lambda:None

def hold():
    (root/'kill-ready').write_text('ready')
    while not (root/'release').exists():time.sleep(.05)

def progress(value):
    if boundary=='partial' and value.get('phase')=='exported and decoded LOD':hold()
bridge.report_progress=progress
original=ExportJob.verify

def verify(self):
    original(self)
    if boundary=='verified':hold()
ExportJob.verify=verify
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12);source=bpy.context.object;source.name='Source'
plan=lods.inspect_source({'name':'Source'})
chain=lods.generate(Generate.model_validate({'name':'Source','chain':'Asset','expected_source':plan['source_sha256'],'levels':[{'triangle_budget':220},{'triangle_budget':100}],'max_relative_error':.3,'error_samples':64}).model_dump(exclude_none=True))
params=Export.model_validate({'chain':'Asset','expected_chain':chain['chain_sha256'],'directory':str(root/'delivery'),'animations':False}).model_dump(exclude_none=True)
domains.dispatch('export_lod_chain',params)
''')
    with (tmp_path/'blender.log').open('w') as log:
        process=subprocess.Popen(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script),'--',boundary],stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+45
            while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.05)
            assert marker.exists(),(tmp_path/'blender.log').read_text()
            state=inspect(directory,'native-test');assert state['writer_active']
            process.kill();process.wait(timeout=10)
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=10)
    state=inspect(directory,'native-test');assert not state['writer_active'] and state['record']['operation_id']=='killed-native-export'
    reconciled=recover(directory,'native-test',state['job_sha256']);assert not reconciled['replayed']
    if boundary=='verified':
        assert reconciled['record']['state']=='ready'
        published=recover(directory,'native-test',reconciled['job_sha256'],publish=True)
        assert published['record']['state']=='published' and validate(directory)['valid']
    else:
        assert reconciled['record']['state']=='interrupted' and reconciled['stage_bytes']>0
        cleanup(directory,'native-test',reconciled['job_sha256'],dry_run=False)
        assert not inspect(directory,'native-test')['stage_exists'] and not directory.exists()


def test_addon_imports_recovery_without_frontend_dependencies(tmp_path):
    import zipfile
    from mcpblender.server import addon_zip
    path=tmp_path/'addon.zip';addon_zip(path);extracted=tmp_path/'extracted'
    with zipfile.ZipFile(path) as archive:archive.extractall(extracted)
    script=tmp_path/'addon-probe.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(extracted))+')\n'+r'''
import importlib.abc
class BlockFrontend(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'pydantic','fastmcp'}:raise ImportError('Frontend dependencies forbidden in native add-on')
sys.meta_path.insert(0,BlockFrontend())
import mcpblender
from mcpblender.blender import domains,export_recovery
assert 'get_capabilities' in domains.COMMANDS and 'rebuild_lod_chain' in domains.COMMANDS
assert 'inspect_texture_quality' in domains.COMMANDS
from mcpblender import uv_chart_layout
assert callable(uv_chart_layout.pack)
assert not any(n.split('.')[0] in {'pydantic','fastmcp'} for n in sys.modules)
print('ADDON_DEPENDENCY_FREE_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'ADDON_DEPENDENCY_FREE_OK' in result.stdout


def test_cancel_after_durable_validation_still_prevents_publication(tmp_path):
    repo=Path(__file__).resolve().parents[1];script=tmp_path/'cancel.py'
    script.write_text('import sys\nsys.path.insert(0,'+repr(str(repo))+')\n'+r'''
import bpy
from pathlib import Path
from types import SimpleNamespace
from mcpblender.blender import lods,domains,bridge
from mcpblender.lod_contracts import Generate,Export
from mcpblender.export_jobs import ExportJob,inspect
bridge._bridge=SimpleNamespace(active={'owner':'cancel-test','operation_id':'cancel-native','storage':{}},cancel_requested=False)
bridge.report_progress=lambda v:None
completed=False

def check():
    if completed:raise bridge.OperationCancelled('late validation cancellation')
bridge.check_cancelled=check
original=ExportJob.verify

def verify(self):
    global completed
    original(self);completed=True
ExportJob.verify=verify
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12);source=bpy.context.object;source.name='Source'
plan=lods.inspect_source({'name':'Source'})
chain=lods.generate(Generate.model_validate({'name':'Source','chain':'Asset','expected_source':plan['source_sha256'],'levels':[{'triangle_budget':220}],'max_relative_error':.3,'error_samples':64}).model_dump(exclude_none=True))
directory=Path(__file__).parent/'delivery';params=Export.model_validate({'chain':'Asset','expected_chain':chain['chain_sha256'],'directory':str(directory),'animations':False}).model_dump(exclude_none=True)
try:domains.dispatch('export_lod_chain',params)
except bridge.OperationCancelled:pass
else:raise AssertionError('Expected cancellation after durable verification')
assert not directory.exists()
state=inspect(directory,'cancel-test');assert state['record']['state']=='cancelled' and not state['stage_exists'] and not state['writer_active']
assert lods.inspect_source({'name':'Source'})['source_sha256']==plan['source_sha256']
print('LATE_EXPORT_CANCEL_OK')
''')
    result=subprocess.run(['blender','--background','--factory-startup','--python-exit-code','1','--python',str(script)],capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'LATE_EXPORT_CANCEL_OK' in result.stdout
