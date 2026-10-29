"""Offline route candidate for a remaining connection. Native DRC still required."""
import math,heapq,json,sys
from route_geometry import load,ROOT
from route_local import dist
from check_route_fragment import check
source,net,sref,spin,eref,epin=sys.argv[1:7]
width=float(sys.argv[7]) if len(sys.argv)>7 else 9.8425
startlayer=int(sys.argv[8]) if len(sys.argv)>8 else 1
endlayer=int(sys.argv[9]) if len(sys.argv)>9 else startlayer
allow_vias=net!='CHASSIS_PE'
step=5.;xmin,ymin,xmax,ymax=25,25,4775,4775
pcb,pads=load(source)
def endpoint(ref,pin):
 if ref.startswith('@'):
  x,y=map(float,ref[1:].split(','));return dict(x=x,y=y)
 return next(p for p in pads if p['ref']==ref and p['pin']==pin)
def clearance(other):
 return (125.985 if net=='CHASSIS_PE' else 314.961) if other in ('AC_L_IN','AC_L_FUSED','AC_N') else 7.874
start=endpoint(sref,spin)
end=endpoint(eref,epin)
if net!='CHASSIS_PE' or min(start['x'],end['x'])>3300:
 xmin=max(25,math.floor((min(start['x'],end['x'])-500)/step)*step)
 xmax=min(4775,math.ceil((max(start['x'],end['x'])+500)/step)*step)
 ymin=max(25,math.floor((min(start['y'],end['y'])-500)/step)*step)
 ymax=min(4775,math.ceil((max(start['y'],end['y'])+500)/step)*step)
