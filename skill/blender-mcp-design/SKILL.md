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
Save the scene for editable delivery. No independent instance timing, external
library loading or realized/exported assembly delivery is implied; consult
USER_MANUAL.md for ownership, dependency and guard limits.
