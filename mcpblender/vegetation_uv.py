"""Portable secondary-UV records for owned shared-template LOD profiles."""
import hashlib
import re
import struct
from . import botany

FORMAT='mcpblender-vegetation-secondary-uv-v1'


def uv_digest(rows):
    digest=hashlib.sha256()
    for row in rows:digest.update(struct.pack('<2f',*row))
    return digest.hexdigest()


def validate(record):
    if not isinstance(record,dict) or record.get('format')!=FORMAT or record.get('record_sha256')!=botany.digest({k:v for k,v in record.items() if k!='record_sha256'}):raise ValueError('Secondary UV record binding changed')
    names=record.get('uv_maps');hashes=record.get('uv_witness');channel=record.get('uv_channel');size=record.get('texture_size')
    if not isinstance(names,list) or not 2<=len(names)<=8 or any(not isinstance(n,str) or not n for n in names) or len(set(names))!=len(names):raise ValueError('Invalid secondary UV channel inventory')
    if type(channel)!=int or channel!=len(names)-1 or record.get('uv_map')!=names[-1]:raise ValueError('Secondary UV must be the recorded appended channel')
    if not isinstance(hashes,dict) or set(hashes)!=set(names) or any(not isinstance(v,str) or not re.fullmatch('[a-f0-9]{64}',v) for v in hashes.values()):raise ValueError('Invalid secondary UV coordinate witness')
    if not isinstance(size,list) or len(size)!=2 or any(type(v)!=int or not 1<=v<=32768 for v in size):raise ValueError('Invalid secondary UV texture dimensions')
    if not re.fullmatch('[a-f0-9]{64}',str(record.get('source_lods_sha256',''))):raise ValueError('Invalid secondary UV source guard')
    if record.get('instance_atlas') is not False:raise ValueError('Shared secondary UVs cannot claim an instance lightmap atlas')
    return hashes


def expected(records):
    if not isinstance(records,list) or not 1<=len(records)<=7:raise ValueError('Invalid secondary UV record count')
    result={};previous=[]
    for record in records:
        hashes=validate(record);names=record['uv_maps']
        if previous and (len(names)<=len(previous) or names[:len(previous)]!=previous):raise ValueError('Secondary UV creation order changed')
        if any(name in result and result[name]!=value for name,value in hashes.items()):raise ValueError('Secondary UV baseline changed between revisions')
        result.update(hashes);previous=names
    return result


def verify_maps(records,names,hashes):
    wanted=expected(records)
    for record in records:
        if names[:len(record['uv_maps'])]!=record['uv_maps']:raise ValueError('Secondary UV channel order changed')
    if any(hashes.get(name)!=value for name,value in wanted.items()):raise ValueError('Secondary UV or preserved texture coordinates changed')
    return wanted


def verify(root,records,assets):
    from pathlib import Path
    from .vegetation_interchange import read
    if not isinstance(records,dict) or not records or not set(records)<=set(assets):raise ValueError('Unexpected secondary UV asset roles')
    for asset,entries in records.items():
        sub=read(Path(root)/asset/'manifest.json');names=sub['source']['uv_maps'];rows=sub['witness']['uvs']
        if len(names)!=len(rows) or len(set(names))!=len(names):raise ValueError('Secondary UV exported inventory changed')
        verify_maps(entries,names,{name:uv_digest(values) for name,values in zip(names,rows)})
