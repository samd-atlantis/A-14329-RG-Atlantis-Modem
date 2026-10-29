"""Offline USB shell bonding candidate; native DRC and fault-current review required."""
import json
from route_geometry import load,ROOT
from check_route_fragment import check
pcb,pads=load('routing-native29-docs.json')
rs=json.loads((ROOT/'remaining-CHASSIS_PE-J16-J14-draft.json').read_text(encoding='utf-8'))['records']
ticket=max(r['h'].get('ticket',0) for r in pcb)+7000
def line(a,b,layer=1,width=40):
 global ticket
 ticket+=1
 rs.append(dict(h=dict(type='LINE',ticket=ticket,id=f'usb_pe_{ticket}'),b=dict(partitionId='',groupId=0,netName='CHASSIS_PE',layerId=layer,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=width,locked=False,zIndex=-1)))
def pad(ref,pin):return next(p for p in pads if p['ref']==ref and p['pin']==str(pin))
upper=[pad(j,p) for j in ('J14','J17') for p in (3,4)]
line((min(p['x'] for p in upper),50),(max(p['x'] for p in upper),50))
for p in upper:line((p['x'],p['y']),(p['x'],50))
for j in ('J14','J17'):
 for lower,upperpin in ((1,3),(2,4)):
  a,b=pad(j,lower),pad(j,upperpin)
  line((a['x'],a['y']),(b['x'],b['y']),2,30)
issues=check(rs,pcb,pads,set(),lambda n1,n2:125.985 if n2 in ('AC_L_IN','AC_L_FUSED','AC_N') else 7.874)
(ROOT/'usb-shield-bonds-draft.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs,issues=issues),indent=2),encoding='utf-8')
print(len(rs),'records',len(issues),'issues')
for i in issues:print(i['id'],i['conflicts'])
