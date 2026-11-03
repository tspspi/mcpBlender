"""Versioned engine-independent source parameters, distinct from baked PBR maps."""
import math
import re
from . import botany
FORMAT='mcpblender-vegetation-materials-v1'
PORTS=('Base Color','Roughness','Metallic','Alpha','Normal','Emission Color','Emission Strength','IOR','Transmission Weight')
MAPS=('BASE_COLOR','NORMAL','ORM','ALPHA','THICKNESS','TRANSMISSION')


def validate(document):
    if document.get('format')!=FORMAT or document.get('contract_sha256')!=botany.digest({k:v for k,v in document.items() if k!='contract_sha256'}):raise ValueError('Vegetation material contract version/content binding changed')
    materials=document['materials'];slots=document['slots']
    if not 1<=len(materials)<=32 or len({m['name'] for m in materials})!=len(materials) or len(slots)>32:raise ValueError('Invalid vegetation material inventory')
    names={m['name'] for m in materials}
    if document.get('materials_sha256')!=botany.digest(materials):raise ValueError('Vegetation material source binding changed')
    if set(document['used_slots'])!=set(slots):raise ValueError('Vegetation used-slot inventory changed')
    if any(not values or any(type(i)!=int or not 0<=i<len(slots[key]) for i in values) for key,values in document['used_slots'].items()):raise ValueError('Invalid vegetation used-slot indices')
    if any(not isinstance(key,str) or not isinstance(value,list) or not 1<=len(value)<=16 or any(name not in names for name in value) for key,value in slots.items()):raise ValueError('Vegetation material slot binding changed')
    if set(document['source_uv'])!=set(slots):raise ValueError('Vegetation UV requirement inventory changed')
    expected_missing=missing_uv(materials,slots,document['source_uv'])
    if document['missing_detail_uv']!=expected_missing:raise ValueError('Vegetation missing-UV requirements changed')
    for material in materials:
        if material['model'] not in {'PRINCIPLED','MANAGED_THIN_FOLIAGE'} or type(material['double_sided'])!=bool or set(material['maps'])!=set(MAPS) or any(v is not None for v in material['maps'].values()):raise ValueError('Source-parameter contract cannot claim baked maps')
        if material['alpha']['mode'] not in {'OPAQUE','UNRESOLVED'} or material['alpha']['cutoff'] is not None or material['transmission']['thickness_m'] is not None:raise ValueError('Unsupported alpha/thickness claim in source material parameters')
        if material['transmission']['model'] not in {'NONE','ARTISTIC_DIFFUSE_BACKLIGHT','PRINCIPLED_SURFACE'}:raise ValueError('Unsupported transmission interpretation')
        if set(material['front_inputs'])!=set(PORTS):raise ValueError('Material front input inventory changed')
        for port,value in material['front_inputs'].items():
            if value['source'] not in {'UNLINKED','CONSTANT_FRONT','NODE_GRAPH','GEOMETRY_NORMAL','TEXTURE_IMAGE'}:raise ValueError('Unsupported material input provenance')
            if value['source'] in {'NODE_GRAPH','GEOMETRY_NORMAL','TEXTURE_IMAGE'} and value['value'] is not None:raise ValueError('Linked/normal inputs cannot claim uniform material values')
            if value['source']=='TEXTURE_IMAGE':
                binding=value.get('image_binding',{});size=binding.get('size')
                if not re.fullmatch('[0-9a-f]{64}',str(binding.get('image_sha256',''))) or not isinstance(size,list) or len(size)!=2 or any(type(v)!=int or v<=0 for v in size) or size[0]*size[1]>4*1024**2 or not binding.get('uv_map') or not binding.get('color_space') or binding.get('output') not in {'Color','Alpha'}:raise ValueError('Invalid frozen source image binding')
            if value['source'] in {'UNLINKED','CONSTANT_FRONT'}:
                width=4 if port in {'Base Color','Emission Color'} else 1
                if width==4 and (not isinstance(value['value'],list) or len(value['value'])!=4) or width==1 and type(value['value']) not in (int,float):raise ValueError('Material input component count changed')
            row=value['value'] if isinstance(value['value'],list) else [value['value']]
            if any(v is not None and (type(v) not in (int,float) or not math.isfinite(v)) for v in row):raise ValueError('Nonfinite material parameter')
        if material['model']=='MANAGED_THIN_FOLIAGE':
            if material['alpha']['mode']!='OPAQUE' or material['transmission']['model']!='ARTISTIC_DIFFUSE_BACKLIGHT' or len(material['source_base_colors']['back'])!=4:raise ValueError('Thin-leaf contract must separate opaque geometry, back color and artistic backlighting')
        if material['delivery']!='NATIVE_PARAMETERS' or material['portable_optical_equivalence'] is not False:raise ValueError('Source parameters do not establish portable optical equivalence')
    return {'materials':len(materials),'slots':len(slots),'contract_sha256':document['contract_sha256'],'format':FORMAT}


