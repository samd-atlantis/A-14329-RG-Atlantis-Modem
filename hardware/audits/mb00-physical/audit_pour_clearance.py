"""Full-shape distance/intersection audit against native cached ground pours.

Requires local Shapely2.1.2; never writes release/native design files. Circular
arcs are tessellated with <=0.00001mm sagitta, not sampled at trace centers.
"""
from pathlib import Path
import collections, hashlib, json, math, sys, zipfile
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
sys.path.insert(0,str(OUT/'.deps'))
import shapely
from shapely.geometry import Point,LineString,Polygon,box
from shapely.ops import nearest_points,unary_union
from shapely.validation import explain_validity
SOURCE=ROOT/'hardware/releases/A-14329-MB00/pcb-assembly49.epro2'
MM=.0254
EPS_MM=.00001
QUADS=1024
docs=[]
with zipfile.ZipFile(SOURCE) as z:
    for name in z.namelist():
        if not name.endswith('.epru'):continue
        head,rows=None,{}
        for line in z.read(name).decode('utf-8-sig').splitlines():
            if not line:continue
            if line.endswith('|'):line=line[:-1]
            a,b=line.split('||',1);h=json.loads(a);b=json.loads(b) if b else None
            if h['type']=='DOCHEAD':
                if head:docs.append({'head':head,'records':[r for r in rows.values() if r['b'] is not None]})
                head={'h':h,'b':b};rows={}
            else:rows[h['id']]={'h':h,'b':b}
        if head:docs.append({'head':head,'records':[r for r in rows.values() if r['b'] is not None]})
pcb=next(d['records'] for d in docs if d['head']['b']['docType']=='PCB')
fresh=OUT/'.pour-native-docs.json';fresh.write_text(json.dumps(docs),encoding='utf8')
sys.path.insert(0,str(ROOT/'hardware/easyeda'))
from route_geometry import load
_,pads=load(str(fresh));fresh.unlink()

def decode(path):
    # Cached poured coordinates are 1/10 of board coordinates: one unit=10mil.
    scale=10*MM
    pts=[(path[0]*scale,path[1]*scale)];i=2;mode='L'
    while i<len(path):
        if isinstance(path[i],str):mode=path[i];i+=1;continue
        if mode=='L':pts.append((path[i]*scale,path[i+1]*scale));i+=2
        elif mode=='ARC':
            deg,x,y=path[i:i+3];x*=scale;y*=scale;i+=3;a=pts[-1];t=math.radians(deg);dx=x-a[0];dy=y-a[1]
            if abs(t)<1e-12:pts.append((x,y));continue
            cx=(a[0]+x)/2-dy/(2*math.tan(t/2));cy=(a[1]+y)/2+dx/(2*math.tan(t/2));rr=math.hypot(a[0]-cx,a[1]-cy);aa=math.atan2(a[1]-cy,a[0]-cx)
            step=2*math.acos(max(-1,min(1,1-EPS_MM/rr)))
            count=max(2,math.ceil(abs(t)/step))
            for j in range(1,count):pts.append((cx+rr*math.cos(aa+t*j/count),cy+rr*math.sin(aa+t*j/count)))
            pts.append((x,y))
        else:raise ValueError(mode)
    return pts

pours={r['h']['id']:r['b'] for r in pcb if r['h']['type']=='POUR'}
planes=[]
for r in pcb:
    if r['h']['type']!='POURED':continue
    rid=json.loads(r['h']['id'])[1];parent=pours[rid]
    paths=[decode(path) for f in r['b']['pourFill'] for path in f['path']]
    rings=[Polygon(q) for q in paths];outer=max(range(len(rings)),key=lambda i:rings[i].area)
    geom=Polygon(paths[outer],[q for i,q in enumerate(paths) if i!=outer])
    info={'id':rid,'net':parent['netName'],'layer':parent['layerId'],'hole_count':len(paths)-1,'raw_area_mm2':geom.area,'raw_is_valid':geom.is_valid,'raw_validity':explain_validity(geom),'normalized_holes':[]}
    assert rings[outer].is_valid, ('Invalid outer contour',rid)
    holes=[]
    for i,q in enumerate(rings):
        if i==outer:continue
        if not q.is_valid:
            normalized=shapely.make_valid(q)
            info['normalized_holes'].append({'path_index':i,'raw_validity':explain_validity(q),'bounds_mm':list(q.bounds),'raw_area_mm2':q.area,'normalized_area_mm2':normalized.area,'area_change_mm2':normalized.area-q.area,'result_type':normalized.geom_type})
            q=normalized
        holes.append(q)
    geom=rings[outer].difference(unary_union(holes))
    info.update({'area_mm2':geom.area,'is_valid':geom.is_valid,'validity':explain_validity(geom)})
    assert geom.is_valid,info
    planes.append((info,geom,rings[outer]))

