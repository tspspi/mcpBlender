---
name: blender-mcp-animation
description: Create, inspect, render and revise Blender animations through mcpBlender, including game/simulation asset animation and video assembly. Use for animation timelines, keyframes, camera motion and frame/video delivery; use blender-mcp-design for static modeling.
---

Inspect the application session, scene, frame range, FPS, actions and resources
with `bridge_status`, `get_scene_info` and `inspect_resources`. Confirm the intended
duration, motion and export destination from the task. Use GUI mode for viewport
feedback; background mode supports camera renders. Discover renderer and video
capabilities with `get_capabilities` rather than assuming GPU/codec availability.

Use `set_keyframes` for object location, Euler rotation (radians) and scale, and
`configure_render` for timing/FPS. Named domain tools take their data in `params`.
For skeletal animation, prefer `create_armature`, `bind_mesh`,
`create_animation_clip`, `set_pose_keyframes` and `set_active_clip`. These work
with Python execution disabled. Define bones with armature-local head/tail
coordinates and optional parents/connected joints. Bind meshes before posing:
AUTO computes native weights, RIGID needs one bone, and EXPLICIT accepts
per-vertex influences. Inspect coverage and weight sums with `inspect_rig`.
Existing bindings/group conflicts are refused; shared mesh edits need explicit
isolation. Unweighted vertices are an error by default.

For existing skins, use `inspect_skin_weights` and carry `weights_sha256` as
`expected_weights` into set/repair/smooth/mirror or binding configuration. These
use raw basis indices, not evaluated vertices. Repair supports prune/influence
limits and explicit ERROR/KEEP/FALLBACK/nearest-rest-segment policies; nearest is
a heuristic. Mirror needs explicit bilateral bone pairs and a chosen plane/space.
Locks and nondeform masks survive by default; shared data requires explicit
`make_single_user=true`. Edits default to queued operations with progress/storage
and cooperative rollback. Inspect issues again and sample deformation at meaningful
poses; normalized weights do not prove a useful bend. See USER_MANUAL.md for
limits and exact replacement semantics.

For rest-skeleton changes, inspect `inspect_armature_rest` and carry `rest_sha256`
as `expected_rest` into `edit_armature_rest`. `bones` patches existing rest fields;
`add_bones` is additive. Heads/tails are armature-local; connected child heads
follow parent tails while child tails stay fixed, and explicit conflicting heads
refuse. Use `parent=""` with `connected=false` to unparent. Shared data needs
explicit isolation. Existing skinning/animation/attachments require
`allow_deformation_change=true`: channels and weights keep their values, so motion
can change. Compare evaluated poses, not only rest geometry. Renaming/removal and
pose-to-rest/animation rebasing are separate; read manual limits before editing.

For reduced skeletal meshes, use `inspect_lod_source`/`generate_lod_chain` with
`deformation="SKINNED"` and the source guard. The chain follows the existing rig
and clips, retaining normalized native-interpolated weights. Choose representative
`pose_frames`; inspect rest and posed error rather than only triangle counts.
Joint protection can preserve bending regions but cannot guarantee a requested
budget. `sample_lod_chain` rechecks current-timeline deformation without clip
switches and restores frame/visibility. Rest/weight/binding edits invalidate the
chain; changed animation/control inputs require fresh pose review. The first skin
workflow is linear, group-only, single modifier and up to four influences.
Relative morph keys can transfer automatically with SKINNED, or alone with
`deformation="MORPH"`. Masked relative deltas interpolate onto reduced rest meshes;
weights follow the original Key controller, including actions/drivers/NLA and mutes.
Animate the source and retain that Key dependency in editable `.blend` delivery.
Every isolated key and sampled current-timeline deformation undergo surface-error
checks; resample after animation changes. Source key/mask or output link edits
invalidate ownership. For morph bundles, pass explicit named `timeline_clips`
(`frame_start`/`frame_end`, inclusive integers) to planner and exporter. These bake
the current evaluated source timeline, including driver/NLA controls, solved rig
constraints and root motion, onto temporary independent copies. Inactive actions
are not switched automatically. The BAKED_MORPH_TIMELINE profile verifies native
proxy poses at every keyed frame and decoded file poses at sampled frames before
publication. Its bind reference is the first range's start; zero-based clip time
maps back through manifest FPS/frame starts. `animations=false` without ranges
delivers rest-bound geometry with current morph defaults.

