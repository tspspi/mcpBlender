"""Dead bundle writers retain only owned, discoverable and guarded staging."""
import json
from pathlib import Path
import subprocess
import sys
import pytest
from mcpblender.export_jobs import inspect,recover,cleanup,list_jobs


@pytest.mark.parametrize('kind,component',[('NUMERIC',None),('BOTANICAL','wood'),('VEGETATION_LOD','lod-0-wood')])
def test_dead_partial_bundle_and_nested_numeric_cleanup(tmp_path,kind,component):
    target=tmp_path/'delivery'
    script="""
import os,sys
from mcpblender.export_jobs import ExportJob
with ExportJob(sys.argv[1],'owner-a',sys.argv[2],{}) as job:
    job.stage.mkdir();job.created()
    if sys.argv[3]=='none':path=job.stage/'asset.glb'
    else:
        nested=job.stage/'.mcpblender-fields-abcdefgh';nested.mkdir();path=nested/'asset.glb'
        (job.stage/sys.argv[3]).mkdir()
    path.write_bytes(b'partial');os._exit(23)
"""
    process=subprocess.run([sys.executable,'-c',script,str(target),kind,component or 'none'],capture_output=True,text=True,timeout=30)
    assert process.returncode==23,process.stderr
    state=inspect(target,'owner-a');assert not state['writer_active'] and state['stage_bytes']==7
    with pytest.raises(PermissionError):inspect(target,'owner-b')
    assert list_jobs(tmp_path,'owner-a')['jobs'][0]['record']['kind']==kind
    interrupted=recover(target,'owner-a',state['job_sha256']);assert interrupted['record']['state']=='interrupted' and not interrupted['replayed']
    with pytest.raises(ValueError,match='Incomplete'):recover(target,'owner-a',interrupted['job_sha256'],publish=True)
    dry=cleanup(target,'owner-a',interrupted['job_sha256']);assert dry['bytes']==7 and dry['dry_run']
    cleanup(target,'owner-a',interrupted['job_sha256'],dry_run=False)
    assert not inspect(target,'owner-a')['stage_exists'] and not target.exists()


def test_nested_unknown_file_refuses_cleanup(tmp_path):
    target=tmp_path/'delivery'
    from mcpblender.export_jobs import ExportJob
    with ExportJob(target,'owner-a','BOTANICAL',{}) as job:
        job.stage.mkdir();job.created();nested=job.stage/'.mcpblender-fields-abcdefgh';nested.mkdir();foreign=nested/'foreign.txt';foreign.write_text('preserve')
    state=inspect(target,'owner-a');assert state['stage_error']
    with pytest.raises(ValueError,match='Unrecognized'):recover(target,'owner-a',state['job_sha256'])
    with pytest.raises(ValueError,match='Unrecognized'):cleanup(target,'owner-a',state['job_sha256'],dry_run=False)
    assert foreign.read_text()=='preserve'


def numeric_bundle(root):
    """Small actual custom-field GLB, independent of Blender or live test artifacts."""
    import struct
    from mcpblender.attribute_glb import FORMAT,verify
    binary=struct.pack('<15f',0,0,0,1,0,0,0,0,-1,0,1,2,0,.5,1)
    document={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(binary)}],
        'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':36},{'buffer':0,'byteOffset':36,'byteLength':12},{'buffer':0,'byteOffset':48,'byteLength':12}],
        'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3'},{'bufferView':1,'componentType':5126,'count':3,'type':'SCALAR'},{'bufferView':2,'componentType':5126,'count':3,'type':'SCALAR'}],
        'meshes':[{'primitives':[{'attributes':{'POSITION':0,'_MCP_CORNER':1,'_MCP_F00_C0':2}}]}],'nodes':[{'mesh':0}],'scenes':[{'nodes':[0]}],'scene':0}
    encoded=json.dumps(document).encode();encoded+=b' '*(-len(encoded)%4)
    data=struct.pack('<4sII',b'glTF',2,28+len(encoded)+len(binary))+struct.pack('<I4s',len(encoded),b'JSON')+encoded+struct.pack('<I4s',len(binary),b'BIN\x00')+binary
    (root/'asset.glb').write_bytes(data)
    witness={'format':FORMAT,'positions':[[0,0,0],[1,0,0],[0,1,0]],'uvs':[],'triangles':[[0,1,2]],'fields':[{'semantic':'_MCP_F00_C0','components':1,'values':[[0],[.5],[1]]}]}
    (root/'manifest.json').write_text(json.dumps({'format':FORMAT,'asset':'asset.glb','witness':witness,'proof':verify(root/'asset.glb',witness),'export_sha256':'a'*64}))


def test_cancelled_verified_output_needs_explicit_discard(tmp_path):
    from mcpblender.export_jobs import ExportJob
    class OperationCancelled(Exception):pass
    target=tmp_path/'complete'
    with pytest.raises(OperationCancelled):
        with ExportJob(target,'owner-a','NUMERIC',{'export_sha256':'a'*64}) as job:
            job.stage.mkdir();job.created();numeric_bundle(job.stage);job.verify()
            raise OperationCancelled('after durable verification')
    state=inspect(target,'owner-a');assert state['record']['state']=='cancelled' and state['record']['verified_at']
    with pytest.raises(ValueError,match='protected'):cleanup(target,'owner-a',state['job_sha256'],dry_run=False)
    cleanup(target,'owner-a',state['job_sha256'],dry_run=False,discard_ready=True)
    assert not inspect(target,'owner-a')['stage_exists'] and not target.exists()


def test_verification_heartbeat_observes_remote_cancellation(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import time
    from mcpblender import export_jobs as jobs
    now=[0.];cancelled=[False];phases=[]
    def clock():now[0]+=1.1;return now[0]
    monkeypatch.setattr(jobs,'time',SimpleNamespace(time=time.time,monotonic=clock))
    class OperationCancelled(Exception):pass
    def check():
        if cancelled[0]:raise OperationCancelled('remote cancellation')
    def progress(value):phases.append(value['phase']);cancelled[0]=True
    target=tmp_path/'heartbeat'
    with pytest.raises(OperationCancelled):
        with jobs.ExportJob(target,'owner-a','NUMERIC',{'export_sha256':'a'*64}) as job:
            job.stage.mkdir();job.created();numeric_bundle(job.stage);job.verify(check,progress)
    assert 'validating durable export stage' in phases
    assert jobs.inspect(target,'owner-a')['record']['state']=='cancelled' and not target.exists()
