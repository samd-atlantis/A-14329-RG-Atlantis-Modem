"""Local regulator input and ground connections; requires native DRC."""
import json,copy
from route_geometry import load,ROOT
from check_route_fragment import check
pcb,pads=load('routing-native19-docs.json');rs=[]
ticket=max(r['h'].get('ticket',0) for r in pcb)+2000
def line(net,a,b,w=11.02):
 global ticket
 ticket+=1;rs.append(dict(h=dict(type='LINE',id=f'buck_local_{ticket}',ticket=ticket),b=dict(partitionId='',groupId=0,netName=net,layerId=1,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=w,locked=False,zIndex=-1)))
def pad(ref,pin):return next(p for p in pads if p['ref']==ref and p['pin']==str(pin))
def xy(p):return p['x'],p['y']
for ref,bulk,ceramic in [('U2','C10','C11'),('U3','C20','C21')]:
 pins=[pad(ref,i) for i in (12,11,10)]
 bus=pins[0]['x']-35
 for p in pins:line('5V_ISO',xy(p),(bus,p['y']))
 line('5V_ISO',(bus,pins[0]['y']),(bus,pins[-1]['y']),20)
 line('5V_ISO',xy(pad(ceramic,1)),(bus,pad(ceramic,1)['y']),20)
 line('5V_ISO',xy(pad(bulk,1)),(bus,pins[0]['y']),30)
 # Connect each ground pin directly into the exposed ground pad.
 ep=pad(ref,17)
 for num in (5,6,7,8,15,16):
  p=pad(ref,num)
  end=(p['x'],ep['y']) if num==15 else ((p['x']+ep['x'])/2,(p['y']+ep['y'])/2)
  line('GND_ISO',xy(p),end)
 # Four standard 0.3 mm drills on a 0.65 mm grid inside the exposed pad.
 # Bottom tenting follows the board rule. Assembly process must review via-in-pad.
 vt=next(r['b'] for r in pcb if r['h']['type']=='VIA')
 for dx in (-12.7953,12.7953):
  for dy in (-12.7953,12.7953):
   ticket+=1;b=copy.deepcopy(vt);b.update(netName='GND_ISO',centerX=ep['x']+dx,centerY=ep['y']+dy,viaDiameter=23.622,holeDiameter=11.811,bottomSolderExpansion=-1000)
   rs.append(dict(h=dict(type='VIA',id=f'buck_thermal_{ticket}',ticket=ticket),b=b))
vt=next(r['b'] for r in pcb if r['h']['type']=='VIA')
for ref,x,y in [('C10',1710,2660),('C11',1730,2880),('C20',2580,2160),('C21',2590,2340),('C23',3290,2200),('C24',3260,2519.7)]:
 line('GND_ISO',xy(pad(ref,2)),(x,y),10)
 if ref=='C21':continue # Existing gndstitch_C21 is within this short ground stub.
 ticket+=1;b=copy.deepcopy(vt);b.update(netName='GND_ISO',centerX=x,centerY=y,viaDiameter=23.622,holeDiameter=11.811)
 rs.append(dict(h=dict(type='VIA',id=f'buck_cap_ground_{ticket}',ticket=ticket),b=b))
remove_ids=['route2810_000000d9']
base=[r for r in pcb if r['h']['id'] not in remove_ids]
base+=json.loads((ROOT/'buck-switch-route-draft.json').read_text())['records']
issues=check(rs,base,pads,set())
(ROOT/'buck-local-route-draft.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs,issues=issues,remove_ids=remove_ids,assembly_review='Thermal via-in-pad requires solder-wicking/process review; bottom tenting specified.'),indent=2))
print(len(rs),'records;',len(issues),'findings')
for i in issues:print(i['id'],i['conflicts'])
