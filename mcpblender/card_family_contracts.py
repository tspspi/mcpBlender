"""Persistent, independently packed alternatives and explicit angular selection."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .mesh_contracts import Name,Digest,Vec3

View=Literal['TOP','FRONT','SIDE']


class Entry(Model):
    view: View
    object: Name


class Source(Model):
    directory: str
    entries: list[Entry] = Field(min_length=1,max_length=3)
    accept_front_pbr: bool = False
    max_angle_degrees: FiniteFloat = Field(default=30,gt=0,le=80)
    max_total_triangles: int = Field(default=1024,strict=True,ge=1,le=4096)
    max_texture_bytes: int = Field(default=256*1024**2,strict=True,ge=1024,le=512*1024**2)

    @model_validator(mode='after')
    def distinct(self):
        if len({e.view for e in self.entries})!=len(self.entries) or len({e.object for e in self.entries})!=len(self.entries):raise ValueError('Family views and objects must be distinct')
        return self


class Create(Source):
    family_collection: Name
    expected_plan: Digest


class Family(Model):
    family_collection: Name


class Direction(Family):
    camera: Name | None = None
    view_direction: Vec3 | None = Field(default=None,description='World-space direction from asset toward viewer; orthographic/parallel rays.')

    @model_validator(mode='after')
    def one_direction(self):
        if (self.camera is None)==(self.view_direction is None):raise ValueError('Specify exactly one camera or world-space view_direction')
        if self.view_direction is not None and max(abs(v) for v in self.view_direction)==0:raise ValueError('Nonzero view_direction required')
        return self


class Select(Direction):
    expected_selection: Digest


class Remove(Family):
    expected_family: Digest


COMMANDS={
 'inspect_foliage_card_family_source':(Source,(),'Validate the opened bake/atlas and inspect bounded canonical TOP/FRONT/SIDE planar alternatives for an independent packed family. Explicit FRONT_PBR acceptance required when applicable. Returns source/geometry/map/options-bound creation guard; no scene edits.'),
 'create_foliage_card_family':(Create,('allow_scene_edit',),'Create a guarded independent collection/root/meshes/private materials and packed textures from a validated bake or atlas. Copies start hidden; original objects and files are preserved. Static alternatives only; select a supported view explicitly.'),
 'inspect_foliage_card_family':(Family,(),'Inspect owned family content, packed resources, placement, visibility and external-reference blockers after save/reopen. No source files required. Returns guard for removal; no optical equivalence implied.'),
 'inspect_foliage_card_family_selection':(Direction,(),'Plan deterministic nearest supported family view from a named ORTHO/PERSP camera or explicit world viewer direction. Perspective tests all family-bound corners against the angular limit. Reports unsupported directions without edits and returns a camera/family-bound selection guard.'),
 'select_foliage_card_family_view':(Select,('allow_scene_edit',),'Apply guarded supported view selection, showing exactly one owned card and hiding the others for viewport/render. No camera handler, interpolation, back-view synthesis or source visibility changes. Repeat explicitly when camera or family placement changes.'),
 'remove_foliage_card_family':(Remove,('allow_scene_edit',),'Guardedly remove an unchanged owned family and its private packed data; refuse changed content or external users. Preserve original bake objects and files.'),
}
