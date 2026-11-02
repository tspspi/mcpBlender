"""Typed object/pose constraints and current-timeline motion inspection."""
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, model_validator

from .config import Model
from .mesh_contracts import Named, Name, Digest, Vec3

ShortName=Annotated[str,Field(min_length=1,max_length=63)]
Axes=Annotated[list[bool],Field(min_length=3,max_length=3)]
Space=Literal['WORLD','LOCAL','POSE','LOCAL_WITH_PARENT']


class Target(Model):
    name: Name
    bone: Name | None = None


class Common(Model):
    influence: FiniteFloat = Field(default=1,ge=0,le=1)
    mute: bool = False


class Spatial(Common):
    owner_space: Space = 'WORLD'


class Targeted(Spatial):
    target: Target
    target_space: Space = 'WORLD'


class CopyLocation(Targeted):
    type: Literal['COPY_LOCATION']
    axes: Axes = [True,True,True]
    invert: Axes = [False,False,False]
    use_offset: bool = False


class CopyRotation(Targeted):
    type: Literal['COPY_ROTATION']
    axes: Axes = [True,True,True]
    invert: Axes = [False,False,False]
    mix_mode: Literal['REPLACE','ADD','BEFORE','AFTER','OFFSET'] = 'REPLACE'


class CopyTransforms(Targeted):
    type: Literal['COPY_TRANSFORMS']
    mix_mode: Literal['REPLACE','BEFORE_FULL','BEFORE','BEFORE_SPLIT','AFTER_FULL','AFTER','AFTER_SPLIT'] = 'REPLACE'
    remove_target_shear: bool = False


class Bounds(Spatial):
    minimum: Vec3 = [-1,-1,-1]
    maximum: Vec3 = [1,1,1]
    use_min: Axes = [True,True,True]
    use_max: Axes = [True,True,True]
    use_transform_limit: bool = False

    @model_validator(mode='after')
    def ordered(self):
        if any(lo>hi and a and b for lo,hi,a,b in zip(self.minimum,self.maximum,self.use_min,self.use_max)):
            raise ValueError('Enabled minimum bounds must not exceed maximum bounds')
        return self


class LimitLocation(Bounds):
    type: Literal['LIMIT_LOCATION']


class LimitScale(Bounds):
    type: Literal['LIMIT_SCALE']
    minimum: Vec3 = [0,0,0]
    maximum: Vec3 = [1,1,1]


class LimitRotation(Spatial):
    type: Literal['LIMIT_ROTATION']
    minimum_degrees: Vec3 = [-180,-180,-180]
    maximum_degrees: Vec3 = [180,180,180]
    axes: Axes = [True,True,True]
    use_transform_limit: bool = False

    @model_validator(mode='after')
    def ordered(self):
        if any(lo>hi and enabled for lo,hi,enabled in zip(self.minimum_degrees,self.maximum_degrees,self.axes)):
            raise ValueError('Enabled rotation minimum must not exceed maximum')
        return self


class DampedTrack(Targeted):
    type: Literal['DAMPED_TRACK']
    track_axis: Literal['TRACK_X','TRACK_Y','TRACK_Z','TRACK_NEGATIVE_X','TRACK_NEGATIVE_Y','TRACK_NEGATIVE_Z'] = 'TRACK_Y'


class IK(Common):
    type: Literal['IK']
    target: Target
    pole: Target | None = None
    pole_angle_degrees: FiniteFloat = Field(default=0,ge=-180,le=180)
    chain_count: int = Field(default=2,strict=True,ge=1,le=32)
    iterations: int = Field(default=128,strict=True,ge=1,le=1000)
    use_tail: bool = True
    use_stretch: bool = False


Settings=Annotated[CopyLocation|CopyRotation|CopyTransforms|LimitLocation|LimitRotation|LimitScale|DampedTrack|IK,Field(discriminator='type')]


class Owner(Named):
    bone: Name | None = None


class InspectConstraints(Owner):
    offset: int = Field(default=0,ge=0)
    limit: int = Field(default=64,ge=1,le=128)


class ConstraintEdit(Owner):
    constraint: ShortName
    expected_constraints: Digest


class ConfigureConstraint(ConstraintEdit):
    settings: Settings


class MoveConstraint(ConstraintEdit):
    index: int = Field(strict=True,ge=0,le=255)


class AnimationControl(Model):
    name: ShortName
    location: Vec3 = [0,0,0]
    display: Literal['PLAIN_AXES','ARROWS','SINGLE_ARROW','CIRCLE','CUBE','SPHERE'] = 'SPHERE'
    size: FiniteFloat = Field(default=.2,gt=0,le=10000)


class ConstraintSampling(Named):
    frames: list[Annotated[int,Field(strict=True,ge=-1048574,le=1048574)]] = Field(min_length=1,max_length=64)
    bones: list[Name] | None = Field(default=None,max_length=32)
    meshes: list[Name] = Field(default_factory=list,max_length=8)
    sample_limit: int = Field(default=16,ge=0,le=64)

    @model_validator(mode='after')
    def unique(self):
        if len(set(self.frames))!=len(self.frames) or len(set(self.meshes))!=len(self.meshes):raise ValueError('Sample frames and meshes must be unique')
        if self.bones is not None and len(set(self.bones))!=len(self.bones):raise ValueError('Sample bone names must be unique')
        return self


EDIT=('allow_scene_edit',)
COMMANDS={
    'create_animation_control':(AnimationControl,EDIT,'Create a named Empty target/pole helper without selection-dependent editing. Animate its transforms using set_keyframes.'),
    'inspect_animation_constraints':(InspectConstraints,(),'Inspect object or pose-bone constraint configuration, native validity, keyed/driven paths and stack fingerprint; page large imported stacks.'),
    'configure_animation_constraint':(ConfigureConstraint,EDIT,'Create/update a typed object/bone constraint. Full settings replace supported fields. Requires current stack fingerprint and conservative dependency validation; refuses keyed/driven constraint edits.'),
    'remove_animation_constraint':(ConstraintEdit,EDIT,'Remove an explicitly named supported constraint after stack/source guard checks; keyed/driven constraints are refused.'),
    'move_animation_constraint':(MoveConstraint,EDIT,'Move a supported named constraint to an absolute stack index with current fingerprint; does not rename resources or rewrite animation.'),
    'sample_constraint_animation':(ConstraintSampling,(),'Sample the current evaluated timeline, including constraints and animated controls, at explicit frames. Reports world transforms/bone endpoints and bound mesh deformation, restoring the current frame without switching clips.'),
}
