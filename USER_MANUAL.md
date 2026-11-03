# mcpBlender User Manual

Operator and MCP-client guidance for modeling, animation, rendering and asset
workflows. For installation and a quick start, see [README.md](README.md).
For permanent service setup, see [persistent installation](docs/DEPLOYMENT.md).
Tool arguments, policies, recovery behavior and workflow limits are documented
below; the repository-owned [skills](README.md#skills) provide task-specific agent
guidance.

## Installation

Requires Python 3.11+, Blender 4.5+ and a Unix system supporting same-user socket
peer checks (FreeBSD/macOS/BSD `getpeereid`, or Linux `SO_PEERCRED`). Live tests
currently cover the installed FreeBSD Blender 5.0.1; other versions are unqualified.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[remote,test]'
.venv/bin/mcpblender --config ./mcpblender.conf --init-config
```

For development with dependencies already available, every CLI example also works
as `python3 -m mcpblender.server ...` from this checkout. No installation into
Blender's Python environment is needed.

For a wheel-based permanent runtime, FreeBSD service supervision and client/skill
setup, see [persistent installation](docs/DEPLOYMENT.md).

## Reusable asset assemblies

Use `inspect_asset_assembly_source` with a closed set of local `objects`, including
parents, rig controls and objects referenced by constraints, drivers or material
nodes. Check `can_create` and resolve `blockers`. Pass its `source_sha256` as
`expected_source` to `create_asset_assembly`, plus a fresh `collection` name.
Creation defaults to a queued operation; use `wait_operation` for completion.
Progress reports free storage in the configured output filesystem and the native
transfer's temporary filesystem. The result includes a final `temporary_storage`
snapshot. The estimate is a heuristic, not a guaranteed allocation ceiling.

Creation copies native objects, data, materials and clips into a persistent,
initially unlinked collection. Parents and native references follow the copied
graph. `copied_objects` maps original names to new component names. Existing managed
nested prototypes remain shared. Source objects and their graph remain intact.
Origin defaults to `BOUNDS_BOTTOM`; alternatives are `BOUNDS_CENTER`,
`WORLD_ORIGIN`, or `CUSTOM` with a world-space `origin` vector.

Inspect with `inspect_asset_assembly`. Pass its `assembly_sha256` as
`expected_asset` to `place_asset_instance`, supplying a fresh object `name`,
`location`, `rotation_degrees` and `scale`. Placements share the prototype's data
and active animation. They do not have independent animation clocks. Negative
scale is supported; zero and near-zero scale are refused.

`set_asset_assembly_editing` takes the same guard and `enabled=true` to link the
prototype directly into the current scene. Edit its mapped components with the
ordinary structured geometry, shader, rig and animation tools; copied managed
clip, driver and NLA metadata follows the copied targets. Disable editing to
remove that direct scene link. This changes only the current scene's direct link;
existing placements remain. Reinspect after edits to obtain a fresh guard.
Membership changes, renaming/adopting/removing prototype components and general
rebuild management are separate workflows.

`inspect_asset_instance` reports evaluated viewport leaf transforms and world
bounds, with `leaf_offset`/`leaf_limit` paging and an `instance_sha256` guard.
`frame_objects` and `setup_preview_stage` accept managed placements for camera
framing. `remove_asset_instance` takes `expected_instance` and removes only that
placement; references from other objects/drivers and prototype membership block
removal. Save the scene normally to retain prototypes, placements and clips.

This workflow requires Object mode, local nonoverridden data and a closed native
graph. Scene/World dependencies and drivers requiring arbitrary Python are refused.
Limits include 128 direct members, eight nesting levels, 20,000 dependency IDs,
two million raw mesh vertices, four million shape-key entries, and two million
curve points in total (200,000 per action). Instance inspection caps evaluated
records at 2,048 and mesh vertices at two million. Guards cover the documented
current native state; image pixel buffers, external file contents and arbitrary
Python dependencies are not frozen. Native write/append calls are not interruptible;
cooperative cancellation and ordinary failure clean owned transfer data. External
linked-library loading, animated realization/export and independent
instance simulation are not covered by these prototype tools. Static mesh
realization is described below.

## Static assembly realization and mesh delivery

Use `inspect_asset_realization` with `instances` naming managed placements. It
snapshots nonempty visible evaluated mesh leaves, including nested placements and
procedural mesh instances, and returns `source_sha256`, counts, world bounds and
paged leaf records (`leaf_offset`/`leaf_limit`). Inspection cleans all temporary
meshes. Pass the guard as `expected_source` to `realize_asset_instances`, with a
fresh `collection` name, then wait for the queued operation.

The result contains the created `objects` and per-leaf source provenance. Each is
an independent static mesh with identity transform and geometry baked into world
space. This preserves affine placement including shear and mirrors; face winding
and transformed corner normals are handled explicitly. UVs, mesh attributes and
material assignments follow the evaluated mesh. Materials remain shared with the
prototype, so material edits affect both. Sources, selection and current frame
remain intact. These are current-viewport snapshots: rig deformation, shape keys
and modifiers are frozen into geometry; rigs, animation, lights and cameras are
not copied. Geometry vector attributes retain their native values rather than
being interpreted as world-space vectors. Shader coordinates, image pixels and
external files are not baked or made independent. Bake textures separately when
needed for material interchange.

The created objects can be edited normally and passed to `export_objects_glb`
with `animations=false`. Save the scene for editable delivery. GLB conversion
uses the existing exporter and its material/attribute limitations; static
realization does not promise preservation of arbitrary shaders or named attributes
in GLB. Dedicated validated multi-asset bundles remain separate.

The operation requires Object mode and finite invertible leaf transforms. Limits
are 128 input placements, 2,048 realized mesh leaves, two million total vertices
and eight million corners. Empty/armature/light/camera helpers are reported as
ignored; other nonmesh geometry refuses realization until converted. Mirrored
faces with repeated vertex indices are refused. Stale guards, name collisions,
ordinary errors and cooperative cancellation clean owned objects, collections and
meshes, including cancellation after linking the collection into the scene.
Source placements are never removed. Storage feedback accompanies queued progress;
this operation itself creates scene data rather than a new file.

## Collision and shadow proxies

For structured render visibility, inspect `inspect_render_visibility` by object
`name` and carry `visibility_sha256` as `expected_visibility` to
`configure_render_visibility`. Patch `hide_render` or individual Cycles ray flags:
`visible_camera`, `visible_diffuse`, `visible_glossy`, `visible_transmission`,
`visible_volume_scatter`, `visible_shadow`. Unspecified fields retain their values.
Stale guards and keyed/driven targeted fields refuse changes; cooperative
cancellation restores the patched fields. `hide_render` excludes the object from
rendering, while ray visibility flags are Cycles-specific. Configure the source's
`visible_shadow=false` before inspecting/generating its replacement proxy so the
proxy's source guard reflects that intentional configuration. Review actual
renders, including any instancing/material interactions.

Use `inspect_asset_proxy_source` with `objects` naming visible local mesh objects
or managed assembly placements. Inputs are evaluated at the current viewport
frame; source deformation and transforms are frozen in independent world-space
proxy meshes. Managed placements include nested and Geometry Nodes mesh leaves.
A direct mesh source needs a nonempty evaluated surface; use a managed placement
to include its un-realized procedural instances.

Choose `purpose` and `method` explicitly:

- `COLLISION` supports `BOX` or `CONVEX_HULL`. Boxes use world-axis-aligned bounds
  and optional nonnegative `padding`. Hulls use the native convex hull of input
  points; they do not perform convex decomposition. Both methods fill gaps and
  holes within each output group. Flat input can use a padded box; a hull requires
  a closed nondegenerate volume. Outputs have no source material dependencies,
  display as wire meshes and are hidden from renders.
- `SHADOW` requires `DECIMATE`, `grouping=PER_LEAF`, and a per-leaf
  `triangle_budget`. UVs, evaluated attributes and shared materials follow the
  source mesh. The output is a static, budgeted mesh configured for Cycles shadow
  rays only: camera, diffuse, glossy, transmission and volume-scatter visibility
  are disabled. Sources retain their visibility and shadow settings. Use `configure_render_visibility` to disable
  source shadow casting before generating a replacement proxy. Eevee and game
  engines require their own visibility/shadow integration; GLB does not encode
  these Cycles flags.

`grouping` defaults to `PER_LEAF`. `PER_SOURCE` combines the leaves of each named
input; `COMBINED` produces one collider for all inputs. A combined convex hull can
block an opening or fill the space between disconnected parts. For trees, select
appropriate trunk/branch components rather than enclosing all foliage and calling
that a trunk collider. These generic tools do not infer botanical structure.

Check `can_generate` and `blockers`, then carry `source_sha256` as
`expected_source` into `generate_asset_proxies`, with the same settings and a fresh
`collection` name. Generation is queued by default and reports progress/storage.
It verifies source freshness before publishing and cleans owned data on ordinary
errors or cooperative cancellation, including cancellation after scene linking.
Native hull/decimation calls cannot be interrupted mid-call.

Each output reports counts, world bounds and sampled bidirectional source/proxy
surface distances. `max_relative_error` is an optional rejection threshold,
normalized by the source group's bounding diagonal. Samples include each leaf;
this is not an exhaustive Hausdorff, silhouette, alpha-coverage or collision
quality bound. Collision outputs additionally require closed manifold geometry
and positive volume. `max_sampled_outside_distance` is meaningful for outward
convex proxies; it is not a signed-distance guarantee for concave shadow meshes.

`inspect_asset_proxies` reports the current `proxy_sha256`, paged members
(`offset`/`limit`), stored quality evidence, current geometry/placement/visibility
issues and separate `source_matches` freshness. A source change can leave the
static proxy internally valid while making it stale. Geometry checks do not
certify a simulation or target engine. Collision members include a
`suggested_collision_shape`; attach a passive rigid body explicitly using the
physics tools when appropriate. No physics world or body is created automatically.
The structured fixture qualifies passive building colliders; arbitrary active
body inertia and collision behavior need separate review.

Use normal scene saving and explicit mesh export for delivery. Shadow materials
remain shared, shader coordinates/images are not baked, and portable shading
requires appropriate supported materials or texture baking. These tools do not
automatically associate exported colliders or shadow meshes with engine assets.

`remove_asset_proxies` takes `expected_proxy` from a fresh inspection. It removes
the owned collection and objects, retains sources/materials and preserves mesh
data still used elsewhere. It refuses changed membership, external references,
foreign object collection links, and attached rigid bodies. Detach physics first
so cache policy remains explicit. Changed source freshness does not prevent
removing an obsolete owned proxy.

Limits: 64 named inputs, 2,048 evaluated leaves, two million total vertices,
eight million corners, at most 256 outputs, and 200,000 input vertices per convex
hull group. Shadow budgets range from 4 to 500,000 triangles per leaf. Sample
counts range from 32 to 2,048 per target/group, with at least eight source samples
per constituent leaf. Point/curve/volume geometry requires conversion first.

## Batch asset packages and dependency validation

`inspect_asset_package` accepts up to 32 named `assets`. Each entry has a portable
ASCII `id` (1..48 letters/digits/underscores/hyphens, starting with a letter or
digit) and `objects` naming local mesh objects or managed assembly placements.
IDs must be distinct ignoring case. Example:

```json
{
  "assets": [
    {"id": "building", "objects": ["BuildingOne"],
     "collision_proxies": ["BuildingCollision"]},
    {"id": "prop", "objects": ["Prop"],
     "shadow_proxies": ["PropShadow"],
     "lods": [{"chain": "PropLOD", "animations": false}]}
  ]
}
```

Optional `collision_proxies` and `shadow_proxies` name owned proxy collections
(up to eight of each per asset). They must be valid, fresh, match the declared
role, and have source objects drawn from that asset's inputs. Optional `lods`
contains up to four native chain selections. A chain must be valid and fresh and
its source must be an asset input. Its existing export profile must permit the
requested options. `animations` defaults to true; morph chains can specify named
`timeline_clips` as in `export_lod_chain`. `animation_samples` (3..9, default 3)
and `skin_tolerance` (default 0.001) use that exporter's native/file proof rules.
Inactive compatible clips participate in the package guard as well as current
geometry; an inactive clip change therefore requires a new plan.

Check `can_export`, `blockers`, dependency inventory and warnings. Carry
`source_sha256` as `expected_source` into `export_asset_package`, with identical
`assets` and a fresh library-relative `directory`. The operation defaults to a
queued job. Estimates include mesh geometry and loaded texture pixel sizes, with
current free-space checks and progress snapshots. Estimates remain heuristic.

The package contains one `primary.glb` per asset, separate collision/shadow GLBs,
optional nested LOD bundles and a root `manifest.json`. Proxy mappings identify each
exported mesh node and retain its original proxy name, method, suggested collision
shape, volume and sampled quality evidence, with independent per-node geometry
proofs. This preserves the information needed for later engine adapters. Primary and proxy geometry
is prepared as independent current-viewport world-space mesh snapshots: evaluated
modifiers, rigs and shape keys freeze into geometry with identity object transforms.
Sources and shared materials remain intact. To deliver a chosen asset pivot/origin,
prepare its source/placement at the desired origin before inspection. Animation
is retained only through the nested LOD export profiles; this is not general
animated assembly export. Cycles shadow visibility and engine collision behavior
are recorded roles requiring downstream integration, not portable GLB behavior.

Export uses a temporary scene with native window-scene activation restored after
each export. Named-object GLB export is limited to the active scene, preventing
selections in other scenes from entering the file. Package publication occurs
only after all members validate, using a staged sibling directory and a final
rename. Existing output directories are refused. Ordinary errors/cooperative
cancellation remove owned scene data and staging, including cancellation at the
final validation boundary. Native export calls cannot be interrupted mid-call;
interrupted-process staging reconciliation remains separate.

`validate_asset_package` checks the complete relative file inventory, hashes,
roles/associations, native/file triangle counts and world bounds, and an independent
fingerprint of every oriented triangle (32-bit world positions, cyclic starting
corner/primitive ordering ignored). It decodes node hierarchy/transforms, validates
positions/normals/UV references and embedded image/texture/material references,
and revalidates nested LOD manifests and association guards. Extra files, symlinks,
unsafe paths, stale native associations at export and mismatched proofs refuse.
The standalone `mcpblender.package_files.validate` uses only the Python standard
library and does not require Blender.

Material dependencies are conservatively inventoried from the referenced native
graph, including unused image nodes. FILE/GENERATED images need loaded finite
pixels; unpacked FILE images also need an available file. Guards include loaded
pixel and external-file hashes, shader state and image color space. Script shaders,
scene-object/context material dependencies and volume delivery require a separate
baking/workflow step. Manifests include names and hashes without absolute source
path fields. Image limits are 64 million float components per image and one GiB
of loaded dependency pixels per member inspection. File/image guards do not make
arbitrary shaders portable: review GLB material conversion and bake unsupported
procedural effects before delivery.

The decoder is a bounded native-export profile, not a general glTF conformance
validator. Static members require one scene, dense nonnormalized attributes,
uncompressed triangles, finite transforms, unit normals and supported material
extensions. It rejects unused/unreachable mesh nodes. PNG validation checks chunks,
CRCs and decompressed non-interlaced scanline layout; JPEG validation checks marker
and segment structure without decoding entropy. Other texture encodings require
conversion. Per-file limits include 512 MiB, 2,048 meshes, 4,096 nodes, depth 64,
two million elements per accessor and four million instantiated triangles. Package
inventory is capped at 2,048 files. Rendered shading, alpha coverage, collisions,
physics and target-engine behavior still need their own qualification.

## Blender startup and attachment

`get_capabilities` reports the connected Blender version and worker command
inventory. Its `domain_support` entries distinguish `structured_partial` (listed
typed commands with an explicit scope) from `python_only` (no dedicated typed
workflow). `python_only_domains` summarizes the latter. A domain name alone does
not imply full Blender support, installed optional APIs or permission to execute
Python. Use MCP `tools/list` for the current connection's permitted tools, and
[VALIDATION.md](VALIDATION.md) for tested versions and scenarios. Discovery itself
does not establish qualification or create a recovery checkpoint.

The MCP server can start Blender through `start_blender`. With
`launch.auto_start=true` (the default), the first operation needing Blender also
starts it lazily when its key has startup permission. Set this false for explicit
startup only. Operation-history and storage queries never require Blender startup. Default startup creates a fresh GUI
instance with factory settings, auto-execution disabled, and our bridge bootstrapped.
The bootstrap disables the splash screen for that session without saving user preferences.
It does not modify Blender preferences or install files into Blender. The GUI has
an **MCP** sidebar panel with bridge start/stop controls.

For a CLI launch before connecting an agent:

```sh
mcpblender --config ./mcpblender.conf --start-blender
```

For a headless session, add `--background` or set `launch.background` in JSON.
Background mode stays alive to accept commands, supports camera rendering, and
cannot capture a GUI viewport. Startup reports readiness only after a round trip
through the socket and confirmation of the launched Blender PID. A live socket is
reused; a busy bridge does not trigger another launch. A launch file lock coordinates
multiple server processes using the same socket.

To attach to an existing GUI without restarting it, use Blender's Python console:

```python
import sys
sys.path.insert(0, "/absolute/path/to/mcpBlender")
from mcpblender.blender import bridge
bridge.start("/absolute/private/directory/bridge.sock")
```

Use the same `bridge.socket_path` in server configuration. `bridge.stop()` detaches.
For optional persistent add-on installation, generate a ZIP and install it through
Blender's **Preferences → Add-ons → Install from Disk**:

```sh
mcpblender --addon-zip /tmp/mcpblender-addon.zip
```

Enable **mcpBlender Unix Bridge**. It uses the default socket unless the Blender
process has `MCPBLENDER_BRIDGE_SOCKET` set. An add-on installation is unnecessary
when starting Blender through the MCP server. Do not enable the installed add-on
and separately register the checkout's UI module in the same session.

## Temporary outputs and retention

Temporary-output retention is enabled by default for callers with library-write
permission. After a successful submission, bounded background maintenance runs
opportunistically, at most once per hour per owner/library (not as a periodic
service when the server is unused). Defaults retain temporary outputs for seven
days, keep at least one hour of recent output, and target a 2 GiB temporary-output
budget. History details expire after 30 days. Configure these under `retention`;
set `enabled=false` to disable automatic maintenance while keeping preview/manual
cleanup available.

Only automatically generated render/screenshot/video paths and generated frame
directories are registered as temporary. Explicit output paths, saved projects,
exports, unregistered legacy files, recovery checkpoints and logs are excluded.
Within generated frame directories, only expected frame, manifest and preview
video filenames are candidates; other files remain. Pins, active/interrupted
operations, symlinks and files modified after operation completion are protected.
Structured use of a temporary output as a material/VSE/import/upload input pins
its output group; that pin stays until explicitly removed. Pin outputs before
custom Python or external software uses them, because those dependencies cannot
be inferred. Saved `.blend` files do not automatically reveal external dependencies.

Use `retention_status`, then `preview_retention_cleanup` to inspect candidate files,
logical bytes, protected groups and history entries. Apply the ten-minute plan
with `apply_retention_cleanup(plan_id=...)`; permissions, pins, file identity and
policy are rechecked before deletion. `set_operation_retention(operation_id=...,
pinned=true)` protects outputs and history, including history for explicit-path
deliverables. Applying cleanup and pin changes require library-write permission.
These tools do not start Blender. Scans and deletion batches are bounded; a
truncated scan reports a lower bound and the budget may remain unmet.

History cleanup drops bulky parameters/results/progress, preserving operation IDs,
request IDs, digests and final states. `details_pruned=true` means the old result is
unavailable; reusing its request ID still returns the original operation and never
re-executes it. SQLite can reuse the freed pages; databases are not automatically
vacuumed and small request-ID tombstones are retained. Expired artifact metadata
is removed when its file is missing. Cleanup reports logical bytes deleted and
fresh filesystem space; filesystem snapshots can retain physical storage.

## Structured shaders and material presets

Structured shader authoring works with Python execution disabled. Use
`shader_node_catalog` to discover supported node types, installed socket identifiers
and property choices; `inspect_shader_graph` inspects existing materials, including
imported node types. Domain-tool arguments go inside `params`.

`configure_shader_graph` creates a complete graph from `material`, `nodes` and
`links`; replacing an existing material requires `replace=true`. Nodes have a
unique `name`, supported Blender node `type`, typed input socket values, optional
properties, and image/color-ramp options. Links name their source/destination node
and socket. Use identifiers or indexes when socket display names are ambiguous.
Script nodes and arbitrary RNA properties are excluded. Image paths stay inside
the caller's library. Socket types/ranges, link destinations and cycles are checked
on a temporary material before applying changes; rare failures during application
can still leave partial edits. Animated/driven or linked materials are refused.

For incremental editing, use `configure_shader_node`, `connect_shader_nodes`,
`disconnect_shader_input` and `remove_shader_node`. Omitted inputs/properties are
preserved; existing input connections need `replace_existing=true` to replace.
`apply_material_preset` creates `PBR`, `TEXTURED_PBR`, `GLASS`, `EMISSION`,
`VOLUME`, `SMOKE` or `FIRE` graphs.
PBR presets accept base-color, roughness, metallic and tangent-space normal maps,
texture scaling and image packing. Base color uses sRGB; data maps use Non-Color.
Roughness/metallic maps use their red channel. Existing materials require explicit
replacement. Assign the result using `assign_material`. These presets provide
Blender shading; arbitrary procedural graphs and glass need target-engine review
or baking before delivery. The GLB qualification covers the textured PBR preset.

Volume presets connect Principled Volume to the material's Volume output.
`VOLUME` uses a constant density; `SMOKE` reads the native `density` grid; `FIRE`
also reads `temperature` and multiplies the flame grid by `blackbody_intensity`.
Controls include `volume_density`, `anisotropy`, `volume_emission_strength`,
`emission_color` and `temperature_scale` (the multiplier for a temperature grid).
The shader catalog includes Principled Volume, Volume Info and Attribute nodes;
string sockets allow explicit grid names. Assign these materials to a closed
mesh or gas domain with `assign_material`. Texture-map inputs belong to PBR presets.
`asset_report` warns that volume materials need a separate target-engine workflow.

Cached gas shading also depends on the Blender build. In Blender 5.0.1, Cycles'
[volume loader](https://github.com/blender/blender/blob/v5.0.1/intern/cycles/scene/image_vdb.cpp)
requires NanoVDB; OpenVDB cache loading alone does not prove rendering support.
The tested FreeBSD build has NanoVDB disabled: caches contain nonzero density,
but smoke/fire renders are empty. Homogeneous mesh-volume rendering and shader
round-trips pass; cached smoke/fire appearance is **not qualified on that build**.


## Compositing, render passes and color management

Structured compositor authoring uses the Blender 5 `compositing_node_group` API.
Use `compositor_node_catalog` for the allowlisted node types, then request a
`node_type` for installed socket identifiers, component counts, menu choices and
editable properties. Several Blender 5 controls are menu sockets rather than
legacy node properties. For example, glare `Type` accepts `Fog Glow`; blur `Size`
is a two-component vector. Apply menu defaults before dependent input defaults.
Identifiers resolve ambiguous display names; socket indexes are also accepted.

`configure_compositor_graph` creates a persistent named `group` from `nodes` and
`links`. Each node has a unique `name`, allowlisted `type`, optional `label`,
`inputs` (`socket`/`value` pairs) and supported `properties`. Color/value constants
accept `output_value`; color ramps accept ordered `ramp` stops. Exactly one
`NodeGroupOutput` is required. Its Image socket is supplied automatically by the
managed interface and must be linked. File-output, script, external-image and
nested group nodes are outside this authoring profile.

```json
{
  "group": "PreviewPost",
  "nodes": [
    {"name": "Layers", "type": "CompositorNodeRLayers"},
    {"name": "Exposure", "type": "CompositorNodeExposure",
     "inputs": [{"socket": "Exposure", "value": 0.5}]},
    {"name": "Output", "type": "NodeGroupOutput"}
  ],
  "links": [
    {"from_node": "Layers", "from_socket": "Image",
     "to_node": "Exposure", "to_socket": "Image"},
    {"from_node": "Exposure", "from_socket": "Image",
     "to_node": "Output", "to_socket": "Image"}
  ]
}
```

Supported nodes include denoise, glare, blur, color balance, exposure,
brightness/contrast, hue/saturation, alpha-over/set-alpha, masks, transforms,
scaling, depth combination, channel separation/combination, lens distortion and
numeric/vector math, mixing and ramps. Not every node/mode has a rendered fixture;
use a small preview to inspect the result. Socket/type/range checks, missing socket
references or Image output links, cycles and disabled-pass links are validated
before publication.
Limits are 128 nodes and 256 links. Numeric/vector defaults must fit native limits;
menu strings must be installed choices. Implicit Blender socket conversions are
permitted when the native link is valid.

A Render Layers node binds explicitly to the scene current at graph creation.
Its optional `view_layer` defaults to the current view layer. Inspection reports
that source scene/layer. Sharing the graph with another scene preserves this
binding; it does not reinterpret the source as whichever scene later renders.

`inspect_compositor_graph` reports nodes, socket defaults/availability, links,
interface and native users. `graph_sha256` guards complete supported unanimated
graphs; large, unsupported or animated graphs have no complete fingerprint.
Unmanaged/imported graphs are inspect-only. Replacement requires `replace=true`
and a fresh `expected_graph`. Multiple scene users require `allow_shared=true`.
Nested/non-scene or linked/overridden users block replacement. Direct native edits,
including mute or property changes, invalidate the guard. Tree animation and
scene-owned animation through the compositor pointer prevent replacement.

Replacement stages a complete new graph, validates it, then remaps local scene
bindings and hands over the public name. Ordinary failure/cooperative cancellation
before final deletion restores original IDs, names and bindings. The final native
deletion is noninterruptible; process-crash rollback at handoff is not qualified.
New named groups persist with fake users; staging failures remove their scratch
data. Creating a graph does not attach it or render an image automatically.

Call `inspect_render_pipeline` for current scene binding, engine, view-layer pass
flags and scalar color settings. Its `settings_sha256` covers those settings,
not scene geometry, custom color curves, animation or external OCIO file contents.
`color_choices` reports installed display/view transforms and looks for the current
view. Look choices can change after choosing another view transform.

`configure_compositing` takes `expected_settings`, optional `group` and its fresh
`expected_graph`, plus `enabled` (default true). Enabling requires a valid managed
local unanimated graph. Without `group`, the existing binding remains; this also
allows disabling an imported compositor. `render_still`, `render_animation` and
existing preview workflows use the bound scene compositor through native rendering.
The structured tools add no secondary file-output nodes or untracked output paths.

`configure_render_passes` takes `expected_settings`, optional `view_layer` and a
`passes` patch. Available keys include `z`, `normal`, `position`, `vector`, `uv`,
`mist`, object/material indices, emission/environment, diffuse/glossy/transmission
components and `denoising_data`. Combined output remains enabled. Cycles auxiliary
denoising passes need the Cycles engine; inspect Render Layers outputs after the
change. Enabling a flag does not guarantee every engine produces that pass.
Pass changes refresh sockets and refuse disabling a pass consumed by an enabled
managed scene compositor referencing that layer. Cancellation or validation failure
restores the old flags. This controls native pass settings; the independent batch workflow below delivers
optional multilayer EXRs. AOV/Cryptomatte setup and mask-index assignment remain
separate.

`configure_color_management` takes `expected_settings` and any of `display_device`,
`view_transform`, `look`, `exposure`, `gamma`, `use_white_balance`,
`white_balance_temperature` and `white_balance_tint`. Values are preflighted on an
owned scene copy against the installed configuration before applying the patch.
Targeted keyed/driven settings are refused. Display/view/look are applied in that
order; native dependent defaults may change when a display/view changes. Supply
an explicit look when required. Failure or cooperative cancellation restores the
original scalar settings. Custom color curves and OCIO configuration-file editing
remain separate. These operations change scene setup; ordinary render capture
continues to restore its temporary resolution/path/engine/camera settings.

## Independent render workers and camera batches

`render_camera_batch` snapshots the current project, starts a separate owned
Blender process and hands the original durable operation to the broker. The
editing instance becomes available after snapshot/launch; the render operation
remains running until its files are independently checked. Use ordinary
`get_operation`/`wait_operation` and `cancel_operation`, not a second job-submission
loop. Request-ID deduplication still applies. Do not replay a batch after a wait
timeout. The operation's progress includes `render_job_id`, directory, worker PID
(for diagnostics), camera/frame, completed render count, bytes and fresh storage.
Native render stats are included when the renderer emits them.

The tool requires snapshot, library-write and application-start permissions.
Call `inspect_render_pipeline` first and carry `settings_sha256` as
`expected_settings`. This guards pipeline settings, not all scene geometry. The
saved `source.blend` SHA-256 is the authoritative binding of the scene actually
rendered. Editing after the snapshot does not update that batch.

```json
{
  "directory": "renders/asset-review-01",
  "expected_settings": "<settings_sha256>",
  "cameras": ["StudioCamera", "DetailCamera"],
  "frame_start": 1,
  "frame_end": 24,
  "frame_step": 4,
  "width": 640,
  "height": 480,
  "engine": "CYCLES",
  "samples": 32,
  "formats": ["PNG", "OPEN_EXR_MULTILAYER"],
  "threads": 2,
  "max_bytes": 4294967296,
  "timeout_seconds": 3600
}
```

The directory must be new. Batches support 1..16 distinct cameras and up to 1000
camera/frame renders, with explicit frame steps, 16..4096px dimensions and 1..16
CPU threads. Up to two workers can run per bridge; inherited OS slot locks keep
the limit across broker/editor restarts. A third launch refuses before creating
its output directory. There is no render farm or GPU scheduler. Cycles CPU is
qualified; the Eevee request surface exists but headless graphics availability
and output are not established by the Cycles fixture.

Each camera/frame is rendered once. Optional formats are saved from that result:
16-bit RGBA PNG and 32-bit multilayer EXR. Blender 5 uses the
`MULTI_LAYER_IMAGE` media type and may write scanline multipart EXRs. The manifest
records each file's camera/frame/format, dimensions, SHA-256 and EXR part/channel
inventory. Filenames use camera/frame indexes (`outputs/c00_f0000.png`), while
actual names and frame numbers remain in the manifest. Depth/normal and other
native passes follow the snapshot's configured view layers. Compositing is
preserved. VSE output and crop borders are disabled in the worker; this is a
full-frame scene-camera batch, not sequencer rendering or video encoding.

The initial source profile requires packed/self-contained render resources.
Unpacked or pixel-dirty images (including generated images), unpacked fonts/sounds,
linked libraries, movie clips, external mesh caches,
fluid modifiers and volume objects refuse rather than silently reading mutable
external inputs. Default weak brush-asset references are editing metadata and do
not count as render resources. File-output/external-image compositor nodes refuse;
active compositing must pass the supported graph checks. Script auto-execution
is disabled in the worker. External-cache freezing, arbitrary script-dependent
projects and solver/physics reproducibility need separate qualification. Source
saving/loading remain native blocking boundaries.

The worker is independent of the editing process and broker. Broker restart
resumes observation of the same delegated operation; editor shutdown/replacement
does not interrupt it. Cancellation writes a job-bound request, and the worker's
own watchdog stops that process, including during tested native rendering. No
stored PID is blindly signalled by production cleanup/recovery code. Timeouts,
free-space/reserve checks and a byte watchdog preserve partial files on failure.
The snapshot estimate is a geometry/image/pass heuristic; polling limits are not
filesystem quotas and can overshoot between checks. Snapshot writing itself is
not forcibly interruptible. A completed result must still fit `max_bytes`.

File tools work with Blender closed:

- `inspect_render_job` reports this MCP owner's job, writer lock, status, bounded
  inventory/free storage and `job_sha256`.
- `validate_render_job` re-reads source/output hashes, exact camera/frame/format
  associations, PNG dimensions and EXR part/channel headers. It reports progress
  and supports cancellation during file hashing. It does not decode every pixel,
  certify visual quality or prove radiometric accuracy. Deep/tiled EXRs and more
  than 32 parts/512 channels are outside the header profile.
- `recover_render_job` requires `expected_job` and no live writer. It adopts a
  complete valid manifest or marks partial output interrupted, without rendering
  again. The original interrupted operation history remains interrupted; recovery
  is a separate explicit file reconciliation.
- `cleanup_render_job` defaults to `dry_run=true`. A fresh `expected_job` is
  required to remove idle owned failed/cancelled partial bundles. Interrupted
  inclusion requires `include_interrupted=true`. Successful bundles, live writers,
  symlinks/unknown entries and current/queued structured references are protected.
  Cleanup/recovery serialize with the writer lock and verify directory/file
  identity. Arbitrary external Python references cannot be inferred.

The directory retains its source snapshot, job/status metadata, worker log and
manifest as provenance. It is an explicit deliverable, not an automatically
expiring temporary output. There is a launch-to-broker-handoff crash window: if
an editor dies after starting a child but before acknowledging delegation, the
original operation can remain interrupted while the file job continues. Inspect
the recorded directory; do not resubmit or guess that no rendering occurred.
Snapshot-stage failures similarly leave an owned partial directory for inspection.

Use this command as a top-level tracked operation. Named-action steps cannot
implicitly delegate the enclosing action's completion; batch embedding is refused.
Existing connected-instance render/animation/video tools retain their behavior.

## Named actions and local recipes

The built-in `preview_setup` action accepts `objects` (mesh names), an optional
fresh `prefix`, `view`, `projection`, `margin` and light `strength`. It creates
persistent key/fill/rim area lights centered on evaluated asset bounds and a fitted
active camera. Existing lights remain; render settings and selection are preserved.
Fit uses the current frame and render aspect: refit after pose or aspect changes.
For example, run `preview_setup` with `{"objects": ["Building"], "prefix": "Studio"}`,
then render with camera `Studio_Camera`. Resource-name collisions are refused
before editing; setup errors remove resources created by the shim and restore the
previous active camera. This action requires scene-edit permission.

`game_asset_prepare` takes `objects` (up to 16 meshes) and an optional
`triangle_budget`. Its default plan only preflights and reports evaluated geometry,
UVs, material slots, transforms and budget warnings. This remains discoverable to
read-only callers and does not create recovery checkpoints. To request edits, set
`apply_rotation_scale`, `generate_uv` or `triangulate` explicitly; triangulation adds
a live `MCP_GameTriangulate` modifier. Shared geometry requires `make_single_user`
for destructive mesh edits. Existing UVMap data requires `overwrite_uv=true`.
All targets are checked before editing. Optional `save_path` and `export_path`
write a project and GLB inside the library without overwriting existing files.
Export includes only the named meshes and restores the user's selection. The
editing/export workflow refuses skinned and shape-key meshes; use the qualified
rig/morph delivery tools for those. Reports are advisory and do not certify Godot
compatibility, texture fidelity or collision suitability. Optional steps require
their own permissions; `describe_action` lists possible and required commands.

`animation_preview` takes `frame_start`, `frame_end`, an optional fresh output
`directory`, `width`, `height`, `engine`, `camera` and `make_video` (default true).
By default it renders the current scene animation. Optional `clips` choose temporary
skeletal or morph actions, for example:

```json
{"frame_start": 1, "frame_end": 24, "camera": "Studio_Camera",
 "clips": [{"kind": "SKELETAL", "name": "Rig", "clip": "Walk"},
           {"kind": "MORPH", "name": "Body", "clip": "Walk"}]}
```

Each target accepts an optional `slot` for imported actions with ambiguous slots.
Clip selection follows the existing rig/morph restrictions (no constraints,
drivers or active NLA blending). The camera is not refitted per frame: allow room
for motion. The shim restores original clips/slots, pose, morph weights, frame and
subframe, camera and render settings on success, failure and cooperative
cancellation. PNG rendering bypasses the user's VSE timeline; MP4 assembly uses a
temporary VSE scene which is then removed. Existing scene contents and compositor
remain relevant to rendered frames. Video requires FFmpeg support, even dimensions
and consecutive frames; `make_video=false` allows a `frame_step` greater than one.

Outputs are `frame-*.png`, `manifest.json` and optional `preview.mp4` inside the new
directory. Operation results expose video/manifest and sample-frame artifacts;
failure/cancellation reports include available partial frames. The storage estimate
covers both PNGs and video, with free-space reporting during progress. Existing
directories are refused. Files remain after failure/cancellation; restoration does
not imply rollback after a process crash. Encoding retains native Blender blocking
and cancellation limits. Snapshot permission is required; a recovery checkpoint
may be saved before rendering a dirty scene, using the ordinary render policy.

The action engine also supports operator-defined JSON recipes.
Add `"action_files": ["actions.json"]` to the server
configuration; relative paths resolve beside that configuration file. Restart
the MCP frontend after changing a recipe. For example:

```json
{
  "format_version": 1,
  "actions": [{
    "name": "custom.make_prop",
    "version": "1",
    "description": "Create and inspect a named prop.",
    "inputs": {
      "name": {"type": "string", "description": "Unique object name."}
    },
    "steps": [
      {"id": "create", "command": "create_primitive", "params": {"name": {"$input": "name"}}},
      {"id": "inspect", "command": "inspect_mesh", "params": {"name": {"$input": "name"}}}
    ]
  }]
}
```

Use `list_actions`, then `describe_action` for the input schema, definition digest
and required capabilities. `plan_action` validates all inputs, step parameters,
permissions and library paths without starting Blender or editing the scene;
preparing output paths can create parent directories. Pass its `request_id` and
the same inputs to `run_action` for matching generated output paths. Request IDs
retain the usual operation deduplication rules; changed definitions or inputs
cannot silently reuse a different operation.

`run_action` defaults to asynchronous submission. With `wait=true`, it returns the
complete operation record, including failed or cancelled state and partial results.
Validation and permission errors are raised before submission. Steps execute
serially within one tracked operation. Progress includes completed steps, nested
operation progress and fresh storage reports. Known output estimates are summed;
some steps have unknown storage requirements. Each step also checks its storage
policy before execution. Completed output artifacts and available partial render
frames remain inspectable through operation status.

Recipes allow 1–64 steps and whole-value `{"$input": "name"}` references, including
inside lists and objects. Inputs support strings, integers, numbers, booleans,
string lists, three-component vectors and RGBA colors. They are strictly typed;
optional inputs require explicit defaults. Expressions, Python execution, nested
actions, project reloads, process lifecycle and network/API operations are excluded.
Every emitted constituent command must be permitted by the caller's policy.

Actions have no rollback: a failed or cooperatively cancelled step can leave scene
edits and files. Native blocking Blender calls retain their existing cancellation
limits. A frontend reconnect can retrieve the original operation by request ID;
interrupted operations are not automatically replayed or resumed step by step.
Live actions also retain their iterator across broker restarts. Transient progress
connection failures reconnect and retry the progress update with a bounded retry;
they do not dispatch the scene edit again. Application exit records an unknown
outcome and restores the last completed checkpoint when recovery is requested.
Inspect that recovered scene before deciding on a new operation.

## Configuration

See [examples/mcpblender.conf](examples/mcpblender.conf). JSON is the configuration
source. Paths beginning with `~` are expanded. Relative file tool paths are relative
to the active policy's `library_root`.

The default bridge socket is `~/.local/state/mcpblender/bridge.sock`. Its immediate
parent must belong to the current user with mode `0700`; the socket is `0600`.
All socket peers verify UID. A separate stdlib-only broker owns the socket and
durable SQLite operation journal; the Blender main-thread worker claims one
operation at a time. This keeps status/progress queries responsive during native
Blender work. The bridge has no network listener or remote API key.
Existing live sockets and non-socket files are preserved; owned stale sockets may
be replaced. This bridge controls one shared Blender session: different remote
keys do not get separate scenes or OS accounts.

`launch.executable`, `launch.background`, `launch.factory_startup`,
`launch.startup_timeout_seconds` and `launch.log_path` configure startup. Blender
continues running after ordinary client/server disconnects. Use `shutdown_blender`
for graceful shutdown. It refuses a dirty project unless a save path or explicit
discard is supplied, and disables automatic restart for that intentional shutdown.
`launch.shutdown_on_exit=true` opts a launching frontend into checkpoint-and-quit
on exit; this defaults false to support multiple independent connections.

`bridge.timeout_seconds` bounds the server's wait for a response. A timeout or
disconnect does **not** cancel queued or running Blender code, undo edits, or stop
a render. Inspect the session and log before retrying a mutation.

## Authentication and transports

The remote authentication formats and Argon2id KDF fields match mcpFreeCAD:

- `Authorization: Bearer <key>`
- `X-API-Key: <key>`
- `?mcp=<key>`
- `?api_key=<key>`

Precedence follows that order. Generate or rotate a named key with:

```sh
mcpblender --config ./mcpblender.conf --genkey design-agent
```

The key is printed once. Only its salted Argon2id hash is stored in the private
configuration file. Rotation preserves an existing key's policy. New keys inherit
the policy model defaults; edit their `library_root` and flags before remote use.
The configuration is loaded at startup; restart the MCP server after key rotation
or policy changes. This leaves Blender running.

```sh
mcpblender --config ./mcpblender.conf --transport stdio
mcpblender --config ./mcpblender.conf --transport remotehttp
```

`--remote` is an alias for selecting remote HTTP. Remote mode refuses to start
without an API key. `/status` is a public server liveness check and does not prove
Blender connectivity; use authenticated `bridge_status` for that.

Example internal client configurations (substitute real paths and issued keys):

```json
{
  "mcpServers": {
    "blender-local": {
      "command": "/absolute/path/to/.venv/bin/mcpblender",
      "args": ["--config", "/absolute/path/to/mcpblender.conf", "--transport", "stdio"]
    },
    "blender-remote": {
      "url": "https://mcp.example.com/blender/mcp/?mcp=ISSUED_KEY"
    }
  }
}
```

Stdio uses the `stdio` policy block, needs no remote API key, and keeps stdout
reserved for MCP. Both transports use the same Blender Unix socket.

HTTP can listen on loopback TCP or a Unix socket (`remote_server.uds` takes
precedence over host/port). For HTTPS behind Apache, see
[examples/apache.conf](examples/apache.conf). The URL key is intentionally
supported. Application access logging is disabled to avoid recording query keys;
configure the proxy access log with `%U` rather than `%r` or `%q`. Do not turn on
request URL debug logging. `remote_server.url_prefix` is the externally visible
base URL including the proxy path, used to construct artifact links.

## Policies, images and jobs

Each API key, and the stdio block, has these flags:

| Flag | Controls |
| --- | --- |
| `allow_code_execution` | Arbitrary Python execution |
| `allow_scene_edit` | Python, selection, transforms, frame changes, project open, asset import |
| `allow_library_write` | Project saves and GLB exports |
| `allow_snapshots` | Viewport images, camera renders and image retrieval |
| `allow_start_blender` | Explicit/lazy process startup and bridge restart |
| `allow_shutdown_blender` | Graceful application shutdown |
| `allow_external_assets` | Configured asset/API sources |
| `enable_autonomous_execution` | Advisory policy surfaced for orchestrators |

Disabled operations are hidden from tool discovery and denied on direct calls.
The autonomy flag is advisory, as in FreeCAD; the server adds no approval workflow.
Structured file tools resolve paths and reject traversal and symlink escapes from
`library_root`. Arbitrary Python has Blender's full OS permissions, so these roots
and per-key flags are not a Python sandbox. API keys share the same Blender scene.
Blender may also resolve linked dependencies of imported assets or projects;
the structured path check constrains the entry file, not Blender's internal reads.

`capture_viewport` returns an artifact identifier; `get_image` returns that image
as MCP image content. `render_still` returns a job identifier immediately; poll
`get_job`, then call `get_image` with the completed result's `artifact_id`.
Job state tracks durable broker operations; frame sequences and video encoding
report completed-frame progress. A native still render may have no finer progress. A camera
render occupies Blender's main thread and can leave the GUI busy until completion.

Remote artifacts have an authenticated `download_url` and, when an external URL
prefix is configured, a `download_url_with_token` valid for ten minutes. Artifact
ownership is checked for API-key downloads and jobs. Token links are bearer
capabilities that can be shared intentionally. Operation and artifact registries are private SQLite databases beside the socket
and survive MCP frontend restarts. The broker admits up to 128 queued/running
operations. Registered temporary outputs and operation history follow the configured
[retention policy](#temporary-outputs-and-retention); explicit deliverables remain
protected. History compaction preserves request-ID tombstones and does not vacuum
the databases. Snapshot permission permits generated image files even when general
library writes are disabled.

`execute_code` has `bpy` available and returns `success`, `stdout`, `stderr`, a
JSON-compatible `result`, and a traceback. Assign the output value to `result`:

```python
bpy.ops.mesh.primitive_cube_add(size=1)
obj = bpy.context.object
obj.name = "Prop_Block"
result = {"name": obj.name, "dimensions": list(obj.dimensions)}
```

Scripts can call `report_progress({...})` and `check_cancelled()` for cooperative
progress/cancellation. Each call has a fresh Python namespace. Scene data persists. Python exceptions
are reported with `success=false`; changes before the exception remain. Captured
Python stdout/stderr are capped at 128,000 characters each. Native Blender output
goes to the Blender log. The bridge bounds JSON messages to 8 MiB.

## Structured asset editing

Asset tools accept a typed `params` object, support `wait=false` and `request_id`,
and work when `allow_code_execution=false`. Editing requires `allow_scene_edit`;
`inspect_mesh` remains available to read-only clients.

- `inspect_mesh`: base or evaluated viewport geometry at the current frame, world
  bounds, triangle counts, boundary/non-manifold edges, degenerate faces, UV bounds
  and zero-area UV faces. Vertex samples are bounded (0–256); a geometry digest
  helps compare poses. The digest covers world vertices and polygon connectivity,
  not materials or UVs. This is not a self-intersection or UV-overlap test.
- `configure_modifier`: create/update a named `BEVEL`, `SUBSURF`, `DECIMATE`,
  `SOLIDIFY`, `TRIANGULATE` or `BOOLEAN` modifier with typed settings. Other stack entries
  remain intact. Settings include defaults; an update replaces the supported
  settings for that modifier. Angles are radians, distances are Blender units.
  Boolean settings name an operand `object`, choose `DIFFERENCE`, `UNION` or
  `INTERSECT`, and use the `EXACT` solver. Self-reference and cycles through
  Boolean operands, parents and constraint targets are rejected. Other imported
  dependency types are not comprehensively analyzed. Inspect the evaluated result
  before applying the modifier; the operand remains in the scene and export it
  only when intended.
- `apply_modifier` / `remove_modifier`: explicitly bake or discard a stack entry.
  Baking shared mesh data requires `make_single_user=true`; shape-key meshes are
  refused. Applying a later stack entry follows Blender's native stack behavior.
- `generate_uv`: SMART island projection or CUBE projection of all faces into a
  named map (`uv_map`, default `UVMap`). Existing coordinates require
  `overwrite=true`; shared meshes require `make_single_user=true`. SMART accepts
  `angle_limit_degrees` and `island_margin`; CUBE accepts `cube_size`. The target
  UV map becomes active. Inspect UV bounds and zero-area faces with `inspect_mesh`.
- `duplicate_object`: choose `new_name`, `linked_data` (default false) and an
  optional world-space `offset`. The copy is linked to the current collection.
  Parent, constraints, materials and animation action references are retained;
  duplicating geometry does not create independent copies of those resources.
- `set_parent`: set a named `parent` or omit it to unparent. `keep_world=true`
  preserves placement using the parent inverse. Cycles and singular parents are
  refused; clearing a parent with world shear is refused rather than losing it.
- `apply_transforms`: bake `location` (default false), `rotation` and `scale`
  (default true) into mesh geometry. Child world placement is preserved. Animated,
  constrained, shape-key or linked/overridden targets are refused; descendants
  must have static transforms and ordinary object parenting. Shared meshes need
  `make_single_user=true`. Modifier parameters are not rescaled automatically.
- `frame_objects`: fit an existing camera (`name`) to evaluated bounds of named
  meshes (`objects`). Choose `view` (`FRONT`, `BACK`, `LEFT`, `RIGHT`, `TOP`,
  `BOTTOM`, `ISOMETRIC`) or a world `direction` from the asset toward the camera;
  `margin` defaults to 1.15. Fits perspective and orthographic cameras and reports
  normalized `projection_bounds` and `fully_in_frame`. Use `configure_camera`
  with `projection="ORTHO"` for an orthographic view. The camera must be static,
  unparented and have independent data. Fit uses current render aspect and frame;
  refit after changing them. Clipping distances may expand to accommodate the asset.

Asset mesh tools require Object mode; operator-based edits also require a visible,
selectable target in the current view layer. They restore object selection and
active object. Linked/overridden mesh editing is refused. Operations do not provide
rollback; inspect the scene after a failure.

Example `configure_modifier` arguments:

```json
{"params":{"name":"Prop","modifier":"SoftEdges","settings":{"type":"BEVEL","width":0.05,"segments":3}}}
```

## UV seams, layout and texel density

`inspect_uv_layout` reads a named base-mesh `uv_map` (default `UVMap`) and returns
`uv_sha256`, including local geometry, world transform, seams, map coordinates and
active/render map selection. Carry it as `expected_uv` into every UV edit and
reinspect after each change. A missing map still has a fingerprint, allowing
safe creation with `unwrap_uv_mesh`. Shared data requires `make_single_user=true`.

Use `set_uv_seams` with `edges: {"indices": [...]}` or a named EDGE selection
(`edges: {"selection": "..."}`). Modes are `ADD`, `REMOVE` and `SET`; SET replaces
the complete seam set. `unwrap_uv_mesh` unwraps all faces using `ANGLE_BASED`,
`CONFORMAL` or installed `MINIMUM_STRETCH`, with `margin`. `pack_uv_islands`
packs a map into the unit tile, with optional `rotate` and `scale` controls.
`activate_uv_map` selects an existing map for editing and rendering/export.
UV edits preserve vertex geometry, shape keys, skin weights, object selection
and unrelated UV map coordinates. Native unwrap/packing operates on a temporary
mesh; only resulting coordinates are copied back. Native operators are blocking
and do not provide mid-call cancellation. These tools require Object mode and
local data; inspection describes the base mesh, not evaluated modifier output.

Inspection groups faces joined by UV-continuous shared edges into islands and
reports bounds, degenerate islands and area-based texel density for
`texture_width`/`texture_height` (1024 each by default). Density is the square root
of pixel area divided by base-mesh world-space surface area, in pixels per
Blender world unit; scene unit labels do not convert it to pixels per meter.
`normalize_uv_density` scales each island about its UV center to `pixels_per_unit`.
It refuses degenerate islands before assignment. Normalization may create
out-of-tile coordinates or overlaps: pack afterward with `scale=false` to retain
the requested density. Such fixed-size islands may not all fit a single tile;
inspect bounds rather than assuming the pack guarantees a fit.

Overlap inspection clips UV triangles and counts positive-area face pairs,
ignoring boundary-only contact and areas at or below 1e-12 UV units squared.
Its bounded sweep reports `overlap.complete=false` when `overlap_budget` is
exhausted; an incomplete zero count does not establish a clean layout. Island,
seam and pair samples report truncation. Defaults allow 50000 overlap candidate
checks (maximum 200000), 128 island samples (maximum 512), up to 100000 faces and
500000 corners, with edge incidence limited to 64 faces. This is a bounded
layout check, not a guarantee of target-engine texture quality. High-to-low
texture baking is a separate workflow.

## Texture baking and PBR bundles

Use `inspect_texture_bake` with a low target `name`, optional high `sources`
(up to 16), target `uv_map` and optional matching `cage`. Inspection fingerprints
the evaluated meshes/transforms/UVs/normals/material slots and supported source
shader graphs/images at the current frame. The target needs a nondegenerate,
nonoverlapping unit-tile UV layout with a complete bounded overlap check. A cage
must match the evaluated target's topology and vertex order. Source materials
connect directly to Principled BSDF by default. Managed thin leaves additionally
support the explicit FRONT_PBR conversion described below. Supported procedural/image nodes are
inspected, while groups, external coordinate objects, linked materials and
animated material graphs are refused. Source images must be saved, packed,
single-frame images with no unsaved pixel edits.

Pass `bake_sha256` as `expected_bake` to `bake_textures`, using the same target,
sources, cage and UV map plus a **new** library-relative `directory`. With no
sources, it bakes the target's own material/surface. The default maps are
`NORMAL`, `AO`, `BASE_COLOR`, `ROUGHNESS` and `METALLIC`; optional maps are
`EMISSION` (emission color) and `ALPHA`. For example:

```json
{"params":{"name":"Low","sources":["High"],"uv_map":"GameUV","expected_bake":"<inspection bake_sha256>","directory":"bakes/prop","width":1024,"height":1024,"samples":32,"cage_extrusion":0.1,"max_ray_distance":1},"wait":false,"request_id":"prop-textures-v1"}
```

The operation returns a tracked job by default. Poll `get_operation` or
`wait_operation`; reuse the same request ID to recover the existing operation.
An owned background Blender loads a saved source copy with script execution
disabled, verifies the source binding and freezes evaluated geometry before
baking. The editing scene/path/frame remain unchanged. The resulting `asset.blend`
is a **static, current-frame low mesh**, with a new PBR material referencing
relative PNG paths. Original editable rigs/modifiers remain in `source.blend` and
the live project. Requested channels transfer; unrequested channels use ordinary
PBR defaults. This does not reproduce arbitrary shader lobes, glass or HDR output.

Maps are 8-bit PNG: normal/AO/roughness/metallic/alpha use Non-Color, base color
and emission use sRGB. Normal maps are tangent-space with positive Y. AO measures
opaque geometry occlusion; alpha is transferred separately, without cutout-aware
AO. Native normal transfer retains a connected source normal/bump input. The
baked material includes the glTF occlusion settings group, so AO, normal and PBR
textures can be embedded by `export_objects_glb`. `maps` returns paths, dimensions,
color spaces and channel statistics; `material` names the new material.

High-to-low jobs first bake zero-margin UV and geometry-hit masks. `projection`
reports hit pixels divided by rasterized target pixels. Jobs below
`min_projection_coverage` (default .99) fail with partial files preserved: adjust
sources, `cage_extrusion`, `max_ray_distance` or the explicit cage. Lowering the
threshold explicitly accepts incomplete transfer. This is a pixel-sampled check
at the requested resolution, not a continuous coverage proof. Padding is excluded
from the comparison. The two diagnostic PNGs remain in the bundle.

Supported dimensions are 32–4096 per axis and at most 4194304 pixels total;
samples 1–256, padding `margin` 0–64 pixels, worker threads 1–16. Evaluated inputs
are limited to 250000 vertices/1000000 corners per object and 500000 vertices in
total. Each source image is limited to 4194304 pixels. These are workload limits,
not a global memory cap. `max_bytes` defaults to 2 GiB (maximum 64 GiB), with a
pixel/map/snapshot storage estimate and live free-space/output-size checks.
`timeout_seconds` defaults to 1800 (maximum 86400). Estimates are heuristics;
monitoring may overshoot between checks and does not reserve filesystem space.

Cancellation terminates/reaps the owned bake child; individual native map calls
are blocking inside that child. Source snapshot saving in the editing instance
is also blocking. Broker restarts preserve the running operation. If its editing
parent dies, a watchdog stops the child; `recover_texture_job` reconciles the
owned directory after both recorded processes are gone, adopting a complete
file-bound result or marking partial output interrupted, without replay.
`inspect_texture_job` reports process liveness and output bytes.

Open the bundle's `asset.blend`, then run `validate_texture_bake` to verify file
hashes and the native mesh/UV/material/image binding. Moving the whole bundle
preserves relative image references. Node UI labels/selection are excluded from
shader content guards; changing geometry or shading invalidates the binding.
`cleanup_texture_job` defaults to a dry run and only removes owned failed or
cancelled partial bundles. Interrupted bundles require `include_interrupted=true`;
successful deliverables, current-project/image references, symlinks and unknown
files are protected. These explicit output bundles are not temporary retention
artifacts. Keep wanted source projects/maps before removing partial work.

## Thin-leaf front-PBR conversion

Texture baking defaults to `thin_foliage_mode="REFUSE"`. Mixed native thin-leaf
shaders require `thin_foliage_mode="FRONT_PBR"` on both `inspect_texture_bake` and
`bake_textures`. The mode is part of the inspection guard. This bounded adapter
accepts the managed thin-leaf shader topology, including supported procedural vein
and bump inputs; it does not accept arbitrary mixed shaders or unknown node types.

Inspection, results, job records, manifests and validation expose
`material_adapters`. Each entry identifies the converted material and reports
omitted native back color, translucent/transmission shading and the backface/
double-sided shader. The worker selects the native `Leaf Surface` Principled inputs
and forces `Leaf Sides` to its front branch inside the disposable child. Original
materials, nodes, optical controls and the editable source snapshot stay intact.
A normal transfer still samples the source geometry and its connected bump;
it does not reverse source geometry or reconstruct tissue thickness.

The result is ordinary front-surface PBR, not equivalent thin-leaf optics. Keep the
editable source and review target-sidedness/shading separately. Conversion metadata
is bound to the owned job during completion, recovery and validation; a mismatched
conversion declaration refuses adoption/validation. Default direct-PBR jobs and
older direct-PBR bundles retain their existing guards and need no conversion flag.

For a static alpha card, create a UV-mapped target plane below a leaf and project
from the editable leaf mesh. Standalone leaf templates now create a node-based PBR
petiole as well as the managed thin blade, so both slots qualify. Select FRONT_PBR
and include BASE_COLOR, NORMAL, ROUGHNESS and ALPHA maps. Deliberately empty pixels
around the leaf require an explicit lower `min_projection_coverage` than the
ordinary .99 high-to-low default. Compare the geometry-hit mask and alpha silhouette;
a lower threshold alone does not prove complete transfer of the intended leaf.

The qualified example uses a default 12cm blade, a 0.08 by 0.14 target rectangle
and 128x128 maps at default scene units. It measures about 35.9% geometry hits and
39.6% alpha occupancy after two-pixel padding. Its delivered mesh has two triangles.
The native PBR card renders in Cycles, and its exported GLB has a nonopaque material
and an embedded base-color texture containing transparent and opaque alpha values.
This verifies the sampled files/Blender path, not Godot behavior or final atlas
quality. Fitted targets and verified-bundle atlases are available below; runtime
overdraw, multi-view representations and
wind-aware delivery remain separate work.

### Fitted leaf and mesh-cluster cards

Use `inspect_foliage_card` with `sources` (1–16 distinct local mesh objects), then
`create_foliage_card` with a new `name`, matching options and the returned
`expected_card=card_sha256`. Both use the evaluated current frame in the active
view layer. Realize collection/Geometry Nodes instances first: sources containing
instances refuse rather than silently omitting them. Managed thin-leaf materials
require explicit `thin_foliage_mode="FRONT_PBR"`, retaining the baking adapter's
loss declaration. Other source slots must satisfy the existing static PBR bake
profile. Source geometry, shaders, transforms, options, frame and scene scale bind
the guard. Source edits require another inspection.

Choose world-axis `view="TOP"` (XY, normal +Z), `FRONT` (XZ, normal −Y) or `SIDE`
(YZ, normal +X). The card sits behind the source along that normal by
`standoff_m` (default .005 metres). `outline="CONVEX_HULL"` trims exterior empty
area; `RECTANGLE` uses two triangles. `padding` (default .02) expands each side by
that fraction of projected width/height. Convex fitting encloses the projected
vertices, including petioles/stems. It preserves neither internal holes nor depth;
source alpha/shading and wind are outside the geometry fit. The generated object
has an editable convex face, `CardUV`, a two-sided PBR material and physical size
converted to current scene units. It does not change or hide the sources.

Inspection reports physical area/depth, triangle counts, metre-space vertices and
UVs. Its bounded `resolution` (32–256, default 128) samples opaque triangle union
against target pixels: `geometry_coverage_fraction`, `empty_fraction` and
`area_amplification` estimate wasted card area. They do not measure render
overdraw, source material opacity or engine performance. Thin/subpixel features
may be missed; compare resolutions and inspect the baked masks. `max_triangles`
(default 100,000, maximum 250,000) bounds source work; `max_vertices` (default 64,
maximum 256) bounds the fitted outline. Over-budget outlines refuse; choose a
rectangle or explicitly raise the budget. Edge-on/degenerate views refuse.

Creation returns `bake_inspection` and `bake_parameters` containing source/target,
guard, UV map, conversion mode, native-unit cage/ray distances and suggested
BASE_COLOR/NORMAL/ROUGHNESS/ALPHA maps. Choose `directory`, texture resolution and
`min_projection_coverage` explicitly before passing these to `bake_textures`.
The separate `suggested_min_projection_coverage` is 80% of sampled geometry
coverage, capped at .99; it is a starting estimate, not transfer validation.
Review worker coverage/alpha maps, reopen `asset.blend`, run
`validate_texture_bake`, and inspect/render the exported card. The shared baker
continues to report free space, own its worker and support cancellation/recovery.
This produces one view of a leaf or mesh cluster; combine verified bakes with the
atlas workflow below.

### Shared PBR texture atlases

Use `inspect_texture_atlas` with `entries=[{"id":"leaf","directory":"leaf-bake"},
{"id":"cluster","directory":"cluster-bake"}]`, then `build_texture_atlas` with the
same options, a new output `directory` and `expected_atlas=atlas_sha256`.
IDs are distinct lowercase identifiers (letters, digits, underscore, starting
with a letter; at most 32 characters). Inputs must resolve to distinct successful
original `bake_textures` bundles inside the active library. Atlas outputs are not
accepted recursively. Existing output directories and outputs inside a source
bundle refuse. Input files, conversion declarations and packed layout bind the
guard; changed sources require inspection again.

Choose `width`/`height` (32–4096 each, at most 4,194,304 pixels) and `gutter`
(0–64 pixels, default 8). All entries must have the same ordered set of baked
8-bit PBR maps, with uniform map dimensions within each entry. Entries may differ
in size. A deterministic height-first shelf layout places them without rotating,
resampling or reducing resolution. Insufficient room refuses. Tile rectangles
use bottom-left pixel coordinates; `uv_rect` is `[u,v,width,height]` for the inner
tile, excluding its gutter. Base-level edge pixels are duplicated through the
gutter. Tangent-space maps retain their orientation.

The plan reports tile/allocated fractions, `base_rgba8_bytes` and
`full_mip_rgba8_bytes`. `max_texture_bytes` (default 256 MiB) caps the full-mip
RGBA8 estimate across all maps; `max_input_bytes` (default 2 GiB) caps the verified
input bundle inventory. These are storage/texture planning figures, not measured
GPU memory. Only base-level PNGs are emitted: mipmap creation, compression and
bleed-free anisotropic sampling are downstream concerns. Geometry coverage from
card inspection is distinct from atlas tile occupancy.

Inspection verifies files/hashes, map encodings, dimensions and layout. The
isolated worker additionally opens each `asset.blend` with scripts disabled,
checks its native binding and requires a static single-UV mesh with positive
nonsingular transforms and matching untextured PBR constants. Per-mesh bounds are
250,000 vertices and the existing bake-signature loop limit; combined bounds are
1,000,000 vertices and 2,000,000 corners. Unsupported inputs fail with their owned
partial job preserved for inspection/cleanup. Bake or simplify sources first.

Output `asset.blend` contains one mesh per ID, one shared material, `AtlasUV` and
the atlas maps. Physical source placement is converted to metre scene units;
editable source bundles and the connected editor remain unchanged. The manifest
records source files/guards, loss declarations, tile layout and each output's
geometry/UV/material/image signature. Reopen the asset and use
`validate_texture_bake` before selected-object GLB export. Validation checks all
atlas objects and binds the declared layout to its owned job. Use the existing
`inspect_texture_job`, `recover_texture_job` and `cleanup_texture_job` commands
for progress/reconciliation/partial cleanup. Atlas building uses the same owned
worker, parent-death handling, timeout, cancellation and free-space reporting as
texture baking. Default execution is asynchronous; poll its operation.

## Mesh element editing and cleanup

Use `inspect_mesh_elements` with `domain=VERTEX`, `EDGE` or `FACE` to page the
stored base mesh. It returns local coordinates, world vertex positions, edge
adjacency, face centers/normals/material indices, shared-data usage and named
selections. Pass its `topology_sha256` as `expected_topology` to every indexed
edit. Optionally pass its `geometry_sha256` as `expected_geometry` to reject
coordinate changes too. This local-geometry fingerprint differs from the world
geometry digest returned by `inspect_mesh`; neither includes UVs/materials.
Evaluated modifier output is not a source of editable base-mesh indices.

`select_mesh_elements` takes a `domain` and `elements`, with exactly one of
`indices` or `selection` inside `elements`. An optional `selection_name` stores
the chosen indices on this object; replacing it requires `replace=true`.
Named selections survive save/reopen, but topology changes make them stale.
`remove_mesh_selection` removes a named group without editing geometry. Limits
are 64 names and 100,000 stored indices in total. Selection writes use a temporary
mesh and do not switch the user's Object/Edit mode or active object.

For example, inspect the roof face index and then call `extrude_mesh_faces`:

```json
{"params": {"name": "Building", "expected_topology": "COPY_CURRENT_TOPOLOGY_SHA256",
            "faces": {"indices": [5]}, "offset": [0, 0, 1]}}
```

The fingerprint and index are placeholders for inspected values. Reinspect after
every edit: indices and fingerprints can change even when vertex counts match.

- `extrude_mesh_faces`: extrude a face region by an explicit object-local offset.
- `inset_mesh_faces`: inset a region or individual faces by local `thickness`.
- `loop_cut_mesh`: cross a quad ring from seed `edge`, adding 1–32 evenly spaced
  cuts; non-quad or non-manifold rings are refused before assignment.
- `merge_mesh_vertices`: weld explicit/named `vertices` at `CENTER`, `FIRST` or
  `LAST` input position.
- `cleanup_mesh`: optional distance weld, degenerate-edge dissolution, loose
  edge/vertex removal and face-normal recalculation.
- `repair_mesh_normals`: recalculate all/selected faces `OUTSIDE` or `INSIDE`, or
  `FLIP` their winding. Outside is not well-defined for every open/nonorientable
  surface; inspect results. This does not author custom split normals.

These tools require local meshes in Object mode without shape keys or armature
deformation. Shared mesh data needs `make_single_user=true`. Geometry operations
work on a temporary BMesh/copy before replacing the object's data; preflight and
operation failures preserve the original geometry. A crash around assignment can
still leave an uncertain outcome. Existing UV layers and material slots are
preserved, but newly generated UVs may need re-unwrapping. Inspect topology,
materials and renders after editing. Mesh edits are limited to one million
vertices/faces; native operations are not forcibly interruptible. Ordinary
operation IDs, request-ID deduplication and broker reconnection apply.

## Botanical branch models and woody masters

The botanical workflow is separate from the stylized `VEGETATION` Geometry Nodes
preset. Its first profile, `QUERCUS_ROBUR`, creates a woody structure and semantic
terminal buds. Optional instanced foliage adds editable lobed leaves and thin-leaf
optics. Wind motion, vegetation-specific LODs and a completed realistic oak asset
remain separate work.

`botanical_species_catalog` reports profiles/defaults and references. The
standalone `mcpblender.botany` module generates and validates versioned JSON using
only Python's standard library. Its art-directed scaffold defines trunk/primary
limbs; crown growth uses nearest-attractor space competition, persistence, a light
vector, gravity bias, local repulsion and seeded variation. These are geometric
controls, not measured light transport or a calibrated biological growth solver.
The broad rounded species envelope is informed by
[Oregon State University's English oak description](https://landscapeplants.oregonstate.edu/plants/quercus-robur);
the crown-filling approach follows the general idea of
[Runions, Lane and Prusinkiewicz's space-colonization model](https://www.algorithmicbotany.org/papers/colonization.egwnp2007.html).

Plan a tree with `plan_botanical_tree` and a `recipe`. Planning is asynchronous by
default; use `wait=true` or poll its operation. It returns `model_sha256`, normalized
recipe, crown envelope and structural metrics without creating native IDs.

```json
{
  "recipe": {
    "species": "QUERCUS_ROBUR",
    "seed": 1,
    "height": 14,
    "crown_width": 13,
    "crown_base": 0.23,
    "trunk_radius": 0.36,
    "primary_branches": 9,
    "attractors": 640,
    "node_budget": 1600,
    "light_direction": [0, 0, 1],
    "gravity": 0.08
  }
}
```

The same generator version/normalized recipe/seed reproduces identifiers and
coordinates in the qualified environment. Branches have stable IDs, parent and
axis IDs, order, birth step, approximate age, start/end, tapered radii, axis anchor,
stiffness and phase. Terminal buds reference their supporting branch and direction.
Surviving scaffold slots keep their IDs across parameter changes; topology changes
can add/remove growth slots, so this is not arbitrary edit correspondence.
The model declares local metres, right-handed Z-up and a trunk-base origin.
`age_years`/stiffness are structural proxies; age is not a biological growth clock.
Radii use descendant demand with a bounded pipe-style support allocation, not a
mechanical strength rating. The requested height is centerline height; mesh radii
can extend slightly beyond it. Crown dimensions guide growth and do not measure
foliage coverage or guarantee complete envelope filling.

Other recipe controls include iterations, segment length, persistence,
light weight, avoidance, randomness, crown offset, pipe exponent and root flare.
Height, width and radius are independent controls; supply compatible dimensions
when changing growth stage. Limits include 4000 branch segments, 2048 attractors
and 80 growth steps. An insufficient budget for the initial scaffold refuses.
Metrics expose counts/orders/axes/buds, centerline bounds/height/width, total
length, branch-angle statistics/histogram, woody asymmetry and reached attractors.
They are not projected leaf area, photosynthesis, silhouette quality or collision
measurements. Growth and meshing report progress and cooperative cancellation.

`create_botanical_tree` takes the same recipe, `expected_model`, a new `collection`
(up to 40 UTF-8 bytes), optional `location`, `radial_sides` (5..16),
`bark_tile_length` in metres and optional existing `bark_material`. It creates an
owned root, tapered wood mesh, hidden nonrendering bud-point mesh and canonical
JSON Text datablock. Default bark is a reusable brown rough PBR material, not
qualified bark texture detail. Initial root scale converts model metres to current
scene units without changing scene unit settings; location uses native scene units.

Wood uses parallel-transport-style cross-section frames, root flare/asymmetry,
shared continuation rings, growth-aligned `BarkUV` and intersecting capped sleeves
at lateral branches. Junctions are not welded/unioned or qualified for close-up
watertight manufacturing. Point attributes include `bot_branch_index`,
`bot_branch_order`, `bot_age`, `branch_anchor`, `branch_stiffness`, `branch_phase`
and `bend_weight`. Branch indexes address the canonical model's branch array.
The bud mesh supplies parent branch indexes and directions. These are native
semantic inputs for future wind/foliage work, not an implemented wind animation or
verified interchange packing. Only BarkUV is created; UV2 remains available.

`inspect_botanical_tree` reports model/mesh validity, ownership and reference
blockers, recipe, metrics, native geometry/attribute inventory, root matrix, scene
unit scale and `tree_sha256`. This guard covers current native identity, contents,
links and relevant state; obtain it again after editing or reopening. It is distinct
from the pure model guard. `list_botanical_elements` pages `BRANCH` or `ORGAN`
records with `offset`/`limit` (at most 128), avoiding a full graph in MCP responses.

To revise growth, plan the changed recipe, inspect the current master, then call
`regenerate_botanical_tree` with both `expected_model` and `expected_tree`. It
stages and verifies a replacement before name handoff and final owned deletion.
Static root parent/binding/placement, parent collection links and owned visibility
are preserved by default; `preserve_placement=false` uses the new initial transform.
Existing bark material is reused unless explicitly replaced. Materials remain
shared; shader/image contents are not frozen by the tree guard.

Manual derived mesh edits block regeneration unless
`discard_derived_edits=true` explicitly authorizes replacing them. Edited/invalid
canonical model Text still blocks regeneration under that flag. Root authored
controls and external/shared native references refuse replacement. Cooperative
failure before final deletion restores original IDs/names/selection and removes
staging; process-crash rollback at handoff is not established. The final native
batch deletion is noninterruptible.

`remove_botanical_tree` takes a fresh `expected_tree`. It can remove unambiguously
owned changed content, but refuses foreign membership, shared/externally referenced
owned IDs, linked/overridden data and protected controls. Materials and outside
parents/collections remain. The canonical Text is owned through a collection ID
reference rather than an unreferenced fake-user copy.

`export_botanical_model` writes guarded canonical JSON to a library `.json` path;
existing output requires `overwrite=true`. It uses owned temporary staging and
publishes without overwriting an unexpected existing target. This export contains
local model semantics, not scene root placement, GLB geometry or a vegetation
adapter manifest. Native numeric attribute retention through GLB, foliage density,
wind deformation, collision/LOD/impostor quality and general species/organ growth
remain separate milestones. Keep the canonical model alongside the editable
`.blend` when developing those downstream representations.

## Procedural botanical surface detail

Use `create_botanical_surface` to create a reusable native material with
`settings.profile` equal to `OAK_BARK` or `OAK_LEAF`, then `assign_material` to
objects. These are bounded procedural recipes, not scanned textures or an atlas.
For an existing tree, use the bark material name from `inspect_botanical_tree` or
the leaf material name from its `foliage` report. Inspect that material with
`inspect_botanical_surface`, then configure it using the returned `material_sha256`
as `expected_material`:

```json
{
  "material": "Oak_LeafSurface",
  "expected_material": "<fresh material_sha256>",
  "settings": {
    "profile": "OAK_LEAF",
    "vein_pairs": 6,
    "vein_slope": 1.5,
    "vein_width": 0.1,
    "midrib_width": 0.025,
    "vein_color": [0.18, 0.29, 0.045, 1],
    "color_strength": 0.35,
    "bump_distance": 0.0004,
    "bump_strength": 0.35
  }
}
```

Pass this to `configure_botanical_surface` inside `params`. Leaf detail requires
a managed thin-leaf material. It adds a paired UV vein pattern and midrib color/
bump while retaining the original front/back color source and thin-leaf shader.
`configure_foliage_material` still edits roughness, front/back colors and optical
mix independently. Veins are an artistic procedural pattern, not a biological
vascular reconstruction or extra mesh topology.

`OAK_BARK` requires a direct surface-only Principled material. Its controls are
`cross_scale` (default 24), `length_scale` (2), `dark_color`, `light_color`,
`bump_distance` (0.012) and `bump_strength` (0.5). Elongated cellular fissures,
plateaus and fine noise produce color and bump. Use growth-aligned BarkUV for tree
wood; ordinary meshes can supply their own named UVs. The settings use UV
coordinates and native bump distance, not calibrated world-metre displacement.
Existing roughness stays unchanged. RGBA color alpha must be one.

Both profiles use a named UV map (`uv_map`, default `BarkUV` or `LeafUV`) and keep
the material's native identity. Set `uv_map="UVMap"` for ordinary primitive meshes.
The name must exist on every relevant mesh; inspection reports mesh users missing
it, without changing those meshes. This source binding stays fixed when
baking to a different target UV map.
Editing affects all material users. Existing color/normal input sources are retained
for removal; unrelated nodes remain. A staged node graph is connected before the
old owned detail nodes are deleted. Cooperative failure before final deletion
restores the old links and removes newly created nodes. `detail_valid` identifies
unchanged owned detail; manual edits to its nodes/links or nested color ramps
refuse rebuilding/removal until reconciled. Fresh material guards are required.
Local unanimated node materials are supported. A profile change requires removing
the old detail and supplying a compatible base shader; creating a separate
material is simpler when changing between PBR bark and thin foliage. Assign new
materials before saving to retain them under Blender's
ordinary material-user rules.

`remove_botanical_surface` takes `material` and `expected_material`, restores the
original color/normal inputs and removes only owned detail nodes. It keeps the
material and independent optical controls. Tree growth regeneration reuses these
shared materials, so their detail survives without rebuilding the shader.

For tiled growth UVs, keep the named source UVs and create a separate packed
unit-tile target UV map (or low mesh) for delivery. Bark's direct PBR graph works
with the existing `inspect_texture_bake` /
`bake_textures` pipeline: normal baking includes connected bump, and base-color/
roughness maps can be delivered in the ordinary PBR bundle. Native thin-leaf
shader lobes require the explicit FRONT_PBR conversion described above; the full
optical shader is not preserved. Fitted card targets use the workflow above;
atlases, thickness/transmission maps and runtime shader equivalence require
separate qualification. The procedural native
graph itself is not a promise of equivalent GLB shading.

## Modular leaves and instanced botanical foliage

`plan_leaf_template` accepts a `leaf` shape: length/width/petiole in metres,
`lobes`, `lobe_depth`, `curl`, `fold`, `vein_ridge` and `rows`. The result includes
`leaf_sha256`, normalized shape, UV-ready geometry counts and summed blade area.
`create_leaf_template` uses that same shape, `expected_leaf` and a new `name`
(maximum 40 UTF-8 bytes) to create an editable native mesh and thin-leaf material.
The recipe and local generated mesh use metres. Creation sets object scale to
`1 / scene.unit_settings.scale_length`, preserving physical size without changing
project units. The response includes normalized `recipe`, `scene_unit_scale` and
`world_bounds_m`. Existing objects are not retroactively resized, and changing the
project's unit settings later does not trigger automatic leaf rescaling. Native
physical size and nonmetre GLB delivery are checked separately; see the export
unit contract below.
The blade has a raised midrib, not a secondary vein network or scanned texture.
Rows increase when necessary to resolve the selected lobe count.

For a managed botanical tree, call `plan_botanical_foliage` with `collection`
and an optional `foliage` recipe. Defaults use six shoots per terminal bud,
ten attachment nodes, three shared prototypes and alternate leaves. Example:

```json
{
  "collection": "Oak",
  "foliage": {
    "seed": 1,
    "shoots_per_bud": 4,
    "attachment_nodes": 8,
    "arrangement": "ALTERNATE",
    "shoot_length": 0.65,
    "spread": 0.7,
    "inclination": 0.25,
    "size_variation": 0.2,
    "variants": 3,
    "max_leaves": 100000,
    "max_expanded_triangles": 8000000,
    "leaf": {"length": 0.12, "width": 0.065, "lobes": 5}
  }
}
```

Obtain a fresh `tree_sha256` from `inspect_botanical_tree`, then call
`configure_botanical_foliage` with the same collection/recipe and both
`expected_tree` and the plan's `foliage_sha256` as `expected_foliage`.
Planning/configuration/removal default to asynchronous operations. Use `wait=true`
or operation polling. Leaf and expanded-triangle limits are checked before
allocating the attachment table. They are geometry budgets, not memory guarantees,
projected crown coverage, GPU performance or draw-call estimates.

Each leaf is attached to a modeled shoot beginning at a semantic terminal bud.
ALTERNATE is the oak-oriented default; OPPOSITE and WHORLED are artistic alternatives.
The native population uses a point mesh, an owned Geometry Nodes group and an
unlinked collection of shared prototypes. It does not realize instances. Point
attributes include `leaf_rotation`, `leaf_scale`, `leaf_variant`, `bot_branch_index`,
`leaf_index`, `leaf_phase` and `leaf_flutter`. Phase/flutter are future motion inputs;
no wind motion is generated. `list_botanical_leaves` reconstructs deterministic
IDs, branch/shoot references and transforms with bounded `offset`/`limit` paging.
The canonical foliage Text stores the versioned recipe and deterministic hashes;
it is separate from the branch/bud JSON exported by `export_botanical_model`.
Save the editable `.blend` to preserve the complete native foliage component.

Tree growth regeneration preserves the foliage recipe and existing leaf material.
Foliage reconfiguration stages a complete replacement, preserving root placement
and bark. Manual derived edits require `discard_derived_edits=true`; inspect and
plan again first. Canonical JSON edits, external native references and unsupported
controls refuse replacement. Cancellation before final handoff preserves original
native IDs. `remove_botanical_foliage` stages the woody-only tree; tree removal
also removes owned foliage points, shoots, prototypes, groups and Text. Reusable
materials remain. Whole-tree owned deletion can remove a damaged canonical model
when no external ownership references block it.

`inspect_foliage_material` reports actual front/back/transmission colors, roughness,
`translucent_mix`, `double_sided`, users and `material_sha256`.
`configure_foliage_material` requires that guard as `expected_material` plus changed
settings. Colors are RGBA with alpha fixed to one. Patches affect all material users.
Linked target inputs refuse direct default-value edits. Double-sidedness is controlled
separately from the artistic diffuse/translucent mix; explicit backface transparency
also operates in Cycles. This native shader is not calibrated physical thickness,
an alpha-card shader or a promise of equivalent glTF/runtime shading. Alpha atlases,
baked vein/bark maps, seasonal optics and vegetation-specific delivery remain open.

## Botanical coverage and crown refinement

`inspect_botanical_coverage` measures the projected union of opaque blade triangles,
not the sum of overlapping leaf areas. Supply a managed `collection`; omit `foliage`
to inspect its current foliage, or supply a proposed foliage recipe to compare
without editing native data. The tree must pass its content/ownership checks.
The result includes `tree_sha256`, model/foliage guards and `proposed_recipe`.
This is a tracked read-only operation, asynchronous by default: poll its operation
or use `wait=true` for bounded work. It creates no native geometry or output files.
Large layouts can take minutes; progress and cooperative cancellation occur between
leaf batches. Existing operation status supplies current free-storage information.

Options are `views` (distinct FRONT, SIDE, TOP), `resolution` (32–256; default 128),
`margin` (0–5m; default 2.5), `max_projected_triangles` (default 60 million; maximum
100 million) and `include_masks` (default false). The work budget counts each
blade triangle in each requested view, before projection. Reduce views or density
when necessary; increasing raster resolution improves sampling but not geometry.

For each view the report provides local-metre projection axes/frame, pixel size,
covered pixels, pixels inside the declared crown ellipse, `crown_coverage_fraction`,
projected union area, area outside that ellipse, reflected-silhouette asymmetry
and `frame_clipped`. Optional `mask_rows_hex` encodes each row as a hexadecimal
integer: row zero is the minimum second projection coordinate, and bit zero is
the minimum first coordinate. FRONT projects X/Z, SIDE Y/Z, TOP X/Y. Frames are
centered on the canonical crown, expanded by the margin; root placement/scale
is deliberately excluded. Keep model, views, margin and resolution fixed when
comparing foliage recipes. Changed tree growth can change that reference frame.

Only pixel centers inside blade triangles count. Wood, shoots, petioles, shader
alpha/translucency, perspective, lighting and wind are excluded. Subpixel leaves
may be missed; check a higher resolution and actual renders before assessing
visual quality. Degenerate projected triangles contribute nothing. Asymmetry
compares occupied samples to their horizontal reflection; random fine foliage can
produce high values even when the broad crown is balanced. These are geometric
sampling metrics, not optical leaf-area index, biological validation or GPU overdraw.

A refinement loop is: inspect current coverage; compare a proposed density recipe;
plan that recipe with `plan_botanical_foliage`; apply it with fresh tree/foliage
guards; render the same camera and inspect coverage again. Existing controls can
increase shoot count, attachment nodes and shoot reach while retaining shared
prototypes. For a dense study of the default 14m source, a tested proposal uses
12 shoots/bud, 16 attachment nodes, `shoot_length=1.2`, `spread=1.1` and an explicit
`max_expanded_triangles=20000000`. This is a higher-cost density study, not a
completed realistic-oak preset or vegetation LOD. Detailed bark, branch junctions,
atlases and wind remain separate milestones.

## Portable botanical wind preparation

Use `inspect_botanical_wind` with a valid managed tree `collection` and optional
`wind` settings, then `sample_botanical_wind` with the same settings and `seconds`.
These tools leave the native scene, frame and geometry unchanged. They prepare
and qualify an engine-independent motion model; native deformation/animation and
GLB attribute packing remains separate. The native preview workflow below uses
this same motion model on an independently owned copy.

The field is a steady world-space `steady_mps` vector plus 1–8 seeded sinusoidal
waves. `gust_mps`, `wavelength_m` and `frequency_hz` control their amplitudes,
spatial scale and frequency. Inspection returns the explicit wave vectors,
amplitudes, angular frequencies and phases, plus the formula. World positions
use metres and time uses seconds. Identical settings produce the same field
across trees, retaining spatial correlation. `phase_offset` varies branch response
and leaf flutter while keeping that common field. Wind speeds and response
coefficients are artistic controls, without a calibrated mechanical model.

Branches rotate parent-first about their segment starts, with each child attached
to its posed parent's endpoint. The field is sampled at undeformed anchors mapped
to world metres. The rotation axis is perpendicular to the inherited branch
direction and wind; response uses perpendicular speed, segment length, recorded
stiffness and phase. `bend_degrees_per_mps` controls response, capped per segment
by `max_segment_degrees`. Sampling refuses poses exceeding
`max_accumulated_degrees`. Inspection reports a conservative all-time field-speed
and summed-rotation bound. A false `rotation_budget_proven_for_all_times` means
the bound cannot establish the guarantee; inspect actual samples or lower response.

Leaf positions and base orientations inherit their parent branch's rigid motion.
Local-X flutter uses `flutter_degrees`, `flutter_hz`, recorded leaf phase/flutter
and `phase_offset`, preserving each leaf's shape. A globally zero field disables
flutter. Root placement is a frozen evaluated snapshot: positive uniform physical
scale, proper rotation and translation are supported; shear, reflection and
nonuniform scale refuse. Admitted float32 rotation roundoff is orthonormalized,
with `placement_rotation_fit_error` reporting the maximum element correction.
Parent animation is excluded from this frozen placement.

Sampling accepts 1–16 distinct times within ±1,000,000 seconds. `offset`,
`leaf_offset` and `limit` (1–32, default 8) page branch/leaf poses. `max_work`
(default 100,000, maximum 1,000,000) bounds branches plus sampled leaves across
times. Every sample reports all-branch segment-length, junction, root-anchor,
cumulative-rotation and endpoint-displacement metrics. Posed positions are returned
in canonical local metres and world metres; local rotation matrices act on the
canonical rest frame. These centerline/rigid-leaf checks exclude tube-surface
strain, collision, native mesh deformation and rendered appearance.

Use `export_botanical_wind` with fresh `expected_wind=wind_sha256`, matching
settings and a `.json` `path` to preserve the model for another backend. The sidecar
contains versioned solver/field settings and formulas, explicit waves, the branch
graph, frozen placement and full rest foliage/shoot attachments when present.
Branch IDs and leaf parent indices refer to its canonical model. Its default
`max_bytes` is 64 MiB; publication checks available space and atomically installs
an owned temporary file. Existing files require `overwrite=true`; cooperative
cancellation before publication preserves the original. Reinspect after source,
placement or settings changes. The JSON carries semantic data for later adapters;
GPU packing and target-engine validation remain open.

### Sampled native wind previews

Use `inspect_botanical_wind_preview_source` with the source tree, `wind` settings
and an increasing `frame_start`/`frame_end` range. Pass the returned `plan_sha256`
as `expected_plan` to `create_botanical_wind_preview`, with matching options and
a fresh `preview_collection` name. Creation defaults to asynchronous execution;
poll the same operation for progress/cancellation. Planning leaves the scene
unchanged. Generation preserves the procedural master, current frame/subframe,
selection and active object, and stages its own data before the final handoff.

The copy contains animated wood, bud points and optional shoots, plus shared leaf
prototypes. Three animated helper points reconstruct each rigid leaf's orientation
through Geometry Nodes. Only one prototype mesh per variant is copied; leaves
remain instances. Ordinary relative shape keys and linear native action curves
store pose samples, so playback survives save/reopen with no Python handlers.
The original shader materials stay shared. Numeric branch/leaf semantics and the
wind/model JSON are retained on owned native data; GLB retention is a later step.
The generated soil ring stays fixed in local coordinates.

Time is `frame / captured_fps`. `frame_step` defaults to 1, the range defaults to
1–49, and the final frame is always included. At most 121 sampled frames over a
2,400-frame span are supported. Motion needs at least eight samples per fastest
field/response/flutter cycle; lower frequencies/step or raise scene FPS when
planning refuses. Native interpolation is linear between samples and freezes at
the endpoints. Use the baked range for rendering. This is a bounded authoring
preview, with explicit cache cost; scalable runtime wind remains separate.

`display_offset_m` moves the preview copy for comparison. The field continues to
use the original frozen source placement, so this display offset is not a new
physical planting location. Use the returned `objects` for `setup_preview_stage`
and rendering; framing includes evaluated mesh instances without realizing them.
`roles`, `root` and `prototype_objects` expose the named native components.

The plan reports raw `coordinate_bytes` and estimated `work` for pose construction
and key/midpoint checks. Defaults allow 30,000 leaf instances, 256 MiB of sampled
coordinates and 30,000,000 work units. Their explicit maxima are 100,000, 2 GiB
and 100,000,000 respectively. Coordinate bytes exclude general Blender overhead;
these limits are not a measured memory/performance guarantee. Progress includes
free storage and a checkpoint-size estimate; checkpoint admission retains its
existing filesystem checks. Native construction uses the connected instance's
main thread and provides cooperative cancellation boundaries.

Before success, native readback checks every sampled frame and every interval
midpoint against the exact solver. Defaults bound key position error to .0001m,
midpoint error to .01m, leaf orientation error to 1 degree and mesh-edge relative
strain to .2. Leaf matrices also retain uniform scale/orthogonality within 1e-5.
All leaf instances are matched to their variant/pose; every nonzero wood/shoot
mesh edge is measured. Review the returned `verification` values and actual
renders. These checks do not establish continuous-time extrema, surface volume,
collision avoidance or biomechanical accuracy.

Use `inspect_botanical_wind_preview` for current content/ownership, timing and
`preview_sha256`. Playback leaves this content guard stable; native edits and
changed scene FPS invalidate its qualification. The preview remains usable after
its source is removed. To delete it, inspect again and pass that guard to
`remove_botanical_wind_preview`. Removal preserves materials, refuses foreign
collection members/external references, and accepts manually edited owned data
only with a fresh guard. Completed creation records UUID ownership markers on
all its native IDs; cooperative failures remove the staged data. Hard-crash
rollback before completion is unqualified; normal application checkpoints and
explicit project saves remain the recovery boundary.

## Structured Geometry Nodes

These tools accept `params` and work with Python execution disabled. Use
`geometry_node_catalog` to discover supported node types and up to 128 existing
groups; request a `node_type` for installed socket identifiers and property choices.
`inspect_mesh` includes the group name for Geometry Nodes modifiers.

`configure_geometry_graph` creates a named persistent group with automatic
Geometry input/output sockets and optional FLOAT, INT, BOOLEAN or VECTOR inputs.
Each input supplies a name, type and default, with optional numeric `minimum` and
`maximum` limits. Those limits persist in the group, appear in inspection, and are
enforced before modifier input updates. Nodes use catalog types, named
instances, allowlisted properties and typed input values. Socket references are
identifiers, unambiguous names or nonnegative indexes. Rotations use XYZ Euler
radians. `GeometryNodeSetMaterial` accepts a named existing `material`; assigning a
material slot on the original mesh does not color newly generated primitives.
`GeometryNodeStoreNamedAttribute` accepts `attribute` and allowlisted `data_type` /
`domain` settings. Primitive UV Map fields can be stored as `FLOAT2` on `CORNER`
under `UVMap` for textured PBR and GLB delivery.

For example, a reusable parameterized box:

```json
{"params":{
  "group":"ParametricBox",
  "inputs":[{"name":"Size","type":"VECTOR","default":[2,3,4]}],
  "nodes":[
    {"name":"Parameters","type":"NodeGroupInput"},
    {"name":"Box","type":"GeometryNodeMeshCube"},
    {"name":"Output","type":"NodeGroupOutput"}],
  "links":[
    {"from_node":"Parameters","from_socket":"Size","to_node":"Box","to_socket":"Size"},
    {"from_node":"Box","from_socket":"Mesh","to_node":"Output","to_socket":"Geometry"}]
}}
```

Use `attach_geometry_nodes` with `name` (mesh object), `group` and optional
`modifier` (default `GeometryNodes`). Different objects can share a group with
independent modifier inputs. Reattaching the same group preserves those values;
an existing modifier pointing elsewhere is refused. `configure_geometry_inputs`
takes `name`, `modifier`, `expected_graph` from inspection's `graph_sha256`, and
`values` containing `socket`/`value` pairs. Interface indexes count only editable
inputs, excluding Geometry. All values are preflighted before applying any;
objects with animation/drivers or inputs using named attributes are refused.

`inspect_geometry_graph` reports interfaces, nodes, defaults, links, users and a
graph fingerprint. Inspection includes imported groups, but editing/attachment
requires a local managed group without animation/drivers or unsupported nodes.
Results are bounded to 128 nodes and 256 links; truncated/unsupported graphs have
no usable fingerprint. Fingerprints cover supported graph configuration, including
material references, rather than the contents of referenced materials. Groups
have a fake user so they survive saving without a modifier attachment.

Replacing a managed graph requires `replace=true`, its current `expected_graph`
and no real users. Detach modifiers with `remove_modifier` first; this deliberately
prevents graph replacement from silently changing multiple attached objects.
Construction uses a temporary group; invalid nodes, properties, socket values,
links, cycles or output wiring preserve the original. Exactly one Group Output
with linked Geometry is required. Multi-input geometry joins are supported.
Nested groups, object references, simulation zones and executable nodes are not
exposed. Direct primitive counts are limited to 512 and subdivision levels to 3;
these limits do not bound geometry generated through fields, linked inputs or
successive modifiers. Inspect evaluated counts and render at representative sizes.

For delivery, `export_objects_glb` and `export_glb` accept explicit
`apply_modifiers=true` to include evaluated static geometry without baking the
editable source. This mode refuses shape-key/armature-deformed meshes. The default
keeps the existing base-mesh export behavior. Alternatively, explicitly bake a
modifier using `apply_modifier`, then inspect the resulting mesh before export.

### Reusable procedural presets

`create_geometry_preset` creates a named reusable group, then
`attach_geometry_nodes` attaches it to an existing mesh. The tool takes `group`
and a discriminated `settings` object. Materials are optional names of existing
materials; use `apply_material_preset` first for textured PBR or other surfaces.
Generated primitives carry a `UVMap` and material references. For example:

```json
{"params":{"group":"ApartmentExterior","settings":{
  "type":"BUILDING","floors":3,"columns":4,"width":8,"depth":5,
  "floor_height":3,"wall_material":"Brick","window_material":"Glass",
  "roof_material":"Roof"}}}
```

| Settings type | Parameters and exposed modifier inputs | Result |
| --- | --- | --- |
| `BUILDING` | `floors` / `Floors` (1–32), `columns` / `Columns` (1–16), `width` / `Width`, `depth` / `Depth` (1–200), `floor_height` / `FloorHeight` (1–10); optional wall/window/roof materials | Solid exterior mass with a flat roof and repeated decorative window panels on front/back. It does not cut openings or provide interiors. |
| `VEGETATION` | `height` / `Height` (.5–30), `crown_radius` / `CrownRadius` (.1–10), `trunk_radius` / `TrunkRadius` (.02–2); fixed `segments` (3–32), optional trunk/leaf materials | Pine-style cylinder trunk and cone crown with its base at local Z=0. |
| `SCATTER_VEGETATION` | Tree parameters plus `density` / `Density` (0–50), `seed` / `Seed` (0–1000000), `spacing` / `Spacing` (.1–20), `max_points` / `MaxPoints` (1–2000) | Seeded Poisson distribution on the input surface, aligned to its normals, capped by point index, realized for delivery and joined with the original surface. |
| `REFINE_MESH` | `levels` / `Levels` (0–3), optional `material` | Catmull–Clark subdivision of the input mesh, retaining the editable source; this is not automatic remeshing or topology repair. |

Parameter names in settings use snake_case; exposed modifier names are shown after
the slash. Use `configure_geometry_inputs` with the current `expected_graph` to
change one object's values. Geometry inspection reports preset type/version,
limits, material references and each modifier's values. Invalid creation or
replacement preserves an existing group; the usual unused-group replacement
guard applies.

Scatter and refinement require the first modifier position and meshes without
shape keys or armature deformation. Bake upstream modifiers explicitly before
attaching them. Attach/input updates return `workload`: scatter estimates candidate
points as **local surface area × density**, refusing estimates above 20000, and
separately caps output instances to `MaxPoints`. Refinement estimates faces from
source polygon corners and subdivision levels, refusing estimates above 250000.
These are checks at those tool calls, not global memory limits or guarantees for
later source edits, native UI edits, fields or stacked modifiers. Distances and
density operate in object-local coordinates; object scale changes world spacing.
Inspect evaluated geometry, materials/UVs and a render before delivery.

## Rigid-body simulation and embedded bakes

Rigid tools work with Python execution disabled. Start with `inspect_physics`;
carry its `physics_sha256` into `expected_physics` for subsequent operations.
The fingerprint covers qualified rigid sources: world/FPS/gravity/cache range,
body properties, original transforms and base mesh coordinates/connectivity.
It excludes materials, temporary evaluation frame and volatile native cache flags.
Inspection paginates bodies and reports unsupported sources explicitly. A missing
fingerprint means the source set cannot be guarded by this workflow.

1. `configure_rigid_world` sets cache `frame_start`/`frame_end` (1–10000), FPS,
   gravity, time scale, solver iterations and substeps. These affect the whole scene.
2. `configure_rigid_body` binds/configures a named local mesh as `ACTIVE` or
   `PASSIVE`. Choose a convex primitive/hull shape for dynamic bodies; concave
   `MESH` collision is supported for passive bodies. Parameters include mass,
   friction, restitution, damping and collision margin. Existing configured
   parameters use the supplied model defaults when omitted.
3. `sample_rigid_bodies` takes up to 64 `objects` and 64 unique `sample_frames`,
   steps sequentially from cache start, and returns evaluated world matrices.
   It restores the original frame/subframe and retains the unbaked memory cache.
4. `bake_rigid_bodies` evaluates the entire configured range, finalizes the native
   cache, verifies pose checkpoints and writes an embedded-cache `.blend` copy to
   explicit `path` under `library_root`. Existing output is refused. The copy
   contains the **entire scene**, with source binding and start/middle/end poses;
   the active project path and original frame are preserved.
5. `validate_rigid_bake` checks the source binding and checkpoint matrices against
   the live baked cache. Validate after opening a snapshot, before relying on it.
   `clear_rigid_bake` explicitly frees the live cache/binding and rewinds to its
   start; saved snapshot files remain unchanged. `remove_rigid_body` removes only
   the binding, preserving the mesh/object.

For example, after inspecting the source fingerprint:

```json
{"params":{"name":"FloorCollider","type":"PASSIVE","collision_shape":"BOX",
  "expected_physics":"<physics_sha256>","reset_unbaked":true}}
```

Reinspect after configuration changes. Editing an evaluated unbaked cache requires
`reset_unbaked=true`; unknown/localized native cache descriptions are treated
conservatively. A baked cache must be cleared explicitly before editing its
configuration. Direct source edits make a saved bake's binding fail validation.
Native `is_outdated` is reported separately: the qualified installed Blender marks
reloaded embedded data outdated even when source binding and saved poses validate.
The native baked flag alone is not proof of a reusable result.

Sampling/baking return an operation immediately by default. Use `request_id` and
poll `get_operation` / `wait_operation`; `wait=true` is available for short runs.
Progress includes the current frame, completion counts and current free/available
storage. Bake estimates combine current project size, mesh/packed-image heuristics
and body-frame counts; available storage is checked before and during stepping
and before saving. Estimates are not hard output-size bounds. Cancellation works
between frames and restores the original frame, retaining partial memory caches.
Native finalization and `.blend` saving cannot be interrupted midway. Broker
restart does not replay evaluation; process interruption still requires inspecting
the operation outcome and latest completed project/checkpoint.

The qualified surface requires unparented, unconstrained, unanimated static local
collider meshes with positive scales, no modifiers/shape keys, BASE collision
geometry and no rigid constraints/compound colliders or force-field dependencies.
Use separate static proxy colliders or explicitly bake modeling modifiers first.
Body count is limited to 500 and source vertices to two million for fingerprinting.
The embedded workflow requires step-one caches with native disk/external flags
disabled. It does not supply cloth/soft-body/fluid/particle baking or convert rigid
motion to keyframes/GLB clips. Snapshot paths are explicit protected deliverables;
temporary-cache retention/cleanup for other backends remains separate work.

## Fluid authoring and isolated cache bundles

Fluid tools work with Python execution disabled. Call `inspect_fluids` and carry
its `fluid_sha256` as `expected_fluid` on authoring and baking commands. Reinspect
after changing a source. Unsupported dependencies produce an explicit reason and
no usable fingerprint. The current surface supports one static liquid/gas domain,
local mesh sources and static mesh collision effectors. Apply source scale before
configuration; a domain needs nonzero volume. Simulation source fingerprints
cover base meshes, transforms, controller settings, gravity, units, FPS and range.

- `configure_fluid_domain`: named mesh, `type` LIQUID/GAS, `resolution` 16–128,
  `frame_start`/`frame_end` (at most 500 frames inside 1–10000), `time_scale`,
  `gravity_weight` (0–1),
  `mesh_scale` 1–2 and six `use_collision_border_*` wall controls.
- `configure_fluid_flow`: named mesh, `type` LIQUID/SMOKE/FIRE/BOTH, `behavior`
  GEOMETRY/INFLOW/OUTFLOW, density, temperature, fuel, surface distance, initial
  `velocity` and subframes. Flow and domain types must match. Installed native
  parameter ranges are checked before creating/updating controllers.
- `configure_fluid_effector`: static mesh collision, surface distance,
  `use_effector` and subframes. `remove_fluid_controller` removes only an owned
  unbaked controller, preserving its mesh and files.

New controllers use modifier name `Fluid` unless supplied. Configuration values
not supplied use the contract defaults. The initial surface excludes animated or
deforming sources, parents/constraints, upstream modifiers, vertex-group/texture
dependencies, force fields, guiding, noise and secondary particles. The native
FLIP display modifier is disabled; liquid surface baking still uses solver
particles. These tools do not provide a gas volume-material preset or convert
simulation into GLB animation. Gas density checkpoints establish cached solver
output, rather than a finished smoke/fire look.

`bake_fluid` requires scene-edit and library-write permission. Supply a new
`directory`, domain `name` and current fingerprint, for example:

```json
{"params":{"name":"LiquidDomain","directory":"fluid/take-001",
  "expected_fluid":"<fluid_sha256>","threads":2},"wait":false,
  "request_id":"fluid-take-001"}
```

The operation returns immediately by default. Poll `get_operation` or
`wait_operation` and use a stable request ID across reconnects. It saves an
unbaked full-scene `source.blend` copy and launches an owned background Blender
worker. The editing instance's project/frame stay unchanged. The worker bakes
native data plus liquid surface geometry, samples start/middle/end, writes
`asset.blend`, and records cache/project hashes in `manifest.json`. Native cache
files remain in `cache/`; they are not embedded in the `.blend`. Its relative
`//cache` reference supports moving the entire bundle. External dependencies of
unrelated scene objects still need ordinary asset packaging.

`threads` defaults to 2 (maximum 16), `max_bytes` to 2 GiB (maximum 64 GiB), and
`timeout_seconds` to 1800 (10–86400). A conservative cell/frame/project heuristic
is checked against the budget and available space before saving/starting. While
the worker runs, progress reports its phase/PID, bytes/file count, estimated
output and current free space. Disk quota/reserve and timeout are checked during
polling, and final byte size is checked again. These are monitored estimates,
not a filesystem quota or a guarantee against other processes consuming space.

Cancellation stops/reaps only this owned worker and preserves partial output.
Native baking blocks the isolated worker; broker queries remain available.
Source snapshot saving in the editing instance remains noninterruptible. Hash
validation yields progress/cancellation in bounded batches. Broker restart keeps
the active worker/job; an editing-instance crash stops its child and leaves the
operation interrupted with unknown outcome. Do not replay that request blindly.

Open `asset.blend`, then call `validate_fluid_bake` with its bundle `directory`.
Validation checks file hashes, source/job/cache binding, and bounded native
liquid-geometry or gas-density checkpoints; it restores the original frame. It
does not prove every frame or target-engine behavior. Authoring cached imported
projects is refused: open the unbaked source copy, edit, and bake to a new bundle.

`inspect_fluid_job` reports ownership/state, process liveness and disk usage.
`recover_fluid_job` reconciles a running marker only after its recorded parent and
worker are gone. A complete bound manifest is adopted without replay, with native
validation still required; an incomplete result becomes interrupted.
`cleanup_fluid_job` defaults to `dry_run=true`. Explicit application can remove an
owned failed/cancelled partial bundle; interrupted output additionally requires
`include_interrupted=true`. Successful deliverables, live workers, current-project
references, symlinks and unknown entries are protected. Existing output directories
are never overwritten; there is no automatic expiration of explicit fluid bundles.

## Structured skeletal animation

`create_armature`, `bind_mesh` and `inspect_rig` take typed `params` and work with
Python execution disabled. Creation/binding require scene-edit permission;
inspection is available to read-only clients.

Create bones from armature-local `head`/`tail` positions, optional `parent`,
`connected` and `roll_degrees`. The armature object's `location` places the whole
skeleton. Bone names must be unique, connected heads must match parent tails,
and cyclic parent relationships are rejected before submission. Creation
preserves active object and selection and never replaces an existing object.

`bind_mesh` names the mesh in `name` and the skeleton in `armature`:

- `AUTO` (default) uses Blender's native bone-heat weighting.
- `RIGID` assigns all vertices to the named `bone` with weight one.
- `EXPLICIT` accepts `weights`, e.g. `[{"vertex":0,"weights":{"Base":0.5,"Tip":0.5}}]`.
  Each vertex index appears once; weights normalize by default.

Bind an unparented, unbound mesh before animating the skeleton, with bones in an
unconstrained rest pose. Existing armature modifiers and conflicting bone-named
groups are refused. Shared mesh data requires `make_single_user=true`.
`require_complete=true` rejects incomplete coverage. Failed binding removes its
new groups/modifiers and restores placement; an isolated mesh copy may remain.
Native automatic weighting can occupy Blender's main thread; operation/storage
status remains available through the broker.

`inspect_rig` reports rest and evaluated pose matrices/endpoints, bone hierarchy,
and skin coverage, weight sums and sampled influences. Bone results are paginated
with `bone_offset`/`bone_limit`. At most 32 bound scene meshes are inspected
automatically; supply `meshes` for a specific subset. Counts identify truncation.

`create_animation_clip` names the rig in `name` and the new action in `clip`.
Supply `tracks` with a bone, property (`location`, `rotation_degrees` or `scale`)
and vector keyframes. Rotations use XYZ Euler **degrees** in bone-local rest
coordinates; translation uses the same local axes. Clips persist through saving
even when inactive. `activate` defaults true; existing action names are refused.

```json
{"params":{"name":"Arm","clip":"Wave","tracks":[{"bone":"Tip","property":"rotation_degrees","keyframes":[{"frame":1,"value":[0,0,0]},{"frame":12,"value":[45,0,0]}]}]}}
```

Use `set_pose_keyframes` to insert/replace specified keys in a managed clip. Other
tracks/frames remain, and only touched keys receive the chosen interpolation.
`set_active_clip` switches clips, resetting unkeyed bone channels to rest to avoid
leaking the previous pose. Omit `clip` to clear the action and reset pose.
These clip tools support ordinary skeletal actions without constraints, drivers
or active NLA blending. Muted NLA stashes created by glTF import are supported;
selecting a clip disables NLA evaluation for single-action playback. Authoring rotations requires XYZ bones; imported compatible
skeletal actions can be selected using their `slot` identifier when ambiguous.

`inspect_animation` lists paginated actions/slots and reports channel paths, key
counts and ranges for a chosen or active action. The action list is global;
`managed_target` identifies clips authored for a specific rig. A chosen action
must resolve to skeletal channels on that rig.

`sample_animation` evaluates up to 64 `frames`, optionally in a chosen `clip`,
returning bone world endpoints and evaluated geometry for up to eight bound
`meshes`. Samples restore the previous frame, subframe, action, slot and original
pose channels, including on cooperative cancellation. Sampling is available to
read-only keys but needs a local rig for temporary evaluation and can mark Blender
dirty. Use sampled vertices/bounds as deformation evidence; inserted keys alone
do not prove skinning is correct. `inspect_rig` gives the current pose and weights.

## Constraint controls, IK and current-timeline sampling

These typed tools work with MCP Python execution disabled. Use
`create_animation_control` for a named Empty goal or pole helper (`location`,
`display`, `size`). Animate its location, Euler rotation or scale with
`set_keyframes`; those rotations are radians. Helper creation preserves selection
and refuses existing names. Helpers and new constraints require scene-edit
permission; inspection and transient sampling are available to read-only keys.

`inspect_animation_constraints` takes object `name` and optional pose `bone`.
It reports constraint order, native properties/references/validity, keyed or driven
paths, and `constraints_sha256`. Carry that hash as `expected_constraints` into
`configure_animation_constraint`, `remove_animation_constraint` or
`move_animation_constraint`, naming the `constraint` explicitly. Inspection pages
with `offset`/`limit`; the fingerprint still covers the entire stack. It binds
configuration, animation paths, owner parenting and rig rest schema, excluding
animated object/pose transforms and UI expansion/active flags. Reinspect after
edits. Current keyed influence values can change the configuration fingerprint.

Supported settings use a `type` discriminator:

- `COPY_LOCATION`: named `target`, axis `axes`/`invert` flags and `use_offset`.
- `COPY_ROTATION`: target, axis flags and native `mix_mode`.
- `COPY_TRANSFORMS`: target, native `mix_mode` and `remove_target_shear`.
- `LIMIT_LOCATION` / `LIMIT_SCALE`: `minimum`, `maximum`, `use_min`, `use_max`
  vectors and optional `use_transform_limit`.
- `LIMIT_ROTATION`: `minimum_degrees`, `maximum_degrees`, `axes` and optional
  `use_transform_limit`. Enabled minima must not exceed maxima.
- `DAMPED_TRACK`: target and `track_axis`, such as `TRACK_Y` or `TRACK_NEGATIVE_Z`.
- `IK`: pose-bone owner, target, optional `pole`, `pole_angle_degrees`,
  `chain_count` (1–32), `iterations` (1–1000), `use_tail` and `use_stretch`.

All settings have `influence` (0–1) and `mute`. Target references are
`{"name":"Goal"}` or `{"name":"Rig","bone":"Control"}`. Copy/track tools
support WORLD/LOCAL object spaces and WORLD/LOCAL/POSE/LOCAL_WITH_PARENT bone
spaces; they target a bone's head, without custom-space or B-Bone shape mapping.
Bounds have `owner_space`. IK uses the standard LEGACY positional solver and
requires enough ancestors for its explicit chain length. Settings are complete
for the exposed fields: omitted supported fields take their model defaults.
Other unexposed native settings are not an arbitrary RNA editing surface.
Changing a constraint's type requires explicit removal first. Removal/reordering
is by name with a current guard; reordering uses the absolute `index` in the stack.

For example, after binding the mesh and inspecting the tip bone:

```json
{"params":{"name":"Arm","bone":"Forearm","constraint":"Reach","expected_constraints":"<inspection constraints_sha256>","settings":{"type":"IK","target":{"name":"HandGoal"},"pole":{"name":"ElbowPole"},"chain_count":2,"pole_angle_degrees":0,"use_stretch":false}}}
```

Prefer a slightly bent rest chain or another deliberately established preferred
bend. A perfectly collinear chain can be singular in Blender's native solver.
IK inspection adds `ik_diagnostics`: current endpoint/target positions and their
distance, chain length and a collinear-rest warning. Native `is_valid` alone does
not prove that a goal is reachable or that the bend looks right. Inspect the
elbow/pole direction and skin deformation at key and intermediate frames.

Dependency validation models object transforms, individual bones, hierarchy,
constraint targets/poles and IK's effects on chain ancestors. An Empty parented
to the armature object can be safe; a target depending on a solved chain bone
can create a cycle. Independent control bones in the same rig are supported.
The check is conservative: hierarchy dependencies are included even when local
spaces might permit a more specialized setup. Reachable driver dependencies,
custom-space/B-Bone dependencies, unsupported constraints/IK modes and vertex
parenting are refused. Any unsupported constraint on a reachable armature blocks
that rig's dependency closure. Unrelated unsupported graphs do not block edits.
This is not a comprehensive dependency solver for arbitrary imported Blender rigs.

Keyed/driven constraints are inspectable but refused by these editing tools,
including removal, to avoid orphaning animation paths. Existing simple skeletal
clip switching/editing still refuses constraints, drivers and active NLA blending.
Use guarded `set_control_keyframes` to animate object/bone controls and constraint
influence after IK setup; it copies the active clip and preserves source channels.
Use visual baking below to convert supported evaluated motion to a separate portable clip.

`sample_constraint_animation` evaluates the **current** timeline, without changing
active actions, NLA settings or pose channels. Supply `name`, up to 64 unique
`frames`, optional `bones` (up to 32), up to eight bound `meshes`, and `sample_limit`.
It reports evaluated world matrices/bone endpoints and mesh samples/bounds/digests,
restoring the original frame/subframe even after an error or cooperative
cancellation. No clip is switched. It submits asynchronously by default; poll the
operation or use `wait=true` for a small sample. Native evaluation of one frame
can block the Blender thread; cancellation is checked between frames. Evaluation
can mark the project dirty. Use dedicated sequential simulation/cache tools when
physics history matters rather than treating arbitrary frame samples as a bake.

Typed creation allows at most 64 constraints per owner; imported stacks can be
inspected up to 256, with at most 128 results per page. Constraint/helper names
must fit 63 UTF-8 bytes. Dependency inspection allows up to 5000 scene objects
and 2000 bones per rig. Local data and Object mode are required for edits. Native
values/enums/references and dependency checks are preflighted before changing the
stack; unexpected property-application failures attempt to restore its edited
fields or remove the new constraint. Inspect state after an unexpected failure.

## Controller channels and animation curves

`inspect_animation_channels` reads the named object's **active action slot**
without switching clips. It works for object/bone transforms, keyed constraint
influence and imported channels, even when editing is unsupported. Supply `name`,
channel `offset`/`limit` (default 16, max 32), and per-channel `key_offset`/
`key_limit` (default 16, max 128). Results include `animation_sha256`, action/slot,
channel paths/components, key coordinates, interpolation/easing, handle positions/
types, group state, curve modifiers, sample counts and pagination. `edit_blockers`
reports binding-level restrictions; per-channel `typed_editable` additionally
checks supported paths, locks/mutes, sampled data and modifiers. No Python
execution or scene-edit permission is required for inspection.

Both editing tools require scene-edit permission, a fresh `expected_animation`
hash and an unused `output_clip` name (63 UTF-8 bytes). They **copy the active
action, edit the copy and activate the result**. Existing channels and other slots
are copied; other objects keep their original bindings. The original action is
retained with a fake user so the previous clip survives save/reopen. A missing
active action is allowed when inserting initial control keys. This intentionally
creates named clip variants rather than rewriting an action shared elsewhere.
Other objects, including a morph slot's owner, are not rebound to the new clip.

The hash covers the active slot's keys, handles, samples, curve/group/modifier
configuration, binding settings and rotation modes. It excludes current poses and
UI selection. It is not a whole-scene or constraint-stack guard; inspect the
constraint stack separately when changing constraints. Inspection supports 4096
curves, 200000 key/sample points, 512 modifiers and 200000 envelope points. Editing
copies at most 16 slots and 200000 key/sample points across the whole action.

`set_control_keyframes` uses object `name`, optional pose `bone`, `property` and
`keyframes`. Supported properties are `location`, `scale` (three components),
`rotation_degrees` (Euler, three components), `rotation_quaternion` (normalized
WXYZ, four components), scalar `influence` in [0,1], and `custom_scalar` with
`custom_property` naming an existing numeric control. Influence additionally
requires the named owner `constraint`. Bone values use local pose-basis axes;
they are not world-space positions. Euler keys require an Euler rotation mode;
quaternion keys require quaternion mode. Native property bounds are checked.

```json
{"params":{"name":"Arm","bone":"HandControl","output_clip":"Reach_Adjusted","expected_animation":"<inspection animation_sha256>","property":"location","keyframes":[{"frame":1,"value":[0,0,0]},{"frame":24,"value":[0,0.2,0.4]}],"interpolation":"BEZIER"}}
```

The tool supports up to 256 distinct frame/value entries and inserts/replaces
only that property's specified keys. Other tracks and untouched key interpolation
remain intact. `interpolation` is LINEAR (default), CONSTANT or BEZIER; touched
Bézier keys get AUTO_CLAMPED handles. Constraints remain active. A keyed channel
can still be overridden by a constraint or by connected-bone behavior: inspect
actual evaluated motion using `sample_constraint_animation`, endpoints and meshes.
Unlike the simple skeletal clip editor, this tool does not reset the rig pose or
require a constraint-free rig.

`edit_animation_curve` selects an inspected `data_path` and integer `component`,
with up to 256 existing key `frames`. Paths are restricted to existing object/bone
location, Euler/quaternion rotation, scale, named constraint influence and numeric
custom control properties. It
never evaluates a Python path supplied by the caller. Its typed `settings` are:

- `TRANSFORM`: `pivot_frame` (0), positive `time_scale` (1), `time_offset` (0),
  `value_scale` (1), `value_offset` (0). Frame becomes
  `pivot + (frame-pivot)*scale + offset`; value becomes `value*scale+offset`.
  Key and handle coordinates are transformed together. Retiming collisions with
  selected or untouched keys are refused. Native auto handles may recalculate.
- `DELETE`: remove exactly the selected keys; other keys/channels remain.
- `INTERPOLATION`: CONSTANT/LINEAR/BEZIER or SINE/QUAD/CUBIC/QUART/QUINT/EXPO/
  CIRC/BACK/BOUNCE/ELASTIC, plus AUTO/EASE_IN/EASE_OUT/EASE_IN_OUT `easing` and
  optional `amplitude`, `back`, `period`. These settings affect outgoing segments.
- `HANDLES`: `left_type`/`right_type` (AUTO_CLAMPED defaults), with AUTO, VECTOR,
  ALIGNED and FREE also available. Explicit `left`/`right` [frame,value]
  coordinates require FREE and exactly one selected key. Times must bracket
  the key. Coordinate editing uses native curve units: Euler values are radians,
  unlike `set_control_keyframes`' degree convenience property.

```json
{"params":{"name":"HandGoal","output_clip":"Reach_Slower","expected_animation":"<inspection animation_sha256>","data_path":"location","component":0,"frames":[1,24],"settings":{"operation":"TRANSFORM","pivot_frame":1,"time_scale":2}}}
```

Frames may be fractional within [-1048574,1048574]. Blender stores key times as
native floats; inspect the returned actual coordinates. Frames that collapse at
native precision or collide during retiming are refused. Curve values/handles
are bounded to finite magnitudes up to 1e12. Raw curve edits do not normalize an
entire quaternion or enforce a property's evaluated range; validate playback.

Editing requires a local Object-mode object/data, no unsupported object drivers,
active NLA tracks/solo/tweak mode, or blended active action. Verified managed
drivers are retained; directly driven target channels are refused, so key their
upstream control properties instead. At most one action layer and
one keyframe strip are supported. Selected locked/muted curves/groups, sampled
curves, modifiers and duplicate native channels are inspect-only. Unrelated
modified curves are copied intact. Failures remove the working copy and restore
the original action/slot, touched property and frame/subframe. Successful edits
restore the frame/subframe and evaluate the new active clip. These bounded edits
run synchronously; they are not a long-running simulation workflow.

Save clip variants in `.blend`, inspect key/intermediate playback, then use
visual baking for supported constrained skeletal delivery. Existing simple clip
tools retain their constraints/drivers/NLA restrictions and reject mixed object/
bone actions; current-timeline inspection works through the constraint sampler.
Managed export can include previous named clip variants as well as the new one;
inspect the delivered animation list. Driver configuration is described below;
NLA authoring and retargeting remain separate workflows.

## Structured animation drivers

Driver tools use named inputs and native simple numeric expressions. They work
with MCP Python execution disabled. No expression is passed to Python `eval` by
the MCP server. `inspect_animation_drivers` is read-only; configuration, removal
and numeric control creation require scene-edit permission.

Create a scalar control using `set_animation_property`: object `name`, optional
pose `bone`, ASCII identifier `property`, `value`, `minimum`/`maximum` (0..1
by default) and optional `description`. Values/ranges are finite and bounded to
1e12 in magnitude; property names are at most 63 ASCII characters and cannot
start with the reserved `mcpblender_` prefix. Existing nonnumeric, keyed or driven
properties are refused. Native UI ranges are hints for other Blender editing;
this tool enforces its supplied bounds on the value being set. It does not
create a constraint or change arbitrary RNA fields.

Animate an existing scalar with `set_control_keyframes`, using
`property="custom_scalar"` and `custom_property="Bend"`. Managed drivers may
remain active on the same object, allowing a rig's own control to drive a bone.
Directly driven channels cannot also be keyed by the guarded channel tools.

```json
{"params":{"name":"Arm","property":"Bend","value":0}}
```

Inspect `inspect_animation_drivers` with object `name` and optional `offset`/
`limit` (default 32, max 64). It covers object/pose drivers and the mesh's
shape-key datablock. Results include `drivers_sha256`, native paths/components,
expression, variables/ID references/spaces, mapping-curve/modifier configuration,
validity, `is_simple_expression`, `typed_editable` and per-driver `edit_blockers`. Supply that hash as
`expected_drivers` to `configure_animation_driver` or `remove_animation_driver`.
The hash describes configuration, not current animated control values or validity.

Both edits select an explicit typed `channel`:

- `TRANSFORM`: optional `bone`, `property` location/rotation_euler/
  rotation_quaternion/scale and zero-based `component`. Euler outputs use radians;
  quaternion components use WXYZ and require quaternion rotation mode. The tool
  does not normalize a complete quaternion automatically.
- `PROPERTY`: optional `bone` and existing numeric custom `property`.
- `CONSTRAINT`: optional `bone` and named `constraint`, driving its influence.
- `SHAPE_KEY`: named relative shape `key` on the mesh; Basis, shared mesh data,
  linked/overridden keys and mismatched managed topology are refused.

```json
{"params":{"name":"Arm","expected_drivers":"<inspection drivers_sha256>","channel":{"kind":"TRANSFORM","bone":"Forearm","property":"rotation_euler","component":0},"settings":{"expression":"bend*pi/2","variables":[{"kind":"PROPERTY","name":"bend","object":"Arm","property":"Bend"}]}}}
```

`settings.variables` contains up to eight distinct named inputs:

- `PROPERTY`: `object`, optional `bone`, numeric custom `property`.
- `SHAPE_KEY`: mesh `object` and relative shape `key`.
- `TRANSFORM`: `object`, optional `bone`, LOC_X/Y/Z, ROT_X/Y/Z or SCALE_X/Y/Z
  `transform`, native WORLD_SPACE (default), LOCAL_SPACE or TRANSFORM_SPACE
  `space`, and AUTO/default or Euler `rotation_mode`. Rotation inputs are radians.

PROPERTY and SHAPE_KEY use native single-property variables. TRANSFORM uses the
native evaluated transform variable; spaces follow Blender's driver semantics.
Input objects must belong to the current scene. Existing scalar values need not
be world coordinates; a bone custom property is independent of its solved pose.

Expressions are at most 255 UTF-8 bytes and 128 syntax nodes. They support numeric
constants (up to 1e12), named inputs, `pi`, `e`, `frame`, arithmetic + - * / ** %,
comparisons, Boolean operations and conditional expressions. Available numeric
functions are radians, degrees, abs/fabs, floor/ceil/trunc/round/int, sin/cos/tan,
asin/acos/atan/atan2, exp/log/sqrt/pow/fmod, lerp/clamp/smoothstep and min/max.
Attribute access, indexing, strings, comprehensions, keyword calls and arbitrary
functions are refused. Names are ASCII identifiers; reserved functions/constants
and Python keywords cannot name variables. Native function arity and evaluation
still matter: installed Blender must accept the expression as simple and valid
at the current frame. Formulas such as division by zero fail and roll back.
Future inputs can still make a previously valid formula invalid; inspect validity
and sample the animated result. Expressions do not clamp influence, shape or
quaternion values automatically: use `clamp` or suitable formulas as needed.

Typed drivers use direct expression output, without a second F-curve mapping,
modifier or sampled curve. Blender's default identity mapping points are removed
on creation. The original target must not already have action/NLA keys for the
same component. Other action tracks are retained. Configuration changes only the
selected managed driver; it does not copy an object or rename its action.

Dependency checks combine raw property nodes with evaluated object/bone nodes,
parents, supported constraints and IK ancestor effects. A scalar on a rig can
safely drive its bone; feedback through that bone's solved transform is refused.
Unknown reachable constraints, external driver configurations or unsupported
parenting are conservatively refused. Unrelated unsupported components do not
block an independent raw input. This is not a comprehensive arbitrary-rig solver.
Existing constraint configuration still conservatively refuses driver-bearing
reachable objects; create/configure constraints before installing their drivers.

Ownership metadata is checked against real native paths, expressions, variables,
references and curve configuration. Imported, externally changed or no-longer-
resolving drivers are inspect-only; metadata alone cannot claim a different
source dependency. Restore their inputs/configuration or use an explicitly
permitted specialized Python workflow for unsupported repairs. Managed removal
requires the current fingerprint and preserves the current driven property
value; it deletes neither input controls nor source clips.

Unexpected configuration/evaluation failures attempt to restore the previous
driver, or remove the new one and restore its property's previous value. These
bounded operations run synchronously. Inspection allows 256 drivers per datablock,
32 variables/curve modifiers and 10000 mapping/sample/envelope points per imported
driver; authoring has at most eight variables. Graph traversal allows 4096 total
scene drivers, 5000 scene objects and 2000 bones per rig. Validate actual evaluated
motion, skin/morph deformation and save/reopen before delivery. Skeletal drivers
can use visual baking below; morph/object-motion baking remains separate work.

## NLA action layering and composite playback

NLA tools compose existing action slots on object/pose controllers or relative
shape-key datablocks. They require no Python execution. `inspect_nla` is
read-only; all authoring requires scene-edit permission. Supply object `name`
and `target="OBJECT"` (default) or `target="SHAPE_KEYS"` for the mesh's keys.
Shape editing requires independent local mesh/key data. Linked/overridden data,
NLA tweak mode and ambiguous duplicate track names/multiple-solo states are
refused for editing.

`inspect_nla` returns the **bottom-to-top** track stack, mute/solo/lock state,
strip types/native settings, selected action slots, source-action content hashes,
control-curve hashes, management/edit support, active action/blending and
`nla_sha256`. Track pagination uses `offset`/`limit` (default 16, max 64).
Carry the fresh hash as `expected_nla` into every edit. The guard includes all
tracks and referenced slot keys/handles/modifiers; editing a source clip invalidates
the previous guard. UI selection and evaluated strip influence/time are excluded.
The native influence envelope is hashed instead. Ownership of a strip is separate
from its source action's editable content.

Author clips first with the skeletal/morph/controller tools. Create layers using
`configure_nla_track` with a unique `track`, `mute`/`solo` flags (false defaults),
and optional `after_track` for insertion after an existing layer. Without it a
new track appends on top. Existing managed tracks can change flags; use
`move_nla_track` with absolute `index` to reorder. Moving a managed track after
another track preserves imported neighbors. Inserting at index zero requires
all tracks up to its original position to be supported/managed: Blender's native
insertion API cannot insert before an existing first track, so that prefix is
rebuilt. A no-op move returns the current state. Track names fit 63 UTF-8 bytes.
Solo follows Blender's single-solo behavior; editing/rebuilding a different
non-solo layer preserves the existing solo layer.

`configure_nla_strip` selects `track`, a globally unique `strip` name, and typed
`settings`. The track must be managed and its existing children supported:

```json
{"params":{"name":"Arm","track":"Gesture","strip":"ReachSlow","expected_nla":"<inspection nla_sha256>","settings":{"clip":"Reach","start":21,"action_start":1,"action_end":25,"scale":2,"repeat":1,"blend":"ADD","influence":0.5,"blend_in":4,"blend_out":4}},"wait":true}
```

Settings name an action `clip` and optional explicit `slot`. The tool selects a
unique compatible OBJECT/KEY slot, validates all channels against existing
transform/custom-control/influence or shape-weight paths, and refuses channels
that are already driven. Path compatibility does not establish semantic rig
retargeting. Source actions must be local and contain animation channels.
Only the selected slot contributes to this target; other objects/slots are not
rebound.

The source window is [`action_start`,`action_end`]. Its timeline duration is
`(action_end-action_start)*scale*repeat`, beginning at `start`. Scale is .0001..
1000; repeat .1..1000 permits partial cycles. `reverse` reverses action playback.
The computed duration must be at least .001 frames, fit the native timeline,
and leave space for its fades. `blend` supports REPLACE, ADD, SUBTRACT, MULTIPLY
and COMBINE. `extrapolation` is NOTHING (default), HOLD_FORWARD or HOLD. Static
`influence` lies in [0,1]; `blend_in`/`blend_out` are timeline-frame fades whose
sum cannot exceed duration. `mute` suppresses a strip. Omitted fields take their
schema defaults; configuration replaces the full exposed settings.

On a single track strips cannot overlap. Crossfades/overlays use separate tracks.
All times are native floats within [-1048574,1048574]. The tool checks actual
native timing/fade values and refuses silent clamping or excessive rounding.
Native action synchronization and auto blends are disabled for typed strips.
Blender otherwise overwrites unanimated strip influence, so the tool builds an
owned linear influence envelope that combines weight and fades. It does not
pretend that setting a static native influence alone changes playback.

`configure_nla_playback` sets `use_nla` (true default), active-action blend,
influence and extrapolation. An active action is a separate layer and can
cover the NLA result. Set `clear_active_action=true` explicitly when the NLA
stack should supply the whole motion; the old action is retained with a fake
user. The tool does not silently stash or delete a source clip. Optional
`reset_base=true` requires this explicit clearing. For rigs it resets bone
transforms to rest while preserving object transforms. Numeric custom controls
remain governed by their own channels/properties.

For shape targets, `reset_base=true` creates/replaces a managed **Shape Base**
layer below the other layers, with a generated zero-weight action. Native NLA
uses an RNA default of one for shape weights; setting static weights to zero is
insufficient for weighted/additive layers. The explicit base makes those layers
blend from zero. It excludes directly driven weights, uses a short constant clip
with HOLD extrapolation, and therefore avoids a huge source-animation range.
Creating this foundation requires a wholly managed supported stack and room for
one extra track when none exists. Repeating the reset retains one base track;
obsolete generated actions are removed only if unused and unchanged. Modified
or shared generated actions and all user source clips are retained. Keep the
zero base beneath additive shape layers; ordinary track movement remains explicit.

`remove_nla_strip` rebuilds its managed track without that strip.
`remove_nla_track` removes an explicitly selected managed track containing only
supported children. Source actions receive fake users and remain available.
Imported, externally modified, locked, transition/meta/sound and arbitrary
animated-control strips are inspect-only; ordinary track flag changes do not
rewrite their contents. Metadata recipes are matched against native action/
slot, timing, blend state and envelope before they can rebuild a strip.

Strip edits/removal, track movement and playback configuration submit
asynchronously by default; poll the operation or use `wait=true` for short work.
Rebuilding stages complete muted replacement tracks before removing any source
tracks. Progress reports strip counts/fraction and current storage. Cooperative
cancellation during staging discards staged tracks and restores frame/active
track, retaining the source stack. Ordinary timing/compatibility failures also
happen before replacement. The short final native replacement is not interrupted;
process crashes/unexpected commit-phase native failures use existing checkpoints
and require inspection/recovery. It is not a filesystem transaction.

Limits are 64 final tracks and 512 top-level strips; imported nesting is inspected
up to four levels/128 children, eight control curves and 10000 control points per
strip. Existing action-slot bounds also apply. Temporarily staged tracks do not
count as final user layers. Save `.blend` to retain editable composition. Sample
its **current** timeline with `sample_constraint_animation`, including skin/morph
meshes. Simple clip switching/sampling/editing retains its active-NLA guard;
mute layers before using those tools to revise a source action, then update the
strip reference or re-inspect the stack guard. Existing render commands render
the current timeline. For portable skeletal delivery, visually bake the composite
and export only its baked rig/skin, then reimport and compare playback. General
morph/object-motion composite baking and animated strip-time/control authoring
remain separate workflows.

## Visual skeletal animation baking

`bake_constraint_animation` captures the **current evaluated timeline**, including
supported controller/constraint motion, into a new independent rig and managed
skeletal action. It requires scene-edit permission and works with MCP Python
execution disabled. It leaves the editable source rig, constraints, actions and
meshes in place. It does not switch the source clip or change the timeline range.

```json
{"params":{"name":"Arm","output_rig":"Arm_Baked","clip":"Reach_Baked","meshes":[{"source":"ArmSkin","output":"ArmSkin_Baked"}],"frame_start":1,"frame_end":48},"wait":true}
```

All output object names and the clip name must be unused and fit 63 UTF-8 bytes.
`meshes` is optional; each entry names a source and a new output. Armature data,
mesh data and the action are independent; materials remain shared. The copied
rig has no object/pose constraints, drivers or NLA tracks. It is unparented and
retains the source object's stationary world transform. Bone names, rest data,
vertex groups and skin settings are retained. Every bone receives location,
continuous-sign quaternion rotation and scale keys at every integer frame, using
linear interpolation. The output action is active, persistent and compatible
with existing clip inspection/sampling and managed GLB export.

Before success, a second native evaluation compares every bone's full world
matrix and every copied mesh vertex's world position against the source at each
integer frame. `tolerance` defaults to .0001 (range .000001.. .01); it is an
absolute limit for both world matrix components and world vertex distances.
Results include `frame_count`, range, output names, `max_pose_matrix_error`,
`max_vertex_world_error` and tolerance. Subframe interpolation, normals, arbitrary
simulation history and other unexamined properties are not certified by these
checks. An unrepresentable shear or other pose/deformation mismatch fails the
operation instead of returning an unchecked asset.

This bounded version requires Object mode, pose evaluation, single-segment bones,
stationary rig/mesh object transforms throughout the range and simple skins:
one enabled vertex-group Armature modifier targeting the source, with no bone
envelopes, shape keys, mesh animation/constraints or other modifiers. Meshes must
be unparented or object-parented to the source rig. Animated object transforms
are explicitly refused; their motion is not silently discarded. Source rig
constraint/driver/NLA evaluation is sampled as-is; this is not an authoring tool
or comprehensive qualification of arbitrary imported rigs.

Limits are 500 consecutive integer frames, 256 bones, 32768 bone-frame samples,
eight meshes and two million vertex-frame comparisons. The operation submits
asynchronously by default; poll it or use `wait=true` for short ranges. Progress
separates baking and verification. Cooperative cancellation and ordinary errors
remove newly created objects/data/action and restore the source frame/subframe.
Native frame evaluation and individual key insertion block until the next check;
process crashes are handled by existing checkpoint/recovery workflows rather
than this in-process cleanup. No external cache bundle is created by the bake.

Save the `.blend` to retain the editable source and baked assets. Select only
the baked rig/meshes for `export_glb` or use the structured object export tool;
otherwise exporting both versions also includes the editable source. Validate
portable delivery by reimporting and comparing playback at key/intermediate
frames. Shared materials remain editable through the existing material tools.

## Static asset LOD chains

In default `deformation="STATIC"` mode, `inspect_lod_source` takes mesh `name`
and reports its current evaluated viewport
geometry, UV maps/render map, material slots and used regions, supported named
attribute schemas, surface bounds and `source_sha256`. The source must be visible
in the current scene/view layer, Object mode, with a finite invertible transform.
Object animation/constraints and shape keys require separate LOD workflows.
Linear armature bindings use SKINNED mode below. Upstream procedural modifiers are evaluated at the current frame;
this creates a static snapshot rather than retaining their generator or physics.
The inspection never edits the source. Materials remain shared by reference.

Pass the fingerprint as `expected_source` to `generate_lod_chain`, choose a fresh
`chain` name (up to 40 UTF-8 bytes), and supply decreasing per-level budgets:

```json
{
  "name": "Building",
  "chain": "Building_LODs",
  "expected_source": "<source_sha256>",
  "levels": [
    {"method": "COLLAPSE", "triangle_budget": 4000},
    {"method": "COLLAPSE", "triangle_budget": 1000}
  ],
  "max_relative_error": 0.05
}
```

The source must have more triangles than the first reduced budget. The tool
creates a new named collection, an Empty `<chain>_Root` at the source's world
transform, an independent `<chain>_LOD0` snapshot and up to seven reduced meshes.
Every reduced level is built independently from LOD0, meets its own budget and
must actually have fewer triangles than the previous level. It preserves the
editable source and does not hide or move it. LOD0 is initially visible; other
representations are hidden in viewport/render. Move the generated root to stage
comparisons without overlapping the source. All outputs use identity stored local
transforms; arbitrary edits to individual levels require a fresh chain.

Strategies:

- COLLAPSE adapts native decimation ratio to the requested budget, triangulating
  the result, with at most eight evaluations. Small budgets can still fail quality
  checks or produce unusable geometry; success is not guaranteed by a ratio.
- PLANAR uses native limited dissolve with `angle_degrees` (default 5), protecting
  UV/material/normal/seam/sharp delimiters and boundaries. Useful for planar hard
  surfaces; failure to meet the budget refuses rather than silently changing the
  requested angle.
- UNSUBDIVIDE reverses a regular subdivided grid with `iterations` (1–6, default 1).
  It is not a general reduction method for arbitrary triangle topology.

All outputs require finite positions/normals/UVs, retained UV names/render map,
material slots, presence of each used material index and supported named attribute
schemas. Presence does not prove exact texture boundaries, mask semantics or
material appearance. Native topology reduction interpolates data; inspect thin
parts, seams and small material regions. `transfer_normals=true` (default) uses
nearest-face-interpolated source custom normals; false explicitly accepts native
recomputed normals. LOD0 preserves the source snapshot's normals.

`error_samples` (16–4096, default 512) samples raw vertices and triangle centers in
both directions against nearest triangle surfaces. The report includes maximum
and RMS distance and maximum distance relative to the source bounding diagonal.
`max_relative_error` (default 0.1) is a hard threshold for that sampled measurement.
It is measured in asset-local coordinates, and does not establish an exhaustive
Hausdorff bound, screen-space silhouette, foliage density or behavior under
nonuniform world scale. Open the render and review the asset at intended sizes.

`inspect_lod_chain` reports current geometry/visibility/recipes/quality, ownership
issues and `chain_sha256`. Carry it as `expected_chain` into
`activate_lod_level` with integer `level` or into `export_lod_chain`. The guard
covers stored mesh content, UVs/attributes, normals, material assignments, root
transform, relative transforms and representation visibility. Shared shader/image
contents are not frozen. Missing/modified geometry, added modifiers/constraints/
animation, changed collection membership or child transforms refuse management
and export. Moving the root is allowed and changes the fingerprint. Source
staleness/unavailability is informational because outputs are independent static
snapshots; regenerate them when the source revision should be adopted.

`activate_lod_level` chooses one representation for viewport/render. This is manual
representation selection, not an automatic distance-switching system. Original
source objects stay untouched and can overlap the chain; stage them appropriately
for screenshots. Do not rely on an inactive hidden object's unevaluated world
matrix; managed guards use its stored transforms.

`export_lod_chain` takes a new `directory` under the active library. It exports
`level_00.glb`, `level_01.glb`, etc. and `manifest.json`; it does not overwrite a
bundle. Each representation is selected/unhidden temporarily, then its state and
the user's selection are restored. Native glTF surface-material conversion applies;
bake procedural shaders when the target needs PBR equivalence. The worker refines
storage estimates from geometry and texture pixels, reports current storage in
progress, and checks available space before output. Estimates are heuristic.

Before publishing the directory, an independent binary parser checks embedded
buffers/images, index bounds, finite positions/normals/UVs, unit normals, triangle
counts/budgets and surface position bounds converted to glTF +Y-up coordinates.
A manifest records file hashes, geometry/quality/budgets and source/chain guards.
`validate_lod_export` re-reads those files independently, refusing missing,
modified, oversized or symlinked members. This does not replace rendered or
native re-import checks, verify every texture/shader visually or configure engine
LOD switching. Each GLB is a separate representation; skeletal validation is described below.

Generate/export default to queued operations; poll/wait/cancel, or pass `wait=true`.
Native evaluation/decimation/export cannot cancel internally. Cooperative errors
or cancellation remove owned generated objects/data or the owned export staging
directory. Publication happens after validation. Process crashes can leave an
interrupted staging directory; crash-time reconciliation/retention is separate.
Explicit completed bundles and source assets are not temporary-retention targets.
Limits: 250,000 snapshot vertices, one million corners, 500,000 triangles per
level, eight representations total and 512 MiB per validated GLB. Broader skinning, foliage reconstruction/impostors/collision/
shadow proxies and
reusable collection-instance/batch delivery workflows remain separate milestones.

## LOD ownership, source visibility and replacement

Use `inspect_lod_management` by `chain` for lifecycle work. It reports a separate
`management_sha256`, removal/rebuild eligibility and blockers, content issues,
source visibility/freshness, shared meshes that will remain, and a
`suggested_rebuild` recipe. The management guard includes native ID identity,
references, membership and visibility, so inspect again after edits or reopening
a scene. It is distinct from the ordinary `chain_sha256` used for sampling/export.

`configure_lod_source_visibility` takes `expected_management` and optional
`hide_viewport`/`hide_render` flags. This hides duplicate original geometry while
keeping the source mesh and controllers intact. These are global object flags,
affecting every scene using that source. Keyed/driven targeted flags refuse edits;
cooperative cancellation restores flags. Show the source before fresh source
inspection, generation, sampling, rebuild or package preparation. A hidden source
can be reported as unavailable for rebuild while its owned chain remains removable.
This tool does not change source geometry, delete sources or automatically choose
which other chains should be visible.

To rebuild, obtain a fresh management report and source guard. Start with
`suggested_rebuild`, adjust the requested `levels`/quality settings as needed, and
call `rebuild_lod_chain` with `expected_management`. The recipe uses the same
fields as `generate_lod_chain`, including `name`, `expected_source` and deformation
mode. Newly generated chains record their generation settings. Older valid
metadata without those settings reconstructs level recipes and known skin profile
fields, using explicit model defaults for unknown options; review these defaults.

Rebuild defaults to a queued job. A complete replacement is generated and checked
before any original names change. It then takes the public collection/root/level
names and parent collection links. Static root placement and parent binding are
preserved by default; skin roots must remain compatible with their rig binding.
Root instancing/constraints/animation that replacement cannot preserve block rebuilding.
`preserve_placement=false` explicitly uses the new source's generated placement.
`preserve_visibility=false` resets collection/root/level visibility to generated
defaults. Otherwise existing flags are carried over; if the selected visible level
was removed by shortening the chain, an available level is made visible.

Selection and the active object follow corresponding replacement levels where
possible. Removing a selected level without a counterpart clears that selection.
Ordinary generation, verification and cooperative cancellation failures before
final deletion restore original IDs, names, links and selection and delete owned
replacement data. The final native batch deletion is noninterruptible; process
crash rollback at that boundary is not established. Source geometry/rigs/Key
controllers and clips remain authoritative and are not replaced or purged.

`remove_lod_chain` takes `expected_management`. It can remove an unambiguously
owned chain even when its derived mesh contents have been edited or its source is
unavailable. It refuses missing/changed membership, foreign object collection
links, external native object/collection/Key references, attached rigid bodies and
linked/overridden ownership. Shared or fake-user mesh data is preserved; materials,
source meshes, rigs and clips are never generically purged. This does not infer
string-name references in scripts or recipes. Rebuild similarly refuses external
native references rather than redirecting their targets silently.

These operations manage existing marked chains. External/manual geometry can be
adopted using the following workflow. Automatic controller detachment/migration
and interrupted-process scene replacement reconciliation remain separate. An
immutable exported package remains a snapshot; replacing its live source chain
requires planning and exporting a fresh package revision.

## External and manually authored LOD adoption

Use `inspect_lod_adoption` with canonical source `name`, `deformation`
(`STATIC`, `SKINNED` or `MORPH`) and ordered `inputs`. Each input has a `name`,
optional `material_slots`, and optional `uv_maps`. The canonical source supplies
LOD0; provide only the reduced levels, from near to far. There must be 1..7
inputs, each with at least four triangles and strictly fewer triangles than the
previous level/source. All inputs and the source must be visible local meshes
in the current view layer. The inspector reports normalized geometry, sampled
rest-surface errors, `canonical_source_sha256` and a combined `source_sha256`.
Inspection creates only temporary copies, which it removes before returning.

```json
{
  "name": "PropSource",
  "deformation": "STATIC",
  "inputs": [
    {"name": "HandEditedNear", "material_slots": [0],
     "uv_maps": {"ImporterUV": "UVMap"}},
    {"name": "HandEditedFar", "material_slots": [0]}
  ],
  "input_geometry": "EVALUATED_STATIC",
  "max_relative_error": 0.1,
  "error_samples": 512
}
```

The combined guard covers source content/binding, input geometry and effective
placement, remapping and quality settings. Pass it as `expected_source` to
`adopt_lod_chain`, together with the same planning fields and a fresh `chain`
name (at most 40 UTF-8 bytes). It is **not** the guard from `inspect_lod_source`.
Creation is a queued operation by default. Failed validation, stale guards or
cooperative cancellation remove owned copies without editing the originals.

`EVALUATED_STATIC` snapshots current viewport geometry, applying input modifiers;
it refuses input armatures, shape keys and object animation/constraints.
`RAW_BASIS` explicitly reads raw reference-key/basis geometry, ignoring incoming
modifiers, skin, morph values and their animation. Current evaluated object
placement still determines alignment. Mesh-data animation is refused in raw
mode. Neither mode imports incoming animation controls. Owned copies are baked
into the canonical source's local coordinates, including affine shear and mirror
winding/custom-normal correction. Input weights are discarded. Originals retain
their geometry, transforms, materials, groups, modifiers and controls.

Without remapping, material slot names/order and UV names/order/render map must
match the canonical source. `material_slots` maps every input slot index to a
canonical slot index; one virtual index represents a mesh without materials.
`uv_maps` maps existing input layer names to existing canonical layer names;
collisions refuse. Both change only owned copies. The canonical render-UV
choice and layer ordering must still match. Materials remain shared canonical
datablocks; texture/shader contents are not baked by adoption.

`preserve_material_regions=true` requires every used canonical material region
to remain represented. `preserve_attribute_schema=true` requires canonical named
attribute schemas to remain present. Either may be explicitly disabled for an
authored reduction that intentionally drops regions/attributes; UV/material slot
layout still has to match. `max_relative_error` and `error_samples` constrain
sampled bidirectional rest-surface error. Input normals are retained through
coordinate normalization rather than replaced by source normals.

For `SKINNED`, weights are interpolated barycentrically from nearest triangles
on the canonical rest surface, then normalized/pruned to `skin_max_influences`
(default four). The canonical rig and linear binding remain authoritative.
For morph-bearing sources, relative deltas and masks are transferred using the
existing morph LOD profile; output values/mutes follow source Key controls.
`pose_frames` and `max_pose_error` govern sampled current-timeline deformation
checks, with isolated-key checks for morphs. Anatomically close surfaces can
produce undesirable nearest-surface transfers: inspect representative poses.
The planner validates rest geometry; creation can still refuse deformation that
fails its pose/key checks. This is not exhaustive silhouette or all-frame proof.

`inspect_lod_chain` and `inspect_lod_management` include `adoption` provenance,
including the original input configuration. Managed geometry is a snapshot:
editing an original input does not change its already adopted levels. Inspect
adoption again with revised inputs/settings, obtain fresh `expected_source`
and `expected_management`, and call `readopt_lod_chain`. It accepts the adoption
fields plus `preserve_placement`/`preserve_visibility`, both true by default.
Re-adoption uses the same staged verification, public-name handoff, reference
refusals and cancellation rollback as rebuilding. Inputs cannot be members of
the chain being replaced. Re-adoption may also replace a generated chain with
manual levels. The final native deletion remains noninterruptible; scene
replacement crash rollback is not established.

Ordinary `rebuild_lod_chain` instead regenerates levels with automatic reduction
at the adopted triangle budgets; it does not reproduce authored topology. Its
suggested generation recipe makes that distinction explicit. Use re-adoption to
retain revised hand-authored geometry. Existing export, package validation and
owned removal work with adopted chains, preserving the original inputs.

## Skeletal LODs and sampled deformation validation

Use `inspect_lod_source(name=..., deformation="SKINNED")` for raw rest mesh
geometry, named vertex weights, original rig/binding, known rig-animation guard
and suggested pose frames. Pass that guard to `generate_lod_chain` with the same
`deformation="SKINNED"`. Static-mode inspection refuses armature deformation
rather than silently flattening it.

The first supported skin workflow uses one enabled linear Armature modifier and
no additional mesh modifiers, envelope mixing, preserve-volume/DQ, mask, multiple
modifier mixing. Relative shape keys can transfer as described below. Bind the intended geometry before skinning. The
source mesh has no object constraints/animation or mesh-data animation; it can be
unparented or object-parented directly to its rig. The rig is in Object/POSE
position with at most 256 single-segment bones and no armature-data animation.
Rig object/bone animation, constraints and drivers can continue evaluating.
Source deform weights must already be finite, normalized and complete with at
most four positive influences. Use `inspect_skin_weights`/`repair_skin_weights`
explicitly before generation if required.

LOD0 copies source rest geometry and weights. Reduced levels retain native
interpolated deform layers; `skin_max_influences` (1–4, default 4) caps/prunes and
normalizes their unlocked derived weights without changing the source. This
whole-chain limit also includes LOD0, which is not silently reweighted. Named
nondeform masks survive native interpolation. Source group-lock flags are copied;
derived weights are computed rather than edits to the locked source data.

For COLLAPSE, `skin_joint_importance` (0–1000, default 10) protects mixed and
rapidly changing bone-weight regions with a temporary native reduction group.
Zero disables protection. The group is removed before publication, and the
original source never receives it. Joint protection can prevent satisfying an
aggressive triangle budget; adjust the budget/profile rather than treating a
rest-only match as good deformation. PLANAR/UNSUBDIVIDE retain their existing
strategy constraints and still undergo pose checks.

`pose_frames` optionally provides 1–16 distinct finite frames, including fractional
frames, within ±1048574. Otherwise suggested current/start/mid/end frames derive
from the active action/nonmuted NLA ranges, with the scene range as fallback.
Choose frames that stress the actual motion and joint extremes. The operation
evaluates the current timeline without switching clips. Each source/LOD surface
comparison must meet `max_pose_error` (default 0.1), in addition to the rest error
threshold. Vertex/triangle-center samples lie on triangulated surfaces, including
bent nonplanar quads; reports remain sampled rather than exhaustive error bounds.
Pose verification is limited to ten million source/target vertex-frame samples.

Generated meshes retain the original rig and follow its clips and object motion.
Their root copies the source's parent/bind transform. Move the rig when moving a
skeletal asset; changing the generated root's bind transform invalidates ownership.
Geometry, group definitions/memberships, modifier binding and rig rest definition
are guarded. Changing animation can leave the geometry valid while making prior
pose measurements stale: `pose_validation_inputs_changed` reports known source/
rig-definition changes. Arbitrary external control/dependency values are not
frozen by these guards. Stored `pose_validation` records refer to their original
frames/inputs, not a perpetual animation-quality certificate.

`sample_lod_chain` takes `chain`, `expected_chain`, optional `pose_frames`,
`error_samples` and `max_pose_error` to compare the current source and derived
skins again. It is a read-authorized queued operation; `wait=true` blocks for the
result. Frames and representation visibility restore on success, error or
cooperative cancellation. Generation failure removes all owned meshes/groups/
collection/root while retaining source data and rig/clip bindings. Native calls
are noninterruptible internally; crash-time atomicity is not implied.

For validated skeletal delivery without morph targets, call `inspect_lod_export` with `chain` and
`animations` (default true). This read-only planner reports export blockers,
compatible clips, the reference frame, `chain_sha256` and `animation_sha256`.
Carry those fingerprints as `expected_chain` and `expected_animation` into
`export_lod_chain`, with a fresh `directory`. The animation guard comes from this
planner, not the source-inspection pose signature. Export writes one self-contained
GLB per level and a manifest, then validates everything before publication.

Animated bundles currently require local, non-overridden rig/data/actions and
simple object/bone transform clips: no constraints, drivers or active NLA blending.
Bake composed control/NLA motion first. The inventory includes the active action,
managed rig actions and actions in NLA strips, including muted stashes. There must
be 1–32 compatible clips, each with integer endpoints within native frame limits
and a span of at most 10,000 frames. Fractional endpoints are explicitly refused.
Full action ranges export independently of the scene playback range. Each GLB
clip starts at zero seconds; map back with `native_frame_start + time * fps` from
the manifest, including clips originally starting at a negative frame.

Use `animations=false` for a bind-only bundle without clips. This also permits
controlled rigs whose live animation cannot pass the simple-clip checks. The rig
and meshes use the captured reference frame's object transforms with the rest
skeleton; unkeyed object channels in animated clips retain that reference baseline.
Moving the existing rig moves the generated meshes. This workflow reduces meshes,
not skeletons. Morph-bearing chains can use the timeline-baked delivery described below.

The independent decoder checks every exported weight, named joints, inverse binds,
curves and finite normalized skin data. It replays the rest pose plus 3–9 sampled
frames per clip (`animation_samples`, default 3), comparing every joint matrix and
representative corresponding vertices against native Blender. Representatives
include distributed vertices and extrema for each weighted joint. `skin_tolerance`
(default 0.001) gates vertex distances and matrix-component differences. Native
glTF drops tiny influences; a maximum weight difference of 0.0004 is permitted
and recorded, while the geometric gate still applies. Nondeforming bone-named
masks are removed only from a temporary export copy and remain in authored data.
Skinned POSITION-buffer bounds reflect native export's world-baked reference
geometry rather than undeformed mesh-local coordinates.

The manifest records clip frame ranges, FPS, reference frame, hashes and sampled
proofs. `validate_lod_export` independently decodes files and recomputes recorded
playback fingerprints (nine significant digits); it does not reevaluate Blender.
The decoder supports this dense, four-influence native export profile, not every
possible glTF encoding. The manifest is limited to 8 MiB, each GLB to 512 MiB,
and native proof work to ten million vertex-frame samples per level. Storage
estimates include geometry, sampled export keys and textures; progress reports
current free space. Frame, action, metadata, visibility and selection restore on
success, ordinary failure and cooperative cancellation. Crash-time staging
reconciliation remains separate. Sampled checks do not certify every animation
frame, silhouette, shader appearance or engine playback; re-import and visually
review representative results before delivery.

## Morph-aware LODs and source controls

Use `deformation="MORPH"` in `inspect_lod_source`/`generate_lod_chain` for a
relative-shape-key mesh without object animation/constraints, modifiers or mesh-data
animation. For an existing supported linear skin with relative keys, use
`deformation="SKINNED"`; morph transfer is automatic. Source keys must be local,
relative, finite and topology-compatible, with a non-Basis key. Disable
`show_only_shape_key`. The limit is 64 keys including Basis and four million
source key-vertex entries. Absolute shape animation is unsupported.

Generation reduces the raw Basis, independently of current morph weights. LOD0
uses exact vertex correspondence; reduced levels project their rest vertices onto
source Basis triangles and interpolate relative deltas barycentrically. The target
rest position is retained. Source vertex-group masks multiply each source delta
before interpolation, then are baked into target key coordinates. Generated key
mask fields are empty, avoiding a second mask multiplication. Names, relative-key
relationships, slider ranges and interpolation settings transfer. Keys whose
relative parent follows them in the source list may be reordered to create their
parent first; reference keys by name. This transfers offsets, not corrective
sculpting or topology reconstruction; inspect complex facial folds and seams.

Each generated non-Basis value is driven from its original source Key value and
mute flag. The original actions, driver expressions, external controls, NLA tracks
and clip selection remain authoritative and unchanged. Continue editing animation
on the source, rather than attempting independent clip editing on driven LOD keys.
The source Key datablock remains a required controller dependency. Keep it in the
editable `.blend` delivery. Generated shape geometry is independent, while weights
follow the source; this is not a detached copy of every clip/driver graph.

`morph_transfer` records key count, projection distance, mask treatment and a
content/controller-link fingerprint per level. `morph_validation` measures every
isolated relative delta at unit weight, even for keys absent from the current
animation. These sampled bidirectional surface errors must meet `max_pose_error`,
as must current-timeline combined deformation at `pose_frames` (or recommended
frames). Combined skin/morph chains also evaluate the original rig. Rest geometry
still meets triangle, UV/material/normal and `max_relative_error` gates. Samples
are not exhaustive pose, silhouette, fold or shading guarantees.

`sample_lod_chain` works for morph-only and combined chains and restores frame/
visibility on success, failure and cooperative cancellation. It follows the current
controller timeline without switching actions. Changing source key coordinates,
relative relationships or masks, losing the source controller, or changing generated
keys/controller links invalidates ownership. Source animation/weight changes keep
transferred geometry usable but can make stored pose measurements stale;
`pose_validation_inputs_changed` compares the recorded controller snapshot.
Arbitrary external dependencies are not frozen. Inspect and resample after edits.

Use `save_blend` to preserve the authored morph chain and its shared controller.
For detached GLB delivery, use the timeline-baked bundle workflow below. Source
snapshots, failed generation and cancellation remove owned temporary meshes/Key
data; source animation is never cleared or switched during transfer. Crash-time
recovery is separate from ordinary failure cleanup.

## Timeline-baked morph LOD bundles

`inspect_lod_export` and `export_lod_chain` support morph-only and combined
skeletal/morph chains. The planner returns `export_profile="BAKED_MORPH_TIMELINE"`,
current chain/animation guards, chosen clips, reference frame and blockers. Carry
`chain_sha256`/`animation_sha256` as `expected_chain`/`expected_animation` into export,
with a fresh `directory` under the library. Use the same `timeline_clips` in both
calls, for example `[{"name":"Walk","frame_start":1,"frame_end":33}]`.

Each named range samples the **currently evaluated timeline**: active source
clips, NLA composition, driver controls, solved rig constraints and rig object
motion. It does not switch to inactive actions or infer a batch of all authored
clips. Select/compose the intended source timeline before planning. Up to 32
uniquely named ranges can overlap or start at negative frames. Endpoints are
strict integers, inclusive, within native frame limits; each range spans 2–10001
frames. When omitted, animated export uses one `Timeline` range from the scene
playback bounds. `timeline_clips` is specific to morph-bearing bundles; passing it
to static/simple skeletal bundles refuses rather than ignoring it.

The exporter creates owned temporary mesh/Key and optional rig copies. It flattens
relative morph deltas onto Basis while retaining target names and already-baked
masks, clears copied drivers/constraints, and keys visual object/bone transforms
and effective morph weights at every integer frame. Quaternions maintain sign
continuity and keyed interpolation is linear. Native proxy evaluation must match
the original level's evaluated vertices and all joint matrices at every baked
frame within `skin_tolerance` (default 0.001). The authored rig, Key controls,
actions, drivers, NLA and masks remain intact. The exported files have baked
animation and embedded textures, without the source Key/controller dependency.

The first range's starting frame supplies the bind reference for animated export.
Each clip starts at zero seconds: native frame = `frame_start + time * fps` using
manifest metadata. `animations=false` produces a bind-only morph bundle with no
clips, preserving the original fractional reference frame and effective morph
weights; the skeleton is exported in rest binding. Omit `timeline_clips` in that
mode. This is not a static snapshot of a constrained bone pose.

Before publication, independent binary decoding checks every exported Basis
vertex, each target offset, optional normalized skin weights and inverse binds
against native rest data. Matching coincident vertices must agree in target
coefficients and weights. It then compares decoded world vertices and joint
matrices against the original evaluated timeline at 3–9 integer frames per clip
(`animation_samples`, default 3). Default-weight and isolated-target playback
fingerprints cover every target, including ones absent from current motion.
`skin_tolerance` gates vertex distances and matrix-component errors; the existing
0.0004 allowance for native tiny-weight filtering remains separately reported.

The manifest records hashes, target/clip inventory, native frame ranges/FPS,
reference, all-frame proxy errors, sampled decoded errors and per-target proofs.
`validate_lod_export` independently replays them and checks their inventory, time
mapping, durations, bounds and declared error limits. Missing/duplicate target or
animation proofs and inconsistent FPS/frame metadata refuse validation. This
rechecks recorded file evidence without rerunning the authored Blender graph.

Baking is limited to ten million native vertex-frame samples and 32768 bone-frame
samples per level, and two million morph weight keys. Existing geometry/target/
file limits apply. Skin meshes must keep a constant mesh-to-rig transform over
requested ranges; object or bone basis shear that cannot be represented by TRS
refuses. Controls requiring other modifier stacks or absolute shape keys remain
outside LOD generation. Integer-frame keys and sampled file checks do not certify
subframe fidelity, every decoded frame, shading, silhouette or target-engine
behavior. Review representative motion and appearance before delivery.

Export reports progress, current free storage and a geometry/key/texture size
estimate. The estimate is heuristic. It restores selection, active object,
visibility and the original fractional frame, deletes owned proxies/actions/data,
and removes staging output on ordinary failure or cooperative cancellation.
Only a validated bundle is published, into a new directory. Native export calls
cannot cancel internally. Process crashes can leave staging directories; their
reconciliation/retention remains separate. Explicitly delivered bundles are not
temporary-retention targets.

## Independent GLB deformation inspection

`inspect_glb_deformation` takes an existing `.glb` `path` under the active library.
It reads the file without importing it or changing the Blender scene, actions or
frame. By default it queues an operation; poll/wait/cancel normally, or use
`wait=true`. Progress includes current storage information. The input path is
protected from owned temporary-retention cleanup while the operation uses it.

The result contains file `sha256`, geometry/dependency inventory, joint names,
morph target names/default weights, clip inventory and sampled world playback.
Each sample reports its clip/time, number of representative vertices,
`sampled_world_bounds`, up to `sample_limit` vertex positions (default 8, maximum
16) and a replay fingerprint. `clip=null` denotes the file's default pose, including
its stored morph weights; it does not force all morphs to zero. World coordinates
use glTF +Y up. Raw POSITION-buffer bounds in `geometry` use the buffer's coordinate
system and can differ from sampled world bounds.

Choose a named `clip` or page clips with `offset`/`limit` (default 4, maximum 8),
then follow `next_offset`. Clip selection overrides paging. `animation_samples`
(default 3, range 3–9) distributes sample times across each selected clip's stored
range, including interpolation between sparse key times. The default pose is also
sampled. Representatives cover distributed vertices, per-joint position extrema
and per-target offset extrema; the bounds are sampled, not exhaustive. Sparse
morph storage is supported with an implicit zero base or replacements over a
dense base. Sparse indices must be ordered, distinct and within the accessor.
LINEAR, STEP and CUBICSPLINE weight channels and default mesh/node weights replay;
morph offsets apply before linear joint deformation.

This is a bounded native export profile: one mesh node/mesh, optional single
linear skin with up to 256 named joints/four influences, up to 63 non-Basis morph
targets, 32 clips, two million exported vertices, two million animation value rows
(morph weights counted individually) and four million target-vertex entries. Buffers/images must be embedded, positions/normals/
UVs must pass the geometry reader, and weights/targets/curves must be finite.
Float morph data can be dense or sparse; quantized/normalized attributes,
compressed geometry, GPU instancing, multiple meshes and arbitrary glTF extensions
are outside this inspection profile. Files are limited to 512 MiB with 16 MiB JSON.
A second file-hash check refuses an asset changed during inspection. Cancellation
is cooperative between decoder/replay work; file reads and geometry parsing can
finish before a pending cancellation is observed.

Inspection proves what this decoder can read and sample from that file. It does
not compare the file to an authored Blender model, evaluate procedural shaders,
certify every frame/vertex or establish target-engine behavior. Native comparison
fixtures qualify selected exports; ordinary inspection is not that comparison.
Timeline-baked morph LOD bundles use this decoder for independent comparison and
readback. Editable morph chains retain their source Key dependency; baked bundle
files contain their sampled animation. Inactive-action batch selection and general
controller-graph serialization are separate from evaluated-timeline baking.

## Existing skeleton and rest-hierarchy refinement

`inspect_armature_rest` reads an Object-mode armature's rest bones without
switching modes. Use `offset`/`limit` (up to 512) for pages. It reports heads/tails,
roll in degrees, parents/connections, deform and inheritance flags, data users,
known skin bindings, bone-parented objects, constraint consumers and current
animation/pose indicators. `edit_blockers` explains linked/overridden data,
armature-data animation or visibility/selection limits. Discovery is not a claim
that every external dependency or resulting motion has been validated.

Carry `rest_sha256` as `expected_rest` into `edit_armature_rest`. Use `bones` for
partial patches of existing bones and `add_bones` for complete new definitions:

```json
{
  "name": "CharacterRig",
  "expected_rest": "<rest_sha256>",
  "allow_deformation_change": true,
  "bones": [{"name": "UpperArm", "tail": [1.2, 0, 1.5], "roll_degrees": 15}],
  "add_bones": [{"name": "HandControl", "head": [1.2, 0, 1.5], "tail": [1.4, 0, 1.5], "parent": "UpperArm", "connected": true, "deform": false}]
}
```

Coordinates are armature-local rest coordinates. Patch fields `head`, `tail`,
`roll_degrees`, `parent`, `connected`, `deform`, `inherit_scale`,
`inherit_rotation` and `local_location` are optional; omitted/null fields keep
their current values. Use `parent=""` and `connected=false` to unparent a bone.
Added bone names are limited to 63 UTF-8 bytes. Added bones require head/tail
and default to no parent, disconnected, deforming,
zero roll, FULL scale inheritance and enabled rotation/local-location inheritance.
Scale inheritance also supports FIX_SHEAR, ALIGNED, AVERAGE, NONE and NONE_LEGACY.
New pose bones use XYZ Euler mode; existing modes and named channels remain.
Explicit roll values wrap modulo a full turn.

The complete planned hierarchy is validated before writes, including names,
cycles and nonzero bone lengths after conversion to native float coordinates.
Connected child heads follow the planned parent tail; their tails stay at the
planned positions. An explicitly supplied connected head must already match
that joint, otherwise the plan refuses. Moving a parent can therefore shorten
its connected children; supply their tails too when the entire limb should move.
Zero-length connected results refuse rather than allowing native bone deletion.
Bone renaming/removal, pose-to-rest conversion, automatic anatomical mapping and
animation rebasing are separate workflows and are not performed by this tool.

The guard covers rest matrices/geometry/inheritance, shared armature object users
and the known skin/attachment/constraint-target inventory. It does not freeze
animation keys, skin weights, arbitrary driver dependencies or every bone option.
Inspect them separately when relevant. Bound, posed, animated, constrained or
bone-attached rigs require explicit `allow_deformation_change=true`: existing
weights, keyframe values, action/driver bindings and named constraint targets stay
in place, so their evaluated deformation/motion can change. Skin rest positions
are not reprojected. Sample important poses and check skin coverage afterward,
especially when disabling deform flags or changing hierarchy/inheritance.

A local visible/selectable Object-mode rig is required. Shared armature object
users require explicit `make_single_user=true`, which copies armature data for
this rig; other rigs keep their data. External references to the old data ID are
not automatically remapped. Ordinary edits retain the original data ID. Native
edit-mode round trips preserve existing pose metadata and references; new bones
are additive. Direct armature-data animation is inspect-only, while object/pose
animation, drivers and constraints may stay active with the deformation flag.

Edits default to queued operations and report progress/storage. `wait=true`
returns the completed result. Cooperative cancellation or ordinary native errors
restore snapshotted rest fields, remove new bones and discard an owned shared-
data copy. Object selection, active bone and existing bone selection are retained.
Native mode changes/evaluation cannot be interrupted internally; rollback is not
crash-durable. At most 512 total bones are supported. Result verification checks
native heads/tails, roll matrices, hierarchy and inheritance against the plan;
it does not establish that all existing animations still perform their intended
motion. Save recovery checkpoints and review evaluated poses before delivery.

## Skin-weight inspection and refinement

Use `inspect_skin_weights` with mesh `name` and optional matching `armature`.
It reports deform bones, group locks, nondeform groups, binding settings, shared
mesh users, normalization/influence/invalid-weight issue counts and paged raw
vertices. `offset`/`limit` (maximum 256) paginate; `issues_only=true` filters the
rows and `max_influences` defines the inspection threshold. Nonfinite stored
weights are reported as JSON null and flagged invalid. Indices refer to the
mesh's raw basis, not evaluated modifier output or a posed surface.

Carry `weights_sha256` as `expected_weights` into every edit. The guard covers
all memberships, group names/locks, raw basis coordinates/topology, rig rest
matrices/deform flags, mesh-to-rig transform and binding settings. Changes to
those inputs require inspection again. It does not freeze animation, arbitrary
external dependencies, other modifiers or evaluated deformation.

- `set_skin_weights`: `weights=[{"vertex":0,"weights":{"Root":0.3,"Arm":0.7}}]`
  replaces that vertex's deform influences. Omitted unlocked deform groups are
  removed. `normalize=true` scales the unlocked remainder after locked weights;
  `normalize=false` preserves supplied magnitudes. Empty/partial rows need
  `allow_unweighted=true` when they cannot fill the normalized budget.
- `repair_skin_weights`: optional unique `vertices` selects a subset; otherwise
  all raw vertices. `threshold` prunes small influences; `max_influences` retains
  the strongest, counting locked positive influences. Normalize the remainder
  without changing locked weights. `unweighted` defaults to ERROR; KEEP permits
  empty/partly filled vertices, FALLBACK needs `fallback_bone`, and NEAREST fills
  missing weight with the nearest unlocked deform rest-bone segment. NEAREST
  uses raw basis points transformed to current armature-local coordinates and
  deterministic bone-name tie breaking; it is a heuristic, not automatic
  anatomical weighting.
- `smooth_skin_weights`: the repair options plus `iterations` and `strength`.
  Each iteration blends the current row with the mean of raw edge neighbors,
  then prunes/normalizes it. All selected vertices read frozen inputs within an
  iteration. Unselected neighbors influence the mean but remain unchanged.
- `mirror_skin_weights`: optional destination `vertices`, `axis`, `plane`,
  `space` ARMATURE (default) or MESH, `tolerance`, `direction`
  POSITIVE_TO_NEGATIVE/NEGATIVE_TO_POSITIVE/SWAP, and explicit
  `bone_pairs=[{"left":"Arm.L","right":"Arm.R"}]`. Unpaired names retain
  their identity. Matching uses reflected basis positions; missing matches or
  equally close candidates with differing weights refuse the entire edit.
  More than 256 candidates within tolerance is refused. Centerline vertices
  within tolerance remain unchanged. Sources are frozen, including for SWAP.
- `configure_skin_binding`: configure the existing unique Armature modifier's
  `use_vertex_groups`, `use_bone_envelopes`, `preserve_volume`, mask `vertex_group`
  and `invert_vertex_group`. Exposed settings replace their previous values;
  omitted fields use defaults. It does not recompute weights or rebind a rig.

Weight operations preserve nondeform groups such as physics pins. Existing
`lock_weight` flags are respected by default, including absent memberships;
`respect_locks=false` explicitly overrides weight protection without changing
those flags. Locked sums above one or too many locked influences refuse repair.
These tools do not author UI group locks or infer bilateral bone names.

Editing requires a local Object-mode mesh and one Armature modifier pointing to
an Object-mode rig in the current scene. Weight edits require group-based
binding enabled. The rig world transform must be invertible. Animated poses and
relative morphs can stay active; verify their evaluated deformation afterward.
Shared mesh data requires explicit `make_single_user=true`; otherwise edits
refuse. Ordinary edits preserve mesh/shape IDs and references; isolation copies
mesh data and its shape data. Materials and rig remain shared.

Set/repair/smooth/mirror default to queued operations. Use `wait=true` for a
blocking response, or poll/wait/cancel the returned operation. Progress includes
storage information; membership writes check cancellation in bounded chunks.
Plans are completed before membership writes. Cooperative cancellation or
ordinary errors roll back changed rows, new groups and any owned data copy.
This is an in-process rollback, not a crash-durable transaction; retain normal
recovery checkpoints. A native API call itself cannot be interrupted.

Limits: 200,000 vertices, 2,048 groups, 512 rig bones, two million memberships;
explicit edits accept 10,000 unique vertex rows. Smoothing is bounded to two
million selected vertex-iterations. Mesh topology and rest bones remain unchanged.
Always inspect issue counts and sample the posed/animated result; normalized
weights alone do not establish good deformation.

## Motion retargeting between skeletons

`inspect_animation_retarget` plans transfer from armature `source` to target
armature `name`. Both must be in the current scene and Object mode. It is
read-only and does not seek frames or switch actions. Supply explicit `mappings`
with `source`/`target` bone names and optional `rotation_correction_degrees`.
If omitted, inspection lists exact-name suggestions; execution never guesses
humanoid anatomy from names. Each source and target bone may occur only once.

Results include `source_rig_sha256`/`target_rig_sha256`, rest matrices/parents,
length ratios, unmapped bones, mapping roots, connected translation roots and
hierarchy warnings. A mapping root has no mapped target ancestor; it can still
have an unmapped native parent. Inspect skipped source ancestors before choosing
local transfer. The proposed `translation_scale` is the median mapped target/
source rest-bone length ratio, not a guaranteed anatomical height/contact scale.
Override it explicitly when needed (finite, positive, up to 1e12).

`retarget_animation` requires nonempty mappings and both fresh hashes as
`expected_source_rig`/`expected_target_rig`. It creates unused `output_rig` and
`clip` names, plus optional `meshes` entries naming a target `source` mesh and
independent `output`. Output object/clip names fit 63 UTF-8 bytes. It copies the
target skeleton's rest data and vertex groups, clears runtime pose/object
constraints, drivers and NLA from the new rig, and activates a persistent managed
quaternion clip. Both input rigs, their actions and target skins remain editable.
It does not temporarily activate another source clip; it samples the source's
**current evaluated timeline**, including NLA, drivers and IK.

```json
{"params":{"source":"MotionRig","name":"CharacterRig","mappings":[{"source":"Hip","target":"Pelvis"},{"source":"LowerArm","target":"Forearm"}],"output_rig":"Character_Walk","clip":"Walk_Transferred","meshes":[{"source":"CharacterSkin","output":"WalkSkin"}],"frame_start":1,"frame_end":48,"expected_source_rig":"<plan source_rig_sha256>","expected_target_rig":"<plan target_rig_sha256>"},"wait":true}
```

Choose the transfer semantics explicitly:

| `rotation_mode` | Meaning |
| --- | --- |
| LOCAL_POSE (default) | Copy each evaluated joint-local pose-basis rotation into the target bone's own axes. Its rest orientation and attachments remain those of the target. Motion in unmapped source ancestors is omitted. |
| ARMATURE_DELTA | Transfer each bone's armature-space rotation relative to its own source rest orientation, then apply it relative to the target rest orientation. Useful for explicit rest/axis alignment and hierarchy differences. |

`alignment_degrees` is a source-to-target armature-axis rotation for
ARMATURE_DELTA and object motion. LOCAL_POSE uses the bones' local axes instead.
Per-map `rotation_correction_degrees` conjugates the transferred rotation in the
target bone's local axes; in armature mode that correction is expressed through
the target rest basis. Corrections do not automatically identify anatomical
flexion axes. Preview the result rather than assuming similar names imply a
suitable mapping.

`translation` is ROOT (default), NONE or ALL. ROOT transfers location only for
mapping roots; ALL additionally transfers each mapped joint's own translation.
LOCAL_POSE scales the source pose-basis translation, applying its per-map axis
correction. In ARMATURE_DELTA, a mapping root receives the scaled source head
displacement from its rest head; child translations add the source's own local
pose contribution expressed in armature coordinates. Unmapped target bones stay
at identity local pose and follow their target parents. Connected target joints
can prevent requested translations: map their parents, choose NONE, or inspect
and revise the mapping. A verification mismatch refuses the output.

`scale_mode="IGNORE"` preserves target proportions and reports mapped source
bones whose local stretch was ignored. COPY_LOCAL transfers mapped local scale
channels instead. Source pose scales must be finite, positive and nondegenerate;
collapsed/mirrored pose scales and multi-segment B-Bones are unsupported here.
Native bone inheritance is used to solve target pose-basis keys. Unrepresentable
shear or other reconstruction differences fail verification.

`frame_start`/`frame_end` are inclusive integer target frames. Source time is
`source_start + (target_frame-frame_start)*playback_speed`; source_start defaults
to frame_start, speed to one. Fractional source sampling is supported. Times must
fit [-1048574,1048574]. `reference_frame` defaults to source_start and establishes
both the source object-motion reference and the target's placement. Rest bone
data remains the reference for joint rotation; this does not subtract an
arbitrary animated pose at reference_frame.

`object_motion="COPY"` (default) transfers rigid source object translation/
rotation relative to that reference, aligned and translation-scaled into the
target's reference placement. Initial source placement is not copied onto the
target. Static object scales/units are supported when native inverses and output
transforms are representable. Animated object scale/shear relative to reference
is refused; choose IGNORE to keep a stationary target object. Bone motion remains
independent of that choice. COPY produces mixed object/skeletal channels; the
managed exporter supports this tagged clip, while simple skeletal clip editing/
switching retains its non-skeletal-channel guard. Use current-timeline sampling,
NLA or the generic render commands for these results.

Target skins need one enabled Armature modifier referencing the target rig.
Supported additional surface modifiers are BEVEL, SUBSURF, WEIGHTED_NORMAL,
TRIANGULATE, SOLIDIFY and DECIMATE. Mesh objects/data must have no animation or
object constraints and must be unparented or object-parented to that target.
Copies are parented to the new output rig so object root motion carries the
skin. Relative shape data is copied independently and frozen at its reference-
frame values; source morph animation/drivers are retained only on the original.
The copied shapes remain editable. Materials remain shared; this does not clone
or rewrite shader graphs. Unsupported dynamic geometry requires a separate bake.

Each target frame gets location/quaternion/scale bone keys with continuous-sign
quaternions and linear interpolation. A second evaluation recomputes the transfer
from the live source and compares all keyed output bone/world matrices with it.
Copied evaluated skins are scanned for finite world vertices and sampled bounds/
digests. Default absolute `tolerance` is .0001 (range .000001.. .01), applying to
matrix components including world translations. This verifies the chosen transfer
math, not anatomical correctness, skin weights, foot locking or subframe/spin
winding accuracy. Inspect binding, key/intermediate poses and rendered motion.

Results include actual translation scale, frame/key counts,
`max_world_matrix_error`, ignored-stretch bones and three representative skin
samples. `within_nla_key_limit` reports whether the generated clip fits the
current 200000-key NLA/channel inspection bound; dense output can still be
rendered/exported directly. Inputs also inherit existing NLA/driver inspection
bounds. Rig hashes cover rest/hierarchy/inheritance and direct rig animation/
constraint/driver configuration; they do not freeze external control objects,
mesh/material data, current poses or evaluated reference placement.

The operation submits asynchronously by default and reports transfer/verification
progress with storage. Limits are 256 bones per input, 500 target frames, 32768
target bone-frame samples, eight skins and ten million raw/evaluated vertex-frame
samples. Cancellation checks between frames and before success; ordinary failures
or cancellation remove newly created rig/mesh/shape/action data and restore the
original frame/subframe. Individual native frame evaluation/key insertion blocks
until the next check. Process failures use existing checkpoint/recovery rather
than this in-process cleanup.

Save `.blend` for editable source/target/result, and select only the transferred
rig/skins for GLB delivery. Reimport and compare actual playback, including root
movement. Retargeting does not transfer a complete control rig, infer humanoid
roles, enforce contact/IK goals on different proportions, or transfer morph clips.
Those remain distinct animation/rig refinement work.

## Structured shape keys

`create_shape_key`, `edit_shape_key`, `inspect_shape_keys`,
`set_shape_key_weights` and `remove_shape_key` use typed `params`. They work with
Python execution disabled; inspection is available to read-only keys.

Create a named `key` on mesh `name`. Basis is created automatically, and new keys
start at weight zero. Supply sparse `vertices` entries such as
`{"vertex":2,"value":[0,0,0.5]}`: `mode="OFFSET"` means displacement from Basis;
`mode="POSITION"` means absolute mesh-local coordinates. Offsets do not accumulate
when repeated. Alternatively supply `source_object` with matching ordered vertex,
edge and polygon topology; its raw local reference coordinates become the shape.
Source object transforms, modifiers and active morph weights are not copied.

Coordinate editing preserves unspecified vertices; `reset_unspecified=true`
resets them to Basis first. Basis editing and absolute shape-key workflows are
refused. Imported relative keys must be relative to Basis to edit coordinates.
`expected_topology` can carry the fingerprint from inspection to reject stale
index-based edits. A stored fingerprint also detects topology changes after a
managed edit. Matching connectivity cannot prove semantic vertex correspondence
on symmetrical/reindexed assets; check the resulting deformation.

Static weights use `values` in [0,1], optionally `reset_others=true`. Shared meshes
need `make_single_user=true` for coordinate/weight/deletion edits. Inspection
reports key values, mute/mask settings, coordinate digests, changed-vertex counts
and samples. Samples for non-Basis keys contain changed vertices. Deletion refuses
Basis, relative-key dependencies and known animation references.

`create_morph_clip` names the mesh in `name`, the action in `clip`, and accepts
`tracks` such as `{"key":"Wide","keyframes":[{"frame":1,"value":0},{"frame":12,"value":1}]}`.
Clips persist while inactive; `activate=false` preserves the current weights and
action. `set_morph_keyframes` updates specified scalar keys without replacing
other frames or action slots. Clip editing can leave partial keys on failure;
there is no general editing rollback. New clips/slots are removed if creation fails.

`set_active_morph_clip` selects a compatible KEY slot and resets unkeyed values to
zero; omitting `clip` clears the action and weights. Static weight setting also
exits shape-key solo preview so the requested mixture can be evaluated. Morph
animation needs independent mesh data. Drivers and active NLA blending are
refused; muted glTF import stashes are supported. `inspect_morph_animation` lists
global actions/slots and reports tracks/key counts for the selected morph slot.

For combined skeletal/morph animation, create the skeletal clip first, then call
`create_morph_clip` with the **same clip name** and `join_existing=true` on its bound
mesh. This explicitly adds a KEY slot to the managed action; the existing OBJECT
slot and bone keys remain intact. Multiple meshes can have independent KEY slots
in one managed clip. Joining an unrelated skeletal rig's action is refused.

`sample_morph_animation` returns weights and evaluated geometry at up to 64 frames.
Use `armature` and `skeletal_clip` to choose and sample the corresponding bone
animation in the same operation. Omitting `skeletal_clip` preserves the rig's
current action; no action leaves its current pose in use. Sampling restores the
previous frame/subframe, weights, actions, slots, solo-preview state and any
explicitly sampled rig pose, including on cooperative cancellation. Temporary
evaluation may mark Blender dirty. Inspect the actual rendered result as well.

`get_scene_info` and `get_object_info` include a shape-key count on mesh objects.
glTF import may create additional bone-display meshes; use this count or
`inspect_shape_keys` to identify the asset mesh when reviewing imported morphs.

## Structured numeric mesh attributes

Use `inspect_mesh_attributes` to list schemas and obtain `attributes_sha256`.
Supply that base-data guard as `expected_attributes` for `create_mesh_attribute`,
`set_mesh_attribute_values`, `ramp_mesh_attribute` and `remove_mesh_attribute`.
Inspect with `attribute`, `offset` and `limit` (at most 128) to page values.
`evaluated=true` reads the current evaluated mesh without changing the source;
its guard cannot authorize base edits. Unrealized instance components require
Geometry Nodes realization before mesh readback.

Creation accepts `FLOAT`, signed 32-bit `INT`, strict `BOOLEAN`, `FLOAT_VECTOR`
(three components) or `FLOAT_COLOR` (nonnegative linear RGBA, HDR allowed), on
`POINT`, `EDGE`, `FACE` or `CORNER`. Supply a uniform initial `value`. Updates
accept one uniform `value` for the whole domain or distinct `indices`, or a
bounded `values` array with contiguous `offset` or matching distinct `indices`.
Values must be finite and fit native float32 storage. There is no implicit unit,
axis, normalization or shader conversion. Names have at most 63 UTF-8 bytes and
cannot use internal prefixes, controls or outer whitespace.

A ramp fills an existing FLOAT field using local X/Y/Z coordinates: vertices,
edge midpoints, face centroids or each corner's vertex. Omit both `input_min` and
`input_max` to use the coordinate extent; otherwise supply an increasing pair.
`output_min`, `output_max` and `clamp` control the result. Degenerate ranges refuse.
For example, create POINT/FLOAT `bend_weight` with value 0, inspect its new guard,
then ramp along Z from output 0 to 1. A shader's `ShaderNodeAttribute` can read
it through its Factor output. In a structured geometry graph, `GeometryNodeInputNamedAttribute` supports
`properties.data_type` and the `attribute` name shortcut. Store a field on
INSTANCE with `GeometryNodeStoreNamedAttribute`, then realize instances for
numeric mesh readback.

Edits protect topology/internal/reserved attributes and UV maps, preserving UV2
and existing UV/color selectors. Creating the first color layer follows Blender's
automatic color activation. Shared mesh data needs `make_single_user=true`;
shared shape-key meshes refuse isolation. Single-user edits retain shape-key and
armature IDs. Animated/driven mesh attributes require a specialized workflow.
Cooperative failures restore values and selectors or discard an isolated copy;
removal rollback can recreate the attribute handle/order. Hard-crash atomicity
is outside this guarantee. Successful writes are read back before handoff.

Budgets are 256 attributes, one million vertices/faces, two million edges, four
million corners and 64 million stored components; explicit update arrays have at
most 100,000 rows. This is a numeric mesh foundation, not a runtime wind packing
schema or proof of custom GLB attribute retention. Unsupported native types are
listed and included in guards but have no value editing through these tools.

## Verified numeric field export

`inspect_attribute_export` takes a static base mesh `name` and up to 16 `fields`,
for example `[{"attribute":"bend_weight","semantic":"wind.bend_weight"},
{"attribute":"branch_anchor","semantic":"wind.branch_anchor"}]`. Use the returned
`export_sha256` as `expected_export` on `export_attribute_bundle` with the same
options and a new `directory`. The versioned `mcpblender-numeric-fields-v1` bundle
contains `asset.glb` and `manifest.json`. Save your editable `.blend` separately.

The manifest records source schemas, semantic labels, scalar lane mapping,
unmapped custom fields, placement/scene units, source corner witnesses and the
GLB hash/proof. Each source component occupies a named FLOAT32 scalar lane such
as `_MCP_F00_C0`; a private `_MCP_CORNER` lane establishes correspondence through
vertex reordering, material splits and UV seams. This uses no texture coordinates.
Booleans become 0/1; integer fields require values within +/-2^24 for exact float32
packing. Float/vector/linear RGBA components remain raw numeric data, including
signed vectors and HDR colors. Custom anchor vectors remain in their declared
native local axes/units; the consumer must apply the recorded source interpretation.
The GLB positions follow ordinary +Y-up/metre-world export conventions.

Before publication, an independent standard-library decoder checks every field
row, local position, oriented triangle, UV channel (including UV2) and metre world
placement against the source witness. `validate_attribute_bundle` repeats this
without needing the original Blender mesh. This checks correspondence with the
saved witness, not signed provenance or a downstream engine/shader's handling of
custom attributes. Editing both witness and file is not an authenticated history.
Unmapped fields are not qualified; PBR/shader fidelity needs its separate pipeline.

This profile accepts POINT/FACE/CORNER custom numeric fields. EDGE values need an
explicit projection. Unrealized instances, modifiers, shape keys, animation and
constraints require a separate static delivery copy. Loose geometry and negative
or singular placements refuse. Shared source meshes/materials stay untouched;
only disposable delivery copies receive export lanes. Up to eight UV channels,
one million corners (default 250,000), four million expanded scalar components,
and 512 MiB output are supported. `max_bytes` defaults to 256 MiB. The initial
space estimate covers witness/geometry and excludes unknown embedded image size;
progress reports free storage and the final manifest check uses actual sizes.

Existing output paths are refused. Cooperative failures remove only owned staging
files and native copies. Final two-file publication is not crash-atomic; a hard
crash can leave a staging/partial output directory requiring operator inspection.
This generic format does not yet populate complete botanical branch hierarchy,
leaf orientation/flutter or a wind runtime shader. Preserve the canonical wind
semantic JSON alongside later vegetation deliveries.

## Botanical wind interchange bundles

Use `inspect_botanical_export` with the managed tree `collection` and optional
`wind` settings. Pass its `export_sha256` as `expected_export` to
`export_botanical_bundle`, with the same settings/budgets and a new `directory`.
`validate_botanical_bundle` verifies a saved bundle independently of the original
Blender project. These tools work with arbitrary Python execution disabled.
Keep the editable `.blend` alongside the bundle; it is not embedded automatically.

The versioned `mcpblender-botanical-wind-bundle-v1` layout contains:

- `semantics.json`: canonical model/generator/seed, stable branch/bud IDs and parent
  hierarchy, compiled wind field/solver/placement, full shoot and leaf attachment
  tables, variant, local XYZ orientation, scale, phase and flutter.
- `wood/` and, for populated foliage, `shoots/`: numeric-field GLB bundles with
  branch index, parent index, axis anchor, segment pivot, phase, stiffness and bend
  weight. Root parent index is -1. Anchors/pivots remain raw root-local metres.
- `leaf-0/` through the configured variant count: one verified static GLB per
  template, referenced by all leaf instance records. Templates stay shared; no
  leaf population realization or `EXT_mesh_gpu_instancing` is emitted.
- `manifest.json`: source/plan guards, file hashes, component inventory, native
  rest-instance comparison metrics and explicit material conversion limits.

Axis anchors and segment pivots have distinct meanings: the anchor is the first
attachment of an entire branch axis; the hierarchical solver rotates each segment
around its own start. Bend weight is the existing clamped local Z/tree-height
profile. The full hierarchy/solver supplies the actual parent-first motion; the
weight field alone is not a complete wind shader. Leaf flutter is a rigid local-X
rotation after attachment rotation, with per-instance phase/amplitude. No wind data
uses UV coordinates. Custom vector lanes stay in canonical Z-up metres; GLB
positions use +Y up and normalized world metres. Consumers must apply the recorded
coordinate contract and placement rather than treating custom vectors as POSITION.

Every native leaf rest instance is matched to its canonical variant, position,
orientation and scale before export. Numeric sub-bundle validation checks all
encoded mesh fields, positions, oriented triangles, UV channels and metre placement.
The independent botanical validator additionally checks model/wind bindings,
branch semantic rows, regenerated seeded leaf attachments and canonical template
vertices. Revalidation needs the files only, even after the source is removed.
These are correspondence checks against unsigned witnesses, not authenticated
provenance, a runtime shader test or continuous-motion certification.

Sources must satisfy managed botanical ownership/content checks and frozen positive
uniform placement. Manually edited derived meshes require a separate delivery
workflow; this export does not bypass master ownership validation. The woody mesh
retains BarkUV; shared templates retain LeafUV. The general numeric exporter also
qualifies UV2 preservation, but authored lightmap UV2 on managed botanical masters
has not been qualified by this fixture. Bud points remain in canonical semantic
organs, without a separate point-only GLB. Bare trees produce only the wood asset.

Default budgets are 30,000 leaf instances, 500,000 total corners and 512 MiB output;
limits are 100,000 instances and one million corners. Numeric sub-bundle scalar
component limits also apply. The initial geometry/semantic estimate excludes
unknown embedded material image sizes; per-component progress and free-storage
checks continue through verification. Native glTF calls are not interruptible;
cancellation is cooperative between native calls and during bounded decoding.

Existing directories are refused. Cooperative failure removes only owned native
copies/staging data and preserves the source, selection and frame. Publication
moves several component folders/files into an exclusively reserved directory;
it is not hard-crash atomic. A crash can leave a hidden staging or partial output
directory requiring inspection. Native thin-leaf/bark graphs are passed through
Blender's glTF exporter; optical/backlighting/vein fidelity is not certified.
Bake PBR with the existing texture workflow when needed. Vegetation LODs,
continuous wind, engine shaders and the final mature-oak reference remain separate.

## Native near/mid vegetation LODs

Use `inspect_botanical_lod_source` with a managed tree `collection` and one to four
reduced `levels`, for example `[{"leaf_budget":5000,"radial_sides":6},
{"leaf_budget":2500,"radial_sides":5,"min_branch_radius_m":0.04}]`. Leaf budgets
must decrease and fit the source; radial sides cannot increase and branch-radius
thresholds cannot decrease. These are absolute leaf counts, not ratios. Planning
and `create_botanical_lods` default to tracked asynchronous operations; poll them
or explicitly request `wait=true`.

Inspect `valid`, each level's pixel losses, triangle counts and work estimates.
Pass the returned `plan_sha256` as `expected_plan` to `create_botanical_lods` with
the same options, a fresh `lod_collection` and optional `display_offset_m`.
Creation refuses failed planned quality gates. It also checks actual native wood
coverage/silhouette before handoff; `native_wood_quality_pending=true` in a plan
makes that additional creation-time check explicit. Review the renders and tune
budgets deliberately; a green pixel gate is not a complete visual assessment.

The native profile includes independent full LOD0 and the requested reduced
levels. A lazy greedy selector scores uncovered opaque blade pixels, weighting
source boundary pixels, in fixed root-local FRONT/SIDE/TOP views. Leaf selections
are nested and deterministic, with canonical IDs/orientation/scale/phase/flutter
retained. `min_branch_radius_m` retains major wood plus every selected leaf's
parent branch and all ancestors. It is a canonical local-metre radius threshold,
prior to the tree's physical placement scale. Lower radial counts rebuild wood
without interpolating discrete branch IDs. Shoots remain only where selected
leaves need them. Every level shares the same copied template collection: leaf
geometry is neither realized nor duplicated for each level or leaf.

`max_coverage_loss` and `max_silhouette_loss` default to .25. These are fractions
of source occupied pixels and source boundary pixels missing from the selected
representation. The boundary includes internal gaps. Wood uses the same crown
window and additionally bounds excess occupied area. The initial plan scores
leaves; creation checks projected native wood triangles too. Native counts must
match planned wood/shoot triangles, and every level's actual leaf instances are
matched to the retained variant/position/orientation/scale. Expanded triangle
budgets include wood, shoots and all leaf instances; stored shared templates cost
less than that expansion. No measured GPU memory/draw-call/frame-time claim follows.

Use `inspect_botanical_lods` for `lods_sha256`; supply it as `expected_lods` to
`activate_botanical_lod` or `remove_botanical_lods`. Activation sets only owned
level viewport/render visibility. The source remains independent. Removal keeps
materials; foreign members/shared external references refuse. Manual changes make
inspection invalid and require `discard_derived_edits=true` for guarded removal.
The profile keeps canonical model/foliage/selection/wind JSON via an owned Text
reference, survives save/reopen and remains inspectable after source removal.
Materials remain shared and editable; their optical equivalence is not certified.

Defaults are 128 pixels per view, a 2.5m crown margin, boundary weight 4, 60 million
combined leaf/native-wood triangle projections, 256 MiB estimated mask payload
and two million gain evaluations. Bounds are 32–256 pixels, one to three distinct
views, 100 million projections, 1 GiB mask payload and five million gain evaluations.
Mask estimates include Python integer/container sizes and are host-specific;
they exclude heap/source/native-scene overhead and do not establish peak RAM.
The mask budget is checked before generating the full attachment table. Clipped
source foliage or empty sampled views refuse qualification. Keep resolution,
views and margin fixed for comparisons. Pixel-center estimates can miss subpixel
blades and exclude alpha/translucency, perspective, lighting and shadow behavior.

The current profile preserves existing bark/leaf materials and generated UVs;
managed-master authored UV2, texture budgets, combined LOD GLB/wind packaging,
collision/shadow proxies, cluster cards/impostors and native animated LOD playback
remain separate work. Cooperative cancellation removes owned staged IDs; hard-crash
recovery during native staging is not independently qualified here. The generic
static/skeletal/morph LOD tools remain available for other asset types.

## Blender to Godot

Use Blender for modeling, materials, UVs, rigging and animation; export selected
assets with `export_glb`. The initial export uses Blender's glTF exporter, GLB,
standard glTF +Y up, and uncompressed meshes. Animation export is configurable.
Use explicit `apply_modifiers=true` for evaluated static geometry, including
Geometry Nodes; this does not change the editable source. Shape-key and
armature-deformed meshes require the normal animation-preserving export mode.

Animated exports use native `ACTIONS` mode. Managed clips belonging to each
exported rig or relative shape-key datablock are included through temporary muted
NLA tracks, removed afterward; the live action, pose, weights and frame are
restored. Skeletal and morph slots in one action merge into one named glTF clip.
Morph-only exports retain inactive managed clips and static default weights too.
Existing active actions/NLA clips
remain eligible, but Blender's automatic broadcasting of unrelated actions to a
single rig is disabled. Select both the rig and its meshes for skeletal delivery.
This does not select a subset of an existing complex NLA project; inspect its
actions and tracks before exporting.

Before export, verify object dimensions, scene unit scale, origins, local axes,
selection, normals, materials and desired animation clips. Keep the editable
`.blend` project alongside the GLB. Godot import, collision setup, shader fidelity
and game behavior require checks in the Godot project; GLB creation alone does
not prove that integration.

GLB world coordinates use metres. For a scene whose `scale_length` differs from
1, export adds positive uniform root transforms to the file, without changing
editor objects, project units or mesh/skin/morph/animation buffers. The response
reports `unit_normalization`. Mesh-local POSITION bounds are still local values;
they must not be read as physical world dimensions. Static LOD manifests also
record `world_bounds_m`, and package geometry proofs use metre world coordinates.
Skeletal/morph quality comparisons retain source scene units and their existing
error budgets. Nondefault decoder reports label their coordinate space; manifests
record `scene_unit_scale` and validation checks the actual encoded root transforms.
Legacy manifests without this field assume scale 1. Scale-1 exports undergo no
unit rewrite.

Use `export_objects_glb` for explicit active-scene export in projects containing
scenes with different unit scales. Whole-file export requires all scenes to have
the same scale and refuses mixed scales before writing. Shared roots across
homogeneous scenes are scaled once. Nondefault-unit normalization is bounded to
512 MiB GLB files and 16 MiB JSON chunks, and writes only the existing owned output
path. It inherits native export's partial-write failure boundary; it does not make
ordinary exports crash-atomic. Camera/light unit properties and downstream engine
behavior are outside the current qualification.

The installed FreeBSD Blender 5.0.1 glTF add-on crashes in its Draco library-name
probe even when compression is disabled. Our structured import/export calls use a
scoped in-memory workaround only when that FreeBSD probe raises `TypeError`.
It disables Draco availability for the operation and restores the original probe
afterward. Fixed Blender versions are left alone. Installed Blender files are
unchanged, and Draco-compressed assets are not supported by this workaround.

## Interrupted LOD/package export recovery

Top-level `export_lod_chain` and `export_asset_package` now register a durable,
owner-scoped export job before writing staging. This covers static, skin and morph
LOD bundles and batch packages. A hidden sibling job directory contains a small
journal, a stable OS writer lock and a registered stage. The delivered output
contains only its normal manifest/files; recovery metadata remains outside it.
Nested LOD exports inside a package belong to the outer package job.

Use `list_export_jobs` to discover journals belonging to the current owner under
`directory="."` (the library root by default). The read-only scan has bounded
`depth` (0..4, default 2), `limit` (1..100), `offset` and `include_finished` options.
It skips symlinks/foreign/unsafe records and reports truncation/next offset; narrow
the parent/depth if its 128-directory/8,192-entry budget is reached. It does not
adopt or clean anything. Finished published/cleaned jobs are omitted by default.

Use the original output `directory` with `inspect_export_job`, even if that output
directory was never published. It reports `job_sha256`, recorded operation ID,
writer lock status, stage inode/inventory/bytes, output identity and free storage.
The OS lock is authoritative for a live writer; PID reuse does not authorize or
prevent recovery. Operations are scoped to the current MCP owner/key as well as
`library_root`; another key's journal is refused. Directories/files are checked for
ownership and symlinks. A mismatched stage inode or unknown file is not adopted.

All four job tools run in the broker and work with Blender closed or busy:

1. Inspect the job and obtain a fresh `job_sha256`.
2. Call `recover_export_job` with `expected_job`. It never replays Blender work.
   Valid complete staging becomes `ready`; incomplete output becomes
   `interrupted`. A successful rename whose final journal update was interrupted
   is recognized by the output inode and revalidated as `published`.
3. To publish a ready snapshot, call recovery again with its fresh guard and
   `publish=true`. The recorded source/animation binding and manifests are
   validated; an existing unrelated output is never overwritten. This publishes
   the completed historical snapshot, not the current scene revision.
4. To discard incomplete staging, call `cleanup_export_job` with a fresh guard.
   It defaults to `dry_run=true`. Review the listed files/bytes, then repeat with
   `dry_run=false`. Valid `ready` output additionally requires explicit
   `discard_ready=true`. Published output is always protected.

Recovery and cleanup default to queued operations, with progress/storage and
cooperative cancellation; use `wait_operation`/`get_operation`. Inspect normally
waits for its short broker operation; discovery defaults to a queued scan. Filesystem metadata jobs bypass the export
space-admission reserve so they remain usable when the reserve is unmet. They
still need filesystem space for small journal updates; a completely full or
read-only filesystem can prevent those updates. Independent LOD validation has
coarse cancellation boundaries; publication is checked again before rename.

Cleanup deletes only registered staging with recognized package/LOD layouts and
matching identities/inventory. It anchors deletion through directory descriptors
and refuses symlinks, replaced data, unknown files, active writers and structured
queued/running file references. New structured operations cannot enter that stage
while cleanup reserves it. Current recorded project paths are also protected;
untracked Python/external references cannot be inferred. Cancellation partway
through deletion leaves `cleaning`; recover it before planning further cleanup.
Ready files that survive reconciliation regain their ready-output protection.

Small journals/locks remain for diagnosis and reuse; this is explicit cleanup of
large abandoned staging, not an automatic library sweep or journal-history purge.
Unknown legacy prefix-only staging without a journal is preserved. A crash in the
small directory-creation/ownership-registration gap can leave an unproven stage;
the tools refuse to guess ownership. Lost/edited journals, unknown files and inode
changes require review outside this automated path. Broker operation history is
not rewritten to claim the interrupted Blender operation completed: recovery has
its own operation result and reports `replayed=false`.

Native export journaling requires owner metadata from the matching updated broker;
a stale broker must be updated/restarted before exporting. The add-on archive
includes the dependency-free recovery/validation helpers, while frontend
FastMCP/Pydantic code stays outside Blender. Recovery here does not restore
in-memory scene edits or resume native render/bake work; application checkpoints
and the dedicated bake job workflows retain their separate responsibilities.

## Long operations and recovery

`submit_operation(command, params, request_id)` returns immediately for any
structured operation, including Python, imports/exports, renders and API transfers.
New domain tools use a typed `params` object and accept `wait` and `request_id`;
long renders and API transfers default to asynchronous execution.
`execute_code(..., wait=false)` is also supported.

Poll `get_operation` or bounded `wait_operation`, or recover IDs using
`list_operations`. `get_job` remains a render polling alias. A wait timeout does
not fail/cancel the operation. Reusing a request ID with identical command arguments
returns the same operation; changed arguments are rejected. Deduplication is scoped
to the API key (or the shared `stdio` identity).

Multiple frontends/connections share one broker. Blender operations execute
serially, and an animation sequence holds its turn across frames. Use a named
action or one Python operation when edits must form an uninterrupted batch. There
is no rollback. Queued work can be cancelled; running Python must call `check_cancelled`,
and frame sequences stop between frames. Native blocking calls and VSE video
encoding are not forcibly interrupted.

The frontend/worker reconnect after broker restart; `restart_bridge` exercises
this while preserving Blender. Claimed work is not claimed twice, and completion
acknowledgements can be retried. If Blender exits, unfinished work becomes
`interrupted` with `outcome_unknown=true`; edits are never automatically replayed.

For server-launched instances, `launch.auto_recover=true` supervises Blender
independently of frontend connections. It allows `launch.max_recovery_attempts`
restarts until an explicit launch resets the budget. A live busy process is not a
crash. Intentional shutdown disables recovery. Manually attached instances are
not taken over by the supervisor.

Recovery copies follow successful edits, throttled by
`launch.checkpoint_interval_seconds` (default 30). Dirty scenes are checkpointed
before renders; `checkpoint` forces a copy. Files live beside the socket in
`recovery/`; `launch.checkpoint_copies` defaults to three. Rotation removes only
older service-generated checkpoints. Recovery opens the latest completed copy
with auto-execution disabled. `start_blender(recover=false)` requests fresh startup.
Status reports checkpoint/recovery paths and errors, application session and broker
epoch. Edits after the last checkpoint and in-flight external effects may be lost
or uncertain.

## Storage feedback

`storage_status` reports current free bytes, configured reserve, usable space and
warnings for the active library. Operation status includes fresh storage data even
while Blender is busy; frame/download progress also carries it. Renders, downloads,
saves and checkpoints check capacity before admission and execution. Frame renders
and streaming downloads recheck as output grows.

`storage.reserve_bytes` defaults to 256 MiB; `storage.warn_below_bytes` to 2 GiB.
Estimates identify conservative pixel bounds, configured download limits,
heuristics, or unknown sizes. They cannot predict arbitrary Python output or quotas;
other processes may consume space after a check. Failures retain completed files;
the server never deletes user output to make room.

## External asset and generation APIs

Configure named `asset_sources` in private JSON:

```json
{
  "asset_sources": {
    "generator": {
      "base_url": "https://assets.example.com/api/",
      "headers": {"Authorization": "Bearer PROVIDER_CREDENTIAL"},
      "timeout_seconds": 120,
      "max_bytes": 268435456
    }
  }
}
```

`request_asset_api` submits JSON requests or polls provider jobs. `download_asset`
streams a result into the library, optionally verifies SHA-256 and publishes it
atomically. Import models with `import_asset`; use images in `configure_material`.
`upload_asset` sends refined assets with PUT/POST. Credentials, signed URLs and
request bodies stay outside the journal. Resources and redirects must remain on
the configured origin.

These are generic HTTP/JSON/file adapters. Specific diffusion services may require
multipart or other provider-specific adapters. No real/paid provider is configured
or qualified. Network jobs continue independently of Blender; a broker exit makes
unfinished transfers uncertain. Remote POST/upload effects are not replayed.

## Representative editing fixture

```sh
python3 tools/building_workflow.py /tmp/CHOOSE_A_NEW_BUILDING_DIRECTORY
```

This fixture retains an editable exterior building with image-textured brick, roof,
windows/glazing, a door, trim, lights and an animated camera. It round-trips an awning
through an authenticated loopback API, packs the texture, saves/reopens the project,
exports GLB, renders 12 frames, assembles image/text/sound strips in Blender's VSE,
and exports H.264/AAC MP4. `ffprobe` independently checks video dimensions, frame
count and audio. The API fixture does not exercise an actual diffusion model.

## Skills and verification

Repository skills:

- [blender-mcp-design](skill/blender-mcp-design/SKILL.md): modeling, inspection and asset preparation.
- [blender-mcp-render](skill/blender-mcp-render/SKILL.md): materials, lighting, camera previews and image review.
- [blender-mcp-animation](skill/blender-mcp-animation/SKILL.md): animation, frame sequences and video delivery.

Install these repository-owned skills explicitly with `tools/install_skills.py`;
see [skill installation](README.md#skills). The installer preserves Codex metadata
and adapts copies for PQC. Package installation alone does not install skills.
Tool descriptions remain usable by other MCP agents.

```sh
python3 -m pytest -q
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q
```

The opt-in suite starts disposable background Blender in a private `/tmp` directory,
uses real stdio and HTTP clients, and terminates only its own test processes.
For a separately authorized GUI smoke test, run
`python3 tools/gui_smoke.py /tmp/CHOOSE_A_NEW_EVIDENCE_DIRECTORY` on the current
display. It retains a test project, viewport image, log and JSON evidence, then
stops only its own Blender process.
See [VALIDATION.md](VALIDATION.md) for the checks performed on this host and their limits.
