"""Base-mesh editing on temporary BMeshes, with explicit stale-index guards."""
import hashlib
import json
import math
import struct

import bmesh
import bpy
from mathutils import Vector

from .assets import mesh_object
from .morphs import topology_digest

COMMANDS = {"inspect_mesh_elements", "select_mesh_elements", "extrude_mesh_faces",
            "inset_mesh_faces", "loop_cut_mesh", "merge_mesh_vertices",
            "cleanup_mesh", "repair_mesh_normals", "remove_mesh_selection"}
SELECTIONS = "mcpblender_element_selections"


def geometry_digest(mesh):
    digest = hashlib.sha256(bytes.fromhex(topology_digest(mesh)))
    for vertex in mesh.vertices:
        digest.update(struct.pack("!3d", *vertex.co))
    return digest.hexdigest()


def groups(obj):
    try:
        result = json.loads(obj.get(SELECTIONS, "{}"))
        if not isinstance(result, dict) or len(result) > 64:
            raise ValueError("Invalid mesh selection metadata")
        for value in result.values():
            if (not isinstance(value, dict) or value.get("domain") not in {"VERTEX", "EDGE", "FACE"}
                    or not isinstance(value.get("topology"), str)
                    or not isinstance(value.get("indices"), list)
                    or any(type(i) is not int or i < 0 for i in value["indices"])):
                raise ValueError("Invalid mesh selection metadata")
        return result
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid mesh selection metadata") from exc


def collections(bm):
    for items in (bm.verts, bm.edges, bm.faces):
        items.ensure_lookup_table()
        items.index_update()
    return {"VERTEX": bm.verts, "EDGE": bm.edges, "FACE": bm.faces}


def inspect(p):
    obj = mesh_object(p["name"])
    mesh = obj.data
    topology = topology_digest(mesh)
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        bm.normal_update()
        items = collections(bm)[p.get("domain", "FACE")]
        offset, limit = p.get("offset", 0), p.get("limit", 128)
        result = []
        for item in list(items)[offset:offset + limit]:
            entry = {"index": item.index, "selected": item.select}
            if isinstance(item, bmesh.types.BMVert):
                entry.update(position=list(item.co), world=list(obj.matrix_world @ item.co))
            else:
                entry["vertices"] = [v.index for v in item.verts]
                if isinstance(item, bmesh.types.BMEdge):
                    entry.update(faces=[f.index for f in item.link_faces],
                                 boundary=item.is_boundary, manifold=item.is_manifold,
                                 length=item.calc_length())
                else:
                    entry.update(normal=list(item.normal), center=list(item.calc_center_median()),
                                 area=item.calc_area(), material_index=item.material_index)
            result.append(entry)
        return {"name": obj.name, "domain": p.get("domain", "FACE"),
                "topology_sha256": topology, "geometry_sha256": geometry_digest(mesh),
                "vertices": len(bm.verts), "edges": len(bm.edges), "faces": len(bm.faces),
                "mesh_data": mesh.name, "data_users": mesh.users,
                "signed_local_volume": bm.calc_volume(signed=True) if bm.faces and all(e.is_manifold for e in bm.edges) else None,
                "total_elements": len(items), "elements": result,
                "next_offset": offset + limit if offset + limit < len(items) else None,
                "named_selections": [{"name": name, "domain": g["domain"],
                                      "count": len(g["indices"]), "valid": g["topology"] == topology}
                                     for name, g in sorted(groups(obj).items())]}
    finally:
        bm.free()


def resolve(obj, reference, domain, topology, items):
    indices = reference.get("indices")
    if indices is None:
        group = groups(obj).get(reference["selection"])
        if not group:
            raise ValueError("Named mesh selection not found")
        if group["domain"] != domain or group["topology"] != topology:
            raise ValueError("Named mesh selection is stale or has the wrong element domain")
        indices = group["indices"]
    if not indices or len(set(indices)) != len(indices) or any(i < 0 or i >= len(items) for i in indices):
        raise ValueError("Mesh element indices must be unique and in range")
    return [items[i] for i in indices]


def guarded(p):
    obj = mesh_object(p["name"], edit=True)
    mesh = obj.data
    groups(obj)
    topology = topology_digest(mesh)
    if p["expected_topology"] != topology:
        raise ValueError("Mesh topology does not match expected_topology; inspect again")
    if p.get("expected_geometry") and p["expected_geometry"] != geometry_digest(mesh):
        raise ValueError("Mesh geometry does not match expected_geometry; inspect again")
    if mesh.shape_keys or any(m.type == "ARMATURE" for m in obj.modifiers):
        raise ValueError("Mesh editing requires a mesh without shape keys or armature deformation")
    if mesh.users > 1 and not p.get("make_single_user", False):
        raise ValueError("Mesh data is shared; pass make_single_user=true to isolate this object")
    if len(mesh.vertices) > 1_000_000 or len(mesh.polygons) > 1_000_000:
        raise ValueError("Structured mesh editing is limited to one million vertices/faces")
    return obj, topology


def ring_edges(seed):
    ring, todo = {seed}, [seed]
    while todo:
        edge = todo.pop()
        if len(edge.link_faces) > 2:
            raise ValueError("Loop cuts require a manifold quad ring")
        for face in edge.link_faces:
            if len(face.verts) != 4:
                raise ValueError("Loop cut crosses a non-quad face; choose another seed edge")
            opposite = next(e for e in face.edges if not set(e.verts) & set(edge.verts))
            if opposite not in ring:
                ring.add(opposite)
                todo.append(opposite)
    return list(ring)


