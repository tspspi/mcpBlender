"""Bounded float32 NONE/ZIPS/ZIP scanline reader for native reference passes.

Layout: https://openexr.com/en/latest/OpenEXRFileLayout.html
ZIP byte prediction/reordering follows the OpenEXR reference format. This is
not a general EXR reader: deep/tiled, subsampled, half/integer and other codecs
are deliberately outside this data-capture profile. Rows are top to bottom.
"""
from array import array
import hashlib
import io
import os
from pathlib import Path
import stat
import struct
import sys
import zlib
from .render_jobs import cstring

MAX_FILE_BYTES=512*1024**2
MAX_OUTPUT_BYTES=256*1024**2
MAX_DECODED_BYTES=512*1024**2
MAX_CHUNK_BYTES=8*1024**2


def read(stream,count):
    data=stream.read(count)
    if len(data)!=count:raise ValueError('Truncated EXR data')
    return data


def scalar(attributes,name,kind,fmt):
    item=attributes.get(name)
    if not item or item[0]!=kind or len(item[1])!=struct.calcsize(fmt):raise ValueError('Invalid EXR attribute: '+name)
    return struct.unpack(fmt,item[1])


def headers(stream):
    signature=read(stream,8);version=struct.unpack('<I',signature[4:])[0]
    if signature[:4]!=b'v/1\x01' or version&0xff!=2 or version&~0x1402:raise ValueError('Unsupported EXR version/deep/tiled profile')
    multipart=bool(version&0x1000);parts=[];names=set();channels=set()
    # A multipart header list has one extra empty-header terminator. Count
    # actual parts, so exactly 32 parts still leave room to read that byte.
    for _ in range(33):
        attributes={}
        for _ in range(256):
            name=cstring(stream)
            if not name:break
            kind=cstring(stream);size=struct.unpack('<I',read(stream,4))[0]
            if size>1024**2 or stream.tell()+size>8*1024**2:raise ValueError('EXR header byte budget exceeded')
            if name in attributes:raise ValueError('Duplicate EXR header attribute')
            attributes[name]=(kind,read(stream,size))
        else:raise ValueError('EXR attribute budget exceeded')
        if not attributes:
            if multipart and parts:break
            raise ValueError('Missing EXR header')
        if len(parts)>=32:raise ValueError('EXR part budget exceeded')
        name=attributes.get('name',('string',b''))[1].decode('utf-8')
        if name in names:raise ValueError('Duplicate EXR part name')
        names.add(name)
        if multipart and attributes.get('type')!=('string',b'scanlineimage'):raise ValueError('Only scanline EXR parts are supported')
        window=scalar(attributes,'dataWindow','box2i','<4i');x0,y0,x1,y1=window;w=x1-x0+1;h=y1-y0+1
        if not 1<=w<=2048 or not 1<=h<=2048 or w*h>4*1024**2:raise ValueError('EXR pixel budget exceeded')
        codec,=scalar(attributes,'compression','compression','<B')
        if codec not in {0,2,3}:raise ValueError('EXR decoder supports NONE/ZIPS/ZIP only')
        order,=scalar(attributes,'lineOrder','lineOrder','<B')
        if order not in {0,1}:raise ValueError('Unsupported EXR scanline order')
        item=attributes.get('channels')
        if not item or item[0]!='chlist':raise ValueError('Missing EXR channels')
        source=io.BytesIO(item[1]);part_channels=[]
        for _ in range(512):
            channel=cstring(source)
            if not channel:break
            pixel,linear,xsample,ysample=struct.unpack('<iB3xii',read(source,16))
            if pixel!=2 or xsample!=1 or ysample!=1:raise ValueError('EXR decoder requires full-resolution float32 channels')
            if channel in channels:raise ValueError('Duplicate EXR channel name')
            channels.add(channel);part_channels.append(channel)
        else:raise ValueError('EXR channel budget exceeded')
        if not part_channels or source.read(1) or len(channels)>512:raise ValueError('Invalid EXR channel list')
        lines=16 if codec==3 else 1;count=(h+lines-1)//lines
        if 'chunkCount' in attributes:
            stored,=scalar(attributes,'chunkCount','int','<i')
            if stored!=count:raise ValueError('EXR chunk count mismatch')
        elif multipart:raise ValueError('Missing multipart EXR chunk count')
        parts.append({'name':name,'window':window,'width':w,'height':h,'channels':part_channels,'codec':codec,'lines':lines,'count':count})
        if not multipart:break
    else:raise ValueError('EXR part budget exceeded')
    if any(p['window']!=parts[0]['window'] for p in parts):raise ValueError('EXR data windows differ')
    return multipart,parts