For bundles without morphs, the existing simple-rig profile exports compatible
local rig clips with full integer frame ranges. Constraints, drivers and active
NLA need a prior bake in that profile. For every bundle, call `inspect_lod_export`,
carry its chain/animation fingerprints into `export_lod_chain` (`expected_chain`,
`expected_animation`), and choose a fresh directory. Use manifest native frame
starts/FPS when comparing zero-based exported playback. `animations=false` delivers bind-only
geometry even for controlled rigs. The decoder compares all joint matrices and
sampled corresponding vertices at 3–9 frames per clip; this is not every-frame
motion or appearance proof. Run `validate_lod_export`, then re-import/sample and
review representative motion. See USER_MANUAL.md for profile and tolerance limits.

For file inspection, call `inspect_glb_deformation` on a library `.glb` path.
It queues by default: poll/wait, or pass `wait=true`. Read target/joint/clip inventory,
then page/select clips and inspect sampled glTF-world (+Y-up) bounds/vertex positions.
Dense and sparse float morphs replay before optional linear skinning. A null clip
sample uses stored default weights. This reads the file without importing it or
changing the scene; it does not compare to authored Blender geometry or certify
all-frame/appearance/engine fidelity. The native profile is one mesh, optional skin,
up to 63 morphs; normalized/compressed/instanced/multiple-mesh assets are outside it.
Morph LOD bundles bake requested current-timeline ranges; serialization of a general controller graph and automatic inactive-action batching remain separate.

Clips name the armature in `name` and the action in `clip`; tracks specify a
`bone`, `property` and vector `keyframes`. Bone `rotation_degrees` uses XYZ Euler
degrees relative to rest-bone axes, unlike object `set_keyframes` rotations in
radians. Clips persist while inactive. Duplicate clip names are refused; use
`set_pose_keyframes` to edit keys. Clip switching resets unkeyed channels to rest.
Ordinary single-action rigs and muted glTF NLA stashes are supported; constraints,
drivers and active NLA blending need another workflow. Constraint controls and
current-timeline sampling are described below; ordinary clip switching/editing
keeps its existing constraint guard. Imported ambiguous actions
require an explicit slot from `inspect_animation`.

For IK or copy/limit/track constraints, bind first, then create Empty goals/poles
with `create_animation_control` and animate them with guarded `set_control_keyframes`. Inspect
`inspect_animation_constraints` for the object or pose `bone`; carry its
`constraints_sha256` as `expected_constraints` into typed configure/remove/move
calls. Settings replace the exposed fields, and omitted fields use defaults.
Targets are named objects or bones. IK requires a bounded ancestor chain, the
standard solver and preferably a bent rest chain; inspect `ik_diagnostics` endpoint
distance and the elbow/pole direction. Native validity is not reach verification.
Independent control bones can work in the same rig; use `set_control_keyframes`
after constraint setup. Configuration/removal of keyed constraints is refused,
but their influence can be animated through the channel tool. Dependency
checks conservatively reject cycles and unsupported reachable dependencies.

Use `inspect_animation_channels` for the current object's action slot and paged
keys/handles/modifiers; carry `animation_sha256` as `expected_animation`.
`set_control_keyframes` supports object/bone location, scale, Euler degrees,
normalized WXYZ quaternions and named constraint influence. Bone values use pose-
basis axes, not world positions. Constraints stay active, so evaluate the result.
Both it and `edit_animation_curve` require an unused `output_clip`: they copy the
active action, activate the new clip and retain the original. Shared peers and
morph owners keep their original bindings; this does not coordinate multi-object
clip switching. Inspect new action/slot/hash after each edit.

