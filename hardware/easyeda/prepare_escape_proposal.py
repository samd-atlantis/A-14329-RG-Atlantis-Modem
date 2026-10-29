"""Offline local rip-up/escape proposal. Never changes the live PCB."""
import json,copy
from route_geometry import ROOT,load
from check_route_fragment import check
docs=json.loads((ROOT/'routing-native29-docs.json').read_text(encoding='utf-8'))
pcb=next(d['records'] for d in docs if d['head']['b']['docType']=='PCB')
remove={'route2810_00000090','route2810_00000091','route2810_00000092','42fc7672480f5a9d'}
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
escape('MODEM_OFF',[pad('U8',6),(3540,1090),(3550,1090)])
escape('MODEM_BUCK_EN',[pad('U3',13),(2710,2212),(2707,2195)])
escape('CONSOLE_RX',[(2490,2785),(2490,2880),(2474,2918)])
escape('3V3_ROUTER',[(2440,2785),(2440,2905)],12)
points=[(2660,2760),(2700,2760),(2700,2990),(2500,2990),(2400,2970),(2375,2945),(2170,2945),(2117.7871,2892.258)]
for a,b in zip(points,points[1:]):
 ticket+=1;rs.append(dict(h=dict(type='LINE',ticket=ticket,id=f'escape29_inner_{ticket}'),b=dict(partitionId='',groupId=0,netName='ROUTER_GPIO0_N',layerId=16,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=8,locked=False,zIndex=-1)))
points=[(2265.3537,2623.0381),(2640,2248.3918),(2640,2200),(2690,2150),(2738.3918,2150),(3042.9112,1845.4806)]
for a,b in zip(points,points[1:]):
 ticket+=1;rs.append(dict(h=dict(type='LINE',ticket=ticket,id=f'escape29_reset_{ticket}'),b=dict(partitionId='',groupId=0,netName='MODEM_RESET_REQ',layerId=2,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=9.8425,locked=False,zIndex=-1)))
issues=check(rs+changed,[r for r in base if r not in changed],pads,set())
(ROOT/'escape-proposal-review.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',removedIds=sorted(remove),changedRecords=changed,records=rs,issues=issues),indent=2),encoding='utf-8')
print(len(rs),'escape records',len(issues),'issues')
for i in issues:print(i['id'],i['net'],i['conflicts'])
if not issues:
 pcb.extend(rs);(ROOT/'routing-escape-proposal-docs.json').write_text(json.dumps(docs),encoding='utf-8')
