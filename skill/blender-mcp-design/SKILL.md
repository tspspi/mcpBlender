---
name: blender-mcp-design
description: Create, inspect and edit Blender models and game assets through mcpBlender, including preparation and GLB export for Godot. Use for live Blender modeling and asset validation; use blender-mcp-render for dedicated lighting and image work.
---

Use the available mcpBlender tools. Tool namespaces depend on the client's server
name. `bridge_status` reports the connected Blender session and current policy.
Use `start_blender` to choose GUI mode when viewport feedback is required. Lazy
startup may also occur on the first Blender operation, according to configuration
and key policy. Do not infer a dead process from a busy or timed-out operation.

Inspect the scene before editing: check objects, names, dimensions, unit scale,
selection, materials and the current project path with `get_scene_info` and
`get_object_info`. These tools expose local transforms and object dimensions;
use `inspect_mesh` for base/evaluated geometry, boundary/non-manifold edges,
world bounds, UV coverage bounds and sampled world vertices at the current frame.
Compare base and evaluated geometry to distinguish stored topology from modifier
results. The geometry digest excludes UVs/materials; the checks do not detect
self-intersection; use `inspect_uv_layout` for a bounded UV-overlap check.

For base-mesh element edits, use `inspect_mesh_elements` and carry its
`topology_sha256` into `expected_topology`; optionally guard coordinates with its
local `geometry_sha256` as `expected_geometry`. Do not substitute the evaluated
mesh's indices or the world-space digest from `inspect_mesh`. Reinspect after
every edit. `select_mesh_elements` can store named vertex/edge/face groups;
topology changes invalidate those groups. Remove obsolete names explicitly with
`remove_mesh_selection`.

Use `extrude_mesh_faces`, `inset_mesh_faces`, `loop_cut_mesh`,
`merge_mesh_vertices`, `cleanup_mesh` and `repair_mesh_normals` for supported
element work. Selection references contain exactly one of `indices` or
`selection`. Distances/offsets are object-local. Loop cuts require a quad ring.
Edits refuse shape-key and armature-deformed meshes; shared data requires explicit
isolation. Inspect winding, UVs, material slots and a render after topology edits.
Boolean modifiers support explicit operand objects and difference/union/intersect;
inspect the evaluated result before applying or exporting, and exclude cutters
from deliverables unless requested. Imported dependency graphs still need review.

For seam-based UV work, inspect `inspect_uv_layout` and carry its `uv_sha256`
as `expected_uv` into each edit. Use `set_uv_seams` with indexed or named EDGE
selections, `unwrap_uv_mesh`, then `pack_uv_islands`. `normalize_uv_density`
uses area-based pixels per Blender world unit at the requested texture width/
height; packing with `scale=false` preserves that density. Reinspect bounds and
`overlap.complete`: a zero count with incomplete checking does not prove a clean
layout. Use `activate_uv_map` to select the named map for rendering/export.
These UV-only tools preserve geometry, shape keys and skinning; shared meshes
still need explicit isolation. Native unwrap/packing cannot cancel mid-call.
For a separate secondary layout on ordinary meshes, inspect the absent named
map (for example UV2), then create_secondary_uv with that expected_uv and actual
texture dimensions. This guarded smart-project/pack action preserves all prior
maps and active/render choices, refuses existing targets or managed owned data,
and reports ordered uv_maps and zero-based Blender uv_channel. It can use the
same chart_layout and tile_padding_pixels controls. Check inspect_texture_quality
on the new map separately; a name or layer index does not certify engine lightmap
use. Decode exported channels with export_attribute_bundle when numeric-field
delivery applies. For owned native vegetation LODs use the dedicated transaction
below. Use create_botanical_secondary_uv for masters; instance lightmap atlases
remain separate workflows.
For an explicit texture-edge border, pack with tile_padding_pixels and matching
texture_width/texture_height. scale=true uniformly shrinks/translates the packed
layout; scale=false only translates and refuses layouts too large for the inset.
Reinspect density and inter-chart/mip gaps afterward; edge padding alone does
not guarantee those. Four base pixels leave two at mip 1. Direct UV edits still
invalidate managed vegetation preparation witnesses and cannot be refreshed as
material-only edits.
For vegetation, request tile_padding_pixels at declared texture_width/height
when planning and creating a NEW bake preparation instead of editing its frozen
UVs afterward. Original source maps stay intact. EXISTING forbids nonzero inset.
Check each resulting component's full geometric quality policy before baking.
For narrow charts or mip-gap failures, optional chart_layout on NEW vegetation
preparation or pack_uv_islands allocates pixel rectangles before freezing UVs.
Declare the actual texture dimensions, min_area_pixels, min_span_pixels and
gutter_pixels (per side at base resolution). Default floors are 64 pixels of
area, two pixels of mean width and four-pixel gutters. Ordinary packing requires
scale=true. Explicit allow_stretch=true permits anisotropic target UV scaling;
otherwise charts retain pixel-space aspect ratios and may refuse to fit. Source
shader UV pins and geometry stay intact. Inspect chart_layout.stretched_charts
and independently require complete/passed quality at intended mip sizes; the
shelf heuristic and mean-width floors do not certify coverage or physical density.
UV area and physical density use local edge differences before global placement,
so distant translation does not collapse the measurements. Placement remains in
their guards. Stored mesh/transform precision and rendering/physics at extreme
offsets remain separate concerns; the inspector does not rebase geometry.
Quality-gated vegetation self-bakes retain source inspection witnesses so
adoption can verify both the original preparation and policy-bearing bake hashes.
Their geometric reports survive packed adoption, source cleanup and semantic
export. inspect_vegetation_delivery(require_quality=true) requires a report for
every component and matching scene units; review quality_policies because each
report covers only its declared thresholds/mip sizes and prepared placement.
It does not rerun sampling or qualify every scaled shared-template instance.
Plan whole-profile budgets explicitly: eleven roles with seven 1024-square maps
need 308 MiB base RGBA8 and about 410.67 MiB for hypothetical full mips. A budget
refusal is a delivery decision; do not silently drop maps or reduce resolution.
Submit long operations asynchronously and keep their operation IDs; an observation
timeout does not prove failure or authorize replay. Save/reopen the packed result
and independently validate export after guarded source cleanup. Review actual
material and LOD renders separately from the declared geometric quality policy.