Use `edit_animation_curve` with inspected `data_path`, `component`, selected key
`frames` and settings operation TRANSFORM (time/value scale and offset), DELETE,
INTERPOLATION (including easing) or HANDLES. Explicit handle coordinates require
FREE and one selected key. Raw curve units are native (Euler radians). Retiming
collisions are refused; native auto handles recalculate. Imported modifiers,
sampled/locked/muted curves, unsupported drivers, active NLA/blended actions and multilayer
editing are inspect-only. Failures restore the original binding/frame. Inspect
`edit_blockers` and per-channel `typed_editable` before proposing edits; validate
key/intermediate playback. Full contracts and bounds are in USER_MANUAL.md.

For driver controls, create a numeric `set_animation_property` on an object/bone,
then key it through `set_control_keyframes` using `property="custom_scalar"` and
`custom_property`. Inspect `inspect_animation_drivers`; carry `drivers_sha256`
as `expected_drivers` when configuring/removing an explicit typed `channel`.
Channels cover transform components (Euler radians/WXYZ), scalar controls, named
constraint influence and relative non-Basis shape weights on independent meshes.
Use named PROPERTY/SHAPE_KEY inputs for raw values or TRANSFORM inputs for native
evaluated spaces. Formulas use native simple numeric expressions, up to eight
inputs; no arbitrary Python calls or attributes. Typical bone rotation formula:
`bend*pi/2`, with a PROPERTY input from the rig's `Bend` scalar.

Managed drivers can remain while keying upstream controls on the same object;
directly driven channels cannot also be keyed. Create/configure constraints before
drivers because constraint editing retains conservative driver dependency guards.
Dependency checks distinguish raw scalar values from solved transforms and reject
feedback; imported/externally changed drivers remain inspect-only. Metadata is
matched against native variables, not trusted as a dependency declaration. Check
native validity and sampled endpoints/deformation, including input extremes;
current-frame validity does not guarantee every future value is valid. Save/reopen
and use visual baking for supported skeletal delivery. Morph/object-motion baking, animated strip-control/time authoring and retargeting
remain separate workflows. Full contracts: USER_MANUAL.md.

For NLA composition, author source clips first. `inspect_nla` uses object `name`
and OBJECT/default or SHAPE_KEYS `target`; carry `nla_sha256` as `expected_nla`.
It reports bottom-to-top layers, active action and source-slot content hashes.
Create named `configure_nla_track` layers, then `configure_nla_strip` with clip/
optional slot, source action_start/end, timeline start/scale/repeat/reverse,
blend/influence/fades and extrapolation. Same-track overlaps are refused; use
separate layers for crossfades. Configure replaces the full exposed settings.
Source actions stay intact. Imported/modified/locked/unsupported strips remain
inspect-only. Moving a managed track after imported neighbors preserves them;
moving to the bottom requires a fully supported prefix.

Use `configure_nla_playback` to enable NLA and explicitly choose whether to clear
the active action (retained as a clip) or blend it above the stack. `reset_base`
requires clearing: rigs reset bone transforms; shape targets get an explicit
zero-weight foundation, because native NLA shape defaults are ONE. Keep that
base below additive/weighted morph layers. It uses a short held constant clip;
repeated resets replace unchanged unused generated actions. Initial shape-base
creation/rebuilding requires a wholly supported managed stack. Never infer a
zero NLA baseline from static weight values alone.

Rebuilds are async by default; inspect progress/storage, or wait=true for short
work. Staging/cancellation leaves the original stack intact; final native commit
uses existing checkpoints for crash recovery. Sample the current composite at
key/intermediate frames with skin/morph deformation, save/reopen, and visually
bake supported skeletal motion before GLB delivery. NLA ACTIONS export of source
clips does not prove the composite was exported. Mute NLA layers before using
simple clip-edit tools; source edits require a fresh stack hash. Full contracts,
limits and native influence-envelope semantics: USER_MANUAL.md.

