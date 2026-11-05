"""Explicit approximate directional depth assets from immutable native captures."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .card_views import View
from .mesh_contracts import Name,Digest

class Settings(Model):
    geometry_mode: Literal['FLAT','ADAPTIVE_NORMAL'] = 'FLAT'
    normal_tolerance_degrees: FiniteFloat = Field(default=15.0,ge=.1,le=90,strict=True)
    max_slope: FiniteFloat = Field(default=16.0,ge=.01,le=64,strict=True)
    max_refinement_work: int = Field(default=8000000,strict=True,ge=1,le=16000000)
    tile_pixels: int = Field(default=4,strict=True,ge=1,le=64)
    alpha_threshold: FiniteFloat = Field(default=.001,gt=0,lt=1)
    edge_depth_policy: Literal['NEAREST','OMIT','REFUSE'] = 'NEAREST'
    edge_radius_pixels: int = Field(default=16,strict=True,ge=0,le=64)
    max_triangles: int = Field(default=32768,strict=True,ge=2,le=131072)
    max_pixels: int = Field(default=1048576,strict=True,ge=1024,le=1048576)
    max_texture_bytes: int = Field(default=256*1024**2,strict=True,ge=1024,le=512*1024**2)
    max_search_work: int = Field(default=2000000,strict=True,ge=1,le=8000000)

    @model_validator(mode='after')
    def tile_size(self):
        if self.tile_pixels not in (1,2,4,8,16,32,64):raise ValueError('Tile size must be a power of two')
        return self

class Source(Model):
    directory: str
    view: View
    settings: Settings = Field(default_factory=Settings)

class Create(Source):
    collection: Name
    expected_plan: Digest
    accept_approximate_optics: bool = False

class Asset(Model):
    collection: Name

class Remove(Asset):
    expected_asset: Digest

COMMANDS={
 'inspect_botanical_depth_source':(Source,(),'Plan one directional depth-patch asset from an immutable native capture with material_fields=true. Bounded geometry/search/pixels/textures; report measured versus estimated edge tiles, source-root units, six packed float data maps and source/file/geometry/map guards. Optional bounded normal-aligned adaptive geometry reports residual error, slope/bounds limits and budget stops; flat geometry remains the default. No beauty-RGB material substitution. Requires Blender only for target scene units. This is a directional approximation, not qualified optical equivalence or complete far workflow.'),
 'create_botanical_depth_asset':(Create,('allow_scene_edit',),'Create guarded independent hidden directional depth patches with private packed native-input textures, Principled plus artistic thin backlighting and separate coverage. Requires accept_approximate_optics=true. Preserve source/native scene resources. Intrinsic shader alpha must be opaque. Six float maps retain raw root-local normals and all input witnesses. No closed geometry, view blending, shadows/wind or native optical-equivalence guarantee.'),
 'inspect_botanical_depth_asset':(Asset,(),'Inspect owned packed directional depth asset after save/reopen without source files. Return content/placement/user guard and blockers for removal. Visibility and uniform positive root placement can change. No optical certification.'),
 'remove_botanical_depth_asset':(Remove,('allow_scene_edit',),'Remove an unchanged guarded owned depth asset and private packed data. Refuse foreign content/users or stale guard; preserve capture archive and original scene assets.'),
}
