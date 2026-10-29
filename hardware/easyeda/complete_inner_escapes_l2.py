import json
from route_geometry import ROOT,load
from route_inner_control_l2 import inner_path
from check_route_fragment import check
source='routing-offline-escapes-complete-docs.json'
docs=json.loads((ROOT/source).read_text()); pcb,pads=load(source)
rs=[]
for net,a,b,w in [('3V3_ROUTER',(3592.3872,1030),(3125,1800),12),('MODEM_OFF',(3590,1120),(2344.8811,2219.4956),8),('CONSOLE_RX',(2474,2918),(1690.9454,2761.8094),8)]:
 pts=inner_path(pcb+rs,pads,net,a,b,w)
 print(net,pts,flush=True)
 if not pts:continue
 cand=[dict(h=dict(type='LINE',id=f'inner30L2_{net}_{i}',ticket=30000+len(rs)+i),b=dict(partitionId='',groupId=0,netName=net,layerId=15,startX=x[0],startY=x[1],endX=y[0],endY=y[1],width=w,locked=False,zIndex=-1)) for i,(x,y) in enumerate(zip(pts,pts[1:]))]
 issues=check(cand,pcb+rs,pads,set());print('issues',len(issues),flush=True)
 if not issues:rs.extend(cand)
(ROOT/'inner-escape-L2-completion-review.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs),indent=2))
