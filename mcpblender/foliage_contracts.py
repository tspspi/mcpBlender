"""Typed modular leaves and instanced foliage on managed botanical trees."""
from pydantic import Field,FiniteFloat,model_validator
from typing import Annotated,Literal
from .config import Model
from .mesh_contracts import Digest
from .nla_contracts import SafeName
from .botanical_contracts import Tree,Guard
class Leaf(Model):
    length: FiniteFloat = .12
    width: FiniteFloat = .065
    petiole: FiniteFloat = .006
    lobes: int = Field(default=5,strict=True)
    lobe_depth: FiniteFloat = .28
    curl: FiniteFloat = .012
    fold: FiniteFloat = .004
    vein_ridge: FiniteFloat = .0007
    rows: int = Field(default=24,strict=True)
    @model_validator(mode='after')
    def validate_shape(self):
        from .foliage import leaf_recipe
        leaf_recipe(self.model_dump());return self
class Foliage(Model):
    seed: int = Field(default=1,strict=True)
    shoots_per_bud: int = Field(default=6,strict=True)
    attachment_nodes: int = Field(default=10,strict=True)
    arrangement: Literal['ALTERNATE','OPPOSITE','WHORLED'] = 'ALTERNATE'
    shoot_length: FiniteFloat = .65
    spread: FiniteFloat = .7
    inclination: FiniteFloat = .25
    size_variation: FiniteFloat = .2
    variants: int = Field(default=3,strict=True)
    max_leaves: int = Field(default=100000,strict=True)
    max_expanded_triangles: int = Field(default=8000000,strict=True)
    leaf: Leaf = Field(default_factory=Leaf)
    @model_validator(mode='after')
    def validate_layout(self):
        from .foliage import recipe
        recipe(self.model_dump());return self
class ShapePlan(Model):
    leaf: Leaf = Field(default_factory=Leaf)
class Template(ShapePlan):
    name: SafeName
    expected_leaf: Digest
    @model_validator(mode='after')
    def bounded_name(self):
        if len(self.name.encode())>40:raise ValueError('Leaf template supports at most 40 UTF-8 bytes')
        return self
class LayoutPlan(Tree):
    foliage: Foliage = Field(default_factory=Foliage)
class Configure(LayoutPlan):
    expected_tree: Digest
    expected_foliage: Digest
    discard_derived_edits: bool = False
    secondary_uv_policy: Literal['PRESERVE','REPROJECT','DISCARD'] = 'PRESERVE'
class Remove(Guard):
    secondary_uv_policy: Literal['PRESERVE','REPROJECT','DISCARD'] = 'PRESERVE'
class Coverage(Tree):
    foliage: Foliage|None = None
    resolution: int = Field(default=128,strict=True,ge=32,le=256)
    views: Annotated[list[Literal['FRONT','SIDE','TOP']],Field(min_length=1,max_length=3)] = ['FRONT','SIDE','TOP']
    margin: FiniteFloat = Field(default=2.5,ge=0,le=5)
    max_projected_triangles: int = Field(default=60000000,strict=True,ge=1,le=100000000)
    include_masks: bool = False
    @model_validator(mode='after')
    def unique_views(self):
        if len(set(self.views))!=len(self.views):raise ValueError('Coverage views must be distinct')
        return self
class Elements(Tree):
    offset: int = Field(default=0,ge=0,le=100000)
    limit: int = Field(default=32,ge=1,le=128)
Color4=Annotated[list[Annotated[FiniteFloat,Field(ge=0,le=1)]],Field(min_length=4,max_length=4)]
class Material(Model):
    material: SafeName
class Optical(Material):
    expected_material: Digest
    front_color: Color4|None = None
    back_color: Color4|None = None
    transmission_color: Color4|None = None
    roughness: FiniteFloat|None = Field(default=None,ge=0,le=1)
    translucent_mix: FiniteFloat|None = Field(default=None,ge=0,le=1)
    double_sided: bool|None = None
    @model_validator(mode='after')
    def patch(self):
        if not any(getattr(self,k) is not None for k in ('front_color','back_color','transmission_color','roughness','translucent_mix','double_sided')):raise ValueError('Supply thin-foliage optical settings')
        if any(getattr(self,k) is not None and getattr(self,k)[3]!=1 for k in ('front_color','back_color','transmission_color')):raise ValueError('Leaf color alpha must be one; alpha-mask optics are separate')
        return self
COMMANDS={
 'inspect_botanical_coverage':(Coverage,(),'Inspect repeatable orthographic blade-triangle pixel coverage against the declared crown ellipse, local metre bounds, asymmetry and work budgets. Uses current managed foliage or a proposed recipe without editing. Reports resolution/clipping limits; excludes wood and shader opacity.'),
 'inspect_foliage_material':(Material,(),'Inspect actual managed thin-leaf front/back colors, roughness, translucency and explicit two-sided shader state with a shared-material guard. These optics are distinct from alpha masking and thickness.'),
 'configure_foliage_material':(Optical,('allow_scene_edit',),'Guardedly patch a shared managed leaf material without rebuilding leaves. Separate translucency from explicit backface transparency; preserve unknown graph edits and restore settings on cooperative failure.'),
 'plan_leaf_template':(ShapePlan,(),'Inspect a portable lobed leaf blade/petiole template with curvature, raised midrib, UVs, triangle and area metrics. Return leaf guard; no native edits.'),
 'create_leaf_template':(Template,('allow_scene_edit',),'Create an editable metre-recipe leaf, converting through object scale for the current scene units without changing unit settings. Return normalized recipe, scene scale and physical world_bounds_m with the default thin-leaf material. This is individual blade geometry, not a cutout atlas or foliage LOD.'),
 'plan_botanical_foliage':(LayoutPlan,(),'Plan deterministic bud-attached shoots and alternate/opposite/whorled leaves on a valid botanical source. Report shared prototype and expanded geometry budgets plus attachment guard.'),
 'configure_botanical_foliage':(Configure,('allow_scene_edit',),'Stage a full botanical master with shared leaf prototypes/Geometry Nodes instances and shoot geometry. Preserve root/bark, protect derived edits, include foliage in future growth regeneration and owned cleanup. Requires tree and foliage plan guards. Authored secondary layouts default to compatible PRESERVE; choose REPROJECT or DISCARD explicitly when geometry changes.'),
 'remove_botanical_foliage':(Remove,('allow_scene_edit',),'Stage and verify the woody master without its foliage component, retaining materials and preserving guarded root placement. Authored leaf secondary UVs require explicit secondary_uv_policy=DISCARD. No unowned data deletion.'),
 'list_botanical_leaves':(Elements,(),'Page deterministic leaf IDs, source branch/shoot attachments, transforms, variation/phase and flutter metadata. Semantic motion inputs only; no wind animation certification.'),
}
