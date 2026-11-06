"""Explicit approximate directional depth assets from immutable native captures."""
from typing import Literal
from pydantic import Field,FiniteFloat,model_validator
from .config import Model
from .card_views import View
from .depth_shadow import MASK_ROLES
from .mesh_contracts import Name,Digest

class Settings(Model):
    geometry_mode: Literal['FLAT','ADAPTIVE_NORMAL','ADAPTIVE_DEPTH_NORMAL','MOMENT_FACETS'] = 'FLAT'
    plane_normal_source: Literal['SHADING_PASS','GEOMETRIC_AOV'] = Field(default='SHADING_PASS',description='Adaptive plane fitting only. GEOMETRIC_AOV requires a capture with geometric_normals=true; shader maps always retain the original native Normal pass.')
    depth_tolerance_m: FiniteFloat|None = Field(default=None,ge=1e-6,le=1000,strict=True,description='Required only for ADAPTIVE_DEPTH_NORMAL. Explicit physical tolerance for measured centre depths; budgets can leave reported residuals above tolerance.')
    normal_tolerance_degrees: FiniteFloat = Field(default=15.0,ge=.1,le=90,strict=True)
    max_slope: FiniteFloat = Field(default=16.0,ge=.01,le=64,strict=True)
    max_refinement_work: int = Field(default=8000000,strict=True,ge=1,le=16000000)
    max_moment_candidates: int = Field(default=32,strict=True,ge=1,le=64)
    output_resolution: int|None = Field(default=None,strict=True,ge=1,le=1024,description='Declared matched square output frame. Capture/output ratio must be a power of two through 64. When set, tile_pixels is measured in output pixels; renderer setup remains explicit.')
    tile_pixels: int = Field(default=4,strict=True,ge=1,le=64,description='Base grid in output pixels when output_resolution is set, otherwise capture-data pixels. Effective capture tile must remain at most 64 pixels.')
    alpha_threshold: FiniteFloat = Field(default=.001,gt=0,lt=1)
    edge_depth_policy: Literal['NEAREST','OMIT','REFUSE'] = 'NEAREST'
    edge_radius_pixels: int = Field(default=16,strict=True,ge=0,le=64,description='Capture-data pixels, independent of output_resolution.')
    max_triangles: int = Field(default=32768,strict=True,ge=2,le=131072)
    max_pixels: int = Field(default=1048576,strict=True,ge=1024,le=1048576)
    max_texture_bytes: int = Field(default=256*1024**2,strict=True,ge=1024,le=512*1024**2)
    max_search_work: int = Field(default=2000000,strict=True,ge=1,le=8000000)

    @model_validator(mode='after')
    def tile_size(self):
        if self.tile_pixels not in (1,2,4,8,16,32,64):raise ValueError('Tile size must be a power of two')
        if self.geometry_mode=='ADAPTIVE_DEPTH_NORMAL' and self.depth_tolerance_m is None:raise ValueError('ADAPTIVE_DEPTH_NORMAL requires explicit depth_tolerance_m')
        if self.geometry_mode!='ADAPTIVE_DEPTH_NORMAL' and self.depth_tolerance_m is not None:raise ValueError('depth_tolerance_m requires ADAPTIVE_DEPTH_NORMAL')
        if self.plane_normal_source=='GEOMETRIC_AOV' and self.geometry_mode not in {'ADAPTIVE_NORMAL','ADAPTIVE_DEPTH_NORMAL'}:raise ValueError('GEOMETRIC_AOV requires adaptive geometry')
        return self

RenderRole=Literal['ALL_RAYS','CAMERA_ONLY','SECONDARY','SHADOW_ONLY','DIFFUSE_SHADOW']

class ShadowMask(Model):
    receiver_view: View
    minimum_span_m: FiniteFloat = Field(default=0.,strict=True,ge=0,le=1e6,description='Retain only valid paired first-hit spans strictly greater than this world-unit distance. Unknown depth is excluded; positive span does not prove distinct surfaces.')

