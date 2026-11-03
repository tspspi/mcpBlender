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
saved input images and a clean low-target UV tile. The isolated worker preserves
the editing scene, producing PNGs plus a static current-frame PBR asset. Check
`projection.fraction`, map statistics and an actual render; a completed job is
not visual qualification. Masks detect geometry projection misses at the output
resolution. Tangent normals use positive Y; data maps are Non-Color, color maps
sRGB. Output is 8-bit PNG, not HDR or arbitrary shader-lobe equivalence. Alpha is
separate and AO does not account for cutouts. The output PBR material carries
glTF AO metadata. Reopen its asset and call `validate_texture_bake` before export.

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
