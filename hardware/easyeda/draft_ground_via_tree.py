import json,math
from route_geometry import load,ROOT
from check_route_fragment import check
p,pads=load('routing-native29-docs.json')
v=[r for r in p if r['h']['type']=='VIA' and r['b']['netName']=='GND_ISO']
parent=list(range(len(v)))
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def pt(i):return(v[i]['b']['centerX'],v[i]['b']['centerY'])
def allowed(a,b):
 for k in range(101):
  x=a[0]+(b[0]-a[0])*k/100;y=a[1]+(b[1]-a[1])*k/100
  if not (20<=x<=4800 and 20<=y<=4800 and (y>=3400 or x>=3350 or y>=1500 and x>=1700)):return False
  for xx,yy,w,h in [(0,2430.9449,1416.3899,304.9606),(1347.9134,2430.9449,314.9606,1456.6929),(1365,1085,1840.4725,297.5984),(2890.5118,1102.3622,314.9606,1102.3622)]:
   if xx-10<x<xx+w+10 and yy-h-10<y<yy+10:return False
 return True
pairs=sorted((math.dist(pt(i),pt(j)),i,j) for i in range(len(v)) for j in range(i))
rs=[]
for length,i,j in pairs:
 if root(i)==root(j):continue
 a,b=pt(i),pt(j)
 if not allowed(a,b):continue
 r=dict(h=dict(type='LINE',id=f'groundtree30_{len(rs)}',ticket=40000+len(rs)),b=dict(partitionId='',groupId=0,netName='GND_ISO',layerId=16,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=20,locked=False,zIndex=-1))
 issues=check([r],p+rs,pads,set(),clearance=lambda n,m:315 if m and m.startswith('AC_') else 7.874)
 if issues:continue
 rs.append(r);parent[root(i)]=root(j)
print('vias',len(v),'tracks',len(rs),'groups',len(set(root(i) for i in range(len(v)))),flush=True)
(ROOT/'ground-via-tree-review.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs,issues=check(rs,p,pads,set(),clearance=lambda n,m:315 if m and m.startswith('AC_') else 7.874)),indent=2))
