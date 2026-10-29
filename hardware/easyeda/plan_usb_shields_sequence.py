"""Offline, sequential USB shell bonds. No live board mutation."""
import json,subprocess,sys
from route_geometry import ROOT
docs=json.loads((ROOT/'routing-native29-docs.json').read_text(encoding='utf-8'))
pcb=next(d['records'] for d in docs if d['head']['b']['docType']=='PCB')
accepted=json.loads((ROOT/'remaining-CHASSIS_PE-J16-J14-draft.json').read_text(encoding='utf-8'))['records']
pcb.extend(accepted);report=[];source='routing-offline-usb-shields-docs.json'
jobs=[('J14','1','J14','3'),('J14','2','J14','3'),('J14','4','J14','3'),('J17','3','J14','4'),('J17','1','J17','3'),('J17','2','J17','3'),('J17','4','J17','3')]
for sr,sp,er,ep in jobs:
 (ROOT/source).write_text(json.dumps(docs),encoding='utf-8');ok=False;attempts=[]
 for width,layer in ((40,1),(40,2),(30,1),(30,2),(20,1),(20,2)):
  result=subprocess.run([sys.executable,str(ROOT/'plan_remaining_connection.py'),source,'CHASSIS_PE',sr,sp,er,ep,str(width),str(layer)],capture_output=True,text=True)
  attempts.append(dict(width=width,layer=layer,result=result.stdout,error=result.stderr))
  if result.returncode:continue
  draft=json.loads((ROOT/f'remaining-CHASSIS_PE-{sr}-{er}-draft.json').read_text(encoding='utf-8'))
  if draft['issues']:continue
  accepted.extend(draft['records']);pcb.extend(draft['records']);ok=True;break
 report.append(dict(start=[sr,sp],end=[er,ep],accepted=ok,attempts=attempts))
 (ROOT/'usb-shields-sequence-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 (ROOT/'usb-shields-sequence-fragment.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=accepted),indent=2),encoding='utf-8')
 print(sr,sp,er,ep,'ACCEPTED' if ok else 'REVIEW',flush=True)
(ROOT/source).write_text(json.dumps(docs),encoding='utf-8')
