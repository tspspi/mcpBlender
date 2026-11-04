"""Structured packing of verified baked texture bundles."""
from pydantic import Field,model_validator
from typing import Annotated
from .config import Model
from .mesh_contracts import Digest

class Entry(Model):
    id: Annotated[str,Field(pattern=r'^[a-z][a-z0-9_]{0,31}$')]
    directory: str

class Plan(Model):
    entries: list[Entry] = Field(min_length=1,max_length=16)
    width: int = Field(default=1024,strict=True,ge=32,le=4096)
    height: int = Field(default=1024,strict=True,ge=32,le=4096)
    gutter: int = Field(default=8,strict=True,ge=0,le=64)
    max_texture_bytes: int = Field(default=256*1024**2,strict=True,ge=1024,le=2*1024**3)
    max_input_bytes: int = Field(default=2*1024**3,strict=True,ge=1024**2,le=16*1024**3)
    @model_validator(mode='after')
    def bounds(self):
        if len({e.id for e in self.entries})!=len(self.entries) or len({e.directory for e in self.entries})!=len(self.entries):raise ValueError('Atlas inputs and IDs must be distinct')
        if self.width*self.height>4*1024**2:raise ValueError('Atlas pixel budget exceeded')
        return self

class Build(Plan):
    expected_atlas: Digest
    directory: str
    threads: int = Field(default=2,strict=True,ge=1,le=16)
    max_bytes: int = Field(default=2*1024**3,strict=True,ge=1024**2,le=64*1024**3)
    timeout_seconds: int = Field(default=1800,strict=True,ge=10,le=86400)

COMMANDS={
 'inspect_texture_atlas':(Plan,(),'Verify successful texture-bake bundles and plan nonrotating, unresampled atlas tiles with explicit gutters and RGBA8 base/full-mip memory budgets. Returns source/layout guard; no scene edits.'),
 'build_texture_atlas':(Build,('allow_scene_edit','allow_library_write'),'Build a shared PBR atlas and separate editable UV-remapped meshes in an isolated owned texture worker. Requires verified matching-map bake bundles and guarded plan. Checks every decoded RGBA8 tile/gutter channel and records a sealed source/file-bound copy witness. Preserves editor scene; reuses texture-job progress/storage/cancellation/recovery/cleanup.'),
}