class Source(Model):
    directory: str
    view: View
    component_filter: Literal['ALL','LEAVES','STRUCTURE'] = Field(default='ALL',description='Select first-hit coverage using captured component_ids. LEAVES/STRUCTURE require valid one-sample opaque identity; native geometry is never edited.')
    projected_coverage_directory: str|None = Field(default=None,min_length=1,description='Optional immutable projected-coverage bundle for this exact capture/view. Requires component_filter=LEAVES. Multiply only base-map coverage; preserve geometry and all captured PBR witnesses.')
    render_role: RenderRole = 'ALL_RAYS'
    settings: Settings = Field(default_factory=Settings)
    shadow_mask: ShadowMask|None = None

    @model_validator(mode='after')
    def mask_role(self):
        if self.projected_coverage_directory is not None and self.component_filter!='LEAVES':raise ValueError('Projected coverage requires component_filter=LEAVES')
        if self.shadow_mask and (self.render_role not in MASK_ROLES or self.shadow_mask.receiver_view==self.view):raise ValueError('Paired shadow mask requires SHADOW_ONLY, DIFFUSE_SHADOW or SECONDARY and a different receiver view')
        return self

class Create(Source):
    collection: Name
    expected_plan: Digest
    accept_approximate_optics: bool = False

class Asset(Model):
    collection: Name

class Remove(Asset):
    expected_asset: Digest

class Layer(Model):
    view: View
    component_filter: Literal['ALL','LEAVES','STRUCTURE'] = Field(default='ALL',description='Select first-hit coverage using captured component_ids. LEAVES/STRUCTURE require valid one-sample opaque identity; native geometry is never edited.')
    projected_coverage_directory: str|None = Field(default=None,min_length=1,description='Optional immutable projected-coverage bundle for this exact capture/view. Requires component_filter=LEAVES. Multiply only base-map coverage; preserve geometry and all captured PBR witnesses.')
    render_role: RenderRole = 'ALL_RAYS'
    settings: Settings = Field(default_factory=Settings)
    shadow_mask: ShadowMask|None = None

    @model_validator(mode='after')
    def mask_role(self):
        if self.projected_coverage_directory is not None and self.component_filter!='LEAVES':raise ValueError('Projected coverage requires component_filter=LEAVES')
        if self.shadow_mask and (self.render_role not in MASK_ROLES or self.shadow_mask.receiver_view==self.view):raise ValueError('Paired shadow mask requires SHADOW_ONLY, DIFFUSE_SHADOW or SECONDARY and a different receiver view')
        return self

class LayerLimits(Model):
    max_total_pixels: int = Field(default=4194304,strict=True,ge=1024,le=10485760)
    max_total_texture_bytes: int = Field(default=256*1024**2,strict=True,ge=1024,le=512*1024**2)
    max_total_triangles: int = Field(default=262144,strict=True,ge=2,le=1310720)

class LayersSource(Model):
    directory: str
    prefix: Name
    layers: list[Layer] = Field(min_length=1,max_length=10)
    limits: LayerLimits = Field(default_factory=LayerLimits)
    @model_validator(mode='after')
    def unique_names(self):
        if len({v.view for v in self.layers})!=len(self.layers):raise ValueError('Depth layers require distinct views')
        if '\0' in self.prefix or any(len((self.prefix+'-'+v.view).encode('utf-8'))>63 for v in self.layers):raise ValueError('Generated collection names must fit 63 UTF-8 bytes without NUL')
        return self

class LayersCreate(LayersSource):
    expected_plan: Digest
    accept_approximate_optics: bool = False

