"""Bounded near/mid botanical LOD plans and owned native lifecycle."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .wind_contracts import Plan
from .mesh_contracts import Digest
from .nla_contracts import SafeName

class Level(Model):
    leaf_budget: int = Field(strict=True,ge=1,le=100000)
    radial_sides: int = Field(default=5,strict=True,ge=5,le=16)
    min_branch_radius_m: FiniteFloat = Field(default=.02,ge=0,le=10)
    max_coverage_loss: FiniteFloat = Field(default=.25,ge=0,le=1)
    max_silhouette_loss: FiniteFloat = Field(default=.25,ge=0,le=1)
    triangle_budget: int = Field(default=30000000,strict=True,ge=1,le=30000000)

class Source(Plan):
    levels: list[Level] = Field(min_length=1,max_length=4)
    resolution: int = Field(default=128,strict=True,ge=32,le=256)
    views: list[Literal['FRONT','SIDE','TOP']] = Field(default=['FRONT','SIDE','TOP'],min_length=1,max_length=3)
    margin: FiniteFloat = Field(default=2.5,ge=0,le=5)
    silhouette_weight: int = Field(default=4,strict=True,ge=1,le=16)
    max_projected_triangles: int = Field(default=60000000,strict=True,ge=1,le=100000000)
    max_mask_bytes: int = Field(default=256*1024**2,strict=True,ge=1024,le=1024**3)
    max_gain_evaluations: int = Field(default=2000000,strict=True,ge=1,le=5000000)
    @model_validator(mode='after')
    def distinct(self):
        if len(set(self.views))!=len(self.views):raise ValueError('Choose distinct projection views')
        if any(a.leaf_budget<=b.leaf_budget for a,b in zip(self.levels,self.levels[1:])):raise ValueError('Leaf budgets must decrease')
        return self

class Create(Source):
    expected_plan: Digest
    lod_collection: SafeName
    display_offset_m: list[FiniteFloat] = Field(default=[0,0,0],min_length=3,max_length=3)
    @model_validator(mode='after')
    def offset(self):
        if any(abs(v)>100000 for v in self.display_offset_m):raise ValueError('Display offset exceeds supported range')
        return self

class Read(Model):
    lod_collection: SafeName

class Edit(Read):
    expected_lods: Digest

class Activate(Edit):
    level: int = Field(strict=True,ge=0,le=4)

class Remove(Edit):
    discard_derived_edits: bool = False

COMMANDS={
 'inspect_botanical_lod_source':(Source,(),'Plan nested greedy leaf LODs in fixed FRONT/SIDE/TOP opaque-blade coverage views. Retain ancestor-closed branch geometry/attachment IDs, radial side and triangle budgets; report quality losses and a source-bound guard. No native edits, optical or runtime performance proof.'),
 'create_botanical_lods':(Create,('allow_scene_edit',),'Create guarded independent near/mid botanical LODs plus full LOD0, with shared leaf templates, canonical wind IDs and native pose/count verification. Refuse failed coverage/triangle gates; preserve source. Cards/impostors/LOD GLB packaging remain separate.'),
 'inspect_botanical_lods':(Read,(),'Inspect owned botanical LOD contents, active level, coverage plan, native pose readback, shared prototypes and current mutation/removal guard.'),
 'activate_botanical_lod':(Activate,('allow_scene_edit',),'Guardedly select one native botanical LOD for viewport/render visibility. Preserve editable source and other scene objects.'),
 'remove_botanical_lods':(Remove,('allow_scene_edit',),'Guardedly remove only owned botanical LOD data, retaining materials and source. Foreign members/references refuse; edited derived data needs explicit discard.'),
}

class Export(Edit):
    material_mode: Literal['NONE','PARAMETERS'] = 'NONE'
    expected_materials: Digest|None = None
    @model_validator(mode='after')
    def material_guard(self):
        if self.material_mode=='PARAMETERS' and self.expected_materials is None:raise ValueError('PARAMETERS delivery needs expected_materials from inspect_vegetation_materials')
        if self.material_mode=='NONE' and self.expected_materials is not None:raise ValueError('expected_materials requires PARAMETERS delivery')
        return self
    directory: str = Field(min_length=1)
    placement: Literal['SOURCE','DISPLAYED'] = 'SOURCE'
    max_bytes: int = Field(default=512*1024**2,strict=True,ge=1024,le=512*1024**2)

class Validate(Model):
    directory: str = Field(min_length=1)

COMMANDS.update({
 'export_botanical_lods':(Export,('allow_library_write',),'Export an unchanged owned native botanical LOD profile into a new directory. Shared template GLBs occur once; per-level wood/shoot GLBs retain branch/wind fields and nested canonical leaf mappings. Independently validate before publication. SOURCE placement omits the display offset by default; DISPLAYED preserves it. No engine shader or optical qualification.'),
 'validate_botanical_lod_bundle':(Validate,(),'Independently decode/validate shared vegetation LOD files, recompute canonical selections/quality, verify attachment ancestry, wind fields, templates, triangle counts, UVs and metre placement. Works after native source/profile removal. Unsigned witnesses do not establish provenance.'),
})
