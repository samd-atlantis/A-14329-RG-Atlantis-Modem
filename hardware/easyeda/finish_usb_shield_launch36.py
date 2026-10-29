import json,math,copy
from route_geometry import ROOT,load
from route_inner_control_l2 import inner_path
from route_local import dist
from check_route_fragment import check
p,pads=load('routing-native35-docs.json');prior=json.loads((ROOT/'usb-shields-inner35-review.json').read_text(encoding='utf-8'));rs=prior['records'];report=[q for q in prior['report'] if q['accepted']]
root=json.loads((ROOT/'remaining-CHASSIS_PE-J16-J14-draft.json').read_text(encoding='utf-8'))['records'];assert not check(root,p,pads,set(),clearance=lambda n,m:126 if m and m.startswith('AC_') else 7.874);pass
def pad(ref,pin):return next(q for q in pads if q['ref']==ref and q['pin']==str(pin))
def pt(q):return(q['x'],q['y'])
data=[r['b'] for r in p if r['h']['type']=='LINE' and r['b']['layerId']==1 and (r['b'].get('netName','').startswith('USB_') and r['b'].get('netName','').endswith(('DP','DM')) or r['b'].get('netName','').startswith('LAN') and r['b'].get('netName','').endswith(('P','N')))]
def gap(a):return min(dist(a,(q['startX'],q['startY']),(q['endX'],q['endY']))-q['width']/2 for q in data)
def line(net,a,b,w):return dict(h=dict(type='LINE',id=f'pe_inner35_{len(rs)}',ticket=210000+len(rs)),b=dict(partitionId='',groupId=0,netName=net,layerId=15,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=w,locked=False,zIndex=-1))
for sref,spin,eref,epin in [('J14',1,'J14',3)]:
 q=pad(sref,spin);a=pt(q);b=pt(pad(eref,epin));w=16;start=a;launch=None
 if gap(a)<w/2+7.874+41.415+.8:
  # A launch capsule wholly contained in the existing plated shield pad adds no reference-plane cut.
  cand=[];rad=min(q['w'],q['h'])/2-w/2;focus=(max(q['w'],q['h'])-min(q['w'],q['h']))/2
  for dx in [k*.25 for k in range(-80,81)]:
   for dy in [k*.25 for k in range(-48,49)]:
    if max(abs(dx)-focus,0)**2+dy*dy<=rad*rad:cand.append((q['x']+dx,q['y']+dy))
  start=max(cand,key=gap);launch=dict(pad=sref+'.'+str(spin),center=a,point=start,width=w,minimumDataGap=gap(start),containedInExistingPad=True)
 print('launch',sref,spin,'data gaps',gap(a),gap(start),flush=True)
 pts=inner_path(p+rs,pads,'CHASSIS_PE',start,b,w)
 if not pts:report.append(dict(start=sref+'.'+str(spin),end=eref+'.'+str(epin),accepted=False,launch=launch));print('NO PATH',flush=True);continue
 c=[]
 if start!=a:c.append(line('CHASSIS_PE',a,start,w))
 for aa,bb in zip(pts,pts[1:]):c.append(line('CHASSIS_PE',aa,bb,w));c[-1]['h']['id']+='_'+str(len(c))
 issues=check(c,p+rs,pads,set(),clearance=lambda n,m:126 if m and m.startswith('AC_') else 7.874)
 print('route',sref,spin,len(c),'issues',len(issues),flush=True);report.append(dict(start=sref+'.'+str(spin),end=eref+'.'+str(epin),accepted=not issues,launch=launch,points=pts,issues=issues))
 if not issues:rs.extend(c)
for i,r in enumerate(rs):r['h']['id']='pe36_'+str(i);r['h']['ticket']=220000+i
(ROOT/'usb-shields-final36-review.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=rs,report=report),indent=2),encoding='utf-8')
