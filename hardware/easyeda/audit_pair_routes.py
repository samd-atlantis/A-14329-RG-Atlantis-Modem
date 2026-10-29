"""Report native pair routing dimensions, length sums, and approximate coupling.

This is a geometry review aid, not a field solver or a replacement for DRC.
Branch-net length sums are explicitly not endpoint propagation-length measurements.
"""
import collections,json,math,sys
from pathlib import Path
from route_local import dist
ROOT=Path(__file__).resolve().parent
source=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'routing-native4-docs.json'
docs=json.loads(source.read_text(encoding='utf-8'))
pcb=next(d['records'] for d in docs if d['head']['b']['docType']=='PCB')
lines=collections.defaultdict(list)
for r in pcb:
    if r['h']['type']=='LINE':lines[r['b'].get('netName','')].append(r['b'])
report=[]
for prefix in [f'LAN{i}_{k}' for i in range(1,5) for k in ('TX','RX')]+['USB_HOST_D','USB_MODEM_D','USB_SERVICE_D','USB_CONSOLE_D']:
    pn,nn=prefix+'P',prefix+('M' if prefix.startswith('USB') else 'N')
    pair=[]
    for net,other in ((pn,nn),(nn,pn)):
        segs=lines[net];length=0;coupled=0;want=15.74 if prefix.startswith('USB') else 13.19
        for b in segs:
            a=(b['startX'],b['startY']);z=(b['endX'],b['endY']);ll=math.dist(a,z);length+=ll
            n=max(1,math.ceil(ll/5))
            for j in range(n):
                t=(j+.5)/n;p=(a[0]+t*(z[0]-a[0]),a[1]+t*(z[1]-a[1]))
                dd=min((dist(p,(s['startX'],s['startY']),(s['endX'],s['endY'])) for s in lines[other] if s['layerId']==b['layerId']),default=1e9)
                if abs(dd-want)<2:coupled+=ll/n
        pair.append(dict(net=net,segments=len(segs),widths_mil=sorted({b['width'] for b in segs}),layers=sorted({b['layerId'] for b in segs}),length_sum_mm=length*.0254,coupled_length_fraction=coupled/length if length else None))
    report.append(dict(pair=prefix,conductors=pair,length_sum_difference_mm=abs(pair[0]['length_sum_mm']-pair[1]['length_sum_mm'])))
out=source.with_name(source.stem+'-pair-audit.json');out.write_text(json.dumps(report,indent=2))
for p in report:print(p['pair'],[(n['segments'],n['widths_mil'],round(n['length_sum_mm'],2),round(n['coupled_length_fraction'] or 0,3)) for n in p['conductors']],'delta',round(p['length_sum_difference_mm'],3))
