"""Structured Geometry Nodes groups; bpy and standard library only."""
import hashlib
import json
import math

import bpy

from .assets import mesh_object
from .shaders import resolve, set_value as shader_set_value, socket_info as shader_socket_info

COMMANDS = {"geometry_node_catalog", "inspect_geometry_graph", "configure_geometry_graph",
            "attach_geometry_nodes", "configure_geometry_inputs"}
NODE_TYPES = (
    "NodeGroupInput", "NodeGroupOutput", "GeometryNodeMeshCube", "GeometryNodeMeshGrid",
    "GeometryNodeMeshLine", "GeometryNodeMeshCylinder", "GeometryNodeMeshCone",
    "GeometryNodeTransform", "GeometryNodeSetPosition", "GeometryNodeInputPosition",
    "GeometryNodeJoinGeometry", "GeometryNodeDistributePointsOnFaces",
    "GeometryNodeInstanceOnPoints", "GeometryNodeRealizeInstances",
    "GeometryNodeSubdivisionSurface", "GeometryNodeSetMaterial", "ShaderNodeMath", "ShaderNodeVectorMath", "ShaderNodeCombineXYZ",
)
PROPERTIES = {
    "GeometryNodeMeshLine": ("mode", "count_mode"),
    "GeometryNodeMeshCylinder": ("fill_type",), "GeometryNodeMeshCone": ("fill_type",),
    "GeometryNodeDistributePointsOnFaces": ("distribute_method",),
    "ShaderNodeMath": ("operation",), "ShaderNodeVectorMath": ("operation",),
}
SOCKET_TYPES = {"FLOAT": "NodeSocketFloat", "INT": "NodeSocketInt",
                "BOOLEAN": "NodeSocketBool", "VECTOR": "NodeSocketVector"}
MANAGED = "mcpblender_geometry_graph"