def missing_uv(materials,slots,source_uv):
    by_name={m['name']:m for m in materials};result={}
    for asset,names in slots.items():
        result[asset]=[{'material':name,'uv_map':by_name[name]['detail']['uv_map']} for name in dict.fromkeys(names) if by_name[name]['detail'] and by_name[name]['detail']['uv_map'] not in source_uv[asset]]
    return result


def finish(materials,slots,used_slots=None,source_uv=None):
    result={'format':FORMAT,'materials':sorted(materials,key=lambda v:v['name']),'slots':dict(sorted(slots.items())),'used_slots':used_slots if used_slots is not None else {key:list(range(len(value))) for key,value in slots.items()}}
    result['source_uv']=source_uv or {key:[] for key in slots}
    result['missing_detail_uv']=missing_uv(result['materials'],slots,result['source_uv'])
    result['materials_sha256']=botany.digest(result['materials'])
    result['contract_sha256']=botany.digest(result);validate(result);return result


def delivery(path,contract,asset):
    from .lod_files import read_glb
    from .package_files import image_info,texture_infos
    import hashlib
    validate(contract);doc,binary=read_glb(path);materials=doc.get('materials',[])
    used={p['material'] for mesh in doc['meshes'] for p in mesh['primitives'] if 'material' in p}
    if any(type(i)!=int or not 0<=i<len(materials) for i in used):raise ValueError('Invalid glTF vegetation material index')
    expected={contract['slots'][asset][i] for i in contract['used_slots'][asset]}
    if {materials[i].get('name') for i in used}!=expected:raise ValueError('Encoded vegetation material names differ from source slots')
    rows=[];images=set()
    for i in sorted(used):
        material=materials[i];textures=[]
        for spec in texture_infos(material):
            index=spec['index']
            if type(index)!=int or not 0<=index<len(doc.get('textures',[])):raise ValueError('Invalid vegetation texture binding')
            source=doc['textures'][index]['source'];images.add(source);channel=spec.get('extensions',{}).get('KHR_texture_transform',{}).get('texCoord',spec.get('texCoord',0))
            if type(channel)!=int or not 0<=channel<=7 or any('TEXCOORD_'+str(channel) not in p['attributes'] for mesh in doc['meshes'] for p in mesh['primitives'] if p.get('material')==i):raise ValueError('Encoded vegetation material requests a missing UV channel')
            textures.append({'texture':index,'image':source,'texcoord':channel})
        rows.append({'encoded':material,'name':material['name'],'double_sided':bool(material.get('doubleSided',False)),'alpha_mode':material.get('alphaMode','OPAQUE'),
                     'alpha_cutoff':material.get('alphaCutoff') if material.get('alphaMode')=='MASK' else None,'pbr':material.get('pbrMetallicRoughness',{}),'textures':textures})
    image_rows=[]
    for index in sorted(images):
        if type(index)!=int or not 0<=index<len(doc.get('images',[])):raise ValueError('Invalid vegetation image index')
        image=doc['images'][index];view=doc['bufferViews'][image['bufferView']];start=view.get('byteOffset',0);payload=binary[start:start+view['byteLength']];info=image_info(payload,image['mimeType'])
        image_rows.append({'image':index,'mime':image['mimeType'],'width':info['width'],'height':info['height'],'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()})
    return {'materials':rows,'images':image_rows,'rgba8_base_bytes_estimate':sum(v['width']*v['height']*4 for v in image_rows),
            'scope':'Encoded material/texture inventory and source-slot names. RGBA8 base estimate excludes mipmaps/driver compression; no optical equivalence.'}
