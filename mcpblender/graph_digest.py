"""Bounded JSON graph hashing with one streamed records field."""
import hashlib
import json


def digest_records(fields,records):
    if 'records' in fields:raise ValueError('records is the streamed graph field')
    digest=hashlib.sha256();digest.update(b'{')
    def encoded(value):return json.dumps(value,sort_keys=True,allow_nan=False).encode()
    for index,key in enumerate(sorted([*fields,'records'])):
        if index:digest.update(b', ')
        digest.update(encoded(key));digest.update(b': ')
        if key!='records':digest.update(encoded(fields[key]));continue
        digest.update(b'[')
        first=True
        for value in records:
            if not first:digest.update(b', ')
            first=False
            digest.update(encoded(value));del value
        digest.update(b']')
    digest.update(b'}')
    return digest.hexdigest()
