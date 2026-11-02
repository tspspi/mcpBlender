"""Bounded, symlink-refusing fluid bundle inventory; no bpy dependency."""
import hashlib
import json
import os
import re
from pathlib import Path

MARKER=".mcpblender-fluid-job.json"
ROOT_FILES={MARKER,"job.json","worker.log","result.json","manifest.json","source.blend","asset.blend"}
ROOT_FILES |= {"source.blend@", "asset.blend@"}
CACHE_DIRS={"config","data","mesh","noise","particles","guiding"}


def write_json(path,value):
    path=Path(path);temporary=path.with_name(path.name+".tmp")
    with temporary.open("w") as stream:
        json.dump(value,stream,sort_keys=True,allow_nan=False);stream.flush();os.fsync(stream.fileno())
    temporary.replace(path)


def read_json(path):
    path=Path(path)
    if path.is_symlink() or path.stat().st_size>8*1024**2:raise ValueError("Invalid fluid metadata file")
    return json.loads(path.read_text())


def inventory(root):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError("Expected a real fluid job directory")
    rows=[];directories=[]
    for parent,dirs,files in os.walk(root,followlinks=False):
        for name in dirs+files:
            path=Path(parent)/name;rel=path.relative_to(root);parts=rel.parts
            if path.is_symlink():raise ValueError("Fluid jobs must not contain symlinks")
            if len(parts)==1:
                allowed=name in ROOT_FILES or name in {"cache"} or name in {p+".tmp" for p in ROOT_FILES}
            else:allowed=parts[0]=="cache" and (len(parts)==2 and path.is_dir() and parts[1] in CACHE_DIRS or len(parts)==3 and parts[1] in CACHE_DIRS and bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*_[0-9]{4,6}\.(?:uni|vdb|bobj\.gz|obj\.gz)(?:\.tmp)?",parts[2])))
            if not allowed:raise ValueError(f"Unknown fluid job entry: {rel}")
            if path.is_dir():directories.append(path)
            elif path.is_file():rows.append({"path":rel.as_posix(),"bytes":path.stat().st_size})
            else:raise ValueError("Nonregular fluid job entry")
            if len(rows)+len(directories)>10000:raise ValueError("Fluid job inventory limit exceeded")
    return sorted(rows,key=lambda r:r["path"]),directories


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda:stream.read(1024**2),b""):digest.update(block)
    return digest.hexdigest()


def manifest(root):
    rows,_=inventory(root)
    return [row|{"sha256":file_hash(Path(root)/row["path"])} for row in rows
            if row["path"].startswith("cache/") or row["path"]=="asset.blend"]


def verify(root,expected):
    actual=manifest(root)
    if actual!=expected:raise ValueError("Fluid bundle files are missing, changed or unexpected")
    return sum(row["bytes"] for row in actual)


def verify_steps(root,expected):
    """Hash in bounded batches so the bridge can report progress and cancel."""
    rows,_=inventory(root)
    actual=[r for r in rows if r["path"].startswith("cache/") or r["path"]=="asset.blend"]
    if actual!=[{"path":r["path"],"bytes":r["bytes"]} for r in expected]:
        raise ValueError("Fluid bundle files are missing, changed or unexpected")
    total=sum(r["bytes"] for r in actual);done=0;last=0;batch=0
    for row in expected:
        digest=hashlib.sha256()
        with (Path(root)/row["path"]).open("rb") as stream:
            for block in iter(lambda:stream.read(1024**2),b""):
                digest.update(block);done+=len(block)
                if done-last>=16*1024**2:
                    yield {"phase":"verifying fluid bundle","bytes_verified":done,"total_bytes":total};last=done
        if digest.hexdigest()!=row["sha256"]:raise ValueError("Fluid bundle files are missing, changed or unexpected")
        batch+=1
        if batch==32:
            yield {"phase":"verifying fluid bundle","bytes_verified":done,"total_bytes":total};last=done;batch=0
    yield {"phase":"verifying fluid bundle","bytes_verified":done,"total_bytes":total}
    return total
