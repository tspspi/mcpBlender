"""Guarded collection display switches for native sources and owned approximations."""
from typing import Literal
from pydantic import Field,model_validator
from .config import Model
from .nla_contracts import SafeName
from .mesh_contracts import Digest

class Target(Model):
    kind: Literal['SOURCE','DEPTH','SUBSET']
    collection: SafeName

class Patch(Target):
    hide_viewport: bool|None = Field(default=None,strict=True)
    hide_render: bool|None = Field(default=None,strict=True)
    @model_validator(mode='after')
    def changes(self):
        if self.hide_viewport is None and self.hide_render is None:raise ValueError('Supply at least one display field per target')
        return self

class Inspect(Model):
    targets: list[Target] = Field(min_length=1,max_length=16)
    @model_validator(mode='after')
    def unique(self):
        if len({v.collection for v in self.targets})!=len(self.targets):raise ValueError('Display target collections must be distinct')
        return self

class Configure(Inspect):
    targets: list[Patch] = Field(min_length=1,max_length=16)
    expected_display: Digest

COMMANDS={
 'inspect_botanical_display':(Inspect,(),'Inspect collection-wide viewport/render flags for up to16 distinct managed SOURCE trees, DEPTH assets or SUBSET assets. Bind ownership/content guards, current scene/view layer/frame, collection identities, and layer/ancestor visibility context. Report keyed/driven fields and other-scene links. Does not change individual object flags, intentional hidden buds, ray roles, excluded layers or ancestor visibility.'),
 'configure_botanical_display':(Configure,('allow_scene_edit',),'Guardedly change hide_viewport/hide_render on a batch of managed botanical collections. Use a fresh inspect_botanical_display guard for the same targets. Preflight every target; refuse stale guards, invalid ownership, cross-scene targets and keyed/driven targeted flags. Preserve object flags, ray roles, layers, ancestors and model data. Roll back all collection flags on cooperative cancellation or failure, including after a partial switch. Showing a collection does not override hidden objects, ancestors or layer exclusions; inspect reported contexts.'),
}
