"""Offline modem USB draft, with ESD common points kept on the through route."""
import math,json
from route_geometry import load,ROOT
from check_route_fragment import check
P,N='USB_MODEM_DP','USB_MODEM_DM';W=9.74
pcb,pads=load('routing-native12-docs.json')
controls=('MODEM_OFF','MODEM_USB_SEL','CONSOLE_RX')
base=[r for r in pcb if not(r['h']['type'] in ('LINE','VIA') and r['b'].get('netName') in (P,N,*controls))]
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
a=[(3515,1220),(3515,1240),(4080,1240),(4140,1180),(4140,870),(4160,870)]
b=[(4240,870),(4250,870),(4250,1300),(4170.98,1379.02),(4170.98,1410)]
ap,an=offset(a,-7.87),offset(a,7.87);bp,bn=offset(b,-7.87),offset(b,7.87)
paths=[
 (P,1,[(3490.16,1076.58),(3488.5,1085),(3488.5,1098),(3475,1111),(3475,1140),(3530,1140)]),
 (N,1,[(3509.84,1076.58),(3510,1110)]),
 (P,2,[(3530,1140),(3530,1200)]+ap+[(4200,850)]),
 (N,2,[(3510,1110),(3502,1110),(3502,1200)]+an+[(4200,890)]),
 (P,1,[(4200,850),(4180,836.22),(4159.685,836.22)]),
 (N,1,[(4200,890),(4170,863.78),(4159.685,863.78)]),
 (P,2,[(4200,850)]+bp+[(4186.7278,1450)]),
 (N,2,[(4200,890)]+bn+[(4155.2378,1450)]),
 (P,1,[(4186.7278,1450),(4186.7278,1525.6326)]),
 (N,1,[(4155.2378,1450),(4155.2378,1525.6326)])]
def pathlen(ps):return sum(math.dist(p,q) for p,q in zip(ps,ps[1:]))
through={net:sum(pathlen(ps) for i,(n,l,ps) in enumerate(paths) if n==net and i not in (4,5)) for net in (P,N)}
amp=(through[P]-through[N])/(2*(math.sqrt(2)-1))
ps=paths[3][2]
for i,(p,q) in enumerate(zip(ps,ps[1:])):
 if abs(p[1]-q[1])<.001 and p[0]<3750<3900+amp<q[0]:
  y=p[1];ps[i+1:i+1]=[(3750,y),(3750+amp,y+amp),(3900,y+amp),(3900+amp,y)];break
else:raise RuntimeError('No tuning segment')
through={net:sum(pathlen(ps) for i,(n,l,ps) in enumerate(paths) if n==net and i not in (4,5)) for net in (P,N)}
vias={P:[(3530,1140),(4200,850),(4186.7278,1450)],N:[(3510,1110),(4200,890),(4155.2378,1450)]}
ticket=max(r['h'].get('ticket',0) for r in pcb)+2000;rs=[]
for net,layer,ps in paths:
 for p,q in zip(ps,ps[1:]):
  ticket+=1;rs.append({'h':{'type':'LINE','id':f'modem_draft_{ticket}','ticket':ticket},'b':dict(partitionId='',groupId=0,netName=net,layerId=layer,startX=p[0],startY=p[1],endX=q[0],endY=q[1],width=W,locked=False,zIndex=-1)})
vt=next(r['b'] for r in pcb if r['h']['type']=='VIA')
for net,ps in vias.items():
 for x,y in ps:
  ticket+=1;c=dict(vt);c.update(netName=net,centerX=x,centerY=y,viaDiameter=23.622,holeDiameter=11.811)
  rs.append({'h':{'type':'VIA','id':f'modem_draft_{ticket}','ticket':ticket},'b':c})
issues=check(rs,base,pads,{P,N});lens={net:sum(math.dist((r['b']['startX'],r['b']['startY']),(r['b']['endX'],r['b']['endY'])) for r in rs if r['h']['type']=='LINE' and r['b']['netName']==net) for net in (P,N)}
(ROOT/'usb-modem-route-draft.json').write_text(json.dumps({'status':'OFFLINE_NOT_APPLIED','records':rs,'issues':issues,'lengths_mil':lens,'through_lengths_mil':through,'limitations':['Native DRC, branch electrical lengths and return via placement remain required.']},indent=2))
print('through lengths',through)
print('lengths',lens,'issues',len(issues))
for x in issues:print(x['net'],x['id'],x['conflicts'])