For high-to-low textures, inspect `inspect_texture_bake` with the low `name`,
high `sources`, target `uv_map` and optional topology-matched `cage`. Carry its
`bake_sha256` as `expected_bake` into `bake_textures` with a new output directory.
Before admission, use `inspect_texture_quality` at the intended dimensions to
check physical minimum directional texels/metre, per-chart pixel-centre coverage
and continuous inter-chart/tile-edge padding at base and requested mip sizes.
Require both complete and passed. To enforce the result, pass the same `quality`
policy to bake inspection and baking; dimensions must match and margin must not
exceed policy padding_pixels. The saved bundle retains the report. Budgets can
make inspection incomplete. These are geometric checks; inspect actual rendered
maps/filtering separately. Existing UV density editing uses Blender units and
area averages, while this inspector accounts for physical metres and stretching.
The default normal/AO/base-color/roughness/metallic maps form a PBR bundle;
alpha and emission-color maps are optional. Check projection coverage and channel
statistics, open `asset.blend`, then `validate_texture_bake` before GLB delivery.
The baked asset is a static current-frame mesh; the original rig/modifiers remain
in the live scene and source snapshot. See `blender-mcp-render` for job/cancellation
and shading limits. Successful bundles are explicit protected deliverables.

For procedural geometry, discover `geometry_node_catalog` and inspect named
groups with `inspect_geometry_graph`. `configure_geometry_graph` builds supported
typed nodes/links with automatic Geometry interface sockets; use typed exposed
inputs for reusable designs. `attach_geometry_nodes` shares a group between local
mesh objects, while `configure_geometry_inputs` changes only the named modifier's
values and requires `expected_graph` from `graph_sha256`. Existing attached groups
cannot be replaced: detach their users explicitly or create a new group. Imported
graphs are read-only. Use GeometryNodeSetMaterial with an existing material to
color generated primitives. Inspect evaluated geometry and view a render after
changing procedural inputs; source mesh topology may remain unchanged. These
tools do not yet expose nested groups or simulation zones.

Prefer `create_geometry_preset` for repeated buildings, pine-style vegetation,
seeded surface scattering or subdivision refinement. Create named materials first,
create the group with typed `settings`, then attach it to a mesh. Presets carry UVs,
material references and persistent limits; inspect those limits before changing
exposed modifier inputs. Building parameters generate a solid exterior with window
panels and a flat roof, without interiors or cut openings. Scatter preserves the
source surface and realizes a capped number of trees. Scatter/refinement must be
the first modifier on geometry without shape keys or armature deformation; bake
upstream work explicitly. Their returned workload estimates explain candidate/
face budgets, but do not bound later native/source edits or all memory use.

For static LODs, inspect `inspect_lod_source` and carry `source_sha256` as
`expected_source` into `generate_lod_chain` with a fresh `chain` and decreasing
`levels` triangle budgets. Outputs are independent viewport snapshots; the source
stays in place. COLLAPSE suits general geometry, PLANAR protects planar seams/
materials, and UNSUBDIVIDE needs a regular grid. Review sampled bidirectional
surface error and render small/thin details: budget/UV/material/normal checks do
not certify silhouette or foliage density. For linear skeletal LODs, select `deformation="SKINNED"` as described below.
Relative morph transfer is described below; botanical impostors remain separate. Materials stay shared; edited per-level geometry requires a new chain.

Use `inspect_lod_chain`, then `chain_sha256` as `expected_chain` for
`activate_lod_level` or `export_lod_chain`. Activation hides other managed levels,
not the original source; move the generated root for comparisons. Inspect its new
fingerprint after changing level/root transform. Export creates separate GLBs and
a checked manifest in a fresh directory; run `validate_lod_export`, then re-import
and view representative results. Binary counts/bounds/UV/normal/dependency checks
are not engine or appearance certification. Native calls cannot cancel internally;
generation/export report progress/storage and clean owned resources on ordinary
errors/cooperative cancellation. Full limits are in USER_MANUAL.md.

For skeletal LODs, inspect/generate with `deformation="SKINNED"`. This uses
raw rest geometry with one enabled linear group-only Armature modifier, normalized
complete weights (up to four influences), and the original rig. Additional mesh
modifiers and DQ/envelopes/masked armature binding require another workflow. Joint-weight
protection helps preserve bends; triangle and sampled pose-error limits can still
refuse. Choose meaningful `pose_frames`, or review suggested action/timeline
frames. Use `sample_lod_chain` again after motion/control changes: stored measurements
cover recorded inputs only, and external dependencies are not frozen. Move the rig
rather than the generated bind root. For delivery, call `inspect_lod_export`, then
carry its `chain_sha256` and `animation_sha256` as `expected_chain` and
`expected_animation` into `export_lod_chain` with a fresh directory. Animated
bundles independently compare decoded joints/weights/inverse binds and sampled
corresponding vertices against native playback. Use `animations=false` for bind-only
output. Animated delivery needs simple local rig/actions with integer clip endpoints;
bake controls/drivers/active NLA first. Clips use zero-based seconds; manifest
native frame starts/FPS preserve their original time mapping. Validate the bundle,
then re-import/sample and visually review. For morph-only assets, use `deformation="MORPH"`; compatible relative keys also
transfer automatically in SKINNED mode. Projection interpolates masked relative
offsets onto reduced rest geometry. Generated weights follow the source Key values
and mutes, preserving source clips/drivers/NLA as the shared controller. Keep that
source dependency in editable Blender delivery; animate the source, not driven LOD
weights. Review every-key and timeline surface checks and resample after control
changes. Modified source keys/masks or generated links invalidate the chain.
For detached morph GLB bundles, plan/export with the same named `timeline_clips`
(start/end integer frames, inclusive). The planner identifies BAKED_MORPH_TIMELINE;
carry both guards into export. The current source timeline, including drivers/NLA
and solved rig constraints/root motion, bakes onto temporary independent copies.
Inactive actions are not switched automatically. Every baked proxy frame and
sampled decoded playback must match native evaluation before publication. Use
`animations=false` without ranges for rest-bound morph delivery. Validate/re-import
and review; see the manual for limits, reference-frame mapping and key ordering.

