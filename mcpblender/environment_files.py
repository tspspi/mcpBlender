"""Bounded header admission for static environment textures, before native decode."""
import hashlib
import os
from pathlib import Path
import re
import stat
import struct


def dimensions(header):
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        if len(header)<33 or header[12:16]!=b'IHDR':raise ValueError('Invalid environment PNG header')
        return struct.unpack_from('>II',header,16)
    if header.startswith((b'#?RADIANCE',b'#?RGBE')):
        header=header.replace(b'\r\n',b'\n')
        split=header.find(b'\n\n')
        if split<0:raise ValueError('Radiance header exceeds admission limit')
        match=re.match(rb'([+-][XY])\s+(\d+)\s+([+-][XY])\s+(\d+)\s*\n',header[split+2:])
        if not match or match[1][-1:]==match[3][-1:]:raise ValueError('Unsupported Radiance resolution header')
        values={match[1][-1:]:int(match[2]),match[3][-1:]:int(match[4])}
        return values[b'X'],values[b'Y']
    if header.startswith(b'\x76\x2f\x31\x01'):
        if len(header)<9:raise ValueError('Truncated EXR header')
        version=struct.unpack_from('<I',header,4)[0]
        if version&255!=2 or version&~(255|0x400):raise ValueError('Environment EXR requires single-part non-deep scanline data')
        offset=8;attrs={}
        def string():
            nonlocal offset
            end=header.find(b'\0',offset)
            if end<0 or end-offset>255:raise ValueError('EXR header string exceeds admission limit')
            value=header[offset:end];offset=end+1;return value
        while True:
            name=string()
            if not name:break
            kind=string()
            if offset+4>len(header):raise ValueError('Truncated EXR attribute')
            length=struct.unpack_from('<I',header,offset)[0];offset+=4
            if offset+length>len(header):raise ValueError('EXR header exceeds admission limit')
            if name in attrs:raise ValueError('Duplicate EXR attribute')
            attrs[name]=(kind,header[offset:offset+length]);offset+=length
        data=attrs.get(b'dataWindow');display=attrs.get(b'displayWindow')
        if not data or data[0]!=b'box2i' or len(data[1])!=16 or display!=data:raise ValueError('Environment EXR requires equal data/display windows')
        channels=attrs.get(b'channels')
        if not channels or channels[0]!=b'chlist':raise ValueError('EXR channel list missing')
        payload=channels[1];pos=0;names=[]
        while pos<len(payload) and payload[pos]:
            end=payload.find(b'\0',pos)
            if end<0 or end+17>len(payload):raise ValueError('Invalid EXR channel list')
            name=payload[pos:end];pixel=struct.unpack_from('<i',payload,end+1)[0];sampling=struct.unpack_from('<ii',payload,end+9)
            if name not in {b'R',b'G',b'B',b'A'} or name in names or pixel not in (1,2) or sampling!=(1,1):raise ValueError('Environment EXR requires ordinary HALF/FLOAT RGB(A) channels')
            names.append(name);pos=end+17
        if pos!=len(payload)-1 or not {b'R',b'G',b'B'}<=set(names):raise ValueError('Invalid environment EXR channels')
        lowx,lowy,highx,highy=struct.unpack('<4i',data[1]);return highx-lowx+1,highy-lowy+1
    if header.startswith(b'\xff\xd8'):
        pos=2
        while pos<len(header):
            if header[pos]!=255:break
            while pos<len(header) and header[pos]==255:pos+=1
            if pos>=len(header):break
            kind=header[pos];pos+=1
            if kind in (0,216,217,218) or 208<=kind<=215:break
            if pos+2>len(header):break
            size=struct.unpack_from('>H',header,pos)[0]
            if size<2 or pos+size>len(header):break
            if kind in (192,193,194):
                if size<8:break
                height,width=struct.unpack_from('>HH',header,pos+3);return width,height
            pos+=size
        raise ValueError('JPEG dimensions unavailable within bounded header')
    raise ValueError('Environment image must be PNG, JPEG, Radiance HDR or ordinary scanline EXR')


def inspect(path,max_bytes,max_pixels,checkpoint=lambda:None):
    path=Path(path)
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NONBLOCK),'rb') as stream:
        before=os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0<before.st_size<=max_bytes:raise ValueError('Environment input must be a regular file within max_image_bytes')
        width,height=dimensions(stream.read(65536))
        if not 0<width<=32768 or not 0<height<=32768 or width*height>max_pixels:raise ValueError('Environment image pixel budget exceeded before decode')
        stream.seek(0);digest=hashlib.sha256();size=0
        while chunk:=stream.read(1024**2):
            checkpoint();size+=len(chunk)
            if size>max_bytes:raise ValueError('Environment image grew beyond byte budget')
            digest.update(chunk)
        after=os.fstat(stream.fileno());current=path.stat()
        identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
        if identity(before)!=identity(after) or identity(before)!=identity(current) or size!=before.st_size:raise ValueError('Environment image changed during admission')
    return {'width':width,'height':height,'bytes':size,'sha256':digest.hexdigest(),'rgba32_estimated_bytes':width*height*16}
