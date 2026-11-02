"""Native simple-expression drivers with typed numeric targets and inputs."""
import ast
import math
import keyword
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, model_validator

from .config import Model
from .mesh_contracts import Named, Name, Digest
from .constraint_contracts import ShortName

ScalarName=Annotated[str,Field(min_length=1,max_length=63,pattern=r'^[A-Za-z][A-Za-z0-9_]*$')]
FUNCTIONS={'radians','degrees','abs','fabs','floor','ceil','trunc','round','int','sin','cos','tan','asin','acos','atan','atan2','exp','log','sqrt','pow','fmod','lerp','clamp','smoothstep','min','max'}
CONSTANTS={'pi','e','frame'}


def validate_expression(expression,names):
    if len(expression.encode())>255:raise ValueError('Driver expression is limited to 255 UTF-8 bytes')
    try:tree=ast.parse(expression,mode='eval')
    except (SyntaxError,ValueError,RecursionError) as exc:raise ValueError('Invalid numeric driver expression') from exc
    nodes=list(ast.walk(tree))
    if len(nodes)>128:raise ValueError('Driver expression exceeds 128 syntax nodes')
    allowed=(ast.Expression,ast.BinOp,ast.UnaryOp,ast.BoolOp,ast.Compare,ast.IfExp,ast.Call,ast.Name,ast.Load,ast.Constant,
             ast.Add,ast.Sub,ast.Mult,ast.Div,ast.Pow,ast.Mod,ast.USub,ast.UAdd,ast.Not,ast.And,ast.Or,ast.Eq,ast.NotEq,ast.Lt,ast.LtE,ast.Gt,ast.GtE)
    for node in nodes:
        if not isinstance(node,allowed):raise ValueError('Only numeric native driver expressions are supported')
        if isinstance(node,ast.Name) and node.id not in set(names)|FUNCTIONS|CONSTANTS:raise ValueError('Unknown driver variable/function: '+node.id)
        if isinstance(node,ast.Call) and (not isinstance(node.func,ast.Name) or node.func.id not in FUNCTIONS or node.keywords):raise ValueError('Only allowlisted native numeric function calls are supported')
        if isinstance(node,ast.Constant) and (type(node.value) not in {float,int,bool} or abs(node.value)>1e12 or not math.isfinite(node.value)):raise ValueError('Driver constants must be finite numeric values up to 1e12')
    return expression


class BoneOwner(Model):
    bone: Name | None = None


class TransformChannel(BoneOwner):
    kind: Literal['TRANSFORM']
    property: Literal['location','rotation_euler','rotation_quaternion','scale']
    component: int = Field(strict=True,ge=0,le=3)
    @model_validator(mode='after')
    def component_size(self):
        if self.component==3 and self.property!='rotation_quaternion':raise ValueError('Component outside transform dimensions')
        return self


class PropertyChannel(BoneOwner):
    kind: Literal['PROPERTY']
    property: ScalarName


class ConstraintChannel(BoneOwner):
    kind: Literal['CONSTRAINT']
    constraint: ShortName


class ShapeChannel(Model):
    kind: Literal['SHAPE_KEY']
    key: Name


Channel=Annotated[TransformChannel|PropertyChannel|ConstraintChannel|ShapeChannel,Field(discriminator='kind')]


class PropertyVariable(PropertyChannel):
    name: ScalarName
    object: Name


class ShapeVariable(ShapeChannel):
    name: ScalarName
    object: Name


class TransformVariable(BoneOwner):
    kind: Literal['TRANSFORM']
    name: ScalarName
    object: Name
    transform: Literal['LOC_X','LOC_Y','LOC_Z','ROT_X','ROT_Y','ROT_Z','SCALE_X','SCALE_Y','SCALE_Z']
    space: Literal['WORLD_SPACE','LOCAL_SPACE','TRANSFORM_SPACE'] = 'WORLD_SPACE'
    rotation_mode: Literal['AUTO','XYZ','XZY','YXZ','YZX','ZXY','ZYX'] = 'AUTO'


Variable=Annotated[PropertyVariable|ShapeVariable|TransformVariable,Field(discriminator='kind')]


class DriverSettings(Model):
    expression: Annotated[str,Field(min_length=1,max_length=255)]
    variables: list[Variable] = Field(default_factory=list,max_length=8)
    @model_validator(mode='after')
    def formula(self):
        names=[v.name for v in self.variables]
        if len(set(names))!=len(names) or set(names)&(FUNCTIONS|CONSTANTS) or any(keyword.iskeyword(n) for n in names):raise ValueError('Variable names must be unique and not reserved')
        validate_expression(self.expression,names)
        return self


class InspectDrivers(Named):
    offset: int = Field(default=0,ge=0)
    limit: int = Field(default=32,ge=1,le=64)


class DriverEdit(Named):
    channel: Channel
    expected_drivers: Digest


class ConfigureDriver(DriverEdit):
    settings: DriverSettings


class ScalarProperty(Named,BoneOwner):
    property: ScalarName
    value: FiniteFloat = Field(ge=-1e12,le=1e12)
    minimum: FiniteFloat = Field(default=0,ge=-1e12,le=1e12)
    maximum: FiniteFloat = Field(default=1,ge=-1e12,le=1e12)
    description: Annotated[str,Field(max_length=256)] = ''
    @model_validator(mode='after')
    def limits(self):
        if self.property.startswith('mcpblender_'):raise ValueError('Reserved property prefix')
        if not self.minimum<=self.value<=self.maximum:raise ValueError('Value must lie within minimum/maximum')
        return self


EDIT=('allow_scene_edit',)
COMMANDS={
 'inspect_animation_drivers':(InspectDrivers,(),'Inspect native object/pose/shape-key drivers, source variables, validity and configuration fingerprint. Imported unowned drivers remain inspect-only.'),
 'configure_animation_driver':(ConfigureDriver,EDIT,'Create/update a managed native simple-expression driver on a typed transform, scalar property, constraint influence or relative shape-key value. Validates numeric formula, inputs and dependency cycles; requires current driver fingerprint.'),
 'remove_animation_driver':(DriverEdit,EDIT,'Remove an explicitly selected managed driver with current fingerprint. Leaves the current driven property value in place; source clips/properties are not deleted.'),
 'set_animation_property':(ScalarProperty,EDIT,'Create/set a bounded numeric custom control property on an object or pose bone. Refuses keyed/driven properties; use guarded control keyframes for animation.'),
}
