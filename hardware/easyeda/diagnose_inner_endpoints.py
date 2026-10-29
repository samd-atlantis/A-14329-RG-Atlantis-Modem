import json,copy
from route_geometry import load
from check_route_fragment import check
p,pads=load('routing-offline-escapes-complete-docs.json')
for net,points in [('3V3_ROUTER',[(3592.3872,1030),(3845,335),(3270,1200),(3345,510),(3125,1800)]),('MODEM_OFF',[(3590,1120),(2344.8811,2219.4956),(1331.1036,3745.0831)])]:
 for x,y in points:
  r=dict(h=dict(type='LINE',id='probe'),b=dict(netName=net,layerId=16,startX=x,startY=y,endX=x,endY=y,width=8))
  others=[]
  for t in p:
   if t['h']['type']=='LINE' and t['b']['layerId']==2 and (t['b'].get('netName','').startswith('USB_') or t['b'].get('netName','').startswith('LAN')):
    q=copy.deepcopy(t);q['b']['layerId']=16;q['b']['width']+=2*41.415;others.append(q)
  print(net,x,y,check([r],p+others,pads,set()),flush=True)
