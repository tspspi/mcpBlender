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

For high-to-low textures, inspect `inspect_texture_bake` with the low `name`,
high `sources`, target `uv_map` and optional topology-matched `cage`. Carry its
`bake_sha256` as `expected_bake` into `bake_textures` with a new output directory.
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
native wood quality is checked additionally during creation. Fixed-view pixel
coverage can miss subpixel leaves; render levels with the same camera and restore
any temporary source visibility changes. inspect_botanical_lods returns lods_sha256
for activate_botanical_lod/remove_botanical_lods. Full LOD0 and reduced levels
share copied templates, retain canonical wind IDs/parents and survive source
removal. Cards/impostors, collision, optical/shadow/runtime
qualification and animated LOD playback remain separate. See USER_MANUAL.md.

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
