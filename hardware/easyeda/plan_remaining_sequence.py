"""Sequential offline fragments, screened against previously accepted fragments."""
import json, subprocess, sys
from route_geometry import ROOT
jobs=[
 ('CONSOLE_RX','standalone','H1-3','U1','32',9.8425),
 ('ROUTER_RESET_N','standalone','H1-4','R36','2',9.8425),
 ('MODEM_PERST_N','standalone','J12-5','Q2','3',9.8425),
 ('MODEM_BUCK_EN','U3','13','R20','2',8),
 ('MODEM_BUCK_EN','standalone','J12-6','R20','2',9.8425),
 ('ROUTER_GPIO0_N','U1','30','R37','2',9.8425),
 ('ROUTER_GPIO0_N','standalone','H1-5','R37','2',9.8425),
 ('3V3_ROUTER','standalone','H1-6','R37','1',9.8425),
 ('3V3_ROUTER','R43','1','R42','1',16),
 ('3V3_ROUTER','C60','1','C70','1',16),
 ('3V3_ROUTER','C93','1','C60','1',16),
 ('USB_C_VBUS','J14','A9','C90','1',9.8425),
 ('MUSB_VBUS','J17','A9','C94','1',9.8425),
 ('MODEM_OFF','U8','6','R21','1',9.8425),
 ('SIM_A_VCC','U14','5','C71','1',9.8425),
 ('5V_ISO','C20','1','standalone','4',20),
]
priority=['MODEM_BUCK_EN','ROUTER_GPIO0_N','ROUTER_RESET_N','CONSOLE_RX','MODEM_PERST_N']
jobs=sorted(jobs,key=lambda j:priority.index(j[0]) if j[0] in priority else 20)
docs=json.loads((ROOT/'routing-native27-docs.json').read_text(encoding='utf-8'))
pcb=next(d['records'] for d in docs if d['head']['b']['docType']=='PCB')
source='routing-offline-sequence-docs.json';report=[];accepted=[]
for net,sref,spin,eref,epin,width in jobs:
 (ROOT/source).write_text(json.dumps(docs),encoding='utf-8')
 cmd=[sys.executable,str(ROOT/'plan_remaining_connection.py'),source,net,sref,spin,eref,epin,str(width),'1']
 result=subprocess.run(cmd,capture_output=True,text=True)
 filename=f'remaining-{net}-{sref}-{eref}-draft.json'
 status=dict(net=net,start=[sref,spin],end=[eref,epin],result=result.stdout.strip(),error=result.stderr.strip(),accepted=False)
 if result.returncode==0:
  draft=json.loads((ROOT/filename).read_text(encoding='utf-8'))
  if not draft['issues']:
   pcb.extend(draft['records']);accepted.extend(draft['records']);status['accepted']=True
 report.append(status)
 (ROOT/'remaining-sequence-report.json').write_text(json.dumps(report,indent=2))
 (ROOT/'remaining-sequence-fragment.json').write_text(json.dumps(dict(status='OFFLINE_NOT_APPLIED',records=accepted),indent=2))
 print(net,sref,eref,'ACCEPTED' if status['accepted'] else 'REVIEW',flush=True)
(ROOT/source).write_text(json.dumps(docs),encoding='utf-8')