For file inspection, call `inspect_glb_deformation` on a library `.glb` path.
It queues by default: poll/wait, or pass `wait=true`. Read target/joint/clip inventory,
then page/select clips and inspect sampled glTF-world (+Y-up) bounds/vertex positions.
Dense and sparse float morphs replay before optional linear skinning. A null clip
sample uses stored default weights. This reads the file without importing it or
changing the scene; it does not compare to authored Blender geometry or certify
all-frame/appearance/engine fidelity. The native profile is one mesh, optional skin,
up to 63 morphs; normalized/compressed/instanced/multiple-mesh assets are outside it.
Morph LOD bundles bake explicit current-timeline ranges and validate native/file correspondence; general graph serialization and inactive-action batching remain separate.

Prefer structured tools for the supported pipeline, including when Python
execution is disabled: `create_primitive` / `create_mesh`, `configure_modifier`,
`apply_modifier` / `remove_modifier`, `generate_uv`, `duplicate_object`,
`set_parent`, `apply_transforms`, `configure_material` and `assign_material`.
Arguments for these tools are inside `params`. Use named resources to avoid
selection-dependent edits. UV generation requires explicit overwrite for an
existing map. Independent duplicates are the default; shared mesh edits require
`make_single_user=true`. Apply transforms before adding dimension-sensitive
modifiers when appropriate; modifier parameters are not rescaled automatically.
Operator-based asset tools require Object mode and a visible/selectable target;
transform baking supports static unconstrained meshes. Inspect partial results
after an error; these operations do not roll back.

Discover `list_actions` and `describe_action`, then validate a named workflow with
`plan_action`. `game_asset_prepare` defaults to inspection of `objects` and a
triangle budget. Request transforms, UV generation or triangulation explicitly;
optional save/export paths require library-write permission. It preflights all
targets, but later failures can leave edits. Its edit/export mode supports static
meshes; use rig/morph tools for animated deformation. Review report issues rather
than treating completion as engine compatibility. `run_action` takes `action`,
`inputs`, optional `request_id` and `wait` directly, without a params wrapper.
With wait=true it returns an operation record even for failure/cancellation: check
state and inspect each step's result. Reuse the planned request ID for matching
generated output paths.

Use `preview_setup` for a fresh persistent fitted camera and three asset-relative
area lights; existing scene lights remain. Choose a fresh prefix. Alternatively,
use `configure_camera` then `frame_objects` to fit named meshes for a preview;
configure the intended render aspect first and check `fully_in_frame`. Refit after
pose/aspect changes. Use Python only for functionality the structured tools do
not yet expose, such as specialized node graphs, when policy allows. For skeletons
and animation, use the structured armature/binding/clip tools described in
`blender-mcp-animation`; inspect weights with `inspect_rig` and evaluate deformation
with `sample_animation` before export.

For relative morph targets, use `create_shape_key` / `edit_shape_key` with sparse
Basis-relative offsets, absolute mesh-local positions or a same-topology source.
`inspect_shape_keys` exposes topology fingerprints, changed-vertex samples and
weight state; carry `expected_topology` into later indexed edits. Coordinate edits
preserve unlisted vertices by default. New keys start at weight zero; use
`set_shape_key_weights` for static previews after clearing active morph animation.
Basis edits and stale topology are refused. Use the animation skill for named
morph clips, combined bone/morph sampling and GLB animation delivery.

Use apply_material_preset for textured PBR surfaces, with packed color, roughness,
metallic and normal maps. For custom supported shaders use shader_node_catalog,
inspect_shader_graph and the typed node/link tools. Existing materials require
explicit graph replacement; prefer incremental edits when preserving a user graph.
Procedural shader graphs do not imply equivalent Godot materials; review or bake
those surfaces before engine delivery.

`execute_code` runs Python on Blender's main thread. `bpy` is preloaded; assign a
JSON-compatible value to `result`. Each call has a fresh namespace but shares the
live scene. Prefer direct data API edits where operators would depend on mode,
area or active selection. Use explicit context overrides for operators that need
them. Report `success=false` scripts as failures even when the MCP tool call itself
completed. Edits before an exception are not rolled back.

Use clear object names and preserve existing user assets. After editing, inspect
the changed geometry independently and request a viewport image with
`capture_viewport`, then **view it** with `get_image`. Headless Blender has no
viewport: use a camera render and distinguish visual evidence from geometry checks.
Keep inspection proportional to the requested asset: dimensions and origin matter
for game props; topology, normals, UVs and deformation matter where the asset needs
them. Object counts alone do not validate a model.

For Godot delivery, verify intended units, dimensions, origins, axes, selection,
material assignments and animation clips. Save the editable `.blend` project and
export a GLB with `export_glb` or `export_objects_glb` (explicit `objects` inside
params, restoring selection). Include the rig and meshes for skinned delivery.
For evaluated static Geometry Nodes/modifiers, request `apply_modifiers=true`;
the default exports the base mesh. This explicit evaluated mode refuses shape-key
and armature-deformed meshes. Parse or reimport the delivery to check its geometry.
Structured file paths are relative to the active
`library_root`. Existing project/export files require explicit `overwrite=true`;
use it when replacement is authorized by the task. `export_glb` exports selected
objects by default and handles glTF axis conversion. Avoid additional blind axis
rotations. Verify the exported artifact and, when Godot is available and in scope,
check import there. GLB export is not proof of Godot material, collision or gameplay
behavior.

