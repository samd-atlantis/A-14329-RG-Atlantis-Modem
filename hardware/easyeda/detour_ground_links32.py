import json
from route_geometry import ROOT,load
from route_ground_plane import inner_path
from check_route_fragment import check
p,pads=load('control-update32-with-feed-docs.json');old,_=load('routing-native32-docs.json');rs=[]
ids={'6703a963b6f00117','0327d3b4cd5582a8','7f2496cdefa75d87','07f8bfe4b6fabd39'}
for rec in [r for r in old if r['h']['id'] in ids]:
 b=rec['b'];pts=inner_path(p+rs,pads,'GND_ISO',(b['startX'],b['startY']),(b['endX'],b['endY']),20);print(rec['h']['id'],pts,flush=True)
 if not pts:continue
 c=[dict(h=dict(type='LINE',ticket=52000+len(rs)+i,id=f'grounddetour32_{rec["h"]["id"]}_{i}'),b=dict(partitionId='',groupId=0,netName='GND_ISO',layerId=16,startX=a[0],startY=a[1],endX=z[0],endY=z[1],width=20,locked=False,zIndex=-1)) for i,(a,z) in enumerate(zip(pts,pts[1:]))]
 issues=check(c,p+rs,pads,set());print('issues',len(issues),flush=True)
 if not issues:rs.extend(c)
(ROOT/'ground-link-detours32-review.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs),indent=2))
