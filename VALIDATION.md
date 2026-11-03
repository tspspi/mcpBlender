# Local validation: 0.2.0

## Owned vegetation bake preparation — 2026-11-03

A four-test gate passed locally on FreeBSD/Blender 5.0.1 in 49.99s: native owned
preparation/sampling/lifecycle checks, an MCP workflow with arbitrary execution
disabled, and source-policy/discovery checks. Native tests prepared all five
small-tree components plus selected reduced-LOD wood/shared-leaf components.
Original mesh/material signatures, UV coordinates, source guards, native ID sets
and selection were preserved. Missing source UVs refused without allocations;
explicit BAKE_LAYOUT generated copy-only sampling and recorded affected consumers.
Stale plans refused. Injected cancellation after actual UV work restored exact
native IDs/selection. Independent copies survived original tree/LOD removal,
save/reopen and guarded cleanup; an externally shared mesh blocked deletion.

Additional preservation checks compared source geometry/topology, corner normals,
material indices, texture space, original UV hashes and every original public
attribute after native UV generation. All-false native sharp-face/edge layers may
be omitted by BMesh; the equivalent dense default layers are restored before
comparison. A nonuniform parent and rotated root exercised inherited shear. The
native preparation and opacity-masked procedural-pixel MCP gate passed together
in 74.30s. Persistent original materials were copied without propagating their
fake-user persistence to owned copies. The final standard-worker affine bake and existing high-to-low regression passed
together in 89.16s (two tests). The reopened baked wood's world matrix matched
the sheared source within 1e-6. The high-to-low fixture retained projection
coverage, all seven maps, native bundle validation, embedded-texture GLB export
and rendered-preview checks. A separate policy/capability/add-on import gate
passed seven tests in 23.63s. Affine snapshot preservation applies to the standard
texture worker; the separate atlas worker was unchanged and is not qualified
for sheared source placement by these checks.

Implicit image and Texture Coordinate UV links were pinned to the original BarkUV
on private materials, while original graphs stayed untouched. Existing named UVs
were retained alongside the new BakeUV. The existing baker independently required
unit-tile, nondegenerate, complete nonoverlapping target UVs. Edit-mode UV operators
rebuild CustomData: holding and writing a pre-edit layer wrapper caused native save
crashes during development. Preparation now reacquires the layer after the native
operation; the final native and MCP save/reopen sequences passed. This is a local
regression result, not general crash-free operation qualification.

The MCP fixture configured procedural OAK_BARK/OAK_LEAF detail, selected wood and
one shared leaf variant, removed the original tree, saved/reopened the preparation,
and baked BASE_COLOR/NORMAL/ROUGHNESS/ALPHA through the existing isolated worker.
Both 64x64, two-sample bundles retained map statistics and actual procedural color
variation. The leaf bundle recorded the FRONT_PBR optical omissions; bark needed
no thin-leaf adapter. Bake operations left the preparation guard unchanged. After
guarded native-copy removal, both baked asset.blend files reopened and passed
native bundle validation. Evidence is retained under the local
`/tmp/mb-vegetation-bake-20261103` directory, including prepared.blend and both
map/editable-asset bundles. Small maps and sample counts qualify plumbing and file
binding, not final visual delivery quality.

Generated missing source coordinates are an explicit appearance change, not a
proof of source shader parity. Automatic adoption into native LOD profiles/bundle
exports, full-tree texture quality/budgets, physical optical calibration, filtering/
shadow/runtime behavior, cards/impostors and engine delivery remain open. An edited
preparation is reported as changed; unsupported shader/image edits can require
operator review before safe inspection/cleanup. Source-backed images stay shared
and are never deleted by preparation cleanup. Smart projection runs on Blender's
main thread with cancellation boundaries between components. Storage checks and
worker cancellation/recovery come from the existing baker; preparation itself
writes no files. No installation, venv, runtime/service changes or pushes occurred.

## Vegetation source material contracts and encoded inventories — 2026-11-03

Read-only `inspect_vegetation_materials` and opt-in parameter delivery are qualified
locally on FreeBSD with Blender 5.0.1. A five-test focused gate passed in 50.71s:
native material/bundle checks, structured MCP LOD export, source-contract rejection
and read-only discovery, and dependency-light add-on import. Both botanical and
LOD exports retained source IDs/geometry guards. Source color changes invalidated
the botanical export guard; stale LOD material fingerprints refused independently
of the geometry guard. The MCP workflow used no arbitrary execution tool, removed
the original tree before export, reopened the saved profile, independently validated
the files and checked the export journal's material and operation binding.

The native fixture distinguished opaque managed leaf geometry from separate
front/back colors and artistic backlighting, with null physical thickness/map
claims. Procedural OAK_BARK/OAK_LEAF details retained their guards and reported
required baking; missing BarkUV on shared-material shoots was reported explicitly.
A packed 32x32 direct base-color image with named UV provenance survived GLB export
and independent byte/dimension/hash inspection. Encoded material JSON and all
referenced texture UV channels were inventoried. Rehashed semantic tampering that
claimed a masked source alpha mode refused. Pure contract checks also rejected
fabricated maps, physical thickness, optical parity and invalid input dimensions.

One earlier mixed run hit the existing temporary broker startup timeout after the
native checks passed. Only its exact late test broker was stopped; a fresh isolated
startup and the full focused rerun succeeded. Production service configuration and
timeouts were unchanged. This is local functional evidence, not long-duration
broker reliability qualification.

The source parameter contract does not generate maps or certify native glTF shader
fidelity. Managed thin-leaf FRONT_PBR conversion still requires an explicit bake
request with its recorded optical omissions. Owned vegetation bake-copy UV
preparation/adoption, texture budget enforcement beyond bundle byte limits, physical
thickness/transmission calibration, optical/shadow/GPU parity, cards/impostors and
animated receiving-engine LOD behavior remain open. The RGBA8 estimate covers base
images only, excluding mipmaps/driver compression/runtime allocations. Existing
parameter-free bundles remain supported. No package installs, venvs, deployed
runtime changes or pushes were performed.

## Durable numeric/botanical/vegetation LOD export recovery — 2026-11-03

Public MCP dispatch now routes numeric-field, botanical-wind and vegetation-LOD
bundle exports through the existing owner-scoped export journal/writer lock.
Nested numeric sub-bundles remain inside the outer job. Complete validated stages
publish by one directory rename, preserving stage inode identity; recovery metadata
stays outside delivered files. New profile namespaces recognize only expected
asset names/files and bounded nested numeric staging. Unknown content/symlinks or
changed identity refuse recovery/cleanup. Source/profile and placement bindings
are validated before publication and again during file-only recovery.

Initial dead-writer/new-profile plus existing job tests passed **13 tests in
31.76 seconds**. Ordinary MCP numeric/botanical/LOD export and broker-only recovery
regression passed **4 tests in 173.67 seconds**. The final combined partial/live/
ready protections, broker-only cleanup, killed native writers, operation-ID binding
and add-on gate passed **17 tests in 96.23 seconds**. Explicit broker restart with
Blender startup disabled plus contract checks passed **4 tests in 12.11 seconds**.
Final verification-heartbeat/cancellation and cleanup regression passed **13 tests
in 1.07 seconds**. Skill and whitespace checks pass. These focused gates do not
constitute a fresh full-project suite or export throughput measurement.

Real Blender processes create complete botanical and shared-LOD bundles and exit
abruptly at the prepublication boundary. Their OS writer locks release; the
registered stages remain. Independent recovery without those Blender processes
validates files, marks them ready and explicitly publishes the same directory
inode, with replayed=false. Published output and validated ready stages refuse
ordinary cleanup. Numeric exports also publish through the journal. A standalone
actual custom-field GLB fixture recovers through MCP with auto_start=false,
survives temporary broker restart and still reports no Blender worker connected.
The same broker-only path previews and removes a recognized seven-byte incomplete
botanical stage after reconciliation. Real MCP LOD export journals record the
original operation ID and published stage identity.

Separate child processes die with incomplete NUMERIC, BOTANICAL and VEGETATION_LOD
stages. Known nested numeric staging is discoverable and cleanable after recovery,
but cannot be published as complete output. Wrong-owner access refuses; a foreign
file inside nested staging blocks recovery/cleanup and is preserved. Dry-run byte
counts and guarded deletion pass. Native scene edits are never replayed and the
original broker operation state is not rewritten to success by file recovery.

Previously verified stages now remain protected even if cancellation or an I/O
failure changed their state to cancelled/failed. Explicit discard_ready=true is
needed to delete them. Interrupted cleanup first requires reconciliation; failed
revalidation removes the stale verification checkpoint so remaining incomplete
owned files can be cleaned with a fresh guard. This preserves the existing
cancelled-cleanup regression. Verification sends progress/free-storage heartbeats
and observes remote cancellation; a controlled-clock test cancels inside validation
rather than waiting until final handoff. Public exporters check cancellation after
durable verification and before rename, without duplicate full botanical/LOD
validation. Existing ordinary and centimetre bundle validators remain compatible.

This is explicit guarded staging retention, not automatic age-based export expiry.
The existing automatic render-output/history policy is unchanged. Published assets,
unknown directories and old unjournaled stages are not cleanup candidates; journal
metadata is retained. Crashes before stage identity registration require operator
review. Tests establish process-death/lock release and broker restart recovery,
not physical power-loss persistence of every file or restoration of unsaved scene
edits. Native glTF calls retain their coarse cancellation boundaries. New fixtures
are reproducible temporary test data; earlier delivery/render evidence is unchanged.
No packages, venvs, installed runtime/service changes or pushes occurred.

## Shared-template vegetation LOD GLB/wind bundles — 2026-11-03

New export_botanical_lods/validate_botanical_lod_bundle tools package unchanged
owned profiles into per-level wood/shoot numeric GLBs, one shared GLB per leaf
variant and canonical hierarchy/instance/selection semantics. SOURCE placement
omits preview offsets by default; DISPLAYED uses the displayed physical placement.
The semantic wind transform and every decoded asset transform are checked against
that choice. Templates normalize to identity physical metre placement. Canonical
leaf/branch/shoot indices remain nested; original branch indices survive pruning.

Initial native export plus existing botanical export regression passed **2 tests
in 86.98 seconds**. The final Python-disabled MCP workflow and expanded native
placement/pruning/rollback gate passed **2 tests in 142.01 seconds**. Policy,
capability and dependency-free add-on checks passed **4 tests in 46.80 seconds**.
The final publication-failure/foreign-file preservation gate passed **1 test in
34.00 seconds**. Skill/whitespace checks pass. Host/test composition varied;
these are focused gate timings, not throughput claims or a full-project suite.

The structured fixture uses the existing sparse 5m, 37-branch, 140-leaf canonical
model and native 140/70/35-leaf levels. Its bundle contains nine GLBs: six
wood/shoot assets and three shared templates. Expanded triangle counts remain
28,548/14,620/7,608. It exports after the original tree is removed, preserves the
native profile guard, saves/reopens the profile, removes it and still validates
the files. Arbitrary Python execution remains disabled throughout MCP editing
and export. Native source geometry/render evidence remains in the preceding
LOD milestone; this gate qualifies delivery rather than new optical behavior.

The native centimetre fixture adds translation, rotation, uniform physical scale
1.2 and an 8m display offset. SOURCE delivery uses x approximately 3m; DISPLAYED
uses x approximately 11m. Four levels retain 140/70/35/2 leaves and the final
stress level prunes wood to nine original branches. Its expanded count is 524;
its full-loss budgets are explicit and do not qualify visual delivery quality.
Each mode has eleven GLBs and only three template assets. Every sub-bundle is
independently decoded for fields, positions, oriented triangles, UVs and metre
placement. Branch fields are checked against the full hierarchy and each retained
index set. The validator regenerates canonical foliage and greedy LOD selections,
comparing quality metrics, nested identities, ancestry and triangle budgets.
Host-specific mask memory accounting is excluded from semantic plan equality;
the saved plan content guard remains checked. Rehashed leaf-index tampering is
rejected. Existing ordinary and centimetre botanical bundles still validate after
extracting the shared numeric-asset verifier/export helper.

Stale guards, small byte bounds and existing destinations refuse. Cancellation
inside the numeric sub-bundle and after full LOD-bundle verification removes only
owned staged data and preserves exact native IDs/profile guard, active level,
frame, active object and selection. A deliberately injected second-file publication
failure preserves a partial destination and an unrelated file written there;
source IDs/guard remain intact. Publication is multi-file and not crash-atomic.
Automatic interrupted-job recovery/retention for this format is still separate.

Evidence under `/tmp/mb-vegetation-lod-export-20261103` includes source.blend,
the ordinary three-level bundle, centimetre SOURCE/DISPLAYED four-level bundles
and proof JSON. All copied bundles were independently revalidated with system
Python. These unsigned witnesses establish correspondence, not provenance,
PBR/texture-budget/backlighting/vein/alpha fidelity, authored managed-tree UV2,
animated LOD playback, a receiving engine scene/shader, optical/shadow/GPU behavior
or cards/impostors/collision. The whole-bundle output limit is 512 MiB; existing
sub-bundle and canonical plan limits apply. Free-space estimates exclude unknown
embedded material images until actual component sizes are available. No packages,
venvs, installed runtime/service changes or pushes occurred.

## Coverage-scored native vegetation LODs — 2026-11-03

New plan/create/inspect/activate/remove tools build independent full LOD0 plus
one to four near/mid levels. A deterministic lazy greedy selector scores opaque
blade pixels and source boundary pixels in fixed root-local views. Selections
are nested; leaf IDs/orientation/scale/phase/flutter remain unchanged. Major wood
and every selected leaf's attachment ancestors remain; lower radial counts rebuild
wood with original branch indices, rather than interpolating discrete IDs.
Shoots retain only required attachments. All levels share one copied prototype
collection. Canonical model/foliage/selection/wind Text persists across save/reopen.

The initial workflow/native/pure and existing native wind regression passed
**7 tests in 150.80 seconds**, including the existing large native wind population
probe after the shared rest-instance builder refactor. Policy/contracts, masks,
capability and dependency-free add-on gate passed **6 tests in 24.04 seconds**.
Final isolated-render/source-visibility-restoration and native lifecycle gates
passed **2 tests in 36.50 seconds**. Later mask-estimate/policy checks passed
**3 tests in 8.47 seconds**; final early-memory/combined-work bounds, actual branch
pruning and lifecycle gate passed **1 test in 9.01 seconds**. Skill/whitespace
checks pass. These focused gates are not a fresh full-project suite.

Pure mask unions match the existing independent foliage coverage analyzer for
source and selected subsets. Leaf selections repeat exactly and remain nested;
branch ancestry closes over all attachment parents. Triangle totals include wood,
shoots and expanded leaf instances. Zero-loss requests with one retained leaf
fail quality; insufficient projection/mask/gain budgets refuse. Native creation
additionally projects actual woody triangles in the same crown window, bounding
missing coverage/boundary and excess occupied area. That gate is explicitly
pending in the initial plan; a leaf-only plan does not certify native wood.

The structured fixture disables arbitrary Python execution and uses a sparse 5m,
37-branch, 140-leaf source. Its 140/70/35-leaf levels share only three prototypes.
LOD0 has 772 wood + 336 shoot + 27,440 expanded leaf triangles = 28,548 triangles.
The reduced totals are 14,620 and 7,608. FRONT/SIDE/TOP leaf pixel losses are
approximately .0323/.0667/.2267 at 70 leaves and .4194/.2000/.5067 at 35 leaves.
The .25 default rejects the second level; the fixture explicitly raises its loss
budgets to .55 before creation. Native wood coverage loss stays below .093 in all
three views. Every leaf instance in every level matches its retained rest pose;
maximum fixture position error was about 9.54e-7m and normalized linear component
error about 3.50e-7. Three fixed-camera 320x256 Cycles images were rendered/opened
and inspected. Temporary source/Cube render visibility is restored before saving;
the original tree guard remains unchanged. The source is intentionally sparse,
not the final mature-oak foliage or realism reference.

A centimetre-scene fixture adds rotation, uniform physical scale and display
offset. Cancellation during the first native level and immediately before
handoff restores the exact native ID set/source guard. Native wood/shoot triangle
counts equal the plan. Activation, save/reopen, independent survival after source
removal, shared-outside-mesh-user refusal, foreign-member refusal and guarded
cleanup all pass. A deliberately aggressive two-leaf stress level prunes wood
from 37 to nine branches while preserving the exact original branch-index set
and parent ancestry. This stress level permits full pixel loss explicitly; it
is a semantics/lifecycle test, not an acceptable visual delivery profile.

Projection admission includes source/rebuilt native wood as well as leaves.
Mask admission happens before full attachment generation; its host-specific
Python integer/container estimate covers mask payload only, not heap/native/peak
RAM. Default budgets are 60 million projections, 256 MiB mask payload and two
million gain evaluations. Work/cancellation remain bounded and progress is tracked.
Native ownership/content/user guards cover staged IDs and shared references;
materials are retained/shared, without optical qualification. Existing wind
preview signatures retain their prior default behavior.

Evidence is local under `/tmp/mb-vegetation-lod-20261103` (.blend, three PNGs,
plan/readback proof). This qualifies static native near/mid representations in
fixed opaque geometry views, not alpha/translucency, perspective/shadows, real
render performance, authored managed-tree UV2, native animated LOD playback,
LOD GLB/wind packaging, cards/impostors or collision. Crown windows do not cover
all trunk-base geometry, and pixel centers can miss subpixel blades; inspect
higher resolution and renders. Hard-crash staging recovery remains unqualified.
No packages, venvs, installed runtime/service changes or pushes occurred.

## Botanical wind interchange and shared templates — 2026-11-03

New inspect/export/validate botanical bundle tools bind canonical wind settings,
model hierarchy and leaf attachment tables to verified wood/shoot numeric GLBs
and one static GLB per leaf variant. Export derives branch index, parent index,
whole-axis anchor, individual-segment pivot, phase, stiffness and height weight
on disposable copies. Axis anchors and solver pivots are deliberately distinct.
The semantic JSON retains stable branch/bud/leaf IDs, generator/seed, full parent
hierarchy, compiled wind field/solver/placement, shoots, leaf XYZ orientation,
scale, variant, phase and flutter. Original native prototypes stay shared; exported
instances reference shared template files rather than realized population meshes.

The final native plus structured workflow tests passed before a policy-fixture
argument error, **2 passed in the 32.64-second stopped run**. Corrected path/policy,
capability, semantic-mapping and dependency-free add-on checks passed **5 tests in
19.35 seconds**. Final nested-sub-bundle and whole-bundle cancellation/semantic
checks passed **2 tests in 15.47 seconds**. Both bundled skills validate; whitespace
checks pass. These focused gates do not constitute a fresh full-project suite.
The placement bug uncovered by the first fixture was fixed and committed
separately; see the exact-placement qualification below.

The structured fixture disables arbitrary Python execution, exports a 5m,
37-branch tree with 28 leaves and three templates, waits through the tracked
operation, revalidates decoded files, saves/reopens the editable source and then
removes it. File-only validation still succeeds. The five delivered GLBs contain
772 wood triangles, 168 shoot triangles and 196 triangles per leaf variant;
wood/template UVs remain intact. This fixture has no authored UV2; the generic
numeric exporter separately qualifies UV2, and managed-master UV2 editing remains
unqualified here. Semantic branch rows are compared to the hierarchy, template
vertices to canonical template generation and the entire seeded attachment table
to regenerated canonical data. Version, wind field, compact foliage, source plan
and content hashes are checked. Sidecar modification fails both ordinary hash
checking and deeper attachment/binding checks after its file inventory is rehashed.

A native .01-scene-unit fixture adds translated/rotated/uniformly scaled placement.
Every actual Geometry Nodes leaf instance is matched uniquely by variant and rest
position/orientation/scale to the table. For its 28 instances, maximum physical
position difference was about 5.84e-7m and maximum normalized linear-matrix
component difference about 3.49e-7. Bare export produces only wood. Stale guards
and byte bounds refuse. Cancellation inside a numeric sub-bundle and after full
botanical verification preserves the exact source guard/native ID set, selected
objects, active object and frame, removing only owned staging/native copies.
Successful exports preserve these too. Root guard inputs canonicalize numeric
wind defaults so equivalent inspected/exported options do not become stale.

The retained source project, ordinary bundle, centimetre bundle and proof JSON
are local under `/tmp/mb-botanical-export-20261103`; both copied bundles were
independently validated with system Python. The output is GLB files plus a shared
instance/hierarchy sidecar, not EXT_mesh_gpu_instancing, a single engine scene,
an executable wind shader or optical/backlighting/vein equivalence. Native shader
export losses are explicit; PBR baking remains a separate workflow. Bud geometry
stays in semantic organs. Controlled/edited managed masters refuse; corner,
instance, component, file traversal and byte budgets bound work. Native glTF calls
are cooperatively cancellable only between calls. Free-space estimates/progress
exclude unknown material images until actual sizes are available. Multi-file
publication is not hard-crash atomic: partial/staging directories need inspection.
Large populations, default full-tree export throughput, vegetation LODs, continuous
native wind and engine parity remain unqualified. No packages, venvs, installed
runtime/services or user Blender sessions changed; nothing was pushed.

## Exact botanical placement through regeneration — 2026-11-03

Regeneration copies the root's rotation mode, ordinary/delta transform channels
and parent inverse directly. Matrix assignment previously decomposed these values
through float32 and could fail the placement check for rotated centimetre scenes
at large native scale. The native regression exercises XYZ, quaternion and
axis-angle modes, translation, scale and delta transforms at .01 scene units;
after foliage regeneration every channel and the complete world matrix match
exactly. The focused placement and botanical export regression passed **2 tests
in 19.29 seconds**. This does not add support for controlled/animated roots or
qualify arbitrary parent deformations. No installed runtime or packages changed.

## Independently verified numeric field GLB bundles — 2026-11-03

The generic numeric field foundation now exports explicit semantic bindings as
raw float32 scalar lanes, with a separate corner-correspondence lane. A versioned
manifest stores source schemas/mapping/witness, UV names, placement and units,
unmapped-field notices, encoded-file hash and proof. Source meshes/materials stay
editable; temporary delivery copies alone receive private export attributes.
There is no UV-channel packing. A standard-library decoder checks all field rows,
local positions, oriented corner triangles, UVs and metre world placement before
publication and on later validate_attribute_bundle calls.

The structured workflow/native/contract/capability/addon gate passed **8 tests in
42.32 seconds**. Tamper/integer-policy and existing unit-normalization regression
passed **7 tests in 17.76 seconds**. Final native changes (expanded-component bound,
nonfinite witness rejection, existing-output refusal and corrupt-file rejection)
passed **2 tests in 9.00 seconds**. A final regular-file/symlink validator gate passed **1 test in 6.96 seconds**. Explicit two-material split/correspondence verification passed **1 test in 4.44 seconds**. Skill and whitespace checks pass. These focused
checks are not a fresh full-project suite.

