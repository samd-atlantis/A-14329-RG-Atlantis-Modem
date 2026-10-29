"""Conservative fragment clearance screen. Native DRC is still mandatory."""
import math
from route_local import dist
def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def segdist(a,b,c,d):
 if cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0:return 0
 return min(dist(a,c,d),dist(b,c,d),dist(c,a,b),dist(d,a,b))
def rectdist(a,b,box):
 x0,y0,x1,y1=box
 if any(x0<=p[0]<=x1 and y0<=p[1]<=y1 for p in (a,b)):return 0
 pts=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
 return min(segdist(a,b,pts[i],pts[(i+1)%4]) for i in range(4))
def shape(r):
 b=r['b']
 if r['h']['type']=='LINE':return (b['startX'],b['startY']),(b['endX'],b['endY']),b['width']/2,{b['layerId']}
 if r['h']['type']=='VIA':return (b['centerX'],b['centerY']),(b['centerX'],b['centerY']),b['viaDiameter']/2,{1,2,15,16}
def check(records,base,pads,pairnets,clearance=7.874):
 def required(n1,n2):return clearance(n1,n2) if callable(clearance) else clearance
 issues=[]
 for r in records:
  b=r['b'];a,z,rad,layers=shape(r);net=b['netName'];found=[]
  for p in pads:
   if p['net']==net or p['layer'] not in layers|{12}:continue
   clr=6 if p['net'] in pairnets and net in pairnets else required(net,p['net'])
   if p['shape']=='ELLIPSE' and abs(p['w']-p['h'])<.01:gap=dist((p['x'],p['y']),a,z)-p['w']/2-rad
   else:gap=rectdist(a,z,(p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2))-rad
   if gap<clr-.02:found.append((p['ref']+'.'+p['pin'],p['net'],round(gap,3)))
  for q in base+records:
   c=q['b'];kind=q['h']['type']
   if kind in ('LINE','VIA'):
    if kind=='VIA' and r['h']['type']=='VIA' and q['h']['id']!=r['h']['id']:
     drill_gap=math.hypot(b['centerX']-c['centerX'],b['centerY']-c['centerY'])-(b['holeDiameter']+c['holeDiameter'])/2
     if drill_gap<11.811-.02:found.append(('DRILL '+q['h']['id'],c.get('netName'),round(drill_gap,3)))
    if c.get('netName')==net:continue
    aa,zz,rr,ll=shape(q)
    if not layers&ll:continue
    clr=6 if c.get('netName') in pairnets and net in pairnets else required(net,c.get('netName'))
    gap=segdist(a,z,aa,zz)-rad-rr
    if gap<clr-.02:found.append((kind+' '+q['h']['id'],c.get('netName'),round(gap,3)))
   elif kind=='REGION' and c['layerId'] in layers|{12} and ('TRACK' in c.get('prohibitType',[]) or r['h']['type']=='VIA' and 'VIA' in c.get('prohibitType',[])):
    for path in c['path']:
     gap=1e9
     if path[0]=='CIRCLE':gap=dist((path[1],path[2]),a,z)-path[3]-rad
     elif path[0]=='R' and path[5]==0:
      x,y,w,h=path[1:5];gap=rectdist(a,z,(x,y-h,x+w,y))-rad
     if gap<-.02:found.append(('KEEPOUT '+q['h']['id'],'',round(gap,3)))
  if found:issues.append({'id':r['h']['id'],'net':net,'geometry':b,'conflicts':found})
 return issues
