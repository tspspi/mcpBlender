"""Graph JSON streaming matches eager hashing and releases previous records."""
import gc
import hashlib
import json
import weakref
import pytest
from mcpblender.graph_digest import digest_records


def test_graph_json_bytes_match_reference():
    fields={'frame':1.25,'nested':[{'name':'ö'}],'references':[['a','b']]}
    rows=[{'z':2,'a':[True,None]},['node',-0.0]]
    expected=hashlib.sha256(json.dumps(fields|{'records':rows},sort_keys=True,allow_nan=False).encode()).hexdigest()
    assert digest_records(fields,iter(rows))==expected
    assert digest_records({},iter([]))==hashlib.sha256(b'{"records": []}').hexdigest()
    with pytest.raises(ValueError):digest_records({'records':[]},[])
    with pytest.raises(ValueError):digest_records({},[float('nan')])


def test_only_current_graph_record_is_retained():
    class Entry(dict):pass
    refs=[]
    def entries():
        for i in range(8):
            gc.collect();assert all(r() is None for r in refs)
            row=Entry(value=i);refs.append(weakref.ref(row));yield row
            del row
    assert len(digest_records({'frame':1},entries()))==64
