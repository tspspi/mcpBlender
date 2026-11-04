"""Guarded UV editing and measurable layout inspection."""
from typing import Literal

from pydantic import Field, FiniteFloat, model_validator

from .mesh_contracts import Named, Name, Digest, Elements
from .uv_layout_contracts import ChartLayout


class UVLayout(Named):
    uv_map: Name = "UVMap"
    texture_width: int = Field(default=1024, ge=1, le=32768)
    texture_height: int = Field(default=1024, ge=1, le=32768)
    island_limit: int = Field(default=128, ge=1, le=512)
    overlap_budget: int = Field(default=50000, ge=1, le=200000)


class UVEdit(UVLayout):
    expected_uv: Digest
    make_single_user: bool = False


class UVSeams(UVEdit):
    edges: Elements
    mode: Literal["SET", "ADD", "REMOVE"] = "ADD"


class UVUnwrap(UVEdit):
    method: Literal["ANGLE_BASED", "CONFORMAL", "MINIMUM_STRETCH"] = "ANGLE_BASED"
    margin: FiniteFloat = Field(default=.02, ge=0, le=.25)


class UVPack(UVEdit):
    margin: FiniteFloat = Field(default=.02, ge=0, le=.25)
    rotate: bool = True
    scale: bool = True
    tile_padding_pixels: FiniteFloat = Field(default=0,ge=0,le=4096)
    chart_layout: ChartLayout | None = None

    @model_validator(mode='after')
    def padding(self):
        if 2*self.tile_padding_pixels>=min(self.texture_width,self.texture_height):raise ValueError('Tile padding must leave a positive texture interior')
        if self.chart_layout and not self.scale:raise ValueError('Pixel chart layout requires scale=true; allocation can change UV density')
        if self.chart_layout and self.texture_width*self.texture_height>4*1024**2:raise ValueError('Chart layout texture pixel budget exceeded')
        return self


class UVDensity(UVEdit):
    pixels_per_unit: FiniteFloat = Field(gt=0, le=1000000)


EDIT = ("allow_scene_edit",)
COMMANDS = {
    "inspect_uv_layout": (UVLayout, (), "Inspect base-mesh UV islands, positive-area overlaps and pixels per Blender world unit. Reports overlap completeness and a fingerprint including geometry, transform, seams and this UV map."),
    "activate_uv_map": (UVEdit, EDIT, "Choose an existing named UV map for editing and rendering/export. Requires a current UV fingerprint and explicit isolation of shared meshes."),
    "set_uv_seams": (UVSeams, EDIT, "Set/add/remove seams on indexed or named edges, guarded by inspect_uv_layout's expected_uv. Does not move geometry or UV coordinates."),
    "unwrap_uv_mesh": (UVUnwrap, EDIT, "Unwrap all base-mesh faces using seams on an isolated temporary mesh, then copy only UV coordinates back. Creates the named map if absent."),
    "pack_uv_islands": (UVPack, EDIT, "Pack existing UV islands in the unit tile. Optional tile_padding_pixels reserves a border at texture_width/height. scale=false preserves UV scale and refuses a layout that cannot fit that interior. Operates on a temporary copy; native packing is not interruptible. Optional chart_layout allocates bounded pixel rectangles with area/mean-span floors and per-chart gutters; stretch requires explicit allow_stretch. Reinspect actual density/chart coverage/mip quality after packing."),
    "normalize_uv_density": (UVDensity, EDIT, "Scale each UV island around its center to pixels_per_unit at the supplied texture dimensions. Does not pack; inspect bounds and pack with scale=false afterward."),
}
