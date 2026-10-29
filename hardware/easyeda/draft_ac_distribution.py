"""Prototype mains distribution candidate; native DRC and load/bond tests required."""
import json
from route_geometry import load,ROOT
from check_route_fragment import check
pcb,pads=load('routing-native24-docs.json');rs=[]
ticket=max(r['h'].get('ticket',0) for r in pcb)+3000
def path(net,layer,ps,w):
 global ticket
 for a,b in zip(ps,ps[1:]):
  ticket+=1;rs.append(dict(h=dict(type='LINE',id=f'ac_distribution_{ticket}',ticket=ticket),b=dict(partitionId='',groupId=0,netName=net,layerId=layer,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=w,locked=False,zIndex=-1)))
def terminal(ref,pin):return sorted([p for p in pads if p['ref']==ref and p['pin']==str(pin)],key=lambda p:p['y'])
def xy(p):return p['x'],p['y']
neck=1.8/.0254;bus=160.
for pin,net,layer in [(1,'AC_L_IN',2),(2,'AC_N',1)]:
 lows=[terminal(ref,pin)[0] for ref in ('CN1','J15','J16')]
 path(net,layer,[(lows[0]['x'],110),(lows[-1]['x'],110)],bus)
 for ref in ('CN1','J15','J16'):
  low,high=terminal(ref,pin);x=low['x']
  path(net,layer,[xy(high),xy(low),(x,200)],neck)
  path(net,layer,[(x,200),(x,110)],bus)
# Protective earth is continuous and unfused. Keep it on the opposite surface
# from the neutral bus; the primary area has no inner copper planes.
pe=[terminal(ref,3) for ref in ('CN1','J15','J16')]
path('CHASSIS_PE',2,[(1440,1000),(pe[-1][0]['x'],1000)],bus)
for ref in ('CN1','J15','J16'):
 low,high=terminal(ref,3);x=low['x']
 path('CHASSIS_PE',2,[xy(low),xy(high)],neck)
 if ref=='CN1':
  path('CHASSIS_PE',2,[xy(high),(x,820),(1440,950)],neck)
  path('CHASSIS_PE',2,[(1440,950),(1440,1000)],bus)
 else:
  path('CHASSIS_PE',2,[xy(high),(x,900)],neck)
  path('CHASSIS_PE',2,[(x,900),(x,1000)],bus)
def p(ref,pin):return xy(next(p for p in pads if p['ref']==ref and p['pin']==str(pin)))
path('AC_L_IN',1,[xy(terminal('CN1',1)[1]),(944.8819,825),p('F1',1)],40)
path('AC_L_FUSED',1,[p('F1',2),p('PS1',2)],40)
path('AC_N',1,[xy(terminal('J15',2)[1]),(1865,1100),p('PS1',1)],40)
primary={'AC_L_IN','AC_L_FUSED','AC_N'}
def clearance(a,b):
 if a in primary or b in primary:return 3.2/.0254 if b in primary|{'CHASSIS_PE'} and a in primary|{'CHASSIS_PE'} else 8/.0254
 return 7.874
issues=check(rs,pcb,pads,set(),clearance)
(ROOT/'ac-distribution-route-draft.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs,issues=issues,review=['Prototype candidate, not a safety certification.','4.064 mm external buses; 1.8 mm short terminal fanouts; 1.016 mm PSU branch.','Neutral top and live bottom; no inner copper in primary area.','Verify 10 A combined load temperature rise and protective-earth fault/ground-bond performance before commercial release.']),indent=2))
print(len(rs),'segments;',len(issues),'findings')
for i in issues:print(i['id'],i['net'],i['conflicts'])
