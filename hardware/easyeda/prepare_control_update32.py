import json,copy
from route_geometry import ROOT,load
from check_route_fragment import check
D=json.loads((ROOT/'routing-native32-docs.json').read_text(encoding='utf-8'));P=next(d['records'] for d in D if d['head']['b']['docType']=='PCB')
review=json.loads((ROOT/'escape-proposal-review.json').read_text(encoding='utf-8'));remove=set(review['removedIds']);remove.update({'6703a963b6f00117','0327d3b4cd5582a8','7f2496cdefa75d87','07f8bfe4b6fabd39'})
P[:]=[r for r in P if r['h']['id'] not in remove]
for r in P:
 if r['h']['type']=='PAD':
  m={'H1-3':'','H1-6':'','H1-8':'CONSOLE_RX','H1-9':'3V3_ROUTER','J12-6':'','J12-8':'MODEM_BUCK_EN'}
  if r['b']['num'] in m:r['b']['netName']=m[r['b']['num']]
 for changed in review['changedRecords']:
  if r['h']['id']==changed['h']['id']:r['b']=copy.deepcopy(changed['b'])
new=[r for r in review['records'] if not(r['b']['netName']=='3V3_ROUTER' and (r['b'].get('centerX')==3592.3872 or r['b'].get('startX')==3592.3872))]
new+=json.loads((ROOT/'escape-sequence-fragment.json').read_text(encoding='utf-8'))['records']
new+=json.loads((ROOT/'inner-escape-L2-completion-review.json').read_text(encoding='utf-8'))['records']
new+=json.loads((ROOT/'remaining-3V3_ROUTER-R102-R103-draft.json').read_text(encoding='utf-8'))['records']
(ROOT/'control-update32-base-docs.json').write_text(json.dumps(D),encoding='utf-8');base,pads=load('control-update32-base-docs.json')
issues=check(new,base,pads,set(),clearance=lambda n,m:315 if m and m.startswith('AC_') else 7.874)
(ROOT/'control-update32-candidate-docs.json').write_text(json.dumps(D),encoding='utf-8')
print('records',len(new),'issues',len(issues),flush=True)
for q in issues:print(q['id'],q['net'],q['conflicts'],flush=True)
(ROOT/'control-update32-review.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',removedIds=sorted(remove),records=new,issues=issues),indent=2))
if not issues:
 P.extend(new);(ROOT/'control-update32-complete-docs.json').write_text(json.dumps(D),encoding='utf-8')
