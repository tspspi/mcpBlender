"""Workflow discovery without implying full bpy coverage or caller permission."""

# Groups describe the typed surface, not all of Blender's functionality.
WORKFLOWS = {
    "numeric_attributes": ({"inspect_attribute_export", "export_attribute_bundle", "validate_attribute_bundle", "inspect_mesh_attributes", "create_mesh_attribute", "set_mesh_attribute_values", "ramp_mesh_attribute", "remove_mesh_attribute"}, "Guarded base-mesh POINT/EDGE/FACE/CORNER float/int32/bool/vector3/linear RGBA fields, local coordinate ramps, explicit shared-data isolation and evaluated mesh readback. UV/internal fields protected; named-attribute GN readers/stores support instance graphs. Versioned static GLB scalar-lane packing independently verifies fields, corner/triangle correspondence, UV channels and metre placement; engine behavior remains separate."),
    "botanical_modeling": ({"refresh_vegetation_bake", "inspect_vegetation_bake_adoption", "adopt_vegetation_bakes", "inspect_vegetation_bake_source", "prepare_vegetation_bake", "inspect_vegetation_bake", "remove_vegetation_bake", "inspect_vegetation_materials", "export_botanical_lods", "validate_botanical_lod_bundle", "inspect_botanical_lod_source", "create_botanical_lods", "inspect_botanical_lods", "activate_botanical_lod", "remove_botanical_lods", "inspect_botanical_export", "export_botanical_bundle", "validate_botanical_bundle", "inspect_botanical_wind_preview_source", "create_botanical_wind_preview", "inspect_botanical_wind_preview", "remove_botanical_wind_preview", "inspect_botanical_wind", "sample_botanical_wind", "export_botanical_wind", "create_botanical_surface", "inspect_botanical_surface", "configure_botanical_surface", "remove_botanical_surface", "botanical_species_catalog", "plan_botanical_tree", "create_botanical_tree", "inspect_botanical_tree", "list_botanical_elements", "regenerate_botanical_tree", "remove_botanical_tree", "export_botanical_model", "inspect_botanical_coverage", "plan_leaf_template", "create_leaf_template", "plan_botanical_foliage", "configure_botanical_foliage", "remove_botanical_foliage", "list_botanical_leaves", "inspect_foliage_material", "configure_foliage_material"}, "Versioned standalone seeded oak-like scaffold/space-colonization branch and bud model, tapered native wood with bark UVs and semantic numeric attributes, metrics/JSON and guarded owned lifecycle. Artistic structure, not botanical/mechanical simulation. Optional guarded instanced foliage uses shared lobed leaf prototypes, seeded bud-attached shoots, UVs, managed procedural bark/vein detail, editable front/back thin-leaf optics and bounded orthographic blade-coverage inspection/proposed-recipe comparisons. Deterministic world-space gust fields, anchored hierarchical segment/leaf pose sampling and guarded semantic JSON export are available. Independent sampled native wind previews retain shared leaf instances, verify key/midpoint poses and edge-strain budgets, and support guarded owned cleanup. Versioned botanical bundles verify branch field GLBs, shared leaf prototypes and canonical leaf/phase/flutter/hierarchy semantics with native rest-instance readback. Coverage-scored near/mid native LODs retain nested leaf IDs, ancestor-closed wood, verified native poses/counts and shared prototypes. Engine wind shaders, unioned junctions, Shared-template LOD GLB/wind bundles independently validate canonical selections/ancestry, fields, UVs, counts and source/displayed metre placement. Opt-in guarded material source contracts separate opaque/double-sided/front-back/backlighting semantics, flag missing procedural UVs and independently inventory encoded GLB materials, images and texture UV bindings. Owned static bake copies preserve source sampling with pinned UV consumers, add or reuse verified nonoverlapping target UVs, isolate private source images/AO groups and feed the isolated texture baker. Guarded refresh accepts supported material/frame revisions while rejecting mesh/UV/attribute changes. Missing source UVs require explicit copy-only fallback; Guarded map adoption binds successful self-bakes to prepared LOD components, packs private images, preserves original UVs/wind fields and carries loss/UV witnesses into independently validated bundles. Source contracts do not bake maps or establish optical parity. Cards/impostors, collision and optical/runtime parity remain separate."),
    "mesh_modeling": ({"create_primitive", "create_mesh", "inspect_mesh", "inspect_mesh_elements",
                       "select_mesh_elements", "remove_mesh_selection", "extrude_mesh_faces",
                       "inset_mesh_faces", "loop_cut_mesh", "merge_mesh_vertices", "cleanup_mesh",
                       "repair_mesh_normals", "duplicate_object", "set_parent", "apply_transforms"},
                      "Static local Object-mode meshes; topology guards required for element edits."),
    "modifiers": ({"configure_modifier", "apply_modifier", "remove_modifier"},
                  "Allowlisted modifiers, including exact mesh Booleans; not arbitrary modifier RNA."),
    "geometry_nodes": ({"geometry_node_catalog", "inspect_geometry_graph", "configure_geometry_graph",
                        "attach_geometry_nodes", "configure_geometry_inputs", "create_geometry_preset"},
                       "Managed graphs, typed inputs and building/tree/scatter/refinement presets; attached graphs cannot be replaced. Imported graphs are read-only."),
    "materials": ({"create_botanical_surface", "inspect_botanical_surface", "configure_botanical_surface", "remove_botanical_surface", "configure_material", "assign_material", "apply_material_preset"},
                  "Material assignment, reusable presets and textured PBR."),
    "shader_nodes": ({"shader_node_catalog", "inspect_shader_graph", "configure_shader_graph",
                      "configure_shader_node", "connect_shader_nodes", "disconnect_shader_input",
                      "remove_shader_node"}, "Allowlisted material shader nodes; not every node or imported group."),
    "lighting": ({"inspect_render_visibility", "configure_render_visibility", "configure_light", "setup_preview_stage"}, "Basic lights and preview staging."),
    "cameras": ({"configure_camera", "frame_objects", "render_camera_batch"}, "Camera setup/framing and independent camera/frame render batches."),
    "animation": ({"set_keyframes", "create_animation_clip", "set_pose_keyframes", "set_active_clip",
                   "inspect_animation", "sample_animation", "create_morph_clip", "set_morph_keyframes",
                   "set_active_morph_clip", "inspect_morph_animation", "sample_morph_animation"},
                  "Object, skeletal and morph clips; see animation_constraints for controls/IK. See animation_drivers for managed numeric links; see animation_nla for layering and animation_retargeting for explicit motion transfer."),
    "animation_constraints": ({"create_animation_control", "inspect_animation_constraints", "configure_animation_constraint", "remove_animation_constraint", "move_animation_constraint", "sample_constraint_animation", "bake_constraint_animation"},
                              "Typed copy/limit/track constraints and bounded legacy IK; conservative object/bone dependency checks, current-timeline sampling. Independent visual pose baking with verified simple skins; keyed/driven constraint edits remain separate."),
    "animation_curves": ({"inspect_animation_channels", "set_control_keyframes", "edit_animation_curve"},
                         "Active-slot inspection and independent clip editing: constrained object/bone controls, constraint influence, retiming, easing and handles. Managed drivers retained while editing upstream controls; driver configuration and NLA layering have separate tools."),
    "animation_drivers": ({"inspect_animation_drivers", "configure_animation_driver", "remove_animation_driver", "set_animation_property"},
                          "Managed native simple-expression drivers with typed object/bone/custom-property/constraint/shape-key sources and conservative dependency validation; imported drivers inspect-only."),
    "animation_nla": ({"inspect_nla", "configure_nla_track", "configure_nla_strip", "remove_nla_strip", "remove_nla_track", "move_nla_track", "configure_nla_playback"},
                      "Object/pose/relative-shape action layering with managed tracks, timing/repeat/reverse, blend/influence/fades and explicit active-action policy. Animated strip controls/transitions/meta editing remain separate."),
    "animation_retargeting": ({"inspect_animation_retarget", "retarget_animation"},
                            "Explicit local-pose or rest-relative armature-space transfer into independent rigs/skins; current-timeline sampling, root motion and verified keyed results. Anatomical mapping and foot locking are not automatic."),
    "rigging": ({"create_armature", "bind_mesh", "inspect_rig", "inspect_armature_rest", "edit_armature_rest", "create_shape_key", "edit_shape_key",
                 "inspect_shape_keys", "set_shape_key_weights", "remove_shape_key"},
                "Skeleton construction/binding, guarded rest geometry/hierarchy/inheritance edits and bone additions, plus relative shape keys. Existing motion is not preserved when rest axes change; rename/removal and pose-to-rest conversion remain separate."),
    "skin_weights": ({"inspect_skin_weights", "set_skin_weights", "repair_skin_weights", "smooth_skin_weights", "mirror_skin_weights", "configure_skin_binding"},
                     "Guarded raw-basis weight editing, pruning/normalization, iterative edge smoothing, geometric mirror with explicit bone pairs and nearest-rest-segment fallback; preserves nondeform groups and locks by default."),
    "uv": ({"generate_uv", "inspect_mesh", "inspect_uv_layout", "set_uv_seams", "unwrap_uv_mesh", "pack_uv_islands", "normalize_uv_density", "activate_uv_map"},
           "Smart/cube projection, guarded seam unwrap/packing, bounded overlap inspection and per-island world-space texel density; texture baking remains separate."),
    "physics": ({"inspect_physics", "configure_rigid_world", "configure_rigid_body", "remove_rigid_body", "sample_rigid_bodies",
                 "inspect_simulations","configure_deform_simulation","configure_collision","configure_force_field","remove_simulation_controller","remove_force_field","sample_simulation"},
                "Rigid bodies plus static-source cloth/soft bodies, collisions and force helpers; see fluids for separate fluid bundles."),
    "fluids": ({"inspect_fluids", "configure_fluid_domain", "configure_fluid_flow", "configure_fluid_effector", "remove_fluid_controller"},
               "One static-source liquid/gas domain, mesh flows and collision effectors; no animated/deforming sources, guiding, noise or secondary particles."),
    "particles": ({"configure_particles","inspect_simulations","sample_simulation"},
                  "Newtonian emitters with optional object instances and static hair; dynamic hair/boids/keyed/fluid particles are not exposed."),
    "simulation_baking": ({"bake_rigid_bodies", "validate_rigid_bake", "clear_rigid_bake","bake_simulation","validate_simulation_bake","clear_simulation_cache",
                           "bake_fluid", "validate_fluid_bake", "inspect_fluid_job", "recover_fluid_job", "cleanup_fluid_job"},
                          "Embedded rigid/cloth/soft/particle snapshots; fluid external bundles use isolated worker, manifest validation, interrupted-job reconciliation and guarded cleanup."),
    "texture_baking": ({"inspect_texture_atlas", "build_texture_atlas", "inspect_foliage_card", "create_foliage_card", "inspect_texture_bake", "bake_textures", "validate_texture_bake", "inspect_texture_job", "recover_texture_job", "cleanup_texture_job"},
                       "Verified bake-bundle PBR atlas packing with explicit gutters and base/full-mip RGBA8 budgets. Guarded fitted convex/rectangle single-view foliage cards with sampled geometry coverage and native-unit bake parameters. Isolated evaluated-mesh normal/AO/PBR PNG bundles, source guards, native asset binding and owned-worker lifecycle; static direct Principled shader graphs plus explicit loss-reporting managed thin-leaf FRONT_PBR conversion."),
    "asset_assemblies": ({"inspect_asset_realization", "realize_asset_instances", "inspect_asset_assembly_source", "create_asset_assembly", "inspect_asset_assembly", "place_asset_instance", "set_asset_assembly_editing", "inspect_asset_instance", "remove_asset_instance"},
                         "Closed local object/data/action graphs copied to persistent collection prototypes; managed nested prototypes stay shared. Guarded linked placements, native viewport leaf/bounds inspection and direct scene editing links. Static current-viewport realization preserves evaluated mesh attributes and shared materials. External library linking, independent instance animation and assembly bundle export remain separate."),
    "asset_proxies": ({"inspect_asset_proxy_source", "generate_asset_proxies", "inspect_asset_proxies", "remove_asset_proxies"},
                     "Static world-space BOX/CONVEX_HULL collision approximations with explicit grouping and sampled surface checks; per-leaf budgeted DECIMATE Cycles shadow-only meshes. Source-preserving generation, freshness and owned cleanup. No automatic convex decomposition, physics attachment or engine integration."),
    "asset_packages": ({"inspect_asset_package", "export_asset_package", "validate_asset_package"},
                       "Guarded batch static primary GLBs, associated collision/shadow proxies and nested validated native LOD bundles. Independent oriented triangle-surface, scene/dependency/UV and inventory validation before directory publication; shader fidelity and engine integration remain separate."),
    "asset_lods": ({"inspect_lod_adoption", "adopt_lod_chain", "readopt_lod_chain", "configure_lod_source_visibility", "inspect_lod_management", "remove_lod_chain", "rebuild_lod_chain", "inspect_glb_deformation", "inspect_lod_export", "sample_lod_chain", "inspect_lod_source", "generate_lod_chain", "inspect_lod_chain", "activate_lod_level", "export_lod_chain", "validate_lod_export"},
                   "Static snapshots, relative morphs with source Key controls, or linear skeletal LODs following the existing rig, collapse/planar/unsubdivide reductions, per-level budgets and sampled rest/pose error. Static and skeletal GLB bundles validated; skin playback is independently decoded and compared with native joint/vertex samples. Integer-frame simple clips use zero-based times. Morphs preserve relative relationships and interpolate masked offsets; native isolated-key and timeline surface checks apply. inspect_glb_deformation independently inspects single-mesh native-profile skin/morph playback. Morph GLB bundles bake named current-timeline ranges on temporary proxies, verify all native baked frames and sampled decoded playback, and restore source controls. Guarded ownership inspection, original-source visibility, staged replacement and shared-data-preserving removal are supported. External/manual LOD adoption copies normalized geometry, supports explicit material remapping and source-controlled skin/morph transfer; guarded re-adoption uses staged replacement. Botanical foliage/impostors remain separate."),
    "compositing": ({"compositor_node_catalog", "inspect_compositor_graph", "configure_compositor_graph", "inspect_render_pipeline", "configure_render_passes", "configure_color_management", "configure_compositing"}, "Blender 5 managed Image-output compositor groups, installed socket/menu discovery, denoise/glare/grading/masks, guarded scene binding, render-pass flags and scalar display/view/look/white-balance controls. Staged replacement supports explicit shared local scene users; imported/animated/nested graphs remain read-only. No file-output nodes or custom color-curve editing. Separate render batches provide PNG/multilayer EXR delivery."),
    "rendering": ({"configure_render", "render_animation", "render_video", "render_animation_preview", "render_camera_batch", "inspect_render_job", "validate_render_job", "recover_render_job", "cleanup_render_job"},
                  "Connected-instance previews plus independent CPU camera/frame batches from owned snapshots. Editing continues; broker operation delegation survives broker restart/editor shutdown. PNG16 and scanline multipart EXR32 with pass/channel inventories, tracked progress/free space, self-cancellation and guarded file-job reconciliation/cleanup. Frozen packed resources required; external cache dependencies, video assembly and GPU/farm scheduling are separate."),
    "video_sequencer": ({"vse_add_strip", "vse_edit_strip", "vse_remove_strip", "vse_list"},
                        "Basic image/movie/audio/text strips; no typed transitions, masks or scene strips yet."),
    "asset_import_export": ({"asset_report", "preflight_game_asset", "export_objects_glb"},
                            "Includes structured GLB delivery; core import_asset/export_asset tools are also available."),
}


def workflow_support(commands):
    """Report commands actually registered by this worker, keeping gaps explicit."""
    available = set(commands)
    return {
        name: {"support": "structured_partial" if methods & available else "python_only",
               "structured_commands": sorted(methods & available), "scope": scope}
        for name, (methods, scope) in WORKFLOWS.items()
    }


DISCOVERY_NOTE = (
    "Worker implementation inventory, not caller authorization or comprehensive Blender support. "
    "Use MCP tools/list for this connection's permitted tools. python_only means no dedicated typed "
    "workflow; it does not guarantee the installed bpy API exists or Python execution is permitted. "
    "Runtime availability is not qualification; see VALIDATION.md for tested versions and scenarios."
)