def plain(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else str(value)
    if isinstance(value, bpy.types.ID):
        return {"name": value.name, "type": value.bl_rna.identifier}
    try:
        return [plain(item) for item in value]
    except TypeError:
        return None


def socket_info(socket, index):
    result = shader_socket_info(socket, index)
    result["default"] = plain(getattr(socket, "default_value", None))
    return result


def set_value(socket, value):
    if socket.type == "ROTATION":
        if not isinstance(value, list) or len(value) != 3 or any(not math.isfinite(v) for v in value):
            raise ValueError("Rotation socket requires three finite Euler angles in radians")
        socket.default_value = value
    else:
        shader_set_value(socket, value)


def group(name, edit=False):
    tree = bpy.data.node_groups.get(name)
    if tree is None or tree.bl_idname != "GeometryNodeTree":
        raise ValueError(f"Geometry Nodes group not found: {name}")
    if edit and (tree.library or tree.override_library or tree.animation_data or not tree.get(MANAGED)):
        raise ValueError("Editing requires a local managed group without animation/drivers")
    if edit and any(node.bl_idname not in NODE_TYPES for node in tree.nodes):
        raise ValueError("Managed group contains unsupported nodes; inspect and rebuild it explicitly")
    return tree


def interface(tree):
    return [item for item in tree.interface.items_tree if item.item_type == "SOCKET"]


def modifier_values(tree, mod):
    return [{"name": s.name, "identifier": s.identifier,
             "value": plain(mod.get(s.identifier, getattr(s, "default_value", None))),
             "use_attribute": bool(mod.get(s.identifier + "_use_attribute", False))}
            for s in interface(tree)[:64] if s.in_out == "INPUT" and s.socket_type != "NodeSocketGeometry"]


def describe(tree):
    nodes = [{"name": node.name, "type": node.bl_idname,
              "properties": {key: plain(getattr(node, key)) for key in PROPERTIES.get(node.bl_idname, ())},
              "inputs": [socket_info(s, i) for i, s in enumerate(list(node.inputs)[:128])],
              "outputs": [socket_info(s, i) for i, s in enumerate(list(node.outputs)[:128])]}
             for node in list(tree.nodes)[:128]]
    sockets = [{"name": s.name, "identifier": s.identifier, "direction": s.in_out,
                "type": s.socket_type, "default": plain(getattr(s, "default_value", None))}
               for s in interface(tree)[:64]]
    links = [{"from_node": l.from_node.name, "from_socket": l.from_socket.identifier,
              "to_node": l.to_node.name, "to_socket": l.to_socket.identifier,
              "valid": l.is_valid} for l in list(tree.links)[:256]]
    content = {"nodes": nodes, "inputs_outputs": sockets, "links": links}
    # Inspection of large/imported graphs is bounded, and must not pretend the
    # truncated fingerprint guards their full contents.
    complete = (len(tree.nodes) <= 128 and len(tree.links) <= 256 and len(interface(tree)) <= 64
                and all(node.bl_idname in NODE_TYPES and len(node.inputs) <= 128 and len(node.outputs) <= 128 for node in tree.nodes))
    digest = hashlib.sha256(json.dumps(content, sort_keys=True, allow_nan=False).encode()).hexdigest() if complete else None
    return content | {"group": tree.name, "graph_sha256": digest, "complete": complete,
                      "total_nodes": len(tree.nodes), "total_links": len(tree.links),
                      "managed": bool(tree.get(MANAGED)), "users": tree.users,
                      "modifier_users": [{"name": obj.name, "modifier": mod.name,
                                          "values": modifier_values(tree, mod)}
                          for obj in bpy.data.objects for mod in obj.modifiers
                          if mod.type == "NODES" and mod.node_group == tree]}


def add_interface(tree, specs=()):
    tree.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    for spec in specs:
        socket = tree.interface.new_socket(name=spec["name"], in_out="INPUT", socket_type=SOCKET_TYPES[spec["type"]])
        # Reuse actual node sockets to enforce installed type/range semantics.
        node = tree.nodes.get("MCP_InterfaceDefaults") or tree.nodes.new("NodeGroupInput")
        node.name = "MCP_InterfaceDefaults"
        set_value(resolve(node.outputs, socket.identifier), spec["default"])
        socket.default_value = node.outputs[socket.identifier].default_value
    tree.nodes.clear()


def configure_node(tree, spec):
    if spec["type"] not in NODE_TYPES:
        raise ValueError("Unsupported Geometry Nodes type")
    node = tree.nodes.new(spec["type"])
    node.name = spec["name"]
    for key, value in spec.get("properties", {}).items():
        if value is None:
            continue
        if key not in PROPERTIES.get(spec["type"], ()):
            raise ValueError(f"Property {key} is unsupported for {spec['type']}")
        prop = node.bl_rna.properties[key]
        if prop.type == "ENUM" and value not in {item.identifier for item in prop.enum_items}:
            raise ValueError(f"Unsupported {key} value; use geometry_node_catalog")
        setattr(node, key, value)
    if spec.get("material"):
        if spec["type"] != "GeometryNodeSetMaterial":
            raise ValueError("material requires GeometryNodeSetMaterial")
        mat = bpy.data.materials.get(spec["material"])
        if mat is None:
            raise ValueError(f"Material not found: {spec['material']}")
        node.inputs["Material"].default_value = mat
    for item in spec.get("inputs", []):
        socket = resolve(node.inputs, item["socket"])
        # Conservative cardinality limits on direct primitive/ subdivision inputs.
        if socket.name in {"Count", "Vertices X", "Vertices Y", "Vertices Z", "Vertices", "Side Segments", "Fill Segments"}:
            if isinstance(item["value"], (list, bool)) or not 1 <= item["value"] <= 512:
                raise ValueError("Primitive counts must be between 1 and 512")
        if socket.name == "Level" and not 0 <= item["value"] <= 3:
            raise ValueError("Subdivision level must be between 0 and 3")
        set_value(socket, item["value"])
    return node


def connect(tree, specs):
    graph, destinations = {node.name: [] for node in tree.nodes}, set()
    for spec in specs:
        source, target = tree.nodes.get(spec["from_node"]), tree.nodes.get(spec["to_node"])
        if source is None or target is None:
            raise ValueError("Geometry link references a missing node")
        output, input = resolve(source.outputs, spec["from_socket"]), resolve(target.inputs, spec["to_socket"])
        if input in destinations and not input.is_multi_input:
            raise ValueError("Each non-multi destination socket may occur only once")
        destinations.add(input)
        if output.type != input.type and {output.type, input.type} != {"VALUE", "INT"}:
            raise ValueError("Geometry link socket types must match (or be numeric)")
        graph[source.name].append(target.name)
        tree.links.new(output, input)
    visited, visiting = set(), set()
    def visit(name):
        if name in visiting:
            raise ValueError("Geometry links must not create cycles")
        if name not in visited:
            visiting.add(name)
            for target in graph[name]:
                visit(target)
            visiting.remove(name)
            visited.add(name)
    for name in graph:
        visit(name)
    outputs = [node for node in tree.nodes if node.bl_idname == "NodeGroupOutput"]
    if len(outputs) != 1 or not outputs[0].inputs["Geometry"].is_linked:
        raise ValueError("Exactly one Group Output with connected Geometry is required")
    if any(not link.is_valid for link in tree.links):
        raise ValueError("Invalid Geometry Nodes link")


def configure(p):
    previous = bpy.data.node_groups.get(p["group"])
    if previous:
        group(previous.name, edit=True)
        if not p["replace"]:
            raise ValueError("Existing group requires replace=true")
        if describe(previous)["graph_sha256"] != p["expected_graph"]:
            raise ValueError("Geometry graph fingerprint is stale")
        if previous.users - int(previous.use_fake_user):
            raise ValueError("Detach all users before replacing a shared/attached graph; change per-modifier inputs instead")
    staged = bpy.data.node_groups.new("MCP_GeometryPreflight", "GeometryNodeTree")
    try:
        add_interface(staged, p["inputs"])
        for spec in p["nodes"]:
            configure_node(staged, spec)
        connect(staged, p["links"])
        staged[MANAGED] = True
        staged.use_fake_user = True
        result = describe(staged)
        if previous:
            bpy.data.node_groups.remove(previous)
        staged.name = p["group"]
        result["group"] = staged.name
        staged = None
        return result
    finally:
        if staged is not None:
            bpy.data.node_groups.remove(staged)


def node_catalog(p):
    if not p.get("node_type"):
        groups = [tree for tree in bpy.data.node_groups if tree.bl_idname == "GeometryNodeTree"]
        return {"node_types": list(NODE_TYPES), "groups": [{"group": tree.name, "managed": bool(tree.get(MANAGED)), "users": tree.users} for tree in groups[:128]],
                "total_groups": len(groups), "note": "Request node_type for installed sockets/property choices. Interface Geometry sockets are added automatically; group listing is limited to 128."}
    if p["node_type"] not in NODE_TYPES:
        raise ValueError("Unsupported Geometry Nodes type")
    scratch = bpy.data.node_groups.new("MCP_GeometryCatalog", "GeometryNodeTree")
    try:
        add_interface(scratch)
        node = scratch.nodes.new(p["node_type"])
        result = describe(scratch)["nodes"][0]
        result["editable_properties"] = {
            key: {"choices": [item.identifier for item in node.bl_rna.properties[key].enum_items]}
            for key in PROPERTIES.get(node.bl_idname, ())}
        return result
    finally:
        bpy.data.node_groups.remove(scratch)


def modifier_result(obj, mod):
    return {"name": obj.name, "modifier": mod.name, "group": mod.node_group.name,
            "graph_sha256": describe(mod.node_group)["graph_sha256"],
            "values": modifier_values(mod.node_group, mod)}


def configure_inputs(p):
    obj = mesh_object(p["name"], edit=True)
    mod = obj.modifiers.get(p["modifier"])
    if mod is None or mod.type != "NODES" or mod.node_group is None:
        raise ValueError("Geometry Nodes modifier not found")
    tree = group(mod.node_group.name, edit=True)
    if describe(tree)["graph_sha256"] != p["expected_graph"]:
        raise ValueError("Geometry graph fingerprint is stale")
    if obj.animation_data:
        raise ValueError("Modifier input editing requires an object without animation/drivers")
    sockets = [s for s in interface(tree) if s.in_out == "INPUT" and s.socket_type != "NodeSocketGeometry"]
    values, seen = [], set()
    # Validate using a scratch copy so type/range errors cannot partly update the modifier.
    scratch = tree.copy()
    try:
        input_node = scratch.nodes.new("NodeGroupInput")
        for item in p["values"]:
            ref = item["socket"]
            matches = [sockets[ref]] if isinstance(ref, int) and 0 <= ref < len(sockets) else [s for s in sockets if s.identifier == ref or s.name == ref]
            if len(matches) != 1 or matches[0].identifier in seen:
                raise ValueError("Missing, ambiguous or duplicate interface input")
            socket = matches[0]
            seen.add(socket.identifier)
            if mod.get(socket.identifier + "_use_attribute", False):
                raise ValueError("Disable the named-attribute input mode before setting a constant")
            set_value(resolve(input_node.outputs, socket.identifier), item["value"])
            value = plain(input_node.outputs[socket.identifier].default_value)
            values.append((socket.identifier, value))
    finally:
        bpy.data.node_groups.remove(scratch)
    for identifier, value in values:
        mod[identifier] = value
    obj.update_tag()
    bpy.context.view_layer.update()
    return modifier_result(obj, mod)


def dispatch(command, p):
    if command == "geometry_node_catalog":
        return node_catalog(p)
    if command == "inspect_geometry_graph":
        return describe(group(p["group"]))
    if command == "configure_geometry_graph":
        return configure(p)
    if command == "configure_geometry_inputs":
        return configure_inputs(p)
    obj = mesh_object(p["name"], edit=True)
    tree = group(p["group"], edit=True)
    mod = obj.modifiers.get(p["modifier"])
    if mod and (mod.type != "NODES" or mod.node_group != tree):
        raise ValueError("Existing modifier has a different type/group; remove it explicitly before attaching")
    if mod is None:
        mod = obj.modifiers.new(p["modifier"], "NODES")
        mod.node_group = tree
    bpy.context.view_layer.update()
    return modifier_result(obj, mod)
