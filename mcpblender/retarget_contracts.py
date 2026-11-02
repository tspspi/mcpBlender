"""Explicit rest-aware motion transfer to independent target assets."""
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, model_validator

from .config import Model
from .mesh_contracts import Named, Name, Digest, Vec3
from .nla_contracts import SafeName, NlaName
from .curve_contracts import Frame


class BoneMap(Model):
    source: SafeName
    target: SafeName
    rotation_correction_degrees: Vec3 = [0,0,0]


class RetargetPlan(Named):
    name: SafeName
    source: SafeName
    mappings: list[BoneMap] = Field(default_factory=list,max_length=256)
    rotation_mode: Literal['LOCAL_POSE','ARMATURE_DELTA'] = Field(default='LOCAL_POSE',description='LOCAL_POSE copies joint-local basis rotations; ARMATURE_DELTA transfers armature-space rotation relative to rest.')
    translation: Literal['NONE','ROOT','ALL'] = 'ROOT'
    translation_scale: FiniteFloat | None = Field(default=None,gt=0,le=1e12,description="Uniform translation multiplier; defaults to median mapped rest-bone length ratio.")
    scale_mode: Literal['IGNORE','COPY_LOCAL'] = 'IGNORE'
    alignment_degrees: Vec3 = Field(default=[0,0,0],description='Source-to-target armature alignment for ARMATURE_DELTA and object root motion; local joints use per-map corrections.')
    object_motion: Literal['COPY','IGNORE'] = 'COPY'

    @model_validator(mode='after')
    def unique(self):
        if len({m.source for m in self.mappings})!=len(self.mappings) or len({m.target for m in self.mappings})!=len(self.mappings):
            raise ValueError('Source and target bones must each occur at most once')
        return self


class RetargetMesh(Model):
    source: SafeName
    output: NlaName


class RetargetAnimation(RetargetPlan):
    mappings: list[BoneMap] = Field(min_length=1,max_length=256)
    output_rig: NlaName
    clip: NlaName
    meshes: list[RetargetMesh] = Field(default_factory=list,max_length=8)
    frame_start: int = Field(strict=True,ge=-1048574,le=1048574)
    frame_end: int = Field(strict=True,ge=-1048574,le=1048574)
    source_start: Frame | None = None
    playback_speed: FiniteFloat = Field(default=1,gt=0,le=1000)
    reference_frame: Frame | None = None
    expected_source_rig: Digest
    expected_target_rig: Digest
    tolerance: FiniteFloat = Field(default=.0001,ge=.000001,le=.01)

    @model_validator(mode='after')
    def bounded(self):
        if not 1<=self.frame_end-self.frame_start+1<=500:raise ValueError('Retarget range must contain 1..500 integer target frames')
        start=self.source_start if self.source_start is not None else self.frame_start
        if start+(self.frame_end-self.frame_start)*self.playback_speed>1048574:raise ValueError('Source sample range exceeds native timeline bounds')
        outputs=[self.output_rig]+[m.output for m in self.meshes]
        if len(set(outputs))!=len(outputs) or len({m.source for m in self.meshes})!=len(self.meshes):raise ValueError('Output names and source meshes must be unique')
        return self


COMMANDS={
 'inspect_animation_retarget':(RetargetPlan,(),'Plan explicit bone/rest motion transfer: rig fingerprints, hierarchy/rest differences, exact-name suggestions, translation roots and median bone-length scale. Does not choose semantic humanoid mappings or alter the timeline.'),
 'retarget_animation':(RetargetAnimation,('allow_scene_edit',),'Transfer the source current evaluated timeline into an independent target-derived rig, quaternion clip and optional copied skins. Explicit bone mapping/rest modes, root motion and timing; verifies keyed output against computed transfer every integer frame, preserving both source assets.'),
}
