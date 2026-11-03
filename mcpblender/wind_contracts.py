"""Typed engine-independent wind inspection, pose sampling and semantic export."""
from typing import Annotated
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .botanical_contracts import Tree
from .mesh_contracts import Digest

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

COMMANDS={
 'inspect_botanical_wind':(Plan,(),'Inspect deterministic world-metre wind waves, anchored parent-first segment/leaf motion rules, frozen placement and source/settings guard. Semantic preparation only; no native deformation or shader adapter.'),
 'sample_botanical_wind':(Sample,(),'Sample the common wind field and hierarchical branch rotations without editing Blender. Page branches/leaves; report all-segment length/junction/root-anchor errors and rotation/displacement budgets. Not native animated geometry or a mechanical solver.'),
 'export_botanical_wind':(Export,('allow_library_write',),'Export guarded versioned wind field/solver settings, canonical branch hierarchy, placement and explicit foliage attachments to JSON. Atomically publish a bounded semantic sidecar with space checks. No GLB attribute packing or native preview certification.'),
}
