"""Offline copper connectivity aid; excludes pours and does not replace native DRC."""
import sys, math, json
from route_geometry import load, ROOT
from check_route_fragment import shape, segdist, rectdist

def audit(name, net):
    pcb,pads=load(name); objects=[]
    for p in pads:
        if p['net']!=net: continue
        objects.append(dict(id=p['ref']+'.'+p['pin'], pad=p, layers={1,2,15,16} if p['layer']==12 else {p['layer']}, a=(p['x'],p['y']),z=(p['x'],p['y']),r=0))
    for r in pcb:
        if r['h']['type'] not in ('LINE','VIA') or r['b'].get('netName')!=net:continue
        a,z,rad,layers=shape(r)
        objects.append(dict(id=r['h']['id'],layers=layers,a=a,z=z,r=rad))
    parent=list(range(len(objects)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def gap(a,b):
        if not a['layers']&b['layers']:return 1e9
        if 'pad' in a and 'pad' in b:
            p,q=a['pad'],b['pad']
            return math.hypot(max(abs(p['x']-q['x'])-(p['w']+q['w'])/2,0),max(abs(p['y']-q['y'])-(p['h']+q['h'])/2,0))
        if 'pad' in b:a,b=b,a
        if 'pad' in a:
            p=a['pad']
            return rectdist(b['a'],b['z'],(p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2))-b['r']
        return segdist(a['a'],a['z'],b['a'],b['z'])-a['r']-b['r']
    for i,a in enumerate(objects):
        for j,b in enumerate(objects[:i]):
            if gap(a,b)<=.02:parent[root(i)]=root(j)
    groups={}
    for i,o in enumerate(objects):groups.setdefault(root(i),[]).append(o)
    groups=sorted(groups.values(),key=len,reverse=True)
    out=[]
    for g in groups:
        nearest=None
        for a in g:
            for h in groups:
                if h is g:continue
                for b in h:
                    d=gap(a,b)
                    if nearest is None or d<nearest[0]:nearest=(round(d,4),a['id'],b['id'],a['a'],a['z'],b['a'],b['z'])
        out.append(dict(count=len(g),pads=[o['id'] for o in g if 'pad' in o],nearest=nearest))
    return out

if __name__=='__main__':
    print(json.dumps({n:audit(sys.argv[1],n) for n in sys.argv[2:]},indent=2))
