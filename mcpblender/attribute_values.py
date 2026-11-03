"""Canonical storage rows for the editable mesh numeric attribute profile."""
import math

TYPES={'FLOAT':('value',1,'f'),'INT':('value',1,'i'),'BOOLEAN':('value',1,'i'),
       'FLOAT_VECTOR':('vector',3,'f'),'FLOAT_COLOR':('color',4,'f')}
DOMAINS={'POINT','EDGE','FACE','CORNER'}
FLOAT_MAX=3.4028234663852886e38


def row(kind,value):
    if kind not in TYPES:raise ValueError('Unsupported editable attribute type')
    size=TYPES[kind][1]
    if kind=='BOOLEAN':
        if type(value)!=bool:raise ValueError('BOOLEAN attributes require true/false values')
        return value
    if kind=='INT':
        if type(value)!=int or not -2147483648<=value<=2147483647:raise ValueError('INT attributes require signed 32-bit integers')
        return value
    values=value if size>1 else [value]
    if not isinstance(values,(list,tuple)) or len(values)!=size or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>FLOAT_MAX for v in values):raise ValueError('Attribute row requires finite float32 components of the declared size')
    if kind=='FLOAT_COLOR' and any(v<0 for v in values):raise ValueError('FLOAT_COLOR uses nonnegative linear RGBA values')
    return [float(v) for v in values] if size>1 else float(values[0])


def safe_name(value):
    if not isinstance(value,str) or not value or value!=value.strip() or len(value.encode())>63 or value.startswith('.') or any(ord(c)<32 or ord(c)==127 for c in value):raise ValueError('Attribute name must be a noninternal name up to 63 UTF-8 bytes without controls/outer whitespace')
    return value
