"""Offline placement screen for moving the SIM clamp away from the modem buck."""
import math,json
from route_geometry import load,ROOT
from check_route_fragment import rectdist
pcb,pads=load('routing-native29-docs.json')
own=[p for p in pads if p['ref']=='U14'];others=[p for p in pads if p['ref']!='U14']
def bbox(p,dx=0,dy=0):return p['x']+dx-p['w']/2,p['y']+dy-p['h']/2,p['x']+dx+p['w']/2,p['y']+dy+p['h']/2
def boxgap(a,b):return math.hypot(max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0))
def clear(x,y):
 dx,dy=x-2677.1654,y-2106.3386
 for p in own:
  box=bbox(p,dx,dy)
  for q in others:
   if q['layer'] not in (1,12) or q['net']==p['net'] and p['net']:continue
   if boxgap(box,bbox(q))<8.5:return False
  for r in pcb:
   b=r['b'];t=r['h']['type']
   if b.get('netName')==p['net'] and p['net']:continue
   if t=='LINE' and b['layerId']==1:
    if rectdist((b['startX'],b['startY']),(b['endX'],b['endY']),box)-b['width']/2<8.5:return False
   if t=='VIA':
    c=(b['centerX'],b['centerY'])
    if rectdist(c,c,box)-b['viaDiameter']/2<8.5:return False
 # Reserve the body and pads against existing component keepouts.
 box=(x-60,y-75,x+60,y+75)
 for r in pcb:
  b=r['b']
  if r['h']['type']!='REGION' or 'COMPONENT' not in b.get('prohibitType',[]):continue
  for path in b['path']:
   if path[0]=='CIRCLE':
    c=(path[1],path[2])
    if rectdist(c,c,box)<path[3]:return False
   if path[0]=='R' and path[5]==0:
    a,bb,w,h=path[1:5]
    if boxgap(box,(a,bb-h,a+w,bb))==0:return False
 return True
out=[]
for x in range(2050,2801,10):
 for y in range(1800,2501,10):
  if clear(x,y):out.append((round(math.dist((x,y),(2000,2250)),2),x,y))
print(sorted(out)[:12])