For motion retargeting, call `inspect_animation_retarget` with source rig `source`,
target `name` and explicit `{source,target,rotation_correction_degrees?}` mappings.
Use exact-name suggestions as suggestions; do not invent anatomical equivalence.
Review rest/parent differences, skipped ancestors, connected translation roots
and median length-ratio translation scale. LOCAL_POSE copies joint-local basis
motion into target axes; ARMATURE_DELTA transfers armature-space rest-relative
rotations. Unmapped ancestors can matter; per-map axis corrections are explicit.

`retarget_animation` requires fresh expected_source_rig/expected_target_rig hashes,
unused output_rig/clip, frame_start/end and optional target skin `{source,output}`
entries. It reads the current evaluated source, including NLA/drivers/IK, and
creates independent target-derived skeleton/skin data and quaternion keys. ROOT
translation applies at mapping roots; IGNORE/default local scale preserves target
proportions. Source_start/playback_speed remap time; reference_frame anchors object
placement. COPY/default object motion transfers rigid locomotion, while IGNORE
keeps the output stationary. Animated object scale/shear is refused. Copied
relative shapes freeze at reference values; materials stay shared. Source assets
remain editable and the original frame is restored.

Poll transfer/verification/storage progress. Every integer target frame checks
keyed matrices against recomputed transfer, with finite skin scans; this does not
prove anatomical mapping, contact, weights or subframe winding. Inspect the rig's
binding and key/intermediate deformation, render a preview and save/reopen. Export
only the transferred rig/skins, reimport and compare root movement/playback. Mixed
object/skeletal clips use current-timeline tools rather than simple clip switching.
Dense output reports within_nla_key_limit; direct rendering/export remains possible.
Limits and supported surface/shape handling are in USER_MANUAL.md. Contact-aware
retargeting, complete control-rig and morph-clip transfer remain separate work.

Use `sample_constraint_animation` to inspect the current constrained timeline at
key/intermediate frames, including bound mesh deformation. It restores the frame
without switching actions or resetting pose channels. It is asynchronous by
default: poll the operation or use `wait=true` for a small sample. Native frame
evaluation blocks; cancellation is between frames. Save/reopen and view a render.
For portable motion use `bake_constraint_animation` with source rig `name`, unused
`output_rig`/`clip`, integer `frame_start`/`frame_end`, and optional `meshes` entries
`{source, output}`. It creates independent constraint-free rig/mesh data and a
managed quaternion clip, verifying every integer-frame bone matrix and copied
mesh vertex against the source. Source controls/actions remain editable. Poll
progress; cooperative cancellation/errors remove the new assets and restore the
frame. This version requires stationary rig/mesh object transforms, single-segment
bones and simple vertex-group skins without other modifiers, shape keys or mesh
animation/constraints. Limits: 500 frames, 256 bones, 32768 bone-frame samples,
eight meshes and two million vertex-frame samples. It refuses unsupported motion
or errors above tolerance (.0001 default); subframes are not certified. Save the
source plus baked assets, export only the baked rig/meshes, reimport and compare
playback. Constraint controls in a `.blend` alone do not prove portable animation. Existing `sample_animation` and simple
clip editing retain their constraints/drivers/NLA restrictions.

For morphs, use `create_shape_key` / `edit_shape_key` and `inspect_shape_keys`.
Coordinates are mesh-local; OFFSET values are displacements from Basis and do
not accumulate when repeated. Sparse edits preserve unlisted vertices unless
`reset_unspecified=true`. A same-topology `source_object` supplies raw local
reference coordinates, without its transform/modifiers. Carry `expected_topology`
from inspection when later edits depend on vertex indices. Basis/absolute-key
editing and changed managed topology are refused. Inspect deformation after edits;
matching connectivity does not prove semantic correspondence of symmetric vertices.

