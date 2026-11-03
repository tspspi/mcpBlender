"""Optional geometry-quality policy bound to a specific bake resolution."""
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .mesh_contracts import Name


class Quality(Model):
    width: int = Field(default=1024,strict=True,ge=32,le=4096)
    height: int = Field(default=1024,strict=True,ge=32,le=4096)
    min_texels_per_meter: FiniteFloat = Field(default=64,ge=0,le=1000000)
    min_chart_pixels: int = Field(default=4,strict=True,ge=1,le=1000000)
    padding_pixels: FiniteFloat = Field(default=2,ge=0,le=64)
    mip_levels: int = Field(default=0,strict=True,ge=0,le=8)
    max_raster_tests: int = Field(default=20000000,strict=True,ge=1,le=200000000)
    max_spacing_tests: int = Field(default=200000,strict=True,ge=1,le=5000000)
    @model_validator(mode='after')
    def pixels(self):
        if self.width*self.height>4*1024**2:raise ValueError('Texture quality pixel budget exceeded')
        return self


class Inspect(Quality):
    name: Name
    uv_map: Name = 'UVMap'


COMMANDS={'inspect_texture_quality':(Inspect,(),'Inspect evaluated target UV chart pixel-centre coverage, physical directional texel density, continuous inter-chart/edge padding and requested mip footprints at a declared resolution. Bounded geometry-only test; does not certify colors, actual filtering or engine appearance. Optional same policy can gate texture baking.')}
