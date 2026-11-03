"""Batch assets with explicit primary, proxy and validated LOD associations."""
from typing import Annotated
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .nla_contracts import SafeName
from .mesh_contracts import Digest
from .lod_contracts import Timeline

Slug=Annotated[str,Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,47}$')]


class LOD(Timeline):
    chain: SafeName
    animations: bool = True
    animation_samples: int = Field(default=3,ge=3,le=9)
    skin_tolerance: FiniteFloat = Field(default=.001,ge=.0000001,le=1)


class Asset(Model):
    id: Slug
    objects: list[SafeName] = Field(min_length=1,max_length=64)
    collision_proxies: list[SafeName] = Field(default_factory=list,max_length=8)
    shadow_proxies: list[SafeName] = Field(default_factory=list,max_length=8)
    lods: list[LOD] = Field(default_factory=list,max_length=4)
    @model_validator(mode='after')
    def distinct(self):
        for values in (self.objects,self.collision_proxies,self.shadow_proxies,[l.chain for l in self.lods]):
            if len(values)!=len(set(values)):raise ValueError('Asset source/association names must be distinct')
        if set(self.collision_proxies)&set(self.shadow_proxies):raise ValueError('Proxy collection cannot have both roles')
        return self


class Plan(Model):
    assets: list[Asset] = Field(min_length=1,max_length=32)
    @model_validator(mode='after')
    def distinct(self):
        if len({a.id.casefold() for a in self.assets})!=len(self.assets):raise ValueError('Asset IDs must be distinct ignoring case')
        return self


class Export(Plan):
    expected_source: Digest
    directory: str = Field(min_length=1)


class Validate(Model):
    directory: str = Field(min_length=1)


COMMANDS={
 'inspect_asset_package':(Plan,(),'Plan batch static primary mesh delivery, associated owned collision/shadow proxies and native validated LOD bundles. Reports guarded source/dependency inventory, blockers, texture/storage estimates and explicit static/interchange limits.'),
 'export_asset_package':(Export,('allow_library_write',),'Export a guarded batch package using owned static mesh snapshots and optional validated LOD bundles. Independently decode triangle surfaces, scene transforms and embedded image/texture/UV references; record proxy associations; verify all files before atomic directory publication. Preserves source scene and cleans ordinary failure/cancellation.'),
 'validate_asset_package':(Validate,(),'Validate package inventory, hashes, independent static GLB scene/surface/dependency proofs, native correspondence and nested LOD manifests. Does not certify arbitrary shader fidelity or engine integration.'),
}
