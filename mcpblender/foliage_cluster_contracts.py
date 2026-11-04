"""Bounded workload planning and independent botanical foliage sources."""
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .nla_contracts import SafeName
from .mesh_contracts import Digest

class Plan(Model):
    collection: SafeName
    anchor_order: int = Field(default=2,strict=True,ge=0,le=8)
    max_leaves: int = Field(default=512,strict=True,ge=1,le=1024)
    max_triangles: int = Field(default=100000,strict=True,ge=1,le=250000)
    max_clusters: int = Field(default=1024,strict=True,ge=1,le=4096)
    offset: int = Field(default=0,strict=True,ge=0,le=4096)
    limit: int = Field(default=32,strict=True,ge=1,le=64)

COMMANDS={'inspect_botanical_foliage_clusters':(Plan,(),
 'Plan deterministic semantic-axis/spatial foliage clusters without realizing instances or modifying the source. Partition every canonical leaf exactly once under explicit leaf, actual native template-triangle and cluster-count budgets. Return paged summaries and a page-independent source-bound fingerprint. Bounds describe leaf centres in source-local metres. This plans workloads only; it does not create cards, merge shaders or qualify optical/wind/far-LOD quality. Long-running plans support operation polling and cancellation.')}


class Create(Plan):
    cluster_collection: SafeName
    cluster_index: int = Field(strict=True,ge=0,le=4095)
    expected_plan: Digest
    display_offset_m: list[FiniteFloat] = Field(default=[0,0,0],min_length=3,max_length=3)
    @model_validator(mode='after')
    def separate(self):
        if self.collection==self.cluster_collection or len(self.cluster_collection.encode())>40:raise ValueError('Choose a distinct cluster collection up to 40 UTF-8 bytes')
        if any(abs(x)>100000 for x in self.display_offset_m):raise ValueError('Cluster display offset exceeds supported range')
        return self

class Read(Model):
    cluster_collection: SafeName

class Remove(Read):
    expected_cluster: Digest
    discard_derived_edits: bool = False

COMMANDS.update({
 'create_botanical_foliage_cluster':(Create,('allow_scene_edit',),'Create one guarded independent static cluster mesh from a foliage workload plan without realizing the full tree. Preserve actual template corner UVs, material bindings, smooth/sharp/seam flags and canonical leaf/branch mappings. Refuse incompatible variant UV schemas, custom split normals and unsupported object/generated/instance-dependent shader sampling. Materials remain shared; no automatic bake, card, wind or optical equivalence. Cooperative failures roll back owned edits.'),
 'inspect_botanical_foliage_cluster':(Read,(),'Inspect an owned independent foliage cluster snapshot, source freshness, canonical leaf mapping, UV schema, content/removal guard and foreign references. Shared materials remain editable; material sampling admission is recorded at creation. Source removal does not invalidate independent geometry.'),
 'remove_botanical_foliage_cluster':(Remove,('allow_scene_edit',),'Remove an owned guarded foliage cluster while preserving source/shared materials/unrelated data. Refuse foreign members/references/physics. Edited native contents require explicit discard_derived_edits.'),
})
