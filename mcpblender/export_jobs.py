"""Owned durable export staging, live-writer locks and non-replaying recovery."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
import uuid

from .storage import snapshot

FORMAT='mcpblender-export-job-v1'
KINDS={'CARD_FAMILY','LOD','PACKAGE','NUMERIC','BOTANICAL','VEGETATION_LOD'}
STATES={'running','verified','ready','interrupted','failed','cancelled','published','cleaning','cleaned'}


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()
def identity(path):
    value=Path(path).lstat()
    return {'device':value.st_dev,'inode':value.st_ino}


def job_root(directory):
    directory=Path(directory).absolute()
    return directory.parent/('.mcpblender-export-'+hashlib.sha256(directory.name.encode()).hexdigest()[:32])


def read_record(root):
    path=root/'record.json';fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        value=os.fstat(stream.fileno())
        if not stat.S_ISREG(value.st_mode) or value.st_uid!=os.geteuid() or value.st_size>2*1024**2:raise ValueError('Invalid export job record')
        record=json.load(stream)
    if not isinstance(record,dict) or record.get('format')!=FORMAT or not isinstance(record.get('state'),str) or record['state'] not in STATES or not isinstance(record.get('id'),str) or not re.fullmatch('[0-9a-f]{32}',record['id']):raise ValueError('Invalid export job ownership/state')
    if not isinstance(record.get('kind'),str) or record['kind'] not in KINDS or not isinstance(record.get('binding'),dict):raise ValueError('Invalid export job profile/binding')
    if record.get('stage')!='staging-'+record['id']:raise ValueError('Invalid export stage name')
    return record


def write_record(root,record):
    path=root/('record-'+uuid.uuid4().hex+'.tmp')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(record,stream,sort_keys=True,allow_nan=False);stream.flush();os.fsync(stream.fileno())
        path.replace(root/'record.json')
        parent=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(parent)
        finally:os.close(parent)
    finally:
        if path.exists():path.unlink()


def directory_check(root):
    value=root.lstat()
    if not stat.S_ISDIR(value.st_mode) or value.st_uid!=os.geteuid() or value.st_mode&0o077:raise ValueError('Export job directory must be real and owned by this OS user')


@contextmanager
def locked(root,*,create=False,blocking=False):
    created=False
    if create:
        try:root.mkdir(mode=0o700);created=True
        except FileExistsError:pass
    directory_check(root)
    flags=os.O_RDWR|os.O_NOFOLLOW|(os.O_CREAT if create else 0)
    fd=os.open(root/'writer.lock',flags,0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode) or os.fstat(fd).st_uid!=os.geteuid():raise ValueError('Invalid export writer lock')
        try:fcntl.flock(fd,fcntl.LOCK_EX|(0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:raise ValueError('Export writer/recovery is active; refuse concurrent access') from None
        yield created
    finally:os.close(fd)


def validate_record(record,directory,owner):
    if record.get('target')!=str(directory):raise ValueError('Export job target binding differs')
    if record.get('owner')!=owner:raise PermissionError('Export job belongs to another MCP owner')


def allowed(record,relative,is_directory):
    parts=relative.split('/')
    if record['kind']=='LOD':
        return not is_directory and len(parts)==1 and (parts[0]=='manifest.json' or re.fullmatch(r'level_0[0-7]\.glb',parts[0]))
    if record['kind']=='CARD_FAMILY':
        from .card_views import DIRECTIONS
        return not is_directory and relative in {'manifest.json','asset.blend',*(v.lower()+'.glb' for v in DIRECTIONS)}
    if record['kind']=='NUMERIC':return not is_directory and len(parts)==1 and parts[0] in {'asset.glb','manifest.json'}
    if record['kind'] in {'BOTANICAL','VEGETATION_LOD'}:
        if len(parts)==1 and parts[0] in {'manifest.json','semantics.json'}:return not is_directory
        asset=(re.fullmatch(r'wood|shoots|leaf-[0-3]',parts[0]) if record['kind']=='BOTANICAL' else re.fullmatch(r'lod-[0-4]-(wood|shoots)|leaf-[0-3]',parts[0]))
        nested=re.fullmatch(r'\.mcpblender-fields-[a-z0-9_]{8}',parts[0])
        if not asset and not nested:return False
        return is_directory if len(parts)==1 else len(parts)==2 and not is_directory and parts[1] in {'asset.glb','manifest.json'}
    if record['kind']!='PACKAGE':return False
    if relative=='manifest.json':return not is_directory
    if parts[0] not in record.get('asset_ids',[]):return False
    if len(parts)==1:return is_directory
    if re.fullmatch(r'lod_0[0-3]|\.mcpblender-lod-[0-9a-f]{32}',parts[1]):
        if len(parts)==2:return is_directory
        return not is_directory and len(parts)==3 and (parts[2]=='manifest.json' or re.fullmatch(r'level_0[0-7]\.glb',parts[2]))
    return len(parts)==2 and not is_directory and (parts[1]=='primary.glb' or re.fullmatch(r'(collision|shadow)_0[0-7]\.glb',parts[1]))


def inventory(root,record):
    if not root.exists():return [],[],0
    if root.is_symlink() or not root.is_dir():raise ValueError('Export stage/output must be a real directory')
    rows=[];dirs=[];total=0
    for parent,directories,files in os.walk(root,followlinks=False):
        for name in directories+files:
            path=Path(parent)/name;info=path.lstat();relative=path.relative_to(root).as_posix();is_directory=stat.S_ISDIR(info.st_mode)
            if not is_directory and not stat.S_ISREG(info.st_mode):raise ValueError('Export job contains symlink/nonregular content')
            if not allowed(record,relative,is_directory):raise ValueError('Unrecognized export job content: '+relative)
            if is_directory:dirs.append(relative)
            else:
                total+=info.st_size
                rows.append({'path':relative,'bytes':info.st_size,'device':info.st_dev,'inode':info.st_ino,'mtime_ns':info.st_mtime_ns})
            if len(rows)+len(dirs)>4096:raise ValueError('Export job inventory exceeds 4096 entries')
    return sorted(rows,key=lambda r:r['path']),sorted(dirs),total


def validate_output(path,record,check_cancelled=lambda:None,progress=None):
    from .lod_files import validate as validate_lods
    from .package_files import validate as validate_package
    check_cancelled();inventory(path,record)
    if record['kind']=='CARD_FAMILY':
        from .card_family_files import validate
        result=validate(path,cancelled=check_cancelled,progress=progress or (lambda v:None))
    elif record['kind'] in {'NUMERIC','BOTANICAL','VEGETATION_LOD'}:
        if any(child.name.startswith('.mcpblender-fields-') for child in Path(path).iterdir()):raise ValueError('Incomplete nested numeric export staging remains')
        if record['kind']=='NUMERIC':
            from .attribute_glb import verify,FORMAT as NUMERIC_FORMAT
            from .vegetation_interchange import read
            manifest=read(Path(path)/'manifest.json')
            if manifest.get('format')!=NUMERIC_FORMAT or manifest.get('asset')!='asset.glb':raise ValueError('Invalid numeric export manifest')
            result=verify(path/'asset.glb',manifest['witness'],cancelled=check_cancelled)
            if result!=manifest['proof']:raise ValueError('Numeric export proof changed')
        else:
            from . import vegetation_interchange,vegetation_lod_files
            if record['kind']=='VEGETATION_LOD':result=vegetation_lod_files.validate(path,cancelled=check_cancelled,progress=progress)
            else:result=vegetation_interchange.validate(path,cancelled=check_cancelled)
    else:result=validate_package(path,check_cancelled) if record['kind']=='PACKAGE' else validate_lods(path)
    check_cancelled()
    manifest=json.loads((path/'manifest.json').read_text())
    if any(manifest.get(key)!=value for key,value in record['binding'].items()):raise ValueError('Export manifest source/animation binding differs from job')
    return result


def inspect(directory,owner):
    directory=Path(directory).absolute();root=job_root(directory);directory_check(root);record=read_record(root);validate_record(record,directory,owner)
    busy=False
    try:
        with locked(root):pass
    except ValueError as exc:
        if 'active' not in str(exc):raise
        busy=True
    stage=root/record['stage'];stage_exists=stage.exists() or stage.is_symlink();target_exists=directory.exists() or directory.is_symlink()
    rows=[];dirs=[];total=0;error=None
    try:
        if stage_exists:
            if record.get('stage_identity')!=identity(stage):raise ValueError('Export stage identity does not match registered ownership')
            rows,dirs,total=inventory(stage,record)
    except (ValueError,OSError) as exc:error=str(exc)
    published_identity=target_exists and record.get('stage_identity')==identity(directory)
    state={'record':record,'stage_files':rows,'stage_directories':dirs,'stage_error':error,'stage_exists':stage_exists,
           'target_exists':target_exists,'target_is_original_stage':bool(published_identity)}
    return state|{'directory':str(directory),'job_directory':str(root),'writer_active':busy,'stage_bytes':total,
                  'job_sha256':digest(state),'storage':snapshot(root),
                  'note':'Recovery does not replay Blender operations or rewrite their broker status. Published target directories are never cleanup candidates.'}


class ExportJob:
    def __init__(self,directory,owner,kind,binding,*,operation_id=None,asset_ids=None):
        self.directory=Path(directory).absolute();self.root=job_root(self.directory);self.owner=owner;self.kind=kind;self.binding={k:v for k,v in binding.items() if v is not None}
        self.operation_id=operation_id;self.asset_ids=asset_ids or [];self.record=None;self.lock=None
    @property
    def stage(self):return self.root/self.record['stage']
    def __enter__(self):
        if self.directory.exists() or self.directory.is_symlink():raise FileExistsError('Export output directory already exists')
        self.lock=locked(self.root,create=True);created=self.lock.__enter__()
        try:
            if (self.root/'record.json').exists():
                previous=read_record(self.root);validate_record(previous,self.directory,self.owner)
                path=self.root/previous['stage']
                if path.exists() or path.is_symlink():raise ValueError('Previous export staging exists; inspect/recover/clean it before retrying')
            elif not created:raise ValueError('Existing export job has no ownership record; refuse adoption')
            token=uuid.uuid4().hex
            self.record={'format':FORMAT,'id':token,'owner':self.owner,'target':str(self.directory),'stage':'staging-'+token,
                         'kind':self.kind,'binding':self.binding,'asset_ids':self.asset_ids,'operation_id':self.operation_id,
                         'state':'running','created_at':time.time(),'writer_pid':os.getpid(),'stage_identity':None}
            write_record(self.root,self.record);return self
        except BaseException:
            self.lock.__exit__(None,None,None);self.lock=None;raise
    def created(self):
        self.record['stage_identity']=identity(self.stage);write_record(self.root,self.record)
    def verify(self,check_cancelled=lambda:None,progress=None):
        if self.record.get('stage_identity')!=identity(self.stage):raise ValueError('Export stage ownership changed')
        last=[time.monotonic()];details=[None]
        def report(value):
            details[0]=dict(value)
            if progress:progress(dict(value))
            last[0]=time.monotonic()
        def check():
            check_cancelled()
            if progress and time.monotonic()-last[0]>=1:
                progress(dict(details[0]) if details[0] is not None else {'phase':'validating durable export stage'});last[0]=time.monotonic();check_cancelled()
        result=validate_output(self.stage,self.record,check,report if progress else None)
        self.record['state']='verified';self.record['verified_at']=time.time();write_record(self.root,self.record)
        if progress:progress({'phase':'verified durable export before publication'});check_cancelled()
        return result
    def __exit__(self,kind,error,traceback):
        try:
            if self.directory.exists() and self.record.get('stage_identity')==identity(self.directory):self.record['state']='published'
            else:self.record['state']='cancelled' if kind and kind.__name__ in {'OperationCancelled','GeneratorExit'} else 'failed'
            self.record['finished_at']=time.time();write_record(self.root,self.record)
        finally:
            self.lock.__exit__(kind,error,traceback);self.lock=None


def recover(directory,owner,expected_job,*,publish=False,check_cancelled=lambda:None,progress=None):
    directory=Path(directory).absolute();root=job_root(directory)
    with locked(root):
        current=inspect(directory,owner)
        # inspect probes our lock as busy; that field is intentionally outside the guard.
        if current['job_sha256']!=expected_job:raise ValueError('Export job fingerprint is stale; inspect again')
        record=current['record'];stage=root/record['stage']
        if current['stage_error']:raise ValueError(current['stage_error'])
        if current['target_is_original_stage']:
            validate_output(directory,record,check_cancelled,progress);record['state']='published'
        elif current['stage_exists']:
            try:validate_output(stage,record,check_cancelled,progress)
            except InterruptedError:raise
            except (ValueError,OSError,KeyError) as exc:
                if publish:raise ValueError('Incomplete/invalid export cannot be published: '+str(exc)) from exc
                record['state']='interrupted';record['validation_error']=str(exc);record.pop('verified_at',None)
            else:
                record['state']='ready'
                if publish:
                    if current['target_exists']:raise FileExistsError('Output exists; refuse recovered publication')
                    check_cancelled();stage.rename(directory);record['state']='published'
        elif current['target_exists']:raise ValueError('Output identity differs from registered export; refuse adoption')
        else:record['state']='interrupted'
        record['recovered_at']=time.time();write_record(root,record)
    return inspect(directory,owner)|{'replayed':False}



@contextmanager
def anchored_parent(root_fd,relative):
    parts=relative.split('/');fd=os.dup(root_fd)
    try:
        for part in parts[:-1]:
            following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=following
        yield fd,parts[-1]
    finally:os.close(fd)


def delete_owned(root,stage,record,rows,dirs,check_cancelled):
    fd=os.open(stage,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        info=os.fstat(fd)
        if {'device':info.st_dev,'inode':info.st_ino}!=record['stage_identity']:raise ValueError('Export stage changed before cleanup')
        for row in rows:
            with anchored_parent(fd,row['path']) as (parent,name):
                info=os.stat(name,dir_fd=parent,follow_symlinks=False)
                actual={'device':info.st_dev,'inode':info.st_ino,'bytes':info.st_size,'mtime_ns':info.st_mtime_ns}
                if not stat.S_ISREG(info.st_mode) or any(actual[k]!=row[k] for k in actual):raise ValueError('Export file changed before cleanup')
        record['state']='cleaning';write_record(root,record)
        for row in rows:
            check_cancelled()
            with anchored_parent(fd,row['path']) as (parent,name):os.unlink(name,dir_fd=parent)
        for path in sorted(dirs,key=lambda p:len(p.split('/')),reverse=True):
            with anchored_parent(fd,path) as (parent,name):os.rmdir(name,dir_fd=parent)
    finally:os.close(fd)
    parent=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        info=os.stat(stage.name,dir_fd=parent,follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode) or {'device':info.st_dev,'inode':info.st_ino}!=record['stage_identity']:raise ValueError('Export stage path changed after cleanup')
        os.rmdir(stage.name,dir_fd=parent)
    finally:os.close(parent)

def cleanup(directory,owner,expected_job,*,dry_run=True,discard_ready=False,references=(),check_cancelled=lambda:None):
    directory=Path(directory).absolute();root=job_root(directory)
    with locked(root):
        current=inspect(directory,owner)
        if current['job_sha256']!=expected_job:raise ValueError('Export job fingerprint is stale; inspect again')
        record=current['record'];stage=root/record['stage']
        if current['stage_error']:raise ValueError(current['stage_error'])
        if record['state']=='published' or current['target_is_original_stage']:raise ValueError('Published deliverables are protected from cleanup')
        if record['state'] in {'running','cleaning'}:raise ValueError('Recover the interrupted export before cleanup')
        if current['stage_exists'] and (record['state'] in {'ready','verified'} or record.get('verified_at') is not None) and not discard_ready:raise ValueError('Validated ready output is protected; explicitly set discard_ready=true')
        if any(Path(p).absolute().is_relative_to(stage) for p in references if p):raise ValueError('Current project references this export staging')
        rows=current['stage_files'];dirs=current['stage_directories']
        if not dry_run:
            # Refuse any inventory drift before touching owned files.
            if inspect(directory,owner)['job_sha256']!=expected_job:raise ValueError('Export job changed during cleanup')
            if current['stage_exists']:delete_owned(root,stage,record,rows,dirs,check_cancelled)
            record['state']='cleaned';record['cleaned_at']=time.time();write_record(root,record)
        return {'dry_run':dry_run,'files':rows,'bytes':current['stage_bytes'],'published_directory_preserved':True}


def list_jobs(directory,owner,*,depth=2,limit=20,offset=0,include_finished=False,check_cancelled=lambda:None):
    base=Path(directory).absolute();pending=[(base,0)];jobs=[];scanned=0;entries=0;eligible=0;truncated=False
    while pending:
        parent,level=pending.pop(0);check_cancelled();scanned+=1
        if scanned>128:truncated=True;break
        try:children=os.scandir(parent)
        except OSError:continue
        with children:
            for child in children:
                entries+=1
                if entries>8192:truncated=True;break
                if not child.is_dir(follow_symlinks=False):continue
                root=Path(child.path)
                if re.fullmatch(r'\.mcpblender-export-[0-9a-f]{32}',child.name):
                    try:
                        record=read_record(root)
                        if record.get('owner')!=owner or job_root(record['target'])!=root:continue
                        if not include_finished and record['state'] in {'published','cleaned'}:continue
                        eligible+=1
                        if eligible<=offset:continue
                        check_cancelled();info=inspect(record['target'],owner)
                        summary={k:info[k] for k in ('directory','job_directory','writer_active','stage_bytes','job_sha256','stage_exists','stage_error','target_exists','target_is_original_stage','storage')}
                        summary['record']={k:record.get(k) for k in ('id','owner','state','kind','operation_id','created_at','finished_at')}
                        jobs.append(summary)
                    except (ValueError,KeyError,OSError):continue
                    if len(jobs)>=limit:truncated=True;break
                elif level<depth and not child.name.startswith('.'):pending.append((root,level+1))
        if truncated:break
    return {'jobs':jobs,'next_offset':offset+len(jobs) if truncated and jobs else None,'scan_truncated':truncated,'scanned_directories':min(scanned,128),
            'note':'Only recognized journals belonging to this owner; at most 128 directories/8192 entries. Narrow the directory/depth when truncated. Unknown/foreign/unsafe records are not adopted.'}

COMMANDS={'list_export_jobs','inspect_export_job','recover_export_job','cleanup_export_job'}


def execute(command,params,progress,cancelled):
    details=[None]
    def report(value):
        details[0]=dict(value);progress(dict(value))
    def check():
        progress(dict(details[0]) if details[0] is not None else {'phase':'checking export job recovery','directory':params['directory']})
        if cancelled():raise InterruptedError('Export job recovery cancelled before a cooperative boundary')
    check();owner=params['_job_owner']
    if command=='list_export_jobs':
        result=list_jobs(params['directory'],owner,depth=params.get('depth',2),limit=params.get('limit',20),offset=params.get('offset',0),include_finished=params.get('include_finished',False),check_cancelled=check)
    elif command=='inspect_export_job':result=inspect(params['directory'],owner)
    elif command=='recover_export_job':
        result=recover(params['directory'],owner,params['expected_job'],publish=params.get('publish',False),check_cancelled=check,progress=report)
    else:
        result=cleanup(params['directory'],owner,params['expected_job'],dry_run=params.get('dry_run',True),discard_ready=params.get('discard_ready',False),references=params.get('_references',()),check_cancelled=check)
    policy=params.get('_storage_policy',{});storage={'reserve_bytes':policy.get('reserve_bytes',256*1024**2),'warn_below_bytes':policy.get('warn_below_bytes',2*1024**3)}
    result['storage']=snapshot(params['directory'],**storage)
    for job in result.get('jobs',[]):job['storage']=snapshot(job['job_directory'],**storage)
    return result
