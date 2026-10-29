from pathlib import Path
import sys,re
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parents[1]/'.tools'/'python'))
if '--html' in sys.argv:
 text=(R/'references'/'quectel-product.html').read_text(encoding='utf8')
 for m in re.finditer('Hardware_Design',text):print(text[m.start()-2000:m.start()+2000])
else:
 import pymupdf
 for p in (R/'references').glob('*.pdf'):
  doc=pymupdf.open(p)
  (p.with_suffix('.txt')).write_text('\n'.join(f'\n=== PDF PAGE {i+1} ===\n'+pg.get_text() for i,pg in enumerate(doc)),encoding='utf8')
  if p.stem=='ai-wb2':pages=[9,10,11,15]
  elif p.stem=='hlk':pages=[10,11,12,13,15,16]
  elif p.stem=='magjack':pages=[0,1]
  elif p.stem=='euicc':pages=[13,14]
  elif p.stem=='acdc':pages=[1]
  else:pages=[]
  for i in pages:
   if i<len(doc):doc[i].get_pixmap(matrix=pymupdf.Matrix(1.6,1.6)).save(R/'references'/f'{p.stem}-p{i+1}.png')
 print('Extracted PDF text and pin-drawing images.')
