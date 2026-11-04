# Local validation: 0.2.0

## Durable validation progress and recovery cancellation — 2026-11-04

Vegetation LOD staged verification and broker-only recovery now forward the
canonical validator's detailed observations. Generic heartbeats retain the latest
detail; other file formats retain their existing generic heartbeat. Recovery
propagates `InterruptedError` as cancellation before the invalid-file handlers,
preserving stage/journal state and preventing publication on both dry reconciliation
and `publish=true` cancellation paths. This does not replay application edits.

Focused journal/progress/ownership, contract and storage checks passed **17 tests
in 6.71s**. Five new tests stub geometry verification to isolate callback forwarding,
heartbeat retention, callback-triggered cancellation, recovery publication and
cancellation with/without publication. Their stubs do not qualify geometry.
Native and broker-only regressions passed **14 tests in 84.61s**, including killed
writers, completed botanical/vegetation recovery with Blender closed, numeric and
nested-stage cleanup, late cancellation, guarded publication and dependency-free
add-on import. Geometry/selection/GLB proof algorithms are unchanged; the full-size
delivery qualification below precedes this observation-only change. These focused
checks are not a fresh full-project suite.

## Full-density multigrid vegetation LOD file delivery — 2026-11-04

The Python-disabled MCP delivery workflow passed **1 test in 1563.99s** from the
saved dense native project. Its three levels retain 88,704/70,000/60,000 leaves
and 1,176 branches each. Nine GLBs contain six wood/shoot assets and three shared
leaf templates; the template geometry occurs once. Expanded triangle totals are
17,457,216 / 13,791,232 / 11,831,232, not measured GPU workload or memory use.
The complete bundle is 184,327,467 bytes, of which 33,454,128 are GLB files;
the remainder includes explicit semantic tables and independent numeric witnesses.

Export plus staged verification/publication took 1031.38s. The source and native
profile guards stayed unchanged, and the durable journal reported published
ownership with the expected material binding. SOURCE placement omits the native
20m display offset. The test then removed both native LOD profile and original
tree and validated the files again in 449.67s, obtaining the same proof. This
recomputes canonical foliage, grid-independent nested selections and all quality
grids, and independently decodes branch/wind fields, ancestry, oriented triangles,
UV channels and metre placement. Native source files are not inputs to that
validator; the original saved project remains retained as an editable checkpoint.

Original procedural materials use PARAMETERS delivery with recorded conversion
limits. This fixture does not establish baked PBR/optical fidelity, filtered alpha,
shadows, animated LOD playback, far cards/impostors or an engine shader. Those
requirements remain open. Native and file proofs, renders, the three source-seed
projects and copied-file hashes are preserved in the ignored workspace under
`tmp/qualification/multigrid-20261104` for relocation.

## Independent vegetation LOD sampling grids — 2026-11-04

New plans use `AREA_PRIORITY_MULTIGRID_V2`: nested geometric-area/hash priorities
independent of raster positions, followed by BASE, finer and shifted coverage and
boundary gates. Native wood uses all grids and a frame including the complete
source trunk. The historical greedy results below describe the earlier method;
old bundles retain that exact verification path rather than being reinterpreted.

A retained 88,704-leaf canopy exposed the earlier method's sampling failure:
22,000 and 6,000 selected leaves passed with zero missing pixels at 64 pixels,
yet independently checking the same selections at 128 pixels found approximately
53–66% and 89–93% missing source coverage. Those profiles are not accepted as
quality-qualified dense delivery.

The new full-population pure probe used BASE 64, FINE 128 and SHIFTED 128 at the
same 1.5m margin and three views. At unchanged .25 loss limits, 60,000 leaves
passed every grid (maximum coverage loss .16627, boundary loss .17821).
50,000 leaves failed (maximum boundary loss .28020); 22,000 failed (maximum
coverage loss .62848). These are sampled opaque-blade metrics, not optical or
perspective equivalence. The projection admission was 146,893,824 triangles across
all grids; mask payload estimate was 85,936 bytes, excluding population/ranking
and general runtime overhead. The 60-million default is not silently increased.

An exact blade-bounding-box rejection optimization reduced this local pure probe
from 863.50s to 388.75s; the entire resulting plan dictionaries compared equal.
These are individual local runs, not a throughput guarantee. Focused tests check
grid-independent nested selections, fine-grid masks against the separate foliage
coverage analyzer, an adversarial coarse-pass/fine-fail fixture, work bounds and
the pre-change legacy plan's portable content hash. Native tests additionally
exercise bounded plan reuse, source/settings/budget invalidation, expiry and
creation without repeating projection. The affected bake, material, recovery,
chart-layout, adoption, quality-adoption and full mapped-delivery regression batch
passed **8 tests in 771.89s**. The larger 1024-pixel, 77-map quality delivery
passed **1 test in 1488.35s**, including eleven-role baking/adoption, source-file
removal, packed save/reopen, rendering, export and independent validation.
The Python-disabled MCP dense planning operation has separately completed with
70,000/60,000-leaf levels at unchanged .25 loss limits: worst coverage/boundary
losses .08719/.10502 and .16627/.17821. Combined leaf/native-wood projection
admission was 147,716,352; the streaming mask estimate was 70,948 bytes. This
700.08s run shared the host with downstream regression work and is not a speed
comparison with the pure probe. The dense native run reached semantic Text
creation after wood and instance verification, but repeated live stack inspection
located a prolonged native memory-copy path inside writing its single huge JSON
line. The owned fixture was explicitly interrupted after 1623.76s; this is not a
passed native lifecycle test. Bounded-line/chunked Text writing replaced that
unbounded insertion, with progress/storage and cancellation checks between writes.
The bounded-writer and native cache/cancellation gates passed **3 tests in
43.36s**. A native 88,704-record Text exceeding 10 MiB round-tripped exactly with
bounded lines; interruption immediately after a semantic chunk write removed all
staged LOD IDs and preserved the existing profile and source guard. Post-fix native
lifecycle/export and structured MCP lifecycle/export regressions passed **4 tests
in 247.71s**. Sampling, contracts, add-on packaging and dependency-free native
add-on import passed **8 tests in 37.27s**, with the existing Starlette/AnyIO
deprecation warning.

The corrected Python-disabled dense MCP workflow passed **1 test in 1151.29s**.
Planning took 433.04s and native creation 148.60s in that run. LOD0/near/mid retain
88,704/70,000/60,000 leaves and share three copied prototypes. Every one of the
218,704 native leaf instances was matched to its canonical variant/rest pose;
maximum position error was 1.90735e-6m and normalized linear-component error
6.54417e-7. All levels retain eight radial sides and all source wood; every wood
coverage/boundary/excess loss was zero on every grid. This does not qualify branch
pruning or cheaper radial geometry on this dense fixture.

Six fixed-camera 320x320, eight-sample Cycles renders (FRONT and ISOMETRIC, all
three levels) were opened and reviewed; every image is distinct. Original source
and Cube visibility were hidden for the comparisons and restored before saving.
The profile remained valid after save/reopen; the source's portable readback and
fresh guard remained intact through profile removal. The renders retain the
source study's overall crown, with sparse front-facing foliage; they do not close
the mature-oak habit/junction/material reference, optical/filtered coverage,
shadow, continuous-wind, distant-card/impostor or receiving-renderer requirements.
Dense native proof and image hashes are retained locally. Full-density GLB
delivery is qualified separately above. No packages, virtual environments,
installed runtime/services, installed skills, Godot or remote Git state changed.

## Complete mapped-profile coverage and mip-budget inspection — 2026-11-04

The final regenerated workflow gate passed 11 tests in 107.76s on local FreeBSD/
Blender 5.0.1, after the strength-aware emission correction. It covered the full
MCP profile workflow, source paths/claims/UV and encoding conventions, read-only
policy/discovery, capabilities and add-on import. A later six-test pure convention
gate passed in 7.25s, including unknown extra emission outside the required map set.
Earlier full-profile gates passed 1 test in 180.77s and 10 tests in 211.62s; their
initial render review found the emission bug described below. Final claims here
refer to the regenerated strength-aware assets.

The 5 m sparse fixture has four native LOD levels and three shared leaf templates:
eight wood/shoot components plus three templates. All eleven received seven maps
(BASE_COLOR/NORMAL/AO/ROUGHNESS/METALLIC/EMISSION/ALPHA), 64x64, two samples. Every
fixture source had zero emission strength; all final emission-map RGB maxima were
zero. The packed profile contains 137 owned IDs, exercising the capacity above
128. All temporary preparation and bake inputs were removed before save/reopen,
export, native profile removal and independent validation of all eleven assets.
Canonical hierarchy/fields, shared-template identity, original/bake UVs, material/
image inventories and source optical-loss records remained checked. Export
operation storage data reported free bytes and available space after reserve.

`inspect_vegetation_delivery` initially reported eleven missing components. After
adoption it passed an explicit 64-pixel/seven-map target with 1261568 source base
RGBA8 bytes and 1681988 bytes for full floor-halved mip chains. A 128-pixel target
reported all eleven resolution gaps; a mip limit one byte below the estimate
failed the budget. Pure tests cover non-power-of-two chains, partial coverage,
missing channels, and legacy emission convention gaps. Counts treat each source
component/map separately; exporter channel packing, compression, GPU allocation,
Blender caches and mip generation are outside the model. Inspection is read-only.

Additional MCP review rendered the full and most reduced levels at 320x256 with
eight Cycles samples and unchanged preview lighting before/after the emission fix.
The original white glow was traced to the bad emission maps; corrected previews
show brown bark and green leaves. Packed image inspection independently confirmed
black emission maps. Evidence under `/tmp/mb-full-profile-20261104` includes the
editable packed profile, delivery, coverage.json, both level PNGs/render operation
records and before-strength-fix views. Independent native inspection counted 137
owned IDs. The sparse, small-map fixture is not a realistic mature-oak or final
texture-quality qualification. The stronger default-size wood-UV case is documented
separately below and does not supply those missing visual claims.

Coverage `complete` means only expected components, required maps/resolution,
known emission convention and declared input-memory budgets pass. Physical
transmission/thickness, lightmap UV2, padding/filtering/texel density, front/back
lighting parity, animated/engine LOD behavior, population performance, cards/
impostors/collision and a mature-oak visual fixture remain open. No packages,
virtual environments, installed runtime/service changes, tags or pushes occurred.

## Strength-aware emission maps — 2026-11-04

Full-profile render review exposed unwanted white glow. Packed BASE_COLOR images
contained the expected bark/leaf colors, but EMISSION maps were white: the worker
baked Emission Color without Emission Strength and then delivered strength 1.
The worker now applies both constant and linked source strength to the temporary
emission shader. Its PNG8/sRGB output is tagged COLOR_TIMES_STRENGTH_PNG8; delivered
PBR strength 1 therefore reproduces that baked LDR emission rather than enabling
a disabled source. No HDR emission fidelity is claimed.

Two real-MCP tests passed in 60.05s: a new zero/constant/linked-strength case and
the existing seven-map high-to-low/GLB/render regression. The new fixture's
zero-strength map was black; bounded nonzero cases matched expected sRGB values.
A subsequent 28.74s emission test also verified that vegetation input adoption
rejects a missing convention without creating native IDs and restores its
negative-test manifest. New adoption records carry the encoding marker. Existing
records without it remain readable but are not newly adopted as qualified
emission maps. The initial bad full-profile previews were retained as before-fix
evidence; the whole profile is being regenerated and reviewed separately.