def capsule(a,b,r):
    # Exact stadium distance uses distance(axis, filled polygon) minus radius.
    # This avoids quadratic distance scans over thousands of buffer vertices.
    return Point(a) if a==b else LineString([a,b])
items=[]
for p in pads:
    if p['net'] not in ['AC_L_IN','AC_L_FUSED','AC_N','CHASSIS_PE']:continue
    x,y,w,h=p['x']*MM,p['y']*MM,p['w']*MM,p['h']*MM
    if p['shape']=='ELLIPSE':
        assert abs(w-h)<.000001,(p['ref'],p['pin'],w,h);g=Point(x,y);radius=w/2
    elif p['shape']=='OVAL':
        if w>=h:g=capsule((x-(w-h)/2,y),(x+(w-h)/2,y),h/2);radius=h/2
        else:g=capsule((x,y-(h-w)/2),(x,y+(h-w)/2),w/2);radius=w/2
    elif p['shape']=='RECT':g=box(x-w/2,y-h/2,x+w/2,y+h/2);radius=0
    else:raise ValueError(p['shape'])
    items.append(({'id':p['id'],'name':p['ref']+'.'+p['pin'],'kind':'PAD','net':p['net'],'layers':[1,2,15,16] if p['layer']==12 else[p['layer']],'capsule_radius_mm':radius},g))
for r in pcb:
    b=r['b'];t=r['h']['type']
    if t not in ['LINE','VIA'] or b.get('netName') not in ['AC_L_IN','AC_L_FUSED','AC_N','CHASSIS_PE']:continue
    if t=='LINE':g=capsule((b['startX']*MM,b['startY']*MM),(b['endX']*MM,b['endY']*MM),b['width']*MM/2);ls=[b['layerId']];radius=b['width']*MM/2
    else:g=Point(b['centerX']*MM,b['centerY']*MM);ls=[1,2,15,16];radius=b['viaDiameter']*MM/2
    items.append(({'id':r['h']['id'],'name':r['h']['id'],'kind':t,'net':b['netName'],'layers':ls,'capsule_radius_mm':radius},g))
distances=[]
for info,g in items:
    for pi,pg,outerg in planes:
        core_distance=g.distance(pg);radius=info['capsule_radius_mm'];d=max(0,core_distance-radius);a,b=nearest_points(g,pg)
        ax,ay=a.x,a.y
        if core_distance>radius and radius:ax+=(b.x-a.x)*radius/core_distance;ay+=(b.y-a.y)*radius/core_distance
        distances.append({'item':info,'plane':pi['id'],'plane_layer':pi['layer'],'same_physical_layer':pi['layer'] in info['layers'],'distance_mm':d,'signed_capsule_gap_mm':core_distance-radius,'conservative_outer_contour_distance_mm':max(0,g.distance(outerg)-radius),'nearest_item_xy_mm':[ax,ay],'nearest_ground_xy_mm':[b.x,b.y]})

