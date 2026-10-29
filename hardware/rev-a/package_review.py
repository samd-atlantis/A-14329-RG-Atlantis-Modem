from pathlib import Path
import json,csv,zipfile,html,urllib.parse,hashlib
R=Path(__file__).resolve().parent;P=R/'kicad'
v=json.loads((P/'exports/verification.json').read_text())
with (P/'system-bom.csv').open('w',newline='',encoding='utf8') as f:
 w=csv.writer(f);w.writerow(['reference','quantity','description','status'])
 w.writerows([['CELL1',1,'Quectel EG25-GL Mini PCIe daughtercard','Exact carrier-approved SKU to be selected; separate from J8 socket'],['ANT1/ANT2',2,'LTE main and diversity antennas','Band coverage / gain / enclosure and certification review'],['RF1/RF2',2,'Modem coax to enclosure RF connectors','Connector types, cable length and insertion loss TBD'],['CASE1',1,'Touch-safe enclosure with 2.4 GHz RF window','Dimensions, PE scheme and environment rating TBD'],['ANT3',1,'Router 2.4 GHz antenna assembly','Use module-supported antenna connector, keep pin22 unlinked unless vendor RF modification selected']])
esc=html.escape
def url(p):return urllib.parse.quote(str(p).replace('\\','/'))
rows=list(csv.DictReader((P/'pin-map.csv').open(encoding='utf8')))
title='Walchem gateway / native KiCad Rev A1'
content=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{font:16px system-ui,sans-serif;background:#f4f6f8;color:#182e44;max-width:1460px;margin:32px auto;padding:0 24px}}h1{{font-size:32px}}h2{{margin-top:36px}}a{{color:#145e97}}.card{{background:white;padding:20px 24px;border:1px solid #d3dce4;border-radius:10px;margin:18px 0}}.metrics{{display:flex;gap:20px;flex-wrap:wrap}}.metric{{flex:1;min-width:150px;background:#e5f2ee;padding:16px;border-radius:7px}}.metric b{{display:block;font-size:26px}}.pending{{background:#fff3d9;padding:18px;border-radius:7px}}img{{width:100%;height:auto;border:1px solid #d3dce4;background:white}}table{{border-collapse:collapse;width:100%;font-size:13px;background:white}}td,th{{padding:8px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#e7edf2}}.scroll{{max-height:520px;overflow:auto}}input{{font:inherit;padding:10px;width:95%;margin:14px 0}}pre{{white-space:pre-wrap;font-size:14px;line-height:1.5}}.links a{{display:inline-block;margin-right:20px;margin-bottom:10px}}</style>
<h1>{title}</h1><p>120 VAC · four Ethernet LAN ports · EG25-GL · physical SIM / eUICC · Wi-Fi + Bluetooth retained · no LoRa</p>
<div class="card links"><a href="walchem_gateway.kicad_pro">Open KiCad project</a><a href="../walchem_gateway_rev_a1.zip">Download project ZIP</a><a href="design-review.md">Engineering review / layout gates</a><a href="bom.csv">PCB BOM</a><a href="system-bom.csv">Off-board system BOM</a><a href="pin-map.csv">Pin map CSV</a><a href="exports/erc.json">Native ERC report</a><a href="exports/netlist.xml">Native netlist</a></div>
<div class="metrics"><div class="metric"><b>{v['schematic_sheets']}</b>native schematic sheets</div><div class="metric"><b>{v['erc_errors']} / {v['erc_warnings']}</b>ERC errors / warnings</div><div class="metric"><b>{v['connected_pins_checked']}</b>connected pins checked against KiCad netlist</div><div class="metric"><b>{v['critical_checks']}</b>additional critical mapping checks</div></div>
<div class="card pending"><strong>Engineering review; not fabrication released.</strong> Six component footprints remain unassigned: J1, F1, J8, U8, J9, U11. The router thermal-land documentation and Ai-WB2 NC/ground pads require exact-revision clarification. Selected module land patterns are provisional. A clean ERC does not validate those physical choices, mains integration, firmware, RF coexistence or regulator transients.</div>'''
svgs=sorted((P/'exports').glob('*.svg'),key=lambda x:x.name)
for svg in svgs:
 label=svg.stem.removeprefix('walchem_gateway-')
 if label=='walchem_gateway':label='00 - Schematic index'
 content+=f'<section class="card"><h2>{esc(label)}</h2><a href="exports/{url(svg.name)}">Open full-resolution SVG</a><img loading="lazy" src="exports/{url(svg.name)}" alt="{esc(label)}"></section>'
content+='<div class="card"><h2>Search physical pin map</h2><input id="filter" placeholder="Filter reference, pin name, net or source"><div class="scroll"><table id="pins"><thead><tr>'+''.join('<th>'+esc(k)+'</th>' for k in ['reference','pin','pin_name','net','source'])+'</tr></thead><tbody>'
for row in rows:content+='<tr>'+''.join('<td>'+esc(row[k])+'</td>' for k in ['reference','pin','pin_name','net','source'])+'</tr>'
content+='</tbody></table></div></div><div class="card"><h2>Engineering review and release boundary</h2><pre>'+esc((P/'design-review.md').read_text(encoding='utf8'))+'</pre></div><script>document.getElementById("filter").addEventListener("input",function(){const q=this.value.toLowerCase();document.querySelectorAll("#pins tbody tr").forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));});</script></html>'
(P/'review.html').write_text(content,encoding='utf8')
# Preserve old concept review, add a prominent route to current native schematics.
old=R/'review.html';text=old.read_text(encoding='utf8')
banner='<div style="background:#e5f2ee;padding:18px;border:1px solid #86aa9b"><strong>Native KiCad Rev A1 is available.</strong> <a href="kicad/review.html">Open current schematics, ERC and pin-map review</a>. The functional diagrams below are the original concept.</div>'
if 'Native KiCad Rev A1 is available.' not in text:text=text.replace('<h1>',banner+'<h1>',1);old.write_text(text,encoding='utf8')
zip_path=R/'walchem_gateway_rev_a1.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
 for file in sorted(P.rglob('*')):
  if file.is_file() and file.suffix not in ['.lck','.kicad_prl'] and '-backups' not in str(file):z.write(file,'walchem_gateway_rev_a1/'+str(file.relative_to(P)))
print('Packaged',zip_path.stat().st_size,'bytes; SHA256',hashlib.sha256(zip_path.read_bytes()).hexdigest())
