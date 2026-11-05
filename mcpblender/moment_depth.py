"""Directional, witness-anchored projected geometry from archived input moments."""
from array import array
import math
from . import botany, capture_data, depth_tiles, normal_moments, normal_quadrature, projected_microfacets

FORMAT = 'mcpblender-moment-depth-patches-v1'
TOLERANCE = 1e-5


def rotate(values, axes):
    x, y, z, xx, xy, xz, yy, yz, zz = values
    q = ((xx, xy, xz), (xy, yy, yz), (xz, yz, zz))
    mean = [capture_data.dot((x, y, z), axis) for axis in axes]
    second = [[sum(axes[i][a]*q[a][b]*axes[j][b] for a in range(3) for b in range(3)) for j in range(3)] for i in range(3)]
    return mean + [second[0][0], second[0][1], second[0][2], second[1][1], second[1][2], second[2][2]]


def geometry(decoded, metadata, view, p, *, cancelled=lambda: None, progress=lambda v: None):
    if not metadata.get('material_fields', {}).get('normal_moments'):
        raise ValueError('Moment facets require captured input moments; recapture with normal_moments=true')
    w, h, camera, axes, root, root_axes, squares, span, near, far = depth_tiles.frame(decoded, metadata, view, p)
    ch = decoded['channels']
    names = ['TreeCapture.MCP_SurfaceWeight.X', *normal_moments.channels()]
    if any(name not in ch or len(ch[name]) != w*h for name in names):
        raise ValueError('Moment facet input channels missing or lengths differ')
    # Reuse the proven bounded witness/partial-edge policy, not its flat buffers.
    base = depth_tiles._geometry(decoded, metadata, view, p, cancelled=cancelled, progress=progress)
    vertices, uvs, faces, records = array('f'), array('f'), [], []
    low, high = [math.inf]*3, [-math.inf]*3
    work = fits = omitted_mass_sum = 0
    maximum_residual = maximum_adjustment = maximum_omission = maximum_area_error = 0.
    maximum_unsupported = maximum_precision = 0.
    weight = ch[names[0]]

    def charge(amount):
        nonlocal work
        work += amount
        if work > p['max_refinement_work']:
            raise ValueError('Moment facet reconstruction work budget exceeded')

    for index, record in enumerate(base['patch_records']):
        cancelled()
        if index % 32 == 0:
            progress({'phase': 'reconstructing normal-moment depth facets', 'completed': index,
                      'total': len(base['patch_records']), 'triangles': 2*len(faces), 'refinement_work': work})
        x, y, right, bottom = record['pixel_rect']
        total_weight = 0.
        sums = [0.]*9
        for yy in range(y, bottom):
            cancelled()
            for xx in range(x, right):
                charge(10)
                i = yy*w+xx
                if ch['TreeCapture.Combined.A'][i] <= p['alpha_threshold']:
                    continue
                value = weight[i]
                if not math.isfinite(value) or not 1e-6 < value <= 1+1e-5:
                    raise ValueError('Moment facets require valid captured surface weights')
                data = [ch[name][i] for name in names[1:]]
                if not all(math.isfinite(v) for v in data):
                    raise ValueError('Moment facets require finite input moments')
                # Validate every contributing pixel, not just a plausible average.
                # Sylvester's criterion on covariance + tolerance*I bounds its
                # least eigenvalue without running a factorization per pixel.
                q = [v/value for v in data]
                nx, ny, nz, xx2, xy, xz, yy2, yz, zz2 = q
                a, b, c = xx2-nx*nx+TOLERANCE, xy-nx*ny, xz-nx*nz
                d, e, f = yy2-ny*ny+TOLERANCE, yz-ny*nz, zz2-nz*nz+TOLERANCE
                if (any(abs(v)>1+TOLERANCE for v in q) or abs(xx2+yy2+zz2-1)>TOLERANCE
                    or a<=0 or a*d-b*b<=0 or a*d*f+2*b*c*e-a*e*e-d*c*c-f*b*b<=0):
                    raise ValueError('Moment facets require valid per-pixel unit input moments')
                total_weight += value
                for j, v in enumerate(data):
                    sums[j] += v
        charge(220)  # Conservative 64 eigen rotations + 3*52 bisections per fit.
        world_moments = [v/total_weight for v in sums]
        fitted = normal_quadrature.fit(world_moments, cancelled=cancelled)
        atoms = [{'weight': a['weight'], 'direction': [capture_data.dot(a['direction'], axis) for axis in axes]} for a in fitted['atoms']]
        target = rotate(world_moments, axes)
        rect = ((x/w-.5)*span, (.5-bottom/h)*span, (right/w-.5)*span, (.5-y/h)*span)
        witness_x, witness_y = record['witness_pixel']
        anchor = (((witness_x+.5)/w-.5)*span, (.5-(witness_y+.5)/h)*span)
        try:
            piece = projected_microfacets.build(rect, atoms, depth=record['depth_scene_units'], near=near, far=far,
                max_slope=p['max_slope'], anchor=anchor, cancelled=cancelled)
        except ValueError as exc:
            raise ValueError('Moment facet tile '+str(record['pixel_rect'])+': '+str(exc)) from exc
        if 2*(len(faces)+len(piece['faces'])) > p['max_triangles']:
            raise ValueError('Depth patch triangle budget exceeded by moment facets')
        start = len(vertices)//3
        for u, v, z in piece['vertices']:
            world = [camera[k]+axes[0][k]*u+axes[1][k]*v+axes[2][k]*z for k in range(3)]
            local = [capture_data.dot([world[k]-root[k] for k in range(3)], root_axes[j])/squares[j] for j in range(3)]
            if any(not math.isfinite(v) or abs(v)>1e20 for v in local):
                raise ValueError('Moment facet coordinates exceed native range')
            vertices.extend(local)
            uvs.extend((u/span+.5, v/span+.5))
            for j in range(3):
                low[j] = min(low[j], vertices[-3+j])
                high[j] = max(high[j], vertices[-3+j])
        # Check the final root-local float32 buffers, including normal directions,
        # camera projection and depth, rather than trusting preconversion vertices.
        positions = []
        for i in range(start, len(vertices)//3):
            local = vertices[3*i:3*i+3]
            world = [root[k]+sum(root_axes[j][k]*local[j] for j in range(3))-camera[k] for k in range(3)]
            actual = [capture_data.dot(world, axis) for axis in axes]
            intended = piece['vertices'][i-start]
            if max(abs(actual[j]-intended[j]) for j in (0, 1)) > span/w*TOLERANCE:
                raise ValueError('Root-local float32 facet projection error exceeds tolerance')
            if not near < -actual[2] < far:
                raise ValueError('Root-local float32 facet exceeds near/far bounds')
            positions.append(actual)
        measured = []
        for face in piece['faces']:
            for a, b, c in ((face[0], face[1], face[2]), (face[0], face[2], face[3])):
                e = [positions[b][j]-positions[a][j] for j in range(3)]
                f = [positions[c][j]-positions[a][j] for j in range(3)]
                cross = (e[1]*f[2]-e[2]*f[1], e[2]*f[0]-e[0]*f[2], e[0]*f[1]-e[1]*f[0])
                length = math.hypot(*cross)
                if not math.isfinite(length) or not length or cross[2] <= 0:
                    raise ValueError('Root-local float32 facet collapses')
                measured.append({'weight': cross[2]/2, 'direction': [v/length for v in cross]})
        area = math.fsum(a['weight'] for a in measured)
        area_error = abs(area/((rect[2]-rect[0])*(rect[3]-rect[1]))-1)
        if area_error > TOLERANCE:
            raise ValueError('Root-local float32 facet area error exceeds tolerance')
        for atom in measured:
            atom['weight'] /= area
        actual_moments = normal_quadrature.moments(measured)
        residual = max(abs(a-b) for a, b in zip(target, actual_moments))
        if residual > TOLERANCE:
            raise ValueError('Root-local float32 facet moment residual exceeds tolerance')
        faces.extend(tuple(start+i for i in face) for face in piece['faces'])
        fits += 1
        maximum_residual = max(maximum_residual, residual)
        maximum_area_error = max(maximum_area_error, area_error)
        maximum_adjustment = max(maximum_adjustment, fitted['max_numerical_adjustment'])
        maximum_omission = max(maximum_omission, piece['omitted_mass'])
        maximum_unsupported = max(maximum_unsupported, piece['unsupported_mass_omitted'])
        maximum_precision = max(maximum_precision, piece['precision_mass_omitted'])
        omitted_mass_sum += piece['omitted_mass']*total_weight
        records.append(record | {'facet_count': len(piece['faces']), 'plane_anchor_pixel': [witness_x+.5, witness_y+.5],
            'normal_input_weight': total_weight, 'normal_moments_camera': target,
            'max_component_residual': residual, 'quadrature_adjustment': fitted['max_numerical_adjustment'],
            'omitted_mass': piece['omitted_mass'], 'unsupported_mass_omitted': piece['unsupported_mass_omitted'],
            'precision_mass_omitted': piece['precision_mass_omitted'], 'projected_area_relative_error': area_error})
    report = base['report'] | {'format': FORMAT, 'patches': len(faces), 'triangles': 2*len(faces),
        'moment_tiles': fits, 'depth_anchor': 'WITNESS_PIXEL_CENTRE', 'refinement_work': work,
        'work_unit': '10 per visited tile pixel plus 220 per bounded tile quadrature fit',
        'max_component_residual': maximum_residual, 'moment_residual_tolerance': TOLERANCE,
        'max_working_matrix_adjustment': maximum_adjustment, 'max_omitted_mass': maximum_omission,
        'max_unsupported_mass_omitted': maximum_unsupported, 'max_precision_mass_omitted': maximum_precision,
        'surface_weighted_omitted_mass': omitted_mass_sum,
        'max_projected_area_relative_error': maximum_area_error,
        'bounds_root_local': {'min': low, 'max': high}, 'vertices_sha256': depth_tiles.floats_sha(vertices),
        'uv_sha256': depth_tiles.floats_sha(uvs),
        'normal_policy': 'Implicit geometric normals from captured input moments; raw normal texture retained as witness only.',
        'scope': 'Witness-anchored orthographic projected-area moment facets. Refuse unsupported mass/clipping/precision/budget; no fallback. Input moments are not renderer closure moments. No filtered-pixel, PBR, color/depth correlation, angular, shadow/wind or optical equivalence guarantee.'}
    report['geometry_sha256'] = botany.digest({k: v for k, v in report.items() if k != 'geometry_sha256'} | {'patch_records': records})
    return {'vertices': vertices, 'uvs': uvs, 'faces': faces, 'patch_records': records, 'report': report}
