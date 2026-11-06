"""Captured first-hit leaf selection and source-preserving native snapshots."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .card_views import View
from .nla_contracts import SafeName
from .mesh_contracts import Digest
from .depth_asset_contracts import RenderRole

class TemplateReduction(Model):
    triangle_budget: int = Field(default=32,strict=True,ge=16,le=512)
    max_relative_error: FiniteFloat = Field(default=.02,strict=True,gt=0,le=1)
    max_area_relative_error: FiniteFloat = Field(default=.02,strict=True,ge=0,le=1)
    error_samples: int = Field(default=512,strict=True,ge=16,le=4096)

class BladeCardEntry(Model):
    asset: SafeName
    directory: str = Field(min_length=1)

class BladeCards(Model):
    bake_collection: SafeName
    expected_preparation: Digest
    entries: list[BladeCardEntry] = Field(min_length=1,max_length=16)
    max_bytes: int = Field(default=512*1024**2,strict=True,ge=1024,le=2*1024**3)
    max_texture_bytes: int = Field(default=128*1024**2,strict=True,ge=1024,le=512*1024**2)
    @model_validator(mode='after')
    def distinct(self):
        if len({e.asset for e in self.entries})!=len(self.entries) or len({e.directory for e in self.entries})!=len(self.entries):raise ValueError('Choose distinct blade roles and bundle directories')
        return self

class Source(Model):
    blade_cards: BladeCards|None = Field(default=None,description='Optional guarded native blade-card adoption from unchanged preparation and exact projected NORMAL/ALPHA bundles for every leaf variant. Preserve original native thin/back optics, use source UV lookup for managed procedural color, retain exact petiole geometry/original UVs and selected IDs/poses. Approximate static representation, not optical/wind/far acceptance; mutually exclusive with template_reduction.')
    directory: str = Field(min_length=1)
    views: list[View] = Field(default=['FRONT'],min_length=1,max_length=10)
    selection: Literal['OBSERVED','UNOBSERVED','COLUMN_COMPLEMENT'] = Field(default='UNOBSERVED',description='OBSERVED/UNOBSERVED select whole source leaves. COLUMN_COMPLEMENT retains all leaves with private materials clipping matching reference component columns; requires exactly one view. Static approximation, not face identity or optical equivalence.')
    template_reduction: TemplateReduction|None = Field(default=None,description='Optional copy-only blade collapse, exact petiole geometry/UV and source-loop-normal transfer. Pin triangle, sampled surface-error and material-region area limits. Preserves all selected instance IDs/poses; no optical acceptance implied.')
    include_structure: bool = True
    render_role: RenderRole = 'ALL_RAYS'
    structure_render_role: RenderRole|None = Field(default=None,description='Optional separate role for copied wood/shoot/bud objects. Defaults to the leaf render_role. Requires include_structure=true.')
    alpha_threshold: FiniteFloat = Field(default=.001,gt=0,lt=1)
    max_total_pixels: int = Field(default=4194304,strict=True,ge=1024,le=10485760)
    @model_validator(mode='after')
    def distinct(self):
        if self.blade_cards and self.template_reduction:raise ValueError('Choose blade_cards or template_reduction')
        if self.selection=='COLUMN_COMPLEMENT' and len(self.views)!=1:raise ValueError('COLUMN_COMPLEMENT requires exactly one capture view')
        if self.structure_render_role is not None and not self.include_structure:raise ValueError('structure_render_role requires include_structure=true')
        if len(set(self.views))!=len(self.views):raise ValueError('Choose distinct capture views')
        return self

class Create(Source):
    subset_collection: SafeName
    expected_plan: Digest

class Read(Model):
    subset_collection: SafeName

class Remove(Read):
    expected_subset: Digest

COMMANDS={
 'inspect_botanical_subset_source':(Source,(),'Plan a native subset from union of one-sample opaque component IDs observed in selected capture views. OBSERVED keeps these source leaves, UNOBSERVED keeps their complement. COLUMN_COMPLEMENT requires one view, retains every leaf and plans private root-relative component-column clipping with original BSDF outside matched cells. Revalidate exact managed source tree/resources/frame/placement and component inventory. Compact counts/digests and bounded previews, no guessed visibility census or source edits.'),
 'create_botanical_subset':(Create,('allow_scene_edit',),'Create a guarded hidden native snapshot with compact point mesh retaining original semantic IDs, instance graph and shared private leaf templates; optionally copy wood/shoot meshes. Preserve source geometry, source visibility and materials. Retain semantic IDs and source poses under selection. Whole-leaf modes retain shared guarded materials. COLUMN_COMPLEMENT privately wraps leaf materials and packs the captured ID grid, retaining all native leaves and clipping same-component pixel columns; original structural/source materials remain guarded dependencies. The projector follows uniform positive root placement. Same-leaf self-occlusion is ambiguous; this is not a face partition. A new instancer can change object-dependent shader Random; not an exact rendered partition or optical certificate. Optional template_reduction copies blade-collapse templates, protects exact petioles/UVs and transfers source loop normals; pins triangle/sampled-local-error/material-region-area policy and deterministic report. Instance IDs/poses stay fixed; optical and far-performance qualification remain separate. Cooperative failure rolls back new owned resources.'),
 'inspect_botanical_subset':(Read,(),'Inspect saved native subset ownership, content, material dependencies, selected leaf counts and removal guard without capture files. Display visibility and uniform positive root placement may change. Report source freshness separately; no optical certification.'),
 'remove_botanical_subset':(Remove,('allow_scene_edit',),'Remove only an unchanged guarded native subset and its private resources. Refuse stale guards, edits or foreign references; preserve shared materials, source and capture files.'),
}
