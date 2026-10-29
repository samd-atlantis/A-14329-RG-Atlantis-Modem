import json
from route_geometry import ROOT,load
from check_route_fragment import check
p,pads=load('ground-endpoints34-working-docs.json');j=json.loads((ROOT/'remaining-GND_ISO-J8-J8-draft.json').read_text(encoding='utf-8'))['records']
for r in j:
 b=r['b']
 if r['h']['type']=='VIA' and b['centerX']==3525 and b['centerY']==1475:b['centerY']=1477
 if r['h']['type']=='LINE':
  for pre in ('start','end'):
   if b[pre+'X']==3525 and b[pre+'Y']==1475:b[pre+'Y']=1477
i=check(j,p,pads,set(),clearance=lambda n,m:315 if m and m.startswith('AC_') else 7.874);print('J8 refined issues',len(i),i,flush=True)
if i:raise SystemExit('Review required')
a=json.loads((ROOT/'ground-endpoints34-review.json').read_text(encoding='utf-8'))['records']+j
for k,r in enumerate(a):r['h']['id']=f'ground35_{k}';r['h']['ticket']=150000+k
base,padbase=load('routing-native34-docs.json');base=[r for r in base if r['h']['id'] not in ('8dc3d9867c704cb1','bcb8735232a9d9af')]
i=check(a,base,padbase,set(),clearance=lambda n,m:315 if m and m.startswith('AC_') else 7.874);print('combined',len(a),'issues',len(i),flush=True)
(ROOT/'ground35-final-fragment.json').write_text(json.dumps(dict(status='OFFLINE_CHECKED_NOT_APPLIED',records=a,issues=i),indent=2),encoding='utf-8')
D=json.loads((ROOT/'ground-endpoints34-working-docs.json').read_text(encoding='utf-8'));next(d['records'] for d in D if d['head']['b']['docType']=='PCB').extend(j);(ROOT/'ground35-proposed-docs.json').write_text(json.dumps(D),encoding='utf-8')
