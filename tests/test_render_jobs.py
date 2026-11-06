"""File validation, ownership/cleanup locks and durable broker render delegation."""
import fcntl
import json
import os
from pathlib import Path
import pytest
from mcpblender import render_jobs as jobs
from mcpblender.broker import Broker
from test_shaders import png


def bundle(root,owner='agent',op='operation',state='succeeded'):
    root.mkdir();(root/'outputs').mkdir();(root/'writer.lock').touch();s=root.stat()
    jobs.write_json(root/jobs.MARKER,{'kind':'mcpblender-render-job','version':1,'id':'job1','operation_id':op,'owner':owner,'identity':[s.st_dev,s.st_ino]})
    (root/'source.blend').write_bytes(b'fixture')
    job={'job_id':'job1','cameras':['Cam'],'frame_start':1,'frame_end':1,'frame_step':1,'formats':['PNG'],'width':16,'height':16,'source_sha256':jobs.file_hash(root/'source.blend'),'max_bytes':1024**2}
    jobs.write_json(root/'job.json',job)
    path=root/'outputs/c00_f0000.png';png(path,lambda x,y:(50,70,90))
    member={'camera':'Cam','camera_index':0,'frame':1,'frame_index':0,'format':'PNG','file':'outputs/c00_f0000.png','bytes':path.stat().st_size,'sha256':jobs.file_hash(path),'header':jobs.image_header(path)}
    jobs.write_json(root/'manifest.json',{'job_id':'job1','source_sha256':job['source_sha256'],'outputs':[member]})
    jobs.write_json(root/'status.json',{'job_id':'job1','state':state,'phase':'test'})
    return root


def test_render_file_integrity_and_associations(tmp_path):
    root=bundle(tmp_path/'job');assert jobs.validate(root,'agent')['valid']
    with pytest.raises(InterruptedError):jobs.validate(root,'agent',cancelled=lambda:True)
    with pytest.raises(ValueError,match='ownership'):jobs.inspect(root,'other')
    manifest=jobs.read_json(root/'manifest.json');bad=json.loads(json.dumps(manifest));bad['outputs'][0]['camera']='Different';jobs.write_json(root/'manifest.json',bad)
    with pytest.raises(ValueError,match='association'):jobs.validate(root,'agent')
    jobs.write_json(root/'manifest.json',manifest)
    path=root/'outputs/c00_f0000.png';original=path.read_bytes();path.write_bytes(original[:-1]+bytes([original[-1]^1]))
    with pytest.raises(ValueError,match='hash'):jobs.validate(root,'agent')
    path.write_bytes(original);(root/'unexpected').write_text('preserve')
    with pytest.raises(ValueError,match='Unrecognized'):jobs.inspect(root,'agent')
    (root/'unexpected').unlink();(root/'outputs/foreign.png').symlink_to(path)
    with pytest.raises(ValueError):jobs.inspect(root,'agent')


def test_render_recovery_and_guarded_cleanup(tmp_path):
    root=bundle(tmp_path/'job',state='running');state=jobs.inspect(root,'agent')
    fd=jobs.lock_fd(root);fcntl.flock(fd,fcntl.LOCK_EX)
    try:
        active=jobs.inspect(root,'agent');assert active['writer_alive']
        with pytest.raises(ValueError,match='active'):jobs.recover(root,'agent',active['job_sha256'])
    finally:os.close(fd)
    state=jobs.inspect(root,'agent');recovered=jobs.recover(root,'agent',state['job_sha256']);assert recovered['status']['state']=='succeeded' and not recovered['replayed']
    with pytest.raises(ValueError,match='protected'):jobs.cleanup(root,'agent',{'expected_job':recovered['job_sha256'],'dry_run':False,'include_interrupted':False})
    # Partial failures are never replayed or mistaken for a completed manifest.
    (root/'manifest.json').unlink();jobs.write_json(root/'status.json',{'job_id':'job1','state':'running'})
    state=jobs.inspect(root,'agent');state=jobs.recover(root,'agent',state['job_sha256']);assert state['status']['state']=='interrupted'
    p={'expected_job':state['job_sha256'],'dry_run':True,'include_interrupted':True}
    assert jobs.cleanup(root,'agent',p)['dry_run']
    with pytest.raises(ValueError,match='references'):jobs.cleanup(root,'agent',p|{'dry_run':False,'_references':[str(root/'source.blend')]})
    jobs.cleanup(root,'agent',p|{'dry_run':False});assert not root.exists()


@pytest.mark.parametrize('command',['render_camera_batch','capture_botanical_views','capture_botanical_projected_coverage'])
def test_broker_delegates_releases_editor_and_restores_after_restart(tmp_path,monkeypatch,command):
    path=tmp_path/'bridge.sock';broker=Broker(path)
    try:
        broker.request('register_worker',{'status':{'session_id':'editing','pid':os.getpid()}})
        op=broker.request('submit',{'owner':'agent','request_id':'render','command':command,'params':{'directory':str(tmp_path/'job')}})
        broker.request('claim',{'session_id':'editing'})
        root=bundle(tmp_path/'job',op=op['operation_id'],state='running');fd=jobs.lock_fd(root);fcntl.flock(fd,fcntl.LOCK_EX)
        receipt={'_external_render':True,'directory':str(root),'render_job_id':'job1','worker_pid':os.getpid(),'estimated_bytes':1024**2}
        completion={'session_id':'editing','operation_id':op['operation_id'],'state':'succeeded','result':receipt}
        broker.request('complete',completion);broker.request('complete',completion)
        assert broker.request('get_operation',{'owner':'agent','operation_id':op['operation_id']})['state']=='running'
        edit=broker.request('submit',{'owner':'agent','request_id':'edit','command':'execute_code','params':{'code':'result=1'}})
        assert broker.request('claim',{'session_id':'editing'})['operation']['operation_id']==edit['operation_id']
        broker.request('detach_worker',{'session_id':'editing'})
        broker.journal.db.close();broker=Broker(path)
        broker.request('register_worker',{'status':{'session_id':'replacement-editor','pid':os.getpid()}})
        # Changing or closing the editor does not interrupt its delegated renderer.
        assert broker.request('get_operation',{'owner':'agent','operation_id':op['operation_id']})['state']=='running'
        import threading
        original_status=jobs.status;retried=threading.Event();attempts=[0]
        def transient(*args):
            attempts[0]+=1
            if attempts[0]==1:raise TimeoutError('transient observation failure')
            retried.set();return original_status(*args)
        monkeypatch.setattr(jobs,'status',transient)
        monitor=threading.Thread(target=broker.monitor_render,args=(op['operation_id'],));monitor.start()
        assert retried.wait(5) and monitor.is_alive()
        assert broker.request('get_operation',{'owner':'agent','operation_id':op['operation_id']})['state']=='running'
        jobs.write_json(root/'status.json',{'job_id':'job1','state':'succeeded'});os.close(fd)
        monitor.join(timeout=5);assert not monitor.is_alive()
        done=broker.request('get_operation',{'owner':'agent','operation_id':op['operation_id']});assert done['state']=='succeeded' and done['result']['valid']
        duplicate=broker.request('submit',{'owner':'agent','request_id':'render','command':command,'params':{'directory':str(root)}})
        assert duplicate['operation_id']==op['operation_id']
    finally:broker.journal.db.close()
