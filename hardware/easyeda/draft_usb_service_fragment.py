"""Service USB draft through recovery access; not applied or released."""
import math,json
from route_geometry import load,ROOT
from check_route_fragment import check
P,N='USB_SERVICE_DP','USB_SERVICE_DM';W=9.74
pcb,pads=load('routing-native14-actual-docs.json')
base=[r for r in pcb if not(r['h']['type'] in ('LINE','VIA') and r['b'].get('netName') in (P,N))]
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
a=[(2900,2550),(3400,2550),(3400,1150)]
b=[(3400,1060),(3400,900),(3650,900),(3650,1040),(3540,1040),(3540,960)]
c=[(3400,2200),(3100,2500),(2900,2500),(2900,2650)]
d=[(4080,400),(4080,1000),(4550,1000),(4550,2200),(3470,2200)]
ap,an=offset(a,-7.87),offset(a,7.87);bp,bn=offset(b,-7.87),offset(b,7.87)
cp,cn=offset(c,7.87),offset(c,-7.87);dp,dn=offset(d,7.87),offset(d,-7.87)
paths=[
 (P,1,[(2875,2735),(2875,2580)]+ap+[(3380,1110)]),
 (N,1,[(2925,2735),(2925,2580)]+an+[(3420,1110)]),
 (P,2,[(3380,1110)]+bp+[(3525,920)]),
 (N,2,[(3420,1110)]+bn+[(3555,935)]),
 (P,1,[(3525,920),(3525,990),(3509.84,1005.16),(3509.84,1023.42)]),
 (N,1,[(3555,935),(3555,997.95),(3529.53,1023.42)]),
 (P,1,[(2875,2735),(2875,2690)]),
 (N,1,[(2925,2735),(2925,2690)]),
 (P,2,[(3435,2180)]+cp+[(2875,2690)]),
 (N,2,[(3435,2220)]+cn+[(2925,2690)]),
 (P,1,[(4066.22,305.315),(4055,316.535),(4055,385)]+dp+[(3435,2180)]),
 (N,1,[(4093.78,305.315),(4105,316.535),(4105,385)]+dn+[(3435,2220)]),
 (P,1,[(4070.16,214.055),(4070.16,260),(4055,275),(4066.22,305.315)]),
 (N,1,[(4089.84,214.055),(4100,270),(4093.78,305.315)]),
 (P,1,[(4089.84,145.945),(4089.84,95)]),
 (P,2,[(4089.84,95),(4070.16,270)]),
 (P,1,[(4070.16,270),(4070.16,260)]),
 (N,1,[(4070.16,145.945),(4070.16,180),(4089.84,180),(4089.84,214.055)])]
vias={P:[(3380,1110),(3525,920),(2875,2690),(3435,2180),(4089.84,95),(4070.16,270)],N:[(3420,1110),(3555,935),(2925,2690),(3435,2220)]}
ticket=max(r['h'].get('ticket',0) for r in pcb)+4000;rs=[]
for net,layer,ps in paths:
 for p,q in zip(ps,ps[1:]):
  ticket+=1;rs.append({'h':{'type':'LINE','id':f'service_draft_{ticket}','ticket':ticket},'b':dict(partitionId='',groupId=0,netName=net,layerId=layer,startX=p[0],startY=p[1],endX=q[0],endY=q[1],width=W,locked=False,zIndex=-1)})
vt=next(r['b'] for r in pcb if r['h']['type']=='VIA')
for net,ps in vias.items():
 for x,y in ps:
  ticket+=1;c=dict(vt);c.update(netName=net,centerX=x,centerY=y,viaDiameter=23.622,holeDiameter=11.811)
  rs.append({'h':{'type':'VIA','id':f'service_draft_{ticket}','ticket':ticket},'b':c})
issues=check(rs,base,pads,{P,N});lens={net:sum(math.dist((r['b']['startX'],r['b']['startY']),(r['b']['endX'],r['b']['endY'])) for r in rs if r['h']['type']=='LINE' and r['b']['netName']==net) for net in (P,N)}
(ROOT/'usb-service-route-draft.json').write_text(json.dumps({'status':'OFFLINE_NOT_APPLIED','records':rs,'issues':issues,'length_sums_mil':lens,'limitations':['Clearance, branch topology, matching, orientation skew, native DRC and electrical review incomplete.']},indent=2))
print('length sums',lens,'issues',len(issues))
for x in issues:print(x['net'],x['id'],x['conflicts'])
