"""Semantic trunk/major-branch selection and owned static convex collision pieces."""
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .nla_contracts import SafeName
from .mesh_contracts import Digest

class Source(Model):
    collection: SafeName
    min_radius_m: FiniteFloat = Field(default=.12,ge=0,le=10)
    max_branch_order: int = Field(default=1,strict=True,ge=0,le=8)
    max_colliders: int = Field(default=128,strict=True,ge=1,le=256)
    triangle_budget: int = Field(default=10000,strict=True,ge=4,le=100000)

class Create(Source):
    collision_collection: SafeName
    expected_plan: Digest
    display_offset_m: list[FiniteFloat] = Field(default=[0,0,0],min_length=3,max_length=3)
    hide_render: bool = True
    parent_to_root: bool = True
    @model_validator(mode='after')
    def separate(self):
        if self.collection==self.collision_collection or len(self.collision_collection.encode())>40:raise ValueError('Choose a distinct collision collection up to 40 UTF-8 bytes')
        if any(abs(x)>100000 for x in self.display_offset_m):raise ValueError('Collision display offset exceeds supported range')
        return self

class Read(Model):
    collision_collection: SafeName
    offset: int = Field(default=0,strict=True,ge=0,le=256)
    limit: int = Field(default=32,strict=True,ge=1,le=128)

class Remove(Read):
    expected_collision: Digest
    discard_derived_edits: bool = False

COMMANDS={
 'inspect_botanical_collision_source':(Source,(),'Plan ancestor-closed trunk/major-branch collision pieces by canonical branch order and radius, without realizing foliage. Each convex hull encloses all native vertices of its selected woody sleeve, including shared rings/root flare. Report actual triangle/volume/containment and explicit count budgets; no persistent edits.'),
 'create_botanical_collisions':(Create,('allow_scene_edit',),'Create guarded independent static convex collision meshes for selected trunk/major branches. Preserve source, placement and native selection; verify closed positive volumes and every selected sleeve vertex. Hidden from renders by default. parent_to_root=false creates independently placed unparented pieces for the existing rigid-body tools; no automatic physics or engine binding. Roll back cooperative failures.'),
 'inspect_botanical_collisions':(Read,(),'Inspect owned static botanical collision pieces, canonical branch mappings, source freshness, volume/containment proof and current removal guard. A removed/changed source does not invalidate the saved independent snapshot; geometry edits, physics or external references are reported.'),
 'remove_botanical_collisions':(Remove,('allow_scene_edit',),'Remove a guarded owned botanical collision snapshot while preserving source/unrelated data. Refuse foreign members, references or attached physics; edited derived geometry requires explicit discard_derived_edits.'),
}
