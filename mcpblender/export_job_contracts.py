"""File-only export recovery, isolated from Blender and remote-owner scoped."""
from pydantic import Field
from .config import Model
from .mesh_contracts import Digest


class Inspect(Model):
    directory: str = Field(min_length=1)


class Guard(Inspect):
    expected_job: Digest


class Recover(Guard):
    publish: bool = False


class Cleanup(Guard):
    dry_run: bool = True
    discard_ready: bool = False


class ListJobs(Model):
    directory: str = '.'
    depth: int = Field(default=2,ge=0,le=4)
    limit: int = Field(default=20,ge=1,le=100)
    offset: int = Field(default=0,ge=0,le=8192)
    include_finished: bool = False


COMMANDS={
 'inspect_export_job':(Inspect,(),'Inspect the current MCP owner\'s durable LOD/package/numeric/botanical export job, live-writer lock, stage identity/inventory and free storage. Works without Blender; does not replay work.'),
 'recover_export_job':(Recover,('allow_library_write',),'Reconcile an abandoned owned export without replaying Blender. Validate completed files, report ready or published output, optionally publish a validated stage. Requires a fresh job guard and no live writer; published/unrelated output is never overwritten.'),
 'cleanup_export_job':(Cleanup,('allow_library_write',),'Preview/remove recognized owned interrupted export staging using a fresh guard, with symlink/inode/inventory checks and live-writer exclusion. Never deletes published output. Ready or previously verified files require explicit discard_ready=true; dry_run defaults true.'),
}

COMMANDS['list_export_jobs']=(ListJobs,(),'Discover export journals belonging to this MCP owner under a library directory using a bounded read-only scan. Omits finished jobs by default, skips symlinks/foreign records and reports truncation. Does not clean or adopt unknown directories; works without Blender.')
