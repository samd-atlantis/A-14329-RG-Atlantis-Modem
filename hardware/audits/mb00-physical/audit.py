"""Reproduce MB00 physical cross-check from the frozen native ZIP.

Run using portable KiCad's Python, which provides pcbnew. This is an audit-only
translation; it deliberately does NOT generate fabrication data or ground pours.
"""
from pathlib import Path
import collections, hashlib, json, math, sys, zipfile
import pcbnew as k

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SOURCE = ROOT / 'hardware/releases/A-14329-MB00/pcb-assembly49.epro2'
MM = .0254
docs = []
with zipfile.ZipFile(SOURCE) as z:
    for name in z.namelist():
        if not name.endswith('.epru'): continue
        head, rows = None, {}
        for line in z.read(name).decode('utf-8-sig').splitlines():
            if not line: continue
            if line.endswith('|'): line = line[:-1]
            h, b = line.split('||', 1)
            h, b = json.loads(h), json.loads(b) if b else None
            if h['type'] == 'DOCHEAD':
                if head: docs.append({'head': head, 'records': [r for r in rows.values() if r['b'] is not None]})
                head, rows = {'h': h, 'b': b}, {}
            else: rows[h['id']] = {'h': h, 'b': b}
        if head: docs.append({'head': head, 'records': [r for r in rows.values() if r['b'] is not None]})
pcb = next(d['records'] for d in docs if d['head']['b']['docType'] == 'PCB')
fps = {d['head']['b']['uuid']: d['records'] for d in docs if d['head']['b']['docType'] == 'FOOTPRINT'}
attrs = {(r['b']['parentId'], r['b']['key']): r['b']['value'] for r in pcb if r['h']['type'] == 'ATTR'}
pn = {}
for r in pcb:
    if r['h']['type'] == 'PAD_NET':
        key = json.loads(r['h']['id']); pn[key[1], key[3]] = r['b']['padNet']
board = k.BOARD(); board.SetCopperLayerCount(4)
layers = {1: k.F_Cu, 15: k.In1_Cu, 16: k.In2_Cu, 2: k.B_Cu}
netnames = sorted(set(pn.values()) | {r['b'].get('netName', '') for r in pcb if r['h']['type'] in ('LINE', 'PAD', 'VIA')})
nets = {}
for name in netnames:
    if name:
        n = k.NETINFO_ITEM(board, name); board.Add(n); nets[name] = n
def v(x, y): return k.VECTOR2I(k.FromMM(x * MM), k.FromMM(-y * MM))
def size(x, y): return k.VECTOR2I(k.FromMM(x * MM), k.FromMM(y * MM))
def layer_set(ids):
    ls = k.LSET()
    for i in ids: ls.AddLayer(i)
    return ls
