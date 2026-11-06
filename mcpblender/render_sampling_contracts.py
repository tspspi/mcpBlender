"""Explicit Cycles sampling profiles, distinct from compositor/color settings."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .mesh_contracts import Digest

class Read(Model):pass

class Settings(Model):
    samples: int|None = Field(default=None,strict=True,ge=1,le=65536)
    sampling_pattern: Literal['AUTOMATIC','TABULATED_SOBOL','BLUE_NOISE']|None = None
    seed: int|None = Field(default=None,strict=True,ge=0,le=2147483647)
    use_animated_seed: bool|None = Field(default=None,strict=True)
    use_adaptive_sampling: bool|None = Field(default=None,strict=True)
    adaptive_threshold: FiniteFloat|None = Field(default=None,strict=True,ge=0,le=1)
    adaptive_min_samples: int|None = Field(default=None,strict=True,ge=0,le=65536)
    use_denoising: bool|None = Field(default=None,strict=True)
    use_layer_samples: Literal['USE','BOUNDED','IGNORE']|None = None
    pixel_filter_type: Literal['BOX','GAUSSIAN','BLACKMAN_HARRIS']|None = None
    filter_width: FiniteFloat|None = Field(default=None,strict=True,ge=.01,le=10)
    use_sample_subset: bool|None = Field(default=None,strict=True)
    sample_offset: int|None = Field(default=None,strict=True,ge=0,le=65536)
    sample_subset_length: int|None = Field(default=None,strict=True,ge=1,le=65536)
    time_limit: FiniteFloat|None = Field(default=None,strict=True,ge=0,le=86400)
    max_bounces: int|None = Field(default=None,strict=True,ge=0,le=1024)
    diffuse_bounces: int|None = Field(default=None,strict=True,ge=0,le=1024)
    glossy_bounces: int|None = Field(default=None,strict=True,ge=0,le=1024)
    transmission_bounces: int|None = Field(default=None,strict=True,ge=0,le=1024)
    volume_bounces: int|None = Field(default=None,strict=True,ge=0,le=1024)
    transparent_max_bounces: int|None = Field(default=None,strict=True,ge=0,le=1024)
    @model_validator(mode='after')
    def nonempty(self):
        if not self.model_dump(exclude_none=True):raise ValueError('Supply a sampling setting')
        return self

class Configure(Model):
    expected_sampling: Digest
    settings: Settings

COMMANDS={
 'inspect_render_sampling':(Read,(),'Inspect current scene Cycles samples, sampler, seed, adaptive/denoising flags, layer sample policy, filter, sample subset/time limit and bounce limits. Report view-layer sample/denoise overrides, animation paths, enum choices and requested execution settings with sampling_sha256. The guard covers this explicit subset, not all integrator settings, geometry, shaders, lighting, hardware availability or bit-exact output.'),
 'configure_render_sampling':(Configure,('allow_scene_edit',),'Guardedly patch explicit Cycles sampling settings with a fresh sampling_sha256. Validate native enums/ranges and a nonempty enabled sample window before mutation; refuse keyed/driven targeted fields. Native returned values are authoritative. Roll back all patched fields on cooperative cancellation or failure. This stores Cycles settings even if another engine is active; CPU/thread execution for independent renders is controlled by render_camera_batch.'),
}
