"""Pure influence pruning/normalization with an immutable locked budget."""
import math


def clean_weights(values,locked,threshold=0,maximum=None,normalize=True,unweighted='ERROR',fallback=None):
    fixed={n:v for n,v in values.items() if n in locked and v!=0}
    if any(not math.isfinite(v) or not 0<=v<=1 for v in fixed.values()):raise ValueError('Invalid locked influence cannot be repaired without overriding locks')
    total_fixed=sum(fixed.values())
    if normalize and total_fixed>1+1e-6:raise ValueError('Locked weights exceed the normalized budget')
    if maximum is not None and len(fixed)>maximum:raise ValueError('Locked influences exceed max_influences')
    free={n:min(v,1) for n,v in values.items() if n not in locked and math.isfinite(v) and v>0 and v>=threshold}
    if maximum is not None:free=dict(sorted(free.items(),key=lambda pair:(-pair[1],pair[0]))[:maximum-len(fixed)])
    remaining=max(0,1-total_fixed);total=sum(free.values())
    if normalize and remaining<=1e-6:free={}
    elif normalize and total>1e-12:free={n:v*remaining/total for n,v in free.items()}
    elif total+total_fixed<=1e-12 or (normalize and remaining>1e-6 and total<=1e-12):
        if unweighted=='ERROR':raise ValueError('No unlocked weights available to fill normalized/unweighted vertex; choose a fallback policy')
        if unweighted in {'FALLBACK','NEAREST'}:
            fallback=fallback() if callable(fallback) else fallback
            if not fallback or fallback in locked:raise ValueError('Fallback bone is missing or locked')
            if maximum is not None and len(fixed)>=maximum:raise ValueError('No influence slot remains for fallback')
            free={fallback:remaining if normalize else max(remaining,1 if not fixed else 0)}
    return fixed|free