This corrects baking behavior; it does not modify source materials or repair old
saved pixels automatically. PNG8 clips/quantizes emission outside its LDR range.
No packages, venvs, installed runtime/service changes or pushes occurred.

## Scalable overlap inspection and bounded bake-chart repair — 2026-11-04

Seven local checks passed in 72.62s: exact broad-phase comparison with independent
all-pairs clipping, separated-row/long-triangle/touching/budget cases, existing UV
contracts, a deliberately folded native target and default-oak native preparation.
An earlier six-test focused gate passed in 8.35s before adding the default-size
regression. Grid bins and an X expiry sweep only reject provably separated
candidates; exact triangle intersection retains the same positive-area threshold.
Comparison-budget exhaustion still reports an incomplete result.

The default 14 m oak scaffold produced 1251 branches and 45616 wood corners. Its
old X-only sweep exhausted 200000 comparisons and also detected actual overlaps.
The spatial scan exposed 60 affected faces. Bounded new-chart isolation/repacking
produced a complete clear result in 72041 candidate comparisons, with nondegenerate
UV islands and the original tree guard/geometry/normals/attributes/authored UVs
unchanged. Native texture-bake inspection accepted the prepared target. Evidence
under `/tmp/mb-default-oak-uv-20261104` contains prepared.blend and proof.json.
This is a wood-UV/input qualification; it does not qualify a fully textured,
realistic mature oak, full foliage, motion, or receiving-engine rendering.

Development showed why repair must retain chart scale: fixed large charts plus
fractional margins could collapse the remaining layout. The final repair derives
regular chart area from each affected face's prior UV triangles and uses scaled
packing margins. Failed/intermediate layouts were refused. A native folded-quad
fixture verifies disabled-repair refusal, successful bounded repair and untouched
geometry/authored map. New charts allow at most two repair passes and 64 faces by
default, configurable up to 256; reused existing maps are never changed. Native
packing has a coarse cancellation boundary. Texel density, padding/filtering and
visual quality remain separate. No packages, venvs, runtime/service changes or
pushes were performed.

## Guarded vegetation texture replacement and source lineage — 2026-11-03

The final local FreeBSD/Blender 5.0.1 gate passed six tests in 72.96s: structured
replacement with native fault/resource probes, portable claims/path/UV checks,
native preparation regression and add-on import. An earlier four-test replacement
gate passed in 89.60s, and a focused native probe confirmed two-role replacement,
constant owned resource counts and retirement of all obsolete private images/
materials. These are bounded functional results, not population-scale benchmarks.

The MCP fixture disabled arbitrary execution, adopted leaf/reduced-wood maps,
then prepared the current leaf PBR with EXISTING BakeUV and private image/AO copies.
Structured IOR and multiplicative color-tint shader edits were refreshed and
self-baked. The new map's mean green channel was below 80 percent of the original
with unchanged UV coverage. Explicit replacement planning excluded the old maps
from the final texture budget while reporting old-plus-staged peak base RGBA8.
Inherited FRONT_PBR loss required acceptance even though the new source was simple
PBR. The resulting second revision retained previous/adaptation/sampling bindings.
The retained original preparation then restored the first verified map source as
revision three, with matching original base-color PNG hash and unchanged UV count.
Default replacement refusal remained active.

The final profile survived removal of preparations and all source bake directories,
save/reopen, GLB export and standalone validation after native profile removal.
The shared prototype, canonical hierarchy/wind attributes, original/bake UVs,
material inventories and inherited losses remained checked. Evidence under
`/tmp/mb-vegetation-revisions-20261103` contains tinted.blend, the restored
adopted.blend, delivery and pre-adoption actual worker inputs. Earlier evidence
remains under the adoption/preparation folders documented below.

Native tests injected failure after replacement swaps and restored exact IDs and
the old LOD guard. Replacements through revisions two and three kept the owned ID
count constant; fresh post-retirement guards matched returned guards. An external
material referencing an adopted image blocked replacement and profile removal.
Releasing the reference allowed private-resource cleanup while the independent
preparation remained valid. Cleanup verifies against the intended retired IDs
internally without relaxing normal public ownership checks. Remaining component
resource dependencies are retained; external users are never silently detached.

New optional version-one record fields bind source owners/revisions/ancestors,
previous adoption hashes and inherited losses. Schema checks reject unaccepted
inherited loss, missing previous revision bindings, invalid lineage and UV-channel
mismatches. Ownership inventories are bounded at 512 IDs to accommodate all
multi-level map resources; complete 512-ID/full-profile stress is not qualified by
these small fixtures. Original source/bake files are not automatically archived or
deleted. Peak estimates exclude other native/cache/driver allocations; physical
optics, full-profile quality, mipmaps, shadow/runtime behavior, cards/impostors and
collision remain open. Scene transactions do not provide crash/power-loss
atomicity or replay. No installs, venvs, runtime/service changes or pushes occurred.

## Reusable vegetation bake UVs and shader-source refresh — 2026-11-03

A four-test focused gate passed in 54.86s on local FreeBSD/Blender 5.0.1: the
code-disabled adoption workflow with revision preparation checks, native bake
preparation, and source policy/discovery checks. The adopted leaf's five packed
images and AO group were privately copied into a new preparation, reusing its
two existing UV channels without changing their hashes or adding a third. The
original LOD guard stayed unchanged during preparation, source edits, refresh
and copy cleanup. A structured IOR edit invalidated the preparation; a stale
refresh guard refused, and a fresh guard accepted the material source, incremented
its revision and changed the initial bake fingerprint. Existing original-source
adoption/export/removal and the native cancellation/rollback checks still passed.

An additional native refresh-refusal regression passed in 9.51s. A separate
native probe used the retained real adopted .blend, preparing both
leaf and reduced wood roles with ten independent packed images. Source LOD guard
and UV count were preserved; supported source edits refreshed while UV changes
refused. New preparations store complete component mesh and public-attribute
witnesses. Refresh cannot accept geometry, normals, original/bake UVs, numeric
fields, material-index or placement changes. Legacy preparations lacking those
witnesses must be recreated. Private source image/AO clones are distinguished
from existing unowned source images, which remain shared and are not deleted.

These controls qualify preparation and source revisions, not replacement of maps
already adopted into the LOD profile. Projection/atlas revision adoption, texture
quality, physical optics and runtime/mipmap/GPU budgets remain separate. Refresh
has guarded metadata rollback; it does not undo the user's earlier shader edits.
No packages, virtual environments, installed-runtime changes or pushes occurred.

## Guarded vegetation PBR map adoption — 2026-11-03

The combined local FreeBSD/Blender 5.0.1 gate passed nine tests in 96.68s:
structured adoption with native rollback probes, existing bake preparation,
seven-map high-to-low baking/GLB/render regression, source-path/claim/UV checks,
capability discovery and dependency-light add-on import. A subsequent three-test
pure gate passed in 8.59s; standalone revalidation of the retained five-asset
bundle also passed after adding the explicit encoded texture UV-channel check.
This validates a bounded static delivery workflow, not a finished mature-tree
asset or animated receiving-engine shader.

The MCP fixture disabled arbitrary execution, built a one-variant small tree and
near LOD, configured procedural bark/leaf detail, then removed the original tree.
It prepared and self-baked the shared leaf prototype and reduced wood component
(BASE_COLOR/NORMAL/AO/ROUGHNESS/ALPHA, 64x64, two samples). Optical-loss refusal,
a 4096-byte texture budget refusal and stale adoption guard refusal preserved the
profile. Explicit FRONT_PBR acceptance permitted the guarded batch. All ten map
inputs contributed 163840 bytes to the conservative base RGBA8 estimate. These
are small plumbing fixtures, not final texture quality or GPU-memory evidence.

Packed private images/materials and prepared UVs survived preparation removal,
deletion of both external bake directories, native save/reopen and export with
the default material mode. Both adopted components encoded normal and occlusion
textures. The bundle retained material/image inventories, optical-loss acceptance,
copy-only missing-UV sampling changes, canonical leaf IDs, branch/wind fields and
all original/target UV layouts. The full profile was removed and its files still
validated independently. Adopted UV records are checked against numeric corner
witnesses and decoded GLB textures must use the adopted channel. Source PNG hashes
do not assert byte identity after exporter channel packing/reencoding.

Native fault injection reused the actual worker outputs and pre-adoption .blend.
Cancellation after packing one component and a forced post-swap verification
failure restored exact native IDs, names, metadata and the original LOD guard.
Modified PNG bytes refused before staging. A supplemental native ownership probe also passed: an external material
referencing an adopted image blocked profile deletion. Removing that reference
allowed cleanup of both private baked materials and their resources while the
independent preparation remained valid. Hidden LOD objects may retain stale cached matrix_world values
on native file load; preparation/adoption now compose static parent channels,
including parent inverses, rather than relying on those hidden-object caches.
The existing sheared-placement preparation regression passed in the combined gate.

The standard worker and adoption share one explicit-UV PBR material recipe.
Its inert glTF AO socket group is accepted only with the expected interface,
nodes, no links and no animation. Native LOD ownership includes private baked
materials, images and AO groups; image content enters the profile guard. Source
materials remain shared/unowned. Export storage estimates include twice the known
adopted base-image budget in addition to geometry/semantics; they still exclude
unknown other native material images and are heuristics, not file-size bounds.
Actual output byte limits and storage checks remain active.

Evidence under `/tmp/mb-vegetation-adoption-20261103` contains adopted.blend, the
five-component delivery, and a pre-adoption snapshot with actual bake inputs for
reproduction. Scene adoption has cooperative rollback, not power-loss durability
or automatic crash replay. Existing adopted roles refuse replacement. Projection/
cage/atlas adoption, revision controls, full-profile texture quality, mipmap/GPU
budgets, physical thickness/transmission, shadow/optical parity, animated engine
LODs and cards/impostors/collision remain open. The unsigned source witnesses are
not authenticated provenance. No packages, venvs, installed runtime/service
changes or pushes were performed.

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

## Geometric texture quality admission

The read-only `inspect_texture_quality` and optional bake `quality` policy are
qualified on the installed FreeBSD Blender 5.0.1. Pure fixtures check analytic
directional density, rotated physical geometry, anisotropic sampling hidden by
area averages, reversed triangle winding, half-open shared-diagonal coverage,
subpixel charts, continuous segment distances, seeded broad-phase agreement
against all-pairs distances, work exhaustion, overlap refusal and mip padding
failure. Contract checks cover dimensions, finite thresholds, bake-margin
compatibility and read-only discovery.

An MCP fixture with arbitrary Python execution disabled creates a plane and
material, rejects a 32x32 texture policy at 16 texels/metre, and accepts a 128x128
policy at 64 texels/metre. It checks stable report witnesses, tile-edge padding
failure, incomplete raster work, no output directory on refused bake admission,
and distinct guarded fingerprints with the policy present. A real isolated
base-color/normal bake retains the quality report, preserves the live source,
and reopens as a validated bundle. Native fixtures check read-only geometry/ID
preservation, equivalent metre/centimetre scenes, nonuniform stretching and
affine placement. The generated add-on imports the inspector with FastMCP and
Pydantic deliberately blocked.

