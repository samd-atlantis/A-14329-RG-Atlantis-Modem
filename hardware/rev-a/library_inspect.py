from pathlib import Path
import sys,copy
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'.tools/python'))
import sexpdata as sx
def key(n):return str(n[0]) if isinstance(n,list) and n else ''
def nodes(n,k):return [x for x in n if key(x)==k]
def node(n,k):return next((x for x in n if key(x)==k),None)
def load(lib,name):
 d=sx.load(open(R/'.tools/kicad/share/kicad/symbols'/f'{lib}.kicad_sym',encoding='utf8'))
 syms={n[1]:n for n in nodes(d,'symbol')}
 n=copy.deepcopy(syms[name]);ext=node(n,'extends')
 if ext:
  parent=load(lib,ext[1]);parent[1]=name
  childprops={p[1]:p for p in nodes(n,'property')}
  parent=[x for x in parent if not(key(x)=='property' and x[1] in childprops)]+list(childprops.values())
  for sub in nodes(parent,'symbol'):
   sub[1]=name+'_'+sub[1].rsplit('_',2)[-2]+'_'+sub[1].rsplit('_',2)[-1]
  n=parent
 return n
if __name__=='__main__':
 for lib,name in [('Converter_ACDC','IRM-20-5'),('Connector','RJ45_Wuerth_7499010121A'),('Regulator_Switching','TPS62132'),('Interface_Expansion','MCP23008-xSS'),('Power_Protection','TPD2EUSB30')]:
  n=load(lib,name);print('\n',lib,name)
  print([(p[1],p[2]) for p in nodes(n,'property')])
  for sub in nodes(n,'symbol'):
   for p in nodes(sub,'pin'):print(str(p[1]),node(p,'number')[1],node(p,'name')[1],node(p,'at')[1:])
