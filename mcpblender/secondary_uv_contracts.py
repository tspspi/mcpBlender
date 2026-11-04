"""Shared structured projection options for owned botanical and LOD meshes."""
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .nla_contracts import SafeName
from .uv_layout_contracts import ChartLayout


class SecondaryLayout(Model):
    assets: list[str] = Field(min_length=1,max_length=32)
    uv_map: SafeName = 'UV2'
    texture_width: int = Field(default=1024,strict=True,ge=1,le=32768)
    texture_height: int = Field(default=1024,strict=True,ge=1,le=32768)
    angle_limit_degrees: FiniteFloat = Field(default=66,gt=0,le=89)
    margin: FiniteFloat = Field(default=.02,ge=0,le=.25)
    rotate: bool = True
    tile_padding_pixels: FiniteFloat = Field(default=4,ge=0,le=4096)
    chart_layout: ChartLayout | None = None
    max_corners: int = Field(default=500000,strict=True,ge=1,le=1000000)

    def uv_options(self):
        return self.model_dump(exclude={'lod_collection','expected_lods','assets','max_corners','collection','expected_tree'})

    @model_validator(mode='after')
    def options(self):
        from .uv_contracts import UVSecondary
        if len(set(self.assets))!=len(self.assets) or any(not a or len(a)>255 for a in self.assets):raise ValueError('Choose distinct nonempty vegetation asset roles')
        UVSecondary(name='validation',expected_uv='0'*64,**self.uv_options())
        return self