An actual GLB fixture covers custom scalar/vector fields, 24 corner witnesses,
12 cube triangles split between two material primitives and two independently decoded UV maps. Deliberate field,
position, UV2, winding, nonfinite-source and placement discrepancies refuse. A
second native fixture packs all five numeric storage types across POINT/FACE/
CORNER into ten scalar lanes. It uses translation, rotation, nonuniform positive
scale and a .01 scene unit. Its decoded world placement and both UV channels match.
INT 16,777,216 packs exactly; 16,777,217 refuses. Cancellation after verification
preserves exact source guard/ID inventory (including a source fake-user mesh),
removes only staged native copies/files, and leaves no output directory. A successful
export likewise preserves IDs/guard; existing output is refused and a malformed
GLB is rejected by subsequent validation; symlinked bundle files refuse before reading. Native scene-unit storage is float32,
so the fixture compares .01 with tolerance rather than exact Python equality.

The structured fixture, with arbitrary Python execution disabled, plans and
exports bend_weight, then revalidates its saved bundle and checks the original
attribute guard. It also retains the earlier instance-field realization, shader,
render and .blend reopen checks. Ordinary homogeneous/mixed-scene unit export
regressions passed with custom-attribute export disabled by default.

This is a static mesh correspondence profile: no loose geometry, modifiers,
constraints, animated/shape-key source or unrealized instance component. EDGE
fields need explicit projection. At most 16 source fields, 64 scalar lanes, eight
UV maps, one million corners and four million expanded scalar components are
supported; a 512 MiB output ceiling applies. Initial free-space estimates exclude
unknown embedded-image sizes, and progress/final checks report actual storage.
Publication uses an exclusively created destination but two file moves are not
hard-crash atomic; interrupted staging/partial directories need operator review.
Saved witnesses are not signed provenance. PBR fidelity, downstream CUSTOM import,
wind shader interpretation, complete botanical hierarchy/leaf packing, vegetation
LODs and continuous wind are not qualified by this generic foundation. Evidence is retained locally at `/tmp/mb-attribute-export-20261103` and its copied
GLB/manifest were independently revalidated. No packages,
venvs, installed runtime/service changes or pushes occurred.

## Guarded numeric mesh attributes — 2026-11-03

Structured create/update/ramp/remove commands now edit custom POINT/EDGE/FACE/
CORNER FLOAT, INT32, BOOLEAN, vector3 and linear RGBA fields. Base-storage guards
cover geometry/topology, all attribute records, selectors and mesh sharing;
evaluated readback uses a distinct representation and cannot authorize base edits.
Native storage is read back before successful handoff. Internal/topology/UV fields
are protected. Cooperative rollback restores in-place values/selectors or removes
only the staged isolated mesh. Names and memory/work dimensions are bounded.

The initial focused workflow/native/contract/geometry/capability/addon gate passed
**9 tests in 38.48 seconds**. Subsequent native verification including explicit
shared-copy cancellation passed **1 test in 4.34 seconds**. The final structured
render/reopen fixture with an independent pixel check passed **1 test in 18.56
seconds**. The design skill validates and whitespace checks pass. These focused
checks do not constitute a fresh full-project suite.

Native checks cover all five storage types and four domains, Boolean sparse
patches, preserved UV/LightmapUV bytes and existing color/UV selectors, stale and
protected-field refusal, create/set/remove cancellation with exact ID inventories,
shared-data refusal/explicit isolation/cancellation, and single-user shape-key
coordinates/Key/action/armature modifier identity. Shared shape-key isolation
refuses without creating IDs. Removing an attribute during rollback may recreate
its native handle/order while preserving its named content and semantic guard.

With arbitrary Python execution disabled, the MCP fixture makes an eight-point
Z ramp, reads it through GeometryNodeInputNamedAttribute, stores it on INSTANCE,
then realizes eight small cube instances. Evaluated readback has 64 point values,
32 zero and 32 one; the eight-point base field and guard stay unchanged. A native
ShaderNodeAttribute Factor output drives base color. The 192x192 Cycles render
shows a white top and darkening sides; independent decoded pixel comparison
rejects a uniformly black result. The project saves/reopens with the same guard.
The first visual probe found coincident startup/fixture cubes; moving the fixture
clear fixed the test scene. Local evidence: `/tmp/mb-attributes-20261103`.

This qualifies evaluated **mesh** readback after realization, not arbitrary
unrealized INSTANCE-component inspection. FLOAT_COLOR is nonnegative linear RGBA;
other native layouts are inventory/hash-only through this surface. First-color
creation uses Blender's automatic activation. Animation/drivers targeting mesh
fields and shared shape-key isolation require specialized workflows. Hard-crash
atomicity, wind packing schemas, custom GLB retention, engine interpretation and
continuous wind remain outside this milestone. No packages, environments,
installed runtime/services or user Blender sessions changed.

## Owned sampled native wind previews — 2026-11-03

Native preview planning/creation/inspection/removal now use the portable solver
on an independent copy. Relative shape keys cache wood, bud/shoot and three-point
leaf-frame samples; Geometry Nodes reconstruct rigid orientations and retain one
prototype per variant. Playback uses native actions/nodes. The soil ring is pinned,
source materials stay shared, and an actual collection-to-Text ID reference keeps
the nonexecutable semantic JSON alive across save/reopen. UUID markers, a closed
native-ID inventory and content/user guards protect removal and staged rollback.

The final native lifecycle/render gate passed **3 tests in 38.29 seconds** for bare
and foliated centimetre trees and the structured rendered fixture. It checks
source guard/ID/frame/selection preservation, cooperative rollback during baking
and before handoff, key and midpoint readback, pinned native soil vertices and
identical endpoint geometry after the baked range. Content guards remain stable
through playback; save/reopen remains valid. A preview survives removal of its
source. External mesh sharing and foreign collection members refuse deletion;
added constraints invalidate qualification. Fresh guarded cleanup preserves the
source/materials. Equivalent returned plan options round-trip without stale guards.

The 5m, 37-branch fixture has 140 leaves sharing three copied prototypes. It bakes
frames 1–13 and independently checks all 25 keys/midpoints, every leaf instance's
variant/position/orientation/uniform scale/orthogonality, all target mesh positions
and every nonzero mesh edge. Its observed maximum errors are approximately
0.000001m at keys, 0.000401m at midpoints, .1371 degrees in leaf orientation,
3.46e-7 in relative leaf scale and 1.64e-7 in normalized axis dot product. Maximum
edge strain is .00950 (about .95%). The 180,432-byte coordinate estimate covers
raw sample coordinates, not total native memory. Three 320×256 Cycles frames were
rendered, opened and inspected; the native project reopens and supports cleanup.

The default 14m source has 1,251 branches and 20,940 leaves. A two-key native
population check passed with all 20,940 instances and only three prototype meshes;
new mesh count equals the four animated components plus the three prototypes.
Keys and their midpoint passed pose/rigidity/edge checks, with maximum midpoint
error about .000115m and edge strain about .00164. Planning the default 49-sample
range fits its default budgets: 55,632,600 raw coordinate bytes and 23,775,808 work
units. This checks that plan, not a completed 49-sample large-population bake or
1000-tree performance. One initial large native probe passed in **209.91 seconds**;
host load and test composition varied, so no throughput/speedup claim is made.

The remaining structured workflow/math/policy/capability/addon gate passed **9
tests in 52.18 seconds**. A combined run had already passed its three native tests
but then hit a temporary broker-startup timeout; its late owned child was removed,
a fresh isolated broker was ready in .163 seconds, and remaining checks were rerun.
Static textured-asset camera framing and managed building-instance preview
regression passed **2 tests in 100.26 seconds**. Server/preview-policy checks passed
**9 tests in 45.67 seconds**, with the existing Starlette/AnyIO deprecation warning.
Camera fitting now bounds evaluated mesh instances without realizing them, and
numeric pose-frame arrays no longer enter image-artifact enrichment. Both bundled
design/animation skills validate; whitespace checks pass. These are focused gates,
not a fresh full-project suite.

The cache has at most 121 samples, eight samples per fastest motion cycle and
explicit instance/coordinate/work budgets. Interpolation is linear and frozen
outside the range; checks cover keys and midpoints rather than continuous extrema.
Creation uses the connected main thread with cooperative progress/cancellation;
raw coordinate/checkpoint estimates do not establish total RAM or save size.
Hard-crash rollback during staging, collision/volume/biomechanics, continuous
scalable wind, runtime wind-attribute retention and engine parity remain open.
Evidence is local under `/tmp/mb-wind-preview-20261103`. No packages, installed
runtime/services or user Blender sessions changed.

## Portable hierarchical wind preparation — 2026-11-03

`inspect_botanical_wind`, `sample_botanical_wind` and `export_botanical_wind`
introduce a standard-library motion model over valid managed botanical masters.
It compiles explicit seeded spatial/temporal world-metre waves, applies
parent-first anchored segment rotations and rigid branch-attached leaf flutter,
and reports a conservative all-time rotation bound. Root translation/proper
rotation/positive uniform physical scale are captured from the evaluated source;
admitted float32 rotation roundoff is fitted to an orthonormal basis and reported.
The source geometry, frame and native IDs remain unchanged.

The final math/policy/native/MCP/capability/addon gate passed **9 tests in 36.05
seconds**. Known field phases have independent answers; canonical settings and
seeds reproduce explicit waves. Branch endpoint distances, connected starts,
fixed root and orthonormal rotations are checked from returned coordinates and
matrices. Leaf rotations preserve point distances; a globally zero field returns
the rest centerline and zero flutter. Tests exercise time variation, rotation
budgets, finite/type/time/placement limits and cooperative sampling cancellation.

The native centimetre fixture uses a translated, rotated, uniformly resized tree
with foliage. It verifies metre placement, unchanged source guard/native-ID set,
root matrix and frame, all-branch length/junction/root metrics, and refusal of
nonuniform placement. Sidecar cancellation after the owned temporary file is
written preserves an existing destination and a foreign conventional `.tmp` file;
the owned temporary is removed. Stale guards and byte limits refuse before
publication; the valid JSON retains model, explicit waves and leaf/shoot data.

With arbitrary Python tools disabled, the structured 5m fixture has 37 branches
and 28 leaves. Sampling at −.5, .2 and 1.5 seconds gives maximum endpoint
displacements approximately .0783, .0818 and .0989m, with cumulative rotations
approximately 2.19, 2.20 and 2.91 degrees. Model segment-length errors are below
1e-12m and junction/root errors are zero. Paged responses stay bounded while
metrics cover every branch. The exported JSON replays the sampled coordinates;
inspection/export avoid mutation checkpoints. Both bundled design/animation
skills validate and whitespace checks pass. Evidence is local under
`/tmp/mb-wind-20261103`. These are focused checks, not a fresh full-project run.

This milestone qualifies portable kinematics and guarded semantic publication.
The field is sampled at undeformed world anchors; parent animation is frozen.
Stiffness/response are artistic controls. Native deformation/animation, tube-surface
strain, collision, rendered wind appearance, GLB attribute packing and runtime
shader parity remain open. No packages, installed runtime/service or user Blender
session were changed.

## Verified-bundle PBR atlases — 2026-11-03

`inspect_texture_atlas` / `build_texture_atlas` now pack successful original bake
bundles into nonrotated/unresampled tiles with edge-duplicated base-level gutters.
Plans bind source file hashes, conversion declarations and layout; explicit
dimensions, input-byte and base/full-mip RGBA8 budgets bound work. The shared
texture worker rechecks native input bindings and emits separate metre-space
meshes, remapped AtlasUV and one shared PBR material. Source bundles and the editor
remain unchanged. Existing validation checks every output object; layout metadata
is also bound during completion and abandoned-job recovery.

The final atlas workflow/layout/policy/addon gate passed **7 tests in 46.74
seconds**. A UV-driven two-dimensional color gradient and a second blue input
exercise four maps and every inner/gutter pixel, matching source RGBA bytes
within one unit after PNG round-trip. Inputs deliberately mix scene scales 1
and .01. Independently decoded GLB coordinates retain the blue plane's 4m origin
and 5m maximum X; raw TEXCOORD accessors match both packed tile rectangles after
glTF's V conversion. The delivered GLB has two meshes and one material. Its
128×64 four-map layout reports 131,072 base RGBA8 bytes and 174,768 full-mip
estimated bytes, with 25% inner-tile occupancy.

The same workflow cancels a live 2048² atlas while actually packing maps, checks
free-space/estimate progress, confirms the owned process exits, recovers the same
cancelled request ID and removes its owned partial directory. A genuine complete
atlas simulates the post-worker/pre-adoption crash window: altered layout metadata
refuses recovery, restored metadata adopts without replay and passes native
validation. Layout changes, native output transforms, stale guards and nested
output paths refuse. Ordinary bake validation still checks its own single object
even if an extraneous empty atlas-style inventory is inserted into its manifest.

Real fitted leaf/cluster bake → atlas → reopen/validate → GLB workflows at scene
scales 1 and .01, plus native addon dependency isolation, passed **3 tests in
98.79 seconds**. Both atlases retain four maps and thin-leaf conversion loss
declarations. The centimetre fixture's base-color and alpha atlas images were
opened and inspected.
Existing high-to-low PBR/GLB, worker cancellation/reconnect/adoption/parent-death
and managed leaf conversion regression plus layout checks passed **7 tests in
118.98 seconds**. Server/texture-policy checks passed **10 tests in 18.34 seconds**
with the existing Starlette/AnyIO deprecation warning. Both bundled skills validate
and whitespace checks pass. These are focused checks, not a fresh full-project run.

The native assembly profile requires original successful bake bundles, matching
map sets, one UV layer, positive nonsingular transforms and matching untextured
PBR constants. Unsupported native inputs fail in the owned worker. Only base PNGs
are emitted; mip chains, compression, anisotropic bleed, measured GPU memory,
wind-aware attributes/LODs and engine import remain unqualified. Physical placement
is preserved, so separate representations may overlap until deliberately arranged.
Evidence is local under `/tmp/mb-atlas-20261103` and
`/tmp/mb-atlas-foliage-20261103`; installed runtimes/services and dependencies were
not changed.

## Fitted leaf and mesh-cluster card targets — 2026-11-03

`inspect_foliage_card` / `create_foliage_card` now fit a convex envelope or rectangle
to evaluated local mesh sources in world TOP/FRONT/SIDE projections. The guard
binds source geometry/transforms, supported shader inputs, options, current frame
and scene scale. Targets retain editable convex geometry and CardUV, returning
inspected parameters for the existing isolated texture worker. They preserve
sources and selection. Instance-bearing sources refuse and require realization.
Source triangle/outline-vertex/raster budgets are explicit; cooperative
cancellation checks run during inspection/rasterization and before handoff.

The final focused native/workflow/math/discovery/addon gate passed **9 tests in
67.13 seconds**. Native checks cover metre/centimetre physical sizes and bake
distances, stale source/material/options, exact native-ID cancellation rollback,
preserved source matrices/selection/active object and refusal of mesh sources
that also emit instances. Pure known-answer triangles check projected area,
normal orientation in all three views, padding, coverage, budget/degeneracy
refusal, cancellation and area stability under large translation. An earlier
card/server/texture-policy gate passed **13 tests in 37.29 seconds**, with the
existing Starlette/AnyIO deprecation warning. The bundled design skill validates.
These are focused checks, not a fresh full-project regression.

With arbitrary Python tools disabled, the structured fixture creates a native
leaf, fits/bakes its card, repeats with a two-leaf mesh cluster, reopens and
validates both texture bundles, exports the leaf card to GLB, independently reads
physical file coordinates and renders a preview. It runs at scene scale 1 and
.01. Both previews were opened and inspected. The default leaf's fitted envelope
has 20 triangles and area approximately .005269m² versus two triangles/.007449m²
for its rectangle. At 128², predicted target geometry coverage is 76.363%; the
worker measures 76.370%, versus the rectangle's predicted 54.028%. The rectangular
two-leaf cluster measures 45.833% geometry coverage at 96² under both unit scales.

These are opaque geometry/sample and Blender delivery results, not measured
runtime overdraw, optical equivalence, engine integration or generalized species
proof. The fit flattens depth and cannot preserve internal holes; native thin-leaf
conversion still requires explicit FRONT_PBR and retains its loss declaration.
Atlas packing, texture-memory/mipmap budgets, wind and vegetation-aware LODs
remain open. Local evidence is under `/tmp/mb-fitted-cards-20261103`, with separate
metre/centimetre bundles and previews. No packages, installed skills, services or
user Blender sessions were changed.

## GLB physical scene units — 2026-11-03

The common exporter now applies scene scale through file-only uniform root
transforms. Scene objects/settings and mesh, skin, morph and animation binary
payloads remain unchanged. Default scale 1 bypasses rewriting. LOD/package
manifests bind their declared scale to encoded transforms; static LODs record
physical world bounds and batch packages prove metre-world surfaces. Native
skeletal/morph replay retains source-scene error budgets through a separately
labeled comparison decode, after checking the delivered unit roots.

Pure unit/LOD/skin/package contract checks passed **31 tests in 11.41 seconds**.
The structured MCP unit workflow and parametrized native morph/package fixtures
passed **5 tests in 60.28 seconds**. Additional native mixed-scene/static-LOD/
skeletal-export checks passed **6 tests in 72.87 seconds**. These are focused
checks, not a fresh full-project regression.

The read-only card inspection is excluded from mutation checkpoints. The
centimetre end-to-end workflow, including that assertion, passed again in
**33.64 seconds** after correcting its bridge classification.

Addon archive/frontend isolation, export-job crash recovery, cancellation before
publication and server policy checks passed **18 tests in 33.60 seconds**, with
the existing Starlette/AnyIO deprecation warning. The bundled design skill
validates.

After tightening physical-bound validation to reject malformed/nonfinite bounds,
the structured unit workflow and unit/LOD/skin/package contract gate passed
**32 tests in 29.81 seconds**, including corrupted-bound refusal.

With arbitrary Python tools disabled, the structured centimetre-scene fixture
delivers a standalone leaf with independently decoded 0.104m extent, static LOD
world bounds, a package with nested LODs, and animated skin. Its raw decoded joint
translation is 0.10 to 0.12m and sampled endpoint displacement is 0.02m. Separate
native morph-only and skinned-morph fixtures run at scale 1 and .01, checking raw
physical coordinates against known source ranges as well as native replay.
Package failure/rollback/ID cleanup runs at both scales. Binary chunk identity,
shared homogeneous scene roots, metadata/transform tampering and scale-1 no-write
behavior have direct checks.

Whole-file mixed-unit scenes refuse before modifying an existing output; explicit
active-scene export still works and leaves units, matrices and native IDs intact.
Nondefault rewriting is bounded to 512 MiB files/16 MiB JSON and inherits native
export's partial-write boundary. No camera/light-unit or downstream Godot
qualification is claimed. Evidence is retained locally under
`/tmp/mb-gltf-units-20261103`; no service, installed runtime or dependencies changed.





## Standalone leaf physical unit conversion — 2026-11-03

Standalone leaf creation now converts its metre recipe using object scale,
matching the existing botanical-root convention. It leaves scene settings intact
and returns normalized recipe, scene unit scale and physical `world_bounds_m`.
Local generated geometry remains in canonical metres. Existing user objects are
not retroactively changed.

The new native unit fixture plus existing foliage lifecycle/backlighting tests
passed **3 tests in 46.81 seconds**. Independent vertex/matrix readback verifies
a 0.104m blade-plus-petiole extent under metric scale .001, .01, 1 and 100, and
imperial .3048. Shape-plan guards remain unchanged across these scales. A saved
centimetre-scene leaf reopens at the same physical size; final cancellation restores
exact native IDs and preserves scene scale. The default-unit thin-leaf PBR/card
and capability regression passed **3 tests in 50.59 seconds**.

A separate export probe originally found .104m native physical extent becoming
10.4 in the .01-scene GLB. The subsequent common-export correction documented
above now independently decodes approximately .104m. The original leaf-creation
fixture itself remains a native-size check; default-unit card results are
unaffected. No service/package/environment changes were made.

## Explicit thin-leaf front-PBR baking and alpha-card delivery — 2026-11-03

`thin_foliage_mode` defaults to REFUSE for inspection/baking. Explicit FRONT_PBR
qualifies only the managed native thin-leaf shader topology and supported static
upstream nodes. Its mode-bound guard and `material_adapters` report identify the
selected front-surface approximation and omitted native back color, translucent/
transmission lobe and backface shader. The disposable worker forces the leaf-side
color selector to its front branch and retains connected normal/bump inputs.
The editor's source material and optics remain unchanged.

The final front-adapter/native topology/profile/server/addon/capability gate passed
**15 tests in 53.34 seconds**, with the existing Starlette/AnyIO deprecation warning.
Existing texture-bake worker cancellation/reconnect/completed-adoption/parent-crash
and native surface ownership checks passed **6 tests in 86.50 seconds**. The alpha
card/export plus existing foliage cancellation/optics/addon checks passed
**5 tests in 53.78 seconds**. Both bundled skills validate and whitespace checks pass.
These are focused checks, not a fresh full-project regression.

With arbitrary Python tools disabled, a reversed high-source plane carrying a
managed leaf material bakes front green (mean RGB approximately .196/.665/.247)
while the native back color is red and its culling/translucency settings differ.
The editing material fingerprint and inspection guard are unchanged after baking.
Default mode refuses before output-directory creation. Unknown topology/nodes
refuse even with FRONT_PBR. Manifest conversion tampering refuses validation;
a simulated abandoned complete bundle also refuses recovery until the declaration
matches its owned record, then adopts without replay and passes native validation.

A second structured fixture projects an actual curved, lobed leaf/petiole onto a
UV plane using FRONT_PBR and BASE_COLOR/NORMAL/ROUGHNESS/ALPHA maps at 128x128.
The template's auxiliary petiole now uses a direct node-based PBR material so
both source slots qualify. Intended silhouette gaps explicitly use a .25 minimum
projection threshold: 5,878/16,384 samples hit geometry (35.876%); two-pixel map
padding produces 39.624% alpha occupancy. The reopened delivered card has two
triangles and passes file/native binding validation. Its Cycles preview and mask
were opened and inspected. Exported GLB material is BLEND/double-sided; its
embedded base-color PNG was independently extracted and decoded, with alpha
0/255 and 39.624% mean occupancy. This proves sampled file alpha, not downstream
engine rendering, optimal mipmaps/overdraw or native optical equivalence.

The fixtures use default scene units. Automatic fitting, multi-leaf/branch atlas
packing, transmission/thickness/back-color maps, wind/LOD attributes and Godot
validation remain open. Subsequent standalone leaf and common GLB unit corrections
are documented above; this adapter fixture itself uses default units.

