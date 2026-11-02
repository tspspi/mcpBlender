"""Guarded native action layering and composite timeline inspection."""
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, model_validator

from .config import Model
from .mesh_contracts import Named, Name, Digest
from .curve_contracts import Frame

NlaName=Annotated[str,Field(min_length=1,max_length=63,pattern=r'^[^\x00]+$')]
SafeName=Annotated[Name,Field(pattern=r'^[^\x00]+$')]

Blend=Literal['REPLACE','ADD','SUBTRACT','MULTIPLY','COMBINE']
Extrapolation=Literal['NOTHING','HOLD_FORWARD','HOLD']


class Target(Named):
    name: SafeName
    target: Literal['OBJECT','SHAPE_KEYS'] = 'OBJECT'


class InspectNLA(Target):
    offset: int = Field(default=0,ge=0)
    limit: int = Field(default=16,ge=1,le=64)


class Guard(Target):
    expected_nla: Digest


class Track(Guard):
    track: NlaName


class TrackSettings(Track):
    mute: bool = False
    solo: bool = False
    after_track: NlaName | None = None


class MoveTrack(Track):
    index: int = Field(strict=True,ge=0,le=63)


class Strip(Track):
    strip: NlaName


class StripSettings(Model):
    clip: SafeName
    slot: SafeName | None = None
    start: Frame
    action_start: Frame
    action_end: Frame
    scale: FiniteFloat = Field(default=1,ge=.0001,le=1000)
    repeat: FiniteFloat = Field(default=1,ge=.1,le=1000)
    reverse: bool = False
    blend: Blend = 'REPLACE'
    extrapolation: Extrapolation = 'NOTHING'
    influence: FiniteFloat = Field(default=1,ge=0,le=1)
    blend_in: FiniteFloat = Field(default=0,ge=0,le=1048574)
    blend_out: FiniteFloat = Field(default=0,ge=0,le=1048574)
    mute: bool = False

    @model_validator(mode='after')
    def span(self):
        length=(self.action_end-self.action_start)*self.scale*self.repeat
        if length<.001 or self.start+length>1048574:raise ValueError('Strip duration must be positive and its end within the timeline')
        if self.blend_in+self.blend_out>length:raise ValueError('Fade lengths must fit within the strip duration')
        return self


class ConfigureStrip(Strip):
    settings: StripSettings


class Playback(Guard):
    use_nla: bool = True
    clear_active_action: bool = False
    active_blend: Blend = 'REPLACE'
    active_influence: FiniteFloat = Field(default=1,ge=0,le=1)
    active_extrapolation: Extrapolation = 'HOLD'
    reset_base: bool = False
    @model_validator(mode='after')
    def explicit_reset(self):
        if self.reset_base and not self.clear_active_action:raise ValueError('Base reset requires explicit active-action clearing')
        return self


EDIT=('allow_scene_edit',)
COMMANDS={
 'inspect_nla':(InspectNLA,(),'Inspect object or shape-key NLA tracks/strips, active-action layering, clip-slot/source fingerprints and supported-edit ownership without switching clips.'),
 'configure_nla_track':(TrackSettings,EDIT,'Create a named managed NLA track or set its mute/solo flags. New tracks append or insert after an explicit track. Requires current whole-stack fingerprint; no source clip is edited.'),
 'configure_nla_strip':(ConfigureStrip,EDIT,'Create/update a named action strip on a managed track: action range, start/scale/repeat/reverse, blend, influence/fades and extrapolation. Builds a validated replacement track before committing; refuses overlaps or unsupported existing children.'),
 'remove_nla_strip':(Strip,EDIT,'Remove a named managed strip by rebuilding its managed track while retaining all source actions and other tracks.'),
 'remove_nla_track':(Track,EDIT,'Remove a managed NLA track containing only supported managed strips; source actions are retained.'),
 'move_nla_track':(MoveTrack,EDIT,'Move a track to an absolute bottom-to-top index. Preserves imported neighbors; moving to index zero requires a supported managed prefix because native insertion cannot precede the first track.'),
 'configure_nla_playback':(Playback,EDIT,'Set NLA enable/active-action blending; optionally explicitly clear and retain the active action. Optional base reset neutralizes rig bone transforms or creates a generated zero-shape foundation; object transforms are preserved. Composite sampling uses the current timeline.'),
}