Retained `/tmp/mb-texture-quality-20261104/` evidence includes the actual bake,
admission proof and an additional read-only inspection of all eleven textured
components from the existing four-level vegetation profile. At 256x256, minimum
density 32 texels/metre, two pixels of padding and mip levels 0–2, every component
completes inspection but fails the chosen policy. Wood minimum directional
densities range approximately 12.30–16.33 texels/metre; narrow shoots lose chart
coverage and all components touch a tile edge. This confirms that the older
complete map/resolution/budget inventory is not a geometric quality certificate.

The combined targeted gate passed 18 tests in 88.35 seconds, including existing
emission baking, native add-on import, capabilities and UV overlap regressions.
Both bundled design/render skills pass their schema validator.

These are pixel-centre geometry samples and continuous inter-chart/tile-edge
distances, not measurements of Cycles dilation, generated mip image quality,
self-padding within one chart, HDR/material optics, target-engine filtering or
visual maturity. Existing prepared layouts are not automatically modified.

## Pixel-based chart allocation

Optional `chart_layout` on UV packing and NEW vegetation preparation allocates
bounded pixel rectangles with area/mean-span floors, gutters and tile borders.
Pure tests check deterministic layouts, unmodified inputs, float32 area/border/
spacing readback, preserved pixel aspect without stretching, explicit stretch
for an otherwise unplaceable sliver, count/interior refusal and cancellation.
A code-disabled MCP fixture separates two overlapping source charts, refuses an
oversized allocation without isolating shared data, preserves geometry and its
sibling, passes density/coverage/two-pixel padding at base and mip 1, and retains
its UV guard after save/reopen (one test passed in 12.49 seconds).

A native fresh seeded 5 m tree fixture creates four LOD levels and three shared
leaf templates, with procedural bark/leaf materials. NEW preparation uses a
1024x1024 pixel layout, minimum area 64, mean span two, four-pixel per-side
gutters, eight-pixel outer border and explicitly allowed chart stretching. Every
wood/shoot/template component passes the independent geometric quality policy:
minimum 32 directional texels/metre, four chart pixel-centre samples and two
pixels of padding at base and mip 1. The eleven reports have minimum directional
density approximately 49.18 texels/metre, minimum mip-1 coverage twelve pixels,
and minimum mip-1 tile-edge margin approximately six pixels. Seven roles use
some anisotropic chart allocation; all three leaf templates preserve their chart
aspect ratios. Geometry, normals, original UVs and numeric attributes satisfy
the existing exact preparation witnesses, and the source LOD guard is unchanged.
A max_charts=1 refusal leaves the original ID inventory unchanged. Save/reopen
preserves valid preparation ownership/content. This test passed in 111.23 seconds.

`/tmp/mb-chart-layout-20261104/profile/` retains `quality.json` and the editable
`prepared-profile.blend`. An earlier three-role probe shows that 512-pixel wood
coverage/spacing can pass while physical density remains below 32; 1024 resolves
that density requirement. The native add-on dependency/import, default-attribute
and targeted contracts/math gate passed eleven tests in 15.63 seconds. These
checks qualify layout geometry on FreeBSD Blender 5.0.1, without claiming actual
new image bakes, normal-map transfer, mip image filtering, mature-oak appearance,
large populations or receiving-engine behavior. The shelf method is a bounded
heuristic, not an optimal packing proof; mean width is not minimum local width.

## Retained quality through vegetation adoption

Quality-bearing self-bakes carry canonical source inspection content. Removing
only the quality report reproduces the unchanged preparation fingerprint; the
full content reproduces the policy-bearing bake fingerprint. Pure tests check
compatibility with the original fingerprint recipe, missing/altered witnesses,
policy/dimension/margin inconsistencies, failed or incomplete chart/mip/density/
padding claims, portable report/map-size correspondence, legacy delivery behavior
and the optional report requirement, including scene-unit changes.

The structured integration fixture uses a seeded 5 m source, two native LOD levels
and three shared leaf templates. It prepares wood and one leaf template with a
pixel border, then actually bakes three maps each at 1024x1024 under minimum
32 texels/metre, four chart pixels and one-pixel padding at base resolution.
It verifies altered source-content refusal before native mutation, guarded
adoption, optical-loss retention, reports in packed native records, cleanup of
the preparation and original bake directories, save/reopen and independently
validated numeric/GLB delivery after the native profile is removed. Other roles
remain unchecked and keep the full-profile report incomplete. Base-only success
does not qualify mip 1 or full-profile visual quality.

Retained source-profile probes at 256, 512 and 1024 pixels complete geometric
inspection but expose narrow wood/shoot chart coverage and leaf mip-gap failures.
These are evidence for chart allocation/spacing work, rather than acceptance
based only on higher image resolution. The probes and successful delivery
fixture are kept under `/tmp/mb-quality-adoption-20261104/`. The integration test
passed in 338.08 seconds: wood measured about 63.29 directional texels/metre and
at least six covered pixels per chart; the leaf template measured about 8156.24
texels/metre and at least 105 pixels. Both had at least sixteen base pixels of
tile-edge space. Six adopted maps total 24 MiB of base RGBA8 input estimates.
The remaining five roles are explicitly unchecked. The native legacy adoption/
replacement, ordinary quality bake and dependency-free add-on regressions passed
four tests in 150.05 seconds; the final focused pure gate passed twelve tests in
10.47 seconds. Both bundled design/render skills remain schema-valid.

## Dense default face attributes during preparation

Re-preparing an already textured component with NEW UVs can make Blender's
BMesh operators omit its dense all-zero `material_index` attribute. Preparation
now restores that exact default representation alongside default sharp layers
before comparing all source attributes. Nonzero indices remain subject to the
ordinary preservation check. A native complete preparation fixture, using a
static source resolver, proves dense zero-index retention, source preservation
and owned cleanup (one test passed in 6.30 seconds). A read-only retained-profile
probe subsequently prepared leaf, shoot and wood copies without the previous
attribute refusal. This does not qualify their texture quality: increasing
resolution still leaves narrow chart coverage and mip-gap failures.

## Explicit UV tile borders

`pack_uv_islands` accepts an optional pixel border at declared texture dimensions.
Analytic tests cover unequal texture axes, uniform aspect-preserving shrink,
translation without density changes, float32 border verification, invalid
interiors, zero-option compatibility and refusal when a fixed-scale layout
cannot fit. A real structured MCP fixture starts with shared plane data: failed
fixed-scale packing preserves both the original coordinates and sharing; an
explicit single-user scaled pack reserves four pixels at 128x128, leaves the
sibling untouched and preserves geometry. The result passes the geometric
quality gate with two pixels of padding at mip 1, survives save/reopen and later
supports fixed-scale packing of a smaller normalized layout without changing
its density. Existing UV unwrap/density/GLB/render and overlap controls also run.

This is tile-edge reservation only. Post-pack shrinking can reduce internal gaps
and density, and does not certify those or actual filtering. Direct UV edits do
not accept or refresh managed vegetation preparation witnesses.
The same inset is available at NEW vegetation preparation time, bound into its
plan and frozen mesh witness. EXISTING layouts refuse nonzero padding. The
default 14-metre, 1,251-branch wood fixture exercises chart repair followed by a
four-pixel border at 1024x1024, complete clear overlap inspection, original source
preservation and native save. It is a UV qualification, not a mature textured
canopy or filtering qualification. The UV contract/editing/quality gate passed
12 tests in 164.25 seconds; the added padded preparation and contract gate passed
five tests in 72.43 seconds. The bundled design skill remains schema-valid.

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

## Slow control observations

The 77-map qualification run completed all texture workers but hit a five-second
control observation timeout during native adoption. The test harness then stopped
its owned application; this was not evidence that adoption itself had failed.
The saved preparation and every successful bake bundle were retained for resume.

Frontend status/get-operation/list-operation reads now retry a timed-out exchange
up to three times using the same request, without treating timeout as evidence to
restart the broker/application. Existing disconnect reconciliation remains.
Mutation control timeouts do not gain this retry path, and semantic errors are
returned immediately. Synthetic timeout/error injection and existing operation
regressions passed thirteen tests in 16.44 seconds. This is bounded observation
resilience, not a guarantee against prolonged host/storage stalls or a diagnosis
of the underlying stall. Clients must retain the operation ID after exhaustion;
a timeout still does not imply terminal operation state.

## Bounded native image ownership signatures

Resuming the full 77-map adoption exposed a real memory failure: the OS killed
Blender for failure to reclaim memory. Native ownership hashing had accumulated
all writable RNA image-pixel arrays as Python lists, then serialized the entire
graph. The metadata image inventory was only about 18 MiB on disk; that did not
represent the decoded/Python working set. A process sample exceeded 5.5 GiB RSS
before death, and the kernel identified the killed owned fixture PID.

Legacy graph signatures now hash the identical canonical JSON array one data
block at a time. Tests prove byte compatibility, release of prior generated
records before requesting the next, nonfinite rejection and continued pixel-edit
detection. A retained legacy eleven-component profile still validates unchanged.

New vegetation LODs/preparations use content_signature_version=2; successful map
adoption upgrades a verified profile to that version. Packed-image records hash
encoded bytes, dimensions, color space, ordinary properties and custom ownership
without materializing pixels. Dirty/unpacked/nonstatic images are refused. Legacy
snapshots remain readable through the streamed version-1 path; unsupported
versions refuse validation. Material image guards and native reference checks
remain in force. Image-specific tests verify that the compact path excludes pixel
properties, rejects dirty buffers and detects changed repacked content.

The focused legacy/compact image, default-attribute, adoption/replacement and bake
preparation gate passed six tests in 77.27 seconds. Final image/digest/add-on checks
passed four tests in 14.06 seconds. The full retained 77-map case subsequently
adopted, saved/reopened, exported and independently validated; a process sample
during previews was about 966 MiB RSS. This sample is not a measured peak or a
general memory bound for rendering; legacy verification still needs one complete
data-block record and native image caches.

## Full quality-bearing texture delivery and render review

```sh
MCPBLENDER_TEST_BLENDER=1 MCPBLENDER_FULL_QUALITY_EVIDENCE_DIR=/tmp/mb-full-quality-final-20261104 python3.11 -m pytest -q -s tests/test_vegetation_quality_full_delivery.py
```

The uninterrupted run passed in 680.34 seconds with arbitrary Python execution
absent from the MCP tool surface. It creates a fresh procedural five-metre tree,
four native LOD levels and three shared leaf templates, prepares every role with
the pixel chart allocator, and actually bakes all seven maps for all eleven
components at 1024x1024, four samples and two-pixel margin. Every self-bake carries
the same declared quality policy: minimum 32 directional texels/metre, four chart
pixel-centre samples, two pixels of padding and mip levels 0–1. Source/preparation
witnesses remain unchanged through baking. All eleven emission maps are black
for the non-emissive source materials.

