import json,copy
from route_geometry import ROOT,load
from check_route_fragment import check
D=json.loads((ROOT/'control-update32-with-feed-docs.json').read_text(encoding='utf-8'));P=next(d['records'] for d in D if d['head']['b']['docType']=='PCB')
g=json.loads((ROOT/'ground-link-detours32-review.json').read_text(encoding='utf-8'))['records'];P.extend(g)
review=json.loads((ROOT/'control-update32-review.json').read_text(encoding='utf-8'))
added=review['records']+json.loads((ROOT/'remaining-5V_ISO-C20-standalone-draft.json').read_text(encoding='utf-8'))['records']+g
base=[r for r in P if r not in added]
(ROOT/'control-update32-final-docs.json').write_text(json.dumps(D),encoding='utf-8');_,pads=load('control-update32-final-docs.json')
issues=check(added,base,pads,set(),clearance=lambda n,m:315 if m and m.startswith('AC_') else 7.874)
restore=[r for r in base if r['h']['type'] in ('LINE','VIA') and r['b'].get('netName') in ('5V_ISO','MODEM_BUCK_EN','MUSB_DETECT_N')]
fragment=copy.deepcopy(restore+added)
assert len({r['h']['id'] for r in fragment})==len(fragment)
for i,r in enumerate(fragment):r['h']['ticket']=100000+i;r['h']['id']='control33_'+str(i)
print('final',len(added),'new/modified routes; restore',len(restore),'issues',len(issues),flush=True)
(ROOT/'control-update32-final-fragment.json').write_text(json.dumps(dict(status='OFFLINE_CHECKED_NOT_APPLIED',records=fragment,issues=issues),indent=2),encoding='utf-8')
