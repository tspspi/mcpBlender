"""Typed botanical model planning, managed woody masters and semantic delivery."""
from typing import Annotated,Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .mesh_contracts import Digest
from .nla_contracts import SafeName

Vec3=Annotated[list[FiniteFloat],Field(min_length=3,max_length=3)]
class Recipe(Model):
    species: Literal['QUERCUS_ROBUR'] = 'QUERCUS_ROBUR'
    seed: int = Field(default=1,strict=True,ge=0,le=2147483647)
    height: FiniteFloat = Field(default=14,ge=1,le=40)
    crown_width: FiniteFloat = Field(default=13,ge=1,le=40)
    crown_base: FiniteFloat = Field(default=.23,ge=.1,le=.6)
    trunk_radius: FiniteFloat = Field(default=.36,ge=.02,le=1)
    age_years: FiniteFloat = Field(default=45,ge=1,le=500)
    primary_branches: int = Field(default=9,strict=True,ge=3,le=16)
    attractors: int = Field(default=640,strict=True,ge=32,le=2048)
    iterations: int = Field(default=40,strict=True,ge=1,le=80)
    node_budget: int = Field(default=1600,strict=True,ge=128,le=4000)
    segment_length: FiniteFloat = Field(default=.55,ge=.1,le=2)
    persistence: FiniteFloat = Field(default=.45,ge=0,le=1)
    light_direction: Vec3 = [0,0,1]
    light_weight: FiniteFloat = Field(default=.12,ge=0,le=1)
    gravity: FiniteFloat = Field(default=.08,ge=0,le=1)
    avoidance: FiniteFloat = Field(default=.12,ge=0,le=1)
    randomness: FiniteFloat = Field(default=.2,ge=0,le=1)
    crown_offset: Annotated[list[FiniteFloat],Field(min_length=2,max_length=2)] = [0,0]
    pipe_exponent: FiniteFloat = Field(default=2,ge=1.5,le=3)
    root_flare: FiniteFloat = Field(default=1.5,ge=1,le=2)
    @model_validator(mode='after')
    def native_recipe(self):
        from .botany import recipe
        recipe(self.model_dump());return self
class Catalog(Model):
    pass
class Plan(Model):
    recipe: Recipe = Field(default_factory=Recipe)
class Create(Plan):
    collection: SafeName
    expected_model: Digest
    location: Vec3 = [0,0,0]
    radial_sides: int = Field(default=8,strict=True,ge=5,le=16)
    bark_tile_length: FiniteFloat = Field(default=1,gt=0,le=10)
    bark_material: SafeName|None = None
    @model_validator(mode='after')
    def name_budget(self):
        if len(self.collection.encode())>40:raise ValueError('Collection supports at most 40 UTF-8 bytes')
        return self
class Tree(Model):
    collection: SafeName
class Guard(Tree):
    expected_tree: Digest
class Inspect(Tree):
    kind: Literal['BRANCH','ORGAN'] = 'BRANCH'
    offset: int = Field(default=0,ge=0,le=4000)
    limit: int = Field(default=32,ge=1,le=128)
class Regenerate(Create):
    expected_tree: Digest
    preserve_placement: bool = True
    discard_derived_edits: bool = False
    secondary_uv_policy: Literal['PRESERVE','REPROJECT','DISCARD'] = 'PRESERVE'
class Export(Guard):
    path: str = Field(min_length=1)
    overwrite: bool = False
COMMANDS={
 'botanical_species_catalog':(Catalog,(),'Discover versioned botanical species/model profiles and bounded recipe defaults. First profile is an artistic English-oak woody scaffold, not biological simulation or completed foliage.'),
 'plan_botanical_tree':(Plan,(),'Generate a deterministic Blender-independent branch/bud graph from species, seed, crown/growth parameters. Return model guard, structural metrics and declared scope; creates no native IDs.'),
 'create_botanical_tree':(Create,('allow_scene_edit',),'Build a managed woody tree master from the inspected model guard: tapered sleeve geometry, growth-aligned bark UVs, branch/anchor/stiffness/phase attributes, semantic buds and persistent canonical JSON. Owns only its new data and rolls back cooperative failures.'),
 'inspect_botanical_tree':(Tree,(),'Inspect managed woody tree geometry/model validity, ownership, dependencies, structural metrics, recipe and current-content guard. Leaf area, wind and watertight junction quality remain separate.'),
 'list_botanical_elements':(Inspect,(),'Page stable branch or bud identifiers, parents, orders, age/radii/anchors and directions from a verified canonical model without returning an unbounded graph.'),
 'regenerate_botanical_tree':(Regenerate,('allow_scene_edit',),'Stage a fresh seeded botanical master before guarded public-name handoff. Preserve static root placement by default, refuse external native references and edited model text; discarding edited derived meshes requires explicit opt-in. Secondary UVs default to PRESERVE on compatible geometry; choose REPROJECT or DISCARD explicitly for changed layouts. Roll back before final native deletion.'),
 'remove_botanical_tree':(Guard,('allow_scene_edit',),'Remove an unambiguously owned botanical master using a current guard, retaining materials and refusing shared/externally referenced native IDs.'),
 'export_botanical_model':(Export,('allow_library_write',),'Export guarded canonical branch/bud model JSON for reuse without Blender. Retains generator/version/recipe/IDs; this is semantic data, not a GLB/foliage/wind export adapter.'),
}

from .secondary_uv_contracts import SecondaryLayout
class SecondaryUV(Guard,SecondaryLayout):
    pass

COMMANDS['create_botanical_secondary_uv']=(SecondaryUV,('allow_scene_edit',),'Guardedly author a new secondary UV on master wood or shared leaf-template roles. Preserve canonical growth model, geometry, attributes, original UVs and material sampling; publish the staged batch with updated native content guards. Regeneration explicitly preserves compatible maps, reprojects saved settings or discards them. Shared templates do not form an instance lightmap atlas.')
