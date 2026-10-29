"""Main isolated PSU ground return and local output-capacitor plane stitching."""
import json,copy
from route_geometry import load,ROOT
from check_route_fragment import check
pcb,pads=load('routing-native24-docs.json')
pcb+=json.loads((ROOT/'ac-distribution-route-draft.json').read_text())['records']
rs=[];ticket=max(r['h'].get('ticket',0) for r in pcb)+1000
def p(ref,pin):
 a=next(p for p in pads if p['ref']==ref and p['pin']==str(pin));return a['x'],a['y']
def line(a,b,w):
 global ticket
 ticket+=1;rs.append(dict(h=dict(type='LINE',id=f'psu_ground_{ticket}',ticket=ticket),b=dict(partitionId='',groupId=0,netName='GND_ISO',layerId=1,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=w,locked=False,zIndex=-1)))
pts=[p('PS1',4),(1150,3120.825),(1150,3350),(1100,3440),(1100,3545)]
for a,b in zip(pts,pts[1:]):line(a,b,40)
line(p('C1',2),(846.4567,3580),40)
line((846.4567,3580),(871.4567,3580),40)
line(p('C2',2),(1490,3515),12)
vt=next(r['b'] for r in pcb if r['h']['type']=='VIA')
for x,y in [(1100,3545),(1125,3545),(1100,3570),(1125,3570),(846.4567,3580),(871.4567,3580),(1490,3515)]:
 ticket+=1;b=copy.deepcopy(vt);b.update(netName='GND_ISO',centerX=x,centerY=y,viaDiameter=23.622,holeDiameter=11.811)
 rs.append(dict(h=dict(type='VIA',id=f'psu_ground_{ticket}',ticket=ticket),b=b))
for r in rs:
 if r['h']['type']!='LINE' or r['b']['width']<40:continue
 for w in (80,60,40):
  r['b']['width']=w
  if not check([r],pcb,pads,set()):break
issues=check(rs,pcb,pads,set())
(ROOT/'psu-ground-return-draft.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs,issues=issues),indent=2))
print(len(rs),'records;',len(issues),'findings')
for i in issues:print(i['id'],i['conflicts'])
