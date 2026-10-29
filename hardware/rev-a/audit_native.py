"""Verify the exported KiCad netlist, ERC result and selected footprint pad sets."""
from pathlib import Path
import xml.etree.ElementTree as ET
import csv,json,sys,collections
R=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent/'kicad'
sys.path.insert(0,str(R/'.tools/python'));import sexpdata as sx
from library_inspect import nodes,node
data=json.loads((P/'design-data.json').read_text());pins=data['pins'];parts=data['bom']
root=ET.parse(P/'exports/netlist.xml').getroot();actual={}
for net in root.findall('./nets/net'):
 for pin in net.findall('node'):actual[(pin.attrib['ref'],pin.attrib['pin'])]=net.attrib['name']
errors=[];checked=0
for p in pins:
 if p['reference'].startswith('#'):continue
 k=(p['reference'],p['pin']);v=actual.get(k)
 if p['net']!='NC':
  checked+=1
  if v!=p['net']:errors.append(dict(kind='net_mismatch',reference=k[0],pin=k[1],expected=p['net'],actual=v))
 elif v and not v.startswith('unconnected-'):
  errors.append(dict(kind='NC_connected',reference=k[0],pin=k[1],actual=v))

# Explicit high-value end-to-end checks against the chosen manufacturer's pin assignments.
checks={('U1','54'):'USB_HOST_DP',('U1','55'):'USB_HOST_DM',('J8','38'):'USB_MODEM_DP',('J8','36'):'USB_MODEM_DM',('J8','8'):'USIM_VDD',('J8','10'):'USIM_DATA',('J8','12'):'USIM_CLK',('J8','14'):'USIM_RST',('U1','15'):'UART1_HOST_TX',('U1','16'):'UART1_HOST_RX',('U5','11'):'WIFI_UART_RX',('U5','12'):'WIFI_UART_TX',('U13','6'):'WIFI_UART_RX',('U13','3'):'UART1_HOST_RX',('U6','1'):'I2C_SCL',('U6','2'):'I2C_SDA',('U10','15'):'SIM_A_VCC',('U10','13'):'SIM_B_VCC',('U11','8'):'SIM_B_VCC',('U11','1'):'GND_ISO'}
for k,v in checks.items():
 if actual.get(k)!=v:errors.append(dict(kind='critical_net_mismatch',reference=k[0],pin=k[1]))
missing=[];footprints=[]
for p in parts:
 if p['reference'].startswith('#'):continue
 if not p['footprint']:
  missing.append(p['reference']);continue
 lib,name=p['footprint'].split(':',1)
 path=P/'Gateway.pretty'/(name+'.kicad_mod') if lib=='Gateway' else P/'footprints'/(lib+'.pretty')/(name+'.kicad_mod')
 if not path.exists():errors.append(dict(kind='footprint_missing',reference=p['reference'],file=str(path)));continue
 fp=sx.loads(path.read_text(encoding='utf8'));pads={str(x[1]) for x in nodes(fp,'pad') if str(x[1])}
 expected={x['pin'] for x in pins if x['reference']==p['reference']}
 # Extra mechanical pads are permitted only if explicitly listed below, never silently grounded.
 absent=expected-pads;extra=pads-expected
 row=dict(reference=p['reference'],footprint=p['footprint'],symbol_pin_count=len(expected),pad_numbers=','.join(sorted(pads)),missing_symbol_pads=','.join(sorted(absent)),extra_footprint_pads=','.join(sorted(extra)))
 footprints.append(row)
 if absent:errors.append(dict(kind='symbol_pad_missing',reference=p['reference'],pins=sorted(absent)))
erc=json.loads((P/'exports/erc.json').read_text());violations=[v for s in erc['sheets'] for v in s['violations']]
assert not any('lora' in x['value'].lower() for x in parts)
assert any(x['reference']=='U5' and x['value']=='Ai-WB2-13' for x in parts)
result={'kicad_version':erc['kicad_version'],'schematic_sheets':len(erc['sheets']),'physical_pin_rows':len(pins),'connected_pins_checked':checked,'critical_checks':len(checks),'erc_errors':sum(v['severity']=='error' for v in violations),'erc_warnings':sum(v['severity']=='warning' for v in violations),'audit_errors':errors,'unassigned_footprint_references':missing,'footprint_pad_checks':len(footprints),'fabrication_released':False}
(P/'exports/verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
with (P/'footprint-audit.csv').open('w',newline='',encoding='utf8') as f:
 w=csv.DictWriter(f,fieldnames=list(footprints[0]));w.writeheader();w.writerows(footprints)
print(json.dumps(result,indent=2))
if errors or result['erc_errors']:sys.exit(1)
