from pathlib import Path
import sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'.tools/python'))
import pymupdf
P=Path(__file__).resolve().parent/'kicad/exports'
for svg in P.glob('*.svg'):
 doc=pymupdf.open(svg);pdf=pymupdf.open('pdf',doc.convert_to_pdf())
 pdf[0].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(svg.with_suffix('.png'))
print('Rendered native KiCad SVG exports to review PNGs.')