keepouts=[]
for r in pcb:
    if r['h']['type']!='REGION':continue
    b=r['b']
    if not set(b.get('prohibitType',[]))&{'COPPER','FILL','PLANE'}:continue
    for pathn,path in enumerate(b['path']):
        if path[0]=='CIRCLE':g=Point(path[1]*MM,path[2]*MM);radius=path[3]*MM
        elif path[0]=='R':
            _,x,y,w,h,angle,*_=path;assert angle==0;g=box(x*MM,(y-h)*MM,(x+w)*MM,y*MM);radius=0
        else:raise ValueError(path)
        for pi,pg,outerg in planes:
            if b['layerId'] not in [12,pi['layer']]:continue
            gap=g.distance(pg)-radius
            area=(g.buffer(radius,quad_segs=QUADS) if radius else g).intersection(pg).area if gap<-.00002 or not radius else 0
            keepouts.append({'region':r['h']['id'],'path':pathn,'prohibits':b['prohibitType'],'plane':pi['id'],'distance_mm':max(0,gap),'signed_capsule_gap_mm':gap,'intersection_area_mm2':area})

def smallest(net,same_only=False):
    candidates=[r for r in distances if r['item']['net']==net and(not same_only or r['same_physical_layer'])]
    return min(candidates,key=lambda r:r['distance_mm']) if candidates else None
selectors=[r for r in pcb if r['h']['type']=='RULE_SELECTOR' and 'GND_ISO' in r['h']['id']]
summary={n:smallest(n) for n in ['AC_L_IN','AC_L_FUSED','AC_N']}
summary['CHASSIS_PE_same_layer']=smallest('CHASSIS_PE',True)
summary['CHASSIS_PE_planar_projection']=smallest('CHASSIS_PE')
critical=summary['AC_N'];cb=next(r['b'] for r in pcb if r['h']['id']==critical['item']['id']);gx,gy=critical['nearest_ground_xy_mm'];ax,ay=cb['startX']*MM,cb['startY']*MM;bx,by=cb['endX']*MM,cb['endY']*MM;dx,dy=bx-ax,by-ay;t=max(0,min(1,((gx-ax)*dx+(gy-ay)*dy)/(dx*dx+dy*dy)));analytic=math.hypot(gx-ax-t*dx,gy-ay-t*dy)-cb['width']*MM/2
assert abs(analytic-critical['distance_mm'])<1e-9
out={'source':str(SOURCE.relative_to(ROOT)),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'shapely':shapely.__version__,'geos':shapely.geos_version_string,'geometry_note':'Full polygon/round-pad/capsule/oval shapes; NOT center distances. Circular cached-fill arcs have <=0.00001mm sagitta; buffer quad_segs1024 (max6.5mm radius error<0.000002mm). Distances are in XY; all-layer primary projection conservatively checks layout separation, not vertical insulation. Invalid hole contours normalized with GEOS make_valid then subtracted as a union from valid outer contour; all normalization logged. Source untouched. Primary conservative outer-contour distances ignore holes entirely and therefore do not depend on this normalization.','planes':[x for x,g,o in planes],'item_counts':{n:dict(collections.Counter(i['kind'] for i,g in items if i['net']==n)) for n in ['AC_L_IN','AC_L_FUSED','AC_N','CHASSIS_PE']},'minimums':summary,'primary_rule_target_mm':8,'primary_GND_under_8mm':[r for r in distances if r['item']['net'].startswith('AC_') and r['distance_mm']<8-.00002],'primary_outer_bound_under_8mm':[r for r in distances if r['item']['net'].startswith('AC_') and r['conservative_outer_contour_distance_mm']<8-.00002],'GND_rule_selectors':selectors,'keepout_comparisons':keepouts,'keepout_overlap_above_0p0001_mm2':[r for r in keepouts if r['intersection_area_mm2']>.0001],'all_distances':distances}
out['independent_critical_line_to_corner_check_mm']=analytic
(OUT/'pour-clearance.json').write_text(json.dumps(out,indent=2),encoding='utf8',newline='\n')
print('Valid planes:',[i for i,g,o in planes])
print('Minimums:',json.dumps(summary,indent=2))
print('Primary/GND distances under8mm:',len(out['primary_GND_under_8mm']))
print('Primary/outer conservative bound under8mm:',len(out['primary_outer_bound_under_8mm']))
print('Keepout comparisons/overlaps:',len(keepouts),len(out['keepout_overlap_above_0p0001_mm2']))
