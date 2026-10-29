"""Generate review-only functional schematics and reproducible numerical studies."""
from pathlib import Path
import csv
import math
from html import escape

ROOT = Path(__file__).resolve().parent

def save_csv(name, rows):
    with (ROOT / name).open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def sheet(title, boxes, wires, notes):
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 760" role="img">',
         '<rect width="1200" height="760" fill="white"/>',
         '<style>text{font-family:Arial,sans-serif;fill:#172b40} .small{font-size:15px} .wire{stroke:#187f73;stroke-width:2;fill:none}</style>',
         f'<text x="30" y="40" font-size="24">{escape(title)}</text>',
         '<text x="30" y="68" font-size="15" fill="#a34b00">Rev A • Functional schematic • Pin mapping and component ratings unresolved • NOT FOR FABRICATION</text>']
    for x,y,w,h,lines in boxes:
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="#eef5fa" stroke="#172b40"/>')
        for i,line in enumerate(lines):
            s.append(f'<text x="{x+12}" y="{y+25+i*23}" font-size="16">{escape(line)}</text>')
    for path,x,y,label in wires:
        s.append(f'<path class="wire" d="{path}"/><text class="small" x="{x}" y="{y}">{escape(label)}</text>')
    for i,n in enumerate(notes):
        s.append(f'<text class="small" x="30" y="{590+i*24}">{escape(n)}</text>')
    s.append('<text x="30" y="738" font-size="13">Walchem gateway | 120 VAC | EG25-GL | 4 LAN | Wi-Fi + BLE retained | LoRa omitted | 2026-10-27</text></svg>')
    return '\n'.join(s)

sheets = {}
sheets['01-power.svg'] = sheet('01 / AC input and independently controlled DC rails', [
 (30,145,150,100,['J1: AC INPUT','L / N','PE: enclosure TBD']),
 (220,145,180,100,['F1 / surge / EMI','Line fuse first','Ratings TBD']),
 (450,145,220,100,['PS1: IRM-20-5','Isolated AC/DC','5 V / 20 W candidate']),
 (760,110,220,110,['U2: TPS62132','5 V → 3V3_ROUTER','L/C per TI reference']),
 (760,270,220,110,['U3: TPS62132','5 V → 3V3_MODEM','EN = MODEM_PWR_EN']),
 (760,430,220,110,['U7: load switch','3V3_ROUTER → 3V3_AUX','EN = WIFI_PWR_EN'])], [
 ('M180 180 H220',185,170,'L/N'),('M400 180 H450',402,168,'AC'),
 ('M670 180 H710 V155 H760',678,145,'5V_ISO'),
 ('M710 180 V315 H760',678,300,'5V_ISO'),
 ('M980 155 H1140',990,143,'U1 router'),('M980 315 H1140',990,303,'U4 modem'),
 ('M1010 155 V405 H720 V475 H760',1017,400,'3V3_ROUTER'),
 ('M980 475 H1140',990,463,'U5 Wi-Fi/BLE')], [
 'Primary L/N and secondary GND_ISO must remain separated; no implied earth-to-secondary bond.',
 'EN defaults: router on; modem and auxiliary radio controlled with defined safe pull states (values TBD).',
 'Modem output bulk capacitance must satisfy regulator stability/startup limits; simulation is sensitivity only.',
 'Power-stage support components, pin numbers and protection ratings require datasheet-level completion.',
 '20 W candidate passes assumed power screen; enclosure thermal derating still must be verified.'])
sheets['02-network.svg'] = sheet('02 / Four-port LAN, cellular and Wi-Fi/Bluetooth', [
 (40,120,280,145,['U1: HLK-7628N','128 MB / 32 MB candidate','USB host + integrated switch','Native Wi-Fi: IP networking']),
 (450,100,310,120,['J2–J5: four 10/100 MagJacks','MDI pairs, matching magnetics','ESD / chassis network TBD']),
 (450,285,310,120,['U4: EG25-GL Mini PCIe','USB 2.0 + modem power','SIM interface → sheet 03']),
 (450,460,310,100,['U5: Ai-WB2-13','Wi-Fi / Bluetooth LE retained','UART provisioning endpoint']),
 (875,285,280,120,['ANT1 / ANT2','LTE main + diversity','Matched coax and SMA']),
 (875,460,280,100,['2.4 GHz antenna provisions','U1: antenna per module guide','U5: PCB antenna keepout'])], [
 ('M320 160 H450',335,148,'LAN1–LAN4'),
 ('M320 205 H370 V330 H450',335,315,'USB D+/D−'),
 ('M320 240 H350 V505 H450',355,493,'UART TX/RX + CTRL'),
 ('M760 335 H875',775,323,'50 ohm RF'),
 ('M760 505 H875',770,493,'RF provisions')], [
 'Native router Wi-Fi is the candidate IP path for controllers; Ai-WB2-13 retains BLE / Wi-Fi provisioning.',
 'UART transparent data is not an automatic IP bridge. Wi-Fi topology and firmware must be demonstrated.',
 'Separate UART service console required; pin mux and logic levels remain unresolved.',
 'USB: short 90-ohm differential layout target; PHY guidance and exact modem connector pinout control final design.',
 'No LoRa device or antenna is included. Wi-Fi/Bluetooth are explicitly retained.'])
