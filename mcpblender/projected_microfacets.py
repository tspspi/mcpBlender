"""Bounded camera-frame geometry for positive projected-area normal mixtures.

This is an internal geometry primitive, not an optical-equivalence guarantee.
Coordinates are (u, v, -depth), with the camera along positive frame Z.
"""
import hashlib
import math
import struct

from .normal_quadrature import moments

FORMAT = 'mcpblender-projected-microfacets-v1'


def build(rect, atoms, *, depth, near, far, max_slope=16.,
          triangle_budget=8, omitted_mass_tolerance=1e-6,
          residual_tolerance=1e-5, cancelled=lambda: None):
    """Partition a rectangle into at most four independent planar strips.

    Only negligible unsupported mass may be omitted, and both that omission
    and float32 geometry must satisfy the requested moment residual. Refuse
    clipping, collapsed geometry, backward normals and significant grazing
    mass instead of silently changing the requested distribution.
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
    if not finite(max_slope) or not 0 < max_slope <= 16:
        raise ValueError('Invalid slope bound')
    if type(triangle_budget) is not int or not 2 <= triangle_budget <= 8:
        raise ValueError('Invalid triangle budget')
    if not finite(omitted_mass_tolerance) or not 0 <= omitted_mass_tolerance <= 1e-6:
        raise ValueError('Invalid omitted mass tolerance')
    if not finite(residual_tolerance) or not 1e-8 <= residual_tolerance <= 1e-3:
        raise ValueError('Invalid residual tolerance')
    if not 1 <= len(atoms) <= 4:
        raise ValueError('One to four weighted directions required')
    kept = []
    omitted = 0.
    source = []
    for atom in atoms:
        cancelled()
        weight, direction = atom['weight'], atom['direction']
        if not finite(weight) or weight <= 0 or len(direction) != 3 or not all(finite(v) for v in direction):
            raise ValueError('Positive finite weight and unit direction required')
        x, y, z = direction
        if abs(math.hypot(x, y, z) - 1) > 1e-6:
            raise ValueError('Unit direction required')
        source.append({'weight': weight, 'direction': tuple(direction)})
        if z <= 0 or math.hypot(x, y) > max_slope * z:
            omitted += weight
        else:
            kept.append(source[-1])
    mass = math.fsum(a['weight'] for a in source)
    if abs(mass - 1) > 1e-6:
        raise ValueError('Unit projected mass required')
    if omitted > omitted_mass_tolerance or not kept:
        raise ValueError('Unsupported normal mass exceeds omission bound')
    if 2 * len(kept) > triangle_budget:
        raise ValueError('Triangle budget exhausted')
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
    edges = [f32(left)]
    cumulative = 0.
    for atom in kept[:-1]:
        cumulative += atom['weight'] / kept_mass
        edges.append(f32(left + (right - left) * cumulative))
    edges.append(f32(right))
    low, high = f32(bottom), f32(top)
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
        centre_u, centre_v = (a + b) / 2, (low + high) / 2
        nx, ny, nz = atom['direction']
        face = []
        for u, v in ((a, low), (b, low), (b, high), (a, high)):
            d = f32(depth + nx / nz * (u - centre_u) + ny / nz * (v - centre_v))
            if not near < d < far:
                raise ValueError('Facet exceeds near/far bounds')
            face.append((u, v, -d))
            uvs.append((f32((u - left) / (right - left)), f32((v - bottom) / (top - bottom))))
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
    return {'format': FORMAT, 'vertices': vertices, 'faces': faces, 'uvs': uvs,
            'rect': list(rect), 'depth': depth, 'near': near, 'far': far,
            'max_slope': max_slope, 'triangle_budget': triangle_budget,
            'triangle_count': len(faces) * 2, 'omitted_mass': omitted,
            'retained_mass': kept_mass, 'source_mass': mass,
            'source_moments': target, 'moments': actual, 'max_component_residual': residual,
            'projected_area_relative_error': area_error,
            'omitted_mass_tolerance': omitted_mass_tolerance,
            'residual_tolerance': residual_tolerance,
            'depth_bounds': [min(-v[2] for v in vertices), max(-v[2] for v in vertices)],
            'vertices_sha256': hashlib.sha256(payload).hexdigest(),
            'scope': 'Projected-area moments only; no optical, occlusion, filtering or angular equivalence guarantee'}
