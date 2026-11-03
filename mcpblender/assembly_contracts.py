"""Reusable native collection prototypes and guarded linked placements."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .nla_contracts import SafeName
from .mesh_contracts import Digest


class Source(Model):
    objects: list[SafeName] = Field(min_length=1,max_length=128)
    @model_validator(mode='after')
    def distinct(self):
        if len(set(self.objects))!=len(self.objects):raise ValueError('Source objects must be distinct')
        return self


class SourceInspection(Source):
    dependency_offset: int = Field(default=0,ge=0)
    dependency_limit: int = Field(default=100,ge=1,le=256)


class Create(Source):
    collection: SafeName
    expected_source: Digest
    origin_mode: Literal['WORLD_ORIGIN','BOUNDS_CENTER','BOUNDS_BOTTOM','CUSTOM'] = 'BOUNDS_BOTTOM'
    origin: list[FiniteFloat] | None = Field(default=None,min_length=3,max_length=3)
    @model_validator(mode='after')
    def custom(self):
        if (self.origin_mode=='CUSTOM')!=(self.origin is not None):raise ValueError('Supply origin only with origin_mode=CUSTOM')
        return self


class Asset(Model):
    collection: SafeName


class Inspection(Asset):
    offset: int = Field(default=0,ge=0)
    limit: int = Field(default=100,ge=1,le=256)


class Guard(Asset):
    expected_asset: Digest


class Place(Guard):
    name: SafeName
    location: list[FiniteFloat] = Field(default_factory=lambda:[0,0,0],min_length=3,max_length=3)
    rotation_degrees: list[FiniteFloat] = Field(default_factory=lambda:[0,0,0],min_length=3,max_length=3)
    scale: list[FiniteFloat] = Field(default_factory=lambda:[1,1,1],min_length=3,max_length=3)
    @model_validator(mode='after')
    def nonsingular(self):
        if any(not 1e-6<=abs(v)<=1e6 for v in self.scale):raise ValueError('Instance scale magnitude must be in [1e-6,1e6]')
        return self


class Editing(Guard):
    enabled: bool


class Instance(Model):
    name: SafeName


class InstanceInspection(Instance):
    leaf_offset: int = Field(default=0,ge=0,le=2048)
    leaf_limit: int = Field(default=32,ge=1,le=128)


class Remove(Instance):
    expected_instance: Digest


class RealizationSource(Model):
    instances: list[SafeName] = Field(min_length=1,max_length=128)
    @model_validator(mode='after')
    def distinct(self):
        if len(set(self.instances))!=len(self.instances):raise ValueError('Instances must be distinct')
        return self


class RealizationInspection(RealizationSource):
    leaf_offset: int = Field(default=0,ge=0,le=2048)
    leaf_limit: int = Field(default=32,ge=1,le=128)


class Realize(RealizationSource):
    collection: SafeName
    expected_source: Digest


COMMANDS={
 'inspect_asset_assembly_source':(SourceInspection,(),'Plan a source-preserving reusable collection: native object/data/action dependencies, missing controls, nested managed prototypes, current-content guard and bounds. Requires a closed local object graph; shared external files are not frozen.'),
 'create_asset_assembly':(Create,('allow_scene_edit',),'Copy a closed native object/data/action graph into an unlinked persistent collection prototype with chosen origin. Preserves parents, constraints, drivers, material/geometry references and managed clips through native append; restores source metadata and cleans temporary data on failure/cancellation. Existing nested prototypes remain shared.'),
 'inspect_asset_assembly':(Inspection,(),'Inspect owned prototype membership, data/dependency inventory, current-content guard, origin and linked placements. Shader/image file contents outside the recorded scope are not frozen.'),
 'place_asset_instance':(Place,('allow_scene_edit',),'Create a named native collection instance with guarded prototype and typed placement. Instances share the prototype, including active animation; source objects remain intact.'),
 'set_asset_assembly_editing':(Editing,('allow_scene_edit',),'Link/unlink the prototype directly in the current scene for ordinary structured component editing. Existing placements continue sharing it; only the direct editing link is changed.'),
 'inspect_asset_instance':(InstanceInspection,(),'Inspect one managed collection instance, current guard and evaluated viewport leaf transforms/bounds through nested instances. Does not realize or export geometry.'),
 'remove_asset_instance':(Remove,('allow_scene_edit',),'Remove a guarded owned placement without deleting its prototype or data. Refuses instances referenced by other objects/drivers.'),
}

COMMANDS.update({
 'inspect_asset_realization':(RealizationInspection,(),'Inspect a static current-viewport mesh realization of managed placements, including nested and procedural mesh leaves. Reports source guard, native attributes, bounds and ignored nonmesh helpers. Does not bake shaders or animation.'),
 'realize_asset_instances':(Realize,('allow_scene_edit',),'Realize guarded managed placements into independent world-space static meshes in a fresh scene collection. Preserves evaluated mesh attributes and shared material assignments; sources remain intact. Animation/rigs and shader coordinates are not baked. Queued operation with cooperative rollback.'),
})
