"""Captured first-hit leaf selection and source-preserving native snapshots."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .card_views import View
from .nla_contracts import SafeName
from .mesh_contracts import Digest
from .depth_asset_contracts import RenderRole

class Source(Model):
    directory: str = Field(min_length=1)
    views: list[View] = Field(default=['FRONT'],min_length=1,max_length=10)
    selection: Literal['OBSERVED','UNOBSERVED'] = 'UNOBSERVED'
    include_structure: bool = True
    render_role: RenderRole = 'ALL_RAYS'
    structure_render_role: RenderRole|None = Field(default=None,description='Optional separate role for copied wood/shoot/bud objects. Defaults to the leaf render_role. Requires include_structure=true.')
    alpha_threshold: FiniteFloat = Field(default=.001,gt=0,lt=1)
    max_total_pixels: int = Field(default=4194304,strict=True,ge=1024,le=10485760)
    @model_validator(mode='after')
    def distinct(self):
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
 'inspect_botanical_subset_source':(Source,(),'Plan a native subset from union of one-sample opaque component IDs observed in selected capture views. OBSERVED keeps these source leaves, UNOBSERVED keeps their complement. Revalidate exact managed source tree/resources/frame/placement and component inventory. Compact counts/digests and bounded previews, no guessed visibility census or source edits.'),
 'create_botanical_subset':(Create,('allow_scene_edit',),'Create a guarded hidden native snapshot with private point mesh, selection graph and shared private leaf templates; optionally copy wood/shoot meshes. Preserve source geometry, source visibility and materials. Retain semantic IDs and source poses under selection. Source materials remain shared guarded dependencies. A new instancer can change object-dependent shader Random; not an exact rendered partition, reduced template LOD or optical certificate. Cooperative failure rolls back new owned resources.'),
 'inspect_botanical_subset':(Read,(),'Inspect saved native subset ownership, content, material dependencies, selected leaf counts and removal guard without capture files. Display visibility and uniform positive root placement may change. Report source freshness separately; no optical certification.'),
 'remove_botanical_subset':(Remove,('allow_scene_edit',),'Remove only an unchanged guarded native subset and its private resources. Refuse stale guards, edits or foreign references; preserve shared materials, source and capture files.'),
}
