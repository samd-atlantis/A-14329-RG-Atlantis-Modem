"""Candidate local output capacitor, Kelvin sense and soft-start connections."""
import json
from route_geometry import load,ROOT
from check_route_fragment import check
pcb,pads=load('routing-native20-docs.json');rs=[]
ticket=max(r['h'].get('ticket',0) for r in pcb)+1000
def path(net,pts,w):
 global ticket
 for a,b in zip(pts,pts[1:]):
  ticket+=1;rs.append(dict(h=dict(type='LINE',id=f'buck_out_{ticket}',ticket=ticket),b=dict(partitionId='',groupId=0,netName=net,layerId=1,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=w,locked=False,zIndex=-1)))
def p(ref,pin):
 a=next(a for a in pads if a['ref']==ref and a['pin']==str(pin));return a['x'],a['y']
path('3V3_ROUTER',[p('L1',2),(2250,2789.37),(2250,2540),(2030.63,2540),p('C13',1)],40)
path('3V3_MODEM',[p('L2',2),(3120,2283.508),p('C23',1)],40)
path('3V3_MODEM',[p('L2',2),(3070.892,2360),(3168.857,2360),p('C24',1)],40)
path('3V3_ROUTER',[p('C13',1),(1940,2620),(1879.9638,2680.0362),p('U2',14)],8)
path('3V3_MODEM',[p('C23',1),(3169.2528,2110),(2746.1055,2110),p('U3',14)],8)
path('5V_ISO',[p('C10',1),(1860.2638,2696.8504),p('U2',13)],10)
path('M_SS',[p('U3',9),(2700.8055,2350),(2660.8055,2390),p('C22',1)],8)
reroute=['MODEM_USB_SEL','MODEM_BUCK_EN','ROUTER_GPIO0_N','CONSOLE_RX']
remove_ids=['route2810_000000b0']
base=[r for r in pcb if r['h']['id'] not in remove_ids and not(r['h']['type'] in ('LINE','VIA') and r['b'].get('netName') in reroute)]
issues=check(rs,base,pads,set())
(ROOT/'buck-output-route-draft.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs,issues=issues,reroute_controls=reroute,remove_ids=remove_ids),indent=2))
print(len(rs),'segments;',len(issues),'findings')
for i in issues:print(i['id'],i['net'],i['conflicts'])
