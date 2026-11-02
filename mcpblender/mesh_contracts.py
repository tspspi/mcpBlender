"""Guarded mesh element workflows, without arbitrary operators or properties."""
from typing import Annotated, Literal

from pydantic import Field, FiniteFloat, model_validator

from .config import Model

Name = Annotated[str, Field(min_length=1, max_length=255)]
Vec3 = Annotated[list[FiniteFloat], Field(min_length=3, max_length=3)]


class Named(Model):
    name: Name


Index = Annotated[int, Field(strict=True, ge=0)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Indices = Annotated[list[Index], Field(min_length=1, max_length=100_000)]
Domain = Literal["VERTEX", "EDGE", "FACE"]


class Elements(Model):
    indices: Indices | None = None
    selection: Name | None = None

    @model_validator(mode="after")
    def explicit_target(self):
        if (self.indices is None) == (self.selection is None):
            raise ValueError("Specify exactly one of indices or a named selection")
        if self.indices is not None and len(set(self.indices)) != len(self.indices):
            raise ValueError("Element indices must be unique")
        return self


class InspectElements(Named):
    domain: Domain = "FACE"
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=128, ge=1, le=512)


class MeshEdit(Named):
    expected_topology: Digest
    expected_geometry: Digest | None = None
    make_single_user: bool = False


class SelectElements(MeshEdit):
    domain: Domain
    elements: Elements
    selection_name: Name | None = None
    replace: bool = False


class RemoveSelection(Named):
    selection_name: Name


class ExtrudeFaces(MeshEdit):
    faces: Elements
    offset: Vec3

    @model_validator(mode="after")
    def nonzero_offset(self):
        if sum(v * v for v in self.offset) <= 1e-24:
            raise ValueError("Extrusion needs a nonzero offset")
        return self


class InsetFaces(MeshEdit):
    faces: Elements
    thickness: FiniteFloat = Field(gt=0)
    individual: bool = False


class LoopCut(MeshEdit):
    edge: Index
    cuts: int = Field(default=1, ge=1, le=32)


class MergeVertices(MeshEdit):
    vertices: Elements
    position: Literal["CENTER", "FIRST", "LAST"] = "CENTER"


class CleanupMesh(MeshEdit):
    merge_distance: FiniteFloat = Field(default=1e-6, ge=0)
    dissolve_distance: FiniteFloat = Field(default=1e-8, ge=0)
    remove_loose: bool = True
    recalculate_normals: bool = True


class RepairNormals(MeshEdit):
    faces: Elements | None = None
    direction: Literal["OUTSIDE", "INSIDE", "FLIP"] = "OUTSIDE"


EDIT = ("allow_scene_edit",)
COMMANDS = {
    "inspect_mesh_elements": (InspectElements, (), "Page base mesh vertices, edges or faces and named selections. Returns topology and local-geometry fingerprints for guarded indexed edits; modifier results are not editable indices."),
    "select_mesh_elements": (SelectElements, EDIT, "Select explicit base-mesh elements and optionally store a named selection. Requires current topology; named selections become stale after topology changes."),
    "remove_mesh_selection": (RemoveSelection, EDIT, "Remove a named mesh-element selection from this object without editing geometry or other selections."),
    "extrude_mesh_faces": (ExtrudeFaces, EDIT, "Extrude selected base-mesh faces as a region by an object-local offset. Validates fingerprints and edits a temporary mesh before assignment."),
    "inset_mesh_faces": (InsetFaces, EDIT, "Inset selected base-mesh faces as a region or individually, using object-local thickness."),
    "loop_cut_mesh": (LoopCut, EDIT, "Insert evenly spaced cuts through the quad face ring crossing a base-mesh seed edge. Rejects non-quad ring faces before editing."),
    "merge_mesh_vertices": (MergeVertices, EDIT, "Weld selected base vertices at their center, first or last input position, preserving other vertices."),
    "cleanup_mesh": (CleanupMesh, EDIT, "Clean a guarded base mesh: optional distance weld, degenerate-edge dissolution, loose geometry removal and normal recalculation. Distances are object-local; inspect results."),
    "repair_mesh_normals": (RepairNormals, EDIT, "Recalculate selected/all face winding outward/inward, or flip it. Outward orientation is only meaningful for suitable connected surfaces; no custom-normal authoring."),
}
