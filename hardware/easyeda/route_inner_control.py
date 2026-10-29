"""Offline inner-2 control bridge; keeps five dielectric heights from bottom data pairs."""
import copy,math
from route_local import route
from check_route_fragment import check,segdist

def inner_path(pcb,pads,net,a,b,width=8):
 transformed=[]
 for r in pcb:
  t=r['h']['type'];v=r['b']
  if t=='LINE':
   if v['layerId']==16:
    q=copy.deepcopy(r);q['b']['layerId']=1;transformed.append(q)
   elif v['layerId']==2 and (v.get('netName','').startswith('USB_') and v.get('netName','').endswith(('DP','DM')) or v.get('netName','').startswith('LAN') and v.get('netName','').endswith(('P','N'))):
    q=copy.deepcopy(r);q['b']['layerId']=1;q['b']['width']+=2*41.415;transformed.append(q)
  elif t=='VIA':transformed.append(r)
  elif t=='REGION' and v['layerId'] in (12,16):
   q=copy.deepcopy(r)
   if q['b']['layerId']==16:q['b']['layerId']=1
   if any(k in v.get('prohibitType',[]) for k in ('COPPER','FILL','PLANE')):q['b']['prohibitType']=list(set(v['prohibitType']+['TRACK']))
   transformed.append(q)
 pp=[]
 for p in pads:
  if p['net']==net:continue
  q=dict(p);q['layer']=1 if p['layer']==16 else (12 if p['layer']==12 else 99);pp.append(q)
 for i,point in enumerate((a,b)):pp.append(dict(ref='virtual',pin=str(i),net=net,x=point[0],y=point[1],w=0,h=0,shape='ELLIPSE',layer=1))
 pts=route(transformed,pp,net,1,width,extra=1000)
 if not pts:return None
 def line(a,b):return dict(h=dict(type='LINE',id='probe'),b=dict(netName=net,layerId=16,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=width))
 clean=[pts[0]];i=0
 while i<len(pts)-1:
  j=i+1
  for k in range(i+2,len(pts)):
   candidate=line(pts[i],pts[k])
   if check([candidate],pcb,pads,set()):continue
   if any(v['b']['layerId']==1 and v['h']['type']=='LINE' and v['b'].get('netName')!=net and segdist(pts[i],pts[k],(v['b']['startX'],v['b']['startY']),(v['b']['endX'],v['b']['endY']))<(v['b']['width']+width)/2+7.874 for v in transformed if v['h']['type']=='LINE'):continue
   j=k
  clean.append(pts[j]);i=j
 return clean