GLB world coordinates are metres: nondefault scene units use file-only uniform
root transforms. Mesh-local POSITION bounds are not world dimensions. Inspect
static LOD `world_bounds_m` or package world proofs; skeletal/morph quality budgets
remain in source scene units, with labeled comparison decodes. Export manifests
bind scene scale to encoded roots. For projects with mixed scene scales, use
explicit active-scene `export_objects_glb`; whole-file export refuses mixed units.
Nondefault unit rewriting is bounded to 512 MiB GLB/16 MiB JSON and does not change
the editable scene. Camera/light unit properties are not qualified.

The scene is shared across keys and clients. Operations execute serially; named
actions group dependent steps into one operation. Operator-local JSON recipes can
compose supported structured commands without Python. For long
work, use `submit_operation` or `execute_code(wait=false)` with a caller-chosen
`request_id`, then poll `get_operation`. Reusing the same ID and arguments recovers
the same operation across connections and frontend restarts. Changed arguments
need a new ID. `interrupted`/`outcome_unknown` requires inspection; it is not a cue
to replay a mutation.

Use `checkpoint` at meaningful editing milestones. Automatic recovery restores a
completed checkpoint, which can predate the latest edits. `bridge_status` reports
session identity and checkpoint/recovery errors. Check `storage_status` before
large imports/exports; operation storage fields report current free bytes and
the estimate/reserve used. Arbitrary Python output size is not predictable.

Explicit project/export paths are protected from temporary-output cleanup. Pin
wanted generated previews with set_operation_retention before external/custom
Python use; structured image/VSE/import use pins them automatically. Inspect
retention_status and preview_retention_cleanup for scope and candidates. Old
history can return details_pruned=true; its request-ID tombstone still prevents
replay, so inspect current state rather than resubmitting with a new ID blindly.

The active
`enable_autonomous_execution` flag is advisory for the orchestrator. Python has
Blender's OS permissions, and structured tool roots do not sandbox arbitrary code.

For reusable components, inspect `inspect_asset_assembly_source` with a closed
local object set (include rig controls and referenced objects). Resolve blockers,
then `create_asset_assembly` with its guard and a fresh collection name. Wait for
the queued operation and use `copied_objects` to find independent components.
Inspect the prototype for `assembly_sha256`, then `place_asset_instance` with
`expected_asset` and typed placement. Instances share the prototype and active
animation. Enable `set_asset_assembly_editing` to edit its mapped components using
structured tools; disable it afterward and reinspect guards. Existing placements
update together; sources remain intact. `inspect_asset_instance` gives current
viewport leaves/bounds; camera framing and preview setup accept managed placements.
Save the scene for editable delivery. No independent instance timing or external
library loading is implied. Static realization is described below; consult
USER_MANUAL.md for ownership, dependency and guard limits.
Current assembly graph guards use version 2: clean packed/saved external image
bytes and clean generated-image parameters, without expanding pixel arrays.
Unsaved image edits block guarded transfer/use; save the image or pack it first
(saving the blend alone is insufficient). PBR presets pack input images by
default. External files remain shared and are not forced to reload; their byte
changes invalidate cached guards. Existing prototypes remain usable, but obtain
fresh guards after the signature upgrade. Limits include 64 megapixels/image,
512 MiB/encoded file and 2 GiB total encoded dependencies, separate from native
decode/cache memory and the existing graph/geometry budgets.

For static assembly delivery, `inspect_asset_realization` takes managed placement
names in `instances`. Carry `source_sha256` as `expected_source` into
`realize_asset_instances` with a fresh collection name; wait for completion.
The returned `objects` are independent current-viewport mesh snapshots in world
space, suitable for `export_objects_glb` with `animations=false`. Sources remain
editable. This freezes the current pose and modifiers; materials remain shared.
Shader coordinates, external files and arbitrary attributes are not automatically
baked into portable GLB equivalents. Compare exported/re-imported geometry and
review materials; use texture baking when necessary.

For collision/shadow meshes, inspect `inspect_asset_proxy_source` with named local
meshes or managed placements. COLLISION uses BOX or CONVEX_HULL: choose PER_LEAF,
PER_SOURCE or COMBINED grouping deliberately because envelopes fill gaps. Resolve
blockers, then carry the guard and identical settings into `generate_asset_proxies`
with a fresh collection; wait for completion. Review volume and sampled surface
errors, then attach physics explicitly if needed. SHADOW requires DECIMATE,
PER_LEAF and a per-leaf triangle budget; outputs are Cycles shadow-only meshes.
Before generating a replacement, use `inspect_render_visibility` and guarded
`configure_render_visibility` to set the source visible_shadow=false. GLB/other
renderers do not inherit these Cycles flags. Materials stay shared. Inspect source freshness before delivery; remove
obsolete proxies using a fresh proxy guard after detaching physics/dependencies.
These generic proxies do not infer trunk/branch collision or validate foliage
silhouette/alpha coverage.

For batch delivery, inspect `inspect_asset_package` with portable asset IDs,
primary `objects`, optional owned collision/shadow collections and native `lods`.
Resolve blockers and review material/dependency warnings. Proxies and LOD sources
must belong to the declared asset inputs and remain fresh. Carry the package guard
and identical assets into `export_asset_package` with a fresh directory; wait for
completion and run `validate_asset_package`. Static primary/proxy snapshots use
world-space geometry, so stage the desired origin beforehand. Animation belongs
to the selected nested LOD profiles, not the static primary mesh. The manifest
records role associations; downstream tools must apply collision/shadow behavior.
Keep source scenes separately for editing, and visually review converted shaders.
See USER_MANUAL.md for validation limits and timeline/skin proof options.

