"""Consolidate checked modem supply branches and replacement socket grounds."""
import json,copy
from route_geometry import load,ROOT
from check_route_fragment import check
pcb,pads=load('routing-native21-docs.json')
base=[r for r in pcb if r['h']['id']!='route2810_0000003f' and not(r['h']['type'] in ('LINE','VIA') and r['b'].get('netName')=='MODEM_PERST_N')]
base+=json.loads((ROOT/'router-power-trunk-draft.json').read_text())['records']
rs=[]
for name in ['modem-power-trunk-draft.json','modem-power-branch-41-draft.json','modem-power-branch-2-draft.json']:
 d=json.loads((ROOT/name).read_text());assert not d['issues'];rs+=d['records']
ticket=max(r['h'].get('ticket',0) for r in base+rs)+1000
vt=next(r['b'] for r in pcb if r['h']['type']=='VIA')
for x,y in [(4110,1262.7926),(4290,1262.7926)]:
 ticket+=1;b=copy.deepcopy(vt);b.update(netName='GND_ISO',centerX=x,centerY=y,viaDiameter=23.622,holeDiameter=11.811)
 rs.append(dict(h=dict(type='VIA',id=f'modem_ground_{ticket}',ticket=ticket),b=b))
ticket+=1;rs.append(dict(h=dict(type='LINE',id=f'modem_ground_{ticket}',ticket=ticket),b=dict(partitionId='',groupId=0,netName='GND_ISO',layerId=1,startX=4170.9878,startY=1202.7926,endX=4139.4878,endY=1202.7926,width=8,locked=False,zIndex=-1)))
ticket+=1;rs.append(dict(h=dict(type='LINE',id=f'modem_ground_{ticket}',ticket=ticket),b=dict(partitionId='',groupId=0,netName='GND_ISO',layerId=1,startX=4265.4678,startY=1262.7926,endX=4290,endY=1262.7926,width=8,locked=False,zIndex=-1)))
issues=check(rs,base,pads,set())
# Fragment source IDs must be unique even when separate planners started at the same ticket.
for i,r in enumerate(rs):r['h']=dict(type=r['h']['type'],id=f'modem_supply_combined_{i}',ticket=ticket+i+1)
(ROOT/'modem-supply-combined-draft.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs,issues=issues,remove_ids=['route2810_0000003f'],reroute_controls=['MODEM_PERST_N']),indent=2))
print(len(rs),'records;',len(issues),'findings')
for i in issues:print(i['id'],i['conflicts'])