sheets['03-sim.svg'] = sheet('03 / Physical SIM and eUICC selection (functional interface only)', [
 (40,180,260,145,['U4 modem SIM interface','SIM_VCC / SIM_CLK','SIM_RST / SIM_IO','Modem-controlled voltage']),
 (430,180,290,145,['U6: SIM selector, part TBD','Isolate inactive branch','Route voltage and signals','No simultaneous SIM use']),
 (860,110,280,100,['J6: nano-SIM socket','Low-capacitance ESD','Card-detect if supported']),
 (860,350,280,100,['U8: MFF2 eUICC','Provider + exact SKU TBD','Provisioning stack required']),
 (430,430,290,100,['U1 control / firmware','SIM_SELECT + MODEM_EN','Safe off / switch / reattach'])], [
 ('M300 245 H430',310,233,'4 SIM nets'),
 ('M720 220 H790 V160 H860',745,145,'SIM_A'),
 ('M720 285 H790 V400 H860',745,385,'SIM_B'),
 ('M575 430 V325',585,380,'SELECT / sequencing')], [
 'Do not connect physical SIM and eUICC directly in parallel. Prevent unpowered-branch back-powering.',
 'TXS02326A is only a candidate architecture; its internal LDO/interface must be reconciled with modem SIM power.',
 'Exact Quectel firmware, SIM voltages, selector control and profile provisioning remain release gates.',
 'Selection gives one active subscription; eSIM multi-profile management is a separate software/provider function.',
 'No symbol pin numbers are implied by this functional drawing.'])
for name, content in sheets.items():
    (ROOT / name).write_text(content, encoding='utf-8')

budgets=[]
for name, modem, router, aux in [('Idle',.2,.25,.08),('Working',1,.6,.2),('Coincident peak',2,1,.35)]:
    output=3.3*(modem+router+aux)
    p5=output/.88+.5
    budgets.append(dict(case=name,modem_A=modem,router_A=router,wifi_ble_A=aux,
        output_3V3_W=round(output,3),input_5V_W=round(p5,3),input_5V_A=round(p5/5,3),
        buck_loss_W=round(output/.88-output,3),headroom_to_assumed_14W=round(14-p5,3)))
save_csv('power-budget.csv',budgets)

sweep=[]
for cap in [470,1000,1500,2200,3300]:
    for tau in [25,100,250]:
        c=cap*1e-6*.8
        # derivative sign is constant here; min occurs at a boundary.
        v0=3.3*.98; di=1.8; esr=.020
        samples=[v0-di*tau*1e-6*(1-math.exp(-t/(tau*1e-6)))/c-di*math.exp(-t/(tau*1e-6))*esr
                 for t in [i*1e-6 for i in range(2001)]]
        mv=min(samples)
        sweep.append(dict(cap_nominal_uF=cap,cap_effective_uF=cap*.8,tau_assumed_us=tau,
            ESR_path_ohm=esr,load_step_A=di,initial_rail_V=v0,min_rail_V=round(mv,4),
            screening_target_V=3.1,screen='MEETS ASSUMED TARGET' if mv>=3.1 else 'BELOW ASSUMED TARGET'))
save_csv('modem-step-sweep.csv',sweep)
assert budgets[-1]['headroom_to_assumed_14W'] > 0
assert next(x for x in sweep if x['cap_nominal_uF']==470 and x['tau_assumed_us']==100)['min_rail_V'] < 3.1
assert next(x for x in sweep if x['cap_nominal_uF']==3300 and x['tau_assumed_us']==100)['min_rail_V'] > 3.1

def table(rows):
    return '<table><tr>'+''.join('<th>'+escape(k)+'</th>' for k in rows[0])+'</tr>'+''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in r.values())+'</tr>' for r in rows)+'</table>'
html='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Walchem gateway Rev A review</title>
<style>body{font:16px Arial;margin:32px auto;max-width:1200px;color:#172b40;padding:0 20px}h1{font-size:30px}svg{width:100%;border:1px solid #ccd6df;margin:12px 0}table{border-collapse:collapse;font-size:13px;width:100%;margin:20px 0}td,th{padding:9px;border:1px solid #ccc;text-align:left}th{background:#eef5fa}.status{background:#fff2d8;padding:16px}pre{white-space:pre-wrap;line-height:1.5} @media print{svg{break-before:page}table{font-size:10px}}</style>
<h1>Walchem cellular gateway — preliminary Rev A</h1><p>120 VAC · four LAN ports · EG25-GL · physical SIM/eUICC · Wi-Fi + Bluetooth · no LoRa</p>
<p class="status">Functional schematic review only. Not pin-mapped CAD; no ERC or vendor-model SPICE run. Numerical results are assumption-driven screening, not hardware validation.</p>'''
html+=''.join(sheets.values())
html+='<h2>Power budget</h2><p>Assumed loads; 88% buck efficiency, 0.5 W auxiliary load. 14 W is a conservative scenario allowance on a 20 W supply, not a manufacturer derating claim.</p>'+table(budgets)
html+='<h2>Modem rail sensitivity</h2><p>1.8 A load increment; initial rail 3.234 V; -20% capacitance; 20 mΩ ESR/path allowance. Response time constants are assumed. 3.10 V is an internal screening target, not the verified modem minimum. Results do not approve capacitor values for the regulator.</p>'+table(sweep)
html+='<h2>Engineering notes, open items and primary references</h2><pre>'+escape((ROOT/'README.md').read_text(encoding='utf-8'))+'</pre></html>'
(ROOT/'review.html').write_text(html,encoding='utf-8')
print('Generated 3 functional schematic SVGs, review.html, 2 simulation CSVs.')
print('Peak 5 V input:',budgets[-1]['input_5V_W'],'W;',budgets[-1]['input_5V_A'],'A')
print('Model sanity checks passed. No ERC, vendor SPICE, or hardware validation claimed.')