For LOD lifecycle changes, use `inspect_lod_management` and its separate management
guard. Show a hidden original with `configure_lod_source_visibility` before fresh
source/rebuild/package planning; the flags affect all scenes using that object.
Start `rebuild_lod_chain` from `suggested_rebuild`, review recipes/defaults, carry
both fresh source and management guards, and wait for the staged replacement.
Sources/rigs/morph controllers remain intact. Existing placement/visibility is
preserved by default; authored root controls and external native references can
block replacement. `remove_lod_chain` removes owned derived content and retains
shared/fake-user meshes and source materials/clips. Reinspect after edits/reopen;
ordinary chain/export guards are not management guards. External adoption and
process-crash rollback remain separate; read USER_MANUAL.md for limits.

After an interrupted LOD/package/numeric/botanical export, inspect `inspect_export_job` using the
original output directory. If it is unknown, start with bounded `list_export_jobs`
and inspect a selected summary for its file inventory. These broker tools work
with Blender closed. Carry the
fresh job guard to `recover_export_job`; it validates files without replaying scene
work. Ready staging can be explicitly published; incomplete staging can be previewed
with `cleanup_export_job`, then deleted with dry_run=false and a fresh guard.
Published output stays protected; discarding ready or previously verified files
needs discard_ready=true.
A live lock, foreign owner, unknown file or changed inode is a refusal, not a reason
to force cleanup. Recover again after cancelled partial cleanup. Journals remain
outside delivered bundles. See USER_MANUAL.md for boundary and reference limits.

For imported or hand-authored reduced geometry, use `inspect_lod_adoption` with
ordered `inputs` (canonical source becomes LOD0). Use its combined `source_sha256`
as `expected_source` for `adopt_lod_chain`; a source-only guard is insufficient.
Explicit `material_slots`/`uv_maps` remap importer names on owned copies. Inputs
must be visible; `RAW_BASIS` ignores incoming skin/morph/modifier deformation,
whereas `EVALUATED_STATIC` requires static inputs. Canonical source supplies skin
weights, relative morphs and controls, with sampled rest/key/pose checks.
Originals remain independent. To refresh authored levels, inspect both adoption
and management again and use `readopt_lod_chain` with both guards. Ordinary
`rebuild_lod_chain` automatically reduces to comparable budgets and does not
recreate hand-authored topology. Inputs cannot belong to the replaced chain.

For a species-aware woody foundation, use botanical_species_catalog and
plan_botanical_tree (async by default), then create_botanical_tree with the same
recipe/model_sha256 as expected_model and a new collection. This differs from the
stylized VEGETATION preset: the canonical model is a seeded branch/bud graph in
local metres, with native wood/BarkUV and semantic attributes. Optional foliage uses shared leaf prototypes; wind, atlas/impostor and completed
vegetation delivery remain open. Inspect the
bare structure before choosing its next representation; a branch count is not
leaf coverage or biological/structural qualification.

Use inspect_botanical_tree for a fresh tree_sha256 and list_botanical_elements
for bounded branch/bud records. Plan a revised recipe and use both guards with
regenerate_botanical_tree. Manual derived edits require explicit discard opt-in;
canonical Text edits and external/shared references refuse regeneration. Static
root placement and existing bark materials remain by default. Source model IDs
are repeatable; topology changes do not guarantee arbitrary edit correspondence.
export_botanical_model writes canonical metre/Z-up JSON, not mesh placement or
verified GLB wind attributes. Preserve that model with the editable project;
remove_botanical_tree retains materials and refuses ambiguous native ownership.

For modular leaves use plan_leaf_template, then create_leaf_template with the same
shape and expected_leaf guard. For tree foliage, inspect_botanical_tree and
plan_botanical_foliage, then configure_botanical_foliage with expected_tree and
expected_foliage. These layout tools default async. Adjust shoot/node density and
leaf geometry under explicit leaf/expanded-triangle budgets. Native Geometry Nodes
instances preserve shared prototypes; no automatic realization or wind animation.
list_botanical_leaves pages attachment metadata. Growth regeneration preserves the
foliage recipe/material; owned removal includes its native dependencies. Manually
edited derived data needs explicit discard consent; canonical edits refuse rebuild.
See USER_MANUAL.md for lifecycle and optics boundaries.

Use inspect_botanical_coverage (async) to compare current or proposed foliage
recipes without editing. Fix views, resolution and margin across comparisons.
It samples opaque blade triangles in root-local orthographic projections; inspect
crown coverage, outside-envelope area, asymmetry and clipping, then plan/apply the
chosen recipe with fresh guards and render the same camera. Coarse samples can
miss small leaves and exclude wood/material optics. Raise resolution for review;
never use summed blade area as projected coverage. Work is bounded by an explicit
per-view triangle budget. See USER_MANUAL.md for mask coordinates and limits.

Managed trees reuse shared bark/leaf materials across regeneration. Use the
botanical surface tools for guarded UV fissure/vein color and bump without
realizing foliage or replacing the material ID. Render close-ups and retain the
editable project; bake procedural bark with the existing texture tools before
portable PBR delivery. Native thin-leaf optics and atlas/wind/vegetation LOD work
remain separate. See USER_MANUAL.md for surface ownership and removal guards.

