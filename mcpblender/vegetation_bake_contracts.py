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
    margin: FiniteFloat = Field(default=.02,ge=.001,le=.1)
    missing_uv_policy: Literal['REFUSE','BAKE_LAYOUT'] = 'REFUSE'
    max_corners: int = Field(default=100000,strict=True,ge=1,le=500000)
    @model_validator(mode='after')
    def source(self):
        if (self.collection is None)==(self.lod_collection is None):raise ValueError('Choose one botanical tree or native LOD profile')
        if self.assets and len(self.assets)!=len(set(self.assets)):raise ValueError('Choose distinct asset roles')
        return self


class Create(Source):
    bake_collection: SafeName
    expected_plan: Digest


class Read(Model):
    bake_collection: SafeName


class Remove(Read):
    expected_preparation: Digest


COMMANDS={
 'inspect_vegetation_bake_source':(Source,(),'Plan source-preserving owned vegetation bake copies with independent materials and nonoverlapping BakeUV. Reports implicit sampling pins, missing named UVs, budgets and a plan guard. BAKE_LAYOUT explicitly permits generated missing source UVs, changing copy sampling only.'),
 'prepare_vegetation_bake':(Create,('allow_scene_edit',),'Prepare guarded independent wood/shoot/shared-template meshes with unique target bake UVs. Preserve original geometry, attributes, UVs and source shader sampling; explicitly opted-in missing UVs use the new layout. Returns existing inspect_texture_bake inputs, not baked images.'),
 'inspect_vegetation_bake':(Read,(),'Inspect owned vegetation bake preparation content, source witness, per-component bake inputs and guarded cleanup blockers independently of the source.'),
 'remove_vegetation_bake':(Remove,('allow_scene_edit',),'Remove only guarded unambiguously owned vegetation bake copies and their private materials. Refuse foreign collection members and external references; baked file bundles are independent.'),
}
