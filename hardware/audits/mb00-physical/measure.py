"""Read-only dimensional/return-plane review of frozen assembly49.

Uses standard-library geometry; arc tessellation for pour point tests is an
independent aid, not a fabrication or field-solver conversion.
"""
from pathlib import Path
import collections, hashlib, json, math, sys, zipfile
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
SOURCE=ROOT/'hardware/releases/A-14329-MB00/pcb-assembly49.epro2'
docs=[]
with zipfile.ZipFile(SOURCE) as z:
    for name in z.namelist():
        if not name.endswith('.epru'):continue
        head,rows=None,{}
        for line in z.read(name).decode('utf-8-sig').splitlines():
            if not line:continue
            if line.endswith('|'):line=line[:-1]
            a,b=line.split('||',1); h=json.loads(a); b=json.loads(b) if b else None
            if h['type']=='DOCHEAD':
                if head:docs.append({'head':head,'records':[r for r in rows.values() if r['b'] is not None]})
                head={'h':h,'b':b};rows={}
            else:rows[h['id']]={'h':h,'b':b}
        if head:docs.append({'head':head,'records':[r for r in rows.values() if r['b'] is not None]})
p=next(d['records'] for d in docs if d['head']['b']['docType']=='PCB')
fresh=OUT/'.native-docs.json';fresh.write_text(json.dumps(docs),encoding='utf8')
sys.path.insert(0,str(ROOT/'hardware/easyeda'))
from audit_net_islands import audit
from route_geometry import load
from check_route_fragment import segdist,rectdist,shape
from route_local import dist
pcb,pads=load(str(fresh))
MM=.0254
def decode_path(path):
    pts=[tuple(path[:2])]; i=2; mode='L'
    while i<len(path):
        if isinstance(path[i],str):mode=path[i]; i+=1;continue
        if mode=='L':pts.append(tuple(path[i:i+2]));i+=2
        elif mode=='ARC':
            deg,x,y=path[i:i+3]; i+=3; a=pts[-1];z=(x,y);t=math.radians(deg);dx=x-a[0];dy=y-a[1]
            if abs(t)<1e-10:pts.append(z);continue
            cx=(a[0]+x)/2-dy/(2*math.tan(t/2));cy=(a[1]+y)/2+dx/(2*math.tan(t/2));rr=math.hypot(a[0]-cx,a[1]-cy);aa=math.atan2(a[1]-cy,a[0]-cx)
            count=max(2,math.ceil(abs(deg)/2))
            for j in range(1,count+1):pts.append((cx+rr*math.cos(aa+t*j/count),cy+rr*math.sin(aa+t*j/count)))
        else:raise ValueError(mode)
    return pts
def winding(poly,point):
    x,y=point;wn=0
    for a,b in zip(poly,poly[1:]+poly[:1]):
        cross=(b[0]-a[0])*(y-a[1])-(x-a[0])*(b[1]-a[1])
        if a[1]<=y<b[1] and cross>0:wn+=1
        elif b[1]<=y<a[1] and cross<0:wn-=1
    return wn
pours={r['h']['id']:r['b'] for r in p if r['h']['type']=='POUR'}
planes=[]
for r in p:
    if r['h']['type']!='POURED':continue
    par=pours[json.loads(r['h']['id'])[1]]
    paths=[decode_path(path) for f in r['b']['pourFill'] for path in f['path']]
    bounds=[(min(x for x,y in q),min(y for x,y in q),max(x for x,y in q),max(y for x,y in q)) for q in paths]
    areas=[sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(q,q[1:]+q[:1]))/2 for q in paths]
    planes.append({'id':json.loads(r['h']['id'])[1],'net':par['netName'],'layer':par['layerId'],'paths':paths,'bounds':bounds,'areas':areas})
def inside(plane,xmil,ymil):
    x,y=xmil/10,ymil/10
    return sum(winding(poly,(x,y)) for poly,bb in zip(plane['paths'],plane['bounds']) if bb[0]<=x<=bb[2] and bb[1]<=y<=bb[3])!=0
ground_vias=[r for r in p if r['h']['type']=='VIA' and r['b']['netName']=='GND_ISO']
plane_vias=[]
for v in ground_vias:
    b=v['b'];plane_vias.append({'id':v['h']['id'],'x_mm':b['centerX']*MM,'y_mm':b['centerY']*MM,'on_filled_layers':[pl['layer'] for pl in planes if inside(pl,b['centerX'],b['centerY'])]})