nx=int((xmax-xmin)/step)+1;ny=int((ymax-ymin)/step)+1;nn=nx*ny
block=[bytearray(nn),bytearray(nn)];vblock=bytearray(nn)
def pt(k):return xmin+(k%nn%nx)*step,ymin+(k%nn//nx)*step
def index(x,y):return round((y-ymin)/step)*nx+round((x-xmin)/step)
def raster(arr,x0,y0,x1,y1,fn):
 for iy in range(max(0,math.floor((y0-ymin)/step)),min(ny-1,math.ceil((y1-ymin)/step))+1):
  y=ymin+iy*step
  for ix in range(max(0,math.floor((x0-xmin)/step)),min(nx-1,math.ceil((x1-xmin)/step))+1):
   x=xmin+ix*step
   if fn(x,y):arr[iy*nx+ix]=1
def circle(arr,x,y,r):raster(arr,x-r,y-r,x+r,y+r,lambda xx,yy:(xx-x)**2+(yy-y)**2<=r*r)
def rectangle(arr,x,y,w,h,r):
 x0,y0,x1,y1=x-w/2-r,y-h/2-r,x+w/2+r,y+h/2+r
 raster(arr,x0,y0,x1,y1,lambda xx,yy:max(abs(xx-x)-w/2,0)**2+max(abs(yy-y)-h/2,0)**2<=r*r)
def segment(arr,a,b,r):raster(arr,min(a[0],b[0])-r,min(a[1],b[1])-r,max(a[0],b[0])+r,max(a[1],b[1])+r,lambda x,y:dist((x,y),a,b)<=r)
for p in pads:
 for layer in (1,2):
  if p['net']==net or p['layer'] not in (layer,12):continue
  r=clearance(p['net'])+width/2+.3
  if p['shape']=='ELLIPSE' and abs(p['w']-p['h'])<.01:circle(block[layer-1],p['x'],p['y'],p['w']/2+r)
  else:rectangle(block[layer-1],p['x'],p['y'],p['w'],p['h'],r)
 # Keep new trunk vias out of all component pads, including this supply's pads.
 rectangle(vblock,p['x'],p['y'],p['w'],p['h'],(11.811/2+4) if p['net']==net else (7.874+23.622/2+1))
for r in pcb:
 b=r['b'];kind=r['h']['type']
 if kind=='LINE' and b.get('netName')!=net and b['layerId'] in (1,2):
  a,z=(b['startX'],b['startY']),(b['endX'],b['endY'])
  segment(block[b['layerId']-1],a,z,b['width']/2+width/2+clearance(b.get('netName'))+1.5)
  if b.get('netName') in ('AC_L_IN','AC_L_FUSED','AC_N'):
   for arr in block:segment(arr,a,z,b['width']/2+width/2+clearance(b.get('netName'))+1.5)
  segment(vblock,a,z,b['width']/2+23.622/2+clearance(b.get('netName'))+1)
 if kind=='LINE' and b.get('netName')!=net and b['layerId'] in (15,16):
  segment(vblock,(b['startX'],b['startY']),(b['endX'],b['endY']),b['width']/2+23.622/2+clearance(b.get('netName'))+1)
 if kind=='VIA':
  for arr in block:
   if b.get('netName')!=net:circle(arr,b['centerX'],b['centerY'],b['viaDiameter']/2+width/2+clearance(b.get('netName'))+1.5)
  circle(vblock,b['centerX'],b['centerY'],b['holeDiameter']/2+11.811/2+12.811)
 if kind=='REGION' and 'TRACK' in b.get('prohibitType',[]):
  for layer in (1,2):
   if b['layerId'] not in (layer,12):continue
   for q in b['path']:
    if q[0]=='CIRCLE':circle(block[layer-1],q[1],q[2],q[3]+width/2+1);circle(vblock,q[1],q[2],q[3]+12.811)
    elif q[0]=='R' and q[5]==0:
     x,y,w,h=q[1:5];rectangle(block[layer-1],x+w/2,y-h/2,w,h,width/2+1);rectangle(vblock,x+w/2,y-h/2,w,h,12.811)

start=endpoint(sref,spin)
end=endpoint(eref,epin)
a=(start['x'],start['y']);b=(end['x'],end['y'])
s=(startlayer-1)*nn+index(*a);goal=(endlayer-1)*nn+index(*b)
assert not block[s//nn][s%nn] and not block[goal//nn][goal%nn],f'Blocked endpoint {a} {b}'
existingViaNodes={index(r['b']['centerX'],r['b']['centerY']) for r in pcb if r['h']['type']=='VIA' and r['b'].get('netName')==net and xmin<=r['b']['centerX']<=xmax and ymin<=r['b']['centerY']<=ymax}
def free(k):return not block[k//nn][k%nn]
def heuristic(k):return math.dist(pt(k),b)
print('START_DIAG',a,'layers',block[0][s%nn],block[1][s%nn],'existing',s%nn in existingViaNodes,'vias',sorted(existingViaNodes),flush=True)
heap=[(heuristic(s),0.,s)];cost={s:0.};prev={};found=None;visits=0
while heap:
 _,g,k=heapq.heappop(heap)
 if g!=cost.get(k):continue
 visits+=1
 if k==goal:found=k;break
 local=k%nn;ix=local%nx;iy=local//nx
 for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
  if not(0<=ix+dx<nx and 0<=iy+dy<ny):continue
  kk=k+dy*nx+dx
  if not free(kk):continue
  if dx and dy and (not free(k+dx) or not free(k+dy*nx)):continue
  gg=g+step*math.hypot(dx,dy)
  if gg<cost.get(kk,1e99):cost[kk]=gg;prev[kk]=k;heapq.heappush(heap,(gg+heuristic(kk),gg,kk))
 if allow_vias and (local in existingViaNodes or not vblock[local]) and free((1-k//nn)*nn+local):
  kk=(1-k//nn)*nn+local;gg=g+(10 if local in existingViaNodes else 150)
  if gg<cost.get(kk,1e99):cost[kk]=gg;prev[kk]=k;heapq.heappush(heap,(gg+heuristic(kk),gg,kk))
print('search',visits,'nodes',bool(found),flush=True)
if found is None:
 todo=[goal%nn];seen={goal%nn};goal_layer=goal//nn
 for k in todo:
  ix=k%nx;iy=k//nx
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
   kk=k+dy*nx+dx
   if 0<=ix+dx<nx and 0<=iy+dy<ny and kk not in seen and not block[goal_layer][kk]:seen.add(kk);todo.append(kk)
  if len(todo)>10000:break
 print('goal island',len(seen),'bounds',min(pt(k)[0] for k in seen),max(pt(k)[0] for k in seen),min(pt(k)[1] for k in seen),max(pt(k)[1] for k in seen),'via sites',sum(not vblock[k] for k in seen))
 raise SystemExit('No main supply path found')
ks=[found]
while ks[-1]!=s:ks.append(prev[ks[-1]])
ks.reverse();points=[(k//nn+1,*pt(k)) for k in ks];points[0]=(startlayer,*a);points[-1]=(goal//nn+1,*b)
out=[points[0]]
for i in range(1,len(points)-1):
 u,v,w=out[-1],points[i],points[i+1]
 if u[0]!=v[0] or v[0]!=w[0] or abs((v[1]-u[1])*(w[2]-v[2])-(v[2]-u[2])*(w[1]-v[1]))>1e-5:out.append(v)
out.append(points[-1])
# Remove grid stair-steps where a straight segment is clear on the same layer.
def visible(a,b):
 if a[0]!=b[0]:return False
 count=max(1,math.ceil(math.dist(a[1:],b[1:])/(step/2)))
 return all(not block[a[0]-1][index(a[1]+(b[1]-a[1])*i/count,a[2]+(b[2]-a[2])*i/count)] for i in range(count+1))
clean=[out[0]];i=0
while i<len(out)-1:
 j=i+1
 for k in range(i+2,len(out)):
  if out[k][0]!=out[i][0]:break
  if visible(out[i],out[k]):j=k
 clean.append(out[j]);i=j
out=clean
rs=[];ticket=max(r['h'].get('ticket',0) for r in pcb)+3000
vt=next(r['b'] for r in pcb if r['h']['type']=='VIA')
for a,b in zip(out,out[1:]):
 ticket+=1
 if a[0]==b[0]:rs.append(dict(h=dict(type='LINE',id=f'remaining_{net}_{sref}_{eref}_{ticket}',ticket=ticket),b=dict(partitionId='',groupId=0,netName=net,layerId=a[0],startX=a[1],startY=a[2],endX=b[1],endY=b[2],width=width,locked=False,zIndex=-1)))
 else:
  if index(a[1],a[2]) in existingViaNodes:continue
  v=dict(vt);v.update(netName=net,centerX=a[1],centerY=a[2],viaDiameter=23.622,holeDiameter=11.811)
  rs.append(dict(h=dict(type='VIA',id=f'remaining_{net}_{sref}_{eref}_{ticket}',ticket=ticket),b=v))

issues=check(rs,pcb,pads,set(),lambda n1,n2:clearance(n2))
filename='remaining-'+net+'-'+sref+'-'+eref+'-draft.json'
(ROOT/filename).write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',source=source,records=rs,points=out,issues=issues),indent=2))
print(filename,len(rs),'records',len(issues),'issues')
for issue in issues: print(issue['id'],issue['conflicts'])