`set_shape_key_weights` sets static values in [0,1]; clear the active morph clip
first. `create_morph_clip` uses mesh `name`, action `clip`, and scalar tracks such
as `{"key":"Wide","keyframes":[{"frame":1,"value":0},{"frame":12,"value":1}]}`.
Use `set_morph_keyframes` for updates and `set_active_morph_clip` for switching.
Switching clears unkeyed weights; omitting clip clears animation and resets weights.
Morph animation needs independent mesh data and supports muted import stashes,
not drivers or active NLA blending. Inspect slots/tracks with `inspect_morph_animation`.

To combine bones and morphs in one exported clip, create the skeletal clip first,
then `create_morph_clip` on the bound mesh using the same name and
`join_existing=true`. Bone and morph slots remain independent and can be edited
separately. Use `sample_morph_animation` with `armature` and `skeletal_clip` to
inspect the combined result at key/intermediate frames. It restores weights,
actions, slots, frame and the explicitly sampled rig pose even on cancellation.
Without skeletal_clip, the chosen armature's current action/pose is used.

Use `execute_code`, when allowed, for unsupported constraints/driver repairs, absolute shape keys, animation
layers or geometry nodes not yet exposed by structured tools. Return inspection
data in `result` and check success/traceback. API details depend on Blender version.

Inspect evaluated poses at key and intermediate frames using `set_frame` and
`inspect_rig`/`inspect_mesh`, or use `sample_animation` to compare several frames
and clips in one operation. Sampling returns world bone endpoints and evaluated
mesh samples/bounds/digests, then restores frame, action, slot and pose even on
cooperative cancellation. It temporarily evaluates a local rig and can mark the
project dirty. Check transforms, framing and intended endpoints;
successful key insertion does not prove the motion is right. Save a `.blend`
project and force a recovery `checkpoint` at useful milestones.

For rigid dynamics, inspect `inspect_physics` and carry `physics_sha256` into
`expected_physics` on world/collider/sampling/bake calls. Use static local proxy
colliders when the visual asset has modifiers, rigging or animation. Set up the
world, active bodies and passive collision surfaces with typed tools. Reinspect
after configuration changes; evaluated unbaked work requires explicit
`reset_unbaked=true`, and baked work must be cleared before configuration edits.
`sample_rigid_bodies` steps sequentially and restores the user's frame; compare
evaluated matrices, not original transform channels, to assess the motion.
`bake_rigid_bodies` saves a full-scene `.blend` copy with embedded cache and pose
checkpoints. It preserves the active project path. Validate with
`validate_rigid_bake` after reopening; native baked/outdated flags alone do not
establish source compatibility. Sampling/baking are asynchronous by default and
report live storage; cancellation restores frame at boundaries, while final native
cache/save calls cannot be interrupted. `clear_rigid_bake` clears live state and
keeps saved files. This workflow does not yet convert physics motion to keyframes
or provide fluid caches; do not assume GLB exports cache animation.

For cloth, soft bodies or particles, first call `inspect_simulations` and pass its
`simulation_sha256` as `expected_simulation` on edits/sampling/baking. Configure a
dedicated static mesh with `configure_deform_simulation` (CLOTH or SOFT_BODY), or
`configure_particles` (Newtonian EMITTER or static HAIR). Cloth pin indices also
require `expected_topology` from mesh inspection. Pass `make_single_user=true`
when configuring shared deform mesh data or removing shared pin weights; linked
objects retain their original data. Use a separate static mesh with
`configure_collision`; `configure_force_field` creates an owned Empty helper.
Animated/deforming sources, mixed dynamic colliders, particle children, dynamic
hair and collection/texture dependencies are outside this workflow. Shared
particle settings need explicit `make_single_user=true` before changing them.

