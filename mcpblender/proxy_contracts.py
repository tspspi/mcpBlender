"""Static collision and shadow representations with explicit approximation policy."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .nla_contracts import SafeName
from .mesh_contracts import Digest


class Source(Model):
    objects: list[SafeName] = Field(min_length=1,max_length=64)
    purpose: Literal['COLLISION','SHADOW'] = 'COLLISION'
    method: Literal['BOX','CONVEX_HULL','DECIMATE'] = 'CONVEX_HULL'
    grouping: Literal['PER_LEAF','PER_SOURCE','COMBINED'] = 'PER_LEAF'
    padding: FiniteFloat = Field(default=0,ge=0,le=10000)
    triangle_budget: int | None = Field(default=None,ge=4,le=500000)
    max_relative_error: FiniteFloat | None = Field(default=None,ge=0)
    sample_count: int = Field(default=256,ge=32,le=2048)
    @model_validator(mode='after')
    def coherent(self):
        if len(set(self.objects))!=len(self.objects):raise ValueError('Proxy source objects must be distinct')
        if self.purpose=='SHADOW':
            if self.method!='DECIMATE' or self.grouping!='PER_LEAF':raise ValueError('Shadow proxies require DECIMATE and PER_LEAF')
            if self.triangle_budget is None:raise ValueError('Shadow proxies require a per-leaf triangle_budget')
        elif self.method=='DECIMATE':raise ValueError('Collision proxies use BOX or CONVEX_HULL')
        elif self.triangle_budget is not None:raise ValueError('triangle_budget applies to DECIMATE only')
        if self.padding and self.method!='BOX':raise ValueError('padding applies to BOX only')
        return self


class Generate(Source):
    collection: SafeName
    expected_source: Digest


class Inspect(Model):
    collection: SafeName
    offset: int = Field(default=0,ge=0)
    limit: int = Field(default=32,ge=1,le=128)


class Remove(Model):
    collection: SafeName
    expected_proxy: Digest


class Visibility(Model):
    name: SafeName


class ConfigureVisibility(Visibility):
    expected_visibility: Digest
    hide_render: bool | None = None
    visible_camera: bool | None = None
    visible_diffuse: bool | None = None
    visible_glossy: bool | None = None
    visible_transmission: bool | None = None
    visible_volume_scatter: bool | None = None
    visible_shadow: bool | None = None
    @model_validator(mode='after')
    def changed(self):
        if not any(getattr(self,k) is not None for k in ('hide_render','visible_camera','visible_diffuse','visible_glossy','visible_transmission','visible_volume_scatter','visible_shadow')):
            raise ValueError('Supply at least one render visibility field')
        return self


COMMANDS={
 'inspect_asset_proxy_source':(Source,(),'Plan static collision BOX/CONVEX_HULL or per-leaf DECIMATE shadow meshes from local mesh objects or managed placements. Reports evaluated counts/bounds, settings-bound source guard and approximation warnings. Does not modify sources.'),
 'generate_asset_proxies':(Generate,('allow_scene_edit',),'Generate guarded independent static collision or Cycles shadow-only meshes with sampled bidirectional surface errors. Preserves sources, validates closed positive-volume colliders, enforces shadow triangle/error budgets, and rolls back owned data on cooperative failure/cancellation. Does not attach physics or hide sources.'),
 'inspect_asset_proxies':(Inspect,(),'Inspect owned proxy geometry, source freshness, approximation proof, visibility and current guard. Physics attachment/export is separate; sampled errors are not exhaustive.'),
 'remove_asset_proxies':(Remove,('allow_scene_edit',),'Remove guarded owned proxy objects and collection, retaining source assets and shared materials. Refuses foreign collection membership, external references, rigid bodies and unowned collection contents.'),
}

COMMANDS.update({
 'inspect_render_visibility':(Visibility,(),'Inspect local object render exclusion and Cycles ray visibility, animation conflicts and guard. Cycles ray flags are not portable engine settings.'),
 'configure_render_visibility':(ConfigureVisibility,('allow_scene_edit',),'Patch guarded local render exclusion/Cycles ray visibility without Python. Refuses keyed/driven targeted flags and rolls back on cooperative cancellation. Disable a source shadow flag before generating its replacement proxy to preserve source freshness.'),
})
