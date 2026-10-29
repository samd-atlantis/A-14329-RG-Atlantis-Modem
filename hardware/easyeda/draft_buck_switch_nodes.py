"""Short top-layer switch-node fanout; offline candidate, native DRC required."""
import json,math
from route_geometry import load,ROOT
from check_route_fragment import check
pcb,pads=load('routing-native19-docs.json')
records=[]
ticket=max(r['h'].get('ticket',0) for r in pcb)+1000
def line(net,a,b,w):
 global ticket
 ticket+=1
 records.append(dict(h=dict(type='LINE',id=f'buck_switch_{ticket}',ticket=ticket),b=dict(partitionId='',groupId=0,netName=net,layerId=1,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=w,locked=False,zIndex=-1)))
for ref,ind,net in [('U2','L1','R_SW'),('U3','L2','M_SW')]:
 pins=sorted([p for p in pads if p['ref']==ref and p['net']==net],key=lambda p:p['y'])
 target=next(p for p in pads if p['ref']==ind and p['net']==net)
 bus=pins[0]['x']+45
 for p in pins:line(net,(p['x'],p['y']),(bus,p['y']),11.02)
 line(net,(bus,pins[0]['y']),(bus,pins[-1]['y']),40)
 line(net,(bus,pins[1]['y']),(target['x'],target['y']),40)
issues=check(records,pcb,pads,set())
(ROOT/'buck-switch-route-draft.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=records,issues=issues),indent=2))
print(len(records),'segments;',len(issues),'clearance findings')
for i in issues:print(i['id'],i['conflicts'])
