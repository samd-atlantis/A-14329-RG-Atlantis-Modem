import json,copy
from route_geometry import ROOT,load
from check_route_fragment import check
p,pads=load('routing-native35-docs.json');rs=[];report=[]
root=json.loads((ROOT/'remaining-CHASSIS_PE-J16-J14-draft.json').read_text(encoding='utf-8'))['records']
ci=check(root,p,pads,set(),clearance=lambda n,m:126 if m and m.startswith('AC_') else 7.874);print('root',ci,flush=True)
if not ci:rs.extend(root)
def pp(ref,pin):
 q=next(q for q in pads if q['ref']==ref and q['pin']==str(pin));return(q['x'],q['y'])
jobs=[('J14upper',1,[pp('J14',3),(3605.51,50),(3794.49,50),pp('J14',4)]),('between',1,[pp('J14',4),(3794.49,50),(3985.51,50),pp('J17',3)]),('J17upper',1,[pp('J17',3),(3985.51,50),(4174.49,50),pp('J17',4)])]
for ref in ('J14','J17'):
 for a,b in ((1,3),(2,4)):jobs.append((ref+str(a),2,[pp(ref,a),pp(ref,b)]))
for name,layer,pts in jobs:
 for w in (40,20):
  c=[dict(h=dict(type='LINE',id=f'pe35_{name}_{i}',ticket=200000+len(rs)+i),b=dict(partitionId='',groupId=0,netName='CHASSIS_PE',layerId=layer,startX=a[0],startY=a[1],endX=z[0],endY=z[1],width=w,locked=False,zIndex=-1)) for i,(a,z) in enumerate(zip(pts,pts[1:]))]
  issues=check(c,p+rs,pads,set(),clearance=lambda n,m:126 if m and m.startswith('AC_') else 7.874)
  if not issues:rs.extend(c);break
 print(name,w,'issues',len(issues),json.dumps(issues),flush=True);report.append(dict(name=name,width=w,issues=issues))
(ROOT/'usb-shields35-review.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs,report=report),indent=2),encoding='utf-8')