The guarded batch adoption and `require_quality=true` delivery inspection both
pass. The input estimate is exactly 322961408 base RGBA8 bytes (308 MiB) and
430615108 full-mip bytes (about 410.67 MiB), within explicit 384/512 MiB budgets.
No quality-report, scene-unit, map or resolution gaps remain for this fixture.
The test removes preparation and original bake directories after packing,
saves/reopens the project, exports every component, removes the native profile
and independently validates all eleven exported assets and semantic witnesses.
The final retained library occupies about 34 MiB on disk; this is not a runtime
memory measurement. Recorded free temporary storage remained above 8.95 GiB.

Four 384x384 Cycles previews were opened and visually reviewed: leaf detail with
and without its baked normal link, plus LOD 0 and LOD 3 at the same camera. An
independent RGB decode found 15854 changed pixels among 147456 in the leaf
comparison, mean absolute channel difference about 0.089/255 and maximum 33/255.
The normal effect is subtle under this lighting, while the baked normal image
itself shows vein detail. The whole-tree previews show bark texture and sparse
foliage; LOD 3 visibly loses foliage. These are functional renders of a young
scaffold, not mature-oak visual acceptance. The explicit FRONT_PBR optical
omissions and copy-only missing-UV fallback remain in the delivery report.
Per-component self-bake AO excludes other canopy components and cutout-aware
occlusion; no physical thin-leaf parity, deep-mip filtering, generated mip image
chain, large population, animation or receiving-engine qualification is implied.

`/tmp/mb-full-quality-final-20261104/` retains operation/storage observations,
per-role bake proof, `library/prepared.blend`, packed `quality-profile.blend`,
quality report, four PNG previews, `visual-review.json` and standalone delivery.
Earlier attempts and the successful retained-checkpoint resume remain separate.
Optional `MCPBLENDER_FULL_QUALITY_RESUME_DIR` points to a retained prepared library
with already successful matching bundles; it verifies their source/report/file
bindings before adoption without replaying texture workers. This is not automatic
replay after an observation timeout. The resumed post-fix path passed separately
in 70.88 seconds. All fixture-owned applications and brokers were stopped; no
installed runtime or service was changed. Both bundled skills validate.

## Bounded assembly image graph guards

Assembly current guards now use graph signature version 2. Image records exclude
writable pixel arrays, hash clean packed bytes or saved external bytes in bounded
chunks, and snapshot clean generated-image parameters. Dirty image edits block
copying/guarded use until the image is saved or packed. External files remain
shared dependencies; hashing does not force cache reload or freeze them. Fixed
limits are 64 megapixels per image, 512 MiB per encoded file and 2 GiB of encoded
inputs per graph. The existing geometry/dependency/shape/action bounds remain.

The graph digest streams one record at a time. Tests compare its exact JSON/hash
against an eager reference and prove previous records are released before asking
for the next. An initial test caught `enumerate` retaining the previous yielded
record; the hasher now avoids that retention.

A native fixture creates seven packed 1024x1024 images, prevents any generic image
pixel-property traversal, then copies its textured object into a prototype and
places two shared instances. It proves source/prototype image independence,
dirty-edit refusal before mutation, changed/repacked source guards, generated
parameter support, external byte changes without cache reload, missing/dynamic
input blockers, per-file/aggregate bounds, save/reopen and unchanged instance
bounds. Limit refusal uses reduced constants, not actual multi-GiB allocations.
Additional cases change an external file while hashing and reference a FIFO from
an already cached image; racing input is refused and nonregular open does not
block. Focused checks passed six tests in 9.32 seconds, followed by three final
image/digest checks in 7.00 seconds. The final focused contract/capability/image/
hash gate passed eight tests in 18.20 seconds.

Existing code-disabled textured-building/render/reopen and skeletal/shared
prototype tests, nested native graph copying, realization and add-on packaging/
import regressions passed seven tests in 53.37 seconds. The generated add-on
includes the stdlib graph hasher and imports it with frontend dependencies blocked.
An independent read-only probe opens two pre-upgrade projects retained under
`/tmp/mb-assembly-20261103/`: all three saved prototypes validate, their historical
metadata is unchanged, and current guards use version 2 with historical source
version 1. Probe evidence is `/tmp/mb-assembly-images-20261104/legacy-proof.json`.

Current guards intentionally change once after this upgrade; callers reinspect
rather than replaying old expected guards. Newly created prototypes record their
source-signature version, while old metadata keeps its original source SHA.
Native decoding/cache allocations are not bounded by the Python streaming
working set. This is current content/provenance qualification, not shader/optical
or receiving-engine equivalence. The bundled design skill remains schema-valid.

## Translation-independent UV measurements

A native before-fix probe measured a 2x2 plane correctly at the origin (area four
square units, 64 texels/metre at 128x128), then reported zero area/density and
refused bake admission after moving it to (100000000,100000000,100000000).
The float32 world-point multiplication erased edge differences before subtraction.
`uv.layout` and geometric quality now subtract local triangle coordinates in
Python double precision, transform the differences by the evaluated linear
matrix, and apply physical scene units for the quality policy. Global translation
does not participate in triangle area or directional density; full placement
continues to participate in source/UV/quality fingerprints.

Pure fixtures cover large local origins, reflection, shear, physical units,
degenerate edges and nonfinite refusal. Native fixtures check parent nonuniform
scale/rotation with child rotation (inherited shear), equivalent metre/centimetre
metrics, near/far equality, read-only ID/mesh preservation and exact collapsed
geometry rejection. A code-disabled MCP fixture verifies area/density and bake
admission at the large offset, changed placement guards, and guarded UV density
normalization preserving local geometry. Nine focused checks passed in 33.61
seconds. Before/after evidence is `/tmp/mb-uv-precision-20261104/`: after the fix
both placements report area four, density 64 and supported admission.

This qualifies geometric measurement and admission diagnostics, not an actual
bake/render/physics/export at the distant location. It cannot restore precision
already lost in Blender's stored local coordinates or evaluated linear matrix.
Existing actual quality-bake/UV-editing/vegetation preparation and baking
regressions passed seven tests in 127.70 seconds at their ordinary placements. The bundled design skill remains schema-valid.

## Guarded secondary UV authoring

`create_secondary_uv` is qualified for ordinary base meshes with an existing
primary map. A code-disabled MCP fixture isolates a shared, nonuniformly scaled
box, creates UV2 with pixel chart allocation and a tile border, preserves the
sibling and primary active/render map, then checks geometric density/padding at
256x256. Save/reopen retains the UV guard. A static numeric-field bundle is
exported and independently decoded: both UV channels, corner correspondence,
geometry and placement match their witnesses. This verifies encoded data rather
than relying on the UV2 name or Blender's layer count alone.

Native checks preserve exact prior UV arrays, seams, vertex selection, local
coordinates, shape-key data and a distinct active versus render map. Cancellation
before publication leaves the source and native ID inventory unchanged. Missing
primary maps, stale guards after another channel is renamed, managed ownership,
and ninth-channel creation are refused. Read-only MCP discovery hides the edit
tool; typed contracts reject invalid projection, scale and border inputs.

This is not receiving-engine lightmap or per-instance atlas qualification.
Secondary authoring on managed botanical masters/profiles, alpha-aware baking,
actual mip generation/filtering and deformation-dependent lightmaps remain open.
The channel inventory reports Blender indices; exported channel meaning must be
verified for the chosen exporter/consumer. UV guards now include ordered map
names, so clients must reinspect older guards. Twelve existing/new UV, chart,
precision and contract checks passed in 119.94 seconds; the bundled design skill
validated and source compilation/whitespace checks passed.
The final ordinary-pack and pixel-layout secondary fixtures both passed in
19.68 seconds. The ordinary path uses native AABB packing: adding Blender's
exact concave repack exceeded the 120-second native test bound on the small
shape-key fixture. Bounding-box packing completed while retaining complete
clear-overlap verification; no timing or scalability bound is claimed for
arbitrary larger meshes or native projection calls.

## Owned vegetation secondary UVs

`create_vegetation_secondary_uv` qualifies new secondary layouts on explicit
native LOD delivery roles. A code-disabled MCP fixture creates a procedural tree,
one reduced woody LOD and a shared leaf variant, then performs a real four-map
64px leaf bake and guarded adoption. A two-role secondary edit preserves the
historical adopted record verbatim, the unchanged preparation, source master,
geometry and primary map choices. A subsequent EXISTING-UV preparation, real
rebake and replacement adoption retains the new map and secondary records.
Save/reopen and independently decoded GLB delivery prove three leaf UV channels
and two woody UV channels. File validation still succeeds after profile removal.
The complete new MCP workflow passed in 65.38 seconds.

Native batch tests inject cancellation after staging the first mesh and after
actual mesh swaps, metadata publication and new ownership verification. Both
restore the exact old metadata, ID inventory and profile/source guards. They
also verify repeated append-only authoring, raw-edit refusal on owned data,
foreign-user refusal and detection of a changed coordinate witness even when its
record digest is recomputed. The native test, add-on import without frontend
dependencies, read-only tool discovery and pure record checks passed five checks
in 14.80 seconds. Portable record tests cover channel ordering, baseline lineage,
intervening appended bake maps, malformed records and altered numeric witnesses.

The quality-adoption fixture additionally adds secondary UVs to a leaf carrying
actual quality-gated 1024px maps, preserving its historical quality and bake
records exactly. Its exporter/validator accepts the added map only through the
separate secondary record and checks that the baked textures still reference the
adopted channel. This fixture plus existing texture replacement/ancestry/rollback,
native LOD lifecycle, placement modes and file-export cancellation regressions
passed four checks in 199.47 seconds. The design skill validates; compilation and
whitespace checks pass. No permanent runtime, environment or dependency changes.

These are five-metre sparse source fixtures, not a mature-tree, full population,
per-instance lightmap atlas or receiving-engine lighting test. New secondary UVs
need their own density/padding inspection; retained bake-quality policies describe
the original texture layout only. Old preparations lacking the new map are
refused for replacement adoption; use a fresh preparation rather than silently
losing UVs. Managed master UV editing, whole-tree/per-instance atlases, lighting
bakes, actual mip/filter/optical behavior and abrupt-crash transaction recovery
remain unqualified. Cooperative native cancellation is observed between native
projection/packing calls, not during those calls. Portable records and manifests
are unsigned correspondence witnesses, not authenticated provenance.
The final default-AABB append, malformed native metadata and portable-record
checks passed three tests in 8.30 seconds. An empty list used in place of the
secondary-record mapping is refused rather than treated as an absent record.

## Authored secondary UVs on procedural botanical masters

A code-disabled MCP fixture authors UV2 on a five-metre master's wood and shared
leaf template without changing canonical growth data or primary sampling. An
identical regeneration preserves exact recorded UV witnesses. A changed-height,
changed-seed regeneration with default PRESERVE refuses and leaves the original
master guard unchanged; explicit REPROJECT produces a valid new layout/baseline.
Save/reopen retains those records. The independently decoded master bundle
verifies two UV channels on wood/leaves and zero on unparameterized shoots.

Native LOD creation inherits exact maps and master records on unchanged LOD0
wood and shared templates; the reduced wood retains its original BarkUV and gets
its own guarded secondary layout through the LOD tool. Both master and LOD bundle
validators still succeed after source removal. Default foliage removal refuses
when it would lose an authored leaf role; explicit DISCARD removes the foliage
and all master secondary layouts. This complete MCP workflow passed in 46.47
seconds. It qualifies encoded coordinate correspondence, not engine lightmap use.

