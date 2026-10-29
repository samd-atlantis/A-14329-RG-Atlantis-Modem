"""Route selected short local nets conservatively; validate in EasyEDA afterward."""
import heapq, json, math, sys
from route_geometry import load,ROOT

def dist(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy))) if dx or dy else 0
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

def route(pcb,pads,net,layer=1,width=9.8425,extra=300):
    ends=[p for p in pads if p['net']==net]
    if len(ends)!=2:return None
    a,b=[(p['x'],p['y']) for p in ends];step=2.5
    box=(max(25,min(a[0],b[0])-extra),max(25,min(a[1],b[1])-extra),min(4775,max(a[0],b[0])+extra),min(4775,max(a[1],b[1])+extra))
    clr=7.874+width/2+.8;obs=[]
    for p in pads:
        if p['net']==net or p['layer'] not in (layer,12):continue
        if box[0]-100<p['x']<box[2]+100 and box[1]-100<p['y']<box[3]+100:
            if p['shape']=='ELLIPSE' and abs(p['w']-p['h'])<.01:
                obs.append(('c',p['x'],p['y'],p['w']/2+clr))
            else:obs.append(('r',p['x']-p['w']/2-clr,p['y']-p['h']/2-clr,p['x']+p['w']/2+clr,p['y']+p['h']/2+clr))
    for r in pcb:
        k=r['h']['type'];v=r['b']
        if k=='LINE' and v['layerId']==layer and v.get('netName')!=net:
            x,y=v['startX'],v['startY'];xx,yy=v['endX'],v['endY']
            if min(x,xx)<box[2]+100 and max(x,xx)>box[0]-100 and min(y,yy)<box[3]+100 and max(y,yy)>box[1]-100:
                obs.append(('s',(x,y),(xx,yy),v['width']/2+clr))
        if k=='VIA' and v.get('netName')!=net:obs.append(('c',v['centerX'],v['centerY'],v['viaDiameter']/2+clr))
        if k=='REGION' and v['layerId'] in (layer,12) and 'TRACK' in v.get('prohibitType',[]):
            for q in v['path']:
                if q[0]=='CIRCLE':obs.append(('c',q[1],q[2],q[3]+width/2))
                elif q[0]=='R':
                    x,y,w,h,angle=q[1:6];co,si=math.cos(math.radians(angle)),math.sin(math.radians(angle))
                    pts=[(x+co*xx-si*yy,y+si*xx+co*yy) for xx,yy in ((0,0),(w,0),(0,-h),(w,-h))]
                    obs.append(('r',min(t[0] for t in pts)-width/2,min(t[1] for t in pts)-width/2,max(t[0] for t in pts)+width/2,max(t[1] for t in pts)+width/2))
    cache={}
    def free(x,y):
        if not(box[0]<=x<=box[2] and box[1]<=y<=box[3]):return False
        for o in obs:
            if o[0]=='c' and (x-o[1])**2+(y-o[2])**2<o[3]**2:return False
            if o[0]=='r' and o[1]<x<o[3] and o[2]<y<o[4]:return False
            if o[0]=='s' and dist((x,y),o[1],o[2])<o[3]:return False
        return True
    def good(k):
        if k not in cache:cache[k]=free(a[0]+k[0]*step,a[1]+k[1]*step)
        return cache[k]
    def point(k):return (a[0]+k[0]*step,a[1]+k[1]*step)
    if not free(*a) or not free(*b):return None
    dirs=((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1))
    heap=[(math.dist(a,b),0,(0,0))];cost={(0,0):0};prev={};goal=None
    while heap:
        _,g,k=heapq.heappop(heap)
        if g!=cost.get(k):continue
        p=point(k)
        if math.dist(p,b)<=step*1.5 and free((p[0]+b[0])/2,(p[1]+b[1])/2):goal=k;break
        for dx,dy in dirs:
            kk=(k[0]+dx,k[1]+dy)
            if not good(kk) or not free(p[0]+dx*step/2,p[1]+dy*step/2):continue
            gg=g+step*math.hypot(dx,dy)
            if gg<cost.get(kk,1e50):cost[kk]=gg;prev[kk]=k;heapq.heappush(heap,(gg+math.dist(point(kk),b),gg,kk))
    if goal is None:return None
    ks=[goal]
    while ks[-1]!=(0,0):ks.append(prev[ks[-1]])
    pts=[point(k) for k in reversed(ks)]+[b];out=[pts[0]]
    for i in range(1,len(pts)-1):
        u,v,w=out[-1],pts[i],pts[i+1]
        if abs((v[0]-u[0])*(w[1]-v[1])-(v[1]-u[1])*(w[0]-v[0]))>1e-5:out.append(v)
    out.append(b);return out

def main():
    pcb,pads=load();ticket=max(r['h']['ticket'] for r in pcb)+1000;report={}
    nets=sorted({p['net'] for p in pads if '_CT' in p['net']})+['M_SS','R_SS']
    for net in nets:
        pts=route(pcb,pads,net)
        report[net]=pts
        if pts:
            for i,(a,b) in enumerate(zip(pts,pts[1:])):
                ticket+=1
                pcb.append(dict(h=dict(type='LINE',ticket=ticket,id=f'local_2810_{net}_{i}'),b=dict(partitionId='',groupId=0,netName=net,layerId=1,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=9.8425,locked=False,zIndex=-1)))
        print(net,'segments',len(pts)-1 if pts else 'BLOCKED',flush=True)
    (ROOT/'routing-local-pass4.json').write_text(json.dumps(report,indent=2))
    (ROOT/'pcb-routing-pass4-authored.epro-source').write_text('|\n'.join(json.dumps(r['h'],separators=(',',':'))+'||'+json.dumps(r['b'],separators=(',',':')) for r in pcb),encoding='utf-8')
if __name__=='__main__':main()
