---
name: blender-mcp-render
description: Set up and review Blender materials, lighting, cameras and still renders through mcpBlender. Use for visual look development and rendered image delivery; use blender-mcp-design for dedicated modeling and game asset export.
---

Start with `bridge_status` and `get_scene_info` to identify the session, scene,
camera and current policy. If a new Blender session is needed and startup is in
scope, use `start_blender`. GUI mode supports viewport images; background mode
supports camera renders. Preserve an existing project's objects and settings unless
the task calls for changing them.

Prefer `inspect_resources`, `configure_material`, `assign_material`,
`configure_light`, `configure_camera` and `configure_render` for supported setup.
These take a typed `params` object and work with Python execution disabled.
For reusable surfaces, prefer `apply_material_preset` with PBR, TEXTURED_PBR,
GLASS or EMISSION. PBR accepts base_color_texture, roughness_texture,
metallic_texture and normal_texture; data maps use Non-Color, base color sRGB,
and packing defaults true. Roughness/metallic maps use their red channel. Assign
the material with assign_material. Existing materials require replace=true.

For custom supported graphs, discover socket identifiers/indexes and property
choices with shader_node_catalog, then inspect_shader_graph. configure_shader_graph
creates/replaces a graph; configure_shader_node, connect_shader_nodes,
disconnect_shader_input and remove_shader_node support incremental edits. Input
defaults cannot override a linked input until it is disconnected. Existing links
need replace_existing=true to replace. Graph edits preflight on a temporary copy;
rare application failures can still leave partial edits. Script nodes, arbitrary
RNA, linked materials and animated shader graphs are excluded. Procedural shaders
and glass need target-engine review/baking; the textured PBR export is qualified.
Use `inspect_texture_bake` then guarded `bake_textures` for normal, opaque-geometry
AO and supported direct-Principled shader-property maps. Sources need packed,
saved input images and a clean low-target UV tile. Optional `inspect_texture_quality` checks minimum directional
texels per physical metre, chart pixel-centre coverage and continuous chart/edge
padding at declared base/mip sizes. A shared `quality` policy on inspection and
baking enforces complete/pass and records the report; use matching dimensions
and margin no larger than policy padding_pixels. Incomplete budgets cannot pass.
It does not test actual mip kernels, colors, dilation or optical appearance.
If chart coverage or mip gaps fail, NEW vegetation preparation can opt into
chart_layout with pixel-area/mean-span floors and per-side gutters at declared
texture dimensions. Generic pack_uv_islands supports the same staged layout.
allow_stretch=true must be explicit; it changes target UV anisotropy while source
sampling maps stay pinned. Reinspect physical density/coverage/padding afterward,
then bake and review actual colors/normal transfer and filtering separately.
Quality-gated vegetation self-bakes also retain the source witness needed for
adoption. Their reports travel with packed maps and semantic exports. Use
inspect_vegetation_delivery(require_quality=true) to flag missing reports or
changed scene units, then inspect each recorded policy; mip_levels=0 certifies
only the declared base footprint. This does not repeat sampling or render review.
Calculate whole-profile input budgets before all-role adoption: eleven roles
with seven 1024x1024 maps need 308 MiB base RGBA8 and about 410.67 MiB for full
hypothetical mip chains, exceeding default delivery budgets. Declare appropriate
limits, then require every role's retained quality report. Render close detail
and multiple LODs afterward; the sparse scaffold qualification is not a mature
canopy or deep-mip appearance certificate. Self-bake AO excludes other scene
components and does not establish whole-canopy occlusion.
The isolated worker preserves
the editing scene, producing PNGs plus a static current-frame PBR asset. Check
`projection.fraction`, map statistics and an actual render; a completed job is
not visual qualification. Masks detect geometry projection misses at the output
resolution. Tangent normals use positive Y; data maps are Non-Color, color maps
sRGB. Output is 8-bit PNG, not HDR or arbitrary shader-lobe equivalence. Alpha is
separate and AO does not account for cutouts. The output PBR material carries
glTF AO metadata. Reopen its asset and call `validate_texture_bake` before export.

For shared material delivery, inspect_texture_atlas accepts successful original
bake directories with distinct IDs. Build with the same options/expected_atlas,
explicit dimensions, gutters and full-mip RGBA8 budget. Maps must match across
entries; native single-UV/static/PBR binding is rechecked in the isolated worker.
Tiles keep resolution and tangent orientation; base-level edge gutters do not
prove mip/anisotropic bleed behavior. Reopen/validate every atlas mesh before
export and inspect the atlas maps. Sources retain their own editable bundles;
native thin-leaf conversion losses remain recorded in the atlas provenance.