Native fault tests cancel after the first master mesh is staged and after the
new UV mesh bindings and content metadata are verified. They also cancel both
PRESERVE and REPROJECT regeneration at public-name handoff before final deletion.
Every failure restores original ID inventory, names, metadata and tree guards.
Recomputed record hashes cannot conceal mismatched actual UV coordinates. These
checks, owned-LOD secondary rollback/repeated append, add-on import without
frontend dependencies, existing master/foliage lifecycle and complex-placement
regressions passed seven tests in 63.51 seconds. Pure policy/model/discovery,
portable-record and canonical-interchange tests passed six in 9.51 seconds.

Master records use their own format/source-tree guard while sharing float32 UV
witness validation with owned LOD delivery. Original bare/foliated bundle formats
remain readable with no optional secondary records. Compatible preservation
requires identical local geometry and original UV baselines; pose/physical-unit
changes still require renewed density/padding inspection. Reprojection runs the
saved structured settings on fresh canonical geometry; its numerical layout is
new. Missing authored roles refuse unless DISCARD is explicit. No policy bypasses
canonical-model or discard_derived_edits protections.

The fixtures do not qualify a mature oak, dense canopy/population, unique
per-instance/whole-tree lighting atlas, lighting bake, filtering/mips/physical
optics or receiving-engine behavior. Cooperative rollback is qualified, including
a late handoff; hard-crash rollback at native deletion remains unqualified. Keep
the editable project, review actual layout quality after changes, and supply
separate secondary maps for reduced geometry rather than transferring coordinates
across different topology. The bundled design skill is schema-valid.
Existing real PBR bake/rebake/adoption through the shared staging helper, legacy
bare/foliated and LOD export placement/cancellation, and the rendered three-seed
master regeneration workflow passed four regressions in 194.49 seconds. No
installation, dependencies, service configuration or installed skills changed.
The final native master rollback and saved-setting/record/policy/discovery checks
passed five tests in 10.20 seconds. Master records require saved projection
settings that agree with the declared map and texture dimensions.

## Dense canopy study preset and larger reference sources

`OAK_CANOPY_STUDY` version 1 integrates the existing canonical oak generator,
dense shoot/leaf recipes and native procedural bark/leaf surfaces. It creates an
ordinary editable master with three shared leaf templates. Planning exposes
model/foliage guards, counts, stored/expanded geometry and explicit budgets.
The new create tool uses the preset guard and preserves existing IDs/materials;
cooperative cancellation removes only newly created data. This is an artistic
study profile, not biological or complete game-asset certification.

The code-disabled MCP fixture creates seeds 1/2/3, renders front/back/right/
isometric plus a sun-only backlit view for each, saves projects, verifies framing
and reopens the final saved source. It passed in 514.38 seconds. The 15 PNGs and
three editable projects are retained under `/tmp/mb-canopy-preset-20261104/`.
Each image was viewed. Whole-tree 320px views show fuller crowns than the sparse
control, but angular/intersecting sleeve branches and strong bark contrast remain
visible. The backlit images are too dark to establish transmission quality.
Dedicated sky/exposure and macro front/backlighting remain required.

| Seed | Leaves | Stored triangles | Conservative canopy top, m | Front coverage | Side coverage | Top coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 92,136 | 75,048 | 14.94 | 56.58% | 62.44% | 77.68% |
| 2 | 90,288 | 73,396 | 15.25 | 56.39% | 59.88% | 78.91% |
| 3 | 88,704 | 71,820 | 14.86 | 56.05% | 59.99% | 74.15% |

Coverage is a separate CPU opaque-blade triangle/pixel-centre measure at 128px,
fixed declared-crown frames and 1.5m margins; no frame clipped. Model/foliage
hashes match the actual MCP-created presets. The seed-1 default control has
20,940 leaves and 19.74%/21.64%/35.58% front/side/top coverage at the same settings.
Seed-1 default/dense measurements took 66.00/343.92 seconds; dense seeds 2/3 took
440.47/406.99 seconds while other qualification ran. These are workload records,
not isolated performance benchmarks or render-opacity/overdraw estimates.

A fresh native process independently reopened all three saved projects, verified
master guards and counted actual mesh triangles and point/template inventory.
The first has 24,204 wood + 50,256 shoot + 3x196 template triangles, agreeing with
the plan. Expanding its leaves would yield 18,133,116 total triangles; the native
source retains sharing. `setup_preview_stage.asset_world_bounds` reports the
conservative evaluated geometry/instance boxes in Blender world units. These
fixtures use scene unit scale 1 and base Z=0; the 14m recipe describes wood, not
the added foliage's complete extent. No GPU memory, draw-call or frame-time claim.

Full-size preset fault tests cancel both before master completion and after
surface/content verification before handoff. ID inventory/names and a preexisting
same-named bark material remain unchanged; stale guards refuse without native
allocation. Successful native readback verifies 92,136 point carriers, three
prototypes and Instance-on-Points without Realize-Instances. Native rollback,
add-on import without frontend dependencies and export-job packaging checks
passed five tests in 224.40 seconds. Pure recipe/determinism/budget/default-surface
and discovery tests passed three in 57.09 seconds; readonly policy regressions
passed three in 7.63 seconds. No environment, package or installation changes.

Run the larger source fixture explicitly with `MCPBLENDER_TEST_BLENDER=1
MCPBLENDER_TEST_CANOPY=1` and `tests/test_botanical_canopy_workflow.py`; set
`MCPBLENDER_CANOPY_EVIDENCE_DIR` to retain its outputs. The seeded delivery fixture
uses `MCPBLENDER_CANOPY_SOURCE` pointing to that retained `Canopy1.blend` (siblings
Canopy2/Canopy3 are used by their parametrized cases). Its export instance limit
is supplied explicitly from the source count, preserving shared templates rather
than realizing a complete leaf population.

The full mature-oak milestone remains open: plausible close-up junctions and
habit, controlled lighting/shadows/physical optics, texture filtering/mips,
wind playback at this density, near/mid/far/collision representations and the
1000-tree workload are not established here. Godot/custom-renderer adapters and
GPU qualification remain outside this Blender-only evidence.

All three larger sources also passed shared-template GLB/semantic delivery via
MCP with code execution disabled and explicit instance budgets. The first case
passed in 141.05 seconds; seeds 2/3 passed two cases in 363.06 seconds. Each export
matches every native leaf rest instance, independently decodes five mesh assets
(wood, shoots and three templates), preserves the source guard, then validates
the files again after guarded source removal. Logical bundle sizes are 81,279,326,
79,459,585 and 77,801,576 bytes; no leaf population was realized into mesh output.
Native instance orientation/scale component differences remain below 6.6e-7 in
the recorded comparison; position comparisons reported zero at that check's
float32 precision. This is geometric/numeric correspondence, not shader parity.
The supplied procedural material graphs still need portable PBR baking/review.

Retained delivery evidence is `/tmp/mb-canopy-delivery-20261104/`, with
`delivery-summary.json` and per-case export proofs. The source study's minimum
observed free output storage was 9,425,666,048 bytes; its operation journal records
reserve and free/available space. This is an observed minimum at polling points,
not a filesystem or peak-memory guarantee. No GPU qualification was performed.

Final recipe/budget/discovery checks passed three tests in 35.47 seconds,
including a whole-asset cap just above leaf-only triangles that now refuses
before leaf-record allocation. The cap includes wood and shoots as well as
leaves. New preset planning/creation advertise wait=false by default; existing
commands retain their defaults. The final readonly/schema compatibility check
passed without requiring Blender startup. All owned Blender fixtures stopped.

## Structured World lighting and material close-ups — 2026-11-04

Stock FreeBSD Blender 5.0.1 now has typed COLOR, atmospheric SKY and static
packed HDRI authoring with arbitrary Python execution disabled. Catalog and
inspection remain available to read-only callers. Configuration isolates the
current scene, verifies a bounded static World graph/image signature and checks
sharing before replacement. Installed SKY AUTO selected MULTIPLE_SCATTERING;
legacy NISHITA was not assumed to exist in this Blender build.

`tests/test_environment_native.py` and `tests/test_environment_contracts.py`
passed three tests in 13.16 seconds after the final admission/inspection changes.
They exercise late cancellation with exact binding/film/fake-user/ID restoration,
shared-scene isolation, sharing-count and film stale-token rejection, retained
user-edited graphs, unchanged managed-data retirement, mist-setting preservation,
animated/object-dependent refusal and packed FLOAT EXR save/reopen after source
removal. Header checks cover PNG/JPEG/Radiance including CRLF/scanline EXR,
unsupported multipart admission, byte/pixel budgets, nonblocking FIFO refusal,
finite typed limits, library boundaries and read-only discovery. These are
bounded admission checks, not full media-codec validation or a security sandbox.
Compositor contract/native rollback and add-on import without frontend
dependencies passed four regression tests in 20.64 seconds.

`tests/test_environment_workflow.py::test_sky_leaf_transmission_bark_and_packed_hdri`
passed through MCP with code execution disabled in 111.45 seconds. Synthetic EXR
input media was prepared outside MCP; all scene editing used typed tools.
Eight Cycles renders cover leaf front/reverse optics, default/finer procedural
bark and HDRI rotation/reopen. In 17,712 common opaque leaf pixels, reverse-side
mean green was 187.07 with transmission and 24.94 without it. This measures the
saved display pixels under these settings, not physical leaf transmission.
The two bark images differ by mean absolute RGB 21.61 in their common opaque
pixels. Both remain stylized, as direct image inspection confirms. Rotating the
HDRI 180 degrees changed a background sample from [236,143,133] to [136,156,229].
Deleting the input EXR, saving and reopening produced identical decoded render
pixels. This establishes relocation/rotation in this fixture, not calibrated
radiance, arbitrary image-format compatibility or cross-engine optical parity.

The optional retained-canopy test uses `MCPBLENDER_ENVIRONMENT_CANOPY_SOURCE`
pointing to an existing Canopy3.blend, avoiding a repeated large source build.
It loads 88,704 shared leaves, disables existing scene lights, configures SKY,
frames/renders through tracked operations and checks the botanical guard remains
unchanged. The initial single-view case passed in 61.20 seconds. Its exposure-zero
backlit view was brighter but visibly washed out, prompting the targeted
exposure/front-light comparison recorded below. None of these views establish
mature-oak habit, close-up junctions, physical optics, distant texture filtering,
full-density wind, shadow delivery, GPU performance or the 1000-tree workload.

Evidence is `/tmp/mb-environment-20261104/`: macro/HDRI images and editable
projects in `library`, display-pixel checks in `pixel-proof.json`, full-canopy
images/projects in `canopy-library`, and operation/storage journals. The checked
input/output free-space reports are polling/checkpoint observations, not peak
memory or complete project-save reservations. Fixtures own isolated background
instances and stop them on exit. No packages, virtual environments, installed
runtime/skills, services, user GUI sessions or engine adapters were changed.