Default direct-Principled material signatures remain unchanged. A real bark PBR
bundle created before this adapter (without adapter fields in its manifest or
record) was reopened in a fresh Blender and passed current validation with an
empty adapter list. Source snapshot preservation, storage admission/progress,
owned-child cancellation and recovery continue through the existing bake machinery.
Local evidence retains the source/baked bundles, extracted alpha image, GLB, card
preview and inspection/validation records. No service/environment/install/push
changes were made.

## Procedural botanical bark and leaf surface detail — 2026-11-03

Structured create/inspect/configure/remove tools add reusable UV-driven OAK_BARK
and OAK_LEAF detail while preserving shared material identity. Bark combines
elongated cellular fissures, fine noise, colors and bump; leaf veins/midrib add
color/bump without replacing the existing front/back thin-leaf optical shader.
These are artistic shader recipes, not scanned biology, mesh displacement,
physical vascular reconstruction or a finished foliage atlas.

After binding source UV names explicitly, the final surface/native ownership/
existing shader/addon/capability suite passed **6 tests in 126.61 seconds** on
Blender 5.0.1. Profile, shader, texture and server contract checks passed
**12 tests in 34.40 seconds**, with the existing Starlette/AnyIO deprecation warning. Both bundled design/render skill
validators and whitespace checks passed.

The structured MCP fixture disables arbitrary Python tools. It creates leaf detail
on an editable leaf and bark detail on a UV plane, changes leaf optics independently,
renders Cycles close-ups, saves/reopens the editable scene and checks ownership.
The bark normal/base-color/roughness maps are baked by the existing isolated worker
into a separate `DeliveryUV` layout while the procedural source remains explicitly
bound to `UVMap`. Inspection also reports mesh users missing the configured UV map;
the baked asset is reopened and validated against its file/native binding. Normal
and base-color channels have nonconstant values (normal red approximately 0.357–
0.643, base-color red approximately 0.188–0.498); roughness remains its original
constant value. This is a representative 96x96 functional bake, not a final texture
resolution recommendation. The final leaf and fissured bark previews were opened
and visually inspected. Editable source, previews and PBR bundle are retained in
local surface-fixture evidence.

The native fixture verifies exact material/node preservation on cancelled output
handoff, cancelled removal and cancelled creation, node-count stability on rebuild,
original source restoration, preservation of unrelated nodes and independent
optical controls, and refusal of edited color-ramp stops/interpolation. A botanical
tree with foliage receives both detailed materials; growth regeneration keeps the
tree valid and reuses the same native material IDs and detail graphs.

Bump distance is a native shader control, not a calibrated physical length across
arbitrary objects/UVs. Both profiles require suitable named source UVs
(BarkUV/LeafUV by default); ordinary meshes can explicitly choose another UV name. At that surface-detail milestone, native thin-leaf output still refused the
direct-Principled texture-bake profile; the subsequent explicit front-PBR adapter
and manual card qualification are documented above. Automatic fitting/atlases remain open. Procedural graph interchange, back-color/translucency/thickness transfer,
vegetation wind/LODs and realistic mature-oak/bark appearance are not qualified
by this milestone. No installed service, package, environment or installed skill
was changed, and no Git publication was performed.

## Projected botanical coverage and density refinement — 2026-11-03

`inspect_botanical_coverage` adds tracked read-only current/proposed foliage
comparison. Coverage uses the union of opaque blade triangles sampled at pixel
centers in canonical local-metre orthographic frames. It reports the declared
crown ellipse coverage, union/outside area, reflection asymmetry and clipping.
Resolution, margins, projection work limits and optional mask rows are explicit.
Root placement, wood/shoot/petiole geometry, shader optics and perspective are
excluded. It creates no native data or files. No GPU or biological interpretation
is implied; small blades may be missed at coarse resolution.

Focused portable coverage, native-render comparison, structured MCP refinement
and addon isolation checks passed **6 tests in 99.89 seconds**. Portable tests
cover triangle unions/overlap, zero-area projections, rotation, source/work guards
and cooperative cancellation. A final clipping/capability refinement passed
**4 tests in 4.47 seconds**. Foliage/core coverage, capabilities and server checks
also passed **13 tests in 17.99 seconds**, with the existing Starlette/AnyIO warning.
After restricting projection/clipping to blade vertices, the final portable, native
and structured coverage suite passed **5 tests in 147.84 seconds**, while the
larger density render was also running. The bundled design skill validator passed.
This is focused regression, not a new complete-project qualification.

The native 128x128 orthographic fixture independently renders generated Geometry
Nodes leaf instances in Cycles. Its opaque-alpha threshold finds 5,418 pixels,
versus 5,083 CPU blade samples (approximately 6.6% difference). Raster samples and
antialiased rendered silhouettes are different measurements; native petioles also
remain visible. The fixture's tolerance is 15%, not a guarantee for other meshes,
resolutions or view angles.

The structured Python-disabled fixture compares a 3m source with sparse and dense
proposed recipes at fixed 64x64 frames. Sampled crown coverage increases from
1.34% to 44.35% front, 2.59% to 46.26% side and 8.43% to 75.29% top. Proposal
inspection preserves the tree fingerprint. Applying the chosen recipe reproduces
the proposed masks and keeps the inspected fingerprint unchanged during the
subsequent coverage operation. This verifies a closed-loop geometric control,
not final mature-oak visual quality or density under arbitrary growth parameters.

The standalone native 14m density study keeps its front sampling frame and
resolution (128x128) fixed: covered crown pixels increase from 773/6,364 (12.15%)
to 3,082/6,364 (48.43%). The selected recipe uses 67,008 leaves, 4,188 modeled
shoots and three shared prototypes; expanded leaf geometry is estimated at
13,133,568 triangles under an explicitly raised 20-million budget. Defaults remain
unchanged. The Cycles preview was rendered and visually inspected; the editable
`oak-dense.blend` and JSON comparison are retained with local fixture evidence.
A separate fresh Blender process reopened that file, confirmed the guarded tree
validity, counted exactly 67,008 native instances backed by three prototypes,
and checked that the saved engine is Cycles.
This larger study uses a native test helper; the separate 3m refinement test proves
the corresponding agent workflow through structured MCP with Python disabled.
An initial scratch preview inherited Eevee/software OpenGL and was deliberately
stopped; it supplies no Eevee performance or quality qualification. The corrected
run explicitly selected Cycles and reproduced both coverage results exactly.
The denser crown remains an artistic study, with realistic bark/junctions, final
oak appearance, atlases, wind, vegetation LODs and delivery still unfinished.

## Modular leaf geometry and shared foliage — 2026-11-03

Blender 5.0.1 native checks verify deterministic leaf attachment, shared Geometry
Nodes prototypes, material reuse, editable root placement, growth regeneration,
variant-count replacement, save/reopen, external mesh-reference refusal, exact
native-ID rollback at final handoff, explicit derived-edit consent and safe owned
removal with damaged canonical foliage. Standalone leaf cancellation removes its
new IDs. Linked material input patches refuse instead of setting unused defaults.
The native lifecycle fixture passes with 448 leaf instances and three prototypes.

The structured MCP fixture passed **1 test in 95.56 seconds** with arbitrary Python
execution disabled. It creates a standalone leaf and a 14m woody tree, attaches
thousands of leaves, pages semantic attachments, edits thin-leaf optics, renders
Cycles tree/leaf views, saves/reopens, and removes foliage while keeping the valid
woody master. Evidence is in the locally retained foliage fixture directory.

A separate native Cycles backlighting fixture passed **1 test in 4.10 seconds**.
It holds camera/light/geometry fixed and independently changes translucency and
backface handling. Image mean RGB increases from approximately 0.00054 to 0.16814
between opaque and translucent settings while mean alpha stays 0.17870. Explicit
backface transparency reduces mean alpha to approximately 0.00039 (the petiole
remains). These are functional image statistics, not optical calibration. The
translucent image and structured leaf/tree previews were opened and inspected.

Existing three-seed woody-tree rendering/regeneration plus server/authentication,
portable botany and foliage checks passed **15 tests in 120.17 seconds**, with the
existing Starlette/AnyIO deprecation warning. This is focused regression, not a
new full-project qualification.

Focused botanical/foliage ownership, addon dependency isolation and capability
checks passed **5 tests in 38.34 seconds**. Portable leaf/core invariants passed
**7 tests in 15.20 seconds**. Bundled design/render skill validation passed.

The generated crown is visibly sparse: this milestone does not qualify the final
mature-oak appearance or projected coverage. Secondary veins, textured/baked
foliage/bark, leaf cards/atlases, unioned branch junctions, vegetation wind, seasonal
variation, additional species, vegetation LOD/impostors, engine shading and export
attribute preservation remain open. Blade area is summed surface area, not canopy
coverage; expanded triangles are a geometry estimate, not a GPU/memory guarantee.
The native material separates double-sidedness from an artistic thin-surface mix;
it has no alpha mask, thickness calibration or interchange shader equivalence.

## Botanical model core and owned woody masters — 2026-11-03

Final schema/native/contracts checks passed **7 tests in 28.10 seconds**, adding
explicit crown, species, axis/anchor/birth-step, growth-inventory and terminal-bud
validation without changing generated geometry. Existing capabilities, server,
storage, Geometry Nodes, assembly and LOD lifecycle regression passed **16 tests
in 65.28 seconds**, with the existing Starlette/AnyIO warning.

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_botany.py tests/test_botanical_native.py tests/test_botanical_contracts.py --tb=short --maxfail=1
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_capabilities.py tests/test_server.py tests/test_storage.py tests/test_geometry.py tests/test_assembly_native.py tests/test_lod_management_native.py --tb=short --maxfail=1
```

The final standalone/native/contracts/real-MCP/add-on suite passed **9 tests in
137.46 seconds**. An expanded native export/ownership gate passed **1 test in
17.03 seconds**, adding source-unit conversion and cancellation around unique
semantic-output staging without touching a foreign conventional `.tmp` file.
Earlier capability/server/storage/add-on coverage passed **17 tests in 45.25
seconds**, with the existing Starlette/AnyIO warning.

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_BOTANICAL_EVIDENCE_DIR=/tmp/mb-botanical-20261103 python3 -m pytest -q tests/test_botany.py tests/test_botanical_contracts.py tests/test_botanical_native.py tests/test_botanical_trees.py tests/test_export_job_native.py::test_addon_imports_recovery_without_frontend_dependencies --tb=short --maxfail=1
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_botanical_native.py --tb=short --maxfail=1
```

The pure standard-library core generates a versioned local-metre/Z-up graph with
branch/axis identifiers, parentage/order, developmental age proxy, start/end
radii, anchors/stiffness/phase and terminal bud attachments. Tests reproduce
identical recipes/seeds, normalize integer/float recipes, distinguish seeds and
verify actual crown-base/light-control geometry changes. Three default seeds
produce bounded 14m centerlines with more than 500 segments and 100 buds each.
Tests verify one rooted parent-before-child graph, junction continuity, decreasing
age along parent paths, positive tapered radii and child cross-section budgets.
Corrupted hierarchy/radii/version/phase/organs and insufficient scaffold budgets
refuse. Growth stops at cooperative cancellation without native state.

The real MCP fixture has arbitrary Python tools disabled. It creates three seeded
woody masters, checks BarkUV and numeric semantic attributes, pages branch records,
exports JSON and validates it in standalone system Python. It renders a woody
preview, changes height/width/light/gravity through planned guarded regeneration,
saves/reopens and renders the edited master. Removing one master preserves another.
The previews were opened and inspected as bare woody structure; they do not qualify
foliage, real oak appearance, close-up branch joins or light transport.

Native lifecycle tests exercise foreign collection instances, shared mesh data,
manual mesh edits requiring explicit discard, edited canonical semantics refusing
even that opt-in, retained material identity and mesh data names, parent collection
links, static root placement and visibility. Cancellation during meshing and at
the final pre-deletion handoff restores exact native ID/name inventories and the
original tree fingerprint. Model Text is owned through a native collection pointer;
removal deletes that Text and exclusive meshes while retaining reusable materials
and external parents/containers. A non-default scene unit scale confirms metre
conversion without changing the scene scale setting.

Semantic JSON export uses exclusive temporary staging, byte admission and a final
link/replace. A cancellation before publication removes only owned staging; an
unrelated `model.json.tmp` survives. Output JSON preserves canonical model identity,
not scene placement or a verified geometry interchange mapping. Native branch-index
attributes map to canonical branch records, but custom glTF retention is not tested.

Qualification is installed FreeBSD Blender 5.0.1 and local Python 3.11. Stable IDs
and coordinates are reproducible in that environment for a fixed generator/recipe;
this is not a cross-platform floating-point or arbitrary-topology edit guarantee.
Age/stiffness/pipe radii are structural artistic approximations. The scaffold and
space-colonization crown use reference-informed shape controls, not a botanical
or mechanical simulation. Crown envelope/attractor coverage are not leaf coverage.
Lateral wood uses intersecting capped sleeves, not a watertight junction union.
Default brown rough PBR and growth-aligned bark UVs are placeholders for later bark
look development. Leaf organs/geometry/optics, wind deformation, foliage LODs,
atlases/impostors, species generalization and vegetation package/export proof all
remain open. Native commit deletion is noninterruptible and process-crash rollback
at regeneration handoff is not qualified.

Evidence `/tmp/mb-botanical-20261103` contains three canonical models, editable
`oak-masters.blend`, before/after woody PNGs and planning/inspection proof JSON.
The bundled design skill validator and `git diff --check` passed. No application
rebuild, packages, venv, installed service or installed skills were changed.

## Independent camera/frame workers and EXR delivery — 2026-11-03

The final render core suite passed **8 tests in 64.36 seconds**, after recording
snapshot-stage cancellation accurately and issuing a bound cancellation request
if a caught failure occurs after child launch. It includes the packed textured
animation/camera fixture, two-worker admission, restart/cancellation, editor
shutdown/renderer SIGKILL, native dirty-input refusal and file/broker contracts.

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_RENDER_EVIDENCE_DIR=/tmp/mb-render-20261103 python3 -m pytest -q tests/test_render_batches.py tests/test_render_native.py tests/test_render_jobs.py tests/test_render_contracts.py --tb=short --maxfail=1
```

Final packed-texture refinement passed **5 worker/compositor/add-on tests in
76.08 seconds**: animated camera output retains packed checker pixels, shader
paths, frame/camera/filename and compositor settings. A native input guard plus
file/contracts checks passed **5 tests in 9.25 seconds**, proving unpacked and
pixel-dirty images refuse before directory creation or native ID changes. The
wider broker/storage/retention/export-recovery/named-action regression passed
**42 tests in 112.03 seconds**, with the existing Starlette/AnyIO warning.

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_render_jobs.py tests/test_render_contracts.py tests/test_operations.py tests/test_server.py tests/test_capabilities.py tests/test_storage.py tests/test_export_jobs.py tests/test_retention.py tests/test_action_integration.py --tb=short --maxfail=1
```

The initial camera-batch lifecycle fixture passed **3 tests in 47.32 seconds**.
The expanded animated/composited camera-batch, connected compositor and extracted
add-on regression passed **5 tests in 76.37 seconds**. A focused broker/file/
contracts/authentication regression passed **16 tests in 18.68 seconds**, with
the existing Starlette/AnyIO warning. Earlier capability/storage/add-on coverage
passed **21 tests in 27.39 seconds**. Final fixture refinements and wider recovery
checks are recorded above.

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_RENDER_EVIDENCE_DIR=/tmp/mb-render-20261103 python3 -m pytest -q tests/test_render_batches.py tests/test_compositing.py tests/test_export_job_native.py::test_addon_imports_recovery_without_frontend_dependencies --tb=short --maxfail=1
python3 -m pytest -q tests/test_render_jobs.py tests/test_render_contracts.py tests/test_operations.py tests/test_server.py --tb=short --maxfail=1
```

The real MCP fixture disables arbitrary Python tools. It authors a packed textured PBR asset,
object animation, two cameras, depth/normal passes and an exposure compositor.
A new camera/frame batch snapshots that source and produces eight PNG/EXR files
for two cameras and two frames. Frame images differ under authored motion.
Independent parsing verifies PNG16 dimensions, scanline multipart EXR32 headers
and Combined/depth/normal channels, source/output hashes and exact camera/frame
associations. A separate Blender library inspection proves the source contains
the original asset and excludes an object created after handoff. The editing
instance retains its filename, frame, camera and compositor settings while that
new object is added. The resulting PNGs were opened for functional inspection;
64px previews are not final visual-quality or radiometric qualification.

Two long workers run concurrently; a third launch refuses without creating its
output directory. The original operation remains running in the broker while
structured edits complete. Restarting the broker preserves the same render;
normal cancellation stops its owned child and leaves a guarded partial bundle.
Successful output cleanup refuses. A further real batch continues after the
editing application is shut down. SIGKILL of that test-owned render worker marks
the operation interrupted; file-only inspection/recovery/cleanup work without
restarting Blender and never replay the rendering.

File-only tests cover owner separation, file hashes and camera associations,
unknown/symlink refusal, writer-lock exclusion, stale guards, successful-output
protection, interrupted-file reconciliation, explicit referenced-output protection
and anchored cleanup. A broker fixture exercises delegation acknowledgement
idempotency, editor queue release, registration of a replacement editor after
restart, original request-ID deduplication and retry after a transient observation
failure while its writer lock remains held. Render file validation also checks
cooperative hashing cancellation. Native worker/slot locks establish liveness;
production recovery/cancellation never blindly signal saved PIDs.

The qualified runtime is FreeBSD Blender 5.0.1 with Cycles CPU. Limits are two
independent workers per bridge, explicit CPU threads and up to 1000 camera/frame
samples. The source requires packed/self-contained render resources. Source
snapshot save/load are native blocking boundaries, and watchdog byte/free-space
checks can overshoot between polls; they are not filesystem quotas. The editor
is available after snapshot and broker handoff, not during snapshot saving.
There is a launch-to-broker-acknowledgement crash window: an interrupted original
operation can coexist with a still-running file job; inspect rather than replay.
The file marker records operation/owner binding and directory identity. Recovery
reconciles files explicitly; it does not rewrite interrupted operation history.

The worker disables script auto-execution, VSE and crop borders, retains snapshot
compositing and renders full camera frames. External resource/cache freezing,
fluid/volume caches, arbitrary script-dependent scenes, headless Eevee/GPU output,
physics reproducibility, farm scheduling and video encoding are not qualified.
The EXR reader verifies bounded scanline headers/parts/channels, not every pixel
or deep/tiled images. Unused weak brush-library references from factory startup
are editing metadata, not active render inputs.

Evidence `/tmp/mb-render-20261103/camera-batch` includes source.blend, job/status/
manifest/log provenance and PNG/EXR outputs; proof.json records the operation and
independent validation. Bundled render/animation skills and user manual describe
ownership, recovery, admission and profile limits. No package installation, venv,
installed service or installed skill was changed.

## Blender 5 compositing, passes and color controls — 2026-11-03

Final focused compositor/native/contracts checks passed **4 tests in 34.75
seconds**, including exact settings-guard restoration after a consumed-pass refusal
and color preflight cleanup before live application. Existing rendered shader,
textured-building/animation/VSE/API and named-action/recovery workflows passed
**10 tests in 184.28 seconds** (including the compositor fixture). This covers
broker restart without replay and application-exit/checkpoint recovery through
the existing action suite; it does not simulate compositor handoff process death.

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_COMPOSITOR_EVIDENCE_DIR=/tmp/mb-compositor-20261103 python3 -m pytest -q tests/test_compositing.py tests/test_shaders.py tests/test_building_workflow.py tests/test_action_integration.py --tb=short --maxfail=1
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_COMPOSITOR_EVIDENCE_DIR=/tmp/mb-compositor-20261103 python3 -m pytest -q tests/test_compositor_native.py tests/test_compositor_contracts.py tests/test_compositing.py --tb=short --maxfail=1
```

The focused real-Blender/native/contracts/policy/archive regression passed
**16 tests in 50.11 seconds**, with the existing Starlette/AnyIO warning. An
expanded native check then passed **1 test in 4.54 seconds**, adding inspection
and unrelated scalar editing on an animated scene without leaking copied IDs.

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_COMPOSITOR_EVIDENCE_DIR=/tmp/mb-compositor-20261103 python3 -m pytest -q tests/test_compositor_native.py tests/test_compositor_contracts.py tests/test_compositing.py tests/test_capabilities.py tests/test_server.py tests/test_storage.py tests/test_export_job_native.py::test_addon_imports_recovery_without_frontend_dependencies --tb=short --maxfail=1
```

The structured fixture disables arbitrary Python tools. It discovers all 30
allowlisted installed node types, including native menu choices and two-component
sockets, creates a material/asset/preview stage, configures Cycles passes and
Standard display rendering, stages and binds an exposure compositor, then replaces
it and compares actual PNG RGB sums. One stop of compositor exposure produces a
measurable increase (greater than 12 percent in encoded RGB sum for this fixture).
This is functional output evidence, not a radiometric accuracy measurement.

It refuses stale graph guards and a missing socket without changing the bound
graph, preflights an invalid color transform without partial exposure edits,
composites normalized depth, refuses disabling its consumed depth pass and renders
a denoise/glare/blur pipeline using Cycles auxiliary data. The project is saved,
reopened and rendered again with retained settings and compositor binding. Tests
check storage availability through the existing server surface. The 96px exposure,
depth and effects images were opened and visually inspected; these are functional
previews rather than final-quality look development.

The native fixture verifies exact native ID inventories after catalog/inspector
scratch work, invalid graph/socket/cycle preflight, cancellation while staging and
after graph-name/user handoff, and cancellation after scalar/pass/binding changes.
Shared two-scene graphs require explicit shared editing; successful replacement
remaps both bindings. Nested graph users refuse. Native mute edits invalidate the
guard. Keyed color settings and animated compositor groups refuse replacement;
conservative imported scene-action paths through the compositor pointer also
refuse. Scratch color preflight on an animated scene leaves original IDs intact.
Disabling an imported graph is allowed without claiming editing ownership.

Installed FreeBSD Blender 5.0.1 is the qualification scope. The profile uses Image
output node groups, not legacy Composite nodes. Render Layers bindings remain
fixed to their authored scene/layer when shared. Unsupported, large or animated
graphs have no complete content fingerprint. Color guards cover scalar settings,
not custom curves, animation or external OCIO file contents. Dynamic enum menus
are discovered through native RNA validation because dynamic enum_items metadata
is empty in this build. No custom OCIO installation or package changes occurred.

Not all exposed nodes/modes have rendered fixtures. There is no external-image,
file-output or nested-group authoring, multilayer EXR/pass delivery, AOV/Cryptomatte
setup, custom color-curve editing, automatic mask-index assignment, separate render
worker or batch-camera qualification here. A pass flag alone does not establish
support in every renderer. Native graph deletion/rendering remain noninterruptible;
cooperative rollback is qualified, process-crash handoff rollback is not.

Evidence `/tmp/mb-compositor-20261103` contains the editable `composited.blend`,
exposure/depth/effects/reopened PNGs and pipeline/pixel-sum proof JSON. The bundled
render skill validator passed. No venv, dependency/package installation, installed
service or installed skill was changed.

## External/manual LOD adoption — 2026-11-03

The extracted add-on also imported successfully with frontend dependencies
blocked (**1 test in 5.61 seconds**). The focused native/contracts/policy/package
regression passed **20 tests in
36.05 seconds**, with the existing Starlette/AnyIO deprecation warning. It covers
adoption, existing LOD contracts and lifecycle contracts, capability reporting,
server/authentication/archive boundaries, storage and native package ownership.
An additional real-Blender workflow regression passed **12 tests in 138.93
seconds**, including new adoption workflows, existing static LODs, lifecycle
replacement/removal, asset packages and assembly realization.

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_lod_adoption_native.py tests/test_lod_contracts.py tests/test_lod_management_contracts.py tests/test_capabilities.py tests/test_server.py tests/test_storage.py tests/test_package_native.py --tb=short --maxfail=1
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_ADOPTION_EVIDENCE_DIR=/tmp/mb-adoption-20261103 python3 -m pytest -q tests/test_lod_adoption.py tests/test_lods.py tests/test_lod_management.py tests/test_lod_management_native.py tests/test_asset_packages.py tests/test_assembly_realization_native.py --tb=short --maxfail=1
```