Thin-leaf materials can enter the texture pipeline using explicit FRONT_PBR on
both inspect_texture_bake and bake_textures; review material_adapters for omitted
optics. Native source materials stay editable. A tested static leaf-to-card recipe
uses separate UV plane geometry, projected normal/color/roughness/ALPHA maps,
reviewed hit/alpha masks, reopened bundle validation and GLB alpha inspection.
Use inspect_foliage_card, then create_foliage_card with matching options and
expected_card for automatic static leaf/mesh-cluster targets. Realize instances
first. Choose world TOP/FRONT/SIDE and convex outline or two-triangle rectangle;
compare physical area, triangle cost and sampled empty area before baking.
Creation returns guarded bake_parameters with CardUV and native-unit cage/rays.
Choose directory, resolution and min_projection_coverage explicitly; the suggested
threshold is only a geometry estimate. Bake with the existing isolated worker,
review coverage/alpha masks, reopen/validate asset.blend and inspect the exported
card. Sources stay editable; the projection flattens depth and holes.
For shared atlases, inspect_texture_atlas with distinct ID/bake-directory entries,
then build_texture_atlas with the same layout options and expected_atlas guard.
Inputs must be successful original texture-bake bundles with matching maps; no
tile rotation/resampling occurs. Choose gutters, dimensions and full-mip RGBA8
budget; the estimate does not emit mipmaps or prove runtime memory/bleed behavior.
Reopen asset.blend and validate_texture_bake checks every ID mesh and shared
material before export. It preserves source placement in metres; arrange separate
representations deliberately. Existing texture-job tools handle recovery/cleanup.
Portable wind field/anchored pose preparation uses inspect_botanical_wind and
sample_botanical_wind. Review all-time bounds plus sampled root/junction/length
errors, then export_botanical_wind with its guard for semantic JSON. Sampling
preserves native geometry. Native preview uses inspect_botanical_wind_preview_source
then create_botanical_wind_preview with matching options/expected_plan and a fresh
collection. Its sampled cache/shared leaf instances preserve the source; inspect
pose/strain metrics and render its bounded baked range. Use returned objects for
preview staging and a fresh preview guard for owned cleanup. Attribute-retention
proof and target runtime validation remain open. Never present front-PBR
transfer as native optical parity or geometry coverage as measured render overdraw.

For custom numeric fields, inspect_mesh_attributes returns a base attributes_sha256
for expected_attributes on create/set/ramp/remove_mesh_attribute. Choose native
POINT/EDGE/FACE/CORNER and FLOAT/INT/BOOLEAN/FLOAT_VECTOR/FLOAT_COLOR explicitly.
Page values; preserve protected UV/internal fields. Shared mesh edits need explicit
make_single_user, and shared shape-key isolation refuses. Ramps use local axes,
not metres/world coordinates. GeometryNodeInputNamedAttribute supports the
attribute shortcut; INSTANCE storage requires realization for evaluated mesh
readback. Evaluated guards cannot edit base data. Check the native result and save
the editable project. For verified static field delivery, inspect_attribute_export
with explicit attribute/semantic bindings, then export_attribute_bundle using its
expected_export guard and a new directory. validate_attribute_bundle independently
decodes fields/positions/triangles/UVs/metre placement. Scalar lanes preserve raw
components; they do not auto-convert anchor vectors into GLB axes/metres. UV2 stays
available for lightmaps. Integers outside +/-2^24 refuse. Save the .blend separately;
complete botanical wind packing and downstream engine behavior remain separate.

For a larger complete source study, botanical_asset_presets exposes
OAK_CANOPY_STUDY. plan_botanical_asset_preset accepts a seed and explicit leaf/
expanded-triangle budgets; create_botanical_asset_preset uses expected_preset
and a fresh collection. It creates the ordinary editable master, three shared
leaf variants and procedural bark/leaf detail without bpy code. Use tracked
operations and poll the same ID; about 89-92k leaves in reference seeds 1/2/3
exceed default small-fixture instance budgets. Inspect returned stored/expanded
triangle counts, export instance hint and LOD mask estimates before downstream
work. The 14m figure describes wood; canopy boxes include added shoots/leaves.
Preview stages return asset_world_bounds in Blender world units; convert with
scene scale for physical dimensions. Save the project and view multiple renders.
This is an artistic canopy study, with remaining junction/optics/lighting/LOD/
collision/population work, not a completed mature-tree or game-runtime certificate.

For master secondary UVs, inspect_botanical_tree supplies mesh_assets and
expected_tree. create_botanical_secondary_uv accepts wood and leaf-N roles with
a new map name, actual texture dimensions and the same chart/border controls as
the LOD secondary tool. It preserves canonical geometry/attributes/primary UVs
and material sampling and updates owned content guards transactionally.
Regeneration and configure_botanical_foliage default secondary_uv_policy=PRESERVE:
exact maps survive only compatible local geometry and original UV baselines.
Choose REPROJECT explicitly for changed geometry using saved layout settings,
then recheck density/padding. DISCARD explicitly removes all authored secondary
maps; removing authored foliage roles requires it. No policy bypasses invalid
canonical models or discard_derived_edits protections. Master GLB bundles verify
all authored UV channels. Native LOD0 and shared leaves inherit exact maps;
reduced wood requires its own create_vegetation_secondary_uv. Shared UVs do not
constitute unique leaf/tree instance lighting atlases.

For owned tree wind interchange, inspect_botanical_export with collection/wind,
then export_botanical_bundle with the same options, expected_export and a new
directory. validate_botanical_bundle works after source removal. It carries full
canonical hierarchy/leaf orientation/phase/flutter semantics and verified branch
fields, wood/shoot GLBs and one shared GLB per leaf variant. Segment pivots differ
from whole-axis anchors; read the recorded coordinate contract. Buds remain
semantic points. No UV channel is used for wind. Keep the editable .blend and bake
PBR separately; native shader optics, continuous motion, engine import and
vegetation LODs remain unqualified. Native rest-instance checks precede publication.

