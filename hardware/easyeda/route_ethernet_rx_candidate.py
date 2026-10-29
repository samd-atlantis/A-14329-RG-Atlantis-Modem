"""Explicit LAN3 RX routing candidate. Geometry screening only; native DRC required."""
import json, math
from route_geometry import load, ROOT
from route_local import dist

P, N = 'LAN3_RXP', 'LAN3_RXN'
W, CLEAR, PAIR_CLEAR = 7.19, 7.874, 6.0
pcb, pads = load('routing-native8-docs.json')
reroute_controls = ('LAN3_RX_CT','LAN3_GREEN_A','LAN4_LED_N')
base = [r for r in pcb if not (r['h']['type'] in ('LINE','VIA') and r['b'].get('netName') in (P,N,*reroute_controls))]
paths = [
 (P,2,[(2326.5748,4094.4887),(2326.5748,4246.81),(2592.354,4246.81),(2635,4204.164),(2635,4175)]),
 (N,2,[(2276.5748,4194.4887),(2276.5748,4260),(2597.817,4260),(2640,4217.817),(2685,4217.817),(2685,4190)]),
 (P,1,[(2635,4175),(2650,4160),(2650,3990),(2635,3975),(2635,3960)]),
 (N,1,[(2685,4190),(2663.19,4168.19),(2663.19,3990),(2670,3983.19),(2670,3960)]),
 (P,2,[(2635,3960),(2570,3895),(2570,3600),(2552.2257412,3600),(2552.2257412,3550),(2570,3550),(2570,3220),(2550,3200),(2550,3170)]),
 (N,2,[(2670,3960),(2583.19,3873.19),(2583.19,3220),(2585,3218.19),(2585,3170)]),
 (P,1,[(2550,3170),(2550,3060.514),(2553.1408,3057.0887)]),
 (N,1,[(2585,3170),(2585,3081.924),(2608.26,3057.0887)]),
]
via_points = {P:[(2635,4175),(2635,3960),(2550,3170)],N:[(2685,4190),(2670,3960),(2585,3170)]}
ticket = max(r['h'].get('ticket',0) for r in pcb)+1000
candidate=[]
for net,layer,pts in paths:
 for a,b in zip(pts,pts[1:]):
  ticket+=1
  candidate.append({'h':{'type':'LINE','id':f'rx3_candidate_{ticket}','ticket':ticket},'b':{'partitionId':'','groupId':0,'netName':net,'layerId':layer,'startX':a[0],'startY':a[1],'endX':b[0],'endY':b[1],'width':W,'locked':False,'zIndex':-1}})
vtemplate=next(r['b'] for r in pcb if r['h']['type']=='VIA')
for net,pts in via_points.items():
 for x,y in pts:
  ticket+=1;b=dict(vtemplate);b.update(partitionId='',groupId=0,netName=net,centerX=x,centerY=y,viaDiameter=23.622,holeDiameter=11.811,locked=False)
  candidate.append({'h':{'type':'VIA','id':f'rx3_candidate_{ticket}','ticket':ticket},'b':b})

def pad_distance(p,pad):
 x,y=p;dx=abs(x-pad['x']);dy=abs(y-pad['y'])
 if pad['shape']=='ELLIPSE' and abs(pad['w']-pad['h'])<.01:return math.hypot(dx,dy)-pad['w']/2
 return math.hypot(max(0,dx-pad['w']/2),max(0,dy-pad['h']/2)) if dx>pad['w']/2 or dy>pad['h']/2 else -min(pad['w']/2-dx,pad['h']/2-dy)

issues=[]
for r in candidate:
 b=r['b'];net=b['netName'];via=r['h']['type']=='VIA';layers=(1,2) if via else (b['layerId'],);rad=b['viaDiameter']/2 if via else W/2
 if via:samples=[(b['centerX'],b['centerY'])]
 else:
  a=(b['startX'],b['startY']);z=(b['endX'],b['endY']);n=max(1,math.ceil(math.dist(a,z)))
  samples=[(a[0]+(z[0]-a[0])*i/n,a[1]+(z[1]-a[1])*i/n) for i in range(n+1)]
 nearest={}
 for p in samples:
  for pad in pads:
   if pad['net']==net or pad['layer'] not in (*layers,12):continue
   wanted=PAIR_CLEAR if pad['net'] in (P,N) else CLEAR
   gap=pad_distance(p,pad)-rad
   if gap<wanted-.01:nearest[f"{pad['ref']}.{pad['pin']} {pad['net']}"]=min(nearest.get(f"{pad['ref']}.{pad['pin']} {pad['net']}",1e9),gap-wanted)
  for q in base+candidate:
   c=q['b'];kind=q['h']['type']
   if kind not in ('LINE','VIA') or c.get('netName')==net:continue
   wanted=PAIR_CLEAR if c.get('netName') in (P,N) else CLEAR
   if kind=='LINE':
    if c['layerId'] not in layers:continue
    gap=dist(p,(c['startX'],c['startY']),(c['endX'],c['endY']))-rad-c['width']/2
   else:gap=math.dist(p,(c['centerX'],c['centerY']))-rad-c['viaDiameter']/2
   if gap<wanted-.01:nearest[f"{kind} {c.get('netName')} {q['h']['id']}"]=min(nearest.get(f"{kind} {c.get('netName')} {q['h']['id']}",1e9),gap-wanted)
 if nearest:issues.append({'id':r['h']['id'],'net':net,'geometry':b,'shortfall_mil':nearest})
report={'status':'OFFLINE_CANDIDATE_NOT_APPLIED','controls_requiring_reroute':reroute_controls,'width_mil':W,'clearance_mil':CLEAR,'pair_gap_mil':PAIR_CLEAR,'records':candidate,'clearance_issues':issues,'limitations':['Sampled geometry only; does not replace native DRC.','Region keepouts, exact curved/custom pads, copper pours, board edges, impedance, and via delay require additional checks.']}
(ROOT/'lan3-rx-routing-candidate.json').write_text(json.dumps(report,indent=2))
print('candidate primitives',len(candidate),'flagged primitives',len(issues))
for issue in issues:print(issue['net'],issue['id'],issue['shortfall_mil'])
