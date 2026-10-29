"""Complete the screened local rip-up proposal offline, in routing priority order."""
import json,subprocess,sys
from route_geometry import ROOT
docs=json.loads((ROOT/'routing-escape-proposal-docs.json').read_text(encoding='utf-8'))
pcb=next(d['records'] for d in docs if d['head']['b']['docType']=='PCB')
jobs=[
 ('MODEM_BUCK_EN','@2707,2195','0','R20','2',8,2,1),
 ('SIM_A_VCC','@2640,2105','0','C71','1',9.8425,2,1),
 ('MODEM_OFF','@3590,1120','0','@2344.8811,2219.4956','0',9.8425,2,2),
 ('MODEM_PERST_N','standalone','J12-5','Q2','3',9.8425,1,1),
 ('MODEM_BUCK_EN','standalone','J12-8','R20','2',9.8425,1,1),
 ('CONSOLE_RX','@2474,2918','0','@1740.1579,3017.7144','0',9.8425,2,2),
 ('3V3_ROUTER','@2440,2905','0','@2370,2985','0',12,2,2),
 ('MUSB_DETECT_N','R102','2','Q4','3',9.8425,1,1),
 ('MUSB_DETECT_N','Q4','3','Q5','1',9.8425,1,1),
 ('3V3_ROUTER','@3592.3872,1030','0','@3845,335','0',12,2,2),
 ('5V_ISO','@2660,2350','0','standalone','4',60,2,1),
]
jobs=sorted(jobs,key=lambda j:0 if j[0]=='3V3_ROUTER' else (20 if j[0]=='5V_ISO' else 5))
source='routing-offline-escapes-complete-docs.json';report=[];accepted=[]
for net,sr,sp,er,ep,w,sl,el in jobs:
 (ROOT/source).write_text(json.dumps(docs),encoding='utf-8')
 result=subprocess.run([sys.executable,str(ROOT/'plan_remaining_connection.py'),source,net,sr,sp,er,ep,str(w),str(sl),str(el)],capture_output=True,text=True)
 status=dict(net=net,start=[sr,sp],end=[er,ep],accepted=False,result=result.stdout,error=result.stderr)
 if result.returncode==0:
  draft=json.loads((ROOT/f'remaining-{net}-{sr}-{er}-draft.json').read_text(encoding='utf-8'))
  if not draft['issues']:pcb.extend(draft['records']);accepted.extend(draft['records']);status['accepted']=True
 report.append(status)
 (ROOT/'escape-sequence-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 (ROOT/'escape-sequence-fragment.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=accepted),indent=2),encoding='utf-8')
 print(net,sr,er,'ACCEPTED' if status['accepted'] else 'REVIEW',flush=True)
(ROOT/source).write_text(json.dumps(docs),encoding='utf-8')
