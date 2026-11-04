"""High-level, guarded canopy study creation for agents without bpy knowledge."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .mesh_contracts import Digest
from .nla_contracts import SafeName

class Catalog(Model):
    pass

class Plan(Model):
    preset: Literal['OAK_CANOPY_STUDY'] = 'OAK_CANOPY_STUDY'
    seed: int = Field(default=1,strict=True,ge=0,le=2147483647)
    max_leaves: int = Field(default=100000,strict=True,ge=1,le=100000)
    max_expanded_triangles: int = Field(default=30000000,strict=True,ge=1000,le=30000000,description='Total wood, shoots and expanded leaf-instance triangles')

class Create(Plan):
    collection: SafeName
    expected_preset: Digest
    location: list[FiniteFloat] = Field(default=[0,0,0],min_length=3,max_length=3)
    @model_validator(mode='after')
    def name_budget(self):
        if len(self.collection.encode())>40:raise ValueError('Collection supports at most 40 UTF-8 bytes')
        return self

COMMANDS={
 'botanical_asset_presets':(Catalog,(),'Discover versioned high-level botanical reference recipes with explicit modeling/qualification scope. Presets create editable masters and shared templates, not opaque imported geometry.'),
 'plan_botanical_asset_preset':(Plan,(),'Plan a dense 14m oak canopy study from one seed: woody/foliage guards, explicit leaf and expanded-triangle limits, stored-versus-expanded triangles, native surface recipes and downstream budget hints. Does not change Blender or measure visual canopy quality.'),
 'create_botanical_asset_preset':(Create,('allow_scene_edit',),'Create the guarded planned oak study as an editable master with shared leaf templates and procedural bark/leaf detail. Own new data only; rollback failure/cancellation before handoff. Preserve explicit caller budgets. Return ordinary botanical tree state for further structured edits; no complete game-asset, lighting or biological qualification.'),
}
