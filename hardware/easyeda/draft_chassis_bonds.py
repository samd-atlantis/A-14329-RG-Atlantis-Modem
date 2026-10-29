"""Offline RJ45 shield bus proposal. Not applied or safety qualified."""
import json
from route_geometry import load, ROOT
from check_route_fragment import check
pcb,pads=load('routing-native25-docs.json')
rs=json.loads((ROOT/'remaining-CHASSIS_PE-J16-J2-draft.json').read_text())['records']
ticket=max(r['h'].get('ticket',0) for r in pcb)+10000
def line(a,b,w=60):
 global ticket
 ticket+=1
 rs.append(dict(h=dict(type='LINE',ticket=ticket,id=f'pe_bond_{ticket}'),b=dict(partitionId='',groupId=0,netName='CHASSIS_PE',layerId=2,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=w,locked=False,zIndex=-1)))
shells=sorted((p for p in pads if p['ref'] in ('J2','J3','J4','J5') and p['pin'] in ('13','14')),key=lambda p:p['x'])
line((shells[0]['x']-35,4700),(shells[-1]['x']+35,4700))
for p in shells:
 x=p['x']+(-35 if p['pin']=='13' else 35)
 line((p['x'],p['y']),(x,p['y']+35),40)
 line((x,p['y']+35),(x,4700),40)
issues=check(rs,pcb,pads,set(),lambda n1,n2:125.985 if n2 in ('AC_L_IN','AC_L_FUSED','AC_N') else 7.874)
(ROOT/'chassis-rj45-bus-draft.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs,issues=issues),indent=2))
print(len(rs),'records',len(issues),'issues')
for issue in issues:print(issue['id'],issue['conflicts'])
