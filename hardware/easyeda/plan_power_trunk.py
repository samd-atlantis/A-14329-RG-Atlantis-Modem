"""Offline two-layer power-trunk candidate. No live application or release claim."""
import math,heapq,json,time,sys
from route_geometry import load,ROOT
from route_local import dist
from check_route_fragment import check
net=sys.argv[1] if len(sys.argv)>1 else '3V3_ROUTER'
branch=sys.argv[2] if len(sys.argv)>2 else None
pcb,pads=load('routing-native22-docs.json' if net=='5V_ISO' else 'routing-native21-docs.json')
width=40. if net=='5V_ISO' else (16. if branch else 40.);step=5.
if net=='3V3_MODEM':
 xmin,ymin,xmax,ymax=2800,900,4775,2500
 pcb+=json.loads((ROOT/'router-power-trunk-draft.json').read_text())['records']
 if branch:
  pcb+=json.loads((ROOT/'modem-power-trunk-draft.json').read_text())['records']
  if branch=='2' and (ROOT/'modem-power-branch-41-draft.json').exists():pcb+=json.loads((ROOT/'modem-power-branch-41-draft.json').read_text())['records']
 if branch=='41':
  pcb=[r for r in pcb if r['h']['id']!='route2810_0000003f' and not(r['h']['type'] in ('LINE','VIA') and r['b'].get('netName')=='MODEM_PERST_N')]
elif net=='5V_ISO':
 xmin,ymin,xmax,ymax=650,2100,2950,3700
 if branch:pcb+=json.loads((ROOT/'5v-main-trunk-draft.json').read_text())['records']
else:xmin,ymin,xmax,ymax=1720,2450,3590,3970
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
  r=7.874+width/2+.1
  if p['shape']=='ELLIPSE' and abs(p['w']-p['h'])<.01:circle(block[layer-1],p['x'],p['y'],p['w']/2+r)
  else:rectangle(block[layer-1],p['x'],p['y'],p['w'],p['h'],r)
 # Keep new trunk vias out of all component pads, including this supply's pads.
 rectangle(vblock,p['x'],p['y'],p['w'],p['h'],7.874+23.622/2+1)
for r in pcb:
 b=r['b'];kind=r['h']['type']
 if kind=='LINE' and b.get('netName')!=net and b['layerId'] in (1,2):
  a,z=(b['startX'],b['startY']),(b['endX'],b['endY'])
  segment(block[b['layerId']-1],a,z,b['width']/2+width/2+8.0)
  segment(vblock,a,z,b['width']/2+23.622/2+8.874)
 if kind=='VIA':
  for arr in block:
   if b.get('netName')!=net:circle(arr,b['centerX'],b['centerY'],b['viaDiameter']/2+width/2+8.0)
  circle(vblock,b['centerX'],b['centerY'],b['holeDiameter']/2+11.811/2+12.811)
 if kind=='REGION' and 'TRACK' in b.get('prohibitType',[]):
  for layer in (1,2):
   if b['layerId'] not in (layer,12):continue
   for q in b['path']:
    if q[0]=='CIRCLE':circle(block[layer-1],q[1],q[2],q[3]+width/2+1);circle(vblock,q[1],q[2],q[3]+12.811)
    elif q[0]=='R' and q[5]==0:
     x,y,w,h=q[1:5];rectangle(block[layer-1],x+w/2,y-h/2,w,h,width/2+1);rectangle(vblock,x+w/2,y-h/2,w,h,12.811)
if net=='5V_ISO':
 start=next(p for p in pads if p['ref']==('C20' if branch else 'C1') and p['pin']=='1')
 end=next(p for p in pads if p['ref']==('C10' if branch else 'C20') and p['pin']=='1')
 if branch=='C2':
  start=next(p for p in pads if p['ref']=='C1' and p['pin']=='1')
  end=next(p for p in pads if p['ref']=='C2' and p['pin']=='1')
else:
 start=next(p for p in pads if p['ref']==('L2' if net=='3V3_MODEM' else 'L1') and p['pin']=='2')
 end=next(p for p in pads if p['ref']==('C25' if net=='3V3_MODEM' else 'U1') and p['pin']==('1' if net=='3V3_MODEM' else '2'))
 if branch:end=next(p for p in pads if p['ref']=='J8' and p['pin']==branch)
