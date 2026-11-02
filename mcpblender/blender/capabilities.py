"""Workflow discovery without implying full bpy coverage or caller permission."""

# Groups describe the typed surface, not all of Blender's functionality.
WORKFLOWS = {
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
    "materials": ({"configure_material", "assign_material", "apply_material_preset"},
                  "Material assignment, reusable presets and textured PBR."),
    "shader_nodes": ({"shader_node_catalog", "inspect_shader_graph", "configure_shader_graph",
                      "configure_shader_node", "connect_shader_nodes", "disconnect_shader_input",
                      "remove_shader_node"}, "Allowlisted material shader nodes; not every node or imported group."),
    "lighting": ({"configure_light", "setup_preview_stage"}, "Basic lights and preview staging."),
    "cameras": ({"configure_camera", "frame_objects"}, "Camera setup and framing."),
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
    "texture_baking": ({"inspect_texture_bake", "bake_textures", "validate_texture_bake", "inspect_texture_job", "recover_texture_job", "cleanup_texture_job"},
                       "Isolated evaluated-mesh normal/AO/PBR PNG bundles, source guards, native asset binding and owned-worker lifecycle; static direct Principled shader graphs."),
    "asset_lods": ({"inspect_lod_source", "generate_lod_chain", "inspect_lod_chain", "activate_lod_level", "export_lod_chain", "validate_lod_export"},
                   "Independent static viewport snapshots, collapse/planar/unsubdivide reductions, strict per-level budgets, UV/material/normal checks and sampled bidirectional surface error; separate validated GLBs. Skinned/morph and botanical foliage/impostor LODs remain separate."),
    "compositing": (set(), "No structured compositor graph authoring yet."),
    "rendering": ({"configure_render", "render_animation", "render_video", "render_animation_preview"},
                  "Rendering uses the connected Blender instance; no separate render workers yet."),
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