def unpack_zip(packed,expected,cancelled):
    try:
        inflater=zlib.decompressobj();data=inflater.decompress(packed,expected+1)
    except zlib.error as exc:raise ValueError('Invalid EXR ZIP stream') from exc
    if len(data)!=expected or not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:raise ValueError('EXR ZIP stream length mismatch')
    predicted=bytearray(data);previous=predicted[0]
    for i in range(1,len(predicted)):
        if i%65536==0:cancelled()
        previous=(previous+predicted[i]-128)&255;predicted[i]=previous
    output=bytearray(expected);split=(expected+1)//2
    output[::2]=predicted[:split];output[1::2]=predicted[split:]
    return output


def decode(path,channels,*,expected_sha256=None,max_pixels=4*1024**2,cancelled=lambda:None,progress=lambda value:None):
    if type(max_pixels) is not int or not 1<=max_pixels<=4*1024**2:raise ValueError('Invalid EXR pixel budget')
    requested=set(channels)
    if not requested or len(requested)!=len(channels) or len(requested)>32:raise ValueError('Request 1..32 distinct EXR channels')
    descriptor=os.open(Path(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 0<before.st_size<=MAX_FILE_BYTES:raise ValueError('EXR file byte budget exceeded or nonregular file')
    except BaseException:
        os.close(descriptor);raise
    with os.fdopen(descriptor,'rb') as stream:
        multipart,parts=headers(stream);present={n for p in parts for n in p['channels']}
        if not requested<=present:raise ValueError('Requested EXR channels missing: '+', '.join(sorted(requested-present)))
        width=parts[0]['width'];height=parts[0]['height'];pixels=width*height
        if pixels>max_pixels:raise ValueError('EXR pixel budget exceeded')
        if pixels*len(requested)*4>MAX_OUTPUT_BYTES:raise ValueError('EXR output memory budget exceeded')
        chosen=[p for p in parts if requested.intersection(p['channels'])]
        if sum(pixels*len(p['channels'])*4 for p in chosen)>MAX_DECODED_BYTES:raise ValueError('EXR decompression work budget exceeded')
        for p in parts:p['offsets']=struct.unpack('<'+str(p['count'])+'Q',read(stream,p['count']*8))
        table_end=stream.tell();chunks=[];intervals=[]
        for pi,p in enumerate(parts):
            for index,offset in enumerate(p['offsets']):
                cancelled();head_size=12 if multipart else 8
                if not table_end<=offset<=before.st_size-head_size:raise ValueError('EXR chunk offset outside data')
                stream.seek(offset)
                if multipart and struct.unpack('<i',read(stream,4))[0]!=pi:raise ValueError('EXR chunk part mismatch')
                y,size=struct.unpack('<iI',read(stream,8));expected_y=p['window'][1]+index*p['lines']
                rows=min(p['lines'],p['height']-index*p['lines']);raw_size=rows*p['width']*len(p['channels'])*4
                if y!=expected_y or not 0<size<=raw_size or p['codec']==0 and size!=raw_size:raise ValueError('EXR chunk row/size mismatch')
                end=offset+head_size+size
                if end>before.st_size:raise ValueError('Truncated EXR chunk')
                intervals.append((offset,end))
                if p in chosen:
                    if raw_size>MAX_CHUNK_BYTES:raise ValueError('EXR chunk memory budget exceeded')
                    chunks.append((p,index,offset+head_size,size,raw_size,rows))
        end=table_end
        for start,stop in sorted(intervals):
            if start!=end:raise ValueError('Overlapping or unreferenced EXR chunk data')
            end=stop
        if end!=before.st_size:raise ValueError('Unreferenced EXR trailing data')
        values={name:array('f',[0.])*pixels for name in requested}
        for completed,(p,index,offset,size,raw_size,rows) in enumerate(chunks):
            cancelled();stream.seek(offset);packed=read(stream,size)
            raw=packed if size==raw_size else unpack_zip(packed,raw_size,cancelled)
            position=0;stride=width*4
            for row in range(rows):
                y=index*p['lines']+row;start=y*width
                for name in p['channels']:
                    if name in values:
                        line=array('f');line.frombytes(raw[position:position+stride])
                        if sys.byteorder!='little':line.byteswap()
                        values[name][start:start+width]=line
                    position+=stride
            progress({'phase':'decoding EXR reference passes','completed':completed+1,'total':len(chunks)})
        cancelled();stream.seek(0);digest=hashlib.sha256()
        for block in iter(lambda:stream.read(1024**2),b''):cancelled();digest.update(block)
        after=os.fstat(stream.fileno());identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if identity(before)!=identity(after):raise ValueError('EXR file changed during decoding')
        sha=digest.hexdigest()
        if expected_sha256 is not None and sha!=expected_sha256:raise ValueError('Decoded EXR source hash mismatch')
    return {'width':width,'height':height,'data_window':parts[0]['window'],'channels':values,'sha256':sha}
