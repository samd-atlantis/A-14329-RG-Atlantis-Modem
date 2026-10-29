"""Offline local rip-up/escape proposal. Never changes the live PCB."""
import json,copy,math
from route_inner_control import inner_path
from route_geometry import ROOT,load
from check_route_fragment import check
docs=json.loads((ROOT/'routing-native29-docs.json').read_text(encoding='utf-8'))
pcb=next(d['records'] for d in docs if d['head']['b']['docType']=='PCB')
remove={'route2810_00000090','route2810_00000091','route2810_00000092','42fc7672480f5a9d','route2810_000000ea','route2810_000000eb','route2810_000000ec'}
for r in pcb:
 if r['h']['type'] in ('LINE','VIA') and (r['b'].get('netName') in ('MUSB_DETECT_N',) or (r['b'].get('netName') in ('MODEM_BUCK_EN',) and r['h']['id'].startswith('remaining_'))):remove.add(r['h']['id'])
for r in pcb:
 if r['h']['type'] in ('LINE','VIA') and r['b'].get('netName')=='5V_ISO' and r['h']['id'].startswith('remaining_5V_ISO_C20_'):remove.add(r['h']['id'])
original=copy.deepcopy(pcb)
pcb[:]=[r for r in pcb if r['h']['id'] not in remove]
for r in pcb:
 if r['h']['type']=='PAD':
  mapping={'H1-3':'','H1-6':'','H1-8':'CONSOLE_RX','H1-9':'3V3_ROUTER','J12-6':'','J12-8':'MODEM_BUCK_EN'}
  if r['b']['num'] in mapping:r['b']['netName']=mapping[r['b']['num']]
changed=[]
for r in pcb:
 if r['h']['id']=='e0a49dfa4a1492b8':r['b']['endY']=2240;changed.append(r)
 if r['h']['id']=='92a7f09ca1f4e400':r['b']['startY']=2240;changed.append(r)
(ROOT/'routing-escape-proposal-docs.json').write_text(json.dumps(docs),encoding='utf-8')
base,pads=load('routing-escape-proposal-docs.json')
ticket=max(r['h'].get('ticket',0) for r in pcb)+10000
vt=copy.deepcopy(next(r['b'] for r in pcb if r['h']['type']=='VIA'))
rs=[]
def escape(net,points,width=8):
 global ticket
 for a,b in zip(points,points[1:]):
  ticket+=1;rs.append(dict(h=dict(type='LINE',ticket=ticket,id=f'escape29_{ticket}'),b=dict(partitionId='',groupId=0,netName=net,layerId=1,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=width,locked=False,zIndex=-1)))
 ticket+=1;v=copy.deepcopy(vt);v.update(netName=net,centerX=points[-1][0],centerY=points[-1][1]);rs.append(dict(h=dict(type='VIA',ticket=ticket,id=f'escape29_{ticket}'),b=v))
def pad(ref,pin):
 p=next(p for p in pads if p['ref']==ref and p['pin']==str(pin));return (p['x'],p['y'])
escape('ROUTER_GPIO0_N',[(2590,2735),(2620,2760),(2660,2760)])
escape('SIM_A_VCC',[pad('U14',5),(2677.1654,2128),(2640,2105)])
escape('MODEM_OFF',[pad('U8',6),(3540,1090),(3590,1120)])
escape('MODEM_BUCK_EN',[pad('U3',13),(2710,2212),(2707,2195)])
escape('CONSOLE_RX',[(2490,2785),(2490,2880),(2474,2918)])
escape('3V3_ROUTER',[(2440,2785),(2440,2905)],12)

escape('3V3_ROUTER',[pad('R102',1),(3592.3872,1030)],12)
def add_path(net,points,layer,width=8):
 global ticket
 for a,b in zip(points,points[1:]):
  ticket+=1;rs.append(dict(h=dict(type='LINE',ticket=ticket,id=f'escape29_bridge_{ticket}'),b=dict(partitionId='',groupId=0,netName=net,layerId=layer,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=width,locked=False,zIndex=-1)))
points=inner_path(base+rs,pads,'ROUTER_GPIO0_N',(2660,2760),(2117.7871,2892.258))
if not points:raise SystemExit('No screened inner boot bridge')
add_path('ROUTER_GPIO0_N',points,16)
# Short bridge around the new enable escape, with through vias on the original reset trace.
def resetvia(x):
 v=copy.deepcopy(vt);v.update(netName='MODEM_RESET_REQ',centerX=x,centerY=4888.3918-x)
 return dict(h=dict(type='VIA',ticket=0,id='resetvia_probe'),b=v)
starts=[resetvia(x) for x in range(2670,2399,-5) if not check([resetvia(x)],base+rs,pads,set())]
ends=[resetvia(x) for x in range(2750,3001,5) if not check([resetvia(x)],base+rs,pads,set())]
print('reset bridge via sites',len(starts),len(ends),flush=True)
found=False
for va in starts:
 for vz in ends:
  a=(va['b']['centerX'],va['b']['centerY']);z=(vz['b']['centerX'],vz['b']['centerY'])
  points=inner_path(base+rs,pads,'MODEM_RESET_REQ',a,z)
  if points:
   for v in (va,vz):
    ticket+=1;v['h']=dict(type='VIA',ticket=ticket,id=f'escape29_resetvia_{ticket}');rs.append(v)
   add_path('MODEM_RESET_REQ',[(2265.3537,2623.0381),a],2,9.8425)
   add_path('MODEM_RESET_REQ',points,16)
   add_path('MODEM_RESET_REQ',[z,(3042.9112,1845.4806)],2,9.8425)
   found=True;break
 if found:break
if not found:raise SystemExit('No screened local reset bridge')
issues=check(rs+changed,[r for r in base if r not in changed],pads,set())
(ROOT/'escape-proposal-review.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',removedIds=sorted(remove),changedRecords=changed,records=rs,issues=issues),indent=2),encoding='utf-8')
print(len(rs),'escape records',len(issues),'issues',flush=True)
for i in issues:print(i['id'],i['net'],i['conflicts'])
if not issues:
 pcb.extend(rs);(ROOT/'routing-escape-proposal-docs.json').write_text(json.dumps(docs),encoding='utf-8')
