"""Bounded camera-frame geometry for positive projected-area normal mixtures.

This is an internal geometry primitive, not an optical-equivalence guarantee.
Coordinates are (u, v, -depth) relative to an optional translated camera frame.
"""
import hashlib
import math
import struct

from .normal_quadrature import moments

FORMAT = 'mcpblender-projected-microfacets-v1'


def build(rect, atoms, *, depth, near, far, max_slope=16.,
          triangle_budget=8, omitted_mass_tolerance=1e-6,
          residual_tolerance=1e-5, anchor=None, origin=None, precision_omissions=(), cancelled=lambda: None):
    """Partition a rectangle into at most four independent planar strips.

    Only negligible unsupported mass may be omitted, and both that omission
    and float32 geometry must satisfy the requested moment residual. Refuse
    clipping, collapsed geometry, backward normals and significant grazing
    mass instead of silently changing the requested distribution.

    ``origin`` is (u, v, depth); add ``position_origin_camera`` to returned
    vertices before interpreting them in the original camera frame. Clipping
    still uses original depths. ``precision_omissions`` identifies source atoms
    the caller has found to collapse after its final coordinate conversion;
    their mass remains included in the original target and omission bound.
    """
    def finite(value):
        return type(value) in (int, float) and math.isfinite(value)

    if len(rect) != 4 or not all(finite(v) for v in rect):
        raise ValueError('Finite rectangle required')
    left, bottom, right, top = rect
    if left >= right or bottom >= top:
        raise ValueError('Positive projected rectangle required')
    area = (right - left) * (top - bottom)
    if not math.isfinite(area) or area <= 0:
        raise ValueError('Projected area exceeds numerical range')
    if not all(finite(v) for v in (depth, near, far)) or not 0 < near < depth < far:
        raise ValueError('Depth must lie inside positive near/far bounds')
    if not finite(max_slope) or not .01 <= max_slope <= 64:
        raise ValueError('Invalid slope bound')
    if type(triangle_budget) is not int or not 2 <= triangle_budget <= 8:
        raise ValueError('Invalid triangle budget')
    if not finite(omitted_mass_tolerance) or not 0 <= omitted_mass_tolerance <= 1e-6:
        raise ValueError('Invalid omitted mass tolerance')
    if not finite(residual_tolerance) or not 1e-8 <= residual_tolerance <= 1e-3:
        raise ValueError('Invalid residual tolerance')
    if not 1 <= len(atoms) <= 4:
        raise ValueError('One to four weighted directions required')
    if (not isinstance(precision_omissions,(list,tuple)) or len(precision_omissions)>4
        or any(type(i) is not int or not 0<=i<len(atoms) for i in precision_omissions)
        or len(set(precision_omissions))!=len(precision_omissions)):
        raise ValueError('Invalid precision omission indices')
    if anchor is not None and (len(anchor) != 2 or not all(finite(v) for v in anchor)):
        raise ValueError('Finite plane depth anchor required')
    if origin is not None and (len(origin)!=3 or not all(finite(v) for v in origin)):
        raise ValueError('Finite translated (u,v,depth) origin required')
    ou,ov,od=origin if origin is not None else (0.,0.,0.)
    kept = []
    omitted = 0.
    unsupported_mass=precision_mass=0.
    source = []
    for source_index,atom in enumerate(atoms):
        cancelled()
        weight, direction = atom['weight'], atom['direction']
        if not finite(weight) or weight <= 0 or len(direction) != 3 or not all(finite(v) for v in direction):
            raise ValueError('Positive finite weight and unit direction required')
        x, y, z = direction
        if abs(math.hypot(x, y, z) - 1) > 1e-6:
            raise ValueError('Unit direction required')
        source.append({'weight': weight, 'direction': tuple(direction),'source_index':source_index})
        if z <= 0 or math.hypot(x, y) > max_slope * z:
            omitted += weight
            unsupported_mass+=weight
        elif source_index in precision_omissions:
            omitted+=weight;precision_mass+=weight
        else:
            kept.append(source[-1])
    mass = math.fsum(a['weight'] for a in source)
    if abs(mass - 1) > 1e-6:
        raise ValueError('Unit projected mass required')
    if omitted > omitted_mass_tolerance or not kept:
        if precision_mass:raise ValueError('Combined precision/unsupported omission mass exceeds bound')
        raise ValueError('Unsupported normal mass exceeds omission bound')
    target = moments(source)
    kept_mass = math.fsum(a['weight'] for a in kept)

    def f32(value):
        try:
            result = struct.unpack('<f', struct.pack('<f', value))[0]
        except (OverflowError, struct.error) as exc:
            raise ValueError('Geometry exceeds float32 range') from exc
        if not math.isfinite(result):
            raise ValueError('Geometry exceeds float32 range')
        return result

    # Endpoints are shared in projection even though each face owns its corners.
    while True:
        edges = [f32(left-ou)]
        cumulative = 0.
        for atom in kept[:-1]:
            cumulative += atom['weight'] / kept_mass
            edges.append(f32((left-ou) + (right - left) * cumulative))
        edges.append(f32(right-ou))
        collapsed = next((i for i, (a, b) in enumerate(zip(edges, edges[1:])) if a >= b), None)
        if collapsed is None:
            break
        candidate = kept[collapsed]['weight']
        if len(kept)==1 or omitted+candidate>omitted_mass_tolerance:
            raise ValueError('Projected intervals collapse in float32')
        precision_mass += candidate
        omitted += candidate
        del kept[collapsed]
        kept_mass = math.fsum(a['weight'] for a in kept)
    if 2 * len(kept) > triangle_budget:
        raise ValueError('Triangle budget exhausted')
    low, high = f32(bottom-ov), f32(top-ov)
    if low >= high or any(a >= b for a, b in zip(edges, edges[1:])):
        raise ValueError('Projected intervals collapse in float32')
    actual_area = (edges[-1] - edges[0]) * (high - low)
    area_error = abs(actual_area / area - 1)
    if not math.isfinite(area_error) or area_error > residual_tolerance:
        raise ValueError('Float32 projected-area error exceeds tolerance')
    vertices, faces, uvs, measured = [], [], [], []
    for index, atom in enumerate(kept):
        cancelled()
        a, b = edges[index:index + 2]
        centre_u, centre_v = (anchor[0]-ou,anchor[1]-ov) if anchor is not None else ((a + b) / 2, (low + high) / 2)
        nx, ny, nz = atom['direction']
        face = []
        for u, v in ((a, low), (b, low), (b, high), (a, high)):
            d = f32((depth-od) + nx / nz * (u - centre_u) + ny / nz * (v - centre_v))
            if not near < d+od < far:
                raise ValueError('Facet exceeds near/far bounds')
            face.append((u, v, -d))
            uvs.append((f32((u - (left-ou)) / (right - left)), f32((v - (bottom-ov)) / (top - bottom))))
        # Test both triangles after float32 conversion; a rounded quad need not
        # be exactly planar. Accumulate their real projected-area moments.
        for i, j, k in ((0, 1, 2), (0, 2, 3)):
            p, q, r = face[i], face[j], face[k]
            e = [q[t] - p[t] for t in range(3)]
            f = [r[t] - p[t] for t in range(3)]
            cross = (e[1]*f[2]-e[2]*f[1], e[2]*f[0]-e[0]*f[2], e[0]*f[1]-e[1]*f[0])
            length = math.hypot(*cross)
            if not math.isfinite(length) or not length or cross[2] <= 0:
                raise ValueError('Degenerate float32 triangle')
            measured.append({'weight': cross[2] / (2 * actual_area),
                             'direction': tuple(v / length for v in cross)})
        start = len(vertices)
        vertices.extend(face)
        faces.append(tuple(range(start, start + 4)))
    actual = moments(measured)
    residual = max(abs(a - b) for a, b in zip(target, actual))
    if residual > residual_tolerance:
        raise ValueError('Float32 facet moment residual exceeds tolerance')
    payload = b''.join(struct.pack('<3f', *p) for p in vertices)
    cancelled()
    return {'format': FORMAT if origin is None else 'mcpblender-projected-microfacets-v2', 'vertices': vertices, 'faces': faces, 'uvs': uvs,
            'position_origin_camera':[ou,ov,-od],
            'source_atom_indices':[a['source_index'] for a in kept],
            'rect': list(rect), 'depth': depth, 'near': near, 'far': far,
            'anchor': list(anchor) if anchor is not None else None,
            'max_slope': max_slope, 'triangle_budget': triangle_budget,
            'triangle_count': len(faces) * 2, 'omitted_mass': omitted,
            'unsupported_mass_omitted': unsupported_mass, 'precision_mass_omitted': precision_mass,
            'retained_mass': kept_mass, 'source_mass': mass,
            'source_moments': target, 'moments': actual, 'max_component_residual': residual,
            'projected_area_relative_error': area_error,
            'omitted_mass_tolerance': omitted_mass_tolerance,
            'residual_tolerance': residual_tolerance,
            'depth_bounds': [min(od-v[2] for v in vertices), max(od-v[2] for v in vertices)],
            'vertices_sha256': hashlib.sha256(payload).hexdigest(),
            'scope': 'Projected-area moments only; no optical, occlusion, filtering or angular equivalence guarantee'}
