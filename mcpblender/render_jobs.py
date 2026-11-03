"""Dependency-free, owner-scoped isolated render bundle files and lifecycle."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct

from .fluid_files import read_json,write_json,file_hash
from .storage import snapshot
MARKER='.mcpblender-render-job.json'
COMMANDS={'inspect_render_job','validate_render_job','recover_render_job','cleanup_render_job'}
ROOT_FILES={MARKER,'job.json','source.blend','source.blend@','worker.log','status.json','manifest.json','cancel.json','writer.lock'}
TERMINAL={'succeeded','failed','cancelled','interrupted'}

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()
def inventory(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('Expected a real render job directory')
    rows=[]
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            path=Path(parent)/name;rel=path.relative_to(root).as_posix()
            try:s=path.lstat()
            except FileNotFoundError:continue
            allowed=rel in ROOT_FILES or rel.removesuffix('.tmp') in ROOT_FILES or rel=='outputs' or bool(re.fullmatch(r'outputs/c[0-9]{2}_f[0-9]{4}\.(png|exr)(@)?',rel))
            if not allowed or stat.S_ISLNK(s.st_mode):raise ValueError('Unrecognized or symlinked render job entry: '+rel)
            if stat.S_ISDIR(s.st_mode):
                if rel!='outputs':raise ValueError('Unexpected render job directory')
            elif stat.S_ISREG(s.st_mode):rows.append({'path':rel,'bytes':s.st_size,'device':s.st_dev,'inode':s.st_ino})
            else:raise ValueError('Nonregular render job entry')
            if len(rows)>2048:raise ValueError('Render job file limit exceeded')
    return sorted(rows,key=lambda r:r['path'])

def record(root,owner):
    root=Path(root);r=read_json(root/MARKER);s=root.lstat()
    if root.is_symlink() or r.get('kind')!='mcpblender-render-job' or r.get('version')!=1 or r.get('owner')!=owner or [s.st_dev,s.st_ino]!=r.get('identity'):raise ValueError('Render job ownership/identity mismatch')
    return r

def lock_fd(root):
    return os.open(Path(root)/'writer.lock',os.O_RDWR|os.O_NOFOLLOW)

def live(root):
    fd=lock_fd(root)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return True
        return False
    finally:os.close(fd)

def status(root,owner):
    r=record(root,owner);value=read_json(Path(root)/'status.json')
    if value.get('job_id')!=r['id']:raise ValueError('Render status binding mismatch')
    return r,value

def inspect(root,owner):
    r,value=status(root,owner);rows=inventory(root);active=live(root)
    body={'record':r,'status':value,'writer_alive':active,'files':rows}
    return body|{'job_sha256':digest(body),'bytes':sum(v['bytes'] for v in rows),'storage':snapshot(root)}

def cstring(stream,limit=4096):
    data=bytearray()
    for _ in range(limit):
        b=stream.read(1)
        if b==b'\0':return data.decode('utf-8')
        if not b:break
        data.extend(b)
    raise ValueError('Invalid EXR string')

def image_header(path):
    with Path(path).open('rb') as f:
        signature=f.read(8)
        if signature==b'\x89PNG\r\n\x1a\n':
            data=f.read(25)
            if len(data)!=25 or data[:8]!=b'\0\0\0\rIHDR':raise ValueError('Invalid PNG header')
            width,height,depth,color=struct.unpack('>IIBB',data[8:18])
            return {'format':'PNG','width':width,'height':height,'bit_depth':depth,'color_type':color}
        if signature[:4]!=b'v/1\x01' or len(signature)!=8:raise ValueError('Unsupported render image header')
        version=struct.unpack('<I',signature[4:])[0]
        if (version&0xff)!=2 or version&~0x1402:raise ValueError('Unsupported deep/tiled EXR profile')
        multipart=bool(version&0x1000);parts=[];channels=[]
        for part_index in range(32):
            attributes={}
            for _ in range(256):
                name=cstring(f)
                if not name:break
                kind=cstring(f);raw=f.read(4)
                if len(raw)!=4:raise ValueError('Truncated EXR attribute')
                size=struct.unpack('<I',raw)[0]
                if size>1024**2 or f.tell()+size>8*1024**2:raise ValueError('EXR header budget exceeded')
                data=f.read(size)
                if len(data)!=size or name in attributes:raise ValueError('Truncated/duplicate EXR header attribute')
                attributes[name]=(kind,data)
            else:raise ValueError('EXR header attribute limit exceeded')
            if not attributes:
                if multipart and parts:break
                raise ValueError('Missing EXR part header')
            if 'dataWindow' not in attributes or attributes['dataWindow'][0]!='box2i' or len(attributes['dataWindow'][1])!=16:raise ValueError('Missing EXR data window')
            if multipart and attributes.get('type',(None,b''))[1]!=b'scanlineimage':raise ValueError('Unsupported EXR part type')
            x0,y0,x1,y1=struct.unpack('<4i',attributes['dataWindow'][1])
            part_name=attributes.get('name',(None,b''))[1].decode('utf-8')
            kind,data=attributes.get('channels',(None,b''))
            if kind!='chlist':raise ValueError('Missing EXR channels')
            import io
            stream=io.BytesIO(data);part_channels=[]
            for _ in range(512):
                name=cstring(stream)
                if not name:break
                entry=stream.read(16)
                if len(entry)!=16:raise ValueError('Invalid EXR channel entry')
                pixel,linear,xsample,ysample=struct.unpack('<iB3xii',entry)
                if pixel not in {0,1,2} or xsample!=1 or ysample!=1:raise ValueError('Unsupported EXR channel layout')
                item={'name':name,'pixel_type':pixel,'part':part_name};channels.append(item);part_channels.append(name)
            else:raise ValueError('EXR channel limit exceeded')
            if len(channels)>512:raise ValueError('EXR total channel limit exceeded')
            parts.append({'name':part_name,'width':x1-x0+1,'height':y1-y0+1,'channels':part_channels})
            if not multipart:break
        else:raise ValueError('EXR part limit exceeded')
        if any(p['width']!=parts[0]['width'] or p['height']!=parts[0]['height'] for p in parts):raise ValueError('EXR parts have differing dimensions')
        return {'format':'OPEN_EXR_MULTILAYER','width':parts[0]['width'],'height':parts[0]['height'],'multipart':multipart,'parts':parts,'channels':channels}

def validate(root,owner,progress=lambda value:None,cancelled=lambda:False):
    root=Path(root);r=record(root,owner);rows=inventory(root);job=read_json(root/'job.json');saved=read_json(root/'manifest.json')
    if sum(v['bytes'] for v in rows)>job['max_bytes']:raise ValueError('Render bundle exceeds byte budget')
    def checked_hash(path):
        value=hashlib.sha256();done=0
        with Path(path).open('rb') as stream:
            for block in iter(lambda:stream.read(1024**2),b''):
                if cancelled():raise InterruptedError('Render file validation cancelled')
                value.update(block);done+=len(block)
                if done%(16*1024**2)==0:progress({'phase':'verifying render file','file':Path(path).name,'bytes_verified':done})
        return value.hexdigest()
    if saved.get('job_id')!=r['id'] or saved.get('source_sha256')!=job.get('source_sha256') or checked_hash(root/'source.blend')!=job['source_sha256']:raise ValueError('Render source/manifest binding mismatch')
    expected={(ci,fi,fmt) for ci,_ in enumerate(job['cameras']) for fi,_ in enumerate(range(job['frame_start'],job['frame_end']+1,job['frame_step'])) for fmt in job['formats']}
    actual=set();members=[]
    for item in saved['outputs']:
        ci,fi,fmt=item['camera_index'],item['frame_index'],item['format'];key=(ci,fi,fmt)
        suffix='png' if fmt=='PNG' else 'exr';name=f'outputs/c{ci:02}_f{fi:04}.{suffix}'
        if key not in expected or key in actual or item['file']!=name or item['camera']!=job['cameras'][ci] or item['frame']!=job['frame_start']+fi*job['frame_step']:raise ValueError('Render camera/frame association mismatch')
        path=root/name;header=image_header(path)
        if path.stat().st_size!=item['bytes'] or checked_hash(path)!=item['sha256'] or header!=item['header'] or header['width']!=job['width'] or header['height']!=job['height'] or header['format']!=fmt:raise ValueError('Render output hash/header mismatch')
        actual.add(key);members.append(item)
        progress({'phase':'verified render output','completed_files':len(members),'total_files':len(expected)})
    if actual!=expected or {v['path'] for v in rows if v['path'].startswith('outputs/')}!={i['file'] for i in members}:raise ValueError('Render output inventory mismatch')
    return {'valid':True,'directory':str(root),'job_id':r['id'],'outputs':members,'frames':[str(root/v['file']) for v in members if v['format']=='PNG'],'path':str(root/'manifest.json'),'source_sha256':saved['source_sha256']}

def request_cancel(root,owner):
    r=record(root,owner)
    if not live(root):return False
    write_json(Path(root)/'cancel.json',{'job_id':r['id']});return True

def _recover(root,owner,expected,info):
    if info['job_sha256']!=expected:raise ValueError('Render job fingerprint is stale')
    if info['writer_alive']:raise ValueError('Render writer is still active')
    r=info['record'];value=info['status']
    if value['state']=='succeeded':validate(root,owner);return info|{'reconciled':False,'replayed':False}
    if (Path(root)/'manifest.json').is_file():
        validate(root,owner);value.update(state='succeeded',phase='recovered verified files')
    else:value.update(state='interrupted',phase='worker departed; partial files preserved')
    write_json(Path(root)/'status.json',value)
    r,value=status(root,owner);rows=inventory(root);body={'record':r,'status':value,'writer_alive':False,'files':rows}
    return body|{'job_sha256':digest(body),'bytes':sum(v['bytes'] for v in rows),'reconciled':True,'replayed':False}

def _cleanup(root,owner,p,info):
    root=Path(root)
    if info['job_sha256']!=p['expected_job']:raise ValueError('Render job fingerprint is stale')
    allowed={'failed','cancelled'}|({'interrupted'} if p['include_interrupted'] else set())
    if info['writer_alive'] or info['status']['state'] not in allowed:raise ValueError('Cleanup requires an idle owned failed/cancelled or explicitly included interrupted job; success is protected')
    if any(Path(ref).is_relative_to(root) for ref in p.get('_references',[]) if ref):raise ValueError('Current/queued operation references render job')
    if not p['dry_run']:
        fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);out=None
        try:
            if [os.fstat(fd).st_dev,os.fstat(fd).st_ino]!=info['record']['identity']:raise ValueError('Render root changed')
            if (root/'outputs').exists():out=os.open('outputs',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            for row in info['files']:
                name=Path(row['path']).name;parent=out if row['path'].startswith('outputs/') else fd
                s=os.stat(name,dir_fd=parent,follow_symlinks=False)
                if not stat.S_ISREG(s.st_mode) or (s.st_dev,s.st_ino,s.st_size)!=(row['device'],row['inode'],row['bytes']):raise ValueError('Render entry changed before cleanup')
            for row in info['files']:os.unlink(Path(row['path']).name,dir_fd=out if row['path'].startswith('outputs/') else fd)
            if out is not None:os.rmdir('outputs',dir_fd=fd)
        finally:
            if out is not None:os.close(out)
            os.close(fd)
        s=root.lstat()
        if [s.st_dev,s.st_ino]!=info['record']['identity']:raise ValueError('Render root path changed before removal')
        root.rmdir()
    return {'dry_run':p['dry_run'],'bytes':info['bytes'],'files':info['files']}

def exclusive_mutation(root,owner,expected,function):
    info=inspect(root,owner)
    if info['job_sha256']!=expected:raise ValueError('Render job fingerprint is stale')
    fd=lock_fd(root)
    try:
        try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise ValueError('Render writer is still active')
        # Lock ownership is proven here; avoid calling live() through a distinct
        # open description while we hold this mutation's lock.
        r,value=status(root,owner);rows=inventory(root)
        fresh={'record':r,'status':value,'writer_alive':False,'files':rows}
        if digest(fresh)!=expected:raise ValueError('Render job changed before mutation')
        return function(fresh|{'job_sha256':expected,'bytes':sum(v['bytes'] for v in rows)})
    finally:os.close(fd)


def recover(root,owner,expected):
    return exclusive_mutation(root,owner,expected,lambda info:_recover(root,owner,expected,info))


def cleanup(root,owner,p):
    return exclusive_mutation(root,owner,p['expected_job'],lambda info:_cleanup(root,owner,p,info))


def execute(command,p,progress=lambda value:None,cancelled=lambda:False):
    root=p['directory'];owner=p['_job_owner']
    if command=='inspect_render_job':return inspect(root,owner)
    if command=='validate_render_job':return validate(root,owner,progress,cancelled)
    if command=='recover_render_job':return recover(root,owner,p['expected_job'])
    return cleanup(root,owner,p)
