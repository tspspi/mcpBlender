"""Geometry-only projected component occupancy captures."""
from pydantic import Field
from .config import Model
from .card_views import View
from .mesh_contracts import Digest

class Source(Model):
    reference_directory: str = Field(min_length=1)
    view: View = 'FRONT'
    samples: int = Field(default=256,strict=True,ge=64,le=4096)

class Capture(Source):
    directory: str = Field(min_length=1)
    expected_plan: Digest
    threads: int = Field(default=2,strict=True,ge=1,le=32)
    max_bytes: int = Field(default=1073741824,strict=True,ge=16777216,le=17179869184)
    timeout_seconds: int = Field(default=1800,strict=True,ge=10,le=86400)

COMMANDS={
 'inspect_botanical_projected_coverage':(Source,(),'Plan geometry-only projected union coverage of each reference first-hit leaf within its pixel cell, ignoring other components. Requires an unchanged opaque one-sample component capture. Pin source, camera, reference grid and a BOX-filtered Cycles sample subset excluding the selecting centre sample. Static captured view; not face identity, lighting or optical certification.'),
 'capture_botanical_projected_coverage':(Capture,('allow_snapshots','allow_library_write','allow_start_blender'),'Capture the guarded projected-coverage plan in an isolated CPU render worker. Packed immutable ID grid and source snapshot; original geometry, shaders and visibility preserved. Existing render-job progress, storage, cancellation, recovery and validation apply. Output white premultiplied EXR32 RGBA occupancy; finite Monte Carlo zeros remain zeros. No automatic depth-asset or native-complement modification.'),
}