COMMANDS={
 'inspect_botanical_depth_layers':(LayersSource,(),'Plan up to ten independent directional depth layers from one immutable capture. Per-view geometry settings and Cycles render roles; aggregate pixel/texture/triangle budgets, target-name preflight, per-layer source guards and one batch plan guard. No allocation, optical equivalence, automatic angular blending or wind qualification.'),
 'create_botanical_depth_layers':(LayersCreate,('allow_scene_edit',),'Create a guarded batch of independently owned hidden depth assets, with layer progress and aggregate checkpoint/storage estimate. Preflight all target names and budgets; roll back newly created layers on cooperative failure/cancellation. Requires accept_approximate_optics=true. Return compact individual inspection/removal guards; each layer remains independently editable through its supported controls. No automatic view selection or optical certification.'),
 'inspect_botanical_depth_source':(Source,(),'Plan one directional depth-patch asset from an immutable native capture with material_fields=true. Optional component_filter=LEAVES or STRUCTURE requires captured component_ids, validates one-sample opaque identity and selects geometry/coverage while preserving captured shader inputs. ALL preserves legacy plans. Filtering does not remove native source geometry or certify a complete partition. Optional output_resolution declares a matched square output grid: tile_pixels is then measured in output pixels and converted to capture pixels; source/output ratios must be powers of two through64 and effective tiles <=64 capture pixels. Capture/texture/work budgets remain at source density. Renderer setup is explicit; extra density does not certify image quality. Bounded geometry/search/pixels/textures; report measured versus estimated edge tiles, source-root units, six packed float data maps and source/file/geometry/map guards. Optional shadow_mask={receiver_view,minimum_span_m} requires a camera-excluded render_role (SHADOW_ONLY, DIFFUSE_SHADOW or SECONDARY) and opposed, equal-span, aligned views in the same capture. Mask layer coverage using valid paired first-hit spans; unknown depth is excluded and counted. This is receiver-dependent span selection, not surface identity or guaranteed duplicate removal. Both decoded view grids count toward batch pixel budgets. Pin a Cycles render_role and its ray flags in the creation plan. Optional bounded normal-aligned adaptive geometry reports residual error, slope/bounds limits and budget stops; flat geometry remains the default. ADAPTIVE_DEPTH_NORMAL requires explicit depth_tolerance_m and jointly refines normal and measured centre-depth residuals under the same hard work/triangle caps. Report actual float32 source-frame triangle depth errors, unknown samples, remaining tolerance and budget stops; no target tolerance or physical surface equivalence is guaranteed. MOMENT_FACETS requires captured normal_moments and fits witness-anchored projected-area normals, with implicit geometric shading; bounded omission/precision checks and max_refinement_work apply. Necessary unit-normal direction-cap preflight reports a ruled-out configured cap and higher canonical caps not ruled out, without auto-adjustment; diagnostics and storage persist in failed-operation progress. max_slope defaults16 and allows explicit .01..64; depth/precision/triangle/work limits remain mandatory. Bounded deterministic alternative factorizations (max_moment_candidates default32, hard64) check hemisphere, clipping and final float32 geometry under the aggregate work cap. Exhaustion refuses without fallback and is not an impossibility proof. Optional plane_normal_source=GEOMETRIC_AOV requires captured geometric_normals and applies only to ADAPTIVE_NORMAL or ADAPTIVE_DEPTH_NORMAL. Slopes/angular residuals use geometric-normal means with pinned provenance; original native shading normals and six maps remain unchanged. SHADING_PASS remains the default with legacy plans unchanged. No beauty-RGB material substitution. Requires Blender only for target scene units. This is a directional approximation, not qualified optical equivalence or complete far workflow.'),
 'create_botanical_depth_asset':(Create,('allow_scene_edit',),'Create guarded independent hidden directional depth patches with private packed native-input textures, Principled plus artistic thin backlighting and separate coverage. Requires accept_approximate_optics=true. Preserve source/native scene resources. Intrinsic shader alpha must be opaque. Six float maps retain raw root-local normals and all input witnesses. MOMENT_FACETS retains those normals as witnesses and uses implicit geometric normals, pinning material bump correction in its guard; significant unsupported reconstructed directions refuse. Apply the planned render_role on creation; collection remains hidden. Camera exclusion does not guarantee exact rendered alpha preservation. No closed geometry, view blending, shadows/wind or native optical-equivalence guarantee.'),
 'inspect_botanical_depth_asset':(Asset,(),'Inspect owned packed directional depth asset after save/reopen without source files. Return content/placement/user guard and blockers for removal. Display visibility and uniform positive root placement can change. Report creation render_role and actual ray_visibility; ray-flag edits invalidate owned content until restored. No optical certification.'),
 'remove_botanical_depth_asset':(Remove,('allow_scene_edit',),'Remove an unchanged guarded owned depth asset and private packed data. Refuse foreign content/users or stale guard; preserve capture archive and original scene assets.'),
}