For near/mid tree LODs, inspect_botanical_lod_source with explicit descending leaf
budgets/radial sides and nondecreasing branch-radius thresholds. Inspect losses
before create_botanical_lods with expected_plan and a fresh lod_collection.
Planning/creation default async; poll or use wait=true. Failed quality gates refuse;
native wood quality is checked additionally during creation. New plans use
AREA_PRIORITY_MULTIGRID_V2: geometric-area/hash priorities independent of raster
positions, with BASE, finer and quarter-pixel-shifted quality grids. Inspect both
quality and validation_quality; every grid must pass. Native wood checks all grids
in a frame including the trunk base. Work budgets count all grids; the default
60 million projections stays unchanged, with an explicit maximum of 400 million.
Retain more geometry when quality fails rather than silently raising loss limits.
Fixed-view pixel coverage can still miss subpixel leaves; render levels with the same camera and restore
any temporary source visibility changes. inspect_botanical_lods returns lods_sha256
for activate_botanical_lod/remove_botanical_lods. Full LOD0 and reduced levels
share copied templates, retain canonical wind IDs/parents and survive source
removal. Cards/impostors, collision, optical/shadow/runtime
qualification and animated LOD playback remain separate. See USER_MANUAL.md.

For secondary UVs on owned LOD delivery meshes, inspect_botanical_lods returns
mesh_assets and the current lods_sha256. Use create_vegetation_secondary_uv with
expected_lods and explicit asset roles (for example lod-1-wood and leaf-0), a new
uv_map (default UV2), actual texture dimensions and optional chart_layout. This
stages the complete batch and preserves geometry/wind fields, prior UVs,
active/render maps, materials and historical bake/quality records. Every target
needs a primary UV and a free channel; no existing target is overwritten. Source
masters remain independent. Reinspect the new map and its geometric quality.
For later material revisions make a new bake preparation after secondary editing,
normally reusing BakeUV with uv_strategy=EXISTING; older preparations missing UV2
cannot be adopted. Secondary records travel with LOD export and are checked
against decoded UV data. Shared templates reuse UV2 for all instances; no unique
leaf/tree lightmap atlas, engine lightmap import or lighting bake follows.

For native LOD file delivery, inspect_botanical_lods then export_botanical_lods
with expected_lods and a new directory. SOURCE placement omits preview offsets
by default; DISPLAYED preserves them. Templates occur once and levels retain
canonical leaf/hierarchy mappings and encoded wind fields. Both export and
validate_botanical_lod_bundle default async; poll or wait=true. The independent
validator recomputes selections and checks decoded fields/UVs/counts/metres even
after all native sources are removed. Save the .blend separately; file proofs do
not certify native material optics or a runtime wind shader. Public MCP exports now use durable export jobs and atomic directory publication.
Inspect/recover/clean registered staging through the shared job tools; do not
delete unknown files to retry. Older unjournaled partial outputs need review.

For vegetation material delivery, inspect_vegetation_materials on the tree or LOD
profile. Review missing_detail_uv, linked/procedural bake requirements and separate
opaque/double-sided/front-back/backlighting fields. Tree parameter delivery uses
material_mode=PARAMETERS in both inspect_botanical_export and export_botanical_bundle;
the export guard includes materials. LOD export requires that mode plus the fresh
expected_materials fingerprint, independently of expected_lods. File validators
check actual encoded material/texture inventories; their base RGBA8 estimate
excludes mipmaps and runtime allocations. No maps or physical thickness are created.
Use the existing isolated FRONT_PBR bake workflow for portable maps; source
parameters do not establish optical parity. See USER_MANUAL.md for the contract.

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

For tree collision, inspect_botanical_collision_source selects trunk/major branches
by canonical start radius and branch order, with ancestor closure and explicit
piece/triangle budgets. create_botanical_collisions uses the fresh expected_plan
and a new collision_collection; it encloses selected native woody sleeves with
closed convex pieces without realizing foliage. Inspect mappings, containment,
volumes and actual renders. Root scaling is included in world_volume_m3; piece
volumes can overlap. hide_render defaults true, wire viewport display is used.
parent_to_root defaults true for asset editing. Set it false at creation for the
existing rigid-body tools, then attach PASSIVE/CONVEX_HULL physics explicitly with
fresh physics guards. The unparented mode's root is only an origin marker. Source
and collision snapshots remain independent. Inspect fresh collision guards before
removal; physics, foreign references and persistent IDs block deletion. Edited
owned data additionally needs explicit discard. Save/reopen and inspect again;
source tree session guards are not portable content hashes. Generic GLB export
supports root plus meshes up to its 64-object limit and uses displayed placement.
No wind-swept collision, automatic engine binding or collision bundle sidecar is
implied. See USER_MANUAL.md for numeric, source and lifecycle limits.

For dense botanical foliage, `inspect_botanical_foliage_clusters` plans bounded
semantic-axis/spatial workloads without realizing the full tree. Poll the operation;
page summaries with offset/limit, and retain its page-independent plan guard.
Actual native template triangles and leaf/count budgets apply. Bounds cover leaf
centres only. Use create_botanical_foliage_cluster with the planning settings,
expected_plan, cluster_index and a new cluster_collection to realize one bounded
independent static source. Selected variants need identical UV schemas; unsupported
object/generated/instancer shader sampling refuses before mutation. Materials stay
shared. Inspect/remove with the snapshot guard; foreign references/physics/shape
keys block deletion and native edits require explicit discard. Pass the returned
object to existing fitted-card tools, then explicitly choose FRONT_PBR for managed
thin leaves, bake, reopen/validate and review alpha before export. No multi-view,
filtered optical/shadow, wind or far-LOD quality follows from a single fitted view.

For matched native/card review, keep a fixed camera/frame/lighting and transparent
film, render each representation in isolation, then compare_png_images on the two
library PNGs. Inspect hard/soft IoU, excess/missing alpha, alpha-area bias and
premultiplied RGB error at declared box-filter scales. Empty reference data cannot
pass; opaque-background alpha is not an isolated silhouette. Treat passed=false
as rejected quality, not success merely because rendering/export completed. This
is image evidence only, not GPU mip/alpha, shadow, wind or engine qualification.

