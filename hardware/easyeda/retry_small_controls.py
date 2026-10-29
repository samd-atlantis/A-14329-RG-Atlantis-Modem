import subprocess,sys,json
from route_geometry import ROOT
for net,a,b in [('3V3_ROUTER','@3592.3872,1030','@3270,1200'),('MODEM_OFF','@3590,1120','@2344.8811,2219.4956')]:
 r=subprocess.run([sys.executable,str(ROOT/'plan_remaining_small_via.py'),'routing-offline-escapes-complete-docs.json',net,a,'0',b,'0','8','2','2'],capture_output=True,text=True);print(net,r.stdout,r.stderr,flush=True)
