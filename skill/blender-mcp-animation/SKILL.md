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

Clips name the armature in `name` and the action in `clip`; tracks specify a
`bone`, `property` and vector `keyframes`. Bone `rotation_degrees` uses XYZ Euler
degrees relative to rest-bone axes, unlike object `set_keyframes` rotations in
radians. Clips persist while inactive. Duplicate clip names are refused; use
`set_pose_keyframes` to edit keys. Clip switching resets unkeyed channels to rest.
Ordinary single-action rigs and muted glTF NLA stashes are supported; constraints,
drivers and active NLA blending need another workflow. Imported ambiguous actions
require an explicit slot from `inspect_animation`.

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

Use `execute_code`, when allowed, for constraints, drivers, absolute shape keys, animation
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
