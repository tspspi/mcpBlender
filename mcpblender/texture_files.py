"""Bounded and symlink-refusing texture bundle files."""
import hashlib
import os
import stat
from pathlib import Path

from .fluid_files import write_json, read_json, file_hash

MARKER='.mcpblender-texture-job.json'
ROOT_FILES={MARKER,'source.blend','asset.blend','job.json','worker.log','result.json','manifest.json','source.blend@','asset.blend@'}
MAPS={'normal','ao','base_color','roughness','metallic','emission','alpha','coverage','uv_mask'}


def inventory(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('Expected a real texture job directory')
    rows=[];directories=[]
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            path=Path(parent)/name;rel=path.relative_to(root);parts=rel.parts
            try:entry=path.lstat()
            except FileNotFoundError:continue  # Atomic native/JSON rename during progress inspection.
            if stat.S_ISLNK(entry.st_mode):raise ValueError('Texture jobs must not contain symlinks')
            allowed=(len(parts)==1 and (name in ROOT_FILES or name in {v+'.tmp' for v in ROOT_FILES} or name=='textures')) or (len(parts)==2 and parts[0]=='textures' and parts[1] in {m+'.png'+suffix for m in MAPS for suffix in ('','@')})
            if not allowed:raise ValueError(f'Unknown texture job entry: {rel}')
            if stat.S_ISDIR(entry.st_mode):
                if parts!=('textures',):raise ValueError('Unexpected texture job directory')
                directories.append(path)
            elif stat.S_ISREG(entry.st_mode):rows.append({'path':rel.as_posix(),'bytes':entry.st_size})
            else:raise ValueError('Nonregular texture job entry')
            if len(rows)+len(directories)>64:raise ValueError('Texture job inventory limit exceeded')
    return sorted(rows,key=lambda r:r['path']),directories


def deliverables(root):
    return [r for r in inventory(root)[0] if r['path'] in {'source.blend','asset.blend'} or r['path'].endswith('.png')]


def manifest(root):
    return [r|{'sha256':file_hash(Path(root)/r['path'])} for r in deliverables(root)]


def verify_steps(root,expected):
    rows=deliverables(root)
    if rows!=[{'path':r['path'],'bytes':r['bytes']} for r in expected]:raise ValueError('Texture bundle files are missing, changed or unexpected')
    total=sum(r['bytes'] for r in rows);done=0;last=0
    for row in expected:
        digest=hashlib.sha256()
        with (Path(root)/row['path']).open('rb') as stream:
            for block in iter(lambda:stream.read(1024**2),b''):
                digest.update(block);done+=len(block)
                if done-last>=16*1024**2:
                    yield {'phase':'verifying texture bundle','bytes_verified':done,'total_bytes':total};last=done
        if digest.hexdigest()!=row['sha256']:raise ValueError('Texture bundle files are missing, changed or unexpected')
    yield {'phase':'verifying texture bundle','bytes_verified':done,'total_bytes':total}
    return total
