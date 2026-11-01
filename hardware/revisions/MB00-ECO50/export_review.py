"""Export candidate purchasing files and scaled native-CAD review images."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'hardware/easyeda'))
sys.path.insert(0,str(ROOT/'.tools/commission-deps'))
from route_geometry import load
from PIL import Image, ImageDraw, ImageFont

def main():
    # CAD runtimes write Windows newlines; keep new review evidence portable.
    for path in (HERE/'kicad-audit').glob('*.json'):
        path.write_text(path.read_text(encoding='utf8'),encoding='utf8',newline='\n')
    docs=json.loads((HERE/'pcb-eco50-docs.json').read_text(encoding='utf8'))
    rows,pads=load(str(HERE/'pcb-eco50-docs.json'))
    at={(r['b']['parentId'],r['b']['key']):r['b']['value'] for r in rows if r['h']['type']=='ATTR'}
    devices={d['head']['b']['uuid']:next(r['b'] for r in d['records'] if r['h']['type']=='META') for d in docs if d['head']['b']['docType']=='DEVICE'}
    components={at[r['h']['id'],'Designator']:r for r in rows if r['h']['type']=='COMPONENT'}
    source=ROOT/'hardware/releases/A-14329-MB00'
    with (source/'A14329_BOM.csv').open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;bom=list(reader)
    # Preserve the original assembly exclusions, including U20 and MODEM1.
    refkey=next(k for k in fields if 'designator' in k.lower())
    entries=[]
    for row in bom:
        remain=[r.strip() for r in row[refkey].split(',') if r.strip() not in ['C22','C25','L2']]
        if remain:row[refkey]=','.join(remain);entries.append(row)
    changed={'C22':('CL10B223KB8NNNC','C0603','C21122'),'C25':('MA10V470M6X8','CAP-POLY-MA-D6.3-L7.7','C46550459'),'L2':('MWSA0503S-1R0MT','IND-MWSA0503S-5.4x5.2','C408355')}
    for ref,(part,fp,sku) in changed.items():
        # The frozen export schema is Comment, Designator, Footprint, LCSC Part #.
        entries.append(dict(zip(fields,[part,ref,fp,sku])))
    with (HERE/'ENGINEERING-BOM.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n',quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(entries)
    with (source/'A14329_CPL.csv').open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f);cf=reader.fieldnames;cpl=list(reader)
    for row in cpl:
        ref=row[cf[0]]
        if ref in ['U19','C25','C61']:
            b=components[ref]['b'];row[cf[1]]=f"{b['x']*.0254:.6f}".rstrip('0').rstrip('.');row[cf[2]]=f"{b['y']*.0254:.6f}".rstrip('0').rstrip('.');row[cf[4]]=str(b['angle']%360)
    with (HERE/'ENGINEERING-CPL.csv').open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=cf,lineterminator='\n',quoting=csv.QUOTE_ALL);w.writeheader();w.writerows(cpl)
    bref={r.strip() for row in entries for r in row[refkey].split(',')}
    assert bref=={row[cf[0]] for row in cpl} and len(bref)==101
    fps={d['head']['b']['uuid']:d['records'] for d in docs if d['head']['b']['docType']=='FOOTPRINT'}
    try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
    except OSError:font=small=ImageFont.load_default()
    def render(bounds,filename,title,highlight):
        x0,y0,x1,y1=bounds;scale=min(1200/(x1-x0),1000/(y1-y0));W=int((x1-x0)*scale)+80;H=int((y1-y0)*scale)+135
        im=Image.new('RGB',(W,H),'#101b25');g=ImageDraw.Draw(im)
        def pt(x,y):return (40+(x-x0)*scale,85+(y1-y)*scale)
        g.text((28,18),title,font=font,fill='white');g.text((28,47),'ECO50 engineering candidate | no filled planes shown | NOT FOR FABRICATION',font=small,fill='#ffcb60')
        for r in rows:
            b=r['b']
            if r['h']['type']=='LINE' and b['layerId'] in [1,2,15,16]:
                if min(b['startX'],b['endX'])>x1 or max(b['startX'],b['endX'])<x0 or min(b['startY'],b['endY'])>y1 or max(b['startY'],b['endY'])<y0:continue
                if not(x0<=b['startX']<=x1 and x0<=b['endX']<=x1 and y0<=b['startY']<=y1 and y0<=b['endY']<=y1):continue
                color={1:'#a94343',2:'#364d9b',15:'#405953',16:'#4d474d'}[b['layerId']]
                g.line([pt(b['startX'],b['startY']),pt(b['endX'],b['endY'])],fill=color,width=max(1,int(b['width']*scale)))
            if r['h']['type']=='VIA' and x0<=b['centerX']<=x1 and y0<=b['centerY']<=y1:
                x,y=pt(b['centerX'],b['centerY']);rad=b['viaDiameter']*scale/2;g.ellipse((x-rad,y-rad,x+rad,y+rad),outline='#79b5b0',width=2)
        for ref,r in components.items():
            c=r['b'];x,y=c['x'],c['y']
            if not(x0<x<x1 and y0<y<y1):continue
            rad=math.radians(c['angle']);co,si=math.cos(rad),math.sin(rad)
            for q in fps.get(at[r['h']['id'],'Footprint'],[]):
                b=q['b']
                if q['h']['type']=='POLY' and b.get('layerId')==48 and b['path'][0]!='CIRCLE':
                    nums=[v for v in b['path'] if not isinstance(v,str)];coords=[pt(x+co*xx-si*yy,y+si*xx+co*yy) for xx,yy in zip(nums[::2],nums[1::2])]
                    g.polygon(coords,outline='#ffce62' if ref in highlight else '#5f8e85',width=3 if ref in highlight else 1)
            xx,yy=pt(x,y);g.text((xx+6,yy+6),ref,font=font if ref in highlight else small,fill='#ffffff' if ref in highlight else '#b1b6bb')
        for p in pads:
            if not(x0<p['x']<x1 and y0<p['y']<y1):continue
            a=pt(p['x']-p['w']/2,p['y']+p['h']/2);b=pt(p['x']+p['w']/2,p['y']-p['h']/2)
            g.rectangle((*a,*b),fill='#a8b7c4',outline='#ffffff' if p['ref'] in highlight else None)
            if p['ref']=='C25':g.text((a[0]+4,a[1]+4),'+' if p['pin']=='1' else '-',font=font,fill='#101b25')
        im.save(HERE/filename)
    render((3300,70,3870,800),'usb-layout-review.png','USB console: U19 relocated; protection retained',{'U19','U16','J14'})
    render((4350,1070,4840,1910),'modem-capacitor-review.png','Modem rail: C25 470 uF; C61 moved for clearance',{'C25','C61','SW4','SW5'})
    checks=json.loads((HERE/'geometry-checks.json').read_text())
    drc=json.loads((HERE/'kicad-audit/kicad-drc.json').read_text())
    errors=[v for v in drc['violations'] if v.get('severity')=='error']
    checks['kicad_copper_short_clearance_drill_errors']=errors
    checks['kicad_warning_counts']=dict(collections.Counter(v['type'] for v in drc['violations']))
    checks['kicad_unconnected_items']={'count':len(drc['unconnected_items']),'nets':sorted({desc['description'].split(']')[0].split('[')[-1] for r in drc['unconnected_items'] for desc in r['items']})}
    checks['assembly_pair_designators']=len(bref)
    (HERE/'review-summary.json').write_text(json.dumps(checks,indent=2)+'\n',encoding='utf8',newline='\n')
    names=['pcb-before-eco50.epro2','pcb-eco50-engineering.epro2','schematic-eco50-engineering.epro2','ENGINEERING-BOM.csv','ENGINEERING-CPL.csv','README.txt','validation.json','geometry-checks.json','planned-plane-envelope.json','review-summary.json','kicad-audit/conversion-manifest.json','kicad-audit/kicad-drc.json']
    manifest={'revision':'MB00-ECO50','status':'ENGINEERING_CANDIDATE_NOT_FOR_FABRICATION','cloud_imported':False,'native_ERC_DRC_passed':False,'power_bench_tested':False,'ordered_hardware_release_changed':False,'files':[dict(file=n,bytes=(HERE/n).stat().st_size,sha256=hashlib.sha256((HERE/n).read_bytes()).hexdigest()) for n in names]}
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8',newline='\n')
    print('BOM/CPL:',len(bref),'matched designators; KiCad copper errors:',len(errors))

if __name__=='__main__':main()