The final expanded retained-canopy case passed in 63.63 seconds. Three 320-pixel,
16-sample Cycles views compare sky backlighting at exposure 0 and -2 stops, then
front lighting at -2 stops (sky rotation 180 degrees). All images were actually
viewed. Lower exposure improves the backlit contrast; front lighting makes the
procedural trunk and green leaf distribution easier to inspect. The botanical
content guard remains unchanged; the saved project retains the final sky and
exposure settings. Foliage still reads as an artistic, relatively sparse
silhouette, with visible angular branching and procedural bark. No mature-tree
visual acceptance or physical-light calibration is claimed. Owned fixtures are
stopped; the broader botanical/workflow backlog remains open.

## Full-density shared canopy wind qualification — 2026-11-04

The retained Canopy3 study (88,704 leaves, three shared templates) now has a
larger native wind/animation qualification fixture in
`tests/test_canopy_wind_workflow.py`. It uses typed MCP tools with arbitrary
Python execution disabled, an explicit 88,704 instance cap, frames 1–13 at 24 fps,
steady wind [3,1,0] m/s, gust 2 m/s and artistic bend response 1 degree per m/s.
The 30,000 default instance limit correctly refuses this population. The plan
reports 52,214,400 raw coordinate bytes and 17,881,584 heuristic work units. Native
creation took 502.66 seconds, with operation polling and free-storage/checkpoint
reports throughout; this timing is one local run, not a performance guarantee.

Creation checked every key and interval midpoint: 25 frames, including every
native leaf instance's pose/variant and nonzero wood/shoot edge strain. Maximum
key position error was 1.9074e-6 m, midpoint position error .000484236 m, leaf
orientation error .137057 degrees, edge strain .00548749, scale relative error
4.4235e-7 and axis dot 3.8650e-7. Leaves remain instances; the preview copies only
three template meshes and stores three helper vertices per leaf. The original
live source guard stays unchanged during creation. Scene lights were disabled;
SKY front lighting and exposure -2 provide consistent 256-pixel, eight-sample
Cycles frames across the animation.

Qualification was completed in two phases. The initial 679.71-second run finished
native construction/readback, all 13 renders, save/reopen and preview removal,
then failed a test assertion comparing source session guards across reopening.
Those guards intentionally include native pointers. Source reports were otherwise
identical. The fixture now compares geometry/semantic reports across reload,
refreshes the session guard, and checks that guard before/after removal. It also
excludes transport operation IDs when comparing reports from different tool
surfaces. No production geometry/guard behavior was weakened to satisfy the test.

A targeted saved-evidence continuation passed in 76.06 seconds without regenerating
the large preview. It confirms source content, reopened preview validity,
guarded cleanup preserving source/materials, fresh-process native playback and
video delivery. The independent native reader accesses shape-key coordinates
through a temporary carrier before the instance-only Geometry Nodes output.
At frames 1, 7, 7.5, 13 and 20 it checks all 88,704 leaf centers/helper axes,
pinned soil vertices and source stability. Frames 1/13 independently count all
88,704 instances and three used templates, with no Realize Instances node. The
fractional-frame center error was .000453682 m and axis error .138477 degrees;
frame 20 exactly matches the sampled endpoint's coordinate hash. This is native
persistence/interpolation evidence, not continuous-time motion qualification.

All 13 decoded RGB frames are distinct. Frames 1/7 and 1/13 differ in 29,147 and
29,428 pixels, with mean absolute channel differences 4.680 and 6.279. Frames
1, 7 and 13 were actually viewed and remain within the chosen fixed camera.
The H.264 MP4 is independently probed as 256x256, 13 frames at 24 fps (about half a
second). This is a short rendered kinematic preview. Sparse artistic habit,
procedural bark, biomechanical response, collision, wind extrema, runtime shader
parity, animated LODs and the 1000-tree workload remain unqualified.

Run the full opt-in fixture with `MCPBLENDER_TEST_BLENDER=1` and
`MCPBLENDER_WIND_CANOPY_SOURCE` pointing to the retained preset Canopy3.blend.
`MCPBLENDER_WIND_CANOPY_EVIDENCE_DIR` retains outputs. The targeted delivery test
uses `MCPBLENDER_WIND_CANOPY_SAVED` pointing to the saved evidence library. Local
evidence is `/tmp/mb-canopy-wind-20261104/`, including operation/storage journals,
`library/canopy-wind.blend`, wind/cleanup/native/pixel/video proofs, 13 PNGs and
the MP4. Temporary native readback objects are removed before final guard checks;
all owned applications/brokers stop. No packages, virtual environments, installed
runtimes/skills, services, user GUI sessions or engine adapters were changed.

## Semantic trunk/major-branch collision snapshots — 2026-11-04

Typed `inspect_botanical_collision_source`, `create_botanical_collisions`,
`inspect_botanical_collisions` and guarded removal now select canonical trunk and
major branches without realizing foliage. Each selected native woody sleeve,
including shared rings/root flare, becomes a closed convex piece. Selection is
ancestor-closed and bounded by explicit count/triangle limits. Source geometry,
selection, frame and placement remain unchanged. Independent saved snapshots
report source geometry/semantic/placement freshness separately from their validity.

The initial native-hull implementation was refused by its containment gate on
an actual mature source: near-coplanar face merging left a selected vertex about
4.88e-6 m outside a face (tolerance 1.18e-6 m). The final implementation uses a
bounded deterministic double-precision hull builder for at most 32 points. It
retains original native coordinate values, checks every input vertex against
all outward triangular halfspaces, verifies closed oriented edges/positive volume,
and uses translated coordinates for stable plane/volume calculations. No extra
numerical package, Blender rebuild or environment change was required.

Final pure hull, schema/readonly, native lifecycle and add-on-without-frontend
checks passed four tests in 24.90 seconds. They include shuffled inputs,
near-coplanar 32-point sleeves, random spherical hulls, large translations,
degenerate/oversized input refusal, count/triangle/stale guards, early/late exact
ID rollback, source/frame/selection preservation, rotation/nonuniform placement
at scene-unit scale .01, reflection/shear refusal, unit/branch-mapping guards,
source movement, save/reopen, source removal and blocked foreign references,
collection members, persistent IDs and attached physics. Native mesh topology,
volume and source-vertex containment are independently checked after publication.
Both parented and explicitly unparented placement modes are covered.

The Python-disabled three-source workflow passed in 133.75 seconds using retained
Canopy1/2/3 sources with 92,136 / 90,288 / 88,704 leaves. Default radius .12 m and
maximum order 1 produced 25 / 30 / 21 convex pieces, with 700 / 840 / 588 triangles.
Maximum reported source-vertex outside distances were below 8.4e-17 m in these
fixtures. No extra geometric padding was applied. Summed piece volumes were
2.67033 / 2.74817 / 2.58337 cubic metres; these are sums, not union volumes.
All three fixed-camera renders were actually viewed. Closed pieces meet/overlap
at joints; this is collision geometry, not a welded render surface.

All three profiles save/reopen, report unchanged source content after refreshing
session guards, and can be removed without changing the live editable-source
guard. Existing explicit-object GLB export delivers the root and all pieces.
The file-only decoder traverses node transforms and checks names/counts, triangle
counts, closed welded-position edges and positive per-piece world volumes against
native plans. It repeats validation after owned profile removal. This establishes
static count/closedness/volume checks, not engine collision-resource or canonical
sidecar delivery; dedicated large-profile collision packaging remains open.

A further five-second saved-project check (one test passed in 5.27 seconds)
independently compares every exported piece's Z-up metre world bounds with its
native saved project. All three sources pass placement tolerances, including the
20 m display offset. The fixture now records native bounds during the full
workflow and enforces the same check on subsequent delivery validation. Storage
journals also confirm positive free bytes, a >=4 MiB collision estimate and space
admission on completed creations. No geometry/render regeneration was needed to
perform these extra file/native comparisons.

The native rigid-body API correctly refused the default parented pieces. An
explicit `parent_to_root=false` creation option supplies independent world-placed
pieces while retaining an origin marker. A targeted Python-disabled contact test
passed in 50.63 seconds: a .1 m box falls onto a generated convex trunk piece,
with sampled centre heights 1.74447, .71111, .59962 and .60065 m at frames
1/12/36/60. The piece top is .54447 m. Attached physics blocks owned deletion;
removing both controllers restores a valid unmodified collision profile, permits
cleanup and preserves the source guard. This is one native Bullet contact,
not wind-swept, compound, engine, broad-phase load or biomechanical qualification.

Evidence is `/tmp/mb-canopy-collision-20261104/`: three editable projects/renders/
GLBs and branch/geometry proofs in `library`, contact/ownership proof in `contact`,
and operation/storage journals. Progress reports current free bytes and a
collision checkpoint heuristic. All owned applications/brokers are stopped.
No packages, virtual environments, installed runtimes/skills, services, normal
GUI sessions, engine adapters, tags or pushes changed.

## Dense LOD planning counterexample — 2026-11-04

A separate pure planning check reused the retained 88,704-leaf source and its
canonical export. At resolution 64, a 160,731,648-byte leaf-mask estimate fits
the default memory budget. Planning took 295.57 seconds and 115,840 gain
evaluations. The 22,000/6,000-leaf subsets report zero FRONT/SIDE/TOP covered-pixel
loss on that grid; the 3,000-leaf subset loses 8.84–16.71% with zero boundary loss.
These are fixed-grid pixel-centre results, not accepted dense LODs.

Independent projection at resolution 128, using the exact same framing and the
previously retained full-source reference, disproves a broad quality inference.
The 22,000-leaf selection loses 52.70–66.21% of covered pixels; the 6,000-leaf
selection loses 89.10–93.24%, and the 3,000-leaf selection 97.40–98.12%. The
105.63-second check confirms severe sampling aliasing/selection bias. No native
LOD profile was created or delivered from these misleading coarse results.
Sampling-aware planning and independent quality checks are required before
qualifying full-density near/mid/far representations. Cards/impostors and their
optical/filtering/wind/export behavior remain open.

Local exploratory evidence is `/tmp/mb-canopy-lod-20261104/` (`plan.json`, options,
progress and `validation128.json`). The broad mature-tree and workflow goal
remains incomplete; this counterexample takes priority over accepting an easier
coarse-grid gate.

### Bounded botanical foliage cluster planning

`inspect_botanical_foliage_clusters` has code-disabled typed MCP coverage for
read-only planning, pagination with a stable full-plan guard, count-budget refusal
and exact source preservation. Pure tests independently check exhaustive disjoint
membership, ancestor anchors, deterministic identity groups under leaf-list
reordering, unequal variant costs, coincident centres, invalid inputs and
cooperative cancellation. Contract/archive checks cover readonly discovery,
asynchronous defaults, bounds and dependency-free add-on packaging.

A retained dense 88,704-leaf, 1,176-branch native source was reopened in stock
Blender 5.0.1. Anchor order 2, maximum 512 leaves and 100,000 actual template
triangles per cluster produced 296 clusters across 171 anchor groups. Every leaf
was assigned once; maximum cluster size was 462 leaves / 90,552 triangles.
The pure membership check took 0.79 seconds; native source inspection, repeated
paged planning and preservation checks took 30.66 seconds. Source guard, selected
objects, active object, current frame and datablock inventory were unchanged.

These results qualify workload partitioning only. Leaf-centre bounds exclude
blade extents. No native cluster source, UV/material merge, fitted card, alpha
bake, shadow/optical/wind/far-LOD or population performance qualification follows
from this milestone. Existing generic card/bake tests retain their narrower scope.

