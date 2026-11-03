"""Typed engine-independent wind inspection, pose sampling and semantic export."""
from typing import Annotated
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .botanical_contracts import Tree
from .mesh_contracts import Digest
from .nla_contracts import SafeName

class Settings(Model):
    seed: int = Field(default=1,strict=True)
    steady_mps: Annotated[list[FiniteFloat],Field(min_length=3,max_length=3)] = [2,0,0]
    gust_mps: FiniteFloat = 1
    waves: int = Field(default=3,strict=True)
    wavelength_m: FiniteFloat = 12
    frequency_hz: FiniteFloat = .2
    bend_degrees_per_mps: FiniteFloat = .5
    max_segment_degrees: FiniteFloat = 3
    max_accumulated_degrees: FiniteFloat = 60
    flutter_degrees: FiniteFloat = 4
    flutter_hz: FiniteFloat = 2
    phase_offset: FiniteFloat = 0
    @model_validator(mode='after')
    def canonical(self):
        from .wind import recipe
        recipe(self.model_dump());return self

class Plan(Tree):
    wind: Settings = Field(default_factory=Settings)

class Sample(Plan):
    seconds: list[FiniteFloat] = Field(default=[0,1,2],min_length=1,max_length=16)
    offset: int = Field(default=0,ge=0,le=4000)
    leaf_offset: int = Field(default=0,ge=0,le=100000)
    limit: int = Field(default=8,strict=True,ge=1,le=32)
    max_work: int = Field(default=100000,strict=True,ge=1,le=1000000)
    @model_validator(mode='after')
    def times(self):
        if len(set(self.seconds))!=len(self.seconds) or any(abs(t)>1e6 for t in self.seconds):raise ValueError('Choose distinct bounded wind sample times')
        return self

class Export(Plan):
    expected_wind: Digest
    path: str = Field(min_length=1)
    overwrite: bool = False
    max_bytes: int = Field(default=64*1024**2,strict=True,ge=1024,le=256*1024**2)

class PreviewPlan(Plan):
    frame_start: int = Field(default=1,strict=True,ge=-1048574,le=1048574)
    frame_end: int = Field(default=49,strict=True,ge=-1048574,le=1048574)
    frame_step: int = Field(default=1,strict=True,ge=1,le=120)
    display_offset_m: Annotated[list[FiniteFloat],Field(min_length=3,max_length=3)] = [0,0,0]
    max_instances: int = Field(default=30000,strict=True,ge=0,le=100000)
    max_coordinate_bytes: int = Field(default=256*1024**2,strict=True,ge=1024,le=2*1024**3)
    max_work: int = Field(default=30000000,strict=True,ge=1,le=100000000)
    max_key_error_m: FiniteFloat = Field(default=.0001,gt=0,le=.1)
    max_midpoint_error_m: FiniteFloat = Field(default=.01,gt=0,le=1)
    max_orientation_error_degrees: FiniteFloat = Field(default=1,gt=0,le=10)
    max_surface_edge_strain: FiniteFloat = Field(default=.2,ge=0,le=1)
    @model_validator(mode='after')
    def span(self):
        if self.frame_end<=self.frame_start or self.frame_end-self.frame_start>2400:raise ValueError('Wind preview needs an increasing range spanning at most 2400 frames')
        count=(self.frame_end-self.frame_start)//self.frame_step+1+bool((self.frame_end-self.frame_start)%self.frame_step)
        if count>121:raise ValueError('Wind preview sample budget is 121 frames')
        if any(abs(x)>100000 for x in self.display_offset_m):raise ValueError('Wind display offset exceeds supported range')
        return self

class CreatePreview(PreviewPlan):
    preview_collection: SafeName
    expected_plan: Digest
    @model_validator(mode='after')
    def separate(self):
        if self.preview_collection==self.collection or len(self.preview_collection.encode())>40:raise ValueError('Choose a distinct preview collection name up to 40 UTF-8 bytes')
        return self

class PreviewRead(Model):
    preview_collection: SafeName

class RemovePreview(PreviewRead):
    expected_preview: Digest

COMMANDS={
 'inspect_botanical_wind_preview_source':(PreviewPlan,(),'Plan a source-preserving native wind preview: sampled shape animation and shared Geometry Nodes leaf instances, coordinate/work budgets and interpolation limits. Return plan guard; no native edits.'),
 'create_botanical_wind_preview':(CreatePreview,('allow_scene_edit',),'Create an independently owned native wind animation with sampled shape keys and shared leaf instances. Verify native key/midpoint poses and surface edge strain, preserve source/frame/selection, and roll back cooperative failures. Does not export runtime wind attributes.'),
 'inspect_botanical_wind_preview':(PreviewRead,(),'Inspect saved native wind preview content/ownership, animation timing, metrics and current removal guard independently of its source. Playback changes do not invalidate content guards.'),
 'remove_botanical_wind_preview':(RemovePreview,('allow_scene_edit',),'Guardedly remove only an unambiguously owned wind preview, retaining shared source materials. Refuse external references and foreign collection members; manual owned edits require a fresh inspection guard.'),
 'inspect_botanical_wind':(Plan,(),'Inspect deterministic world-metre wind waves, anchored parent-first segment/leaf motion rules, frozen placement and source/settings guard. Semantic preparation only; no native deformation or shader adapter.'),
 'sample_botanical_wind':(Sample,(),'Sample the common wind field and hierarchical branch rotations without editing Blender. Page branches/leaves; report all-segment length/junction/root-anchor errors and rotation/displacement budgets. Not native animated geometry or a mechanical solver.'),
 'export_botanical_wind':(Export,('allow_library_write',),'Export guarded versioned wind field/solver settings, canonical branch hierarchy, placement and explicit foliage attachments to JSON. Atomically publish a bounded semantic sidecar with space checks. No GLB attribute packing or native preview certification.'),
}
