import collections,json
m={}; mat=''
for l in open('hardware/easyeda/mesh-check46/modem-height-check46.obj'):
 if l.startswith('usemtl '): mat=l.strip()[7:]
 elif l.startswith('v '):
  v=list(map(float,l.split()[1:])); a=m.setdefault(mat,{'min':[1e9]*3,'max':[-1e9]*3,'z':collections.Counter()}); a['min']=[min(x,y) for x,y in zip(a['min'],v)]; a['max']=[max(x,y) for x,y in zip(a['max'],v)]; a['z'][round(v[2],5)]+=1
print(json.dumps({k:{**v,'z':v['z'].most_common(5)} for k,v in m.items() if k in ['mtl14','mtl15','mtl46','mtl47','mtl48','mtl49','mtl50']},indent=2))
