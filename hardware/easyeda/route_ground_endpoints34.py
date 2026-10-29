import json,subprocess,sys
from route_geometry import ROOT
D=json.loads((ROOT/'routing-native34-docs.json').read_text(encoding='utf-8'));P=next(d['records'] for d in D if d['head']['b']['docType']=='PCB');P[:]=[r for r in P if r['h']['id'] not in ('8dc3d9867c704cb1','bcb8735232a9d9af')]
source='ground-endpoints34-working-docs.json';accepted=[];report=[]
for sr,sp,er,ep,w in [('C24','2','C23','2',20),('U3','16','C20','2',8),('R35','2','C71','2',12),('J8','4','J8','9',8),('J9','5','J9','10',12)]:
 (ROOT/source).write_text(json.dumps(D),encoding='utf-8');r=subprocess.run([sys.executable,str(ROOT/'plan_remaining_connection.py'),source,'GND_ISO',sr,sp,er,ep,str(w),'1','1'],capture_output=True,text=True);ok=False
 if r.returncode==0:
  q=json.loads((ROOT/f'remaining-GND_ISO-{sr}-{er}-draft.json').read_text(encoding='utf-8'))
  if not q['issues']:P.extend(q['records']);accepted.extend(q['records']);ok=True
 report.append(dict(start=sr+'.'+sp,end=er+'.'+ep,accepted=ok,stdout=r.stdout,stderr=r.stderr));print(sr,er,ok,r.stdout,r.stderr,flush=True)
(ROOT/source).write_text(json.dumps(D),encoding='utf-8');(ROOT/'ground-endpoints34-review.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=accepted,report=report),indent=2),encoding='utf-8')
