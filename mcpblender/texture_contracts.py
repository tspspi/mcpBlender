"""Typed image baking and owned isolated texture-bundle jobs."""
from typing import Literal

from pydantic import Field, FiniteFloat, model_validator

from .config import Model
from .mesh_contracts import Name, Digest
from .texture_quality_contracts import Quality

Map = Literal['NORMAL','AO','BASE_COLOR','ROUGHNESS','METALLIC','EMISSION','ALPHA']


class TextureSources(Model):
    name: Name
    sources: list[Name] = Field(default_factory=list,max_length=16)
    uv_map: Name = 'UVMap'
    cage: Name | None = None
    thin_foliage_mode: Literal['REFUSE','FRONT_PBR'] = 'REFUSE'
    quality: Quality | None = None

    @model_validator(mode='after')
    def distinct(self):
        if len(set(self.sources))!=len(self.sources) or self.name in self.sources or self.cage in [self.name,*self.sources]:
            raise ValueError('Target, sources and cage must be distinct')
        if self.cage and not self.sources:raise ValueError('A projection cage requires high-to-low sources')
        return self


class BakeTextures(TextureSources):
    expected_bake: Digest
    directory: str
    maps: list[Map] = Field(default=['NORMAL','AO','BASE_COLOR','ROUGHNESS','METALLIC'],min_length=1,max_length=7)
    width: int = Field(default=1024,strict=True,ge=32,le=4096)
    height: int = Field(default=1024,strict=True,ge=32,le=4096)
    samples: int = Field(default=32,strict=True,ge=1,le=256)
    margin: int = Field(default=8,strict=True,ge=0,le=64,description='Attribute padding pixels. Projected ALPHA always uses zero padding; self-bakes retain this margin.')
    cage_extrusion: FiniteFloat = Field(default=.1,ge=0,le=1000)
    min_projection_coverage: FiniteFloat = Field(default=.99,ge=0,le=1)
    max_ray_distance: FiniteFloat = Field(default=1,gt=0,le=10000)
    threads: int = Field(default=2,strict=True,ge=1,le=16)
    max_bytes: int = Field(default=2*1024**3,strict=True,ge=1024**2,le=64*1024**3)
    timeout_seconds: int = Field(default=1800,strict=True,ge=10,le=86400)

    @model_validator(mode='after')
    def limits(self):
        if self.quality and (self.width,self.height)!=(self.quality.width,self.quality.height):raise ValueError('Bake dimensions must match the texture quality policy')
        if self.quality and self.margin>self.quality.padding_pixels:raise ValueError('Bake margin must not exceed the quality policy padding_pixels')
        if len(set(self.maps))!=len(self.maps):raise ValueError('Bake maps must be unique')
        if self.width*self.height>4*1024**2:raise ValueError('Texture bake pixel budget exceeded')
        return self


class TextureBundle(Model):
    directory: str


class CleanupTexture(TextureBundle):
    dry_run: bool = True
    include_interrupted: bool = False


WRITE=('allow_library_write',)
COMMANDS={
    'inspect_texture_bake':(TextureSources,(), 'Inspect evaluated target/high sources/cage, UV validity and supported static Principled materials. Optional quality policy requires complete physical directional density, chart coverage and mip-padding checks at its declared dimensions. Projected ALPHA uses zero padding while other maps retain margin; bundles record and validate the policy. Managed thin leaves require explicit FRONT_PBR; reports omitted optics and a mode-bound source fingerprint for guarded baking.'),
    'bake_textures':(BakeTextures,('allow_scene_edit',)+WRITE,'Bake normal/AO/PBR maps in an isolated owned worker. Creates a new manifest-bound PNG/editable-asset bundle, preserving live scene; reports space/progress and supports worker cancellation. Optional quality policy must match dimensions and cover bake margin; rechecked in worker and retained in manifest. Explicit FRONT_PBR records managed thin-leaf approximation metadata; default mode refuses it.'),
    'validate_texture_bake':(TextureBundle,(),'Verify bundle file hashes, conversion metadata and the opened baked asset geometry/UV/material/image binding. New atlas bundles also check the sealed retained pixel-copy witness; source images need not remain present. Open its asset.blend first.'),
    'inspect_texture_job':(TextureBundle,(),'Inspect an owned texture-bake job, recorded process liveness and output bytes.'),
    'recover_texture_job':(TextureBundle,WRITE,'Reconcile a departed texture-bake job without replay; adopt a complete verified result or mark partial output interrupted.'),
    'cleanup_texture_job':(CleanupTexture,WRITE,'Preview/remove only owned failed/cancelled partial bundles; interrupted jobs require explicit inclusion. Refuses success, references, unknown entries and symlinks.'),
}
