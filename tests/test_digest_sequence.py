"""Canonical sequence hashing stays compatible without retaining past entries."""
import gc
import weakref
import pytest
from mcpblender.botany import digest,digest_sequence


def test_streamed_array_matches_eager_canonical_bytes():
    for values in ([],[None,True,False,1,-2,1.25,-0.0],[(1,'ö\n'),{'z':[1,2],'a':{'x':3}}]):
        assert digest_sequence(iter(values))==digest(values)
    with pytest.raises(ValueError):digest_sequence(iter([{'x':float('nan')}]))


def test_prior_records_are_released_before_requesting_next():
    class Record(dict):pass
    references=[]
    def source():
        for i in range(20):
            gc.collect()
            assert all(ref() is None for ref in references)
            value=Record(number=i);references.append(weakref.ref(value));yield value
            del value
    assert digest_sequence(source())==digest([{'number':i} for i in range(20)])
