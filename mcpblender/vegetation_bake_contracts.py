"""Owned static vegetation copies prepared for the existing texture baker."""
from typing import Literal
from pydantic import Field, FiniteFloat, model_validator
from .config import Model
from .mesh_contracts import Name, Digest
from .nla_contracts import SafeName


class Source(Model):
    collection: SafeName | None = None
    lod_collection: SafeName | None = None
    assets: list[Name] | None = Field(default=None,min_length=1,max_length=16)
    uv_map: Name = 'BakeUV'
    uv_strategy: Literal['NEW','EXISTING'] = 'NEW'
    max_uv_repairs: int = Field(default=64,strict=True,ge=0,le=256)
    margin: FiniteFloat = Field(default=.02,ge=.001,le=.1)
    tile_padding_pixels: FiniteFloat = Field(default=0,ge=0,le=4096)
    texture_width: int = Field(default=1024,strict=True,ge=32,le=4096)
    texture_height: int = Field(default=1024,strict=True,ge=32,le=4096)
    missing_uv_policy: Literal['REFUSE','BAKE_LAYOUT'] = 'REFUSE'
    max_corners: int = Field(default=100000,strict=True,ge=1,le=500000)
    @model_validator(mode='after')
    def source(self):
        if (self.collection is None)==(self.lod_collection is None):raise ValueError('Choose one botanical tree or native LOD profile')
        if self.assets and len(self.assets)!=len(set(self.assets)):raise ValueError('Choose distinct asset roles')
        if self.texture_width*self.texture_height>4*1024**2:raise ValueError('Preparation texture pixel budget exceeded')
        if 2*self.tile_padding_pixels>=min(self.texture_width,self.texture_height):raise ValueError('Tile padding must leave a positive texture interior')
        if self.tile_padding_pixels and self.uv_strategy!='NEW':raise ValueError('Tile padding requires NEW UVs; EXISTING preserves authored coordinates')
        return self


class Create(Source):
    bake_collection: SafeName
    expected_plan: Digest


class Read(Model):
    bake_collection: SafeName


class Remove(Read):
    expected_preparation: Digest


COMMANDS={
 'inspect_vegetation_bake_source':(Source,(),'Plan source-preserving owned vegetation bake copies with independent materials and nonoverlapping BakeUV. NEW layouts optionally reserve tile_padding_pixels at texture_width/height; EXISTING preserves authored coordinates. Reports implicit sampling pins, missing named UVs, budgets and a plan guard. BAKE_LAYOUT explicitly permits generated missing source UVs, changing copy sampling only.'),
 'prepare_vegetation_bake':(Create,('allow_scene_edit',),'Prepare guarded independent wood/shoot/shared-template meshes with new or explicitly reused target bake UVs. Preserve original geometry, attributes, UVs and source shader sampling; explicitly opted-in missing UVs use the new layout. Returns existing inspect_texture_bake inputs, not baked images.'),
 'inspect_vegetation_bake':(Read,(),'Inspect owned vegetation bake preparation content, source witness, per-component bake inputs and guarded cleanup blockers independently of the source.'),
 'refresh_vegetation_bake':(Remove,('allow_scene_edit',),'Guardedly accept supported material/frame edits on owned bake copies as the next bake source. Require frozen mesh, attributes, UVs, placement and private material slots; update bake fingerprints and revision. Does not accept mesh edits or change the original source.'),
 'remove_vegetation_bake':(Remove,('allow_scene_edit',),'Remove only guarded unambiguously owned vegetation bake copies and their private materials. Refuse foreign collection members and external references; baked file bundles are independent.'),
}


class BakeEntry(Model):
    asset: Name
    directory: str = Field(min_length=1)


class Adoption(Read):
    lod_collection: SafeName
    entries: list[BakeEntry] = Field(min_length=1,max_length=16)
    accept_front_pbr: bool = False
    replace_existing: bool = False
    max_bytes: int = Field(default=256*1024**2,strict=True,ge=1024,le=2*1024**3)
    max_texture_bytes: int = Field(default=64*1024**2,strict=True,ge=4096,le=512*1024**2)
    @model_validator(mode='after')
    def distinct(self):
        if len({e.asset for e in self.entries})!=len(self.entries) or len({e.directory for e in self.entries})!=len(self.entries):raise ValueError('Choose distinct asset roles and bake directories')
        return self


class Adopt(Adoption):
    expected_plan: Digest


COMMANDS.update({
 'inspect_vegetation_bake_adoption':(Adoption,(),'Plan guarded adoption of successful source-bound texture-bake PNGs and prepared UVs into matching native LOD components. Verify files, source/material correspondence, optical-loss acceptance and base RGBA8 budget. No scene edits or native file import.'),
 'adopt_vegetation_bakes':(Adopt,('allow_scene_edit',),'Guardedly adopt a checked batch of baked PBR maps/UVs into unchanged owned LOD components. Preserve geometry, wind fields and original UVs; pack privately owned images and retain loss/source witnesses. Requires explicit acceptance for FRONT_PBR leaves. Replacing adopted roles requires explicit replace_existing; preserve inherited optical losses and retire only unused private resources.'),
})


class Delivery(Model):
    lod_collection: SafeName
    required_maps: list[Literal['NORMAL','AO','BASE_COLOR','ROUGHNESS','METALLIC','EMISSION','ALPHA']] = Field(default=['BASE_COLOR','NORMAL','AO','ROUGHNESS','METALLIC','ALPHA'],min_length=1,max_length=7)
    min_texture_size: int = Field(default=128,strict=True,ge=32,le=4096)
    max_texture_bytes: int = Field(default=64*1024**2,strict=True,ge=4096,le=512*1024**2)
    max_mip_bytes: int = Field(default=96*1024**2,strict=True,ge=4096,le=768*1024**2)
    @model_validator(mode='after')
    def maps(self):
        if len(self.required_maps)!=len(set(self.required_maps)):raise ValueError('Choose distinct required maps')
        return self


COMMANDS['inspect_vegetation_delivery']=(Delivery,(),'Inspect every native LOD wood/shoot and shared leaf template for adopted-map coverage, requested map/resolution gaps, optical omissions and whole-profile source-map base/full-mipmap RGBA8 estimates. Returns complete only for these declared file/material criteria, not visual or engine qualification.')
