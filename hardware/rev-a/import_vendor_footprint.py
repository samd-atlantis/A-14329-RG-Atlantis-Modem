"""Run using bundled KiCad Python; import original manufacturer Altium PcbLib."""
from pathlib import Path
import pcbnew,sys,re
sys.stdout.reconfigure(encoding='utf8')
R=Path(__file__).resolve().parent
lib=next((R/'references/hlk-carrier').glob('*.PcbLib'))
plugin=pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.ALTIUM_DESIGNER)
print('Library',lib,flush=True)
names=plugin.FootprintEnumerate(str(lib))
print('Footprints',list(names),flush=True)
out=R/'kicad/Gateway.pretty';out.mkdir(exist_ok=True)
for name in names:
 fp=plugin.FootprintLoad(str(lib),name)
 print(name,[(p.GetNumber(),p.GetPosition().x,p.GetPosition().y) for p in fp.Pads()],flush=True)
 fp.SetValue(name)
 pcbnew.FootprintSave(str(out),fp)
 # Keep original converted vendor footprint, then derive project version with documented third thermal land.
 text=(out/(name+'.kicad_mod')).read_text(encoding='utf8')
 text=text.replace('(footprint "'+name+'"','(footprint "HLK7628N_56"',1)
 text=text.replace('(pad "57"','(pad "EP3"').replace('(pad "58"','(pad "EP2"')
 note='Manufacturer PcbLib converted by KiCad 9: signal pads and two thermal lands retained; EP1 central land added from manual p12. Exact revision mechanical validation REQUIRED.'
 if '(descr ' in text:text=re.sub(r'\(descr "[^"]*"\)', '(descr "'+note+'")',text,count=1)
 else:text=text.replace('(layer "F.Cu")','(layer "F.Cu") (descr "'+note+'")',1)
 text=text.rstrip()[:-1]+'(pad "EP1" smd rect (at -18.1 9.45) (size 5 5) (layers "F.Cu" "F.Paste" "F.Mask")))'
 (out/'HLK7628N_56.kicad_mod').write_text(text,encoding='utf8')
 print('Saved project footprint with vendor signal pads and documented provisional central thermal pad',flush=True)