manifest = {'source': str(SOURCE.relative_to(ROOT)), 'sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'kicad': k.Version(), 'native_counts': dict(collections.Counter(r['h']['type'] for r in pcb)), 'limits': ['Audit copy only; never fabricate this translation.', 'Native ground pours/filled copper, keepouts, silkscreen, mask/paste rules, courtyards and 3D are NOT translated.', 'No schematic parity/ERC implied by this PCB cross-check.', 'Connectivity results involving GND_ISO must be read with omitted-pour limitation.'], 'components': [], 'pads': [], 'holes': []}
def newfp(ref, x=0, y=0):
    f = k.FOOTPRINT(board); f.SetReference(ref); f.SetValue('AUDIT_ONLY'); f.SetPosition(v(x, y)); f.Reference().SetVisible(False); f.Value().SetVisible(False); board.Add(f); return f
def addpad(f, b, ref, rid, net, cx, cy, angle):
    p = k.PAD(f); p.SetNumber(str(b['num'])); p.SetPosition(v(cx, cy)); p.SetOrientation(k.EDA_ANGLE(angle, k.DEGREES_T))
    sh = b['defaultPad']; p.SetSize(size(sh['width'], sh['height']))
    shapes = {'RECT': k.PAD_SHAPE_RECT, 'OVAL': k.PAD_SHAPE_OVAL, 'ELLIPSE': k.PAD_SHAPE_CIRCLE}
    assert sh['padType'] != 'ELLIPSE' or abs(sh['width']-sh['height']) < .001, ('Non-circular ellipse', rid)
    p.SetShape(shapes[sh['padType']]); hole = b.get('hole')
    if hole and hole['width'] > 0 and hole['height'] > 0:
        p.SetAttribute(k.PAD_ATTRIB_PTH if b.get('plated') else k.PAD_ATTRIB_NPTH)
        hw, hh = hole['width'], hole['height']
        ha = b.get('relativeAngle') or 0
        assert ha % 90 == 0, ('Unsupported relative drill angle', rid, ha)
        if ha % 180: hw, hh = hh, hw
        p.SetDrillSize(size(hw, hh))
        p.SetDrillShape(k.PAD_DRILL_SHAPE_CIRCLE if hole['holeType'] == 'ROUND' else k.PAD_DRILL_SHAPE_OBLONG)
        p.SetLayerSet(layer_set([k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu,k.F_Mask,k.B_Mask]))
    else:
        p.SetAttribute(k.PAD_ATTRIB_SMD); p.SetLayerSet(layer_set([layers[b['layerId']], k.F_Mask if b['layerId'] == 1 else k.B_Mask]))
    if net: p.SetNet(nets[net])
    f.Add(p)
    manifest['pads'].append({'ref':ref, 'pin':str(b['num']), 'source_id':rid,'net':net,'x_mm':cx*MM,'y_mm':cy*MM,'width_mm':sh['width']*MM,'height_mm':sh['height']*MM,'angle':angle,'layer':b['layerId'],'hole':hole})
def addhole(ref, x, y, radius):
    f=newfp(ref); p=k.PAD(f); p.SetNumber(''); p.SetAttribute(k.PAD_ATTRIB_NPTH); p.SetShape(k.PAD_SHAPE_CIRCLE); p.SetPosition(v(x,y)); p.SetSize(size(2*radius,2*radius)); p.SetDrillSize(size(2*radius,2*radius)); p.SetLayerSet(layer_set([k.F_Cu,k.B_Cu,k.F_Mask,k.B_Mask])); f.Add(p)
    manifest['holes'].append({'ref':ref,'x_mm':x*MM,'y_mm':y*MM,'diameter_mm':2*radius*MM})
for r in pcb:
    if r['h']['type']!='COMPONENT': continue
    c=r['b']; cid=r['h']['id']; ref=attrs.get((cid,'Designator'),cid); fp=attrs.get((cid,'Footprint'))
    assert c['layerId']==1, 'Bottom component not supported'
    assert fp in fps, ('Missing footprint',ref,fp)
    f=newfp(ref,c['x'],c['y']); co,si=math.cos(math.radians(c['angle'])), math.sin(math.radians(c['angle']))
    manifest['components'].append({'ref':ref,'footprint':fp,'x_mm':c['x']*MM,'y_mm':c['y']*MM,'angle':c['angle']})
    for q in fps[fp]:
        b=q['b']
        if q['h']['type']=='PAD':
            x,y=b['centerX'],b['centerY']; addpad(f,b,ref,q['h']['id'],pn.get((cid,q['h']['id']),''),c['x']+co*x-si*y,c['y']+si*x+co*y,c['angle']+b.get('padAngle',0))
        elif q['h']['type']=='FILL' and b.get('layerId')==12:
            paths=b['path']; paths=[paths] if isinstance(paths[0],str) else paths
            for path in paths:
                assert path[0]=='CIRCLE'; _,x,y,rad=path; addhole(ref+'.'+q['h']['id'],c['x']+co*x-si*y,c['y']+si*x+co*y,rad)
standalone=newfp('TEST_PADS')
for r in pcb:
    b=r['b']; t=r['h']['type']; rid=r['h']['id']
    if t=='PAD': addpad(standalone,b,'TEST_PADS',rid,b['netName'],b['centerX'],b['centerY'],b.get('padAngle',0))
    elif t=='LINE' and b['layerId'] in layers:
        track=k.PCB_TRACK(board); track.SetStart(v(b['startX'],b['startY'])); track.SetEnd(v(b['endX'],b['endY'])); track.SetWidth(k.FromMM(b['width']*MM)); track.SetLayer(layers[b['layerId']]);
        if b.get('netName'): track.SetNet(nets[b['netName']])
        board.Add(track)
    elif t=='VIA':
        via=k.PCB_VIA(board); via.SetPosition(v(b['centerX'],b['centerY'])); via.SetWidth(k.FromMM(b['viaDiameter']*MM)); via.SetDrill(k.FromMM(b['holeDiameter']*MM)); via.SetViaType(k.VIATYPE_THROUGH); via.SetLayerPair(k.F_Cu,k.B_Cu); via.SetNet(nets[b['netName']]); board.Add(via)
    elif t=='FILL' and b['layerId']==12:
        for path in b['path']:
            assert path[0]=='CIRCLE'; addhole(rid,*path[1:])
    elif t=='POLY' and b['layerId']==11:
        assert b['polyType']=='BOARD_OUTLINE'
        p=b['path']; assert p[2]=='L'; points=[p[:2]]+[p[i:i+2] for i in range(3,len(p),2)]
        manifest['outline_mm']=[[x*MM,y*MM] for x,y in points]
        for a,z in zip(points,points[1:]):
            s=k.PCB_SHAPE(board); s.SetShape(k.SHAPE_T_SEGMENT); s.SetStart(v(*a)); s.SetEnd(v(*z)); s.SetWidth(k.FromMM(.1)); s.SetLayer(k.Edge_Cuts); board.Add(s)
    elif t=='POLY' and b['layerId'] in layers:
        assert b['path'][0]=='CIRCLE'; _,x,y,rad=b['path']; s=k.PCB_SHAPE(board); s.SetShape(k.SHAPE_T_CIRCLE); s.SetCenter(v(x,y)); s.SetEnd(v(x+rad,y)); s.SetWidth(k.FromMM(b['width']*MM)); s.SetLayer(layers[b['layerId']]); board.Add(s)
k.SaveBoard(str(OUT/'mb00-audit-only.kicad_pcb'),board)
project={'meta':{'filename':'mb00-audit-only.kicad_pro','version':1},'board':{'design_settings':{'rules':{'min_clearance':.15,'min_track_width':.15,'min_via_diameter':.6,'min_through_hole_diameter':.3,'min_hole_to_hole':.3,'min_copper_edge_clearance':.5,'min_via_annular_width':.1},'rule_severities':{'lib_footprint_issues':'ignore','lib_footprint_mismatch':'ignore','missing_courtyard':'ignore','silk_over_copper':'ignore','silk_overlap':'ignore','solder_mask_bridge':'ignore'}}},'net_settings':{'classes':[{'name':'Default','clearance':.15,'track_width':.2,'via_diameter':.6,'via_drill':.3}]}}
(OUT/'mb00-audit-only.kicad_pro').write_text(json.dumps(project,indent=2))
(OUT/'mb00-audit-only.kicad_dru').write_text('''(version 1)
(rule "native signal floor incl differential pairs, 1um conversion tolerance"
 (constraint clearance (min 0.149mm))
 (constraint hole_clearance (min 0.199mm))
 (constraint hole_to_hole (min 0.299mm))
 (constraint via_diameter (min 0.599mm))
 (constraint hole_size (min 0.299mm))
 (constraint annular_width (min 0.099mm)))
(rule "primary to primary or PE 3.2mm source rule"
 (condition "(A.NetName == 'AC_L_IN' || A.NetName == 'AC_L_FUSED' || A.NetName == 'AC_N') && (B.NetName == 'AC_L_IN' || B.NetName == 'AC_L_FUSED' || B.NetName == 'AC_N' || B.NetName == 'CHASSIS_PE')")
 (constraint clearance (min 3.199mm)))
(rule "primary to secondary 8mm source rule"
 (condition "(A.NetName == 'AC_L_IN' || A.NetName == 'AC_L_FUSED' || A.NetName == 'AC_N') && B.NetName != '' && B.NetName != 'AC_L_IN' && B.NetName != 'AC_L_FUSED' && B.NetName != 'AC_N' && B.NetName != 'CHASSIS_PE'")
 (constraint clearance (min 7.999mm)))
''')
(OUT/'conversion-manifest.json').write_text(json.dumps(manifest,indent=2))
print('Converted',len(manifest['components']),'components,',len(manifest['pads']),'pads,',len(manifest['holes']),'NPTH holes. GND pours deliberately omitted.')
