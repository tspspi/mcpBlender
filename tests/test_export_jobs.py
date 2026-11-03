"""Real dead-writer locks, immutable publication and conservative owned cleanup."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from mcpblender.export_jobs import ExportJob,inspect,recover,cleanup,job_root
from test_package_files import manifest


def partial_process(directory,wait=False):
    script="""
import os,sys
from pathlib import Path
from mcpblender.export_jobs import ExportJob
with ExportJob(sys.argv[1],'key-a','PACKAGE',{'source_sha256':'a'*64},asset_ids=['prop']) as job:
    job.stage.mkdir();job.created();(job.stage/'prop').mkdir();(job.stage/'prop/primary.glb').write_bytes(b'partial')
    print('READY',flush=True)
    if sys.argv[2]=='wait':sys.stdin.read(1)
    os._exit(23)
"""
    return subprocess.Popen([sys.executable,'-c',script,str(directory),'wait' if wait else 'exit'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)


def test_live_writer_death_reconcile_and_cleanup(tmp_path):
    directory=tmp_path/'asset';process=partial_process(directory,True)
    try:
        assert process.stdout.readline().strip()=='READY'
        current=inspect(directory,'key-a');assert current['writer_active'] and current['stage_bytes']==7
        with pytest.raises(ValueError,match='active'):recover(directory,'key-a',current['job_sha256'])
        with pytest.raises(PermissionError):inspect(directory,'key-b')
        process.kill();process.wait(timeout=10)
        current=inspect(directory,'key-a');assert not current['writer_active']
        ready=recover(directory,'key-a',current['job_sha256']);assert ready['record']['state']=='interrupted' and not ready['replayed']
        dry=cleanup(directory,'key-a',ready['job_sha256']);assert dry['dry_run'] and dry['bytes']==7
        with pytest.raises(ValueError,match='stale'):cleanup(directory,'key-a',current['job_sha256'],dry_run=False)
        cleanup(directory,'key-a',ready['job_sha256'],dry_run=False)
        cleaned=inspect(directory,'key-a');assert cleaned['record']['state']=='cleaned' and not cleaned['stage_exists']
        assert not directory.exists()
    finally:
        if process.poll() is None:process.kill();process.wait(timeout=10)


def abandoned_complete(directory,*,rename=False):
    # Exit without __exit__, exactly as an abrupt writer death would leave it.
    job=ExportJob(directory,'key-a','PACKAGE',{'source_sha256':'a'*64},asset_ids=['prop']);job.__enter__()
    job.stage.mkdir();job.created();manifest(job.stage);job.verify()
    if rename:job.stage.rename(directory)
    job.lock.__exit__(None,None,None);job.lock=None
    return inspect(directory,'key-a')


def test_ready_publish_and_post_rename_reconcile(tmp_path):
    directory=tmp_path/'asset';state=abandoned_complete(directory)
    ready=recover(directory,'key-a',state['job_sha256']);assert ready['record']['state']=='ready'
    with pytest.raises(ValueError,match='protected'):cleanup(directory,'key-a',ready['job_sha256'],dry_run=False)
    done=recover(directory,'key-a',ready['job_sha256'],publish=True);assert done['record']['state']=='published'
    with pytest.raises(ValueError,match='protected'):cleanup(directory,'key-a',done['job_sha256'],dry_run=False)
    assert (directory/'manifest.json').exists()
    other=tmp_path/'post-rename';state=abandoned_complete(other,rename=True)
    assert state['target_is_original_stage'] and state['record']['state']=='verified'
    recovered=recover(other,'key-a',state['job_sha256']);assert recovered['record']['state']=='published'


def test_foreign_unknown_symlink_and_identity_refusal(tmp_path):
    directory=tmp_path/'asset';process=partial_process(directory);process.wait(timeout=10)
    state=inspect(directory,'key-a');stage=Path(state['job_directory'])/state['record']['stage']
    (stage/'foreign.txt').write_text('preserve')
    current=inspect(directory,'key-a');assert current['stage_error']
    with pytest.raises(ValueError,match='Unrecognized'):recover(directory,'key-a',current['job_sha256'])
    (stage/'foreign.txt').unlink();(stage/'prop/linked.glb').symlink_to(tmp_path/'outside')
    current=inspect(directory,'key-a');assert current['stage_error']
    with pytest.raises(ValueError):cleanup(directory,'key-a',current['job_sha256'])
    (stage/'prop/linked.glb').unlink();stage.rename(stage.with_name('moved'));stage.mkdir()
    current=inspect(directory,'key-a');assert 'identity' in current['stage_error']
    with pytest.raises(ValueError,match='identity'):recover(directory,'key-a',current['job_sha256'])


def test_unrelated_target_and_current_reference_preservation(tmp_path):
    directory=tmp_path/'asset';process=partial_process(directory);process.wait(timeout=10)
    state=inspect(directory,'key-a');state=recover(directory,'key-a',state['job_sha256'])
    stage=Path(state['job_directory'])/state['record']['stage']
    with pytest.raises(ValueError,match='references'):cleanup(directory,'key-a',state['job_sha256'],dry_run=False,references=[stage/'prop/primary.glb'])
    directory.mkdir();(directory/'foreign.txt').write_text('preserve')
    state=inspect(directory,'key-a');cleanup(directory,'key-a',state['job_sha256'],dry_run=False)
    assert (directory/'foreign.txt').read_text()=='preserve'


def test_cancelled_cleanup_reconciles_remaining_owned_files(tmp_path):
    directory=tmp_path/'asset';state=abandoned_complete(directory)
    ready=recover(directory,'key-a',state['job_sha256']);checks=0
    def cancel():
        nonlocal checks
        checks+=1
        if checks==2:raise InterruptedError('stop after first deletion')
    with pytest.raises(InterruptedError):cleanup(directory,'key-a',ready['job_sha256'],dry_run=False,discard_ready=True,check_cancelled=cancel)
    current=inspect(directory,'key-a');assert current['record']['state']=='cleaning'
    with pytest.raises(ValueError,match='Recover'):cleanup(directory,'key-a',current['job_sha256'])
    current=recover(directory,'key-a',current['job_sha256']);assert current['record']['state']=='interrupted'
    cleanup(directory,'key-a',current['job_sha256'],dry_run=False)
    assert not inspect(directory,'key-a')['stage_exists']


def test_broker_blocks_active_stage_references_and_late_submissions(tmp_path):
    import time
    from mcpblender.broker import Broker
    directory=tmp_path/'asset';process=partial_process(directory);process.wait(timeout=10)
    state=inspect(directory,'key-a');state=recover(directory,'key-a',state['job_sha256'])
    stage=Path(state['job_directory'])/state['record']['stage']
    runtime=tmp_path/'runtime';runtime.mkdir();broker=Broker(runtime/'bridge.sock')
    broker.worker={'pid':os.getpid(),'session_id':'queue-fixture'}
    try:
        broker.request('submit',{'owner':'key-a','request_id':'queued-read','command':'import_asset','params':{'path':str(stage/'prop/primary.glb')}})
        queued=broker.request('submit',{'owner':'key-a','request_id':'cleanup','command':'cleanup_export_job','params':{'directory':str(directory),'expected_job':state['job_sha256'],'dry_run':False}})
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            result=broker.request('get_operation',{'owner':'key-a','operation_id':queued['operation_id']})
            if result['state'] not in {'queued','running'}:break
            time.sleep(.01)
        assert result['state']=='failed' and 'references' in result['error'] and stage.exists()
        broker.export_cleanup_paths['fixture']=stage
        with pytest.raises(ValueError,match='cleanup is in progress'):
            broker.request('submit',{'owner':'key-a','request_id':'late-read','command':'import_asset','params':{'path':str(stage/'prop/primary.glb')}})
    finally:
        broker.journal.db.close()


def test_bounded_owner_discovery_and_finished_filter(tmp_path):
    from mcpblender.export_jobs import list_jobs
    first=tmp_path/'first';abandoned_complete(first)
    second=tmp_path/'nested/second';second.parent.mkdir();abandoned_complete(second)
    assert len(list_jobs(tmp_path,'key-a',depth=0)['jobs'])==1
    result=list_jobs(tmp_path,'key-a',limit=1);assert len(result['jobs'])==1 and result['scan_truncated'] and result['next_offset']==1
    assert len(list_jobs(tmp_path,'key-a',offset=1)['jobs'])==1
    assert not list_jobs(tmp_path,'other-key')['jobs']
    state=inspect(first,'key-a');recover(first,'key-a',state['job_sha256'],publish=True)
    assert len(list_jobs(tmp_path,'key-a')['jobs'])==1
    assert len(list_jobs(tmp_path,'key-a',include_finished=True)['jobs'])==2
    malformed=tmp_path/('.mcpblender-export-'+'0'*32);malformed.mkdir(mode=0o700);(malformed/'record.json').write_text(json.dumps({'format':'mcpblender-export-job-v1','state':'running','id':3}))
    assert len(list_jobs(tmp_path,'key-a',include_finished=True)['jobs'])==2