The structured MCP fixture disables arbitrary Python execution. It creates
manual reduced meshes, explicitly remaps an importer material, refuses stale
combined guards, adopts two levels plus canonical LOD0, preserves input geometry,
re-adopts through staged replacement with relocated root placement, exports and
validates a static GLB bundle, saves/reopens the project and removes the managed
chain without removing its inputs. Separate source-authoritative skeletal and
morph cases validate three timeline poses, preserve original control fingerprints
and export animated bundles through the existing independent GLB validation.

The native fixture additionally imports a real GLB, remaps its UV layer/material
on owned copies, normalizes mirrored/sheared placement with outward winding,
checks default material-region/attribute loss refusals and explicit opt-outs,
and refuses hidden inputs, zero error limits and stale input edits. Re-adoption
refuses inputs inside the replaced chain. Cancellation during creation and at
the final pre-deletion handoff preserves exact native ID inventories and the
original management fingerprint. A combined skeletal/relative-morph fixture
ignores bogus incoming groups and morphs, transfers canonical skin weights and
relative keys, validates three poses, preserves source fingerprints and returns
to its exact initial native ID set after removal. Cancellation after key transfer
also leaves no copied Key datablocks.

This covers installed FreeBSD Blender 5.0.1, sampled rest/key/pose comparisons
and process-local cooperative rollback. It does not qualify anatomical surface
matching, exhaustive silhouette error, every frame, arbitrary rigs, automatic
LOD switching, Godot or other Blender versions. Inputs must be visible and UV
layout/render-map compatible; raw mode explicitly ignores incoming deformation.
Current evaluated placement still affects raw geometry alignment. Materials stay
shared canonical IDs. Ordinary rebuild automatically reduces at adopted budgets;
re-adoption is required to retain revised authored topology. Source controller
detachment and scene-replacement process-crash rollback remain separate.

Evidence `/tmp/mb-adoption-20261103` contains an editable adopted `.blend`, static
GLB bundle and planning/replacement/export proof JSON. No new render or visual
quality claim is made. Both bundled skill validators and `git diff --check`
passed. No packages, venvs, installed service or installed skills were changed.

## Interrupted staged export recovery — 2026-11-03

Focused durable files, broker-only MCP, contracts and real native crash tests:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_export_jobs.py tests/test_export_job_mcp.py tests/test_export_job_contracts.py tests/test_export_job_native.py --tb=short --maxfail=1
```

Result: **14 passed in 27.97s**. Real test-owned Blender processes are killed with
SIGKILL after the first static LOD file and after durable export validation. The
live lock blocks recovery while each process runs; after death, partial output
reconciles as interrupted and cleans, while validated staging publishes without
replaying Blender. A separate native cancellation arriving after journal
validation still prevents publication and cleans owned staging. This qualifies
process death at these boundaries, not arbitrary hardware/power-loss behavior.

Pure filesystem checks cover live subprocess writers, actual lock release after
kill, owner isolation, pre-/post-rename reconciliation, ready-output protection,
missing manifests, foreign output preservation, unknown/symlink/replaced-inode
refusal, fresh guards, dry runs, reference protection, cancelled partial cleanup
and bounded owner-only discovery/filtering/pagination. Deletion is anchored to
registered directory descriptors and refuses inventory drift. Broker queue tests
protect structured stage readers and refuse late submissions into cleanup paths.

The MCP fixture uses automatic Blender startup disabled and a disk reserve larger
than available space. Discovery, inspect, reconcile and publication still succeed
without a Blender worker; free-space/progress and unmet reserve are reported.
Published data refuses cleanup. Filesystem metadata jobs need no export-size
admission but still need enough space for small journal writes.

The final discovery-summary, malformed-record and storage-policy checks passed
**11 tests in 26.00s** after the focused run.

Broker/startup/retention/server/storage regression plus file-only checks:

```sh
python3 -m pytest -q tests/test_export_jobs.py tests/test_export_job_mcp.py tests/test_export_job_contracts.py tests/test_operations.py tests/test_broker_startup.py tests/test_retention.py tests/test_server.py tests/test_storage.py --tb=short --maxfail=1
```

Result: **39 passed in 45.89s**, with the existing Starlette/AnyIO deprecation
warning. Earlier existing static/skin/morph/package exports with journaling enabled
passed **17 tests in 118.83s**. After removing native-side frontend contract
imports, native recovery/add-on/lifecycle/package checks passed **9 tests in
78.37s**. The add-on archive is extracted and imported in Blender with Pydantic
and FastMCP imports explicitly blocked. It includes the dependency-free recovery,
validation and shared recipe-default helpers and excludes frontend/server code.
Native recipe defaults are checked against the frontend contract defaults.

Scope: registered top-level LOD/package exports. Nested LOD staging belongs to its
outer package. Broker job recovery works independently of app startup and records
its own result; it does not rewrite the interrupted original operation's status.
Small journals/locks remain, and unknown legacy staging is preserved. Lost/edited
records, ownership-registration gaps, changed inodes, unknown files and untracked
external/Python references cannot be guessed away. Independent LOD validation has
coarse cancellation boundaries; final publication is checked again afterward.
Automated age-based journal pruning/staging sweeps, general single-file export
recovery and other bake/render lifecycle work remain separate. Both bundled
skills validate; see USER_MANUAL.md for operational safeguards and limits.


## LOD ownership, replacement and source visibility — 2026-11-03

Focused native/structured/contract gate:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_LOD_MANAGEMENT_EVIDENCE_DIR=/tmp/mb-lod-management-20261103 python3 -m pytest -q tests/test_lod_management.py tests/test_lod_management_native.py tests/test_lod_management_contracts.py --tb=short --maxfail=1
```

Result: **5 passed in 51.40s**. With Python execution disabled, the static fixture
hides/shows its original source through guarded visibility tools, refuses a stale
management guard, rebuilds 250/120-triangle levels to 200/80 budgets, preserves the
source fingerprint, saves/reopens and removes only the owned chain. Queued rebuild
reports storage. The skin/morph fixture rebuilds both deformation profiles and
removes them while keeping original rig animation and morph source fingerprints.
Evidence includes an editable source/rebuilt scene and proof JSON under the
command's evidence directory. No new render qualification is claimed here.

The native fixture verifies unambiguously owned removal despite edited mesh
contents, outside constraint/instancer refusal, shared mesh retention, fake-user
mesh retention, stale source replacement, root placement/static parent binding,
nested collection parent links, active/selected level mapping and visible fallback
when shortening a chain. Root-authored controls/instancing block replacement. Cancellation
before name handoff and after handoff verification restores exact ID sets, public
names, source guard and selection. Source visibility cancellation restores flags.
A morph-specific handoff cancellation restores all temporary Key/mesh IDs; after
successful replacement/removal the entire pre-generation ID set returns. Legacy
metadata without a generation recipe reconstructs its recorded level recipes.
Explicit placement/visibility reset options are checked separately. The final
expanded native/lifecycle-contract gate passed **3 tests in 10.87s**.

Existing static/skin/morph LOD exports, package delivery, server/storage/capability
and contract regression:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_lods.py tests/test_skin_lod_export.py tests/test_morph_lods.py tests/test_asset_packages.py tests/test_lod_contracts.py tests/test_server.py tests/test_storage.py tests/test_capabilities.py --tb=short --maxfail=1
```

Result: **23 passed in 136.10s**, with the existing Starlette/AnyIO deprecation
warning. Both bundled design/animation skills pass their structural validator.
Qualification remains FreeBSD Blender 5.0.1.

This manages existing marked chains. Arbitrary external-level adoption, authored
root-controller migration, source-controller detachment and automatic distance
switching remain separate. Guards inspect native ID references and membership;
string-name references in scripts/recipes cannot be inferred. Shared/fake-user
meshes and source/material/clip data are retained, not generically purged. Source
visibility flags are global to that object; show it before generation, sampling,
rebuild or package planning. Ordinary cooperative rollback is verified before the
final noninterruptible native deletion, not through a process crash during it.
See USER_MANUAL.md for recipes and guard semantics.


## Batch asset packages — 2026-11-03

Focused contracts, independent decoder, native rollback and structured pipeline:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_PACKAGE_EVIDENCE_DIR=/tmp/mb-package-20261103 python3 -m pytest -q tests/test_package_files.py tests/test_package_contracts.py tests/test_package_native.py tests/test_asset_packages.py --tb=short --maxfail=1
```

Result: **22 passed in 48.80s**.

The structured fixtures use arbitrary Python execution disabled. A two-asset
textured package contains a building primary, associated 28-triangle convex
collider, textured prop primary, 150-triangle shadow proxy and a three-level
static LOD bundle. Independently decoded oriented triangle fingerprints, counts,
node transforms, bounds and embedded image/texture/UV references match native
snapshots. Re-imported building counts/UVs/world bounds match the placed source.
Proxy mappings retain method/shape/quality/source association and per-node proofs.
Tampered member bytes, extra files and a collider associated with another asset
refuse validation/planning. Queued progress reports free space and the refined
geometry/texture estimate. The manifest has no absolute source path fields.

A separate skin fixture packages a static current-pose primary plus a three-level
animated skin bundle. Adding an inactive clip changes the package guard even at
an unchanged current pose; the stale plan refuses export. The nested bundle
contains two independently validated clips per level. A morph fixture packages a
static primary and a three-level timeline-baked morph bundle with the named
Breathe range. All nested bundle/animation/source guards are associated in the
root manifest and revalidated with their existing independent LOD validators.

A staging-name collision refuses creation and preserves the pre-existing
directory and contents. Native cancellation after mesh export and after final package validation restores
the exact native ID set and deletes owned staging. Injected decoder failure also
cleans staging and owned data. Successful export preserves frame/subframe,
selection, active object and source guard; no overwrite is allowed. Additional
checks cover missing unpacked textures and loaded-pixel edits participating in the
guard. The final expanded native gate, including staging collision preservation,
passed **1 test in 4.97s**. Known-answer pure fixtures check hierarchical translation/scale, oriented
surface fingerprints, cycles/multiple parents/unreachable nodes, invalid references,
image/texture/UV dependencies, PNG CRC/scanline layout, unsafe paths, symlinks,
hashes, native proof corruption and undeclared files.

A scene-only context override crashed the installed Blender glTF exporter in an
owned headless probe. Export now temporarily activates the isolated scene through
the actual window and restores the original scene/view layer in finally. Native
rollback/success checks pass with this path. Explicit-object GLB export now uses
the active scene to prevent selections from other scenes entering the export.

Existing server/storage/capability/static LOD/animated skin bundle and textured
asset delivery regression passed **16 tests in 99.56s**, with the existing
Starlette/AnyIO deprecation warning:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_server.py tests/test_storage.py tests/test_capabilities.py tests/test_lods.py tests/test_skin_lod_export.py tests/test_action_integration.py::test_game_asset_inspection_preflight_and_textured_delivery --tb=short --maxfail=1
```

Retained evidence is under the focused command's evidence directory: static
batch (two assets/nine files), animated skin (one asset/six files), morph (one
asset/six files), a source scene and structured proof JSON. System Python validates
all three without importing bpy. The bundled design skill passes its structural
validator. Qualification remains FreeBSD Blender 5.0.1.

This is prepared static primary/proxy delivery plus reused supported LOD animation
profiles. It does not provide general animated assembly export, editable external
library packaging, shader fidelity certification, automatic engine setup or full
glTF conformance. The decoder has explicit dense/native-profile limits; PNG uses
CRC/decompressed scanline validation, JPEG uses structural validation without
entropy decoding. Process-crash staging reconciliation and broader retention,
LOD lifecycle and botanical requirements remain separate. See USER_MANUAL.md.


## Collision/shadow proxies and guarded render visibility — 2026-11-03

Final focused gate:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_PROXY_EVIDENCE_DIR=/tmp/mb-proxy-20261103 python3 -m pytest -q tests/test_proxies.py tests/test_proxies_native.py tests/test_proxy_contracts.py --tb=short --maxfail=1
```

Result: **5 passed in 31.39s** on FreeBSD Blender 5.0.1. The Python-disabled MCP
fixture creates a two-story procedural building, a reusable placed prototype and
its 28-triangle convex collider. A passive native rigid body uses that collider;
a falling cube's center heights are 10.0, 7.2199998 and 7.2199998 at frames
1/24/60, consistent with the 6.2-high roof plus the cube's half-height and collision
margin. The source instance guard remains unchanged. Guarded removal refuses an
attached rigid body; physics detachment is explicit.

The same fixture configures source shadow visibility through typed guarded tools,
refuses a stale visibility guard, and generates a textured 150-triangle shadow
mesh. Its sampled maximum relative surface error is 0.0102831 (fixture evidence,
not a general bound). Existing GLB delivery retains the 150 triangles and one
embedded image; save/reopen retains valid native ownership and geometry. Moving
the source makes source_matches false while leaving the frozen proxy valid, and
the old source guard refuses generation.

Native checks cover padded combined boxes, convex envelopes of separated parts,
per-source grouping, closed manifold positive-volume output, sampled outside
checks, error-threshold refusal, degenerate hull refusal, partial output name
collision, source inspection ID cleanup, and cooperative rollback during generation
and after scene linking. Shadow decimation discards all work objects/meshes;
shared materials survive guarded removal. Referencing a proxy from an external
object blocks deletion. Visibility cancellation restores the original flags and
keyed targeted visibility edits refuse.

An isolated Cycles render scene contains the shadow proxy without its original
sphere. The 128×128 paired shadow-on/off images have **847 darkened pixels** and
an unchanged camera-center patch. Visual inspection confirms the displaced shadow
and no visible sphere. These images, native/structured scenes, a textured GLB and
JSON proofs are retained under the command's evidence directory. This proves the
fixture's Cycles shadow-only behavior, not Eevee, alpha foliage or engine support.

Before adding the visibility-control extension, the combined proxy, realization,
server, storage and capability regression passed **17 tests in 70.02s**, including
the shared evaluated-mesh-copy refactor:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_PROXY_EVIDENCE_DIR=/tmp/mb-proxy-20261103 python3 -m pytest -q tests/test_proxies.py tests/test_proxies_native.py tests/test_proxy_contracts.py tests/test_assembly_realization.py tests/test_assembly_realization_native.py tests/test_capabilities.py tests/test_server.py tests/test_storage.py --tb=short --maxfail=1
```

After the visibility extension, pure contract/server/storage/capability checks
passed **13 tests in 15.03s**, with one opt-in Blender capability check skipped
and the existing Starlette/AnyIO warning:

```sh
python3 -m pytest -q tests/test_proxy_contracts.py tests/test_capabilities.py tests/test_server.py tests/test_storage.py --tb=short --maxfail=1
```

Both bundled design/render skills pass their structural validator.

Scope: static world-space approximations and current-viewport source guards.
Hull/box grouping can close doors and fill disconnected gaps. There is no automatic
convex decomposition, trunk/branch selection, active-body inertia qualification,
engine association or physics attachment. Surface checks are sampled and do not
prove exhaustive containment, silhouette or alpha coverage. Shadow ray flags are
Cycles-specific and do not transfer through GLB; materials remain shared and
external shader/image state is not baked. See USER_MANUAL.md for limits and
source freshness/removal semantics. Broader botany, collision decomposition and
batch dependency packaging remain separate.


## Static assembly realization and mesh delivery — 2026-11-03

Combined structured/native and existing assembly/server/storage/capability gate:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_REALIZATION_EVIDENCE_DIR=/tmp/mb-realization-20261103 python3 -m pytest -q tests/test_assembly_realization.py tests/test_assembly_realization_native.py tests/test_assembly_contracts.py tests/test_assemblies.py tests/test_assembly_native.py tests/test_capabilities.py tests/test_server.py tests/test_storage.py --tb=short --maxfail=1
```

Result: **19 passed in 81.48s**, with the existing Starlette/AnyIO deprecation
warning. With arbitrary Python disabled, a textured procedural building prototype
is placed twice and realized into independent static mesh objects. Source guards,
leaf paging, queued storage feedback, UVs, per-leaf triangle counts, world bounds,
no modifiers, and source instance fingerprint preservation are checked. The
existing GLB exporter produces matching triangle counts, one embedded image and
native-to-glTF position bounds. Native re-import gives two meshes with matching
combined triangle counts and world bounds. Moving a source refuses the old guard;
save/reopen retains the realized mesh bounds. Evidence contains a GLB, editable
scene and proof JSON under the command's evidence directory.

The native fixture checks nested placements, nonuniform mirrored/sheared affine
transforms, exact transformed vertex correspondence, outward polygon normals,
transformed custom corner normals, UV presence, named point attributes, shared
material identity, source selection/active object preservation, frozen shape-key
pose, and ordinary cancellation during creation and after scene publication with
exact native ID-set restoration. The native fixture also checks un-realized
Geometry Nodes instance leaves, their separate transformed bounds, and partial
creation name-collision cleanup. Evaluated mesh copying explicitly removes owned
orphan Key datablocks without changing source shape data. Geometry and controls
remain in the editable
prototype; changing its morph value does not alter the realized meshes.

The workflow snapshots current viewport mesh geometry only. It does not preserve
animation, rig structure or helpers in the realized output. Materials remain
shared and shaders/image pixels/external dependencies are not baked. Arbitrary
named attributes are preserved in native mesh data, not promised in GLB. This
checks static delivery through the existing exporter, not a new validated
multi-asset bundle or animated assembly exporter. Process-crash cleanup, external
library loading, collision/shadow generation and botanical pipelines remain open.


## Reusable native asset assemblies — 2026-11-03

Focused structured/native gate:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_ASSEMBLY_EVIDENCE_DIR=/tmp/mb-assembly-20261103 python3 -m pytest -q tests/test_assembly_contracts.py tests/test_assembly_native.py tests/test_assemblies.py --tb=short --maxfail=1
```

Result: **5 passed in 30.42s** on FreeBSD Blender 5.0.1. With Python execution
disabled, a packed-texture procedural building is copied to an independent native
prototype and placed twice. Editing the copied Geometry Nodes floor input changes
both instances from two to three floors, without changing the source geometry.
A stale prototype guard refuses placement. Managed instance bounds support preview
stage setup and camera framing. A 192×192 Cycles render is decoded and checked for
material color coverage; visual inspection confirms the expected three-story
building, windows, roof and textured walls. Scene save/reopen retains placements
and evaluated bounds. The rig fixture copies a native rig/skin with a managed
property driver, verifies remapped typed-editable targets, and changes the copied
control without changing the source target.

The native fixture covers parent, constraint, Key driver and material object
reference remapping, independent data/materials, active/inactive managed clips,
nested prototype reuse without leaked copied nested data, linked placements,
source frame/selection/active state and fingerprints, and referenced-placement
removal refusal. Ordinary cancellation after append restores the exact native ID
set and source fingerprint. A subsequent regression also checks cancellation after
final prototype verification. Evidence includes editable native scenes, a render
and structured proof JSON under the command's evidence directory.

Existing camera/preview, Geometry Nodes, storage, server and capability regression,
including the expanded native assembly cancellation fixture:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_assembly_native.py tests/test_capabilities.py tests/test_storage.py tests/test_server.py tests/test_action_integration.py::test_preview_setup_fits_offset_assets_and_refuses_collisions tests/test_geometry.py --tb=short --maxfail=1
```

Result: **16 passed in 71.57s**, with the existing Starlette/AnyIO deprecation
warning. Both bundled design/animation skills pass their structural validator.

These are scoped current-scene tests. External library linking, independent
instance animation/simulation, membership migration, realized assembly export,
collision proxies and botanical assets are not qualified. Guards do not freeze
image pixel buffers or external files. Native write/append is synchronous and
cannot be interrupted mid-call; process-crash cleanup is not established here.
See USER_MANUAL.md for graph limits and ownership rules.


## Timeline-baked morph LOD bundles — 2026-11-02

Final focused gate:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_MORPH_LOD_EVIDENCE_DIR=/tmp/mb-morph-bundle-structured-20261102 MCPBLENDER_MORPH_BUNDLE_EVIDENCE_DIR=/tmp/mb-morph-bundle-20261102 python3 -m pytest -q tests/test_morph_lods.py tests/test_morph_bundle_native.py tests/test_lod_contracts.py tests/test_morph_glb.py tests/test_skin_glb.py --tb=short --maxfail=1
```

Result: **29 passed in 64.73s**. The structured fixture uses arbitrary Python
execution disabled, creates a textured 540-triangle prop and transfers morphs to
250/120-triangle LODs. Two explicitly named current-timeline ranges export with
embedded textures and independently checked manifests. Queued export reports
current storage. Native re-imported far-LOD playback at frames 0/4/8 matches the
original far level at frames 1/5/9 within 0.001. Editable save/reopen and subsequent
source clip changes remain covered. The worst sampled decoded vertex error in
this textured fixture is 2.39e-7.

The native fixture covers morph-only and combined skeletal/morph spheres, reduced
720→400 triangles. A masked key relative to another non-Basis key is flattened
only on export copies. Active source NLA, an external-property driver, a rig
constraint, root motion, unused nondeforming bone masks and negative-start ranges
bake into independent files. Every integer-frame proxy vertex/joint comparison
passes; decoded samples, all rest vertices/target offsets, default weights, skin
weights and inverse binds agree with native data. Worst decoded vertex errors are
4.92e-7 (morph-only) and 9.69e-7 (combined); worst all-frame native proxy error is
7.16e-7. These are fixture measurements, not general fidelity bounds.

Cancellation during timeline baking and after decoded proof removes staging and
all proxy object/mesh/armature/Key/action IDs. An injected decoder position error
refuses publication; retry succeeds. Exact ID counts, source controller/NLA/driver
state, selection, active object, chain guard and fractional frame restore. Both
modes also produce validated bind-only bundles at the fractional reference frame.
Corrupt FPS, missing target proofs and nonfinite recorded bounds refuse readback.
Contracts reject duplicate clip names, fractional endpoints and oversized ranges.

Existing LOD/static/skin/bundle/inspection/server/capability regression:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_lods.py tests/test_lod_native.py tests/test_skin_lods.py tests/test_skin_lod_native.py tests/test_skin_lod_export.py tests/test_skin_bundle_native.py tests/test_morph_lod_native.py tests/test_glb_deformation.py tests/test_server.py tests/test_capabilities.py --tb=short --maxfail=1
```

