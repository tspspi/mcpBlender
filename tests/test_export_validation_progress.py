"""Detailed validator observations and cancellation through durable job control.

Geometry verification is stubbed here; native/file suites qualify its contents.
These tests exercise the real journal, binding, ownership and publication paths.
"""
import json
import time
from types import SimpleNamespace
import pytest
from mcpblender import export_jobs as jobs,vegetation_lod_files


BINDING={'profile_guard':'a'*64}
DETAIL={'phase':'projecting independent vegetation quality grids','completed':128,'total':256}
PROOF={'fixture':'observation wiring only'}


def stage(job):
    job.stage.mkdir();job.created()
    (job.stage/'manifest.json').write_text(json.dumps(BINDING))


def test_native_job_forwards_details_and_retains_them_in_heartbeat(tmp_path,monkeypatch):
    clock=[0.];seen=[]
    monkeypatch.setattr(jobs,'time',SimpleNamespace(monotonic=lambda:clock[0],time=time.time))
    def validator(path,*,cancelled,progress):
        clock[0]=2.;cancelled()  # Heartbeat before detailed observations exist.
        progress(dict(DETAIL));clock[0]=4.;cancelled()
        return dict(PROOF)
    monkeypatch.setattr(vegetation_lod_files,'validate',validator)
    with jobs.ExportJob(tmp_path/'asset','stdio','VEGETATION_LOD',BINDING) as job:
        stage(job)
        assert job.verify(progress=lambda d:seen.append(dict(d)))==PROOF
        assert seen[0]['phase']=='validating durable export stage'
        assert sum(d==DETAIL for d in seen)>=2
        assert job.record['state']=='verified'
        job.stage.rename(job.directory)
    assert jobs.inspect(job.directory,'stdio')['record']['state']=='published'


def test_detail_callback_cancellation_never_marks_stage_verified(tmp_path,monkeypatch):
    class OperationCancelled(Exception):pass
    def validator(path,*,cancelled,progress):
        progress(dict(DETAIL))
        return dict(PROOF)
    def observe(d):
        if d.get('completed')==128:raise OperationCancelled('cancelled during detailed validation')
    monkeypatch.setattr(vegetation_lod_files,'validate',validator)
    with pytest.raises(OperationCancelled):
        with jobs.ExportJob(tmp_path/'asset','stdio','VEGETATION_LOD',BINDING) as job:
            stage(job);job.verify(progress=observe)
    record=jobs.read_record(job.root)
    assert record['state']=='cancelled' and 'verified_at' not in record
    assert job.stage.is_dir() and not job.directory.exists()


def abandoned(tmp_path):
    with jobs.ExportJob(tmp_path/'asset','stdio','VEGETATION_LOD',BINDING) as job:
        stage(job)
    return job,jobs.inspect(job.directory,'stdio')


def test_recovery_executor_forwards_details_and_publishes(tmp_path,monkeypatch):
    seen=[]
    def validator(path,*,cancelled,progress):
        cancelled();progress(dict(DETAIL));cancelled()
        return dict(PROOF)
    monkeypatch.setattr(vegetation_lod_files,'validate',validator)
    job,info=abandoned(tmp_path)
    result=jobs.execute('recover_export_job',{'directory':str(job.directory),'_job_owner':'stdio','expected_job':info['job_sha256'],'publish':True},lambda d:seen.append(dict(d)),lambda:False)
    assert result['record']['state']=='published' and result['target_is_original_stage']
    assert sum(d.get('completed')==128 for d in seen)>=2
    assert not result['replayed']


@pytest.mark.parametrize('publish',[False,True])
def test_recovery_cancellation_is_not_an_invalid_bundle(tmp_path,monkeypatch,publish):
    cancel=[False]
    def validator(path,*,cancelled,progress):
        progress(dict(DETAIL));cancelled()
        return dict(PROOF)
    def observe(d):
        if d.get('completed')==128:cancel[0]=True
    monkeypatch.setattr(vegetation_lod_files,'validate',validator)
    job,info=abandoned(tmp_path);before=jobs.read_record(job.root)
    with pytest.raises(InterruptedError,match='cancelled'):
        jobs.execute('recover_export_job',{'directory':str(job.directory),'_job_owner':'stdio','expected_job':info['job_sha256'],'publish':publish},observe,lambda:cancel[0])
    assert jobs.read_record(job.root)==before
    assert job.stage.is_dir() and not job.directory.exists()
