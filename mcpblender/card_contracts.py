"""Typed guarded fitting of static foliage/mesh cluster bake targets."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .mesh_contracts import Name,Digest


class Plan(Model):
    sources: list[Name] = Field(min_length=1,max_length=16)
    view: Literal['TOP','FRONT','SIDE'] = 'TOP'
    outline: Literal['RECTANGLE','CONVEX_HULL'] = 'CONVEX_HULL'
    padding: FiniteFloat = Field(default=.02,ge=0,le=.25)
    standoff_m: FiniteFloat = Field(default=.005,gt=0,le=100)
    resolution: int = Field(default=128,strict=True,ge=32,le=256)
    max_vertices: int = Field(default=64,strict=True,ge=4,le=256)
    max_triangles: int = Field(default=100000,strict=True,ge=1,le=250000)
    thin_foliage_mode: Literal['REFUSE','FRONT_PBR'] = 'REFUSE'
    @model_validator(mode='after')
    def unique(self):
        if len(set(self.sources))!=len(self.sources):raise ValueError('Card sources must be distinct')
        return self


class Create(Plan):
    name: Name
    expected_card: Digest
    @model_validator(mode='after')
    def separate_target(self):
        if self.name in self.sources:raise ValueError('Card name must differ from sources')
        return self


COMMANDS={
 'inspect_foliage_card':(Plan,(),'Fit an orthographic convex-envelope or rectangular card to evaluated mesh sources. Inspect physical geometry, sampled coverage/empty area, material conversion and budgets without editing. Returns a mode/source/frame/unit-bound card guard. Realize instances first.'),
 'create_foliage_card':(Create,('allow_scene_edit',),'Guardedly create an editable fitted UV card without changing sources. Return inspected bake parameters for the existing isolated texture worker; baking remains explicit. Static single-view approximation, not an atlas or wind representation.'),
}