Result: **21 passed in 128.68s**, with the existing Starlette/AnyIO deprecation
warning. A final native edge-case rerun passed in **9.54s** after separating
object/bone quaternion continuity bookkeeping and explicitly rejecting every
nonfinite matrix component. It uses a bone named `object`, restores a hidden/
unselectable rig, rejects a stale controller guard before output and rejects a
nonfinite pose on an unused bone without retaining proxy data or a bundle. Standalone system Python validates all three retained bundles
without importing `bpy`.

Evidence: `/tmp/mb-morph-bundle-20261102/{MorphOnlyBundle/,SkinMorphBundle/}` and
`/tmp/mb-morph-bundle-structured-20261102/{morph-lods.blend,morph-bundle/,morph-proof.json}`.
Both bundled design/animation skills pass validation. No new render, system
installation, package/venv change, installed-skill update, service or user GUI
change is claimed.

This qualifies explicit current-timeline baking, including solved controls, not
automatic selection of all inactive authored actions or serialization of a general
controller graph. Source graphs stay intact in the editable project; exported
files contain integer-frame linear baked animation. Every native proxy frame is
checked, but decoded file comparison is sampled (3–9 frames per clip), with no
exhaustive subframe/appearance/engine guarantee. Skin mesh-to-rig layout must be
constant; unrepresentable object/bone basis shear refuses. Limits are ten million
vertex-frame samples, 32768 bone-frame samples and two million weight keys per
level, plus existing geometry/morph/file bounds. Staging crash reconciliation,
retention integration and broader LOD management remain separate.

## Independent morph/skin GLB replay and inspection — 2026-11-02

Final focused gate:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_MORPH_GLB_EVIDENCE_DIR=/tmp/mb-morph-glb-20261102 python3 -m pytest -q tests/test_skin_glb.py tests/test_morph_glb.py tests/test_morph_glb_native.py tests/test_glb_deformation.py tests/test_lod_contracts.py --tb=short --maxfail=1
```

Result: **28 passed in 42.33s**. Known-answer tests cover default mesh/node
weights, LINEAR/STEP/CUBICSPLINE scalar weight grouping, matrix-node morph channels
and rotation of morph offsets before skinning. Sparse targets work with zero bases
and dense overlays, including 16/32-bit indices and truncated-value refusal; duplicate/unsorted/out-of-range indices refuse. Incorrect
counts/names, nonfinite data, changed target fingerprints, unsupported instancing,
unknown clips, cancellation and changed-file readback are checked.

System Blender 5.0.1 exports both a morph-only sphere and a combined skeletal/morph
sphere, each with two shape targets (including a localized sparse target) and an animated clip. Every exported split
vertex is mapped to native Basis data; decoded world positions at five frames
match native evaluated positions within 3.39e-7 in both fixtures. The combined
fixture includes bone rotation and shared rig/Key action slots. These are real
native exports and comparisons, not only synthetic GLB tests.

The structured fixture runs with arbitrary Python disabled. It creates a
roof-lift morph, exports the GLB and inspects localized sparse morph data through
the queued `inspect_glb_deformation` tool. It checks changing sampled bounds,
current-storage progress, unchanged scene/frame/selection/animation and refusal
of malformed files. Contracts test read-only discovery, path confinement, file
extension and paging/sample limits. The input is registered with active retention
protection. No import or authored-scene mutation is needed for inspection.

Existing LOD/static/skin/morph/bundle/server/capability regression:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_lods.py tests/test_lod_native.py tests/test_skin_lods.py tests/test_skin_lod_native.py tests/test_skin_lod_export.py tests/test_skin_bundle_native.py tests/test_morph_lods.py tests/test_morph_lod_native.py tests/test_server.py tests/test_capabilities.py --tb=short --maxfail=1
```

Result: **21 passed in 242.99s**, with the existing Starlette/AnyIO deprecation
warning. Both bundled design and animation skills pass the skill validator.

Evidence: `/tmp/mb-morph-glb-20261102/{MorphOnly.glb,MorphOnly.json,SkinMorph.glb,SkinMorph.json}`.
No new rendered appearance or engine behavior qualification is claimed. Native
comparison covers the fixture exports, not arbitrary imported assets. Ordinary
inspection reports sampled file playback and does not establish authored-model
correspondence, every-frame geometry, shading or a general glTF conformance result.
The profile requires one embedded-buffer mesh, optional linear skin, float morphs,
up to 63 targets and bounded curves/vertices. Compression, normalized/quantized
attributes, GPU instances, multiple meshes and general extension handling remain
outside this reader. Morph LOD bundle publication/controller-graph baking remains
open. No package, virtual environment, installed runtime/skill, service or user GUI
changes were made.

## Relative morph LOD transfer — 2026-11-02

The structured MCP fixture runs with arbitrary Python disabled. It creates a
540-triangle dense prop with Widen/Lift keys and a managed clip, then generates
250/120-triangle levels. Each level retains three keys, passes every isolated-key
surface gate and combined timeline samples, and keeps the original morph action
unchanged. Fractional resampling, save/reopen and source clip edits are checked;
clip edits retain usable geometry and flag prior pose measurements as stale.

The native fixture provides a known-answer masked triangle projection, including
preservation of the target rest vertex's normal offset. A dense sphere tests a
key relative to another non-Basis key and baked mask deltas. Generated weights
follow the original action, external-control driver, mute flag and active NLA
strip. A combined linear-rig/morph chain also passes sampled deformation and
save/reopen. Corrupted output coordinates and source key definitions invalidate
ownership. Cancellation during transfer, isolated-key validation and timeline
sampling must restore exact object/mesh/Key/action/collection counts, source
animation and the original fractional frame. Inspection leaves no temporary Key
copies or extra action users.

Preceding LOD/static/skin/bundle/capability gate:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_morph_lods.py tests/test_morph_lod_native.py tests/test_lod_contracts.py tests/test_lods.py tests/test_lod_native.py tests/test_skin_lods.py tests/test_skin_lod_native.py tests/test_skin_lod_export.py tests/test_skin_bundle_native.py tests/test_capabilities.py --tb=short --maxfail=1
```

Result: **16 passed in 113.56s**. Final focused morph/legacy shape-key gate:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_MORPH_LOD_EVIDENCE_DIR=/tmp/mb-morph-lod-20261102 python3 -m pytest -q tests/test_morph_lods.py tests/test_morph_lod_native.py tests/test_lod_contracts.py tests/test_shape_keys.py tests/test_morph_contracts.py --tb=short --maxfail=1
```

Result: **14 passed in 79.72s**. The structured prop's worst sampled timeline
relative error is 2.78e-7; its worst isolated-key error is 2.95e-7. These results
apply to this tube-like fixture and do not establish a general reduction bound.
Both bundled design/animation skills validate.
Evidence is retained under `/tmp/mb-morph-lod-20261102/`: editable morph-only and
combined skin/morph projects, plus structured chain/sampling records. No new
render or target-engine appearance qualification is claimed. No packages, virtual
environments, installed runtime/skills, service configuration or user GUI changed.

This is source-controlled relative-key transfer. The source Key datablock remains
an explicit animation dependency; complete independent clip/driver graph copies
are not created. Masks are baked before interpolation. Bounds and surface checks
are sampled, not exhaustive deformation/shading proof. Limits are 64 keys and
four million source key-vertex entries, with the existing rest/pose work bounds.
Absolute keys, unsupported modifier stacks, detached animation delivery and
validated morph GLB bundles remain separate. Planner/export explicitly refuses
morph-bearing bundles before writing files; use editable Blender delivery now.

## Validated animated skeletal LOD bundles — 2026-11-02

Final focused gate on system Blender 5.0.1:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_SKIN_BUNDLE_EVIDENCE_DIR=/tmp/mb-skin-bundle-20261102 python3 -m pytest -q tests/test_skin_glb.py tests/test_skin_lod_export.py tests/test_skin_bundle_native.py tests/test_lod_contracts.py tests/test_skin_lods.py::test_control_driven_timeline_and_raw_binding_preserved --tb=short --maxfail=1
```

Result: **11 passed in 38.08s**. Six independent stdlib decoder tests include
known-answer LINEAR/SLERP and CUBICSPLINE interpolation, malformed weights/joints/
times/inverse binds and replay-proof mismatch refusal. The structured MCP fixture
runs with arbitrary Python disabled. It generates textured 540/250/120-triangle
skeletal levels and exports Bend, Idle and negative-start clips despite a shorter
scene playback range. All clips retain their full ranges as zero-based seconds;
manifest frame starts/FPS preserve the mapping. Bind-only export also succeeds.

Every weight and inverse bind is checked against native source data. Decoded
joint matrices and corresponding representative vertices match native samples
within 0.001, including per-joint extrema. Re-imported far-LOD Bend playback is
activated through structured NLA tools and matches native world bounds at three
poses. Stale animation guards refuse output. The planner reports eligibility,
compatible clips, reference frame and the full animation fingerprint.

A separate native fixture preserves nondeforming bone-named mask groups, hidden/
unselectable rig state, a fractional reference frame, action metadata and exact
source/chain guards. Cancellation after a successful native comparison and an
injected decoded-joint mismatch both remove staging output and restore ID counts.
Retry succeeds without leaked proxy objects/meshes; fractional clip endpoints
refuse before staging. A controlled rig refuses animated export and succeeds with
`animations=false`. Source rig/clip bindings remain unchanged.

Evidence: `/tmp/mb-skin-bundle-20261102/{animated-lods.blend,animated-bundle/}`.
The existing LOD/native-skin/server/capability regression gate also passed:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_lod_contracts.py tests/test_lods.py tests/test_lod_native.py tests/test_skin_lods.py tests/test_skin_lod_native.py tests/test_server.py tests/test_capabilities.py --tb=short --maxfail=1
```

Result: **19 passed in 84.30s**, with the existing Starlette/AnyIO deprecation
warning. Both bundled design and animation skills pass the skill validator. No new render
is claimed. No packages, virtual environments, installed runtime/skills, service
configuration or user GUI were changed.

This qualifies one dense native GLB profile, not arbitrary glTF. Replay proofs
cover sampled frames/vertices, not exhaustive deformation, visual appearance or
engine behavior. Native tiny-weight filtering is tolerated to 0.0004 and reported;
vertex/matrix tolerances still gate publication. Animated export currently needs
local non-overridden simple rigs/actions, integer endpoints, at most 32 clips and
10,000-frame spans. Bind-only output can retain live controls. Morph transfer,
linked-data copying, crash-time staging reconciliation and retention remain open.

## Linear skeletal LODs and sampled pose validation — 2026-11-02

FreeBSD Blender 5.0.1/system Python, isolated source-checkout instances and MCP
arbitrary Python disabled. Final focused/static regression:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_SKIN_LOD_EVIDENCE_DIR=/tmp/mb-skin-lod-20261102 python3 -m pytest -q tests/test_lod_contracts.py tests/test_skin_lods.py tests/test_skin_lod_native.py tests/test_lods.py tests/test_lod_native.py --tb=short --maxfail=1
```

**10 passed in 69.78 seconds.** `deformation="SKINNED"` inspects raw rest data
and linear bindings, then generates independent LOD meshes following the existing
rig/clips. The dense two-bone tube reduces 540 → 250 → 120 triangles with normalized
native-interpolated weights. An unprotected reduction fails the posed-error gate;
the temporary mixed/gradient-weight joint protection passes, with maximum sampled
relative errors about 0.02730/0.02754 for the two reduced levels at the bent pose.
LOD0/source self-comparison stays below 1e-6. Surface sampling now uses triangle
centers: polygon centers can lie off bent nonplanar quads and give a false positive
error even when comparing identical meshes. Older static measurements above
retain their original vertex/face-center scope.

Live checks cover source weight/action invariance, automatic parent/bind following,
frame/visibility restoration, additional fractional pose frames, guard failures,
modified derived weight detection, save/reopen and raw region/UV/normal checks.
Rig-object root motion follows into the reduced mesh. Explicit existing GLB
mesh-plus-rig delivery contains one skin/two joints, joint/weight attributes and
animation; re-imported playback bounds match the native far LOD at frames 1/5/9
within 0.001 world units. A pose-space COPY_ROTATION control fixture produces at
least three distinct source shapes, passes five-pose LOD validation and retains
its original geometry samples afterward. No new render is claimed here.

A native probe verifies nondeform pin-mask retention, removal of temporary joint
protection groups, preserve-volume refusal, cancellation during generation pose
verification with exact object/mesh/collection counts and source guard restoration,
and cancellation while sampling a published chain with unchanged content/visibility
fingerprint and restored fractional frame. Rig rest changes invalidate ownership.
Static bundle export explicitly refuses a skin chain; it does not silently discard
the skin. New frame/influence/profile contracts and read-policy visibility pass.

Preceding existing LOD/capability/skeletal/weight regression:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_lod_contracts.py tests/test_lods.py tests/test_lod_native.py tests/test_capabilities.py tests/test_skeletal_animation.py tests/test_skin_contracts.py tests/test_skin_weights.py tests/test_skin_native.py --tb=short --maxfail=1
```

**19 passed in 182.07 seconds**, followed by the final ten-test run after the
triangle-center correction and control fixture were finalized. Bundled animation
and design skill validation, compile checks and staged whitespace/privacy checks
passed. Evidence: `/tmp/mb-skin-lod-20261102/{skin-lods.blend,skin-lod.glb,pose-comparison.json}`.

This covers one enabled linear group-only Armature modifier, up to four influences
and 256 single-segment bones. Additional mesh modifiers, envelopes (including bone
multiplication), DQ/preserve-volume, masks, morph transfer, skeleton reduction and
all imported rig/scale/strategy combinations remain unqualified/unsupported as
specified in USER_MANUAL.md. Skin COLLAPSE is qualified; PLANAR/UNSUBDIVIDE retain
static qualifications and still require their skin pose checks. External control
values/dependencies are not frozen by source/rig signatures. Pose samples are not
an exhaustive animation or silhouette guarantee. Dedicated validated animated
skin bundles, interrupted staging reconciliation and broader asset assembly remain
open. No package/venv/installed-runtime/service/skill or normal GUI changes.


## Static LOD chains and independently checked delivery — 2026-11-02

Installed FreeBSD Blender 5.0.1 and system Python, isolated source-checkout
background fixtures, MCP arbitrary Python disabled. Final focused qualification:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_LOD_EVIDENCE_DIR=/tmp/mb-lod-20261102 python3 -m pytest -q tests/test_lod_contracts.py tests/test_lods.py tests/test_lod_native.py --tb=short --maxfail=1
```

**6 passed in 45.26 seconds.** Live tests cover source-preserving evaluated static
snapshots, typed decreasing budgets, native collapse/planar/unsubdivide reductions,
UV/material/render-map retention, normal transfer, sampled error limits,
source/chain staleness, guarded level selection and save/reopen. Reload guards use
stored basis/parent-inverse transforms: hidden objects' derived matrix caches can
remain unevaluated after reload. Arbitrarily modified managed geometry is refused.
A two-floor procedural building retains three used material regions and its packed
PBR texture through snapshot/reduction and two-level GLB delivery.

The textured sphere fixture reduces 960 → 498 → 150 triangles against budgets
960/500/150. Its measured maximum sampled relative surface errors are approximately
0/0.003036/0.010481. These are deterministic local-space bidirectional vertex/face-
center samples, not exhaustive or projected silhouette bounds. Every GLB is
independently decoded for positions, unit normals, UVs, triangle counts/budgets,
indices, embedded image/buffer dependencies and +Y-up local surface bounds.
Hashes and a manifest are re-read before publication and by the validation tool;
corrupted members refuse validation. Re-import confirms far-LOD counts, UVs and
world placement. The 192×192 Cycles far-LOD image is decoded for blue texture
coverage and was opened/visually inspected. The source and exported mesh are
staged away from the derived root to avoid overlap. Evidence:
`/tmp/mb-lod-20261102/{lods.blend,lod_far.png,lod-bundle/}`.

A separate native probe verifies object-linked material overrides, two material
regions, exact object/mesh/collection counts after cancellation following generated
LOD1, error-threshold refusal cleanup and source fingerprint preservation. Export
cancellation after the first decoded GLB removes the owned staging directory,
leaves no published bundle, and restores representation visibility/content guards;
retry succeeds. MCP export progress includes storage information. These probes
establish cooperative cleanup, not process-crash recovery or interrupted staging
reconciliation. Native kernel/export calls remain noninterruptible.

Existing asset/geometry/shader/server/storage/capability regression:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_capabilities.py tests/test_server.py tests/test_asset_editing.py tests/test_geometry_presets.py tests/test_shaders.py tests/test_storage.py --tb=short --maxfail=1
```

**19 passed in 200.12 seconds**, with the existing Starlette/AnyIO deprecation
warning. Final focused checks followed the last position-bound/region checks.
Bundled design skill validation and whitespace/privacy checks passed. No package,
venv, installed runtime/service/skill or normal GUI changes.

This milestone is static LOD support. It does not qualify skinned/morph LOD
transfer, every procedural attribute type, all coordinate scales/transforms,
maximum workload, exact material/shader appearance or texture seam fidelity,
automatic distance switching, botanical crown/leaf reconstruction, wind semantics,
impostors, collision/shadow proxies, engine integration or crash-time cleanup.
Shared materials remain editable, rather than frozen by mesh guards. Source
staleness is informational for independently generated snapshots. The full asset
assembly/delivery and botanical workflow requirements remain open.


## Existing skeleton/rest-hierarchy refinement — 2026-11-02

FreeBSD Blender 5.0.1 and system Python, isolated source-checkout background
fixtures; MCP arbitrary code execution disabled. Final focused qualification:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_rest_contracts.py tests/test_rest_edit.py tests/test_rest_native.py --tb=short --maxfail=1
```

**5 passed in 54.88 seconds.** Typed tests cover guarded existing head/tail/roll
patches, connected-head following with stationary child tails, additions,
reparenting/unparenting, scale/rotation/local-location inheritance, pagination,
stale/cycle/connected-head/zero-length refusal, native float-collapse/overflow
preflight, wrapped rolls, UTF-8 new-name bounds and read-only tool visibility.
Real Blender checks preserve object selection/frame, original data ID for normal
edits, and shared peer rest geometry/data when explicit isolation is requested.
Bound/animated rigs refuse without the explicit deformation-change flag. A posed
skinned limb retains its original action-channel fingerprint and weights; moving
the Tip joint from height 1 to 1.5 changes a 90-degree pose vertex from
`[9.8, -1, 0.8]` to `[9.8, -0.5, 1.3]` as analytically expected, with unchanged
rest geometry and persistence through save/reopen.

A native probe uses oblique rolled bones, nonidentity pose channels, a pose
driver/constraint, custom bone properties, bone selection and a bone-parented
attachment. Deterministic cooperative cancellation after rest writes restores
the original rest fingerprint, removes the new bone, and retains original
armature/driver/constraint identities and attachment targets. A cancelled shared
copy restores its original pointer and armature count; successful isolation
retains pose metadata/references. Armature-data animation remains inspectable but
refuses editing. Blender 5 pose-bone selection and legacy bone selection are
handled by available properties; only the installed Blender 5 host is qualified.

Combined regression during implementation:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_rest_contracts.py tests/test_rest_edit.py tests/test_rest_native.py tests/test_skin_contracts.py tests/test_skin_weights.py tests/test_skin_native.py tests/test_capabilities.py tests/test_constraint_contracts.py tests/test_constraints.py tests/test_retarget_contracts.py --tb=short --maxfail=1
```

**24 passed in 139.26 seconds**, followed by the final five-test run above after
native-precision/name handling was finalized. Bundled animation skill validation
and staged whitespace/privacy checks passed. No new render/export comparison,
maximum-scale performance, arbitrary imported control rigs, all constraint types,
all inheritance enum variants, animation rebasing, pose-to-rest conversion,
rename/removal or crash-time rollback is qualified here. Native verification is
of rest fields/matrices, not preservation of intended animated motion. Existing
animation/skin values intentionally stay unchanged; evaluated motion may change.
No installed runtime/skill/service, packages, environments or normal GUI changes.


## Guarded skin-weight refinement — 2026-11-02

System Python 3.11 and installed FreeBSD Blender 5.0.1, source checkout,
isolated background instances; no packages, environments or installed runtime
changes. Focused qualification:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_skin_contracts.py tests/test_skin_weights.py tests/test_skin_native.py --tb=short --maxfail=1
```

**7 passed in 75.65 seconds.** MCP fixtures disable arbitrary Python execution.
They exercise missing/unnormalized weights, nearest-rest-segment fallback,
strongest-influence pruning, stale guards, failed-plan atomicity, frozen-input
edge smoothing, actual changed posed deformation, bilateral mirror and SWAP,
shared mesh refusal/isolation and unchanged peer fingerprint/deformation,
binding settings and invalid-mask refusal, conflicting/missing geometric
matches, and edited weight persistence through save/reopen. A 10,000-vertex,
32-bone asynchronous edit is cancelled after membership writes have started;
progress contains storage, rollback restores the exact initial fingerprint,
scene frame/active selection and subsequent editability.

A separate native Blender probe constructs UI-locked deform groups, a nondeform
pin mask and a driven shape key. It checks locked normalization budgets, absent
locked memberships through smoothing, unchanged mask values, unchanged mesh/Key/
driver identity for ordinary edits, explicit lock override retaining UI flags,
and deterministic cancellation after 128 writes with newly created group cleanup.
Shared-copy cancellation restores the original pointer and mesh/Key counts;
successful isolation retains original peer data and its shape driver. Native
fixture setup is not an MCP arbitrary-code feature.

Existing skeletal/morph/capability/server regression:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_animation_contracts.py tests/test_skeletal_animation.py tests/test_morph_contracts.py tests/test_shape_keys.py tests/test_capabilities.py tests/test_server.py --tb=short --maxfail=1
```