Poll the tracked operation/storage fields during baking. Cancel stops its owned
child; broker restart preserves it. After parent death, `inspect_texture_job` and
`recover_texture_job` reconcile without replay once recorded processes are gone.
`cleanup_texture_job` defaults to inspection and protects successful/referenced
outputs; removing interrupted partials needs explicit inclusion. Snapshot saving
in the editing instance remains blocking. Never replay an uncertain bake solely
because a call timed out.

For a standard persistent preview stage, discover and plan `preview_setup`, then
run it with `inputs` containing mesh `objects` and a fresh `prefix`. It fits an
active camera and creates key/fill/rim area lights around evaluated bounds, leaving
existing lights and render settings intact. Check the step result's camera fit
and view the render. `run_action` arguments are direct action/inputs/wait/request_id;
wait=true returns a full operation record whose state must be checked even when
the MCP call succeeds. Failed/cancelled actions can have partial edits/files.
Set the render aspect before `frame_objects`, which fits an existing camera
(`name`) to named meshes (`objects`) using a view preset or world direction.
Check `fully_in_frame`, then judge the rendered image. Fit covers the current
frame only; refit after aspect or pose changes. Orthographic setup uses
`configure_camera` with `projection="ORTHO"`.

For compositing, start with `inspect_render_pipeline` and
`compositor_node_catalog`. Blender 5 uses a managed Image-output group; build it
with `configure_compositor_graph`, then bind it using `configure_compositing`
with fresh settings and graph guards. `CompositorNodeRLayers` binds the current
scene and selected view layer; sharing a graph preserves that source binding.
Use installed socket identifiers/menu choices rather than legacy properties:
glare Type can be `Fog Glow`, and blur Size is a two-component vector. Exactly
one `NodeGroupOutput` must receive Image. File-output/nested/external-image nodes
are excluded. To revise the whole graph, inspect it and supply replace=true plus
expected_graph; multiple local scene users require allow_shared=true. Imported,
animated or nested-user graphs are not replaced. Staged replacement rolls back
cooperative failures before its final native deletion; crash rollback is unqualified.

Use guarded `configure_render_passes` for depth, normals, component passes and
Cycles denoising_data, then inspect Render Layers output availability. Disabling
a consumed pass refuses and restores flags. `configure_color_management` exposes
installed display/view/look, exposure/gamma and white balance; keyed/driven target
settings refuse. settings_sha256 covers pipeline settings, not geometry or custom
color curves. Pass flags do not deliver EXR files or certify engine support.
Render a small preview and inspect actual pixels after changing the pipeline.

Use `execute_code`, when permitted, for unsupported nodes/groups or settings not
yet exposed by structured tools. `bpy` is available; assign structured output
to `result`, and check `success` and traceback. Namespace variables do not persist
across calls; scene data does. Native Blender output may be in the Blender log.

Begin with a small preview and suitable sample count, then inspect the actual
image before committing time to a larger render. `capture_viewport` produces a
GUI viewport artifact. `render_still` submits a camera-render job; poll `get_job`
until it succeeds or fails, then call `get_image` with the completed result's
`artifact_id`. Render dimensions are limited to 16–4096 pixels per axis. The
structured render tool restores temporary resolution, output path, engine, format
and active camera after completion; intentional lasting look changes belong in
the scene setup.

For motion previews, `animation_preview` renders PNGs and optional H.264 through a
temporary VSE scene. It can choose temporary skeletal/morph clips and restores live
animation/frame/render state. View the returned step result's preview_artifacts;
inspect partial_output after failure/cancellation. The camera fit covers one frame,
so allow enough room for the entire motion. Native video encoding is blocking.

Judge framing, silhouette, lighting, surface readability, clipping and the user's
requested style from the retrieved image. Adjust and render again when needed.
Successful file creation or a completed job alone does not prove visual quality.
Use the intended production renderer for final fidelity; a workbench preview does
not validate material shading. Do not infer GPU support from installed Blender;
inspect capabilities or use a bounded CPU test when the hardware is unknown.

Rendering can occupy Blender's main thread and make the GUI busy. The separate
broker keeps `get_operation`, `get_job` and storage reports available. Operation
and artifact identifiers survive frontend restart. Frame sequences report completed
frames; native still renders may not have finer progress. A timeout does not stop
the render. Use a stable request ID and recover the existing operation before
resubmitting. Remote token URLs expire after ten minutes.

