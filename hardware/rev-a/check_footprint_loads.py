"""Run in KiCad's bundled Python to verify local footprints load in its native parser."""
from pathlib import Path
import pcbnew,json
P=Path(__file__).resolve().parent/'kicad';results=[]
for lib in [P/'Gateway.pretty']+list((P/'footprints').glob('*.pretty')):
 for path in lib.glob('*.kicad_mod'):
  fp=pcbnew.FootprintLoad(str(lib),path.stem)
  if fp is None:raise ValueError('Native parser rejected '+str(path))
  results.append(dict(file=str(path.relative_to(P)),pads=len(list(fp.Pads()))))
(P/'exports/footprint-loads.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print('Native KiCad footprint parser accepted',len(results),'footprints.')
