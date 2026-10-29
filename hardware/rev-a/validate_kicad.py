from pathlib import Path
import os,subprocess,json,sys
R=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent/'kicad'
env=os.environ.copy();env['KICAD_CONFIG_HOME']=str(R/'.tools/kicad-config');env['KICAD_DOCUMENTS_HOME']=str(R/'.tools/kicad-docs')
env['KICAD9_SYMBOL_DIR']=str(R/'.tools/kicad/share/kicad/symbols');env['KICAD9_FOOTPRINT_DIR']=str(R/'.tools/kicad/share/kicad/footprints')
cli=R/'.tools/kicad/bin/kicad-cli.exe'
(P/'exports').mkdir(exist_ok=True)
commands=[['version'],['sch','erc','--format','json','--output',str(P/'exports/erc.json'),str(P/'walchem_gateway.kicad_sch')],['sch','export','netlist','--format','kicadxml','--output',str(P/'exports/netlist.xml'),str(P/'walchem_gateway.kicad_sch')],['sch','export','svg','--output',str(P/'exports'),str(P/'walchem_gateway.kicad_sch')]]
logs=[]
for args in commands:
 p=subprocess.run([str(cli)]+args,env=env,cwd=P,capture_output=True,text=True,timeout=180)
 logs.append(dict(args=args,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
 print(p.returncode,' '.join(args[:3]),p.stdout[:2000],p.stderr[:1000],flush=True)
(P/'exports/cli-log.json').write_text(json.dumps(logs,indent=2),encoding='utf8')
if any(p['returncode'] for p in logs):sys.exit(1)
