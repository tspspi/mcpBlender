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
    "geometry_nodes": (set(), "No structured Geometry Nodes authoring yet."),
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
                  "Object, skeletal and morph clips; constraints, drivers, retargeting and NLA need Python."),
    "rigging": ({"create_armature", "bind_mesh", "inspect_rig", "create_shape_key", "edit_shape_key",
                 "inspect_shape_keys", "set_shape_key_weights", "remove_shape_key"},
                "Skeleton construction, binding and relative shape keys; no existing-bone or weight repair tools."),
    "uv": ({"generate_uv", "inspect_mesh"}, "Smart/cube projection and inspection; no seams, packing or texture baking tools."),
    "physics": (set(), "No structured rigid/soft body, cloth, fluid or force-field workflows yet."),
    "particles": (set(), "No structured particle workflow; inspect the installed API before custom Python use."),
    "simulation_baking": (set(), "No shared simulation cache/bake workflow yet."),
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
