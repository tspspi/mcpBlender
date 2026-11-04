"""Slow status reads retry the same observation without restarting or mutation."""
import asyncio
import pytest
import mcpblender.server as module
from mcpblender.config import Config


@pytest.mark.parametrize('action',['status','get_operation','list_operations'])
def test_read_timeout_repeats_same_request_without_restart(tmp_path,monkeypatch,action):
    config=Config();config.stdio.library_root=str(tmp_path);_,state=module.build_server(config)
    calls=[]
    def call(path,command,params,timeout):
        calls.append((path,command,params.copy(),timeout))
        if len(calls)<3:raise RuntimeError('Bridge timed out; execution may still be running. Do not blindly retry mutations.')
        return {'state':'running','operation_id':'known'}
    def restart(*a,**k):raise AssertionError('Timeout must not restart the broker')
    monkeypatch.setattr(module,'call',call);monkeypatch.setattr(module,'ensure_broker',restart)
    result=asyncio.run(state.control(action,operation_id='known',owner='owner'))
    assert result['state']=='running' and len(calls)==3 and calls[0]==calls[1]==calls[2]


@pytest.mark.parametrize('action',['submit','cancel_operation','restart_broker','retention_apply'])
def test_write_timeout_does_not_repeat_or_restart(tmp_path,monkeypatch,action):
    config=Config();config.stdio.library_root=str(tmp_path);_,state=module.build_server(config);calls=[]
    def call(*args):calls.append(args);raise RuntimeError('Bridge timed out; execution may still be running.')
    monkeypatch.setattr(module,'call',call)
    monkeypatch.setattr(module,'ensure_broker',lambda *a,**k:pytest.fail('Unexpected restart'))
    with pytest.raises(RuntimeError,match='timed out'):asyncio.run(state.control(action,operation_id='known'))
    assert len(calls)==1


def test_repeated_timeout_is_bounded_and_semantic_errors_are_not_retried(tmp_path,monkeypatch):
    config=Config();config.stdio.library_root=str(tmp_path);_,state=module.build_server(config);calls=[]
    def call(*args):calls.append(args);raise RuntimeError('Bridge timed out; execution may still be running.')
    monkeypatch.setattr(module,'call',call)
    with pytest.raises(RuntimeError,match='timed out'):asyncio.run(state.control('get_operation',operation_id='known'))
    assert len(calls)==3
    calls.clear()
    def denied(*args):calls.append(args);raise RuntimeError('Operation not found')
    monkeypatch.setattr(module,'call',denied)
    with pytest.raises(RuntimeError,match='not found'):asyncio.run(state.control('get_operation',operation_id='unknown'))
    assert len(calls)==1
