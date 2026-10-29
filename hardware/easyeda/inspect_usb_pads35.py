from route_geometry import load
p,pads=load('routing-native35-docs.json')
for q in pads:
 if q['ref'] in ('J14','J17') and q['pin'] in ('1','2','3','4'):print(q)