a=(start['x'],start['y']);b=(end['x'],end['y']);s=index(*a);goal=index(*b)
if net=='5V_ISO' and not branch:b=(2660,2350);goal=nn+index(*b)
assert not block[0][s] and not block[goal//nn][goal%nn], f'Power-pad escape is blocked: a={a}, b={b}'
if branch=='41':
 # Refine conservative rectangular via exclusion in the small socket escape pocket.
 pocket=[goal];seen={goal}
 for k in pocket:
  ix=k%nx;iy=k//nx
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
   kk=k+dy*nx+dx
   if 0<=ix+dx<nx and 0<=iy+dy<ny and kk not in seen and not block[0][kk]:seen.add(kk);pocket.append(kk)
  if len(pocket)>2000:break
 from check_route_fragment import rectdist
 for k in pocket:
  x,y=pt(k)
  if any(p['net']==net and rectdist((x,y),(x,y),(p['x']-p['w']/2,p['y']-p['h']/2,p['x']+p['w']/2,p['y']+p['h']/2))<13.811 for p in pads):continue
  trial=dict(h=dict(type='VIA',id='via_probe'),b=dict(netName=net,centerX=x,centerY=y,viaDiameter=23.622,holeDiameter=11.811))
  if not check([trial],pcb,pads,set()):vblock[k]=0
 print('refined socket via sites',sum(not vblock[k] for k in pocket),flush=True)
def free(k):return not block[k//nn][k%nn]
def heuristic(k):return math.dist(pt(k),b)
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
 if not vblock[local] and free((1-k//nn)*nn+local):
  kk=(1-k//nn)*nn+local;gg=g+150
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
ks.reverse();points=[(k//nn+1,*pt(k)) for k in ks];points[0]=(1,*a);points[-1]=(goal//nn+1,*b)
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
 if a[0]==b[0]:rs.append(dict(h=dict(type='LINE',id=f'power_trunk_{ticket}',ticket=ticket),b=dict(partitionId='',groupId=0,netName=net,layerId=a[0],startX=a[1],startY=a[2],endX=b[1],endY=b[2],width=width,locked=False,zIndex=-1)))
 else:
  v=dict(vt);v.update(netName=net,centerX=a[1],centerY=a[2],viaDiameter=23.622,holeDiameter=11.811)
  rs.append(dict(h=dict(type='VIA',id=f'power_trunk_{ticket}',ticket=ticket),b=v))
if net=='5V_ISO' and not branch:
 ticket+=1;v=dict(vt);v.update(netName=net,centerX=2660,centerY=2350,viaDiameter=23.622,holeDiameter=11.811)
 rs.append(dict(h=dict(type='VIA',id=f'5v_input_via_{ticket}',ticket=ticket),b=v))
for via in list(r for r in rs if r['h']['type']=='VIA'):
 v=via['b'];added=False
 for dx,dy in ((25,0),(0,25),(-25,0),(0,-25)):
  ticket+=1;vv=dict(v);vv.update(centerX=v['centerX']+dx,centerY=v['centerY']+dy)
  extra=[dict(h=dict(type='VIA',id=f'power_parallel_{ticket}',ticket=ticket),b=vv)]
  for layer in (1,2):
   ticket+=1;extra.append(dict(h=dict(type='LINE',id=f'power_parallel_{ticket}',ticket=ticket),b=dict(partitionId='',groupId=0,netName=net,layerId=layer,startX=v['centerX'],startY=v['centerY'],endX=vv['centerX'],endY=vv['centerY'],width=20,locked=False,zIndex=-1)))
  if not check(extra,pcb+rs,pads,set()):rs.extend(extra);added=True;break
 if not added:raise SystemExit('No clear parallel via location')
def powerpad(ref,pin):
 p=next(p for p in pads if p['ref']==ref and p['pin']==str(pin));return p['x'],p['y']
local_paths=[]
if net=='3V3_MODEM':
 if not branch:local_paths=[([powerpad('J8',41),powerpad('J8',39)],16),([(4425,1600),powerpad('J8',52)],16),([(4425,1600),powerpad('C61',1)],20)]
elif net=='5V_ISO':
 if not branch:local_paths=[([powerpad('PS1',3),powerpad('C1',1)],80),([(2660,2350),powerpad('C20',1)],26)]
else:local_paths=[([powerpad('U1',2),powerpad('U1',3)],30),([powerpad('U1',3),powerpad('C30',1)],30)]
for points,w in local_paths:
 for a,b in zip(points,points[1:]):
  ticket+=1;rs.append(dict(h=dict(type='LINE',id=f'power_local_{ticket}',ticket=ticket),b=dict(partitionId='',groupId=0,netName=net,layerId=1,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=w,locked=False,zIndex=-1)))
if branch and net!='5V_ISO':
 for r in rs:
  if r['h']['type']!='LINE':continue
  for w in (40,30,20,16):
   r['b']['width']=w
   if not check([r],pcb,pads,set()):break
if net=='5V_ISO':
 for r in rs:
  if r['h']['type']!='LINE':continue
  original=r['b']['width']
  for w in (80,60,40,original):
   r['b']['width']=w
   if not check([r],pcb,pads,set()):break
issues=check(rs,pcb,pads,set())
filename=f'modem-power-branch-{branch}-draft.json' if branch else ('modem-power-trunk-draft.json' if net=='3V3_MODEM' else 'router-power-trunk-draft.json')
if net=='5V_ISO':filename=('5v-cap-branch-draft.json' if branch=='C2' else '5v-router-branch-draft.json') if branch else '5v-main-trunk-draft.json'
(ROOT/filename).write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',points=out,records=rs,issues=issues,review='Via ampacity, return paths and native DRC remain required.'),indent=2))
print(len(rs),'records;',len(issues),'clearance findings')
for i in issues:print(i['id'],i['conflicts'])
