import json,copy
from route_geometry import load,ROOT
from check_route_fragment import check
p,pads=load('routing-native31-docs.json');rs=[];vt=copy.deepcopy(next(r['b'] for r in p if r['h']['type']=='VIA'));t=50000
jobs=[('U8','5',[(3560,1050),(3560,1010)],8),('J8','4',[(3525.3178,1575)],16),('J8','34',[(4123.7378,1575)],16),('J9','5',[(1875,2270)],20),('standalone','2',[(3380,695)],40)]
for ref,pin,points,w in jobs:
 s=next(q for q in pads if q['ref']==ref and q['pin']==pin);ps=[(s['x'],s['y'])]+points;c=[]
 for a,b in zip(ps,ps[1:]):
  t+=1;c.append(dict(h=dict(type='LINE',id=f'gndlocal30_{t}',ticket=t),b=dict(partitionId='',groupId=0,netName='GND_ISO',layerId=1,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=w,locked=False,zIndex=-1)))
 t+=1;v=copy.deepcopy(vt);v.update(netName='GND_ISO',centerX=points[-1][0],centerY=points[-1][1]);c.append(dict(h=dict(type='VIA',id=f'gndlocal30_{t}',ticket=t),b=v))
 i=check(c,p+rs,pads,set(),clearance=lambda n,m:315 if m and m.startswith('AC_') else 7.874);print(ref,pin,len(i),json.dumps(i),flush=True)
 if not i:rs.extend(c)
(ROOT/'ground-local-stitches-review.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs),indent=2))
for net,x,y in [('5V_ISO',2660,2350),('GND_ISO',2580,2160)]:
 v=copy.deepcopy(vt);v.update(netName=net,centerX=x,centerY=y,viaDiameter=70.866,holeDiameter=0)
 r=dict(h=dict(type='VIA',id='padprobe_'+net),b=v)
 print('FIXTURE_PAD',net,check([r],p,pads,set()),flush=True)
