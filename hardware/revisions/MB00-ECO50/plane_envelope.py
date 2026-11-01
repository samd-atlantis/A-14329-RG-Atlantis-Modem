"""Conservative primary copper to the entire planned ground-plane envelope."""
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'hardware/audits/mb00-physical/.deps'))
sys.path.insert(0,str(ROOT/'hardware/easyeda'))
from shapely.geometry import Polygon,LineString,box
from route_geometry import load

def main():
    rows,pads=load(str(HERE/'pcb-eco50-docs.json'))
    items=[]
    for p in pads:
        if p['net'] in ['AC_L_IN','AC_L_FUSED','AC_N']:
            items.append((p['ref']+'.'+p['pin'],p['net'],box(p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2),0))
    for r in rows:
        b=r['b']
        if r['h']['type']=='LINE' and b.get('netName') in ['AC_L_IN','AC_L_FUSED','AC_N']:
            items.append((r['h']['id'],b['netName'],LineString([(b['startX'],b['startY']),(b['endX'],b['endY'])]),b['width']/2))
    results=[]
    for r in rows:
        if r['h']['type']=='POUR':
            b=r['b'];v=[x for x in b['path'][0] if not isinstance(x,str)];q=Polygon(zip(v[::2],v[1::2]))
            found=min(((g.distance(q)-radius)*.0254,name,net) for name,net,g,radius in items)
            results.append(dict(layer=b['layerId'],minimum_mm=found[0],item=found[1],net=found[2]))
    result={'scope':'Conservative primary pad bounding boxes and track capsules to the entire planned plane outline, before native keepout/thermal clearances. Filled copper must be a subset after correct native rebuild. Does not validate creepage, fabrication tolerances, actual Gerbers or safety.','results':results}
    (HERE/'planned-plane-envelope.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print(results)
    assert len(results)==2 and all(r['minimum_mm']>=9 for r in results)

if __name__=='__main__':main()
