"""Offline USB host pair draft; never a substitute for native PCB DRC."""
import math,heapq,json
from route_geometry import load,ROOT
from route_local import dist

pcb,pads=load('routing-native11-docs.json')
step=5.; xmin,ymin,xmax,ymax=2700.,1000.,3650.,3010.
nx=int((xmax-xmin)/step)+1;ny=int((ymax-ymin)/step)+1
blocked=bytearray(nx*ny)
radius=9.74+3+7.874+1.5
def mark(box,predicate):
 x0,y0,x1,y1=box
 for j in range(max(0,int((y0-ymin)//step)),min(ny,int((y1-ymin)//step)+2)):
  y=ymin+j*step
  for i in range(max(0,int((x0-xmin)//step)),min(nx,int((x1-xmin)//step)+2)):
   if predicate(xmin+i*step,y):blocked[j*nx+i]=1
def circle(x,y,r):mark((x-r,y-r,x+r,y+r),lambda a,b:(a-x)**2+(b-y)**2<=r*r)
for p in pads:
 if p['layer']!=12:continue
 if p['shape']=='ELLIPSE' and abs(p['w']-p['h'])<.01:circle(p['x'],p['y'],p['w']/2+radius)
 else:
  box=(p['x']-p['w']/2-radius,p['y']-p['h']/2-radius,p['x']+p['w']/2+radius,p['y']+p['h']/2+radius)
  mark(box,lambda x,y:True)
for r in pcb:
 b=r['b'];k=r['h']['type']
 if k=='LINE' and b['layerId']==2:
  a=(b['startX'],b['startY']);z=(b['endX'],b['endY']);rr=b['width']/2+radius
  mark((min(a[0],z[0])-rr,min(a[1],z[1])-rr,max(a[0],z[0])+rr,max(a[1],z[1])+rr),lambda x,y:dist((x,y),a,z)<=rr)
 elif k=='VIA':circle(b['centerX'],b['centerY'],b['viaDiameter']/2+radius)
 elif k=='REGION' and b['layerId'] in (2,12) and 'TRACK' in b.get('prohibitType',[]):
  for q in b['path']:
   if q[0]=='CIRCLE':circle(q[1],q[2],q[3]+radius)
   elif q[0]=='R':
    x,y,w,h,ang=q[1:6];co,si=math.cos(math.radians(ang)),math.sin(math.radians(ang))
    pts=[(x+co*a-si*c,y+si*a+co*c) for a,c in ((0,0),(w,0),(0,-h),(w,-h))]
    mark((min(p[0] for p in pts)-radius,min(p[1] for p in pts)-radius,max(p[0] for p in pts)+radius,max(p[1] for p in pts)+radius),lambda a,b:True)
# Stay over the existing secondary-side ground reference, away from primary.
mark((xmin,ymin,3350+radius,1500+radius),lambda x,y:x<3350+radius and y<1500+radius)
def key(p):return (round((p[0]-xmin)/step),round((p[1]-ymin)/step))
def point(k):return (xmin+k[0]*step,ymin+k[1]*step)
def free(k):return 0<=k[0]<nx and 0<=k[1]<ny and not blocked[k[1]*nx+k[0]]
start,end=key((2911.415,2910)),key((3475,1150))
dirs=((0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1))
heap=[(0,0,start,-1)];cost={(start,-1):0};prev={};goal=None
print('endpoints',point(start),free(start),point(end),free(end),flush=True)
while heap:
 _,g,k,d=heapq.heappop(heap)
 if cost.get((k,d))!=g:continue
 if k==end:goal=(k,d);break
 for nd,(dx,dy) in enumerate(dirs):
  kk=(k[0]+dx,k[1]+dy)
  if not free(kk) or dx and dy and (not free((k[0]+dx,k[1])) or not free((k[0],k[1]+dy))):continue
  gg=g+step*math.hypot(dx,dy)+(8 if d>=0 and d!=nd else 0)
  state=(kk,nd)
  if gg<cost.get(state,1e30):cost[state]=gg;prev[state]=(k,d);heapq.heappush(heap,(gg+math.dist(point(kk),point(end)),gg,kk,nd))
if goal is None:raise SystemExit('NO CLEAR CORRIDOR')
ks=[goal]
while ks[-1][0]!=start:ks.append(prev[ks[-1]])
pts=[point(s[0]) for s in reversed(ks)];out=[pts[0]]
for i in range(1,len(pts)-1):
 a,b,c=out[-1],pts[i],pts[i+1]
 if abs((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))>1e-5:out.append(b)
out.append(pts[-1]);print('centerline',out)
(ROOT/'usb-host-centerline-draft.json').write_text(json.dumps({'status':'OFFLINE_NOT_APPLIED','centerline':out,'width_mil':9.74,'gap_mil':6,'limitations':['Fanouts, exact offsets, matching, return vias and native DRC remain required.']},indent=2))
