import math,json
from route_geometry import load,ROOT
from check_route_fragment import check
P,N='USB_HOST_DP','USB_HOST_DM';W=9.74
pcb,pads=load('routing-native17-docs.json')
reroute_controls=('MODEM_OFF','MODEM_USB_SEL','CONSOLE_RX')
base=[r for r in pcb if not (r['h']['type'] in ('LINE','VIA') and r['b'].get('netName') in (P,N,*reroute_controls))]
center=[(2911.415,2960),(2911.415,2945),(3035,2945),(3475,2505),(3475,1600),(3395,1520),(3395,1180),(3475,1100),(3475,1000)]
def offset(pts,amount):
 normals=[]
 for a,b in zip(pts,pts[1:]):
  dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy);normals.append((-dy/l,dx/l))
 out=[]
 for i,p in enumerate(pts):
  if i==0:n=normals[0]
  elif i==len(pts)-1:n=normals[-1]
  else:
   u,v=normals[i-1:i+1];den=1+u[0]*v[0]+u[1]*v[1];n=((u[0]+v[0])/den,(u[1]+v[1])/den)
  out.append((p[0]+amount*n[0],p[1]+amount*n[1]))
 return out
pp,nn=offset(center,-7.87),offset(center,7.87)
amp=9.804484906016/(2*(math.sqrt(2)-1))
xx=nn[3][0]
nn=nn[:4]+[(xx,2200),(xx+amp,2200-amp),(xx+amp,2150),(xx,2150-amp)]+nn[4:]
paths=[
 (P,1,[(2883.8548,3057.0887),(2883.8548,3000)]),
 (N,1,[(2938.9748,3057.0887),(2938.9748,3000)]),
 (P,2,[(2883.8548,3000),(2883.8548,2980),pp[0]]+pp[1:]+[(3450,960)]),
 (N,2,[(2938.9748,3000),(2938.9748,2980),nn[0]]+nn[1:]+[(3500,960)]),
 (P,1,[(3450,960),(3450,980),(3470.47,1000.47),(3470.47,1023.42)]),
 (N,1,[(3500,960),(3500,985),(3490.16,994.84),(3490.16,1023.42)])]
vps={P:[(2883.8548,3000),(3450,960)],N:[(2938.9748,3000),(3500,960)]}
ticket=max(r['h'].get('ticket',0) for r in pcb)+1000;rs=[]
for net,layer,ps in paths:
 for a,b in zip(ps,ps[1:]):
  ticket+=1;rs.append({'h':{'type':'LINE','id':f'host_draft_{ticket}','ticket':ticket},'b':dict(partitionId='',groupId=0,netName=net,layerId=layer,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=W,locked=False,zIndex=-1)})
vt=next(r['b'] for r in pcb if r['h']['type']=='VIA')
for net,ps in vps.items():
 for x,y in ps:
  ticket+=1;b=dict(vt);b.update(netName=net,centerX=x,centerY=y,viaDiameter=23.622,holeDiameter=11.811)
  rs.append({'h':{'type':'VIA','id':f'host_draft_{ticket}','ticket':ticket},'b':b})
issues=check(rs,base,pads,{P,N});lens={net:sum(math.dist((r['b']['startX'],r['b']['startY']),(r['b']['endX'],r['b']['endY'])) for r in rs if r['h']['type']=='LINE' and r['b']['netName']==net) for net in (P,N)}
report={'status':'OFFLINE_NOT_APPLIED','records':rs,'issues':issues,'lengths_mil':lens,'controls_requiring_reroute':reroute_controls,'limitations':['Native DRC, via delay and signal integrity remain required.']}
(ROOT/'usb-host-route-draft.json').write_text(json.dumps(report,indent=2));print('lengths',lens,'issues',len(issues))
for x in issues:print(x['net'],x['id'],x['conflicts'])
