"""Typed guarded numeric mesh fields and local coordinate ramps."""
from typing import Annotated,Literal
from pydantic import Field,StrictBool,StrictInt,model_validator
from .config import Model
from .mesh_contracts import Name,Digest
from . import attribute_values as values

Number=Annotated[float,Field(strict=True,allow_inf_nan=False)]
Row=StrictBool|StrictInt|Number|Annotated[list[Number],Field(min_length=3,max_length=4)]
Kind=Literal['FLOAT','INT','BOOLEAN','FLOAT_VECTOR','FLOAT_COLOR']
Domain=Literal['POINT','EDGE','FACE','CORNER']

class Inspect(Model):
    name: Name
    attribute: Name|None = None
    evaluated: bool = False
    offset: int = Field(default=0,strict=True,ge=0,le=4000000)
    limit: int = Field(default=32,strict=True,ge=1,le=128)

class Edit(Model):
    name: Name
    attribute: Name
    expected_attributes: Digest
    make_single_user: bool = False
    @model_validator(mode='after')
    def attribute_name(self):values.safe_name(self.attribute);return self

class Create(Edit):
    data_type: Kind
    domain: Domain = 'POINT'
    value: Row
    @model_validator(mode='after')
    def fill(self):values.row(self.data_type,self.value);return self

class Update(Edit):
    value: Row|None = None
    values: list[Row]|None = Field(default=None,min_length=1,max_length=100000)
    indices: list[Annotated[int,Field(strict=True,ge=0,le=4000000)]]|None = Field(default=None,min_length=1,max_length=100000)
    offset: int = Field(default=0,strict=True,ge=0,le=4000000)
    @model_validator(mode='after')
    def selection(self):
        if (self.value is None)==(self.values is None):raise ValueError('Supply one uniform value or explicit values')
        if self.indices is not None and (len(set(self.indices))!=len(self.indices) or self.offset):raise ValueError('Choose distinct indices or a contiguous offset')
        if self.values is not None and self.indices is not None and len(self.values)!=len(self.indices):raise ValueError('Values and indices must have equal lengths')
        if self.value is not None and self.offset:raise ValueError('Uniform assignment uses all elements or explicit indices')
        return self

class Ramp(Edit):
    axis: Literal['X','Y','Z'] = 'Z'
    input_min: Number|None = None
    input_max: Number|None = None
    output_min: Number = 0.
    output_max: Number = 1.
    clamp: bool = True
    @model_validator(mode='after')
    def bounds(self):
        if (self.input_min is None)!=(self.input_max is None) or self.input_min is not None and self.input_max<=self.input_min:raise ValueError('Supply an increasing input interval or omit both bounds')
        values.row('FLOAT',self.output_min);values.row('FLOAT',self.output_max);return self

COMMANDS={
 'inspect_mesh_attributes':(Inspect,(),'Inspect bounded numeric mesh attribute schemas/guards and page supported field rows. Choose base or read-only evaluated mesh data. Unrealized instance fields require realization in Geometry Nodes for mesh readback.'),
 'create_mesh_attribute':(Create,('allow_scene_edit',),'Guardedly create a custom POINT/EDGE/FACE/CORNER FLOAT, INT32, BOOLEAN, vector3 or linear RGBA field with a uniform value. Protect topology/UV/internal fields, isolate shared meshes explicitly, preserve skin/shape IDs on single-user data and roll back cooperative failures.'),
 'set_mesh_attribute_values':(Update,('allow_scene_edit',),'Guardedly fill a custom numeric field, patch distinct indices or write a bounded contiguous value range. Use base-data guards; preserve unrelated fields and UV/color selectors.'),
 'ramp_mesh_attribute':(Ramp,('allow_scene_edit',),'Fill an existing custom FLOAT field from a local-coordinate axis ramp: vertices, edge midpoints, face centers or corner vertex positions. Explicit/automatic input range, output bounds and optional clamp; no world/unit conversion.'),
 'remove_mesh_attribute':(Edit,('allow_scene_edit',),'Guardedly remove one custom numeric field. Protect internal/UV/color storage outside the supported profile and preserve unrelated values; shared data needs explicit isolation.'),
}

class Binding(Model):
    attribute: Name
    semantic: Name

class ExportPlan(Model):
    name: Name
    fields: list[Binding] = Field(min_length=1,max_length=16)
    max_corners: int = Field(default=250000,strict=True,ge=1,le=1000000)
    @model_validator(mode='after')
    def unique_fields(self):
        if len({f.attribute for f in self.fields})!=len(self.fields) or len({f.semantic for f in self.fields})!=len(self.fields):raise ValueError('Attribute sources and semantic names must be distinct')
        return self

class ExportBundle(ExportPlan):
    expected_export: Digest
    directory: str = Field(min_length=1)
    max_bytes: int = Field(default=256*1024**2,strict=True,ge=1024,le=512*1024**2)

class ValidateBundle(Model):
    directory: str = Field(min_length=1)

COMMANDS.update({
 'inspect_attribute_export':(ExportPlan,(),'Plan static base-mesh numeric field export with explicit semantic mapping, raw float32 scalar lanes and corner witnesses that preserve UV channels. Return a source/unit/placement-bound guard. EDGE fields and unrealized instances need explicit conversion.'),
 'export_attribute_bundle':(ExportBundle,('allow_library_write',),'Export a guarded static numeric-field GLB and versioned mapping/witness manifest into a new directory. Independently decode custom fields, local positions, oriented triangles and all UV channels before publication; preserve editable source. No engine shader qualification.'),
 'validate_attribute_bundle':(ValidateBundle,(),'Revalidate the encoded numeric-field GLB against its saved source witness and file hash. Checks file correspondence, not trusted provenance or engine behavior.'),
})
