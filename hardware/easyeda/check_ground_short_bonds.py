import json
from route_geometry import load,ROOT
from check_route_fragment import check
p,pads=load('routing-native31-docs.json');rs=[]
for i,(a,b) in enumerate([((3540,275),(3540,214.055)),((4080,360),(4177.91,360)),((3510,920),(3450,777.56))]):
 r=dict(h=dict(type='LINE',ticket=51000+i,id=f'ground_short32_{i}'),b=dict(partitionId='',groupId=0,netName='GND_ISO',layerId=1 if i<2 else 15,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=12,locked=False,zIndex=-1))
 issues=check([r],p+rs,pads,set());print(i,issues,flush=True)
 if not issues:rs.append(r)
(ROOT/'ground-short-bonds-review.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs),indent=2))