# Ground connectivity graph from the same bounding-pad/trace approach as the
# older net-islands helper, with each native filled plane added as one node.
objects=[]
for pad in pads:
    if pad['net']=='GND_ISO':objects.append({'id':pad['ref']+'.'+pad['pin'],'pad':pad,'a':(pad['x'],pad['y']),'z':(pad['x'],pad['y']),'r':0,'layers':{1,2,15,16} if pad['layer']==12 else {pad['layer']}})
for r in p:
    if r['h']['type'] not in ('LINE','VIA') or r['b'].get('netName')!='GND_ISO':continue
    a,z,rad,ls=shape(r);objects.append({'id':r['h']['id'],'a':a,'z':z,'r':rad,'layers':ls,'via':r['h']['type']=='VIA'})
parent=list(range(len(objects)+len(planes)))
def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
def gap(a,b):
    if not a['layers']&b['layers']:return 1e9
    if 'pad' in a and 'pad' in b:
        x,y=a['pad'],b['pad'];return math.hypot(max(abs(x['x']-y['x'])-(x['w']+y['w'])/2,0),max(abs(x['y']-y['y'])-(x['h']+y['h'])/2,0))
    if 'pad' in b:a,b=b,a
    if 'pad' in a:
        q=a['pad'];return rectdist(b['a'],b['z'],(q['x']-q['w']/2,q['y']-q['h']/2,q['x']+q['w']/2,q['y']+q['h']/2))-b['r']
    return segdist(a['a'],a['z'],b['a'],b['z'])-a['r']-b['r']
for i,a in enumerate(objects):
    for j,b in enumerate(objects[:i]):
        if gap(a,b)<=.02:parent[find(i)]=find(j)
def groups():
    gs=collections.defaultdict(list)
    for i,o in enumerate(objects):gs[find(i)].append(o['id'])
    return list(gs.values())
before=groups(); links=[]
for i,o in enumerate(objects):
    if not(o.get('via') or 'pad' in o and o['pad']['layer']==12):continue
    for j,pl in enumerate(planes):
        if pl['layer'] in o['layers'] and inside(pl,*o['a']):
            parent[find(i)]=find(len(objects)+j);links.append({'object':o['id'],'plane':pl['id']})
after=groups()
# Convert isolated-net groups, counting only pad-bearing components separately.
net_islands={net:audit(str(fresh),net) for net in sorted({x['net'] for x in pads if x['net'] and x['net']!='MECHANICAL_HOLE' and x['net']!='GND_ISO'})}
track_by_net=collections.defaultdict(list)
for r in p:
    if r['h']['type']=='LINE':track_by_net[r['b']['netName']].append(r)
ac=[]
for r in p:
    if r['h']['type']!='LINE':continue
    b=r['b'];n=b['netName'];w=b['width']*MM;l=math.hypot(b['endX']-b['startX'],b['endY']-b['startY'])*MM
    if n not in ['AC_L_IN','AC_L_FUSED','AC_N','CHASSIS_PE'] or (n=='CHASSIS_PE' and w<1.6):continue
    resistance=1.724e-8*(l/1000)/((w/1000)*35e-6)
    ac.append({'id':r['h']['id'],'net':n,'layer':b['layerId'],'width_mm':w,'length_mm':l,'r_20C_35um_milliohm':resistance*1000,'heat_at_10A_W':resistance*100,'note':'Hypothetical 10A through THIS segment, not actual branch load or temperature prediction; PSU-only branches do not carry panel feed load.'})
pairs=[]
for prefix in [f'LAN{i}_{side}' for i in range(1,5) for side in ['TX','RX']]+['USB_HOST_D','USB_MODEM_D','USB_SERVICE_D','USB_CONSOLE_D']:
    a=prefix+'P';b=prefix+('M' if prefix.startswith('USB') else 'N')
    def stats(net):
        ls=track_by_net[net];vs=[x for x in p if x['h']['type']=='VIA' and x['b']['netName']==net]
        return {'net':net,'segments':len(ls),'vias':len(vs),'layers':sorted({x['b']['layerId'] for x in ls}),'widths_mm':sorted({round(x['b']['width']*MM,6) for x in ls}),'length_sum_mm':sum(math.hypot(x['b']['endX']-x['b']['startX'],x['b']['endY']-x['b']['startY'])*MM for x in ls)}
    x,y=stats(a),stats(b);pairs.append({'name':prefix,'P':x,'N':y,'sum_difference_mm':abs(x['length_sum_mm']-y['length_sum_mm'])})
