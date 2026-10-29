"""Direct USB-C service draft; recovery contacts deliberately carry no USB."""
import math,json
from route_geometry import load,ROOT
from check_route_fragment import check
P,N='USB_SERVICE_DP','USB_SERVICE_DM';W=9.74
pcb,pads=load('routing-native15-docs.json')
controls=('MUSB_VBUS','MUSB_CC1','MUSB_CC2','MODEM_USB_SEL','CONSOLE_RX','USB_UART_TX_BUF','USB_UART_RX_BUF','USB_UART_OE_N')
replace_ground_ids=('route2810_000000ee','ba61a2c477adfc7c')
base=[r for r in pcb if r['h']['id'] not in replace_ground_ids and not(r['h']['type'] in ('LINE','VIA') and r['b'].get('netName') in (P,N,*controls))]
def offset(pts,amount):
 ns=[]
 for a,b in zip(pts,pts[1:]):
  dx,dy=b[0]-a[0],b[1]-a[1];l=math.hypot(dx,dy);ns.append((-dy/l,dx/l))
 out=[]
 for i,p in enumerate(pts):
  if i==0:n=ns[0]
  elif i==len(pts)-1:n=ns[-1]
  else:
   u,v=ns[i-1:i+1];den=1+u[0]*v[0]+u[1]*v[1];n=((u[0]+v[0])/den,(u[1]+v[1])/den)
  out.append((p[0]+amount*n[0],p[1]+amount*n[1]))
 return out
center=[(3560,820),(3560,780),(4080,780),(4080,400)]
pp,nn=offset(center,-7.87),offset(center,7.87)
paths=[
 (P,1,[(3509.84,1023.42),(3509.84,1005.16),(3543.8,971.2),(3543.8,850),(3530,850)]),
 (N,1,[(3529.53,1023.42),(3560,992.95),(3560,850),(3600,850),(3600,900)]),
 (P,2,[(3530,850)]+pp+[(4055,380)]),
 (N,2,[(3600,900)]+nn+[(4105,380)]),
 (P,1,[(4055,380),(4055,341.535),(4066.22,330.315),(4066.22,305.315)]),
 (N,1,[(4105,380),(4105,341.535),(4093.78,330.315),(4093.78,305.315)]),
 (P,1,[(4070.16,214.055),(4070.16,260),(4055,275),(4066.22,305.315)]),
 (N,1,[(4089.84,214.055),(4089.84,260),(4105,275),(4093.78,305.315)]),
 (P,1,[(4089.84,145.945),(4089.84,110)]),
 (P,2,[(4089.84,110),(4065,260)]),
 (P,1,[(4065,260),(4070.16,260)]),
 (N,1,[(4070.16,145.945),(4070.16,180),(4089.84,180),(4089.84,214.055)]),
 ('GND_ISO',1,[(3513.912,905.5118),(3510,920)]),
 ('GND_ISO',1,[(3521.91,705),(3465,705)]),
 ('GND_ISO',1,[(4080,344.685),(4080,360)])]
def pathlen(ps):return sum(math.dist(p,q) for p,q in zip(ps,ps[1:]))
tree={net:sum(pathlen(ps) for n,l,ps in paths if n==net) for net in (P,N)}
amp=(tree[N]-tree[P])/(2*(math.sqrt(2)-1))
ps=paths[2][2]
for i,(p,q) in enumerate(zip(ps,ps[1:])):
 if abs(p[1]-q[1])<.001 and p[0]<3750<3900+amp<q[0]:
  y=p[1];ps[i+1:i+1]=[(3750,y),(3750+amp,y-amp),(3900,y-amp),(3900+amp,y)];break
else:raise RuntimeError('No tuning segment')
vias={P:[(3530,850),(4055,380),(4089.84,110),(4065,260)],N:[(3600,900),(4105,380)],'GND_ISO':[(3510,920),(3465,705),(4080,360)]}
ticket=max(r['h'].get('ticket',0) for r in pcb)+4000;rs=[]
for net,layer,ps in paths:
 for p,q in zip(ps,ps[1:]):
  ticket+=1;rs.append({'h':{'type':'LINE','id':f'service_direct_{ticket}','ticket':ticket},'b':dict(partitionId='',groupId=0,netName=net,layerId=layer,startX=p[0],startY=p[1],endX=q[0],endY=q[1],width=W,locked=False,zIndex=-1)})
vt=next(r['b'] for r in pcb if r['h']['type']=='VIA')
for net,ps in vias.items():
 for x,y in ps:
  ticket+=1;c=dict(vt);c.update(netName=net,centerX=x,centerY=y,viaDiameter=23.622,holeDiameter=11.811)
  rs.append({'h':{'type':'VIA','id':f'service_direct_{ticket}','ticket':ticket},'b':c})
issues=check(rs,base,pads,{P,N})
main={net:sum(pathlen(ps) for i,(n,l,ps) in enumerate(paths) if n==net and i<8) for net in (P,N)}
reverse={P:main[P]-pathlen(paths[6][2])+pathlen(paths[8][2])+pathlen(paths[9][2])+pathlen(paths[10][2])+pathlen(paths[6][2][1:]),N:main[N]+pathlen(paths[11][2])}
(ROOT/'usb-service-direct-draft.json').write_text(json.dumps({'status':'OFFLINE_NOT_APPLIED','records':rs,'issues':issues,'main_lengths_mil':main,'reverse_orientation_lengths_mil':reverse,'controls_requiring_reroute':controls,'ground_primitives_replaced':replace_ground_ids,'references':['https://www.ti.com/video/6087491555001'],'limitations':['Fanout and USB-C orientation length matching, native DRC and return vias remain required.']},indent=2))
print('main',main,'reverse',reverse)
print('primitives',len(rs),'issues',len(issues))
for x in issues:print(x['net'],x['id'],x['conflicts'])
