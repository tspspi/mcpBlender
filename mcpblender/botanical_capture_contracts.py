"""Native instanced whole-tree reference captures, preceding far-asset fitting."""
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .card_views import View
from .nla_contracts import SafeName
from .mesh_contracts import Digest

class Source(Model):
    collection: SafeName
    views: list[View] = Field(default=['FRONT','SIDE','BACK','LEFT'],min_length=1,max_length=10)
    resolution: int = Field(default=512,strict=True,ge=32,le=2048)
    margin: FiniteFloat = Field(default=1.1,ge=1.01,le=2)
    world_strength: FiniteFloat = Field(default=.5,gt=0,le=10)
    material_fields: bool = False
    normal_moments: bool = False
    samples: int = Field(default=16,strict=True,ge=1,le=1024)
    max_leaves: int = Field(default=100000,strict=True,ge=0,le=250000)
    max_render_triangles: int = Field(default=32000000,strict=True,ge=1,le=100000000)
    max_bounds_work: int = Field(default=2000000,strict=True,ge=8,le=4000000)
    @model_validator(mode='after')
    def unique(self):
        if self.normal_moments and not self.material_fields:raise ValueError('normal_moments requires material_fields=true')
        if len(set(self.views))!=len(self.views):raise ValueError('Capture views must be distinct')
        return self

class Capture(Source):
    directory: str = Field(min_length=1)
    expected_capture: Digest
    threads: int = Field(default=2,strict=True,ge=1,le=16)
    max_bytes: int = Field(default=4*1024**3,strict=True,ge=1024**2,le=128*1024**3)
    timeout_seconds: int = Field(default=3600,strict=True,ge=10,le=86400)

COMMANDS={
 'inspect_botanical_view_capture':(Source,(),'Plan native whole-tree reference captures without realizing leaf instances. Bound analytical prototype-box work and expanded render triangles; pin source/materials, static root/pivot, units, cameras and neutral-world lighting. Read-only; no far mesh or PBR reconstruction.'),
 'capture_botanical_views':(Capture,('allow_snapshots','allow_library_write','allow_start_blender'),'Guardedly snapshot only a static managed botanical tree and render directional PNG plus multilayer EXR reference/data passes in an owned independent worker. Preserve editing scene and instances; worker-only canonical visibility. Uses render-job progress/free space, cancellation, byte/time limits and recovery. Optional material_fields captures native shader-input AOVs with a separate surface weight, preserving backlighting/side evaluation. Optional normal_moments requires material_fields and admits shared unit normal inputs; records first/second moments for diagnostics, not a fitted shader. Data is not a reconstructed game material or far representation.'),
}


class Data(Model):
    material_inputs: bool = False
    directory: str = Field(min_length=1)
    views: list[View]|None = Field(default=None,min_length=1,max_length=10)
    alpha_threshold: FiniteFloat = Field(default=.5,gt=0,lt=1)
    max_pixels: int = Field(default=1048576,strict=True,ge=1024,le=4194304)
    max_total_pixels: int = Field(default=4194304,strict=True,ge=1024,le=41943040)
    @model_validator(mode='after')
    def distinct(self):
        if self.views is not None and len(set(self.views))!=len(self.views):raise ValueError('Data views must be distinct')
        return self

COMMANDS['inspect_botanical_capture_data']=(Data,(),'Read decoded native reference EXR depth/position/normal/alpha within bounded pixel/byte budgets, without Blender. Verify immutable source/files and metadata, including copied archives; report hit/coverage, normal length, camera projection and depth-position discrepancies separately for covered and opaque pixels. material_inputs=true additionally separates normal vector length from constant-one surface weight for covered/opaque/partial pixels; report bounds and unavailable observations without changing inputs. No automatic correction, reconstruction or job adoption.')
