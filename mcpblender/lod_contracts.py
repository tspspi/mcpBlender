"""Asset LOD generation, managed selection and validated static/skin/morph bundles."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .mesh_contracts import Digest
from .nla_contracts import SafeName


class Source(Model):
    name: SafeName
    deformation: Literal['STATIC','SKINNED','MORPH'] = 'STATIC'


class Level(Model):
    triangle_budget: int = Field(ge=4,le=500000)
    method: Literal['COLLAPSE','PLANAR','UNSUBDIVIDE'] = 'COLLAPSE'
    angle_degrees: FiniteFloat = Field(default=5,ge=0,le=180)
    iterations: int = Field(default=1,ge=1,le=6)


class Generate(Source):
    chain: SafeName
    expected_source: Digest
    levels: list[Level] = Field(min_length=1,max_length=7)
    transfer_normals: bool = True
    max_relative_error: FiniteFloat = Field(default=.1,ge=0,le=1)
    error_samples: int = Field(default=512,ge=16,le=4096)
    skin_max_influences: int = Field(default=4,ge=1,le=4)
    skin_joint_importance: FiniteFloat = Field(default=10,ge=0,le=1000)
    pose_frames: list[FiniteFloat] | None = Field(default=None,min_length=1,max_length=16)
    max_pose_error: FiniteFloat = Field(default=.1,ge=0,le=1)
    @model_validator(mode='after')
    def recipe(self):
        if len(self.chain.encode('utf-8'))>40:raise ValueError('Chain name supports at most 40 UTF-8 bytes')
        if self.pose_frames is not None and (len(set(self.pose_frames))!=len(self.pose_frames) or any(abs(f)>1048574 for f in self.pose_frames)):raise ValueError('Pose frames must be distinct and within native limits')
        budgets=[l.triangle_budget for l in self.levels]
        if any(a<=b for a,b in zip(budgets,budgets[1:])):raise ValueError('LOD budgets must strictly decrease')
        return self


class Chain(Model):
    chain: SafeName


class TimelineClip(Model):
    name: SafeName
    frame_start: int = Field(strict=True,ge=-1048574,le=1048574)
    frame_end: int = Field(strict=True,ge=-1048574,le=1048574)
    @model_validator(mode='after')
    def span(self):
        if not 1<=self.frame_end-self.frame_start<=10000:raise ValueError('Timeline clips require 2..10001 integer frames')
        return self


class Timeline(Model):
    timeline_clips: list[TimelineClip] | None = Field(default=None,min_length=1,max_length=32)
    @model_validator(mode='after')
    def names(self):
        if self.timeline_clips and len({c.name for c in self.timeline_clips})!=len(self.timeline_clips):raise ValueError('Timeline clip names must be distinct')
        return self


class ExportPlan(Chain,Timeline):
    animations: bool = True


class Guard(Chain):
    expected_chain: Digest


class Activate(Guard):
    level: int = Field(strict=True,ge=0,le=7)


class SampleSkin(Guard):
    pose_frames: list[FiniteFloat] | None = Field(default=None,min_length=1,max_length=16)
    error_samples: int = Field(default=512,ge=16,le=4096)
    max_pose_error: FiniteFloat = Field(default=.1,ge=0,le=1)
    @model_validator(mode='after')
    def frames(self):
        if self.pose_frames is not None and (len(set(self.pose_frames))!=len(self.pose_frames) or any(abs(f)>1048574 for f in self.pose_frames)):raise ValueError('Pose frames must be distinct and within native limits')
        return self


class Export(Guard,Timeline):
    directory: str = Field(min_length=1)
    animations: bool = True
    animation_samples: int = Field(default=3,ge=3,le=9)
    skin_tolerance: FiniteFloat = Field(default=.001,ge=.0000001,le=1)
    expected_animation: Digest | None = None


class InspectGLB(Model):
    path: str = Field(min_length=1)
    clip: SafeName | None = None
    offset: int = Field(default=0,ge=0,le=32)
    limit: int = Field(default=4,ge=1,le=8)
    animation_samples: int = Field(default=3,ge=3,le=9)
    sample_limit: int = Field(default=8,ge=0,le=16)


class Validate(Model):
    directory: str = Field(min_length=1)


COMMANDS={
 'inspect_glb_deformation':(InspectGLB,(),'Independently decode a library GLB with a single native-profile mesh, optional linear skin and relative morph targets. Read-only joint/target/clip inventory, bounded sampled world playback and replay fingerprints; embedded dense/sparse float morph buffers; no compressed/instanced geometry. Does not compare to Blender or certify appearance.'),
 'inspect_lod_source':(Source,(),'Inspect STATIC viewport geometry, MORPH relative shape keys or SKINNED raw rest geometry/linear binding, UV/material/attribute inventory and source guard. Skin mode reports weights, rig and suggested pose frames. Morph weights follow original source controllers; object-motion sources remain separate.'),
 'generate_lod_chain':(Generate,('allow_scene_edit',),'Create independent LOD0 and reduced geometry in a managed collection/root. MORPH transfers relative keys/masks with source-controlled weights; SKINNED also retains the existing linear rig, native-interpolated normalized/pruned weights and sampled pose validation. COLLAPSE/PLANAR/UNSUBDIVIDE, decreasing budgets, UV/material/normal checks and sampled bidirectional surface error; preserves source and cleans up cancellation/failures.'),
 'sample_lod_chain':(SampleSkin,(),'Sample current-timeline deformation of a SKINNED or MORPH LOD chain versus its source. Reports bounded bidirectional surface error at chosen/recommended poses, restores frame/visibility and refuses stale guards or excessive error; does not switch clips.'),
 'inspect_lod_chain':(Chain,(),'Inspect managed LOD meshes, recipes/budgets, sampled quality, source staleness and current-content fingerprint. Invalid or modified chains are not silently exportable.'),
 'activate_lod_level':(Activate,('allow_scene_edit',),'Select one managed LOD representation by viewport/render visibility, preserving source objects and geometry. Requires a current chain fingerprint.'),
 'inspect_lod_export':(ExportPlan,(),'Plan a static, skeletal or timeline-baked morph LOD bundle: current chain guard, compatible clip inventory, bind-only option, export blockers and full animation guard. Does not write files or switch clips.'),
 'export_lod_chain':(Export,('allow_library_write',),'Export each static, skeletal or morph LOD into a GLB plus checked manifest. Morphs bake explicit current-timeline ranges (drivers/NLA/constraints) onto owned proxies; source controls remain intact. Skin bundles validate joints/weights/curves and compare independent decoded playback with native poses; compatible integer-frame clips use zero-based seconds. Restore state and publish only after validation.'),
 'validate_lod_export':(Validate,(),'Independently re-read a generated LOD bundle, verify hashes, GLB triangle/attribute/dependency inventory and recorded skin replay fingerprints. No engine or silhouette certification.'),
}
