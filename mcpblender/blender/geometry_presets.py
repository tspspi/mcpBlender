"""Trusted procedural recipes compiled to the same inspectable typed graphs."""
class Graph:
    def __init__(self, p):
        self.spec = {"group": p["group"], "replace": p.get("replace", False),
                     "expected_graph": p.get("expected_graph"), "inputs": [], "nodes": [], "links": [],
                     "_preset": {"type": p["settings"]["type"], "version": 1}}
        self.node("NodeGroupInput", name="Parameters")
        self.node("NodeGroupOutput", name="Output")

    def node(self, kind, inputs=None, properties=None, name=None, **extra):
        name = name or f"{kind.removeprefix('GeometryNode').removeprefix('ShaderNode')}{len(self.spec['nodes']):03}"
        spec = {"name": name, "type": kind, "inputs": [], "properties": properties or {}} | extra
        self.spec["nodes"].append(spec)
        for socket, value in (inputs or {}).items():
            if isinstance(value, tuple):
                self.link(value, (name, socket))
            else:
                spec["inputs"].append({"socket": socket, "value": value})
        return name

    def link(self, source, target):
        self.spec["links"].append({"from_node": source[0], "from_socket": source[1],
                                   "to_node": target[0], "to_socket": target[1]})

    def input(self, name, kind, default, minimum, maximum):
        self.spec["inputs"].append({"name": name, "type": kind, "default": default,
                                    "minimum": minimum, "maximum": maximum})
        return "Parameters", name

    def math(self, operation, a, b=0):
        return self.node("ShaderNodeMath", {0: a, 1: b}, {"operation": operation}), 0

    def vector(self, x=0, y=0, z=0):
        return self.node("ShaderNodeCombineXYZ", {"X": x, "Y": y, "Z": z}), "Vector"

    def transform(self, mesh, translation=None, rotation=None):
        inputs = {"Geometry": mesh}
        if translation is not None:
            inputs["Translation"] = translation
        if rotation is not None:
            inputs["Rotation"] = rotation
        return self.node("GeometryNodeTransform", inputs), "Geometry"

    def paint(self, mesh, material):
        if not material:
            return mesh
        return self.node("GeometryNodeSetMaterial", {"Geometry": mesh}, material=material), "Geometry"

    def primitive(self, kind, inputs, material=None):
        node = self.node(kind, inputs)
        stored = self.node("GeometryNodeStoreNamedAttribute", {"Geometry": (node, "Mesh"), "Value": (node, "UV Map")},
                           {"data_type": "FLOAT2", "domain": "CORNER"}, attribute="UVMap")
        return self.paint((stored, "Geometry"), material)

    def instance(self, points, mesh, rotation=None):
        inputs = {"Points": points, "Instance": mesh}
        if rotation is not None:
            inputs["Rotation"] = rotation
        return self.node("GeometryNodeInstanceOnPoints", inputs), "Instances"

    def realize(self, mesh):
        return self.node("GeometryNodeRealizeInstances", {"Geometry": mesh}), "Geometry"

    def join(self, *meshes):
        node = self.node("GeometryNodeJoinGeometry")
        for mesh in meshes:
            self.link(mesh, (node, "Geometry"))
        return node, "Geometry"

    def finish(self, mesh):
        self.link(mesh, ("Output", "Geometry"))
        return self.spec