Use `sample_simulation` for bounded world-space mesh/particle readback; static
hair root/tip coordinates are in emitter object space. Sampling steps from the
cache start and restores the original frame. Configuration edits require explicit
`reset_unbaked=true` if evaluated caches exist, or clearing baked caches first.
`bake_simulation` saves a full-scene `.blend` copy with the selected embedded cache;
`validate_simulation_bake` checks source binding and bounded checkpoints after
reopening. Static hair needs ordinary project saving rather than a time bake.
`clear_simulation_cache` preserves saved snapshots; removal tools affect owned
controllers/helpers. Frame/cache budgets and free-space checks constrain work.
Watch tracked progress/storage and cancel at frame boundaries; native cache
finalization/save remain noninterruptible. Other point-cache disk backends, cache-to-
keyframe export and automatic deletion of explicit snapshots are not provided.

For fluids use `inspect_fluids` and `expected_fluid`, then typed
`configure_fluid_domain`, `configure_fluid_flow` and `configure_fluid_effector`.
Apply scale first; use one static-source domain without extra modifiers, parents,
animation, force fields or texture/group dependencies. `bake_fluid` writes a new
full-scene project/cache bundle in an isolated worker; default return is a tracked
job. Monitor storage/phase and cancel through operation tools. Cancellation stops
only its owned worker; partial files remain. Keep the entire bundle together.
Open `asset.blend` and run `validate_fluid_bake` to check hashes/source binding and
native geometry/density checkpoints. Cached projects are protected from authoring;
edit the unbaked `source.blend` and bake to a new directory instead. No gas volume
material preset or cache-to-game-animation conversion is implied by data baking.
After a parent crash, inspect/recover the job rather than replaying it. Recovery
requires both recorded processes gone and adopts a complete manifest or records
interruption; adopted output still needs native validation. Partial cleanup is
dry-run by default, protects successful/reference-bound output and requires
explicit inclusion for interrupted work.

Render a small preview frame sequence before committing to expensive output.
Prefer the named `animation_preview` action for PNG/video delivery without editing
the user's sequencer. Discover its schema with `describe_action` and validate with
`plan_action`. Inputs include frame_start/end, dimensions, camera, directory and
make_video (default true). Optional clips entries name kind SKELETAL or MORPH,
target name, clip and optional slot; both kinds can select slots of one combined
action. Choices restore original assignments, pose/weights, frame/subframe and
render settings after success, failure or cooperative cancellation. Existing output
directories are refused; partial files remain. Video requires consecutive frames,
even dimensions and FFmpeg. Use preview_setup for a persistent camera/light stage
and leave room for moving geometry; it does not refit across the animation.
run_action takes direct action/inputs/request_id/wait arguments. Its wait=true
result is a full operation record: check state, then steps[].result or partial_output.
Reuse the planned request ID for stable output paths. A timeout is still active
work. Named actions serialize their steps against other queued operations.

`render_animation` returns immediately by default and reports per-frame progress;
poll `get_operation`/`wait_operation`, then view its `preview_artifacts` with
`get_image`. Inspect beginning, middle and end frames. Use a stable request ID for
retry/reconnect recovery; do not replay an uncertain interrupted edit.

Check `storage_status` before long sequences and watch live storage fields while
rendering. Completed PNGs remain when a sequence stops. Queued work cancels
immediately, frame sequences cancel between frames, and Python can cooperate via
`check_cancelled()`. Native render/video calls are not forcibly interrupted.

An omitted output path/directory produces temporary output subject to retention
(seven days by default, with a 2 GiB target and one-hour minimum age). Use explicit
directories for deliverables or set_operation_retention to pin a generated output
group. Structured VSE input pins its source group; external editors/custom Python
need an explicit pin. Cleanup previews report candidates and protections; failed
or cancelled output can expire, while interrupted unknown-outcome work is protected.
details_pruned=true means history details expired, not permission to replay an edit.

