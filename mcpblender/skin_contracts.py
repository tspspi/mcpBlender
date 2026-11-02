"""Guarded raw skin-weight inspection, editing and repair."""
from typing import Annotated, Literal
from pydantic import Field, FiniteFloat, model_validator
from .config import Model
from .mesh_contracts import Named, Digest
from .nla_contracts import SafeName

Vertex=Annotated[int,Field(strict=True,ge=0)]


class SkinTarget(Named):
    name: SafeName
    armature: SafeName | None = None


class InspectSkin(SkinTarget):
    offset: int = Field(default=0,ge=0)
    limit: int = Field(default=32,ge=1,le=256)
    issues_only: bool = False
    max_influences: int = Field(default=4,ge=1,le=32)


class SkinEdit(SkinTarget):
    expected_weights: Digest
    make_single_user: bool = False
    respect_locks: bool = True


class WeightEntry(Model):
    vertex: Vertex
    weights: dict[SafeName,Annotated[FiniteFloat,Field(ge=0,le=1)]] = Field(max_length=512)


class SetWeights(SkinEdit):
    weights: list[WeightEntry] = Field(min_length=1,max_length=10000)
    normalize: bool = True
    allow_unweighted: bool = False
    @model_validator(mode='after')
    def unique(self):
        if len({v.vertex for v in self.weights})!=len(self.weights):raise ValueError('Vertex entries must be unique')
        return self


class Selection(SkinEdit):
    vertices: list[Vertex] | None = Field(default=None,min_length=1,max_length=200000)
    @model_validator(mode='after')
    def unique(self):
        if self.vertices is not None and len(set(self.vertices))!=len(self.vertices):raise ValueError('Selected vertices must be unique')
        return self


class RepairSettings(Selection):
    threshold: FiniteFloat = Field(default=.0001,ge=0,le=1)
    max_influences: int = Field(default=4,ge=1,le=32)
    unweighted: Literal['ERROR','KEEP','FALLBACK','NEAREST'] = 'ERROR'
    fallback_bone: SafeName | None = None
    @model_validator(mode='after')
    def fallback(self):
        if (self.unweighted=='FALLBACK') != bool(self.fallback_bone):raise ValueError('fallback_bone is required exactly for FALLBACK')
        return self


class SmoothWeights(RepairSettings):
    iterations: int = Field(default=1,ge=1,le=32)
    strength: FiniteFloat = Field(default=.5,gt=0,le=1)


class BonePair(Model):
    left: SafeName
    right: SafeName


class MirrorWeights(RepairSettings):
    axis: Literal['X','Y','Z'] = 'X'
    space: Literal['ARMATURE','MESH'] = 'ARMATURE'
    plane: FiniteFloat = 0
    direction: Literal['POSITIVE_TO_NEGATIVE','NEGATIVE_TO_POSITIVE','SWAP'] = 'POSITIVE_TO_NEGATIVE'
    tolerance: FiniteFloat = Field(default=.0001,gt=0,le=10000)
    bone_pairs: list[BonePair] = Field(default_factory=list,max_length=256)
    @model_validator(mode='after')
    def pairs(self):
        names=[n for p in self.bone_pairs for n in (p.left,p.right)]
        if len(names)!=len(set(names)):raise ValueError('Each mirror bone can belong to only one distinct pair')
        return self


class SkinBindingSettings(SkinTarget):
    expected_weights: Digest
    use_vertex_groups: bool = True
    use_bone_envelopes: bool = False
    preserve_volume: bool = False
    vertex_group: SafeName | Literal[''] = ''
    invert_vertex_group: bool = False


EDIT=('allow_scene_edit',)
COMMANDS={
 'inspect_skin_weights':(InspectSkin,(),'Inspect raw vertex weights, deform/nondeform groups, locks, normalization/influence issues, binding settings and a weight/topology/rest fingerprint. Vertex pagination can filter issues.'),
 'set_skin_weights':(SetWeights,EDIT,'Replace selected raw vertices\' deform influences with named weights, preserving nondeform groups and respecting locks by default. Normalizes unlocked remainder unless disabled; guarded atomic rollback, explicit shared-data isolation.'),
 'repair_skin_weights':(RepairSettings,EDIT,'Prune, cap and normalize selected/all raw skin weights. Preserve locks/nondeform groups; unweighted policy ERROR/KEEP/FALLBACK/nearest rest-bone segment. Reports progress/storage and rolls back failures/cancellation.'),
 'smooth_skin_weights':(SmoothWeights,EDIT,'Smooth selected weights over raw edge neighbors using frozen iterative inputs; prune/normalize with locks and explicit unweighted policy. Other vertices and nondeform groups remain unchanged.'),
 'mirror_skin_weights':(MirrorWeights,EDIT,'Mirror raw skin weights across a mesh/armature-local plane, with explicit bilateral bone pairs and direction. Refuses missing/ambiguous geometric matches; preserves destination locks/nondeform groups.'),
 'configure_skin_binding':(SkinBindingSettings,EDIT,'Configure the existing unique armature modifier\'s group/envelope/preserve-volume and mask settings with current weight fingerprint; does not rebind or change weights.'),
}
