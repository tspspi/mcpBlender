"""Bounded, non-destructive controller and F-curve editing."""
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, model_validator

from .config import Model
from .mesh_contracts import Named, Name, Digest
from .constraint_contracts import ShortName

Frame = Annotated[FiniteFloat, Field(strict=True, ge=-1048574, le=1048574)]
Value = Annotated[FiniteFloat, Field(strict=True, ge=-1e12, le=1e12)]
Interpolation = Literal['CONSTANT', 'LINEAR', 'BEZIER']
HandleType = Literal['AUTO', 'AUTO_CLAMPED', 'VECTOR', 'ALIGNED', 'FREE']


class InspectChannels(Named):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=16, ge=1, le=32)
    key_offset: int = Field(default=0, ge=0)
    key_limit: int = Field(default=16, ge=1, le=128)


class NewClip(Named):
    output_clip: ShortName
    expected_animation: Digest


class ControlKey(Model):
    frame: Frame
    value: Value | Annotated[list[Value], Field(min_length=3, max_length=4)]


class ControlKeys(NewClip):
    bone: Name | None = None
    constraint: ShortName | None = None
    custom_property: Annotated[str,Field(min_length=1,max_length=63,pattern=r'^[A-Za-z][A-Za-z0-9_]*$')] | None = None
    property: Literal['location', 'rotation_degrees', 'rotation_quaternion', 'scale', 'influence', 'custom_scalar']
    keyframes: list[ControlKey] = Field(min_length=1, max_length=256)
    interpolation: Interpolation = 'LINEAR'

    @model_validator(mode='after')
    def values(self):
        if len({k.frame for k in self.keyframes}) != len(self.keyframes):
            raise ValueError('Key frames must be unique')
        if (self.property == 'influence') != bool(self.constraint):
            raise ValueError('Constraint must be specified exactly for influence keys')
        if (self.property=='custom_scalar') != bool(self.custom_property):
            raise ValueError('custom_property is required exactly for custom_scalar keys')
        for key in self.keyframes:
            if self.property == 'influence':
                if isinstance(key.value, list) or not 0 <= key.value <= 1:
                    raise ValueError('Influence values must be scalars in [0,1]')
            elif self.property=='custom_scalar':
                if isinstance(key.value,list):raise ValueError('Custom control values must be scalars')
            elif not isinstance(key.value, list) or len(key.value) != (4 if self.property == 'rotation_quaternion' else 3):
                raise ValueError('Transform keys require three components, or four quaternion components')
            elif self.property == 'rotation_quaternion' and abs(sum(v*v for v in key.value)-1) > 1e-5:
                raise ValueError('Quaternion keys must be normalized in WXYZ order')
        return self


class TransformKeys(Model):
    operation: Literal['TRANSFORM']
    pivot_frame: Frame = 0
    time_scale: FiniteFloat = Field(default=1, gt=0, le=1000)
    time_offset: Frame = 0
    value_scale: Value = 1
    value_offset: Value = 0


class DeleteKeys(Model):
    operation: Literal['DELETE']


class InterpolateKeys(Model):
    operation: Literal['INTERPOLATION']
    interpolation: Literal['CONSTANT', 'LINEAR', 'BEZIER', 'SINE', 'QUAD', 'CUBIC', 'QUART', 'QUINT', 'EXPO', 'CIRC', 'BACK', 'BOUNCE', 'ELASTIC']
    easing: Literal['AUTO', 'EASE_IN', 'EASE_OUT', 'EASE_IN_OUT'] = 'AUTO'
    amplitude: FiniteFloat = Field(default=0.8, ge=0, le=1000)
    back: FiniteFloat = Field(default=1.70158, ge=0, le=1000)
    period: FiniteFloat = Field(default=4.1, gt=0, le=1000)


class HandleKeys(Model):
    operation: Literal['HANDLES']
    left_type: HandleType = 'AUTO_CLAMPED'
    right_type: HandleType = 'AUTO_CLAMPED'
    left: Annotated[list[Value], Field(min_length=2, max_length=2)] | None = None
    right: Annotated[list[Value], Field(min_length=2, max_length=2)] | None = None

    @model_validator(mode='after')
    def manual(self):
        if (self.left is not None and self.left_type != 'FREE') or (self.right is not None and self.right_type != 'FREE'):
            raise ValueError('Explicit handle coordinates require FREE handle types')
        return self


class EditCurve(NewClip):
    data_path: Annotated[str, Field(min_length=1, max_length=512)]
    component: int = Field(default=0, strict=True, ge=0, le=3)
    frames: list[Frame] = Field(min_length=1, max_length=256)
    settings: Annotated[TransformKeys | DeleteKeys | InterpolateKeys | HandleKeys, Field(discriminator='operation')]

    @model_validator(mode='after')
    def unique(self):
        if len(set(self.frames)) != len(self.frames): raise ValueError('Selected key frames must be unique')
        if isinstance(self.settings, HandleKeys) and (self.settings.left is not None or self.settings.right is not None) and len(self.frames) != 1:
            raise ValueError('Explicit handles edit exactly one key')
        return self


EDIT = ('allow_scene_edit',)
COMMANDS = {
    'inspect_animation_channels': (InspectChannels, (), 'Inspect the active object action slot, paged F-curves/keys/handles/modifiers and binding fingerprint. Read-only; no clip switching.'),
    'set_control_keyframes': (ControlKeys, EDIT, 'Key object/bone transforms, numeric custom controls or named constraint influence into a NEW clip copied from the active action. Preserves source clip and unrelated channels; activates the independent result. Requires current animation fingerprint, no drivers or active NLA blending.'),
    'edit_animation_curve': (EditCurve, EDIT, 'Transform/retime, delete, interpolate/ease or edit handles of selected existing F-curve keys in a NEW independent active clip. Native channel units (radians for rotations). Guarded whitelist, source fingerprint and collision checks; source action remains unchanged.'),
}
