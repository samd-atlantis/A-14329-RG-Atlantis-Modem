"""Conservative pad clearance screen for proposed regulator placement."""
import json,math
from route_geometry import load,ROOT
pcb,pads=load('routing-native14-actual-docs.json')
positions={'C20':(2620,2210),'L2':(2992.126,2283.5039),'R37':(2500,2250),'SW3':(2440,2410),'C23':(3208.6614,2200),'C24':(3208.6614,2460)}
attrs={(r['b']['parentId'],r['b']['key']):r['b']['value'] for r in pcb if r['h']['type']=='ATTR'}
old={attrs.get((r['h']['id'],'Designator')):(r['b']['x'],r['b']['y']) for r in pcb if r['h']['type']=='COMPONENT'}
for p in pads:
 if p['ref'] in positions:
  a,b=old[p['ref']],positions[p['ref']];p['x']+=b[0]-a[0];p['y']+=b[1]-a[1]
issues=[]
for i,p in enumerate(pads):
 for q in pads[i+1:]:
  if p['ref']==q['ref'] or not ({p['ref'],q['ref']}&positions.keys()) or p['net']==q['net'] and p['net']:continue
  if p['layer']!=q['layer'] and 12 not in (p['layer'],q['layer']):continue
  dx=abs(p['x']-q['x'])-(p['w']+q['w'])/2;dy=abs(p['y']-q['y'])-(p['h']+q['h'])/2
  gap=math.hypot(max(0,dx),max(0,dy)) if dx>0 or dy>0 else max(dx,dy)
  if gap<7.874:issues.append((p['ref']+'.'+p['pin'],q['ref']+'.'+q['pin'],round(gap,3)))
report={'status':'OFFLINE_PLACEMENT_NOT_APPLIED','positions_mil':positions,'pad_clearance_issues':issues,'limitations':['Courtyards, existing traces, component keepouts, thermal layout and native DRC still require review.']}
(ROOT/'power-placement-draft.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
