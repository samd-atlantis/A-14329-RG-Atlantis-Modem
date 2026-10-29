import json
from route_geometry import load,ROOT
from check_route_fragment import check
p,pads=load('routing-native29-docs.json')
r=dict(h=dict(type='LINE',ticket=31000,id='ground_explicit_30_1'),b=dict(partitionId='',groupId=0,netName='GND_ISO',layerId=16,startX=4110,startY=1262.7926,endX=4290,endY=1262.7926,width=20,locked=False,zIndex=-1))
i=check([r],p,pads,set());print(json.dumps(i));(ROOT/'ground-explicit-bridge-review.json').write_text(json.dumps(dict(records=[r],issues=i),indent=2))