### Independent selected botanical cluster sources and card delivery

`create_botanical_foliage_cluster`, `inspect_botanical_foliage_cluster` and
`remove_botanical_foliage_cluster` add an owned independent static mesh snapshot
for one planned cluster. Native tests compare every selected vertex against its
canonical pose/physical placement (including centimetre scene scale, source
rotation, nonuniform scale and world-metre preview offset), every UV corner across
two authored channels, material slots, smoothing/edge flags and canonical point
indices. Transformed corner normals are explicitly assigned and independently
compared after Blender's quantized encoding, with a 0.05-degree world-orientation
limit. Creation also checks every corner and records its measured error.

Checks cover cooperative cancellation before/after native staging with exact
source/ID preservation, stale plans, unsafe implicit/explicit Generated and
instancer UV sampling, mixed variant UV schemas, foreign collection members,
external mesh users, derived edits, active-UV changes, Object-mode admission,
save/reopen, source removal and guarded cleanup preserving shared materials.
Readonly discovery, contracts and dependency-free add-on packaging are covered.

The code-disabled MCP path creates the selected ordinary source, fits a card,
bakes BASE_COLOR/NORMAL/ROUGHNESS/ALPHA in an isolated worker, verifies the live
source unchanged, removes source and snapshot, reopens/validates the independent
bundle, exports GLB and renders a preview. Separate small and retained dense
fixtures exercise this path. Seven focused tests passed in 208.43 seconds;
the final native/contract/archive checks passed three tests in 15.00 seconds,
including Object-mode admission.

For the retained 88,704-leaf tree, the largest planned cluster contains 462 leaves
and 90,552 source triangles. All 184,800 native corners passed normal readback,
maximum 0.04094 degrees. The fitted target has 34 triangles; its four maps are
256 by 256. Projection hits are 7,032 of 46,668 target pixels (15.068%, above the
12.136% chosen gate). Alpha includes both zero and one. The complete typed MCP
sequence took 160.77 seconds, including all paginated dense workload inspections.
The 70,000-byte GLB independently parses with BLEND alpha mode and three embedded
images (alpha is packed with base colour). Both small and dense rendered previews
were visually inspected and show leaf groups separated by transparent gaps.

This establishes bounded source preparation and one fitted-view file-delivery
path. FRONT_PBR remains an explicitly lossy conversion of native thin-leaf optics.
The rendered preview is not a matched native/card comparison or a multi-view,
shadow, filtering, overdraw, wind, population, mature-tree or receiving-engine
qualification. Atlas/far representations and those independent quality gates
remain open. No Godot operation, package installation or Blender rebuild was used.

Botanical cluster/collision inspection commands are explicitly classified as
read-only by the native bridge. Live MCP checks confirm cluster planning/snapshot
inspection and collision planning/snapshot inspection return no recovery metadata
and therefore do not trigger mutation checkpoints. The cluster delivery regression
passed in 56.70 seconds; a dedicated small collision lifecycle check passed in
14.21 seconds. The optional large-canopy collision tests were not enabled in that
run (three skipped), so no new large-canopy physics claim follows from this fix.

### PNG comparison and matched dense-card rejection

`compare_png_images` is a read-only, library-contained comparison of bounded
non-interlaced RGB/RGBA PNG8/16. Fourteen pure cases cover all five PNG row filters,
8/16-bit precision, RGB opacity, explicit sRGB/linear interpretation, transparent
RGB invariance, missing/shifted silhouettes, colour errors, partial box-filter
blocks, uninformative hard masks, empty-reference rejection, CRC/profile/size
admission and cancellation. Contracts/path-policy, add-on archive and code-disabled
MCP checks bring the focused run to 17 tests passed in 23.90 seconds. The native
scene readback remains equal (excluding per-request operation IDs); comparisons
return no recovery metadata or scene/image datablock edits.

A separate typed MCP measurement run used the retained dense selected cluster and
its delivered GLB. Both were rendered at 512 by 512 in Cycles with 16 samples,
the same fixed TOP orthographic camera/frame, white world strength 0.5 and
transparent film; all other mesh/light objects were hidden. The original native
thin shader was retained, so FRONT_PBR optical losses were not suppressed. Camera
matrix readback was identical. Input-file hashes bind the measured PNGs. Both
renders were visually inspected.

The measurement completed, but the approximation FAILS the default quality gates.
At full size, native alpha area is 22,274.02 pixels versus 38,486.34 for the card
(+72.79%). Hard silhouette IoU is 0.58260, soft-alpha IoU 0.57875, missing fraction
zero and excess fraction 0.71644. Alpha MAE is 0.06185; premultiplied RGB RMSE is
0.01210. At box-filter factors 2/4/8, hard IoU is 0.57897/0.57771/0.56149 and
soft-alpha IoU remains about 0.57875. All four levels reject hard/soft overlap and
alpha MAE. The images visibly show gaps filled between leaves. Exact-image
self-comparison passes; the measurement and basic MCP checks passed two tests in
78.75 seconds. A passing measurement test is not accepted card quality.

The 256px texture bake used two pixels of EXTEND padding for every map, including
ALPHA. This is a concrete suspected contributor to excess opacity; the alpha path
must be investigated and corrected before qualifying dense card silhouettes. The
comparison gates were not relaxed. Box-filter results do not qualify GPU mipmaps,
alpha clipping/compression, shadows, wind, population or receiving-engine behavior.

### Projected opacity padding correction

The matched dense-card rejection above was traced with an existing-API control:
rebaking all maps at zero margin reduced alpha occupancy from 0.18599 to 0.10730
and passed the unchanged image gates. The same source, 256px maps, camera, 512px
renders, lighting, sample counts and thresholds were retained. Full-size hard IoU
became 0.89904, soft IoU 0.88082 and alpha-area bias -0.310%; factors 2/4/8 also
passed. This isolates EXTEND padding as the dominant excess-opacity contributor.

New projected jobs requesting ALPHA now record
`PROJECTED_ALPHA_NO_EXTEND_V1`: ALPHA uses zero margin and other maps retain the
requested padding. Self-bakes and jobs without projected ALPHA retain their
existing margin behavior. The policy is bound across job/marker/manifest, and
per-map effective margins are checked during completion, validation and
finished-file recovery. Explicit source policies enter atlas input guards.
Legacy bundles with no policy remain readable with their original pixels and
are not retroactively accepted as silhouette-correct.

The corrected dense bake retained two-pixel colour/normal/roughness padding and
zero ALPHA padding. Its alpha occupancy is 0.10730, identical to the all-zero-margin
control. The same matched native-versus-delivered-GLB protocol now PASSES the
unchanged hard/soft IoU >=0.8, alpha MAE <=0.05 and RGB RMSE <=0.1 gates at all four
scales. Full size: hard IoU 0.89823, soft IoU 0.88071, alpha MAE 0.01076,
alpha-area bias -0.3185% and premultiplied RGB RMSE 0.00595. Factors 2/4/8 have
hard IoU 0.90982/0.93971/0.95798 and soft IoU 0.89877/0.92363/0.95095. Colour
padding improves RGB error over the all-zero-margin control. The corrected render
was visually inspected; leaf gaps remain visible.

The positive matched comparison plus metre/centimetre fitted-card/bake/reopen/
atlas/GLB regressions passed three tests in 111.59 seconds. Dense rebake with legacy
validation, new policy checks and a synthetic completed-file recovery refusal/
reconciliation, plus pure policy and native emission regressions, passed three
tests in 46.34 seconds. Final policy/contracts/quality-binding checks passed seven
tests in 5.57 seconds. Recovery here is a deliberately edited finished-file
fixture, not a new live-crash qualification. All owned workers terminated normally.

This accepts one fixed TOP-view selected-cluster approximation at the measured
resolution/filter scales. It does not establish multi-view/whole-tree, GPU mip or
alpha mode, compression, shadows, wind, population, calibrated optics or Godot
behavior. The original padded render remains rejected evidence; gates were not
relaxed. Atlas optical comparisons and far representations remain open.

### Exact atlas pixels and two-cluster source-free delivery

New atlas plans require `RGBA8_CORE_AND_CLAMPED_GUTTER_V1`. The isolated worker
independently decodes source/emitted PNGs and compares every RGBA8 channel in tile
cores and clamped gutters, including RGB beneath zero alpha. It converts
bottom-origin UV rectangles to top-origin PNG rows. An initial verifier-origin
mismatch was corrected and covered with an asymmetric 4x6 test before accepting
native results. No packing algorithm or image-transfer tolerance was loosened.

Per-map source/output PNG hashes and per-tile counts/zero error form a retained
copy witness sealed by the owned job marker. Completion, validation and
finished-file recovery check the declared method, source/layout/file bindings,
counts and seal. Validation verifies current file hashes/native bindings and the
retained evidence; it does not repeat source pixel comparisons when inputs are
missing. Historical atlases without the method keep their original checks.

A code-disabled typed MCP run reused the corrected dense cluster 167 and created
cluster 168 from the retained master. Each has 462 leaves / 90,552 source triangles;
all 924 canonical leaf IDs are distinct. Cluster 168's maximum native normal
readback error is 0.03822 degrees, within the existing 0.05-degree gate. Their
34/33-triangle TOP-view cards use four corrected 256px PBR/alpha maps. A 1024x512
atlas with eight-pixel gutters retains two editable meshes and one shared material.
For each map, 131,072 core and 16,896 gutter pixels passed exact RGBA checks.

Copied input bundles were removed after assembly. The standalone atlas asset
reopened, validated its retained witness and exported a 203,412-byte GLB with two
meshes, one BLEND material and embedded textures. Native clusters, individual
card GLBs and atlas GLB were rendered with one fixed TOP orthographic camera at
512px/Cycles16/transparent film/white world0.5, hiding other meshes and lights.
Camera readback was unchanged. Native and atlas images were visually inspected.

Individual-card versus atlas hard silhouette IoU is 1.0 at box factors 1/2/4/8;
soft IoU exceeds 0.999997 at every level. Full-size premultiplied RGB RMSE is
0.0000221. All levels pass the stricter copy-render gates (hard/soft IoU >=0.99,
alpha MAE <=0.005, RGB RMSE <=0.01). Native versus atlas passes the existing
approximation gates: hard IoU 0.92485/0.93946/0.95533/0.96641 and soft IoU
0.91257/0.93088/0.95170/0.97140; full RGB RMSE 0.00521. Native versus separate
cards also passes. The full measurement/delivery sequence took 198.23 seconds;
its test passed in 211.36 seconds. The metre card/atlas regression passed in
38.43 seconds; final pixel/PNG/contracts/layout/archive/centimetre checks passed
23 tests in 72.99 seconds. All owned workers terminated.

This qualifies two distinct selected clusters in one fixed view and an exact
unresampled atlas transfer. It does not qualify all 296 clusters, multi-view or
whole-tree far representations, GPU mip/alpha/compression behavior, shadows, wind,
population budgets, mature-tree biology or receiving-engine behavior. Base/full-mip
planning numbers remain estimates, not measured GPU memory or runtime performance.

### Bounded fitted-card view families

