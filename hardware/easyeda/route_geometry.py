"""Conservative geometry extraction for reviewing native EasyEDA routing.

All coordinates are native mils. Generated routes still require EasyEDA DRC.
"""
import json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def load(name='routing-resume-docs.json'):
    docs=json.loads((ROOT/name).read_text(encoding='utf-8'))
    pcb=next(d['records'] for d in docs if d['head']['b']['docType']=='PCB')
    fps={d['head']['b']['uuid']:d['records'] for d in docs if d['head']['b']['docType']=='FOOTPRINT'}
    attrs={(r['b']['parentId'],r['b']['key']):r['b']['value'] for r in pcb if r['h']['type']=='ATTR'}
    nets={}
    for r in pcb:
        if r['h']['type']=='PAD_NET':
            k=json.loads(r['h']['id']);nets[k[1],k[3]]=r['b']['padNet']
    pads=[]
    for r in pcb:
        if r['h']['type']!='COMPONENT':continue
        c=r['b'];cid=r['h']['id'];a=math.radians(c['angle']);co,si=math.cos(a),math.sin(a)
        for p in fps.get(attrs.get((cid,'Footprint')),[]):
            if p['h']['type']=='FILL' and p['b'].get('layerId')==12:
                paths=p['b'].get('path',[])
                if paths and isinstance(paths[0],str):paths=[paths]
                for path in paths:
                    if path[0]!='CIRCLE':continue
                    x,y,rad=path[1:4]
                    pads.append(dict(ref=attrs.get((cid,'Designator'),cid),pin='HOLE_'+p['h']['id'],id=cid+p['h']['id'],net='MECHANICAL_HOLE',x=c['x']+co*x-si*y,y=c['y']+si*x+co*y,w=2*rad,h=2*rad,layer=12,hole=None,shape='ELLIPSE'))
            if p['h']['type']!='PAD':continue
            b=p['b'];x,y=b['centerX'],b['centerY'];pa=math.radians(c['angle']+b.get('padAngle',0))
            sh=b['defaultPad'];w,h=sh['width'],sh['height']
            pads.append(dict(ref=attrs.get((cid,'Designator'),cid),pin=b['num'],id=cid+p['h']['id'],
                net=nets.get((cid,p['h']['id']),''),x=c['x']+co*x-si*y,y=c['y']+si*x+co*y,
                w=abs(math.cos(pa))*w+abs(math.sin(pa))*h,h=abs(math.sin(pa))*w+abs(math.cos(pa))*h,
                layer=b['layerId'],hole=b.get('hole'),shape=sh['padType']))
    for r in pcb:
        if r['h']['type']=='PAD':
            b=r['b'];sh=b['defaultPad'];a=math.radians(b.get('padAngle',0));w,h=sh['width'],sh['height']
            pads.append(dict(ref='standalone',pin=b['num'],id=r['h']['id'],net=b['netName'],
                x=b['centerX'],y=b['centerY'],w=abs(math.cos(a))*w+abs(math.sin(a))*h,
                h=abs(math.sin(a))*w+abs(math.cos(a))*h,layer=b['layerId'],hole=b.get('hole'),shape=sh['padType']))
    return pcb,pads

if __name__=='__main__':
    pcb,pads=load()
    (ROOT/'routing-current-pads.json').write_text(json.dumps(pads,indent=2))
    for n in sorted({p['net'] for p in pads if '_CT' in p['net'] or p['net'] in ('M_SS','R_SS')}):
        print(n,[(p['ref'],p['pin'],round(p['x'],2),round(p['y'],2)) for p in pads if p['net']==n])