Use `vse_add_strip`, `vse_edit_strip`, `vse_remove_strip` and `vse_list` to assemble
image/movie, sound and text strips when a video is requested. `render_video`
exports a tracked H.264/AAC MP4 from the sequencer. Verify actual encoded dimensions,
FPS/duration, frame count and audio with independent media inspection when available.
For game/simulation assets, preserve editable animation and export GLB with the
intended actions; verify playback and material/axis/scale behavior in the target
engine when in scope. Video export alone does not validate engine animation.
Select both the armature and meshes for GLB delivery. Managed clips are exported
for their own rig/shape-key data; unrelated actions are not broadcast automatically.
Slots in the same action merge into one named GLB animation. Check exported morph
targets and weight channels as well as joint animation. Imported files can contain
bone-display meshes; identify the actual morph mesh using shape-key counts or
inspection. Preserve
the `.blend`, inspect the GLB skin/clip contents and re-import when useful.

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
library loading or animated assembly export is implied. Static current-pose
mesh realization is available through `inspect_asset_realization` and
`realize_asset_instances`; this freezes animation and keeps materials shared.
Consult USER_MANUAL.md for ownership, dependency and guard limits.

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

After an interrupted LOD/package export, inspect `inspect_export_job` using the
original output directory. If it is unknown, start with bounded `list_export_jobs`
and inspect a selected summary for its file inventory. These broker tools work
with Blender closed. Carry the
fresh job guard to `recover_export_job`; it validates files without replaying scene
work. Ready staging can be explicitly published; incomplete staging can be previewed
with `cleanup_export_job`, then deleted with dry_run=false and a fresh guard.
Published output stays protected; discarding ready files needs discard_ready=true.
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

For an animation frame sequence across named cameras while editing continues,
prefer top-level render_camera_batch with frame_start/end/step and a fresh
inspect_render_pipeline guard. Poll its original operation; broker restart and
editor shutdown preserve handed-off workers. This produces PNG/optional multilayer
EXR, not encoded video. It uses a frozen packed-resource source snapshot; later
scene edits do not affect that job. See the render skill/manual for file-job
recovery and cleanup after an uncertain launch; never replay solely on timeout.

For managed vegetation motion preparation, inspect_botanical_wind defines a
seeded common world-metre field and source/settings guard. sample_botanical_wind
pages anchored hierarchical branch and rigid leaf/flutter poses at chosen seconds.
Inspect displacement, root/junction/length errors and the all-time rotation bound;
sampling leaves the native timeline/geometry unchanged. export_botanical_wind preserves explicit
waves, canonical hierarchy, placement and foliage attachments as guarded semantic
JSON. Keep it with the editable source; it does not create animated mesh output.

For native motion, inspect_botanical_wind_preview_source, then create with matching
options, expected_plan and a fresh preview_collection. Use returned objects for
setup_preview_stage; display_offset_m separates the copy while retaining the
original field placement. Poll the original operation. The bounded sampled shape
cache and shared instanced leaves survive .blend save/reopen without handlers.
Review key/midpoint pose errors, edge strain and actual frames; render inside its
baked range. Sampling frequency, instance, coordinate and work budgets can refuse
expensive/undersampled requests. Source/frame/selection stay preserved. Inspect
the preview for a fresh removal guard; foreign/shared dependencies block deletion.
Runtime wind attributes/GLB packing remain separate. See USER_MANUAL.md for timing,
native-main-thread cancellation, interpolation and recovery limits.

For portable botanical wind delivery, use inspect_botanical_export then
export_botanical_bundle with its expected_export guard, identical options and a
new directory. validate_botanical_bundle checks the saved files independently.
The format keeps the canonical wind solver/hierarchy, segment pivots, distinct
axis anchors and per-instance leaf rotation/phase/flutter; leaf template GLBs stay
shared. These are rest-geometry/semantic correspondence proofs, not an engine wind
shader or continuous-motion test. Use the existing sampled native wind preview
for Blender motion review, keep the .blend, and read USER_MANUAL.md for limits.

For static native LOD wind delivery, export_botanical_lods retains per-level
branch fields, shared leaf templates and canonical instance/hierarchy mappings.
Inspect the profile for expected_lods; SOURCE placement omits preview offsets,
DISPLAYED retains them. validate_botanical_lod_bundle revalidates independently
of Blender sources. These tools default async. Animated LOD playback and receiving
engine shaders still need separate qualification; see USER_MANUAL.md.
