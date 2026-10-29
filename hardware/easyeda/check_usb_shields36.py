import json
from route_geometry import ROOT,load
from check_route_fragment import check
p,pads=load('routing-native35-docs.json');d=json.loads((ROOT/'usb-shields-final36-review.json').read_text(encoding='utf-8'));i=check(d['records'],p,pads,set(),clearance=lambda n,m:126 if m and m.startswith('AC_') else 7.874);print(len(d['records']),'records',len(i),'issues',i,flush=True);d['issues']=i;(ROOT/'usb-shields-final36-review.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
