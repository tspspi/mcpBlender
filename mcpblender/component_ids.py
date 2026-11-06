"""First-sample leaf-component identity, separate from material identity."""
import math
import re
from . import botany,capture_material_fields

FORMAT='mcpblender-native-component-ids-v1'
ATTRIBUTE='mcp_capture_leaf_component'
FIELDS=[{'key':'leaf_component','name':'MCP_LeafComponent','type':'VALUE'}]


def channels():return ['TreeCapture.MCP_LeafComponent.X']


def contract(fields,leaf_count,point_mesh,instancer,indices_sha256):
    capture_material_fields.validate(fields)
    def constant(binding):return binding.get('constant',binding.get('default')) if binding.get('source') is None else None
    for row in fields['materials']:
        b=row['bindings']
        if constant(b['alpha'])!=1 or constant(b['transmission_weight'])!=0 or constant(b['cull_weight'])!=0:
            raise ValueError('Component IDs require static opaque alpha=1, transmission=0 and disabled culling')
    if type(leaf_count) is not int or not 0<=leaf_count<=250000:raise ValueError('Invalid component leaf count')
    if any(v is not None and (not isinstance(v,str) or not 1<=len(v)<=256) for v in (point_mesh,instancer)) or (point_mesh is None)!=(instancer is None) or leaf_count and point_mesh is None:raise ValueError('Invalid component instancer inventory')
    if not isinstance(indices_sha256,str) or not re.fullmatch('[0-9a-f]{64}',indices_sha256):raise ValueError('Invalid component index digest')
    value={'format':FORMAT,'fields':[dict(v) for v in FIELDS],'attribute_type':'INSTANCER','source_attribute':'leaf_index',
           'derived_attribute':ATTRIBUTE,'offset':1,'structural_value':0,'samples':1,'point_mesh':point_mesh,'instancer':instancer,
           'leaf_count':leaf_count,'leaf_indices_sha256':indices_sha256,'material_fields_sha256':fields['fields_sha256'],
           'materials':[{'material':r['material'],'id':r['id']} for r in fields['materials']]}
    return value|{'components_sha256':botany.digest(value)}


def validate(value,fields):
    if not isinstance(value,dict):raise ValueError('Invalid component-ID contract')
    expected=contract(fields,value.get('leaf_count'),value.get('point_mesh'),value.get('instancer'),value.get('leaf_indices_sha256'))
    if value!=expected:raise ValueError('Component-ID contract changed')
    return value


def validate_header(header,value,fields):
    validate(value,fields);present={r['name']:r['pixel_type'] for r in header['channels']}
    for name in channels():
        if present.get(name)!=2:raise ValueError('Component-ID EXR lacks float32 channel: '+name)


def measure(geometry,weight,ids,leaf_count,threshold,*,cancelled=lambda:None):
    alpha=geometry['channels']['TreeCapture.Combined.A']
    if len(weight)!=len(alpha) or len(ids)!=len(alpha):raise ValueError('Component-ID channel lengths differ')
    counts={k:0 for k in ('covered_pixels','structural_pixels','leaf_pixels','invalid_alpha','nonbinary_alpha','invalid_surface_weight','nonfinite_ids','noninteger_ids','out_of_range_ids')}
    seen=set();maximum_rounding_error=0.
    for i,a in enumerate(alpha):
        if i%8192==0:cancelled()
        if not math.isfinite(a) or not -1e-6<=a<=1+1e-6:counts['invalid_alpha']+=1;continue
        if a<=threshold:continue
        counts['covered_pixels']+=1;counts['nonbinary_alpha']+=abs(a-1)>1e-5
        w=weight[i]
        if not math.isfinite(w) or abs(w-1)>1e-5:counts['invalid_surface_weight']+=1;continue
        value=ids[i]/w
        if not math.isfinite(value):counts['nonfinite_ids']+=1;continue
        error=abs(value-round(value));maximum_rounding_error=max(maximum_rounding_error,error)
        if error>1e-5:counts['noninteger_ids']+=1;continue
        index=round(value)
        if not 0<=index<=leaf_count:counts['out_of_range_ids']+=1;continue
        if index==0:counts['structural_pixels']+=1
        else:counts['leaf_pixels']+=1;seen.add(index-1)
    return {'method':FORMAT,**counts,'source_leaf_count':leaf_count,'distinct_leaf_count':len(seen),'leaf_index_preview':sorted(seen)[:16],
            'observed_leaf_indices_sha256':botany.digest(sorted(seen)),'maximum_integer_rounding_error':maximum_rounding_error,
            'integer_ids_valid':counts['covered_pixels']>0 and not any(v for k,v in counts.items() if k not in {'covered_pixels','structural_pixels','leaf_pixels'}),
            'scope':'One-sample opaque-surface renderer AOV: zero denotes structural wood/shoot geometry, positive values encode native semantic leaf_index+1. Not a material ID, persistent instance ID, inferred surface match, full visibility census or transport certificate. Preview is bounded to sixteen indices.'}


def inspect_view(path,sha,geometry,threshold,value,*,cancelled=lambda:None,progress=lambda value:None):
    from . import exr_scanline
    names=['TreeCapture.MCP_SurfaceWeight.X',*channels()]
    data=exr_scanline.decode(path,names,expected_sha256=sha,cancelled=cancelled,progress=progress)['channels']
    return measure(geometry,data[names[0]],data[names[1]],value['leaf_count'],threshold,cancelled=cancelled)
