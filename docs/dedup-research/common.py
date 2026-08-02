import json,sys,itertools,re
sys.path.insert(0,'.')
from norm import base, strip_edition, toks
DATA=json.load(open('pairs.json',encoding='utf-8'))
def syear(r):
    m=re.search(r'(19|20)\d{2}',r.get('year') or ''); return int(m.group(0)) if m else None
def gyear(r):
    v=(r.get('year') or '')[:4]; return int(v) if v.isdigit() else None
def rows(q):
    out=[]
    for r in q['steam']: out.append(('S',str(r['id']),r['title'],syear(r),r))
    for r in q['gog']:   out.append(('G',str(r['id']),r.get('title_ru') or r['title'],gyear(r),r))
    for r in q['oldgames']: out.append(('O',str(r['id']),r['title'],None,r))
    return out
def all_pairs():
    info={}
    for q in DATA:
        for a,b in itertools.combinations(rows(q),2):
            if a[0]==b[0]: continue
            k=tuple(sorted([(a[0],a[1]),(b[0],b[1])]))
            info.setdefault(k,(a,b,q['query']))
    return info