def operate(command, obj, bm, p, topology):
    items = collections(bm)
    if command in {"extrude_mesh_faces", "inset_mesh_faces"}:
        faces = resolve(obj, p["faces"], "FACE", topology, items["FACE"])
        if command == "extrude_mesh_faces":
            old_edges = {e for f in faces for e in f.edges}
            old_verts = {v for f in faces for v in f.verts}
            result = bmesh.ops.extrude_face_region(bm, geom=faces)
            vertices = [v for v in result["geom"] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, verts=vertices, vec=Vector(p["offset"]))
            bmesh.ops.delete(bm, geom=[f for f in faces if f.is_valid], context="FACES_ONLY")
            unused = [e for e in old_edges if e.is_valid and not e.link_faces]
            if unused:
                bmesh.ops.delete(bm, geom=unused, context="EDGES")
            unused = [v for v in old_verts if v.is_valid and not v.link_edges]
            if unused:
                bmesh.ops.delete(bm, geom=unused, context="VERTS")
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        elif p.get("individual"):
            bmesh.ops.inset_individual(bm, faces=faces, thickness=p["thickness"], depth=0,
                                       use_even_offset=True, use_interpolate=True)
        else:
            bmesh.ops.inset_region(bm, faces=faces, thickness=p["thickness"], depth=0,
                                   use_boundary=True, use_even_offset=True, use_interpolate=True)
    elif command == "loop_cut_mesh":
        if p["edge"] >= len(bm.edges):
            raise ValueError("Loop-cut edge is out of range")
        edges = ring_edges(bm.edges[p["edge"]])
        if len(bm.verts) + len(edges) * p["cuts"] > 1_000_000:
            raise ValueError("Loop cut exceeds the mesh editing budget")
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=p["cuts"], use_grid_fill=True)
    elif command == "merge_mesh_vertices":
        vertices = resolve(obj, p["vertices"], "VERTEX", topology, items["VERTEX"])
        if len(vertices) < 2:
            raise ValueError("Merge requires at least two vertices")
        target = vertices[-1] if p.get("position") == "LAST" else vertices[0]
        position = sum((v.co for v in vertices), Vector()) / len(vertices) if p.get("position", "CENTER") == "CENTER" else target.co.copy()
        bmesh.ops.weld_verts(bm, targetmap={v: target for v in vertices if v != target})
        target.co = position
    elif command == "cleanup_mesh":
        if p["merge_distance"]:
            bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=p["merge_distance"])
        if p["dissolve_distance"]:
            bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=p["dissolve_distance"])
        if p["remove_loose"]:
            loose = [e for e in bm.edges if not e.link_faces]
            if loose:
                bmesh.ops.delete(bm, geom=loose, context="EDGES")
            loose = [v for v in bm.verts if not v.link_edges]
            if loose:
                bmesh.ops.delete(bm, geom=loose, context="VERTS")
        if p["recalculate_normals"]:
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    elif command == "repair_mesh_normals":
        faces = resolve(obj, p["faces"], "FACE", topology, items["FACE"]) if p.get("faces") else list(bm.faces)
        if p["direction"] != "FLIP":
            bmesh.ops.recalc_face_normals(bm, faces=faces)
        if p["direction"] != "OUTSIDE":
            bmesh.ops.reverse_faces(bm, faces=faces)
    else:
        raise ValueError("Unsupported mesh edit")


def dispatch(command, p):
    if command == "inspect_mesh_elements":
        return inspect(p)
    if command == "remove_mesh_selection":
        obj = mesh_object(p["name"], edit=True)
        stored = groups(obj)
        if p["selection_name"] not in stored:
            raise ValueError("Named mesh selection not found")
        del stored[p["selection_name"]]
        obj[SELECTIONS] = json.dumps(stored)
        return inspect({"name": obj.name})
    obj, topology = guarded(p)
    bm = bmesh.new()
    candidate = None
    original = obj.data
    try:
        bm.from_mesh(original)
        if command == "select_mesh_elements":
            items = collections(bm)[p["domain"]]
            chosen = resolve(obj, p["elements"], p["domain"], topology, items)
            stored = groups(obj)
            name = p.get("selection_name")
            if name:
                if name in stored and not p.get("replace"):
                    raise ValueError("Named selection already exists; pass replace=true")
                if name not in stored and len(stored) >= 64:
                    raise ValueError("At most 64 named selections per object")
                stored[name] = {"domain": p["domain"], "topology": topology,
                                "indices": [item.index for item in chosen]}
                if sum(len(g["indices"]) for g in stored.values()) > 100_000:
                    raise ValueError("Named selections exceed the 100,000-index budget")
            # Direct RNA selection writes can allocate custom-data layers and
            # invalidate an in-progress MeshVertex iterator. BMesh owns stable
            # elements and commits the complete selection on a temporary mesh.
            for values in (bm.verts, bm.edges, bm.faces):
                for item in values:
                    item.select = False
            for item in chosen:
                item.select_set(True)
            candidate = original.copy()
            bm.to_mesh(candidate)
            candidate.update()
            obj.data = candidate
            candidate = None
            if original.users == 0:
                bpy.data.meshes.remove(original)
            if name:
                obj[SELECTIONS] = json.dumps(stored)
            return inspect({"name": obj.name, "domain": p["domain"]})
        operate(command, obj, bm, p, topology)
        if len(bm.verts) > 1_000_000 or len(bm.faces) > 1_000_000:
            raise ValueError("Edit exceeds one million vertices/faces")
        if any(not all(math.isfinite(x) for x in v.co) for v in bm.verts):
            raise ValueError("Mesh edit produced non-finite coordinates")
        bm.normal_update()
        candidate = original.copy()
        bm.to_mesh(candidate)
        candidate.update()
        obj.data = candidate
        candidate = None
        if original.users == 0:
            bpy.data.meshes.remove(original)
        return inspect({"name": obj.name})
    finally:
        bm.free()
        if candidate is not None:
            bpy.data.meshes.remove(candidate)
