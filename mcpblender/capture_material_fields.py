"""Versioned shader-input fields for native tree captures, not lit-sprite colors."""
import math
from . import botany
FORMAT='mcpblender-native-material-fields-v1'
FIELDS=[{'key':key,'name':'MCP_'+name,'type':kind} for key,name,kind in (
 ('base_color','BaseColor','COLOR'),('roughness','Roughness','VALUE'),('metallic','Metallic','VALUE'),('alpha','Alpha','VALUE'),
 ('emission_color','Emission','COLOR'),('emission_strength','EmissionStrength','VALUE'),('ior','IOR','VALUE'),('transmission_weight','Transmission','VALUE'),
 ('thin_color','ThinColor','COLOR'),('thin_weight','ThinWeight','VALUE'),('thin_mode','ThinMode','VALUE'),('cull_weight','CullWeight','VALUE'),
 ('surface_weight','SurfaceWeight','VALUE'),('material_id','MaterialId','VALUE'))]


def channels():return ['TreeCapture.'+row['name']+'.'+axis for row in FIELDS for axis in ('RGB' if row['type']=='COLOR' else 'X')]


def validate(value):
    if value.get('format')!=FORMAT or value.get('fields')!=FIELDS or value.get('fields_sha256')!=botany.digest({k:v for k,v in value.items() if k!='fields_sha256'}):raise ValueError('Native material field contract changed')
    materials=value.get('materials',[])
    if not 1<=len(materials)<=32 or len({m['material'] for m in materials})!=len(materials) or [m['id'] for m in materials]!=list(range(1,len(materials)+1)):raise ValueError('Invalid native material field inventory')
    if any(m['model'] not in {'PRINCIPLED','MANAGED_THIN_FOLIAGE'} or set(m['bindings'])!={r['key'] for r in FIELDS} for m in materials):raise ValueError('Native material field bindings changed')
    for material in materials:
        if material.get('thickness_m') is not None:raise ValueError('Native material fields do not infer physical thickness')
        for field in FIELDS:
            binding=material['bindings'][field['key']]
            if not isinstance(binding,dict):raise ValueError('Invalid material field binding')
            if 'constant' in binding:
                if set(binding)!={'constant'}:raise ValueError('Ambiguous constant material field')
                default=binding['constant']
            else:
                if set(binding)!={'node','socket','source','default'} or not all(isinstance(binding[k],str) and binding[k] for k in ('node','socket')):raise ValueError('Invalid linked material field')
                source=binding['source']
                if source is not None and (not isinstance(source,dict) or set(source)!={'node','socket'} or not all(isinstance(v,str) and v for v in source.values())):raise ValueError('Invalid material field source socket')
                default=binding['default']
            values=default if isinstance(default,list) else [default]
            width=4 if field['type']=='COLOR' else 1
            if len(values)!=width or any(type(v) not in (int,float) or not math.isfinite(v) for v in values):raise ValueError('Invalid material field default width/value')
        if material['bindings']['surface_weight']!={'constant':1.} or material['bindings']['material_id']!={'constant':float(material['id'])} or material['bindings']['thin_mode']!={'constant':float(material['model']=='MANAGED_THIN_FOLIAGE')}:raise ValueError('Native material field witness/identity changed')
    if 'normal_moments' in value:
        from . import normal_moments
        normal_moments.validate(value['normal_moments'],materials)
    return value


def validate_header(header,value):
    validate(value);present={r['name']:r['pixel_type'] for r in header['channels']}
    names=channels()
    if 'normal_moments' in value:
        from . import normal_moments
        names+=normal_moments.channels()
    for name in names:
        if present.get(name)!=2:raise ValueError('Native material field EXR lacks float32 channel: '+name)


def groups():
    """Keep each requested output below the decoder budget even at 2048px."""
    result=[];pending=[];count=1
    for field in FIELDS:
        if field['key']=='surface_weight':continue
        width=3 if field['type']=='COLOR' else 1
        if count+width>12:result.append(pending);pending=[];count=1
        pending.append(field);count+=width
    if pending:result.append(pending)
    return result


