# Local validation: 0.2.0

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

Absolute shape-key animation, fluid/external-cache bakes, constraints/drivers/active NLA blending, other Blender/platform versions,
long-duration workloads, external HTTPS deployment, Godot behavior and real
external generation services are not qualified by this suite.