return_plane_screen=[]
for pair in pairs:
    for conductor in ['P','N']:
        net=pair[conductor]['net'];unsupported=total=0;bad=[]
        for r in track_by_net[net]:
            b=r['b'];pl=next(x for x in planes if x['layer']==(15 if b['layerId']==1 else 16));ll=math.hypot(b['endX']-b['startX'],b['endY']-b['startY']);count=max(1,math.ceil(ll*MM/.25));miss=0
            for i in range(count):
                t=(i+.5)/count;px=b['startX']+t*(b['endX']-b['startX']);py=b['startY']+t*(b['endY']-b['startY'])
                if not inside(pl,px,py):miss+=1
            total+=ll*MM;unsupported+=ll*MM*miss/count
            if miss:bad.append({'id':r['h']['id'],'layer':b['layerId'],'segment_length_mm':ll*MM,'unsupported_sample_length_mm':ll*MM*miss/count,'start_mm':[b['startX']*MM,b['startY']*MM],'end_mm':[b['endX']*MM,b['endY']*MM]})
        return_plane_screen.append({'net':net,'length_sum_mm':total,'unsupported_sampled_length_mm':unsupported,'flagged_segments':bad})
out={'source':str(SOURCE.relative_to(ROOT)),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'non_ground_net_groups':net_islands,'differential_pairs':pairs,'mains_tracks':ac,'thermal_assumptions':{'temperature_C':20,'copper_thickness_um':35,'rho_ohm_m':1.724e-8,'limitation':'Resistance/heat estimate only; excludes pad/current crowding, plated barrel, solder/contact resistance, branch current division, copper temperature coefficient and heat transfer.'},'ground_via_native_pour_center_tests':plane_vias,'plane_polygon_limits':'Native cached filled paths decoded at 10 native mil per cached unit; arc tessellation2degrees; point-in-filled-polygon test at via centers ONLY, not full-plane continuity/impedance proof.','stackup':[r for r in p if r['h']['type']=='LAYER_PHYS']}
out['ground_connectivity']={'groups_without_pours':before,'groups_with_cached_pours':after,'plane_links':links,'plane_contour_areas_native_units2':{x['id']:x['areas'] for x in planes},'limitation':'Pad connections use bounding boxes; native cached pour contours assumed valid. Each plane has one outer contour with holes; this is complementary evidence, not regenerated native DRC or dielectric safety validation.'}
out['return_plane_projection_screen']=return_plane_screen
out['return_plane_projection_limit']='0.25mm midpoint sampling at trace CENTER; isolated antipads and pad breakout edges are counted. Flagged length is not an SI fail criterion; review geometry before judging. Does not model return current spread, stitching via inductance or differential field coupling.'
keepout_hits=[]
for r in p:
    if r['h']['type'] not in ('LINE','VIA') or r['b'].get('layerId',1) not in [1,2,15,16]:continue
    a,z,rad,ls=shape(r)
    for q in p:
        if q['h']['type']!='REGION' or 'TRACK' not in q['b'].get('prohibitType',[]) or q['b']['layerId'] not in ls|{12}:continue
        for path in q['b']['path']:
            if path[0]=='CIRCLE':clear=dist((path[1],path[2]),a,z)-path[3]-rad
            elif path[0]=='R' and path[5]==0:
                _,x,y,w,h,*_=path;clear=rectdist(a,z,(x,y-h,x+w,y))-rad
            else:raise ValueError(('Unsupported track keepout',path))
            if clear<-.02:keepout_hits.append({'route_id':r['h']['id'],'region_id':q['h']['id'],'overlap_mm':-clear*MM})
out['track_and_via_keepout_intersections']=keepout_hits
(OUT/'measurements.json').write_text(json.dumps(out,indent=2))
print('Non-GND pad-bearing split nets:',{n:len([g for g in gs if g['pads']]) for n,gs in net_islands.items() if len([g for g in gs if g['pads']])>1})
print('Ground via centers inside native pours:',collections.Counter(tuple(v['on_filled_layers']) for v in plane_vias))
print('Ground groups before/after cached pours:',len(before),len(after))
print('Return centerline screen:',[(x['net'],round(x['unsupported_sampled_length_mm'],3)) for x in return_plane_screen])
print('Pair length SUM differences:',[(p['name'],round(p['sum_difference_mm'],4)) for p in pairs])
print('Track/via keepout intersections:',len(keepout_hits))
fresh.unlink()
