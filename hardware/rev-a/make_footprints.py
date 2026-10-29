"""Provisional module land patterns transcribed from vendor dimension drawings.
Not released until checked against exact module samples / vendor library.
"""
from pathlib import Path
import json,csv,shutil,sys
R=Path(__file__).resolve().parents[2];P=Path(__file__).resolve().parent/'kicad';D=P/'Gateway.pretty';D.mkdir(exist_ok=True)
def start(name,w,h,description):
 return f'(footprint "{name}" (version 20241229) (generator "pcbnew") (layer "F.Cu") (descr "{description}") (attr smd) (property "Reference" "REF**" (at 0 {-h/2-2} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15)))) (property "Value" "{name}" (at 0 {h/2+2} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15)))) (fp_rect (start {-w/2} {-h/2}) (end {w/2} {h/2}) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab")) (fp_rect (start {-w/2-1.5} {-h/2-1.5}) (end {w/2+1.5} {h/2+1.5}) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))'
def pad(num,x,y,w,h):return f'(pad "{num}" smd rect (at {x:.4f} {y:.4f}) (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask"))'
name='AiWB2_13';s=start(name,18,20,'PROVISIONAL: Ai-WB2-13 V1.1.0 pp9-10; 1.5 mm pitch; validate land extension and NC pads before manufacture')
for i in range(9):
 s+=pad(i+1,-8.8,-2.9+1.5*i,2.2,1.0)
 s+=pad(18-i,8.8,-2.9+1.5*i,2.2,1.0)
s+='(fp_rect (start -10 -11) (end 10 -3.4) (stroke (width 0.2) (type default)) (fill none) (layer "Dwgs.User")) (fp_text user "ANTENNA: NO COPPER / METAL ALL LAYERS" (at 0 -12.5) (layer "Dwgs.User") (effects (font (size 0.8 0.8) (thickness 0.15)))))'
(D/(name+'.kicad_mod')).write_text(s,encoding='utf8')
name='HLK7628N_56';s=start(name,35.5,18.7,'PROVISIONAL: Hi-Link manual p12 recommended pads; exact revision and thermal land geometry must be checked')
for i in range(23):
 s+=pad(i+1,32.1-1.4*i-17.75,-9.35,.9,1.8)
 s+=pad(i+34,1.3+1.4*i-17.75,9.35,.9,1.8)
for i in range(10):s+=pad(i+24,-17.75,3.0+1.4*i-9.35,1.8,.9)
# Vendor's unnumbered thermal pads intentionally left as separate EP identifiers, all grounded in symbol.
s+=pad('EP1',14.0-17.75,9.6-9.35,5,5)
s+=pad('EP2',29.25-17.75,5.3-9.35,2.7,1.2)
s+=pad('EP3',29.25-17.75,13.35-9.35,2.7,1.7)
s+=')'
# Prefer the converted manufacturer footprint; never overwrite it with a hand-transcribed fallback.
target=D/(name+'.kicad_mod')
if not target.exists() or 'Manufacturer PcbLib' not in target.read_text(encoding='utf8'):
 target.write_text(s,encoding='utf8')
# All selected standard footprints are vendored locally so the project does not depend on system paths.
data=json.loads((P/'design-data.json').read_text(encoding='utf8'));names=set(x['footprint'] for x in data['bom'] if x['footprint'])
libs={'Gateway'};missing=[]
for fp in names:
 lib,part=fp.split(':',1);libs.add(lib)
 if lib=='Gateway':continue
 src=R/'.tools/kicad/share/kicad/footprints'/(lib+'.pretty')/(part+'.kicad_mod')
 dest=P/'footprints'/(lib+'.pretty')/src.name
 if not src.exists():missing.append(fp);continue
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
table='(fp_lib_table (version 7)'+''.join(f'(lib (name "{lib}") (type "KiCad") (uri "${{KIPRJMOD}}/{"Gateway.pretty" if lib=="Gateway" else "footprints/"+lib+".pretty"}") (options "") (descr "Project-local footprints"))' for lib in sorted(libs))+')'
(P/'fp-lib-table').write_text(table,encoding='utf8')
print('Local footprints:',len(names),'missing:',missing)