**26 passed in 206.19 seconds**, with the existing Starlette/AnyIO deprecation
warning. Bundled animation skill validation and staged whitespace/privacy checks
passed. No rendering or new post-refinement GLB comparison is claimed here.
Nearest weighting is geometric, not anatomical; good deformation is not implied
by normalization. General arbitrary imported rigs, maximum-scale performance,
all mirror spaces/transforms, invalid native file corruption, other Blender
versions and crash-time atomicity remain unqualified. Existing-bone rest/hierarchy
authoring remains a separate milestone. The full workflow backlog remains open.


## Explicit rest-aware retargeting and root-motion delivery — 2026-11-02

The combined retarget/NLA/driver/controller/constraint/bake/skeletal/morph/
capability/server regression passed **63 tests in 346.57 seconds**, with the
existing Starlette/AnyIO warning:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_RETARGET_EVIDENCE_DIR=/tmp/mb-retarget-20261102 python3 -m pytest -q tests/test_retarget_contracts.py tests/test_retarget.py tests/test_nla_contracts.py tests/test_nla.py tests/test_driver_contracts.py tests/test_animation_drivers.py tests/test_curve_contracts.py tests/test_animation_curves.py tests/test_constraint_contracts.py tests/test_constraints.py tests/test_animation_bake.py tests/test_animation_contracts.py tests/test_skeletal_animation.py tests/test_morph_contracts.py tests/test_shape_keys.py tests/test_capabilities.py tests/test_server.py --tb=short --maxfail=1
```

Final focused contracts/live checks passed **7 tests in 49.02 seconds**, including
the composite NLA/driver/IK source, small object units and native source/target
scene guards:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_RETARGET_EVIDENCE_DIR=/tmp/mb-retarget-20261102 python3 -m pytest -q tests/test_retarget_contracts.py tests/test_retarget.py --tb=short --maxfail=1
```

Two targeted final checks passed: **1 in 13.86 seconds** for copied-morph cleanup,
source-preserving failure/cancellation and ignored singular source-object scale;
**1 in 13.46 seconds** for integer/fractional time remapping, scale modes, unmapped
bones and independent static morph copies. Installed native source confirms that
Mesh ID deletion also deletes its owned shape-key ID; there is no separate
`bpy.data.shape_keys.remove` collection API on this build.

MCP Python execution is disabled. A named source chain drives a differently named
target with segment lengths two and three instead of one and one. Its median
translation ratio is 2.5. Analytic endpoints at three frames combine scaled bone
translation, target segment geometry and source object locomotion. Output skin
deformation changes; original source/target fingerprints and skin digests remain
unchanged after transfer. Save/reopen retains the result. GLB has one mesh, one
skin and the named motion; reimported playback bounds match within .0003,
including object motion. The copied target PBR material renders as a blue bent
limb; decoded pixels verify its presence, and the preview was visually inspected.
The preview is rendered before reimport to avoid coincident comparison geometry.

A second fixture changes target rest direction/roll. ARMATURE_DELTA keeps an
armature-space rotation axis as expected, whereas LOCAL_POSE bends in the target
joint's own axes. An explicit local correction turns the motion into a twist,
retaining its endpoint. A partial mapping into an offset root verifies that root
head displacement does not invent translation when that source joint rotates
about its own rest head. Unmapped target bones follow rest hierarchy. Ignoring
versus copying local stretch yields independently checked target lengths.
Time remapping covers target frames 101..105/source 1..9 and fractional source
1.25,1.75,2.25, with analytic scale/endpoints. Static relative shapes copy
independently and remain editable without changing the original target mesh.

A source action is layered through NLA into a scalar, driving IK influence on a
bent chain. Retargeting samples that evaluated timeline into a different target
at remapped times. Independent matrix multiplication/transposition checks joint-
local rotations at three source/target frame pairs; copied skin has distinct
finite deformation digests. This qualifies evaluated-source transfer, not contact
preservation on different limb proportions.

Stale fingerprints refuse before editing. Unsupported animated source object
scale fails after output creation: new rig/skin/morph/action data is removed and
frame restored. Exact output names can be reused. Explicit IGNORE permits source
object scaling, including a singular reference when local bone poses remain
valid. A real 64-bone/500-frame transfer is cancelled after key insertion begins;
progress includes storage, outputs are removed, frame restored and exact rig/
clip names reusable. Pure contracts cover mapping uniqueness, finite scales,
time bounds, safe output names and read-only plan visibility.

Evidence: `/tmp/mb-retarget-20261102/retarget.blend`, `retarget.glb`,
`retarget.png`, `comparison.json`. Verification is every integer target frame
against defined transfer math plus finite evaluated skin scans; independent
fixtures test the expected semantics. It does not prove automatic anatomical
mapping, foot/contact locking, complete control-rig/morph-clip transfer, winding/
subframe fidelity, arbitrary B-Bones/nonrepresentable shear, large-scene latency
or process-kill rollback. Static extra surface modifiers beyond tested simple
skins are exposed but not each visually qualified. Rig fingerprints are not a
whole-scene/external-control/mesh/material snapshot. Existing simple clip tools
retain their mixed-channel guard; tagged mixed clips export through the managed
exporter, with object transform/mode snapshots restored. No packages/venvs,
installed runtime/skills, user GUI or engine integration changed; isolated
source-checkout background Blender only.


## NLA composition, generated shape base and composite delivery — 2026-11-02

The combined NLA/driver/controller/constraint/bake/skeletal/morph/capability/server
suite passed **57 tests in 317.64 seconds**, with the existing Starlette/AnyIO
warning:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_NLA_EVIDENCE_DIR=/tmp/mb-nla-20261102 python3 -m pytest -q tests/test_nla_contracts.py tests/test_nla.py tests/test_driver_contracts.py tests/test_animation_drivers.py tests/test_curve_contracts.py tests/test_animation_curves.py tests/test_constraint_contracts.py tests/test_constraints.py tests/test_animation_bake.py tests/test_animation_contracts.py tests/test_skeletal_animation.py tests/test_morph_contracts.py tests/test_shape_keys.py tests/test_capabilities.py tests/test_server.py --tb=short --maxfail=1
```

After asynchronous defaults, managed movement around imported neighbors,
single-solo preservation and recipe/native consistency guards, the focused suite
passed **7 tests in 66.15 seconds**:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_NLA_EVIDENCE_DIR=/tmp/mb-nla-20261102 python3 -m pytest -q tests/test_nla_contracts.py tests/test_nla.py --tb=short --maxfail=1
```

The final shape-foundation capacity guard passed its live regression
(**1 test in 14.77 seconds**); final NUL-free name/range/permission contracts
passed **2 tests in 3.31 seconds**.

MCP Python execution is disabled. An object action is reused at a new start,
scaled, repeated, reversed and trimmed into a later strip. Independent native
world-position checks verify timing, REPLACE/ADD/SUBTRACT/MULTIPLY/COMBINE blending,
track order, mute/solo and preservation of a separate solo layer during rebuild.
Overlap and stale guards refuse without changing the fingerprint. Strip/track
removal retains source actions. Save/reopen retains managed ownership/playback.

A weighted two-bone limb combines tip rotation and additive root translation.
Three independently computed endpoints and distinct skin deformations agree.
Visual baking checks every integer-frame bone matrix and skin vertex over nine
frames without changing the source NLA fingerprint. Exported GLB has exactly one
mesh, one skin and the named composite animation. Native reimported skinned mesh
playback bounds match the source composite within .0002 at three frames. An
independent fade fixture checks edge, ramp and middle contributions. Another rig
layers a scalar control action driving a native bone driver; three endpoint/skin
samples and a 17-frame visual bake agree.

Native source inspection showed that unanimated strip influence is recalculated,
so typed strips use a generated linear envelope combining weight/fades. It also
showed the native NLA shape-weight RNA default is one, confirmed by opening the
saved scene directly with native Blender. Shape-base reset now stages an explicit
zero-weight foundation beneath additive/weighted shape layers. A short constant
clip with HOLD extrapolation avoids an excessive source range. Two independent
morphs produce expected evaluated bounds at three frames, with zero contribution
outside the layer ranges. Repeated resets retain one foundation and remove the
previous unchanged unused generated action. Source edits invalidate the stack
hash without losing structural strip ownership; shared shape-data edits refuse.
A native timing-rounding failure during staging preserves the original stack.

A trusted external native-Blender fixture supplies a 256-strip managed layer
plus an imported neighbor. Moving the managed layer after the imported track
preserves the neighbor; moving it before an unsupported prefix is refused. A
real rebuild is cancelled after staging reports progress/storage: staged tracks
are discarded, frame seven and the exact source fingerprint restored. A second
fixture supplies a correct native ownership hash but an inconsistent timing
recipe; inspection and editing refuse it without changing the stack. Metadata
is therefore checked against actual native timing, slot, blending and envelope.

Evidence: `/tmp/mb-nla-20261102/nla-composite.blend`, `nla-composite.glb`,
`comparison.json` and `nla-morph.blend`. Scope is typed local action slots and
managed action strips; transition/meta/sound editing, arbitrary animated control/
time curves, unsupported import repair, multi-object coordinated layer editing,
NLA-specific process-kill recovery, large-scene performance and morph/object-motion
composite baking remain unqualified. Native final replacement is short and not
interruptible; crash handling uses existing checkpoints rather than a filesystem
transaction. No packages/venvs, installed runtime/skills, user GUI session or
engine integration changed; isolated source-checkout background Blender only.


## Typed native drivers and animated scalar controls — 2026-11-02

The combined driver/controller/constraint/visual-bake/skeletal/morph/capability/
server regression passed **50 tests in 287.90 seconds**, with the existing
Starlette/AnyIO deprecation warning:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_DRIVER_EVIDENCE_DIR=/tmp/mb-drivers-20261102 python3 -m pytest -q tests/test_driver_contracts.py tests/test_animation_drivers.py tests/test_curve_contracts.py tests/test_animation_curves.py tests/test_constraint_contracts.py tests/test_constraints.py tests/test_animation_bake.py tests/test_animation_contracts.py tests/test_skeletal_animation.py tests/test_morph_contracts.py tests/test_shape_keys.py tests/test_capabilities.py tests/test_server.py --tb=short --maxfail=1
```

Final driver contracts/live checks passed **7 tests in 41.03 seconds**, including
pose-bone scalar animation and shared shape-data refusal after the last guards:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_DRIVER_EVIDENCE_DIR=/tmp/mb-drivers-20261102 python3 -m pytest -q tests/test_driver_contracts.py tests/test_animation_drivers.py --tb=short --maxfail=1
```

With MCP Python disabled, a scalar on a translated two-bone rig drives tip
rotation using `bend*pi/2`. The scalar is keyed after installing the driver on
the same rig. Native samples at three frames verify independently computed
endpoints and distinct skin deformations. Visual baking checks every bone matrix
and skin vertex over nine frames against an independent constraint-free rig.
Save/reopen preserves the native driver, ownership and configuration fingerprint.
Updating its expression changes the measured reach; stale removal is refused,
and guarded removal succeeds. A pose-bone custom scalar is independently keyed
and drives that bone, with its endpoint checked against sin/cos(.5).

Native transform variables drive object location. WORLD_SPACE minus
TRANSFORM_SPACE/LOCAL_SPACE on a parented helper gives the independently expected
parent translation. Constraint influence controlled by a scalar produces half/
full follow, and changing its input leaves the configuration fingerprint stable.
Cycle refusals cover a rig control reading its driven bone, a parent feedback
loop and influence feedback through its solved owner. Pure property/evaluated
node controls verify safe same-rig raw inputs and unrelated blocked components.

A relative shape-key driver changes actual mesh bounds as its scalar changes;
a shape-weight input also drives another object's scale. Shared mesh data is
reported as an edit blocker and refused for shape-driver changes. Division by
zero and sqrt(-1) fail native evaluation: the prior driver or a new target's
nonzero original property value is restored, with the fingerprint unchanged.
Blender's native driver creation adds identity mapping points on this build;
typed creation removes them and uses direct expression output. Installed native
source confirms the no-points identity evaluation and 255-byte expression limit.

A trusted external native-Blender fixture supplies ownership metadata with a
correct native hash but a false source declaration. MCP inspection exposes the
real variables and marks it inspect-only; direct replacement and a consumer
through its evaluated transform are refused without changing the fingerprint.
An unrelated scalar input remains usable. Native metadata is therefore matched
against real paths/variables rather than accepted as the dependency authority.
Contracts reject arbitrary calls/attributes/indexing/strings/comprehensions,
unknown/reserved variables, oversized formulas/constants, reserved control names
and invalid bounds. Read-only discovery exposes inspection and hides edits.

Evidence: `/tmp/mb-drivers-20261102/drivers.blend` contains the editable keyed rig,
native driver, source skin and independently verified baked skeleton/skin/clip.
Qualification is bounded to the typed object/pose/scalar/influence/relative-shape
surface and tested Blender 5.0.1. It does not establish arbitrary RNA/material-
node drivers, every native variable type/space/rotation combination, future-input
validity, unsupported-driver repair, large-scene latency or morph/object-motion
baking. Constraint configuration retains its earlier conservative driver guard;
create constraints before drivers. Core NLA authoring was subsequently qualified above; core retargeting was subsequently qualified above; contact-aware transfer and advanced strip controls remain open.
No package, venv, installed runtime/skill, user GUI or engine integration changed;
verification used isolated source-checkout background Blender instances.


## Controller channels and F-curve refinement — 2026-11-02

The expanded new/legacy controller, constraint, visual-bake, skeletal animation,
contract, capability and server suite passed **33 tests in 228.62 seconds**, with
the existing Starlette/AnyIO deprecation warning:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_CURVE_EVIDENCE_DIR=/tmp/mb-curves-20261102 python3 -m pytest -q tests/test_curve_contracts.py tests/test_animation_curves.py tests/test_constraint_contracts.py tests/test_constraints.py tests/test_animation_bake.py tests/test_animation_contracts.py tests/test_skeletal_animation.py tests/test_capabilities.py tests/test_server.py --tb=short --maxfail=1
```

After final strict/native-float guards and whole-action size checks, the focused
contracts/live suite passed **5 tests in 37.27 seconds**:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_CURVE_EVIDENCE_DIR=/tmp/mb-curves-20261102 python3 -m pytest -q tests/test_curve_contracts.py tests/test_animation_curves.py --tb=short --maxfail=1
```

MCP Python execution is disabled. A same-rig nondeforming control bone is keyed
**after** two-bone IK setup; native endpoint samples reach three independently
specified world goals within .015. Named constraint influence is then keyed from
zero to one: the first endpoint returns to FK rest, the last reaches its goal.
The new action retains the control tracks. Stale hashes are refused. Save/reopen
retains the active named variant, source clip and paged key data. Evidence:
`/tmp/mb-curves-20261102/controller-curves.blend`.

A second object shares the original action. Successive independent variants
change outgoing Bézier interpolation, a manual FREE handle and QUAD/EASE_IN
playback. Native evaluated translation verifies the shaped motion. Retiming and
value transforms produce the expected key/handle coordinates and intermediate
playback. Collision refusal preserves the current fingerprint. An out-of-bounds
numeric edit fails after a working action is copied/bound; rollback restores the
source binding and frame, and the exact output name can immediately be reused.
Deleting two keys retains the requested remaining point and unrelated channels.
The peer's original action fingerprint and linear playback remain unchanged.

A trusted external native-Blender CLI prepares imported fixtures; MCP opens them
with Python execution off. Drivers, active NLA, locked groups, noise/envelope
modifiers and sampled curves remain inspectable and refuse unsupported edits,
preserving their fingerprints. Inspection reports envelope points and samples.
An arbitrary nontransform property path is refused. WXYZ quaternion and Euler-
degree insertion produce independently checked world rotations. Near-identical
high-frame times that collapse to one native float are refused. Contracts cover
value dimensions, finite/strict frames, quaternion norms, required influence
owner, selected-key uniqueness, operation types and read-only tool visibility.

Scope: active-slot copy-on-edit for local Object-mode data, with at most one
layer/strip and bounded keys/slots. Other objects and morph-slot owners are not
rebound; grouped multi-object editing is not qualified. Source clips are retained
as persistent variants, not deleted temporary files. Inspection hashes are action/
binding guards, not whole-scene guards. Raw curve edits do not certify normalized
quaternions, evaluated constraint reach, subframe accuracy, arbitrary imported
rig compatibility or coordinated morph delivery. Driver authoring was a separate milestone; see its qualification above.
NLA authoring was subsequently qualified above; advanced strip controls and contact-aware/control-rig transfer remain separate work. No package/venv, installed service/skill, user
GUI session or engine integration was changed; isolated background Blender only.


## Independent visual skeletal baking — 2026-11-02

The focused contracts and real-Blender suite passed **8 tests in 31.75 seconds**:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_BAKE_EVIDENCE_DIR=/tmp/mb-visual-bake-20261102 python3 -m pytest -q tests/test_constraint_contracts.py tests/test_animation_bake.py --tb=short --maxfail=1
```

With MCP Python disabled, a translated two-bone rig and weighted skin are driven
by an animated Empty through a copy-rotation constraint. Visual baking creates a
separate constraint-free rig, independent mesh and managed quaternion clip.
Native verification evaluates every integer frame and compares every bone's full
world matrix and every copied vertex's world position, failing above .0001.
Independent MCP samples at five key/intermediate frames verify endpoints/bounds;
the original constraint fingerprint, selection and current frame stay unchanged.
Save/reopen and GLB export/reimport retain the single named clip and skin; imported
playback bounds agree with the editable source within .0002 at all five samples.
Resampling the source after export produces its original mesh deformation digests.
A separate preferred-bend two-bone IK fixture reproduces the evaluated chain.

A moving rig-object fixture is refused during sampling; newly created objects,
armature/mesh data and action are removed and the frame restored. Reusing the
output names and clip succeeds on a valid single-frame range. A 64-bone,
500-frame operation is cancelled after keying has started: it ends cancelled,
restores frame seven, removes outputs and permits immediate reuse of the exact
rig/clip names. Pure contracts check ranges, unique sources/output names, strict
integer frames, finite tolerance and read-only tool visibility.

The combined new/legacy constraints, skeletal animation, contracts, capability and
server regression passed **28 tests in 132.39 seconds**, with the existing
Starlette/AnyIO deprecation warning:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_BAKE_EVIDENCE_DIR=/tmp/mb-visual-bake-20261102 python3 -m pytest -q tests/test_constraint_contracts.py tests/test_animation_bake.py tests/test_constraints.py tests/test_animation_contracts.py tests/test_skeletal_animation.py tests/test_capabilities.py tests/test_server.py --tb=short --maxfail=1
```

Editable source plus baked output, portable GLB and sampled JSON evidence:
`/tmp/mb-visual-bake-20261102/`. This qualification covers stationary rig/mesh
object transforms and single-segment bones with simple vertex-group skins;
animated object transforms, shape keys, extra mesh modifiers and bone envelopes
are refused. It does not establish arbitrary imported-rig compatibility, subframe
accuracy, normal equivalence, retargeting, large-scene performance or crash-time
in-process cleanup. Existing checkpoint/recovery remains the crash boundary.
No packages, virtual environments, installed runtimes/skills or engine adapters
were changed; tests used isolated source-checkout background Blender instances.


## Typed constraints, IK and current-timeline sampling — 2026-11-02

The combined new/legacy animation, capability and server suite passed **23 tests
in 134.24 seconds**, with the existing Starlette/AnyIO warning:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_CONSTRAINT_EVIDENCE_DIR=/tmp/mb-constraints-20261102 python3 -m pytest -q tests/test_constraint_contracts.py tests/test_constraints.py tests/test_animation_contracts.py tests/test_skeletal_animation.py tests/test_capabilities.py tests/test_server.py --tb=short --maxfail=1
```

Real Blender 5.0.1, with MCP Python execution disabled, binds a slightly bent
two-bone limb and creates animated Empty goals/poles and a two-bone IK constraint.
The helper safely parents to the rig object's transform. At three keys and two
intermediate frames the tip reaches its interpolated goal within .015 world
units, with five distinct finite mesh deformation digests. Reversing the pole
changes the elbow position while retaining the goal; influence zero restores the
FK rest endpoint. Sampling restores the frame and does not switch the action.
Save/reopen retains the controls and reach. Its Cycles preview was opened and
inspected; an independent decoded-PNG control requires over 300 blue-dominant
pixels. Editable `.blend`, PNG and sampled JSON: `/tmp/mb-constraints-20261102/`.

A separate animated nondeforming control bone in the same rig drives IK while its
ordinary managed clip stays active. The original perfectly collinear fixture
stalled in the native solver; a direct native probe confirmed accurate reach with
a preferred rest bend. Inspection now reports endpoint distance and the
collinear-rest warning; a native straight-chain fixture verifies that diagnostic.
This is not a promise that arbitrary pole angles or unreachable targets solve.

Object fixtures verify actual copy location/rotation/transforms, location/rotation/
scale bounds and damped-track direction. Reordering changes the result as
expected. Stale hashes, type changes and dependency cycles are refused without
changing the stack. A reverse dependency from the helper to an IK ancestor is
also refused. Pure graph controls cover same-rig independent bone targets,
ancestor effects, unrelated unsupported dependencies, diamonds, missing references
and a 1500-object chain without Python recursion overflow. Read-only policy keeps
inspection/sampling available and hides the editing tools.

A fixture prepared outside MCP using the native Blender CLI supplies an imported
keyed constraint, a driven target and an unsupported armature constraint. MCP
opens it with code execution disabled. Inspection reports keyed paths and refuses
configuration/removal, driver dependency traversal and the unsupported reachable
armature, preserving the original fingerprint. This qualifies refusal/preservation;
it does not claim typed authoring of keyed constraints or drivers. Legacy skeletal
binding, clips, independent deformation, rendering and GLB checks also pass.

Scope: allowlisted copy/limit/damped-track constraints and bounded LEGACY IK on
local Object-mode data. Dependency validation is conservative and rejects unknown
reachable behavior; it is not a comprehensive arbitrary-rig analysis. Existing
simple clip tools retain their constraint/driver/active-NLA guards. Constrained
channel editing, curve refinement and visual baking were separate milestones;
see their qualifications above. Driver authoring was subsequently qualified above; retargeting and NLA authoring remain open. Native frame evaluation blocks and cancellation checks are between frames;
this run does not qualify long-running sampling cancellation or large scenes.
No packages, virtual environments, installed services/skills or engine-specific
integrations were changed. Verification used isolated background instances.


## Isolated high-to-low texture bundles — 2026-11-02

Expanded texture/UV/capability/shader-contract/server/storage checks passed
**25 tests in 147.38 seconds**, with the existing Starlette/AnyIO warning.
After excluding node UI fields from content binding, normalizing output node
names and fixing a real atomic-status-file inventory race, the final focused run
passed **9 tests in 81.05 seconds**. A final rendered-color control passed
**1 test in 22.70 seconds**:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_TEXTURE_EVIDENCE_DIR=/tmp/mb-textures-20261102 python3 -m pytest -q tests/test_texture_contracts.py tests/test_texture_baking.py tests/test_capabilities.py --tb=short --maxfail=1
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_TEXTURE_EVIDENCE_DIR=/tmp/mb-textures-20261102 python3 -m pytest -q tests/test_texture_baking.py::test_high_low_maps_reopen_glb_and_binding --tb=short --maxfail=1
```

