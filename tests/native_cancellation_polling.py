"""Exercise real bridge polling with a deterministic clock and broker stub."""
import sys,resource
from pathlib import Path
from types import SimpleNamespace
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
sys.path.insert(0,sys.argv[sys.argv.index('--')+1])
from mcpblender.blender import bridge
saved=bridge._bridge;clock=bridge.time;storage=bridge.snapshot
now=[0.];seen=[];cancel=[False]
def control(command,**params):
    assert command=='progress';seen.append(params['progress']);return {'cancel_requested':cancel[0]}
fake=SimpleNamespace(active={'command':'inspect_mesh','operation_id':'fixture'},path=Path('/tmp/unused-polling-fixture'),cancel_requested=False,control=control)
try:
    bridge._bridge=fake;bridge.time=SimpleNamespace(monotonic=lambda:now[0]);bridge.snapshot=lambda *a,**k:{'free_bytes':123456789}
    bridge.report_progress({'phase':'decoding alpha','completed':10,'total':100})
    for _ in range(100000):bridge.check_cancelled()
    assert len(seen)==1
    now[0]=.11;bridge.check_cancelled();assert len(seen)==2 and seen[-1]['phase']=='decoding alpha' and seen[-1]['completed']==10
    # Explicit observations publish immediately, even within a poll interval.
    bridge.report_progress({'phase':'packing maps','completed':2});assert len(seen)==3
    cancel[0]=True;now[0]=.22
    try:bridge.check_cancelled()
    except bridge.OperationCancelled:pass
    else:raise AssertionError('Cancellation not observed at next poll')
    assert len(seen)==4 and seen[-1]['phase']=='packing maps' and seen[-1]['storage']['free_bytes']==123456789
    for _ in range(10):
        try:bridge.check_cancelled()
        except bridge.OperationCancelled:pass
        else:raise AssertionError('Known cancellation was throttled')
    assert len(seen)==4
    # Same reset performed when the bridge claims a new tracked operation.
    fake.cancel_requested=False;fake.last_cancel_poll=float('-inf');fake.last_progress=None;cancel[0]=False
    bridge.check_cancelled();assert len(seen)==5 and seen[-1]['phase']=='checking cancellation'
    print('CANCELLATION_POLLING_COMPLETE',flush=True)
finally:bridge._bridge=saved;bridge.time=clock;bridge.snapshot=storage

# The same bridge functions must observe cancellation from a real durable journal.
import tempfile
from mcpblender.broker import Broker
with tempfile.TemporaryDirectory(prefix='mb-cancel-poll-') as directory:
    broker=Broker(Path(directory)/'bridge.sock')
    try:
        broker.request('register_worker',{'status':{'session_id':'editor','pid':__import__('os').getpid()}})
        op=broker.request('submit',{'owner':'fixture','request_id':'poll','command':'inspect_mesh','params':{}})
        active=broker.request('claim',{'session_id':'editor'})['operation']
        native_control=lambda command,**params:broker.request(command,params|{'session_id':'editor'})
        bridge._bridge=SimpleNamespace(active=active,path=Path(directory)/'bridge.sock',cancel_requested=False,control=native_control)
        bridge.time=SimpleNamespace(monotonic=lambda:now[0]);bridge.snapshot=lambda *a,**k:{'free_bytes':123456789};now[0]=0.
        bridge.report_progress({'phase':'decoding native grid','completed':128,'total':512})
        broker.request('cancel_operation',{'owner':'fixture','operation_id':op['operation_id']});now[0]=.11
        try:bridge.check_cancelled()
        except bridge.OperationCancelled:pass
        else:raise AssertionError('Durable journal cancellation not observed')
        current=broker.request('get_operation',{'owner':'fixture','operation_id':op['operation_id']})
        assert current['cancel_requested'] and current['progress']['phase']=='decoding native grid' and current['progress']['completed']==128
        print('DURABLE_CANCELLATION_POLLING_COMPLETE',flush=True)
    finally:
        bridge._bridge=saved;bridge.time=clock;bridge.snapshot=storage;broker.journal.db.close()