def building(g, p):
    width = g.input("Width", "FLOAT", p["width"], 1, 200)
    depth = g.input("Depth", "FLOAT", p["depth"], 1, 200)
    floor = g.input("FloorHeight", "FLOAT", p["floor_height"], 1, 10)
    count = g.input("Floors", "INT", p["floors"], 1, 32)
    columns = g.input("Columns", "INT", p["columns"], 1, 16)
    height = g.math("MULTIPLY", floor, count)
    half_height = g.math("MULTIPLY", height, .5)
    shell = g.primitive("GeometryNodeMeshCube", {"Size": g.vector(width, depth, height)}, p.get("wall_material"))
    shell = g.transform(shell, g.vector(z=half_height))
    roof = g.primitive("GeometryNodeMeshCube", {"Size": g.vector(g.math("ADD", width, .3), g.math("ADD", depth, .3), .2)}, p.get("roof_material"))
    roof = g.transform(roof, g.vector(z=g.math("ADD", height, .1)))
    spacing = g.math("DIVIDE", width, g.math("ADD", columns, 1))
    start_x = g.math("ADD", g.math("MULTIPLY", width, -.5), spacing)
    row = g.node("GeometryNodeMeshLine", {"Count": columns, "Start Location": g.vector(x=start_x), "Offset": g.vector(x=spacing)})
    window = g.primitive("GeometryNodeMeshCube", {"Size": g.vector(g.math("MULTIPLY", spacing, .6), .06, g.math("MULTIPLY", floor, .5))}, p.get("window_material"))
    row_geometry = g.instance((row, "Mesh"), window)
    floors = g.node("GeometryNodeMeshLine", {"Count": count, "Offset": g.vector(z=floor),
                                            "Start Location": g.vector(z=g.math("MULTIPLY", floor, .5))})
    panels = g.realize(g.instance((floors, "Mesh"), row_geometry))
    face_y = g.math("ADD", g.math("MULTIPLY", depth, .5), .025)
    front = g.transform(panels, g.vector(y=g.math("MULTIPLY", face_y, -1)))
    back = g.transform(panels, g.vector(y=face_y))
    return g.join(shell, roof, front, back)


def tree(g, p):
    height = g.input("Height", "FLOAT", p["height"], .5, 30)
    crown = g.input("CrownRadius", "FLOAT", p["crown_radius"], .1, 10)
    trunk = g.input("TrunkRadius", "FLOAT", p["trunk_radius"], .02, 2)
    bark = g.primitive("GeometryNodeMeshCylinder", {"Vertices": p["segments"], "Radius": trunk,
                       "Depth": g.math("MULTIPLY", height, .4)}, p.get("trunk_material"))
    bark = g.transform(bark, g.vector(z=g.math("MULTIPLY", height, .2)))
    leaves = g.primitive("GeometryNodeMeshCone", {"Vertices": p["segments"], "Radius Top": 0,
                         "Radius Bottom": crown, "Depth": g.math("MULTIPLY", height, .75)}, p.get("leaf_material"))
    # The cone node starts at z=0; the cylinder node is centered on z=0.
    leaves = g.transform(leaves, g.vector(z=g.math("MULTIPLY", height, .25)))
    return g.join(bark, leaves)


def compile_preset(p):
    g, settings = Graph(p), p["settings"]
    kind = settings["type"]
    if kind == "BUILDING":
        mesh = building(g, settings)
    elif kind in {"VEGETATION", "SCATTER_VEGETATION"}:
        mesh = tree(g, settings)
        if kind == "SCATTER_VEGETATION":
            density = g.input("Density", "FLOAT", settings["density"], 0, 50)
            seed = g.input("Seed", "INT", settings["seed"], 0, 1_000_000)
            spacing = g.input("Spacing", "FLOAT", settings["spacing"], .1, 20)
            maximum = g.input("MaxPoints", "INT", settings["max_points"], 1, 2000)
            distributed = g.node("GeometryNodeDistributePointsOnFaces", {"Mesh": ("Parameters", "Geometry"),
                                 "Density Max": density, "Distance Min": spacing, "Seed": seed}, {"distribute_method": "POISSON"})
            index = g.node("GeometryNodeInputIndex")
            compare = g.node("FunctionNodeCompare", {"A_INT": (index, "Index"), "B_INT": maximum},
                             {"data_type": "INT", "operation": "LESS_THAN"})
            bounded = g.node("GeometryNodeSeparateGeometry", {"Geometry": (distributed, "Points"),
                             "Selection": (compare, "Result")}, {"domain": "POINT"})
            mesh = g.realize(g.instance((bounded, "Selection"), mesh, (distributed, "Rotation")))
            # The original surface stays visible and keeps its material/UV data.
            mesh = g.join(("Parameters", "Geometry"), mesh)
    elif kind == "REFINE_MESH":
        level = g.input("Levels", "INT", settings["levels"], 0, 3)
        mesh = g.node("GeometryNodeSubdivisionSurface", {"Mesh": ("Parameters", "Geometry"), "Level": level}), "Mesh"
        mesh = g.paint(mesh, settings.get("material"))
    else:
        raise ValueError("Unknown procedural preset")
    return g.finish(mesh)
