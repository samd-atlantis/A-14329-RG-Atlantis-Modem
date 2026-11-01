"""Native geometry checks and optional audit-only KiCad translation.

Run with ordinary Python for the native screen; --kicad uses pcbnew and must
be run with the bundled KiCad Python. Neither output is fabrication data.
"""
import collections
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'hardware/easyeda'))
from route_geometry import load
from check_route_fragment import check,shape,rectdist,segdist
from audit_net_islands import audit as islands

def main():
    name=str(HERE/'pcb-eco50-docs.json')
    rows,pads=load(name)
    relevant=[p for p in pads if p['ref'] in ['L2','C25','C61','U19']]
    primitives=[r for r in rows if r['h']['type'] in ['LINE','VIA']]
    issues=check(primitives,[],relevant,{'USB_CONSOLE_DP','USB_CONSOLE_DM'})
    # Ignore existing trace-to-trace issues in unrelated native rule classes;
    # this screen is specifically every copper primitive versus moved/new pads.
    pin_issues=[]
    for issue in issues:
        cc=[c for c in issue['conflicts'] if any(c[0]==p['ref']+'.'+p['pin'] for p in relevant)]
        if cc:pin_issues.append(dict(id=issue['id'],net=issue['net'],conflicts=cc))
    pad_issues=[]
    for p in relevant:
        for q in pads:
            if p['id']==q['id'] or p['net']==q['net'] or not(p['layer']==q['layer'] or 12 in [p['layer'],q['layer']]):continue
            gap=math.hypot(max(abs(p['x']-q['x'])-(p['w']+q['w'])/2,0),max(abs(p['y']-q['y'])-(p['h']+q['h'])/2,0))
            if gap<7.874-.02:pad_issues.append(dict(a=p['ref']+'.'+p['pin'],b=q['ref']+'.'+q['pin'],gap_mm=gap*.0254))
    changed_nets=['USB_CONSOLE_DP','USB_CONSOLE_DM','CONSOLE_TX','3V3_MODEM','M_SW','M_SS']
    connectivity={n:islands(name,n) for n in changed_nets}
    opens={n:[g for g in gs if g['pads']] for n,gs in connectivity.items() if len([g for g in gs if g['pads']])>1}
    # Conservative body gap uses a 10.3 x 4.0 mm CH340C body envelope,
    # and a conservative 1.1 mm envelope for U19 rather than copper spacing.
    body_gap_mm=(3635-4/.0254/2)-(3500+1.1/.0254/2)
    # Socket/card envelope from saved JAE/Quectel mechanical placement.
    # The 30 mm card is centered on J8 x=3942.6378 mil. C25 base max 6.8 mm.
    cap_card_gap_mm=(4685.0394-3.4/.0254)-(3942.6378+15/.0254)
    cap_card_gap_mm*=.0254
    frozen=json.loads((ROOT/'hardware/releases/A-14329-MB00/manifest.json').read_text())
    changed_frozen=[f['file'] for f in frozen['files'] if hashlib.sha256((ROOT/'hardware/releases/A-14329-MB00'/f['file']).read_bytes()).hexdigest()!=f['sha256']]
    result=dict(status='ENGINEERING_CANDIDATE',new_or_moved_pad_copper_issues=pin_issues,pad_to_pad_issues=pad_issues,changed_signal_nets_pad_bearing_opens=opens,connectivity=connectivity,U19_to_U16_max_body_gap_mm=body_gap_mm*.0254,C25_max_base_to_nominal_card_edge_gap_mm=cap_card_gap_mm,frozen_release_hash_changes=changed_frozen,native_courtyard_DFM=False,native_ERC_DRC=False,physical_power_validation=False)
    (HERE/'geometry-checks.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print('new/moved pad conflicts',len(pin_issues),'pad-bearing opens',len(opens),'frozen hash changes',len(changed_frozen))
    for issue in pin_issues:print(issue)
    print('pad-to-pad conflicts',pad_issues)
    print('U19/U16 conservative body gap mm',result['U19_to_U16_max_body_gap_mm'])
    print('C25/card envelope gap mm',cap_card_gap_mm)
    if '--kicad' in sys.argv:convert_kicad()
    return not(pin_issues or pad_issues or opens or changed_frozen)

def convert_kicad():
    out=HERE/'kicad-audit';out.mkdir(exist_ok=True)
    source=(ROOT/'hardware/audits/mb00-physical/audit.py').read_text(encoding='utf8')
    source=source.replace('OUT = Path(__file__).resolve().parent',f'OUT = Path({str(out)!r})')
    source=source.replace('ROOT = OUT.parents[2]',f'ROOT = Path({str(ROOT)!r})')
    source=source.replace("'hardware/releases/A-14329-MB00/pcb-assembly49.epro2'","'hardware/revisions/MB00-ECO50/pcb-eco50-engineering.epro2'")
    exec(compile(source,'audit-eco50-only','exec'),{'__name__':'__main__','__file__':str(HERE/'audit-copy.py')})

if __name__=='__main__':
    if '--convert-only' in sys.argv:convert_kicad()
    else:sys.exit(0 if main() else 1)
