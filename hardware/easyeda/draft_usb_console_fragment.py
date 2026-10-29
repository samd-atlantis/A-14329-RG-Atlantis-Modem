"""Console USB draft; CH340C data, with USB-C contact crossover."""
import math,json
from route_geometry import load,ROOT
from check_route_fragment import check
P,N='USB_CONSOLE_DP','USB_CONSOLE_DM';W=9.74
pcb,pads=load('routing-native15-docs.json')
service=json.loads((ROOT/'usb-service-direct-draft.json').read_text())
controls=(*service['controls_requiring_reroute'],'USB_C_VBUS','USB_C_CC1','USB_C_CC2','USB_UART_3V3','CONSOLE_TX')
base=[r for r in pcb if r['h']['id'] not in service['ground_primitives_replaced'] and not(r['h']['type'] in ('LINE','VIA') and r['b'].get('netName') in (P,N,*controls))]+service['records']
for p in pads:
 if p['ref']=='U19':
  dx,dy=p['x']-3865,p['y']-325;p['x'],p['y']=3600+dy,325-dx;p['w'],p['h']=p['h'],p['w']
 if p['ref']=='C92':p['y']+=50
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
center=[(3610,325),(3450,325),(3450,420)]
pp,nn=offset(center,7.87),offset(center,-7.87)
paths=[
 (P,1,[(3619.685,311.22),(3650,300)]),
 (N,1,[(3619.685,338.78),(3650,350)]),
 (P,2,[(3650,300)]+pp+[(3420,505)]),
 (N,2,[(3650,350)]+nn+[(3460,450)]),
 (P,1,[(3420,505),(3521.91,505)]),
 (N,1,[(3460,450),(3521.91,455)]),
 (P,1,[(3690.16,214.055),(3690.16,260),(3675,275),(3619.685,311.22)]),
 (N,1,[(3709.84,214.055),(3709.84,260),(3725,275),(3690,310),(3670,350),(3619.685,338.78)]),
 (P,1,[(3709.84,145.945),(3709.84,110)]),
 (P,2,[(3709.84,110),(3685,260)]),
 (P,1,[(3685,260),(3690.16,260)]),
 (N,1,[(3690.16,145.945),(3690.16,180),(3709.84,180),(3709.84,214.055)]),
 ('GND_ISO',1,[(3580.315,325),(3540,275)]),
 ('GND_ISO',1,[(3392.44,560),(3370,560)])]
def pathlen(ps):return sum(math.dist(p,q) for p,q in zip(ps,ps[1:]))
tree={net:sum(pathlen(ps) for n,l,ps in paths if n==net) for net in (P,N)}
delta=tree[P]-tree[N];chamfer=12;hh=(delta+4*chamfer*(2-math.sqrt(2)))/2
ps=paths[3][2]
for i,(p,q) in enumerate(zip(ps,ps[1:])):
 if abs(p[1]-q[1])<.001 and p[0]>3560>3488>q[0]:
  y=p[1];ps[i+1:i+1]=[(3560,y),(3548,y+12),(3548,y+hh-12),(3536,y+hh),(3512,y+hh),(3500,y+hh-12),(3500,y+12),(3488,y)];break
else:raise RuntimeError('No tuning segment')
vias={P:[(3650,300),(3420,505),(3709.84,110),(3685,260)],N:[(3650,350),(3460,450)],'GND_ISO':[(3540,275),(3370,560)]}
ticket=max(r['h'].get('ticket',0) for r in pcb)+6000;rs=[]
for net,layer,ps in paths:
 for p,q in zip(ps,ps[1:]):
  ticket+=1;rs.append({'h':{'type':'LINE','id':f'console_draft_{ticket}','ticket':ticket},'b':dict(partitionId='',groupId=0,netName=net,layerId=layer,startX=p[0],startY=p[1],endX=q[0],endY=q[1],width=W,locked=False,zIndex=-1)})
vt=next(r['b'] for r in pcb if r['h']['type']=='VIA')
for net,ps in vias.items():
 for x,y in ps:
  ticket+=1;c=dict(vt);c.update(netName=net,centerX=x,centerY=y,viaDiameter=23.622,holeDiameter=11.811)
  rs.append({'h':{'type':'VIA','id':f'console_draft_{ticket}','ticket':ticket},'b':c})
issues=check(rs,base,pads,{P,N});lens={net:sum(math.dist((r['b']['startX'],r['b']['startY']),(r['b']['endX'],r['b']['endY'])) for r in rs if r['h']['type']=='LINE' and r['b']['netName']==net) for net in (P,N)}
main={net:sum(pathlen(ps) for i,(n,l,ps) in enumerate(paths) if n==net and i<8) for net in (P,N)}
reverse={P:main[P]-pathlen(paths[6][2])+pathlen(paths[8][2])+pathlen(paths[9][2])+pathlen(paths[10][2])+pathlen(paths[6][2][1:]),N:main[N]+pathlen(paths[11][2])}
(ROOT/'usb-console-route-draft.json').write_text(json.dumps({'status':'OFFLINE_NOT_APPLIED','records':rs,'issues':issues,'length_sums_mil':lens,'main_lengths_mil':main,'reverse_orientation_lengths_mil':reverse,'controls_requiring_reroute':controls,'U19_placement_mil':[3600,325,90],'C92_placement_mil':[3420,560,180],'references':['https://www.ti.com/video/6087491555001'],'limitations':['Native DRC and USB-C orientation verification remain required.']},indent=2))
print('main',main,'reverse',reverse)
print('length sums',lens,'issues',len(issues))
for x in issues:print(x['net'],x['id'],x['conflicts'])