Check `storage_status` before long/high-resolution output and watch operation
storage fields during rendering. Estimates identify their assumptions; they do
not guarantee space if other processes consume it. `checkpoint` preserves an
editing milestone before expensive work. Preserve wanted images and the editable
project for delivery. Save paths
are relative to the active `library_root`; arbitrary Python has Blender's full OS
permissions. Report which images were actually viewed and which checks remain.

Automatically generated render paths are temporary: default retention is seven
days with a 2 GiB target and one-hour minimum age. Use explicit output paths for
deliverables or set_operation_retention(operation_id, pinned=true). Structured
use as a material/VSE input pins the output group; pin before external/custom
Python use because those dependencies cannot be inferred. Preview cleanup with
preview_retention_cleanup before applying a plan. details_pruned=true means old
history expired; recover current state instead of replaying its mutation.

For a simpler Cycles shadow caster, inspect `inspect_asset_proxy_source` with
purpose SHADOW, method DECIMATE, PER_LEAF grouping and a triangle budget. Generate
with its source guard and identical settings; review approximation error and
rendered shadows. The output is invisible to camera/diffuse/glossy/transmission/
volume-scatter rays but visible to shadow rays. Source shadow casting remains
unchanged: before proxy generation, inspect `inspect_render_visibility` and use
its guard with `configure_render_visibility` to disable source visible_shadow. These flags do not
transfer through GLB or provide Eevee/engine shadow integration. Alpha foliage
coverage needs visual qualification; a triangle budget alone does not prove it.

For a camera/frame batch that leaves the editor available, use top-level
`render_camera_batch` with fresh pipeline expected_settings, a new directory,
cameras/frame range and PNG or OPEN_EXR_MULTILAYER formats. It requires snapshot,
library-write and application-start permission. Poll/cancel the original durable
operation; no second launch is needed when observation times out. The snapshot
hash binds actual scene content; later edits do not update it. Packed resources
are required, external fluid/volume/cache inputs refuse, and worker script
execution is disabled. Compositing is preserved; VSE and crop borders are disabled.
Two workers per bridge and explicit CPU threads/bytes/timeout bound admission.
Broker restart/editor shutdown preserve a handed-off render. Native snapshot
save/load are still blocking, and watchdog byte limits are not disk quotas.

Use inspect_render_job/validate_render_job without Blender for status and file
proof. After a dead worker, recover_render_job with a fresh job_sha256 reconciles
complete files or records interruption without replay. Inspect the directory after
an uncertain launch/handoff; an interrupted operation does not prove no child ran.
Guarded cleanup defaults dry-run and protects successful/live/referenced/unknown
files. EXR header/channel checks do not certify pixels or every renderer; inspect
a small PNG preview before spending time on a larger batch. Video encoding and
external dependency freezing remain separate workflows.

Managed botanical leaves have separate front/back colors and a thin-surface
translucent mix. Use inspect_foliage_material and configure_foliage_material with
a fresh expected_material guard. Patches affect all users. Double-sidedness is
independent of translucency; colors require opaque alpha. Linked target inputs
refuse default patches. Check both leaf close-ups and tree views, including
backlighting. This artistic native shader is not physical thickness, alpha-card
shading or qualified glTF/runtime equivalence. Wind and atlases remain separate.

For native botanical detail, create_botanical_surface supplies OAK_BARK and
OAK_LEAF recipes. Existing tree materials can use inspect_botanical_surface then
configure_botanical_surface with expected_material and profile/settings. Shared
material identity and original color/normal sources remain; leaf optics stay
independently editable. Inspect detail_valid before rebuilding/removing and
preserve manual shader edits. Bark uses growth-aligned named UVs for
fissures/grain; leaves use blade UVs for paired vein color/bump. Bump is shader
relief, not geometry. Bark can use the ordinary PBR bake pipeline; thin-leaf lobes
require explicit thin_foliage_mode=FRONT_PBR on inspection and baking. Review
material_adapters: native back color/translucency/backface shading are omitted. Do not claim an
atlas, physical vascular model or runtime-equivalent shading from these recipes.

For front-PBR leaf/card delivery, inspect/bake with the same explicit mode and
fresh expected_bake; the default refuses native mixed thin-leaf shaders. Original
optics remain in the editable source. A card needs its own clear unit-tile UVs,
ALPHA map and deliberate silhouette/projection review; empty pixels are not a
projection failure only when explicitly intended. Review converted maps and a
render, validate the reopened asset, and verify exported alpha. Current proof is
sampled Blender/GLB delivery. Verified-bundle static atlases are available;
Godot, multi-view vegetation representations and wind remain separate.