def normal_filtering(geometry,weight,threshold,*,cancelled=lambda:None):
    """Separate coverage from the length of a filtered first normal moment.

    Native opaque-surface controls establish common accumulation weights for the
    Normal pass and constant-one AOV. The ratio is diagnostic, not a recovered
    distribution, BSDF roughness or an instruction to scale material energy.
    """
    channels=geometry['channels'];alpha=channels['TreeCapture.Combined.A']
    normals=[channels['TreeCapture.Normal.'+axis] for axis in 'XYZ']
    if any(len(v)!=len(alpha) for v in [weight,*normals]):raise ValueError('Normal filtering channel lengths differ')
    counts={key:0 for key in ('covered_pixels','invalid_alpha','invalid_surface_weight','missing_surface_weight','nonfinite_normals','conditional_length_over_one','zero_conditional_normals')}
    groups={key:{field:{'count':0,'min':math.inf,'max':-math.inf,'sum':0.,'squared':0.} for field in ('raw_length','surface_weight','conditional_length')} for key in ('covered','opaque','partial')}
    for i,a in enumerate(alpha):
        if i%8192==0:cancelled()
        if not math.isfinite(a) or not -1e-6<=a<=1+1e-6:counts['invalid_alpha']+=1;continue
        if a<=threshold:continue
        counts['covered_pixels']+=1;w=weight[i]
        if not math.isfinite(w) or w<0 or w>1+1e-5:counts['invalid_surface_weight']+=1;continue
        if w<=1e-6:counts['missing_surface_weight']+=1;continue
        xyz=[row[i] for row in normals]
        if not all(math.isfinite(v) for v in xyz):counts['nonfinite_normals']+=1;continue
        raw=math.sqrt(sum(v*v for v in xyz));conditional=raw/w
        counts['conditional_length_over_one']+=conditional>1+1e-4;counts['zero_conditional_normals']+=conditional<1e-6
        values={'raw_length':raw,'surface_weight':w,'conditional_length':conditional}
        for key in ('covered','opaque' if a>=1-1e-6 else 'partial'):
            for field,value in values.items():
                row=groups[key][field];row['count']+=1;row['min']=min(row['min'],value);row['max']=max(row['max'],value);row['sum']+=value;row['squared']+=value*value
    result={}
    for key,fields in groups.items():
        result[key]={field:{'count':r['count'],'min':r['min'] if r['count'] else None,'max':r['max'] if r['count'] else None,
                           'mean':r['sum']/r['count'] if r['count'] else None,'rms':math.sqrt(r['squared']/r['count']) if r['count'] else None} for field,r in fields.items()}
    return {'method':'SURFACE_CONDITIONAL_NORMAL_LENGTH_V1',**counts,'groups':result,
            'interpretation':'Normal-pass vector length divided by the constant-one surface AOV weight, not beauty alpha. Native opaque-surface coverage controls establish common accumulation weights. Below-unit conditional length can reflect directional mixing; it does not identify a unique orientation distribution or BSDF, and is not an albedo/roughness correction. Bounds violations and unavailable observations are counted without clamping.'}


def inspect_view(path,expected_sha256,geometry,threshold,contract,*,cancelled=lambda:None,progress=lambda value:None,quadrature_pixels=0):
    import math
    from . import exr_scanline
    validate(contract);output={};counts={'covered_with_surface_weight':0,'covered_without_surface_weight':0,'invalid_surface_weight':0,'fractional_material_id_pixels':0}
    alpha=geometry['channels']['TreeCapture.Combined.A'];weight_name='TreeCapture.MCP_SurfaceWeight.X';weight_stats=None;filtering=None
    for group in groups():
        names=[weight_name,*('TreeCapture.'+f['name']+'.'+axis for f in group for axis in ('RGB' if f['type']=='COLOR' else 'X'))]
        decoded=exr_scanline.decode(path,names,expected_sha256=expected_sha256,cancelled=cancelled,progress=progress);weight=decoded['channels'][weight_name]
        if weight_stats is None:
            filtering=normal_filtering(geometry,weight,threshold,cancelled=cancelled)
            low=math.inf;high=-math.inf;total=0.;count=covered=0
            for i,(a,w) in enumerate(zip(alpha,weight)):
                if i%8192==0:cancelled()
                counts['invalid_surface_weight']+=not math.isfinite(w) or w<0 or w>1+1e-5
                if not math.isfinite(a) or not a>threshold:continue
                covered+=1
                if math.isfinite(w) and w>1e-6:low=min(low,w);high=max(high,w);total+=w;count+=1
            counts['covered_with_surface_weight']=count;counts['covered_without_surface_weight']=covered-count
            weight_stats={'min':low if count else None,'max':high if count else None,'mean':total/count if count else None}
        for field in group:
            rows=[decoded['channels']['TreeCapture.'+field['name']+'.'+axis] for axis in ('RGB' if field['type']=='COLOR' else 'X')];width=len(rows);low=[math.inf]*width;high=[-math.inf]*width;sums=[0.]*width;count=invalid=0
            for i,a in enumerate(alpha):
                if i%8192==0:cancelled()
                w=weight[i]
                if not math.isfinite(a) or not a>threshold or not math.isfinite(w) or w<=1e-6:continue
                values=[row[i]/w for row in rows]
                if not all(math.isfinite(v) for v in values):invalid+=1;continue
                count+=1
                for j,v in enumerate(values):low[j]=min(low[j],v);high[j]=max(high[j],v);sums[j]+=v
                if field['key']=='material_id':counts['fractional_material_id_pixels']+=abs(values[0]-round(values[0]))>.001
            output[field['key']]={'count':count,'nonfinite_pixels':invalid,'min':low if count else None,'max':high if count else None,'mean':[v/count for v in sums] if count else None}
    extra={}
    if contract.get('normal_moments'):
        from . import normal_moments
        extra['normal_moments']=normal_moments.inspect_view(path,expected_sha256,geometry,threshold,cancelled=cancelled,progress=progress,quadrature_pixels=quadrature_pixels)
    return {**extra,'fields_sha256':contract['fields_sha256'],**counts,'raw_surface_weight':weight_stats,'normal_filtering':filtering,'normalized_inputs':output,
            'interpretation':'Straight input statistics divide raw AOVs by their constant-one surface weight, not beauty alpha. Integer averaged material IDs do not prove a single material. No clamping, physical thickness inference or optical-equivalence gate.'}
