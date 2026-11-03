"""Isolated camera/frame render batches and owned file-job lifecycle."""
from typing import Literal
from pydantic import Field,model_validator
from .config import Model
from .nla_contracts import SafeName
from .mesh_contracts import Digest
class Batch(Model):
    directory: str = Field(min_length=1)
    expected_settings: Digest
    cameras: list[SafeName] = Field(min_length=1,max_length=16)
    frame_start: int = Field(strict=True,ge=-1048574,le=1048574)
    frame_end: int = Field(strict=True,ge=-1048574,le=1048574)
    frame_step: int = Field(default=1,strict=True,ge=1,le=10000)
    width: int = Field(default=640,strict=True,ge=16,le=4096)
    height: int = Field(default=480,strict=True,ge=16,le=4096)
    engine: Literal['CYCLES','BLENDER_EEVEE_NEXT'] = 'CYCLES'
    samples: int = Field(default=32,strict=True,ge=1,le=1024)
    formats: list[Literal['PNG','OPEN_EXR_MULTILAYER']] = Field(default=['PNG'],min_length=1,max_length=2)
    threads: int = Field(default=2,strict=True,ge=1,le=16)
    max_bytes: int = Field(default=4*1024**3,strict=True,ge=1024**2,le=128*1024**3)
    timeout_seconds: int = Field(default=3600,strict=True,ge=10,le=86400)
    @model_validator(mode='after')
    def bounded(self):
        if self.frame_end<self.frame_start or (self.frame_end-self.frame_start)//self.frame_step+1>1000:raise ValueError('Render batch supports 1..1000 frame samples')
        if len(set(self.cameras))!=len(self.cameras) or len(set(self.formats))!=len(self.formats):raise ValueError('Cameras and formats must be distinct')
        if len(self.cameras)*((self.frame_end-self.frame_start)//self.frame_step+1)>1000:raise ValueError('Render batch supports at most 1000 camera/frame renders')
        return self
class Directory(Model):
    directory: str = Field(min_length=1)
class Guard(Directory):
    expected_job: Digest
class Cleanup(Guard):
    dry_run: bool = True
    include_interrupted: bool = False
COMMANDS={
 'render_camera_batch':(Batch,('allow_snapshots','allow_library_write','allow_start_blender'),'Snapshot the current project and render named cameras/frame samples in an independent owned Blender worker. Original operation stays running in the broker while editing continues. PNG and/or multilayer EXR, per-render progress/free space, cancellation, timeout and byte limits; no automatic replay after death.'),
 'inspect_render_job':(Directory,(),'Inspect an owned isolated render job, file-writer lock, progress, inventory and cleanup guard without Blender.'),
 'validate_render_job':(Directory,(),'Independently verify a completed render bundle: source/file hashes, camera/frame/format associations and PNG/EXR dimensions/channel headers. Does not certify image quality or decode every pixel.'),
 'recover_render_job':(Guard,('allow_library_write',),'Reconcile a departed isolated render worker without replay. Requires a fresh guard and no writer; valid finished files may be adopted, partial jobs become interrupted.'),
 'cleanup_render_job':(Cleanup,('allow_library_write',),'Preview/remove owned failed/cancelled partial render bundles with a fresh guard and no writer. Interrupted inclusion is explicit; successful bundles and current/queued references are protected.'),
}