With MCP Python disabled, real Blender 5.0.1 projects a 17x17 detailed surface
onto a one-face low plane. Seven maps cover tangent normal, geometry AO, base
color, roughness, metallic, emission color and alpha. Source fingerprint/path
remain unchanged. Masks report 100 percent projected coverage at the fixture's
96x96 resolution. Normal channels vary, AO includes dark and unoccluded regions,
the procedural checker transfers both colors, and scalar means match .3/.7/.8.
The baked low mesh has a PBR material with relative texture paths and a glTF
occlusion settings group. Its actual Cycles preview was opened and inspected;
the final control independently decodes the PNG and requires over 200 red-dominant
and over 200 blue-dominant pixels. GLB has embedded base/metallic-roughness,
normal, occlusion and emission textures.

Opening and relocating the bundle preserves native validation. Geometry edits
and actual PNG corruption invalidate it, while changing a shader node UI label
does not. A custom matching cage succeeds; a deliberately too-short projection
ray fails the coverage threshold with a readable error and preserved partial
output. Self baking from a saved packed PNG produces flat normals, white AO,
transferred alpha and varying color. This also exercises packed input image
binding across the isolated source snapshot.

During a real 1024x1024 AO bake, broker restart preserves the editing instance;
cancellation stops/reaps its owned child and reusing the request ID does not
replay. Progress contains free bytes, the estimate, phase/map and output bytes.
Dry-run cleanup preserves files; applying it refuses current project references
and unknown entries before removing the owned cancelled partial. Success is
protected. A complete genuine output with metadata modeling the narrow
post-worker/pre-publication crash window is adopted only after recorded processes
are gone, then reopened and natively validated.

A separate fixture actually SIGKILLs its isolated editing instance during baking.
The operation becomes interrupted, its child watchdog exits, and a fresh instance
reconciles partial files without replay. Cleanup requires explicit inclusion of
interrupted work. A deterministic file-reader test reproduces a temporary status
entry disappearing during atomic rename; inventory tolerates that event while
continuing to reject symlinks, nonregular and unknown files. Both bundled design
and render skills validate. No packages, virtual environments, installed runtime
or installed skills were changed. One early integration attempt never reached
baking because host swap pressure delayed broker startup; its fixture-owned
late broker was stopped before retry. Existing user applications were untouched.

Scope: current-frame evaluated local meshes and direct static Principled source
graphs; bounded saved/packed single-image inputs. Output is 8-bit PNG and a static
low asset. Original rig/modifier editing remains in the live/source project.
AO treats geometry as opaque, not alpha-cutout foliage. Emission transfers color,
not arbitrary HDR radiance or shader lobes. Projection validation samples output
pixels, and bounds/storage estimates are not global memory caps or filesystem
reservations. Native map calls block only the owned child; source snapshot saving
in the editing instance remains blocking. Other versions/platforms, larger
workloads and production asset qualification remain unproven.
Evidence: `/tmp/mb-textures-20261102/`.


## UV seam/layout/density tools — 2026-11-02

The expanded UV/contracts/capability/server suite passed **25 tests in 80.15
seconds**, with the existing Starlette/AnyIO warning. Final qualification added
an independent density check after GLB reimport, MINIMUM_STRETCH and degenerate
triangle overlap controls; **7 focused tests passed in 70.20 seconds**:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_UV_EVIDENCE_DIR=/tmp/mb-uv-20261102 python3 -m pytest -q tests/test_uv_contracts.py tests/test_uv_editing.py tests/test_capabilities.py --tb=short --maxfail=1
```

Real Blender 5.0.1, with MCP Python execution disabled, isolates a shared
rectangular box, assigns named edge seams and unwraps six nonoverlapping islands.
Normalization reaches 128 pixels per world unit with nonuniform object scale;
packing with scale=false preserves that density. Activating DeliveryUV chooses it
for render/export. Geometry/topology remain unchanged; maps and their guarded
fingerprints survive save/reopen. A checker preview was opened and inspected.
GLB reimport has nondegenerate UVs and retains a six-island layout at the requested
density. This verifies UV delivery; the procedural checker itself is not a baked
PBR texture and its appearance is not claimed to survive GLB.

Separate fixtures detect deliberately overlapping projections, remove overlap
by packing, reject stale transform/map guards, normalize at a nonsquare texture
size and refuse collapsed-world-area islands without changing the UV fingerprint.
An exhausted overlap budget explicitly reports incomplete inspection. Native
ANGLE_BASED, CONFORMAL and MINIMUM_STRETCH paths are exercised. A skinned limb
with a relative shape key keeps its geometry, shape data, bone/weight inspection
and object selection through seam edits, unwrap and packing. Read-only policy
exposes inspection but hides the six UV editing tools. Pure clipping controls
include reversed winding, partial overlap, disjoint triangles, boundary-only
contacts and degenerate triangles. The bundled design skill validates.

These tools edit the entire base-mesh UV map, not evaluated deformation. Density
is area-based pixels per Blender world unit. Native unwrap/packing is blocking;
inspection is bounded and incomplete overlap checks are never a clean-layout
proof. High-to-low texture baking, pins/partial-face editing and general UDIM
workflows are outside this milestone. Evidence: `/tmp/mb-uv-20261102/`.
No packages, virtual environments or installed runtimes/skills were changed.


## Volume shader authoring — 2026-11-02

Focused verification passed **5 tests with 1 expected failure in 81.89 seconds**:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_EXPECT_EMPTY_CACHED_VOLUMES=1 MCPBLENDER_VOLUME_EVIDENCE_DIR=/tmp/mb-volumes-20261102 python3 -m pytest -q tests/test_volume_materials.py tests/test_shader_contracts.py tests/test_shaders.py tests/test_capabilities.py --tb=short --maxfail=1
```

With MCP Python execution disabled, typed tools create constant volume, smoke and
flame/temperature-driven fire graphs. Invalid numeric-socket string edits preserve
the graph. Attribute properties/string sockets and all volume graphs survive
save/reopen, including a fluid asset saved outside its bundle. Cache validation
continues to pass. Asset reporting flags target-engine volume conversion limits.
A homogeneous emissive mesh volume produces over 100 additional warm pixels
against its emission-off control; the rendered image was opened and inspected.

The expected failure is deliberately **not a rendering pass**. The actual cached
fire, emission-off and smoke renders are identical empty scenes. Separate native
quick-smoke and direct OpenVDB fixtures reproduce missing volumes; cached density,
flame and temperature grids are nonzero. The local Blender 5.0.1 build cache has
`WITH_NANOVDB=OFF`, consistent with Cycles' upstream loader requiring NanoVDB.
This explains the Cycles failure; the separate EEVEE failure remains unresolved.
No renderer rebuild, package change or installed-runtime change was performed.
The expected-failure opt-in applies only after graph/bundle persistence checks,
at the actual visible-fire assertion. Without that explicit environment flag,
the cached-render test fails normally. Other errors are never converted to xfail.
Keep cached smoke/fire visual qualification open and rerun without the flag on
a suitable Blender build. Evidence is under `/tmp/mb-volumes-20261102/`.


## Static-source fluid bundles — 2026-11-02

The full regression passed **119 tests in 716.87 seconds**, with the existing
warning. Final refinements then passed **21 focused tests in 106.16 seconds**:
source binding now includes nested domain effector weights/collection guards;
actual zero-gravity liquid stays aloft while the normal fixture falls onto its
shelf. The original project path is preserved. A partial bundle's open source
project blocks deletion. The isolated worker uses its bundle as its working
directory and disables its own native core dumps. The full regression precedes
these final refinements; the focused run covers their affected workflows.

An earlier expanded focused suite passed **21 tests in 100.73 seconds**, with the existing
Starlette/AnyIO deprecation warning:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_FLUID_EVIDENCE_DIR=/tmp/mb-fluids-20261102 python3 -m pytest -q tests/test_fluids.py tests/test_fluid_contracts.py tests/test_capabilities.py tests/test_broker_startup.py tests/test_server.py tests/test_storage.py --tb=short --maxfail=1
```

Real Blender 5.0.1 creates a liquid domain, geometry source and interior collision
shelf through typed tools with Python execution disabled. Isolated worker baking
produces native data and a surface; at frame 24 the falling liquid remains within
one domain cell of the shelf top. The live project's frame stays unchanged.
A fresh Blender opens the baked asset, validates file/source/cache/checkpoint
bindings, detects a changed collider and renders the cached mesh. The coarse blue
liquid preview was opened and inspected. A relocated bundle also validates through
its relative cache path. Actual corruption of a cache file is detected.

Smoke inflow produces increasing sampled density; grid checkpoints survive saving
and reopening. This qualifies solver data, not volume-material authoring or final
smoke/fire rendering. A running 240-frame native bake survives broker restart,
then cancellation terminates/reaps its owned child. Progress includes available
space and estimates; retrying the same request ID returns the same cancelled job.

A disposable editing-instance SIGKILL interrupts its operation and its owned bake
worker exits. A fresh instance reconciles the abandoned directory without replay.
Interrupted output is preserved unless explicitly included in cleanup. A separate
metadata fixture models parent death after a genuine complete worker result;
reconciliation adopts its file-bound manifest and still requires native validation.
Recovery refuses live recorded processes. Successful deliverables, symlinks,
unknown entries and referenced outputs are protected from partial-job cleanup.
Cleanup defaults to inspection, and an explicitly applied cancelled-job cleanup
removes only the verified owned directory.

Earlier focused runs passed 19 tests in 85.91 seconds, then 6 fluid/contract/
capability checks in 88.05 seconds after native range checks. The final run adds
portable-bundle/adoption checks and finite/nonzero-domain preflight. The bundled
animation skill validator and `git diff --check` passed.

Native fluid cache enums differ from the class-only RNA catalog: liquid meshes
use BOBJECT. Liquid domains also create a legacy FLIP display system unless
explicitly disabled; surface baking still uses solver particles. Workers use
modular UNI data caches and optional liquid meshes. Source snapshots contain the
whole scene; output caches remain external. Storage estimates/quota monitoring
are heuristics, not filesystem reservations. Snapshot saving in the editing
instance remains noninterruptible; native baking blocks only the owned child.
Hash validation yields bounded batches and native checkpoint sampling restores
the frame. Native checkpoint equality is sampled, not an all-frame solver proof.

Evidence under `/tmp/mb-fluids-20261102/` contains liquid/smoke bundles and a liquid
PNG. Other Blender/platform versions, large workloads, animated/deforming fluid
sources, guiding, noise/secondary particles, force-field coupling, cache-to-game
animation and finished gas volume materials are outside this qualification.
No packages, virtual environments, installed services or installed skills changed.

## Broker request draining — 2026-11-02

Broker shutdown now closes its listener and drains accepted handlers before
closing their shared journal. Input reads have a five-second total deadline.
A deterministic socket fixture holds a partial request across restart, waits
until the listener is closed, then finishes that accepted request and verifies
its reply still uses a live journal. All six broker-startup checks passed;
the combined broker/fluid-development run passed nine tests in 60.48 seconds,
including restart during an isolated native bake followed by cancellation.
This fixes the observed closed-database progress race; it does not make remote
network operations replayable after broker interruption.

## Cloth, soft bodies, particles and force helpers — 2026-11-02

The initial point-cache suite passed **4 tests in 62.29 seconds**, using real
Blender 5.0.1 through MCP with arbitrary Python execution disabled. It covers
pinned cloth contacting a floor, soft-body collision, Newtonian object-instance
particles, measurable wind response, static hair strand length and running bake
cancellation. Expanded simulation/rigid/capability/server/storage checks passed
**18 tests in 152.37 seconds**. The complete regression then passed **114 tests
in 646.63 seconds**, including explicit coordinate-space metadata and collider
enable-state fingerprints, with the existing Starlette/AnyIO warning. The final
shared-mesh isolation guard is verified by additional focused checks below.

After that guard, **15 focused tests passed in 92.38 seconds**:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_SIM_EVIDENCE_DIR=/tmp/mb-sim-20261102 python3 -m pytest -q tests/test_simulations.py tests/test_simulation_contracts.py tests/test_capabilities.py tests/test_server.py tests/test_storage.py --tb=short --maxfail=1
```

Linked-mesh pin edits are refused without explicit isolation. After isolating and
removing one object's cloth pins, a linked copy retains its pinned position under
actual simulation. The bundled animation skill validator and `git diff --check`
also passed. The full 114-test run precedes this final isolation refinement.

Typed configuration uses an inspected simulation fingerprint; cloth pin indices
also require a topology fingerprint. Dedicated static meshes, static collision
objects and owned Empty force helpers are the supported dependency model. Shared
particle settings require explicit isolation. Evaluated unbaked caches require
explicit reset; baked caches must be cleared before configuration changes.
Shared deform meshes and removal of shared pin weights require explicit
`make_single_user=true`; the linked object's original geometry/weights remain.

Sequential sampling restores the original frame. Embedded-cache baking saves a
full-scene `.blend` copy, preserving the active project path. Validation compares
source binding and bounded geometry/particle checkpoints, including a particle
snapshot opened in a separate disposable Blender process. This is sampled
validation, not an all-frame solver proof. Moving a dependency invalidates its
binding; clearing live caches preserves the snapshot bytes.

Frame/point/cache budgets and per-frame storage checks constrain work. Tracked
progress includes free space and estimated output size. A broker restart preserves
the running operation; cancellation restores the frame at a cooperative boundary
and a repeated request ID does not replay it. Native cache finalization/save remain
noninterruptible. Existing snapshot paths are refused.

Native API checks caught three important behaviors: `hair_length` aliases emitter
velocity, so it must only be assigned for hair; static hair needs NEWTON physics
with dynamics disabled, as NO collapses strands; legacy `trail_count` normalizes
from 0 to 1 on reload and is excluded from the physics fingerprint. Computed
soft-body location/rotation/scale estimates are also excluded as solver outputs.

External/disk/fluid caches, particle children/dynamic hair, animated/deforming
sources, dynamic colliders and collection/texture dependencies are unsupported.
Static hair is saved normally rather than frame-baked. Cache motion is not yet
converted to exported animation. Explicit snapshots are protected deliverables;
this feature does not implement their automatic retention/deletion. No installed
service, package, dependency or installed skill was changed.

Evidence under `/tmp/mb-sim-20261102/` includes cloth and particle renders, plus
cloth/soft/particle `.blend` snapshots. Both renders were opened and inspected.
The particle image was rendered after opening the saved cache in a fresh Blender
process. These low-resolution functional previews do not establish final visual
quality, target-engine behavior or long-duration workload stability.

## Capability classification — 2026-11-02

`MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_capabilities.py
--tb=short --maxfail=1` passed **2 tests in 11.66 seconds**. The inventory is
checked against registered command contracts, and a real MCP query with Python
execution disabled verifies structured mesh/shader discovery, explicit Python-only
gaps, and no checkpoint mutation. Inventory describes worker implementation;
caller permissions and feature qualification remain separate concerns.

## Geometry Nodes foundation — 2026-11-02

The initial combined Geometry Nodes/capability/server suite passed **13 tests in
43.11 seconds**. Expanded focused checks then passed **6 tests in 44.54 seconds**:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_GEOMETRY_EVIDENCE_DIR=/tmp/mb-geometry-20261102 python3 -m pytest -q tests/test_geometry_contracts.py tests/test_geometry.py tests/test_capabilities.py --tb=short --maxfail=1
```

Real Blender 5.0.1 runs with Python execution disabled. Every catalog node is
instantiated. A reusable floor-array group attaches to two objects; per-modifier
integer inputs produce independently verified 5/3-floor meshes. Graph inspection
reads back both values. The graph, material references, input values and evaluated
geometry survive save/reopen; detaching one modifier leaves the other intact.
A Cycles preview was opened and visually inspected. Evidence includes the PNG,
editable project and explicit-object GLB.

The fixture found that ordinary GLB export omits procedural modifiers by default.
Explicit `apply_modifiers=true` now exports evaluated static geometry without
changing the source. GLB accessors verify the intended five-floor height and the
material reference. Evaluated export refuses shape-key meshes, while the normal
export retains a morph target. Other checks cover float/vector/boolean interfaces,
Euler rotation and multi-input geometry joins; invalid replacements, socket types,
properties, cycles, cardinalities and stale guards preserve existing results.
Read-only policy hides/denies graph edits. The bundled design skill validates.

This qualifies bounded managed groups and the tested combinations, not every
node combination, imported nested graphs, field workload limits, simulation zones,
reusable procedural presets or separate render workers. The installed user service
and installed skills were not changed; no dependency/environment changes occurred.

## Procedural presets — 2026-11-02

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_PRESET_EVIDENCE_DIR=/tmp/mb-presets-20261102 python3 -m pytest -q tests/test_geometry_presets.py tests/test_geometry.py tests/test_geometry_contracts.py tests/test_capabilities.py tests/test_shaders.py tests/test_shader_contracts.py tests/test_action_integration.py tests/test_actions.py tests/test_asset_contracts.py tests/test_server.py --tb=short --maxfail=1
```

**41 tests passed in 179.32 seconds**, with the existing Starlette/AnyIO warning.
An additional isolated scatter run passed **1 test in 18.29 seconds**, verifying
normal alignment on a vertical surface and fixture independence.

With arbitrary Python execution disabled, real Blender 5.0.1 creates a textured
brick building, separate roof/window materials and repeated window panels. Two
objects share a recipe with independent floor counts; dimensions and vertex
counts match the parameters. Generated UVs have no zero-area faces in the building
fixture. Packed textures and three material references survive evaluated GLB
export; graph fingerprints, parameter limits and geometry survive save/reopen.
Invalid replacement with a missing material preserves the original recipe.

Vegetation uses UV-bearing trunk/crown meshes with distinct materials and the
requested height. The initial fixture caught the cone node's bottom-origin versus
the cylinder node's centered origin; the recipe now accounts for both. Seeded
surface scattering caps output to five trees, then two after changing MaxPoints;
changing/restoring a seed changes/restores the geometry fingerprint. A vertical
surface verifies tree axes follow its normal. Candidate-budget refusal preserves
the target and rejects mixed parameter batches without partial application.
Forest geometry survives save/reopen and exports both tree materials.

Refinement preserves the original source mesh while producing the expected 24/96
subdivision faces from a cube. Out-of-range levels, shape-key geometry, an upstream
modifier and an excessive face estimate are refused. Returned workload records
expose estimates and limits. The building/forest PNGs were opened and visually
inspected; PNG, blend and GLB evidence is retained outside Git.

This qualifies the supplied exterior/pine/scatter/subdivision recipes, not an
architectural interior generator, arbitrary species or topology repair. Workload
checks apply at attachment/input update; area-based candidate estimates are not
hard intermediate-memory limits. Preset metadata and limits remain inspectable.
The design skill source validates; installed service/skills were not changed.

## Structured shaders and material presets

On 2026-11-01, `MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q
tests/test_shader_contracts.py tests/test_shaders.py --tb=short` passed **2 tests in
15.95 seconds**. Unit checks reject executable nodes, nonfinite values, duplicate
names, path escape and read-only edits without starting Blender. Real Blender
checks run with Python execution disabled: catalog discovery, procedural noise/ramp
graphs, invalid replacement with the original graph preserved, incremental node
and link edits, connection overwrite refusal, and all four material presets.
The textured PBR preset packs all four maps with appropriate color spaces, renders
a checker-painted sphere, survives save/reopen, and exports GLB with base-color,
metallic/roughness and normal texture references verified by JSON parsing. The
render was opened and visually inspected. Evidence: `/tmp/mb-shaders-20261101/`.
This qualifies the installed Blender 5.0.1 surface, not arbitrary imported node
groups, animated shader graphs, every supported node combination or Godot shaders.

## Guarded mesh editing — 2026-11-02

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_MESH_EVIDENCE_DIR=/tmp/mb-mesh-20261102 python3 -m pytest -q tests/test_mesh_contracts.py tests/test_mesh_editing.py tests/test_asset_contracts.py tests/test_asset_editing.py tests/test_server.py --tb=short --maxfail=1
```

**25 tests passed in 69.18 seconds**, with the existing Starlette/AnyIO warning.
Using real background Blender with arbitrary Python tools disabled, the new
fixture inspects indexed elements, stores a named roof selection, extrudes/insets
the roof, rejects old fingerprints and stale named selections, and preserves the
result across save/reopen. Repeating an extrusion request after broker restart
returns the original operation without changing the newer mesh. The rendered
preview was opened and visually inspected; evidence includes the saved project.

Other checks verify quad-ring cuts, shared-data refusal and explicit isolation,
invalid-index/non-quad/coordinate-conflict refusal without mesh replacement,
shape-key refusal, inward/outward winding, vertex merging and loose cleanup.
Difference/union/intersection Boolean results have expected volumes; explicit
GLB export includes the finished shell and excludes the cutter. Contract checks
cover malformed indices/parameters and read-only policy enforcement.

An initial selection implementation triggered a native crash while directly
writing vertex selection. Selection now uses temporary BMesh/copy assignment;
the reproducing fixture and the combined suite pass. This milestone supports
local Object-mode meshes without shape keys/armature deformation, not sculpting,
retopology or arbitrary imported dependency graphs. Generated UV quality still
needs review. The installed user service/skills were not upgraded or restarted.

## Rigid-body evaluation and embedded cache snapshots — 2026-11-02

The initial focused physics suite passed **3 tests in 33.04 seconds**; adding a
fresh-process restore check passed **5 physics/capability checks in 67.81 seconds**.
Source binding was then expanded to include collision masks, deactivation
settings, effector weights and cache mode, with final source rechecks.
The final focused physics/capability run passed **5 tests in 49.38 seconds**:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_physics.py tests/test_physics_contracts.py tests/test_capabilities.py --tb=short --maxfail=1
```

After diff review caught and corrected displaced legacy filename validation,
**10 host tests passed in 11.69 seconds** (`test_physics_contracts.py`,
`test_server.py`, `test_storage.py`), including explicit preservation of existing
open/save/GLB suffix checks. The animation skill source validates.

