"""Guarded, additive rest-skeleton refinement without arbitrary RNA paths."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .mesh_contracts import Named,Digest,Vec3
from .nla_contracts import SafeName

ScaleMode=Literal['FULL','FIX_SHEAR','ALIGNED','AVERAGE','NONE','NONE_LEGACY']


class RestTarget(Named):
    name: SafeName
    offset: int = Field(default=0,ge=0)
    limit: int = Field(default=128,ge=1,le=512)


class BonePatch(Model):
    name: SafeName
    head: Vec3 | None = None
    tail: Vec3 | None = None
    roll_degrees: FiniteFloat | None = None
    parent: SafeName | Literal[''] | None = None
    connected: bool | None = None
    deform: bool | None = None
    inherit_scale: ScaleMode | None = None
    inherit_rotation: bool | None = None
    local_location: bool | None = None
    @model_validator(mode='after')
    def changed(self):
        if not any(getattr(self,k) is not None for k in type(self).model_fields if k!='name'):raise ValueError('Bone patch must contain a change')
        return self


class AddBone(Model):
    name: SafeName
    head: Vec3
    tail: Vec3
    roll_degrees: FiniteFloat = 0
    parent: SafeName | Literal[''] = ''
    connected: bool = False
    deform: bool = True
    inherit_scale: ScaleMode = 'FULL'
    inherit_rotation: bool = True
    local_location: bool = True


    @model_validator(mode='after')
    def native_name(self):
        if len(self.name.encode('utf-8'))>63:raise ValueError('New bone names support at most 63 UTF-8 bytes')
        return self


class EditRest(RestTarget):
    expected_rest: Digest
    bones: list[BonePatch] = Field(default_factory=list,max_length=512)
    add_bones: list[AddBone] = Field(default_factory=list,max_length=512)
    make_single_user: bool = False
    allow_deformation_change: bool = False
    @model_validator(mode='after')
    def edits(self):
        names=[b.name for b in self.bones+self.add_bones]
        if not names or len(names)!=len(set(names)):raise ValueError('Edits require distinct existing/new bone names')
        return self


COMMANDS={
 'inspect_armature_rest':(RestTarget,(),'Inspect paged rest bones, hierarchy/inheritance, shared users and deformation/animation impact with a rest fingerprint. Does not switch modes or modify the scene.'),
 'edit_armature_rest':(EditRest,('allow_scene_edit',),'Patch existing bone head/tail/roll/parent/connectivity/deform/inheritance or add bones. Guarded whole-hierarchy plan, connected-head following, explicit shared isolation and deformation-change acknowledgement. Retains named animation channels/weights; does not preserve their evaluated motion. Rollback on ordinary errors/cancellation.'),
}