`inspect_foliage_card_views` captures evaluated sources once and fits requested
TOP/FRONT/SIDE alternatives with source, aggregate projected-triangle and total
output-triangle limits. Each row retains the existing single-view creation guard
and parameters. It returns the matching orthographic framing preset (SIDE maps to
RIGHT), not an automatic angular-selection or crossed-card renderer. Native
checks cover metre/centimetre placement, unchanged IDs/transforms/selection,
per-view guard equivalence, budget refusal, cooperative cancellation, stale
sources, independent target creation and refusal of degenerate views. Typed MCP
checks verify readonly behavior/no recovery checkpoint and direct consumption of
the returned creation parameters. Existing single-view tests remain valid.
Eight focused native/contracts/MCP/fitting/archive tests passed in 79.36 seconds.

The retained 462-leaf / 90,552-triangle source produces a 271,656 projected-triangle
workload and 116 fitted triangles: TOP 34, FRONT 49, SIDE 33. At 256px texture
resolution for all views, TOP passed but FRONT and SIDE were rejected against
512px native renders. Base hard/soft IoU was 0.79816/0.77352 for FRONT and
0.67275/0.66743 for SIDE. Alpha-area biases were about -0.159%/-0.094%, with balanced
missing/excess boundaries rather than the previous opacity-padding expansion.
The failed measurement completed in 287.47 seconds and remains rejected evidence.
No criterion was loosened and no requested view was omitted.

A second run used TOP256/FRONT512/SIDE512 maps and a shared 2048x1024 RGBA8 atlas.
Each orientation was framed once with an ORTHO camera on source plus fitted target;
native, individual GLB and atlas GLB reused that camera/frame/lighting at
512px/Cycles16/transparent film/white world0.5. All nine comparisons, each at box
factors 1/2/4/8, passed their existing criteria. Native-to-atlas full-size hard/soft
IoU was TOP 0.89839/0.88082, FRONT 0.89726/0.88415, SIDE 0.81282/0.81597. At factor8
these became 0.96067/0.95075, 0.96429/0.96763 and 0.92593/0.94465. Individual-to-atlas
hard IoU is 1.0 throughout; soft IoU exceeds 0.99998. Atlas core/gutter RGBA copying
passed the exact witness checks. The three-view GLB is 489,924 bytes. The sequence
took 497.76 seconds; the positive test passed in 507.53 seconds.

Front/side native and delivered images were visually inspected. Despite the
silhouette and global RGB gates passing, substantial darker/specular shading
regions remain in FRONT/SIDE under the explicitly lossy FRONT_PBR conversion.
A follow-up map diagnostic found negative tangent-Z normal components in 6,739
of 14,511 opaque FRONT texels (46.44%) and 4,301 of 9,389 opaque SIDE texels
(45.81%), versus 1 of 7,032 TOP texels. This is a concrete lead for investigating
view-conditioned normal facing; it is not yet a confirmed cause or correction.
Global premultiplied RGB error must not be interpreted as calibrated foreground
optical equivalence. Those shading differences remain an open quality issue.

This qualifies bounded planning and the measured alternative-view file/silhouette
pipeline only. It does not qualify intermediate/back views, angular selection or
interpolation, drawing the alternatives together, native optical equivalence,
whole-tree far assets, shadows, wind, population performance or receiving-engine
behavior. Sources and failed-resolution evidence remain preserved; no Blender
rebuild, package installation or Godot operation was used.

### Foreground colour diagnostics and normal-map controls

PNG comparison now reports reference-alpha-normalized premultiplied RGB RMSE and
shared-coverage straight-colour RMSE, with weighted image-luminance diagnostics.
Optional explicit gates are disabled by default, preserving existing criteria.
Empty/unavailable overlap is null and cannot pass an enabled overlap gate. Pure
checks demonstrate that transparent padding dilutes the old whole-image error but
not the new colour scores; alpha-only differences remain separate from shared
colour. Reference-area error can exceed one for excess coverage. Explicit null
criteria are preserved across both MCP serialization stages and actually disable
the requested gate. Readonly scene equality, policy/path contracts, archive and
server regressions passed 25 tests in 28.07 seconds.

Controlled native renders reused the retained FRONT512/SIDE512 assets and the exact
recorded cameras under the same uniform world/transparent-film protocol. Four
variants were rendered: original map, flat geometric card normals, complete-vector
negation where mapped tangent Z was negative, and Z-only reflection. Source assets
and files were preserved. The original asset versus delivered GLB baseline has
IoU 1.0 and global RGB RMSE about 0.0000198/0.0000146, so the large shading loss is
already present before export.

Shared-coverage RGB RMSE for FRONT is original 0.06254, flat 0.02450, full flip
0.04170 and Z reflection 0.04200. SIDE is 0.06808, 0.03262, 0.05393 and 0.05495.
Original shared-coverage image-luminance bias is -64.88%/-69.25%; flat controls
reduce that to -8.86%/-8.96%. Full flips only reduce it to -42.41%/-52.08%.
Silhouettes remain near the prior accepted values. These controls establish a
large normal-dependent transport effect; they do not establish a correct normal
projection algorithm or optical equivalence. No normal-processing fix was shipped.

The same real control PNGs were read through the new code-disabled MCP metrics
surface; its diagnostic test passed in 35.37 seconds. An illustrative optional
0.03 overlap-colour gate rejects the original views and still rejects the flat
SIDE control. That test criterion is a diagnostic example, not a chosen product
optics tolerance or acceptance of flat-normal assets. Further work must examine
normal facing, geometric-normal/shading-normal transport and self-occlusion under
controlled lighting, rather than treating a partial flip as a complete solution.

### Projected-normal transport controls and directional inspection

Further controls on the same retained FRONT/SIDE bake assets kept cameras,
lighting and source PNGs fixed. Disabling shadow, diffuse, glossy, or all
secondary-ray visibility produced identical measured errors to the original:
overlap RGB RMSE 0.06254/0.06808, image-luminance bias -64.88%/-69.25%.
A diffuse-only closure retained the darkening, at RMSE 0.06913/0.07720.
The facing-flipped diffuse controls still had biases -51.52%/-60.88%.
These results exclude those ray-visibility changes as a correction in this
fixture; they do not qualify arbitrary scenes or light transports.

A separate square control removed texture/UV encoding entirely. It used an
explicit constant world-space shader normal at 0, 60 and 80 degrees, uniform
world lighting, and either flat geometry or geometry tilted to match the shader
normal, with the same projected square. Diffuse mean decoded PNG red was
0.09465/0.04880/0.02698 for flat geometry and approximately 0.09465 for all three
matching-geometry cases. Principled likewise differed with true geometry.
These are decoded, display-transformed PNG values, not scene radiance or a
physical energy ratio. The control demonstrates geometric/shading-normal
transport dependence without implicating normal-map encoding. It does not
establish a portable correction formula, native optical equivalence, or that
normal maps alone can reproduce the source geometry's transport on a flat card.
Original assets/maps were preserved; no normal correction was shipped.

`inspect_projected_normal_transfer` is a read-only, bounded diagnostic over a
successful original projected bake and its unchanged opened native asset. It
validates hashes and binding, measures raw tangent directions on covered texels,
and reports target planarity/smoothing/custom-normal context. It explicitly has
no optical acceptance gate and changes no data. Normal Z refers to the shading
TBN, which need not be the geometric face frame. Atlas and self-bake input is
outside this inspector's scope. Empty coverage/undefined vectors remain null
rather than yielding a passing fraction. Analytic checks cover directions,
quantization dead band, file-alpha independence, scalar-red coverage, invalid
vectors, unit-length error, PNG16, dimension mismatch, admission and cancellation.

Code-disabled MCP qualification reopened relocated TOP256/FRONT512/SIDE512 bundles
and measured 7,032/14,511/9,389 covered texels. Backward fractions with the explicit
2/255 dead band were 0.000142/0.464131/0.457344; grazing fractions were
0.011519/0.101234/0.272233. All three targets were planar, flat-shaded cards.
The inspector preserved reported scene state and added no recovery checkpoint.
Wrong opened assets and changed PNGs were rejected. A newly baked 32x32 NORMAL-only
projection used the hit-mask red fallback (1,024 valid covered directions), and a
successful self-bake was refused. The two native MCP tests passed in 35.21 seconds;
29 focused pure/contract/server/archive regressions passed in 18.35 seconds.
This qualifies diagnostics and their boundaries, not a normal-map correction or
receiving-engine lighting behavior. All owned native jobs finished normally.

### Persistent packed card families and guarded view selection

A family can be created from an unchanged validated original bake or atlas with
one to three declared canonical TOP/FRONT/SIDE alternatives. Source hash/map,
geometry, static placement-chain and option guards bind creation. It copies
private meshes/materials/groups and packs verified PNG bytes, retaining optical
conversion declarations. The original source objects/files are preserved.
Bake placement anchors are supported through bounded static Object-parent chains;
creation freezes world placement rather than retaining those source parents.
Families start hidden and select one alternative explicitly for viewport/render.

Pure angular checks cover canonical directions, deterministic exact ties, reverse
and diagonal refusal, conservative perspective-corner limits, non-finite/zero
inputs, large finite vector normalization and declared policy bounds. Discovery
checks keep inspectors available to read-only clients and gate mutations; source
paths remain library bounded and tracked for retention. The standalone add-on
archive includes the selector and native family implementation.

Code-disabled native MCP qualification copied the retained 116-triangle,
three-view cluster atlas into an independent packed family with four native maps.
Six matched 512x512 Cycles renders at 16 samples compared each original atlas view
against its selected packed copy. Every TOP/FRONT/SIDE comparison had hard and
soft IoU 1.0 and shared-coverage RGB RMSE zero at scales 1, 2 and 4. This run passed
in 150.13 seconds. This demonstrates the measured copy fidelity; the prior dark
FRONT/SIDE shading relative to native foliage is unchanged and remains open.

Native checks also exercised independent source-file absence after save/reopen,
selected-object GLB exports with embedded textures, camera-pose staleness,
unsupported-direction nonmutation, root rotation, rejection/restoration of
nonuniform scale, conservative perspective-envelope refusal, edited-content and
external linked-copy deletion blockers, and removal preserving original objects.
The four native maps export as three GLB images because base colour and alpha
are combined. No family selection controller is encoded by generic GLB export.

A fresh 32x32 seven-map projection exercised ordinary bake-anchor compatibility,
private AO group copying, packed save/reopen with the source bundle absent, and
GLB material bindings for base colour, normal, metallic/roughness, occlusion and
emission. Copied AO groups retain the `glTF Material Output` name prefix required
by the installed Blender exporter. File embedding and material references were
checked; this is not receiving-engine lighting qualification.

The angular cone is an explicit support policy, not a calibrated quality gate.
Intermediate-angle visual quality, angular blending, automatic playback/camera
following, whole-tree far/impostor delivery, wind, shadows and population costs
remain outside this milestone. Cancellation cleanup follows owned staging, but
this milestone does not add a live crash or cancellation-injection qualification.

After bake-anchor support was added, the final two native MCP workflows passed
in 73.92 seconds. Reparenting with unchanged world geometry preserved the base
bake validation but invalidated the family creation plan; an animated ancestor
was refused and reopening restored the original guard. The final 24 focused
pure/contract/server/archive regressions passed in 45.20 seconds. All owned test
workers finished normally. No package, environment or installed runtime changes
were required.