Projected ALPHA now uses zero padding while other bake maps retain margin. Verify
the bundle's map_policy and per-map bake_margin; legacy files retain old pixels.
Do not reuse an old operation ID/directory expecting a corrected rebake. Compare
matched transparent-film renders after any padding/resolution change. The corrected
dense selected-cluster example passes its fixed TOP-view gates, not multi-view,
shadow, wind, GPU alpha/mip or whole-tree population acceptance.

For multiple cards, inspect/build_texture_atlas on distinct successful corrected
bake bundles; retain native source placement and review all outputs. New plans
require RGBA8_CORE_AND_CLAMPED_GUTTER_V1: exact core/gutter channel checks include
transparent RGB, with source/file/layout-bound sealed evidence. Reopen/validate
asset.blend before GLB export. Retained evidence can be validated after input
bundles are removed; rebuilding cannot. Compare individual delivered cards versus
the atlas under the same fixed camera before comparing the atlas with native
geometry. An exact copy witness does not certify mipmaps, angular views, shadows,
wind or whole-tree/population budgets.

Use inspect_foliage_card_views to prepare TOP/FRONT/SIDE alternatives from one
ordinary source inspection under source/projected/output-triangle budgets.
Consume each row's create_parameters plus a fresh name with create_foliage_card;
the global views_sha256 is not an expected_card. Bake/validate each view separately.
For review configure ORTHO then frame_objects on source plus that target using
camera_frame_view (SIDE -> RIGHT), and keep the camera fixed between native/card/
atlas renders. Alternatives do not provide angular selection/interpolation or
an automatically safe crossed-card, wind or whole-tree far representation.

For persistent alternatives, open the unchanged baked/atlas asset and use
inspect_foliage_card_family_source with directory and explicit view/object entries.
Accept lossy FRONT_PBR explicitly when declared; keep angular/triangle/texture
budgets. create_foliage_card_family consumes expected_plan and a new collection,
packing private images/materials and preserving original objects. Copies start
hidden. Hide originals separately for matched review. Inspect the family after
save/reopen; it is independent of source files. Move/rotate/uniformly scale only
its root and keep its collection directly visible in the current scene/view layer.

Use inspect_foliage_card_family_selection with exactly one camera or world-space
direction from asset toward viewer, then select_foliage_card_family_view with the
fresh selection_sha256. Unsupported/reverse directions are unmeasured coverage,
not permission to reuse a back view. The fixed cone (default30degrees) is declared
support, not a quality certificate. Perspective checks the whole bounds envelope.
Selection shows one owned alternative; repeat explicitly when camera/root changes.
No playback handler, interpolation or automatic far-LOD switch is installed.
Export only the returned visible object for a static GLB selection; glTF does not
receive the selector. Remove only a valid fresh family guard; edits/external users
block deletion. Keep native sources and original optics declarations.

For all-view portable delivery, inspect the family and call export_foliage_card_family
with expected_family, a new directory and explicit byte budget. Poll durable job
progress/storage; use export-job inspect/recover/cleanup after interrupted writers,
never replay solely because observing an operation timed out. Validate with
validate_foliage_card_family_bundle after relocation. The bundle includes one
embedded GLB per available view and a family-only packed editable asset.blend.
Open/inspect the blend separately; independent validation hash-checks that file.

Read selector origin/normals/bounds in GLTF_WORLD_Y_UP_METRES, choose exactly one
available view under its declared cone, and do not apply native placement twice.
The files contain displayed placement, not an engine selector or animation. Corner/
view identity lanes consume no UV channel. Binary geometry/UV/normal/placement and
PBR bindings are validated; texture pixels, angular quality, optics, custom wind
payloads and engine behavior need their own evidence. Preserve optical losses.

Use inspect_projected_normal_transfer on the unchanged original projected bake,
not an atlas, to inspect covered backward/grazing tangent normals and geometric
context. It validates binding, changes no maps and infers no optical pass/fail.
A flipped normal map cannot restore missing true-geometry transport by itself.

Sparse foliage can hide large shading differences in whole-image RGB RMSE. Review
reference_area_rgb_rmse and overlap_rgb_rmse, and set their optional quality gates
explicitly when appearance matters. Reference-area error still includes coverage
loss; overlap uses straight colour weighted by shared alpha and needs independent
silhouette gates. Explicit null criteria disable those gates through MCP. Dark
FRONT/SIDE cards remain a shading issue: flat normals improve the current uniform-
world control, while flipping backward map normals only partially helps. Neither
control is a native-optics or dynamic-lighting correction.

For camera staging, frame_objects reports source_bounds_world in native scene units.
Hidden target/collection visibility is temporarily enabled for evaluated bounds and
restored afterward. Keep targets in a nonexcluded current view-layer path; refit
when frame, aspect or geometry changes. Orthographic fits account for actual
projection/shift; setup_preview_stage shares the hidden-source evaluation path.

Fitted cards/families support TOP/FRONT/SIDE plus BACK/LEFT/BOTTOM and the four
FRONT_RIGHT/BACK_RIGHT/BACK_LEFT/FRONT_LEFT horizon diagonals. Default view requests
stay TOP/FRONT/SIDE. Explicitly budget larger requests (max ten views, 2.5M summed
source projections, 2540 fitted triangles; lower defaults still apply). Pass the
returned camera_frame_parameters into frame_objects; diagonal camera_frame_view
is null. No agent-side basis/quaternion computation is required.

A complete eight-view horizon ring has nearest samples within22.5degrees along
that ring, with poles additionally available. Elevation gaps remain outside the
default30degree cone; neither rendering quality nor full-sphere coverage follows
from that geometric bound. Each back/diagonal is independently baked, never a
reused reverse face. New delivery uses bundle-v2 with all ten catalog names;
legacy bundle-v1 retains its original three-view tie contract and validates.