For portable vegetation map preparation, inspect_vegetation_bake_source on a tree
or native LOD profile, optionally choosing asset roles. Use its plan_sha256 as
expected_plan for prepare_vegetation_bake with identical options and a fresh
bake_collection. Poll that operation. Copies preserve source geometry/UVs and pin
shader sampling before adding verified BakeUV. Missing source UVs refuse by
default; BAKE_LAYOUT is an explicit copy-only sampling change, recorded per node.
Review source_sampling_changes before choosing that fallback. Existing UV maps
stay unchanged. Preparation writes no images. For each returned component, pass
its inspect_texture_bake arguments to that inspector, then bake_textures with the
fresh guard, directory, map/texture limits and the returned explicit FRONT_PBR
mode for leaves. Keep its optical omissions. Prepared copies survive source
removal and save/reopen; inspect/remove_vegetation_bake guard owned cleanup and
preserve file bundles. Read USER_MANUAL.md for ownership, UV and sampling limits. For native LOD
adoption, prepare/bake the exact LOD roles and preserve the initial bake guard;
inspect_vegetation_bake_adoption takes lod_collection, bake_collection and entries
of asset/directory. Review optical loss and budgets; accept_front_pbr=true is
required for leaf approximations. Adopt with its expected_plan. Packed owned maps
and prepared UVs then survive preparation/file removal and save/reopen. Original
wind fields/UVs remain intact. Adopted roles require explicit replace_existing=true for replacement. LOD
export automatically carries material/loss/UV witnesses; this is not optical parity.

For revisions on an already textured LOD, prepare with uv_strategy=EXISTING and
its BakeUV to retain the layout and channel count. Private source images/AO groups
are independently copied. After structured edits to prepared private shaders,
inspect_vegetation_bake returns a changed-content guard; refresh_vegetation_bake
accepts supported material/frame edits with that expected_preparation and returns
a new initial bake fingerprint. It refuses frozen geometry/UV/attribute/placement
changes; older preparations need recreation. Refresh updates the bake source,
not the LOD's adopted maps. Keep the original source and re-bake with fresh guards.

For an adopted texture revision, inspect/adopt with replace_existing=true, the
new successful bake directories and the current plan guard. Final profile budgets
exclude retired maps; inspect peak_rgba8_base_bytes separately. Retained original
preparations and refreshed/current-PBR sources are supported when geometry/UVs
match. FRONT_PBR acceptance remains required for inherited losses, even for a
simple PBR rebake. Revisions preserve previous/source/optical lineage and retire
only unused private resources; external references refuse. Keep old source/bake
bundles if restoration is needed; replacement does not archive old pixels. Save
and revalidate export. Repeated PBR rebakes can accumulate filtering loss.

New vegetation bake layouts may isolate/repack a bounded number of folded or
overlapping face charts. Review repaired_uv_faces; max_uv_repairs=0 refuses repair,
default 64, maximum 256. Existing source UVs and explicit EXISTING layouts are
preserved. A clear exact overlap check is not a texel-density, padding/filtering
or visual-quality guarantee. Native packing still has coarse cancellation limits.

Before delivering a textured vegetation profile, inspect_vegetation_delivery
checks every level's wood/shoot mesh and each shared leaf template. Choose the
required maps, min_texture_size and base/full-mipmap RGBA8 budgets explicitly.
Review missing_assets, missing_maps, resolution_gaps, optical_omissions and sampling
changes. complete means only these declared coverage/resolution/input-budget
criteria passed; it does not certify visual quality, padding/filtering, UV2,
physical optics, engine shaders or animated LOD behavior. Export/validate files
separately and review representative renders at the intended quality target.

For scene environment lighting, use environment_catalog and inspect_environment,
then configure_environment with the fresh expected_environment and settings mode
COLOR, SKY or HDRI. SKY AUTO resolves the installed atmospheric model; angles are
in degrees. HDRI takes a static 2:1 library image, bounded encoded/pixel budgets,
optional color_space and rotation_degrees, and packs a private copy for relocation.
Only ordinary scanline RGB(A) EXR is accepted alongside PNG/JPEG/Radiance HDR.
Inspect available storage and decoded-size estimates. Other scenes and unmanaged
or edited Worlds are preserved. Animated/unsupported/linked dependencies refuse.
Scene lights and exposure are independently controlled: inspect existing SUN
lights before adding a sky sun, and use inspect_render_pipeline plus guarded
configure_color_management for exposure. film_transparent controls camera
background without removing illumination. Keep asset guards, check macro leaf
front/back transmission and bark scale, then review the whole asset. Save/reopen
packed inputs. These controls do not establish physical optics or engine parity.
