"""Bounded JSON lines for native text editors with costly long-line insertion."""
import json


def chunks(value, *, line_limit=4096, chunk_limit=256*1024, max_line=65536):
    """Insert whitespace only after structural commas; never split JSON strings.

    Limits count ASCII bytes, since the encoder escapes non-ASCII characters.
    A single oversized token refuses rather than entering an unbounded native
    line write. Callers retain ownership of partial output and its rollback.
    """
    if not 1<=line_limit<=max_line or chunk_limit<line_limit:
        raise ValueError('Invalid JSON text line/chunk limits')
    encoded=json.dumps(value,sort_keys=True,allow_nan=False)
    quoted=escaped=False;start=0;lines=[];size=0
    for index,char in enumerate(encoded):
        if quoted:
            if escaped:escaped=False
            elif char=='\\':escaped=True
            elif char=='"':quoted=False
        elif char=='"':quoted=True
        elif char==',' and index-start>=line_limit:
            line=encoded[start:index+1]+'\n';lines.append(line);size+=len(line);start=index+1
            if size>=chunk_limit:
                yield ''.join(lines);lines=[];size=0
        if index-start>=max_line:
            raise ValueError('JSON token exceeds native text line limit')
    lines.append(encoded[start:])
    yield ''.join(lines)
