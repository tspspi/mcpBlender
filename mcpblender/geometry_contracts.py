"""Bounded Geometry Nodes authoring without scripts, arbitrary RNA or dependencies."""
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, StrictBool, StrictInt, model_validator

from .config import Model

Name = Annotated[str, Field(min_length=1, max_length=63)]
Socket = Annotated[int, Field(strict=True, ge=0)] | Name
Value = StrictBool | StrictInt | FiniteFloat | Annotated[list[FiniteFloat], Field(min_length=3, max_length=4)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
NODE_TYPES = (
    "NodeGroupInput", "NodeGroupOutput", "GeometryNodeMeshCube", "GeometryNodeMeshGrid",
    "GeometryNodeMeshLine", "GeometryNodeMeshCylinder", "GeometryNodeMeshCone",
    "GeometryNodeTransform", "GeometryNodeSetPosition", "GeometryNodeInputPosition",
    "GeometryNodeJoinGeometry", "GeometryNodeDistributePointsOnFaces",
    "GeometryNodeInstanceOnPoints", "GeometryNodeRealizeInstances",
    "GeometryNodeSubdivisionSurface", "GeometryNodeSetMaterial", "GeometryNodeStoreNamedAttribute",
    "GeometryNodeInputIndex", "FunctionNodeCompare", "GeometryNodeSeparateGeometry",
    "GeometryNodeInputNamedAttribute",
    "ShaderNodeMath", "ShaderNodeVectorMath", "ShaderNodeCombineXYZ",
)


class InputValue(Model):
    socket: Socket
    value: Value


class InterfaceInput(Model):
    name: Name
    type: Literal["FLOAT", "INT", "BOOLEAN", "VECTOR"]
    default: Value
    minimum: FiniteFloat | None = None
    maximum: FiniteFloat | None = None

    @model_validator(mode="after")
    def valid_limits(self):
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum exceeds maximum")
        if self.type == "BOOLEAN" and (self.minimum is not None or self.maximum is not None):
            raise ValueError("Boolean inputs do not accept numeric limits")
        return self


class Properties(Model):
    operation: Name | None = None
    mode: Name | None = None
    count_mode: Name | None = None
    distribute_method: Literal["RANDOM", "POISSON"] | None = None
    fill_type: Literal["NONE", "NGON", "TRIANGLE_FAN"] | None = None
    data_type: Literal["FLOAT", "INT", "BOOLEAN", "FLOAT_VECTOR", "FLOAT2", "FLOAT_COLOR"] | None = None
    domain: Literal["POINT", "EDGE", "FACE", "CORNER", "INSTANCE"] | None = None


class GeometryNode(Model):
    name: Name
    type: Literal[NODE_TYPES]
    properties: Properties = Field(default_factory=Properties)
    inputs: list[InputValue] = Field(default_factory=list, max_length=32)
    material: Name | None = None
    attribute: Name | None = None

    @model_validator(mode="after")
    def material_node(self):
        if self.material and self.type != "GeometryNodeSetMaterial":
            raise ValueError("material requires GeometryNodeSetMaterial")
        if self.attribute and self.type not in {"GeometryNodeStoreNamedAttribute","GeometryNodeInputNamedAttribute"}:
            raise ValueError("attribute requires a named-attribute reader/store node")
        return self


class GeometryLink(Model):
    from_node: Name
    from_socket: Socket
    to_node: Name
    to_socket: Socket


class Group(Model):
    group: Name


class GeometryGraph(Group):
    inputs: list[InterfaceInput] = Field(default_factory=list, max_length=32)
    nodes: list[GeometryNode] = Field(min_length=1, max_length=128)
    links: list[GeometryLink] = Field(default_factory=list, max_length=256)
    replace: bool = False
    expected_graph: Digest | None = None

    @model_validator(mode="after")
    def unique_names(self):
        if len({n.name for n in self.nodes}) != len(self.nodes):
            raise ValueError("Geometry node names must be unique")
        names = [item.name for item in self.inputs]
        if "Geometry" in names or len(set(names)) != len(names):
            raise ValueError("Interface input names must be unique; Geometry is reserved")
        if self.replace and not self.expected_graph:
            raise ValueError("Replacement requires expected_graph from inspection")
        return self


class GeometryCatalog(Model):
    node_type: Literal[NODE_TYPES] | None = None


class GeometryModifier(Group):
    name: Name
    modifier: Name = "GeometryNodes"


class GeometryValues(Model):
    name: Name
    modifier: Name = "GeometryNodes"
    expected_graph: Digest
    values: list[InputValue] = Field(min_length=1, max_length=32)


class BuildingPreset(Model):
    type: Literal["BUILDING"]
    floors: int = Field(default=2, strict=True, ge=1, le=32)
    width: FiniteFloat = Field(default=6, ge=1, le=200)
    depth: FiniteFloat = Field(default=4, ge=1, le=200)
    floor_height: FiniteFloat = Field(default=3, ge=1, le=10)
    columns: int = Field(default=3, strict=True, ge=1, le=16)
    wall_material: Name | None = None
    window_material: Name | None = None
    roof_material: Name | None = None


class TreePreset(Model):
    type: Literal["VEGETATION"]
    height: FiniteFloat = Field(default=3, ge=.5, le=30)
    crown_radius: FiniteFloat = Field(default=.8, ge=.1, le=10)
    trunk_radius: FiniteFloat = Field(default=.12, ge=.02, le=2)
    segments: int = Field(default=8, strict=True, ge=3, le=32)
    trunk_material: Name | None = None
    leaf_material: Name | None = None


class ScatterPreset(TreePreset):
    type: Literal["SCATTER_VEGETATION"]
    density: FiniteFloat = Field(default=.2, ge=0, le=50)
    seed: int = Field(default=0, strict=True, ge=0, le=1_000_000)
    spacing: FiniteFloat = Field(default=1.5, ge=.1, le=20)
    max_points: int = Field(default=500, strict=True, ge=1, le=2000)


class RefinePreset(Model):
    type: Literal["REFINE_MESH"]
    levels: int = Field(default=1, strict=True, ge=0, le=3)
    material: Name | None = None


class GeometryPreset(Group):
    settings: Annotated[BuildingPreset | TreePreset | ScatterPreset | RefinePreset, Field(discriminator="type")]
    replace: bool = False
    expected_graph: Digest | None = None

    @model_validator(mode="after")
    def replacement_guard(self):
        if self.replace and not self.expected_graph:
            raise ValueError("Replacement requires expected_graph from inspection")
        return self


EDIT = ("allow_scene_edit",)
COMMANDS = {
    "geometry_node_catalog": (GeometryCatalog, (), "Discover supported Geometry Nodes and installed sockets/properties. No arbitrary scripts, groups or object references."),
    "inspect_geometry_graph": (Group, (), "Inspect a Geometry Nodes group, interface identifiers, users, links and graph fingerprint. Imported groups are read-only."),
    "configure_geometry_graph": (GeometryGraph, EDIT, "Create a typed Geometry Nodes group with Geometry input/output and optional typed inputs. Replace only unused managed groups with expected_graph; preflight preserves the original on failure."),
    "attach_geometry_nodes": (GeometryModifier, EDIT, "Attach a managed Geometry Nodes group to a local mesh modifier. Existing modifier must already reference the same group; no implicit replacement."),
    "configure_geometry_inputs": (GeometryValues, EDIT, "Set typed modifier interface values, guarded by expected_graph. Does not change defaults or other users. Use interface identifiers or unambiguous names."),
    "create_geometry_preset": (GeometryPreset, EDIT, "Create a reusable BUILDING, VEGETATION, SCATTER_VEGETATION or REFINE_MESH node group with bounded typed inputs. Attach separately; materials must exist. Replacements require an unused managed group and expected_graph."),
}
