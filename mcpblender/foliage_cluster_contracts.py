"""Read-only workload planning for bounded botanical foliage sources."""
from pydantic import Field
from .config import Model
from .nla_contracts import SafeName

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