Real Blender 5.0.1 runs with arbitrary Python tools disabled. Typed setup creates
active/passive BOX colliders. Sequential simulation shows a cube falling from
Z=6 to a resting center at Z=1 on its collision floor, within 0.05 Blender units.
Sampling restores the original frame; stale fingerprints and implicit unbaked
cache invalidation are refused. A native embedded bake is saved as a `.blend`
copy without changing the active project path. Start/middle/end matrices validate
after reopen, including in a second disposable Blender process. Source transform
changes break the binding; restoring the source permits checkpoint validation.
Native outdated flags after load are reported separately from those checks.

Broker restart during a running simulation preserves Blender's PID and operation;
cancellation at a frame boundary restores the original frame. Reusing the same
request ID returns the original cancelled/completed operation. Progress includes
current free bytes and a worker-refined output estimate. Clearing the live bake
leaves the saved snapshot byte-for-byte unchanged, and body removal preserves the
mesh. The rendered settled cube was opened and visually inspected; evidence is
retained outside Git under `/tmp/mb-physics-20261102/`.

An API probe demonstrated that external-cache flags can produce a native baked
flag without valid data/files. The implemented workflow therefore requires native
disk/external flags disabled and checks pose checkpoints. Another probe confirmed
rigid data can be embedded and restored from a project. Validation covers source
binding and pose checkpoints, not every cached frame or arbitrary imported
physics dependencies. This milestone is not cloth/fluid/particle baking, automatic
cache snapshot retention/deletion or conversion to animation keyframes. Native
finalization/project save remain blocking calls. No installed runtime was changed.

## Latest complete regression — 2026-11-02

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q --tb=short --maxfail=1
```

**110 tests passed in 591.35 seconds**, with the existing host Starlette/AnyIO
deprecation warning. This source-checkout run covers the mesh editing, capability
and Geometry Nodes/preset and rigid-body foundations alongside recovery, retention,
modeling, materials, skeletal/morph animation and video workflows. The expanded
physics source guard changes were checked separately as documented above. No installed
service deployment or Godot work was performed.

The preceding complete run passed 103 tests in 424.37 seconds before procedural
presets and rigid-body/cache tools were added.

## Previous complete regression — 2026-11-01

On 2026-11-01, after the installation-driven recovery and splash changes:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q --tb=short --maxfail=1
```

**85 tests passed in 543.02 seconds**, with the existing host Starlette/AnyIO
deprecation warning. This run includes the new startup/recovery contention
regressions and the earlier modeling, shader, animation, video, retention and
interruption checks. The installed service was independently exercised as below.

## Permanent installation and recovery qualification

On 2026-11-01, the standard sdist and wheel build passed with dependency checks
enabled in a private Python environment. Installed package imports were checked
outside the checkout, declared runtime constraints passed, and every installed
Python module was compared with current source. The environment reuses existing
host dependencies; no host dependency upgrades or Blender rebuild were performed.

The authenticated loopback FreeBSD service is boot-enabled and supervised.
Missing/invalid keys returned 401. Separate Codex and PQC credentials discovered
93 tools; PQC's native HTTP transport queried the shared recovered asset and found
all three adapted skills. Its configuration validates after backing up and aligning
stale sample agent model overrides with the instance's already selected models.
Installed stdio attached to the same GUI/session. Private configurations, keys,
backups, host service settings and evidence remain outside Git.

Through the installed HTTP endpoint, structured tools created a UV-mapped textured
asset and preview stage, saved a project, exported GLB, rendered a Cycles image and
captured a viewport. The rendered image was visually inspected. Service restart
and supervised frontend exit preserved Blender's PID/session. Broker restart
preserved Blender and operation history. Killing the owned test application
restored its checkpoint and asset in a new session without replaying the completed
render. Evidence is retained privately in the model library.

This installed crash test exposed a duplicate-launch race. The broker supervisor
and frontends now share a nonblocking launch lock, and a frontend waits for an
already-starting recovery PID. Ten focused broker/operation tests passed, including
deterministic contention and pending-worker coverage. The real Blender recovery
test now immediately queries during recovery rather than waiting for registration;
it passed in 31.55 seconds. A fresh installed GUI confirmed session-only splash
suppression. The earlier first launch had its welcome dialog dismissed manually.

Actual reboot/login access, longer-duration service operation, log rotation,
external HTTPS ingress and Godot integration remain unqualified. Godot is paused.

## Shader and retention regression

On 2026-11-01, FreeBSD Blender 5.0.1:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_SHADER_EVIDENCE_DIR=/tmp/mb-shaders-20261101 python3 -m pytest -q --tb=short --maxfail=1
```

**83 tests passed in 334.08 seconds**, with the existing host Starlette/AnyIO
deprecation warning. This includes named recipes, all three built-in workflows,
typed permission/path preflight, real asset/animation delivery, cancellation and
late-failure restoration, broker restart, application interruption and checkpoint
recovery without replay, structured shader authoring/PBR delivery, and scoped
temporary-output/history retention. The earlier startup handshake failure described below
was corrected and this complete run passed. The final wheel and add-on archive
were checked for current workflow/recovery code; the setuptools build-environment
limitation below applied at the time of that run. Permanent installation was
qualified separately afterward, as described above.

## Retention controls

The complete run covers temporary-output tracking, explicit deliverable protection,
pins and structured-input protection, active/unknown operation protection, age and
size thresholds, bounded scans, modified-file refusal and final/ancestor symlink
replacement. Registration errors leave no queued scene edit. History compaction
preserves request-ID/digest tombstones; both renders and scene edits remain
deduplicated after their details are pruned. The real MCP test cleans a generated
Cycles render without replaying it, and verifies pin/unpin and library-write policy.
After adding paginated output-group reporting, the focused retention suite passed
**9 tests in 9.71 seconds**, including a fresh real MCP/Blender run.

Cleanup is limited to new registered generated outputs. It does not sweep legacy
files, delete explicit output paths, vacuum databases, rotate logs or infer external
Python/editor dependencies. Unknown filenames inside frame directories remain.
Automatic maintenance is opportunistic during submissions; age tests use controlled
local fixtures, not a seven-day soak. Physical reclamation depends on the filesystem.
The wheel (dependency-check-skipped due to the host setuptools version noted below)
and add-on archive were checked byte-for-byte for current shader/retention workers.
All three updated bundled skills passed validation; no permanent installation or
client configuration was performed.

## Built-in preview setup

On 2026-11-01, `MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q
tests/test_actions.py tests/test_action_integration.py --tb=short` passed **14 tests
in 26.75 seconds**. Separate action/server checks passed 18 tests. With Python
execution disabled, Blender created an offset painted asset, rejected a missing
target without adding objects, fitted perspective and orthographic cameras,
refused a repeated stage prefix without changing objects, and rendered a Cycles
preview. The retained `/tmp/mb-actions-resume/stage.png` was opened and visually
inspected. Existing scene objects and lights remain visible by design; this is
stage setup, not scene isolation or final-quality lighting.

## Game-asset preparation

The action checks expanded to **16 tests passed in 34.94 seconds** on 2026-11-01.
Real Blender checks verify all-target preflight before transforms, explicit UV and
triangulation edits, retained world geometry, a saved project, and an explicit-object
GLB with an embedded texture checked by parsing its JSON chunk. Selection is
restored after export. Existing UVs are refused without overwrite consent. A
separate read-only frontend runs inspection and budget checks without a recovery
checkpoint. Unit checks cover optional-step permission denial, path escape and
duplicate targets. No target-engine compatibility claim follows from these checks.

## Animation-preview workflow

The dedicated real Blender workflow test passed on 2026-11-01 in **22.64 seconds**,
with Python execution disabled. It creates a textured skinned/morph asset,
temporarily selects both slots of a combined clip, and renders five changing PNG
frames plus an H.264 video. Independent ffprobe checks confirm five frames at
12 fps. Exact inspected geometry, live clips, frame, objects, render settings and
user VSE strips are restored after success, running cancellation and a deliberately
introduced encoding-output conflict. Partial-frame artifacts remain available on
failure/cancellation. Save/reopen preserves geometry, clips, camera/timeline and
the packed texture. Parsing explicit-object GLB confirms bone and weight channels
and the embedded texture. First/last PNGs and an extracted encoded video frame were
opened and visually inspected. Evidence: `/tmp/mb-actions-resume/`.

The complete action group (`tests/test_actions.py tests/test_action_integration.py`)
passed **18 tests in 77.73 seconds**. The first full regression attempt passed 62
other tests but had five shared-fixture errors: the initial broker status handshake
timed out before Blender launched. The action group passed when rerun; the broker
startup retry was subsequently corrected and qualified in the complete run above.
That earlier attempt was not a full-suite pass.

The add-on archive contains the workflow worker without frontend dependencies.
A standard `python3 -m build --wheel --no-isolation` was blocked by the host's
setuptools 63.1.0 (the project declares >=68). An artifact sanity build using
`--skip-dependency-check` succeeded and its workflow modules were checked. This
does not qualify the declared build environment; no packages were installed or
upgraded. All three bundled skills passed the skill-creator validator.

## Named-action engine milestone

### Interruption and startup checks

Five focused checks passed in **29.90 seconds** on 2026-11-01. Startup unit checks
cover read-only status timeout/disconnect retry with one broker spawn and immediate
propagation of unrelated protocol/policy errors. Real Blender checks restart the
broker during a 64-step editing action, then verify all 64 unique objects, the same
Blender session, and request-ID deduplication. A separate action is interrupted by
killing its owned Blender process after completed edits. Its unknown outcome is
recorded; explicit application restart restores the completed checkpoint, and
resubmitting its request ID does not replay the interrupted action. These are
bounded local interruption checks, not power-failure or long-duration proof.

On 2026-11-01, the focused engine and shared-infrastructure checks passed:

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_actions.py tests/test_action_integration.py tests/test_server.py tests/test_operations.py tests/test_storage.py tests/test_wire.py --tb=short
```

**30 tests passed in 21.95 seconds**, with the existing host Starlette/AnyIO
deprecation warning. Tests cover strict recipe inputs, forbidden commands and
templates, permission filtering and preflight, library-path confinement, stable
generated paths, storage estimates and configuration-relative recipe files.
Real Blender tests use Python execution disabled and verify successful serial
editing/inspection, explicit partial failure with retained edits, frontend reconnect
and request-ID deduplication, and running cancellation between completed steps.
Owned test Blender and broker processes are stopped by fixture cleanup.

This is a focused check of the current changes. The complete regression below
predates the engine. Built-in workflow recipes, specialized server-side shims,
action-specific broker-restart/crash tests and representative named-action asset
delivery remain pending. Actions provide partial reports, not transactional rollback
or step-by-step recovery. No permanent installation was performed.

## Latest complete regression (before the action engine)

On 2026-11-01, FreeBSD Blender 5.0.1:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_MORPH_EVIDENCE_DIR=/tmp/mb-morph-20261101 python3 -m pytest -q
```

**49 tests passed in 247.29 seconds**, with the existing host Starlette/AnyIO
deprecation warning. The wheel built without dependency downloads and contains
the morph contracts and worker. The add-on bundle includes the morph worker
without frontend dependencies. Updated animation/design skills passed their
validators. Blender was not rebuilt; no permanent deployment or client/skill
installation was performed.

## Shape-key additions

`MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_morph_contracts.py tests/test_shape_keys.py`
passed **4 tests** on the installed Blender 5.0.1 with Python execution disabled.
The tests checked sparse Basis-relative/absolute coordinate edits, half-weight
evaluated positions, non-accumulating offsets, reset/delete, named-key pagination,
source topology refusal, shared-data isolation and save/reopen. Invalid indices,
stale fingerprints, nonfinite input and read-only editing were refused. New key
weights are explicitly zeroed because this Blender build initializes new keys at one.

Named morph animation and delivery checks subsequently covered:

- Scalar keyframe insertion/update and intermediate fractional weights, checked
  against independently calculated mesh bounds; switching resets unkeyed values.
- Temporary sampling of another morph clip, with exact restoration of geometry,
  frame, weights and action. Running combined sampling was cancelled on a detailed
  mesh; both morph and skeletal states were restored with the original digest.
- A shared action with separate OBJECT/KEY slots. Editing bone keys preserved the
  morph slot and editing morph keys preserved bone channels. Joining an unrelated
  skeletal action and deleting an animated shape were refused.
- A textured segmented limb with combined skeletal/morph motion. Five consecutive
  frames were rendered and encoded at 192x192, 12 FPS. Independent ffprobe verified
  H.264 and five frames; the first and fully flared/bent PNGs were opened and viewed.
  The video covers the first five frames of the nine-frame source clip.
- Save/reopen with matching sampled geometry digests. GLB inspection verified
  named combined and morph-only clips, rotation/weight channels, a named POSITION
  morph target, skin attributes, UVs and embedded texture. Both clips were
  re-imported and sampled at frames 1, 3, 5 and 9: weights matched within 0.00001
  and evaluated world bounds within 0.0001 Blender units. Export restored the live
  state and removed its temporary tracks.
- Morph-only export with no rig, an inactive managed action and static weight
  0.25. The file retained that default weight and its animation; source state
  remained unchanged, and re-imported sampled weights matched the source.

Evidence is retained under `/tmp/mb-morph-20261101/`: `morph-animation.blend`,
`morph-animation.glb`, `morph-solo.glb`, `morph-evidence.json`, `morph-preview/` and
`morph-preview.mp4`. All these workflows ran with Python execution disabled.
Qualification covers small relative Basis-based shapes, including one morph on
a two-bone skinned mesh. It does not establish general facial-rig, corrective
driver, absolute-shape-key or target-engine correctness.

## Skeletal-stage complete regression

On 2026-11-01, FreeBSD Blender 5.0.1:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_SKELETAL_EVIDENCE_DIR=/tmp/mb-skeletal-20261101 python3 -m pytest -q
```

**39 tests passed in 221.96 seconds.** The one warning is the pre-existing host
Starlette/AnyIO deprecated alias. The wheel built without dependency downloads
and includes the skeletal worker. Updated animation/design skills passed the
skill-creator validator. No permanent deployment or consuming-agent installation
was performed.

## Skeletal tools additions

`MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_animation_contracts.py tests/test_skeletal_animation.py`
passed **3 tests** on Blender 5.0.1. Python execution was disabled. Live checks
created a connected two-bone armature, bound a segmented mesh with blended explicit
weights, verified world endpoints/paginated inspection and preserved selection,
and exercised rigid and native automatic binding. Existing binding and invalid
vertex references were refused. Contract tests reject cyclic/invalid skeletons,
malformed weight arguments and editing through a read-only policy.

Named clip addition: the focused command passed **5 tests**. It authored and
edited bone tracks, sampled key and intermediate poses, checked the upper mesh
ring against an independently calculated 45-degree endpoint, verified a fixed
lower ring, and compared exact geometry digests before/after temporary sampling.
Switching clips reset unkeyed channels; clearing the action restored rest pose.
Duplicate names, missing bones and cross-rig managed actions were refused.

Delivery/cancellation addition: the full suite above also covered a textured,
two-bone segmented mesh with blended skinning, two named clips, five rendered
preview frames and a 192x192 H.264/AAC MP4. Independent ffprobe inspection confirmed
five video frames. Beginning and bent-middle PNGs were opened and visually
inspected. A preview assembled from every other source frame is a motion sample,
not a timing qualification for the full clip.

The editable project survived save/reopen with matching sampled geometry digests.
Independent GLB JSON/binary inspection verified exactly the two intended clip
names, a two-joint skin, normalized exported weights, UVs and an embedded texture.
Unrelated actions from other test rigs were excluded. The GLB was re-imported;
both imported clips were selected and sampled through structured tools despite
their muted NLA stashes. At frames 1, 5 and 9, their evaluated mesh world bounds
matched the corresponding source clip within 0.0001 Blender units. Export restored
the source pose and removed its temporary NLA tracks.

A separate detailed-mesh sampler was cancelled while running. Its operation
became cancelled and the prior frame, clip and exact evaluated geometry digest
were restored. Python execution remained disabled throughout these workflows.

Evidence is retained under `/tmp/mb-skeletal-20261101/`: `skeletal-animation.blend`,
`skeletal-animation.glb`, `skeletal-evidence.json`, `rig-preview/` and
`rig-preview.mp4`. These are small-rig checks: automatic weighting was qualified
on a one-bone fixture; explicit blending, rigid binding and playback on two bones.
They do not establish arbitrary character-rig or target-engine correctness.

## Structured asset additions

Asset-stage full regression command:

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_ASSET_EVIDENCE_DIR=/tmp/mb-asset-editing-20261101 python3 -m pytest -q
```

**32 tests passed in 151.53 seconds**, with the same host Starlette/AnyIO
deprecation warning. Wheel construction also passed, including the new asset
worker module. The updated design/render skills passed their schema validators.

The Python-disabled asset fixture additionally qualified perspective and
orthographic camera fits, portrait/landscape aspect ratios, multi-object fits,
view presets and a custom direction. It created a beveled textured prop through
structured tools, rendered a CPU preview, saved/reopened the project and exported
and re-imported a GLB. Independent GLB JSON inspection verified embedded image
data and UV attributes; re-imported world bounds matched the source. The cleaned
192x128 preview was opened and visually inspected. Evidence is retained in
`/tmp/mb-asset-editing-20261101/`: `asset-preview.png`, `asset-editing.blend`,
`asset-editing.glb` and `asset-evidence.json`. This qualifies static asset editing;
skeletal deformation and Godot integration remain separate work.

`MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q tests/test_asset_contracts.py tests/test_asset_editing.py`
passed **3 tests** on the installed Blender 5.0.1. A disposable stdio client had
Python execution disabled. It verified base/evaluated cube geometry and world
bounds, bevel baking, all five structured modifier types, removal, missing/type
errors, selection preservation and boundary detection on an open triangle.
Contract tests reject arbitrary modifier properties and excessive subdivision;
read-only policy tests check discovery and direct submission denial.

UV projection addition: the same focused command passed **4 tests**. SMART and
CUBE projection produced finite, nonzero-area UVs without changing geometry;
overwrite protection and two-map persistence through save/reopen were verified.

Hierarchy/transform addition: the focused command passed **5 tests**. Live checks
covered world placement under a rotated, nonuniformly scaled parent; cycle
refusal; child placement during parent transform baking; unparenting; independent
and shared geometry copies; shared-data refusal/isolation when baking a modifier;
and refusal to bake animated object transforms. Python execution remained disabled.

2026-11-01, FreeBSD, installed Blender 5.0.1, Python 3.11, FastMCP 4.0.3.
Blender was not rebuilt and its installed files/preferences were not changed.
Permanent deployment and consuming-agent configuration remain deferred.

## Initial 0.2.0 regression baseline

```sh
MCPBLENDER_TEST_BLENDER=1 python3 -m pytest -q
```

**26 tests passed in 149.35 seconds.** One warning comes from the host's
Starlette/AnyIO deprecated test alias. Live tests used disposable processes and
private temporary directories, with actual stdio and HTTP MCP clients.

Covered behavior:

- Same-UID socket verification, private parent/socket modes, live-socket preservation,
  stale-socket recovery and refusal to overwrite other files.
- FreeCAD-compatible Argon2id hashes and all four remote key formats, tool discovery
  and direct-call policy enforcement, path traversal/symlink refusal, artifact/job
  ownership, token expiry and credential-free HTTP logs.
- Persistent operation/artifact recovery across separate MCP frontend processes;
  concurrent submissions of one request ID execute the mutation once, while changed
  arguments with the same ID are rejected.
- A client disconnect during a long Python edit leaves it running and recoverable.
  Queued cancellation prevents execution; running cancellation is cooperative.
- Broker restart during active Python work preserves its result without repetition.
- Application exit records unfinished work as interrupted with unknown outcome.
  Automatic recovery launches a replacement Blender from the completed checkpoint;
  an independent object readback verifies the saved pose and absence of replay.
- Opt-in frontend-exit shutdown preserves a checkpoint and stops its owned application.
- Graceful shutdown disables automatic recovery. A later editing request exercises
  lazy application startup. Bridge restart preserves Blender's process/session.
- Capacity checks reject low-space work before admission and recheck queued work
  before execution. Storage status reflects changing free bytes. Pixel estimates
  scale with resolution and frame count.
- Actual object/material/modifier edits, selection/transforms, save/open, overwrite
  refusal, GLB export/re-import, CPU rendering and MCP image delivery.

## Representative editing evidence

Retained under `/tmp/mb-building-20261101-final/`:

- `evidence.json`: resource/timeline inspection, API requests and independent ffprobe data.
- `library/building.blend`: editable image-textured exterior building and camera animation.
- `library/building-edited.blend`: sequencer timeline with image, title and sound strips.
- `library/building.glb`: exported model with packed image texture.
- `library/walkthrough-frames/`: 12 PNG frames and a manifest, with differing frame hashes.
- `library/walkthrough.mp4`: 384x256, 12-frame H.264 video with an AAC audio stream.

The fixture used structured mesh, material, light, camera and keyframe tools;
packed/reopened the texture; and rendered a changing camera view. A rendered frame
was opened and visually inspected. An earlier equivalent video frame was also
extracted and inspected to verify the VSE title overlay. CPU previews deliberately
use low samples; they are functional evidence, not final-quality artwork.

An authenticated loopback API fixture handled generation submission/status, GLB
and texture downloads, refinement export and upload. The received upload was
checked independently and provider credentials were absent from SQLite/WAL files.
This qualifies the generic adapter against a local fixture, not a diffusion vendor.

## GUI, packaging and skills

`python3 tools/gui_smoke.py /tmp/mb-gui-validation-v02` passed on the current display.
It launched a fresh GUI Blender through MCP, edited an object, saved/reopened the
project and retrieved a 640x480 viewport screenshot through protocol 2. That image
was opened and visually inspected. Session identity survived project reload; the
owned test process and broker were stopped. The retained directory contains the
project, screenshot, JSON evidence and Blender log. Host LLVM shader warnings did
not prevent rendering.

The pure-Python 0.2.0 wheel built without dependency downloads. All three skills
passed the skill-creator validator. The generated add-on bundle contains the worker
and stdlib-only broker dependencies, without FastMCP or Pydantic.

## Limits

Native Blender rendering still occupies its main thread; the broker stays usable.
Native blocking operations are not forcibly cancellable, and arbitrary Python
cannot be assigned a reliable storage estimate. Recovery preserves the completed
checkpoint, not edits after it, and does not imply rollback or power-failure proof.

Absolute shape-key animation, general external-cache bakes, arbitrary constraint/driver/NLA combinations outside the documented profiles, other Blender/platform versions,
long-duration workloads, external HTTPS deployment, Godot behavior and real
external generation services are not qualified by this suite.
