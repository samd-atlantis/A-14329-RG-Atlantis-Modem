"""Reproducible engineering revision; never rewrites the ordered MB00 release.

The new output-filter population is a bench candidate, not a stability signoff.
Use with the component drawings and README.txt in this directory.
"""
from pathlib import Path
import collections
import copy
import csv
import hashlib
import json
import math
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "hardware/audits/mb00-electrical"))
from audit import extract, attrs, schematic, pcb as pin_map, critical_expectations
sys.path.insert(0, str(ROOT / "hardware/easyeda"))
from route_geometry import load
from check_route_fragment import check

def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

def json_file(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n", encoding="utf8", newline="\n")

def docs_from(path):
    # Preserve the native document headers/tickets as well as final records.
    docs=[]
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith('.epru'):continue
            head=None;records={}
            for line in z.read(name).decode('utf-8-sig').splitlines():
                if not line:continue
                hs,bs=line.removesuffix('|').split('||',1)
                h=json.loads(hs);b=json.loads(bs) if bs else None
                if h['type']=='DOCHEAD':
                    if head:docs.append({'head':head,'records':[r for r in records.values() if r['b'] is not None]})
                    head={'h':h,'b':b};records={}
                else:records[h['id']]={'h':h,'b':b}
            if head:docs.append({'head':head,'records':[r for r in records.values() if r['b'] is not None]})
    return docs

def write_native(source, target, docs, title):
    content = "\n".join(compact(r["h"])+"||"+compact(r["b"])+"|"
                        for d in docs for r in [d["head"], *d["records"]])
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.filename.endswith(".epru"):
                zout.writestr(info,content.encode("utf8"))
            elif info.filename=="project2.json":
                p=json.loads(zin.read(info.filename));p["title"]=title
                zout.writestr(info,compact(p).encode("utf8"))
            else:zout.writestr(info,zin.read(info.filename))

def main():
    source=HERE/"pcb-before-eco50.epro2"
    schsource=ROOT/"hardware/releases/A-14329-MB00/schematic-assembly49.epro2"
    docs=docs_from(source)
    json_file(HERE/'before-docs.json',docs)
    pd=next(d for d in docs if d["head"]["b"]["docType"]=="PCB")
    rows=pd["records"]; original=copy.deepcopy(rows)
    next(r['b'] for r in rows if r['h']['type']=='META')['title']='PCB1-ECO50-ENGINEERING'
    att=attrs(rows)
    comps={att[r["h"]["id"],"Designator"]:r for r in rows if r["h"]["type"]=="COMPONENT"}
    ticket=max(r["h"].get("ticket",0) for r in rows)+1000
    added=[]
    def rec(kind, body, rid=None):
        nonlocal ticket
        ticket+=1
        r={"h":{"type":kind,"id":rid or f"ec503110{ticket:08x}","ticket":ticket},"b":body}
        added.append(r);return r
    def line(net, layer, points, width):
        for a,b in zip(points,points[1:]):
            rec("LINE",dict(partitionId="",groupId=0,netName=net,layerId=layer,startX=a[0],startY=a[1],endX=b[0],endY=b[1],width=width,locked=False,zIndex=-1))
    def via(net,x,y):
        b=copy.deepcopy(next(r["b"] for r in rows if r["h"]["type"]=="VIA"))
        b.update(netName=net,centerX=x,centerY=y,viaDiameter=23.622,holeDiameter=11.811)
        rec("VIA",b)
    def change_attr(ref,key,value):
        next(r["b"] for r in rows if r["h"]["type"]=="ATTR" and r["b"]["parentId"]==comps[ref]["h"]["id"] and r["b"]["key"]==key)["value"]=value

    # Retain the protection device; move it out of the CH340C body envelope.
    assert comps["U19"]["b"]["x"]==3600 and comps["U19"]["b"]["y"]==325
    comps["U19"]["b"].update(x=3500,y=285)
    label=next(r["b"] for r in rows if r["h"]["type"]=="ATTR" and r["b"].get("parentId")==comps["U19"]["h"]["id"] and r["b"]["key"]=="Designator")
    label.update(x=3425,y=380,angle=0)
    # Original two USB junctions and the working signal path are retained.
    # Only new ESD shunt branches are added; remove obsolete ESD ground stub/via.
    remove={"conse0133356ea398f66","cons0920a95be9abd25b","458618fd5813397f",
            "22c149ac8d3cd2c1","14a47d27125b276f","e6217bd13e60a2ee",
            "gndstitch_C61","d78d04f2434c51f3","6199149f3c980b98"}
    line("USB_CONSOLE_DP",1,[(3519.685,271.22),(3535,271.22),(3565,301.22),(3585,311.22),(3619.685,311.22)],9.74)
    line("USB_CONSOLE_DM",1,[(3519.685,298.78),(3550,329.095),(3619.685,338.78)],9.74)
    line("GND_ISO",1,[(3480.315,285),(3470,285)],9.74)
    via("GND_ISO",3470,285)
    via("GND_ISO",3540,214.055)
    line("CONSOLE_TX",1,[(3689.1519,464.0188),(3605.1331,380),(3470,380),(3470,338.6832),(3482.4594,326.2238)],9.8425)

    # More manufacturing margin around the primary domain. The nominal minimum
    # remains 8 mm for existing signal copper; ground fills have a 9 mm selector.
    for primary in ["AC_L_IN","AC_L_FUSED","AC_N"]:
        rec("RULE_SELECTOR",{"ruleOrder":3,"ruleKeyValue":{"SAFE":"PRIMARY_GROUND_9MM"},"copperValue":{"COPPER":None},"innerPlaneValue":{"PLANE":None}},compact(["RULE_SELECTOR",[["NET",primary],["NET","GND_ISO"]]]))
    rule=copy.deepcopy(next(r["b"] for r in rows if r["h"]["id"]=='["RULE","SAFE","PRIMARY_SECONDARY_8MM"]'))
    for spacing in rule["ruleContext"]["safeSpacing"]:
        spacing["content"]=[[9/.0254 for _ in row] for row in spacing["content"]]
    rec("RULE",rule,'["RULE","SAFE","PRIMARY_GROUND_9MM"]')
    # Move the horizontal plane boundary near AC_N up by 1.27 mm. This changes
    # no primary conductors and preserves the lower and upper ground lobes.
    for r in rows:
        if r["h"]["type"]=="POUR":
            p=r["b"]["path"][0]
            for i in range(0,len(p)-1):
                if p[i]==1700 and p[i+1]==1500:p[i+1]=1550
                if p[i]==3350 and p[i+1]==1500:p[i+1]=1550

    # Exact replacement parts have local device/footprint documents, leaving
    # shared router-regulator L1/C12 and all other ceramic capacitors unchanged.
    doc_by_id={d["head"]["b"]["uuid"]:d for d in docs}
    def new_device(ref,uid,updates,fp=None):
        old=doc_by_id[att[comps[ref]["h"]["id"],"Device"]]
        d=copy.deepcopy(old);d["head"]["b"]["uuid"]=uid;d["head"]["b"]["user"]={"uuid":uid}
        meta=next(r["b"] for r in d["records"] if r["h"]["type"]=="META")
        meta["title"]=updates["Manufacturer Part"];meta.pop("images",None);meta["source"]=""
        da=meta["attributes"]
        for k in list(da):
            if k.startswith("3D Model") or k in ["LCSC Part Name","Description","Rated Current","Temperature Coefficient","Type","Polarity","Current - Saturation(Isat)","Current Rating","DC Resistance(DCR)"]:da.pop(k)
        da.update(updates)
        if fp:da["Footprint"]=fp
        da["ECO Status"]="ENGINEERING CANDIDATE - POWER BENCH VALIDATION REQUIRED"
        docs.append(d);change_attr(ref,"Device",uid)
        comps[ref]["b"]["attrs"].update({k:v for k,v in updates.items() if k in ["Value","Manufacturer Part","Supplier Part"]})
        return da
    def footprint(ref,uid,title,body_path,pad_positions,pad_sizes,polarity=False):
        # Copy only an existing pad record's schema, not its dimensions.
        fpold=doc_by_id[att[comps[ref]["h"]["id"],"Footprint"]]
        d=copy.deepcopy(fpold);d["head"]["b"]["uuid"]=uid;d["head"]["b"]["user"]={"uuid":uid}
        pads=[copy.deepcopy(r) for r in fpold["records"] if r["h"]["type"]=="PAD"]
        for pad in pads:
            n=pad["b"]["num"];pad["b"].update(centerX=pad_positions[n][0]/.0254,centerY=pad_positions[n][1]/.0254,padAngle=0,padOffsetX=0,padOffsetY=0,relativeAngle=0)
            # Explicit stencil openings; never inherit a DNP/hand-solder -100mm mask.
            if polarity:pad["b"].update(topPasteExpansion=-2,bottomPasteExpansion=-2)
            pad["b"]["defaultPad"].update(padType="RECT",width=pad_sizes[0]/.0254,height=pad_sizes[1]/.0254)
        meta=copy.deepcopy(next(r for r in fpold["records"] if r["h"]["type"]=="META"));meta["b"].update(title=title,source="",description="ECO50 locally authored from saved manufacturer drawing; native DFM review required")
        for k in list(meta["b"].get("attributes",{})):
            if k.startswith("3D Model"):meta["b"]["attributes"].pop(k)
        d["records"]=[meta,*pads]
        path=[]
        for x,y in body_path:
            if len(path)==2:path.append("L")
            path.extend([x/.0254,y/.0254])
        d["records"].append({"h":{"type":"POLY","id":"eco50shape48","ticket":138},"b":dict(groupId=0,netName="",layerId=48,width=2,path=path,locked=False,zIndex=138,polyType="NORMAL")})
        # Break the side outlines around solder lands; do not draw silkscreen
        # through the longer capacitor or smaller inductor terminal pads.
        sx=(max(abs(x) for x,y in body_path)+.15)/.0254
        sy=(max(abs(y) for x,y in body_path)+.15)/.0254
        gap=(pad_sizes[1]/2+.3)/.0254
        for i,sign in enumerate([1,-1]):
            silk=[-sx,sign*gap,'L',-sx,sign*sy,sx,sign*sy,sx,sign*gap]
            d['records'].append({'h':{'type':'POLY','id':f'eco50silk{i}','ticket':140+i},'b':dict(groupId=0,netName='',layerId=3,width=5,path=silk,locked=False,zIndex=140+i,polyType='NORMAL')})
        if polarity:
            d["records"].append({"h":{"type":"POLY","id":"eco50plusH","ticket":150},"b":dict(groupId=0,netName="",layerId=3,width=6,path=[-190,75,"L",-165,75],locked=False,zIndex=150,polyType="NORMAL")})
            d["records"].append({"h":{"type":"POLY","id":"eco50plusV","ticket":151},"b":dict(groupId=0,netName="",layerId=3,width=6,path=[-177.5,62.5,"L",-177.5,87.5],locked=False,zIndex=151,polyType="NORMAL")})
        docs.append(d);change_attr(ref,"Footprint",uid)
        return uid

    lfp=footprint("L2","ec50311000000001","IND-MWSA0503S-5.4x5.2",[(-2.7,-2.6),(-2.7,2.6),(2.7,2.6),(2.7,-2.6),(-2.7,-2.6)],{"1":(2.05,0),"2":(-2.05,0)},(1.9,2.5))
    new_device("L2","ec50311000000002",{"Manufacturer":"Sunlord","Manufacturer Part":"MWSA0503S-1R0MT","Supplier Part":"C408355","Supplier":"LCSC","Value":"1uH","Tolerance":"+/-20%","Current Rating":"Manufacturer table: 7.8A Max / 8.5A Typ","Current - Saturation(Isat)":"Manufacturer table: 8A Max / 10A Typ","DC Resistance(DCR)":"14mOhm max","Supplier Footprint":"SMD,5.4x5.2mm","Datasheet":"https://atta.szlcsc.com/upload/public/pdf/source/20231024/D9DB0CBBB5804BFBC9233D4A02F4216A.pdf"},lfp)
    new_device("C22","ec50311000000003",{"Manufacturer":"Samsung Electro-Mechanics","Manufacturer Part":"CL10B223KB8NNNC","Supplier Part":"C21122","Supplier":"LCSC","Value":"22nF","Tolerance":"+/-10%","Voltage Rating":"50V","Temperature Coefficient":"X7R","JLCPCB Part Class":"Basic Part","Datasheet":"https://jlcpcb.com/partdetail/21834-CL10B223KB8NNNC/C21122"})
    # MA package bottom view: A/B=6.6 +/-0.2, lead width 0.5..0.9,
    # inner terminal gap P=2.1 +/-0.2 mm. Authored lands extend 0.6 mm past
    # the maximum 6.8 mm base; inner land gap 1.8 mm accommodates tolerances.
    cfp=footprint("C25","ec50311000000004","CAP-POLY-MA-D6.3-L7.7",[(-3.4,-3.4),(-3.4,3.4),(3.4,3.4),(3.4,-3.4),(-3.4,-3.4)],{"1":(-2.45,0),"2":(2.45,0)},(3.1,1.6),True)
    c25da=new_device("C25","ec50311000000005",{"Manufacturer":"JIERR","Manufacturer Part":"MA10V470M6X8","Supplier Part":"C46550459","Supplier":"LCSC","Value":"470uF","Tolerance":"+/-20%","Voltage Rating":"10V","Type":"Polymer","Polarity":"Polarized; pin 1 positive","ESR":"20mOhm @100kHz","Ripple Current":"3.1A @100kHz","Height":"7.7mm nominal; allow 8.5mm","Supplier Footprint":"SMD,D6.3xL7.7mm","Datasheet":"https://atta.szlcsc.com/upload/public/pdf/source/20260306/24758A4FC016E80367B87853635CDCC1.pdf"},cfp)
    # A separate polarized symbol avoids changing the shared C24 symbol.
    cap_symbol=next(copy.deepcopy(d) for d in docs_from(schsource) if d['head']['b']['docType']=='SYMBOL' and d['head']['b']['uuid']==c25da['Symbol'])
    cap_symbol['head']['b']['uuid']='ec50311000000006'
    cap_symbol['head']['b']['user']={'uuid':'ec50311000000006'}
    oldpart=next(r['h']['id'] for r in cap_symbol['records'] if r['h']['type']=='PART')
    newpart='MA10V470M6X8.1'
    for r in cap_symbol['records']:
        if r['b'].get('partId')==oldpart:r['b']['partId']=newpart
        if r['h']['type']=='PART':r['h']['id']=newpart;r['b'].update(title=newpart,BBOX=[-18,-18,18,18])
        if r['h']['type']=='META':r['b'].update(title='MA10V470M6X8_POLARIZED',source='',description='Positive pin 1; negative pin 2')
    pt=next(r for r in cap_symbol['records'] if r['h']['type']=='POLY')
    for i,points in enumerate([[{'x':-15,'y':13},{'x':-7,'y':13}],[{'x':-11,'y':9},{'x':-11,'y':17}]]):
        q=copy.deepcopy(pt);q['h'].update(id=f'eco50positive{i}',ticket=200+i);q['b'].update(points=points,zIndex=200+i);cap_symbol['records'].append(q)
    docs.append(cap_symbol);c25da['Symbol']='ec50311000000006'
    # Keep the long positive land clear of SW4's grounded switch terminal.
    c25oldy=comps["C25"]["b"]["y"];comps["C25"]["b"]["y"]=1405
    for r in rows:
        if r["h"]["type"]=="ATTR" and r["b"].get("parentId")==comps["C25"]["h"]["id"] and r["b"].get("x") is not None:r["b"]["y"]+=1405-c25oldy
    line("GND_ISO",1,[(4685.0394,c25oldy+59.74),(4685.0394,1435+2.45/.0254)],20)
    # Clear the larger C25 terminal lands. Move the adjacent 1uF bypass and
    # reconnect its positive branch, with a short new ground via.
    c61=comps["C61"];oldy=c61["b"]["y"];newy=1660;c61["b"]["y"]=newy
    cid=c61["h"]["id"]
    for r in rows:
        if r["h"]["type"]=="ATTR" and r["b"].get("parentId")==cid and r["b"].get("x") is not None:r["b"]["y"]+=newy-oldy
    # Route edit is based on actual pad endpoints extracted below, not guessed
    # capacitor pin numbering or a value-only footprint substitution.
    removed_ground=[]
    beforepath=HERE/"before-docs.json"
    _,oldpads=load(str(beforepath))
    old61={p["pin"]:p for p in oldpads if p["ref"]=="C61"}
    dy=newy-oldy
    for r in rows:
        if r["h"]["type"]!="LINE":continue
        b=r["b"]
        for pin,p in old61.items():
            for stem in ["start","end"]:
                if math.dist((b[stem+"X"],b[stem+"Y"]),(p["x"],p["y"]))<.02:
                    if p["net"]=="GND_ISO":remove.add(r["h"]["id"]);removed_ground.append(r["h"]["id"])
                    else:b[stem+"Y"]+=dy
    gp=next(p for p in old61.values() if p["net"]=="GND_ISO")
    line("GND_ISO",1,[(gp["x"],gp["y"]+dy),(4650,gp["y"]+dy)],12)
    via("GND_ISO",4650,gp["y"]+dy)
    for ref,x,y in [('C25',4740,1565),('C61',4740,1700)]:
        label=next(r['b'] for r in rows if r['h']['type']=='ATTR' and r['b'].get('parentId')==comps[ref]['h']['id'] and r['b']['key']=='Designator')
        label.update(x=x,y=y,angle=0)

    # Native-reviewed C61 ground branch, including the obstacle-avoiding bends.
    for r in json.loads((HERE/"native-ground-route.json").read_text()):
        rec("LINE",r["b"],r["h"]["id"])

    # No stale filled copper may be mistaken for a rebuilt plane.
    rows[:]=[r for r in rows if r["h"]["id"] not in remove and r["h"]["type"]!="POURED"]+added
    for r in rows:
        if r["h"]["type"]=="STRING" and r["b"].get("text")=="A-14329-MB00":r["b"]["text"]="A-14329-MB00 ECO50"
    note=copy.deepcopy(next(r["b"] for r in rows if r["h"]["type"]=="STRING"))
    note.update(layerId=14,x=5000,y=3300,text="ECO50 ENGINEERING - NOT FOR FABRICATION\nC25 470uF POLY / L2 1uH / C22 22nF\nPower loop, startup and load-step validation required.\nRebuild ground pours and run native ERC/DRC.",fontSize=45,strokeWidth=5,angle=0,origin="LEFT_BOTTOM")
    rows.append(rec("STRING",note))
    # Retain the PCB UUID so File Source can apply this to its backed-up working
    # document. Frozen releases are read-only inputs to all checks.
    target=HERE/"pcb-eco50-engineering.epro2"
    write_native(source,target,docs,"PCB1-ECO50-ENGINEERING")
    json_file(HERE/"pcb-eco50-docs.json",docs)
    # Raw multi-document source retains the replacement device/footprint docs.
    (HERE/"pcb-eco50.epro-source").write_text("\n".join(compact(r["h"])+"||"+compact(r["b"])+"|" for d in docs for r in [d["head"],*d["records"]]),encoding="utf8",newline="\n")

    # Use the original schematic snapshot plus previously audited Q3 correction.
    sd=docs_from(schsource);sr=next(d["records"] for d in sd if d["head"]["b"]["docType"]=="SCH_PAGE")
    sa=attrs(sr);sc={sa[r["h"]["id"],"Designator"]:r for r in sr if r["h"]["type"]=="COMPONENT" and (r["h"]["id"],"Designator") in sa}
    for r in sr:
        if r["h"]["id"]=="ed2700000000011e":r["b"]["endY"]=-1070
        if r["h"]["id"]=="ed27000000000126":r["b"]["endY"]=-830
        if r["h"]["type"]=="ATTR" and r["b"].get("key")=="NET":
            if r["b"].get("parentId")=="ed2700000000011d":r["b"]["y"]=-1070
            if r["b"].get("parentId")=="ed27000000000125":r["b"]["y"]=-830
    for ref in ["L2","C22","C25"]:
        dev=next(d for d in docs if d["head"]["b"]["uuid"]==attrs(rows)[comps[ref]["h"]["id"],"Device"])
        da=next(r["b"]["attributes"] for r in dev["records"] if r["h"]["type"]=="META")
        for r in sr:
            if r["h"]["type"]=="ATTR" and r["b"].get("parentId")==sc[ref]["h"]["id"]:
                key=r["b"]["key"]
                if key=="Device":r["b"]["value"]=dev["head"]["b"]["uuid"]
                elif key in da and key not in ["Designator","Symbol"]:r["b"]["value"]=da[key]
        sc[ref]["b"]["attrs"].update({k:da[k] for k in ["Value","Supplier Part","Manufacturer Part"]})
        sd.append(copy.deepcopy(dev))
    # C25 uses the same electrical capacitor symbol; explicit '+' pin marking
    # and the polarized value are added without changing its original nets.
    for r in sr:
        if r["h"]["type"]=="ATTR" and r["b"].get("parentId")==sc["C25"]["h"]["id"] and r["b"]["key"]=="Value":r["b"]["value"]="470uF / 10V POLY (+ pin 1)"
        if r["h"]["type"]=="ATTR" and r["b"].get("parentId")==sc["C25"]["h"]["id"] and r["b"]["key"]=="Symbol":r["b"]["value"]='ec50311000000006'
    sc['C25']['b']['partId']=newpart
    sc['C25']['b']['attrs']['Value']='470uF / 10V POLY'
    sd.append(copy.deepcopy(cap_symbol))
    sd.extend(copy.deepcopy(d) for d in docs if d["head"]["b"]["uuid"] in [lfp,cfp])
    notes={"DesignTitle":"A-14329-MB00 ECO50 ENGINEERING | 4-PORT CELLULAR ROUTER", "ModemNotes":"J8: ordered EC25AFFA-MINIPCIE; separately installed. Reserved card pins remain unconnected.", "Review2":"ECO50 TEST: C25 470uF polymer, L2 1uH, C22 22nF. Startup/load-step/stability/thermal and mechanical fit validation required before fabrication release.", "Version":"MB00-ECO50 ENGINEERING - NOT FOR FABRICATION"}
    for r in sr:
        if r['h']['type']=='ATTR' and r['b'].get('key') in notes:r['b']['value']=notes[r['b']['key']]
    schtarget=HERE/"schematic-eco50-engineering.epro2"
    write_native(schsource,schtarget,sd,"Schematic1-ECO50-ENGINEERING")

    # Electrical mappings must remain identical; assess copper separately.
    pp,_=pin_map(extract(target));pm=collections.defaultdict(set)
    for p in pp:pm[p["ref"],p["pin"]].add(p["net"])
    ss=schematic(extract(schtarget))
    mismatch=[s for s in ss if s["conflicts"] or pm.get((s["ref"],s["pin"]))!={s["net"]}]
    critical=[k for k,v in critical_expectations().items() if pm.get(k)!={v}]
    assert not mismatch,("schematic parity",mismatch)
    assert not critical,("critical pins",critical)
    newrows,newpads=load(str(HERE/"pcb-eco50-docs.json"))
    newids={r["h"]["id"] for r in added}
    changed_lines=[r for r in newrows if r["h"]["type"] in ["LINE","VIA"] and (r["h"]["id"] in newids or r in rows and any(o["h"]["id"]==r["h"]["id"] and o["b"]!=r["b"] for o in original))]
    issues=check(changed_lines,[r for r in newrows if r["h"]["id"] not in {q["h"]["id"] for q in changed_lines}],newpads,{"USB_CONSOLE_DP","USB_CONSOLE_DM"})
    summary={"status":"ENGINEERING_CANDIDATE_NOT_FOR_FABRICATION","source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"pcb_sha256":hashlib.sha256(target.read_bytes()).hexdigest(),"schematic_sha256":hashlib.sha256(schtarget.read_bytes()).hexdigest(),"critical_pin_checks":len(critical_expectations()),"critical_pin_failures":critical,"schematic_pin_keys":len(ss),"schematic_parity_failures":mismatch,"new_or_changed_copper_primitives":len(changed_lines),"local_clearance_issues":issues,"removed_ids":sorted(remove),"cached_pours_removed":True,"native_pours_rebuilt":False,"native_drc_passed":False,"power_load_step_tested":False,"ordered_release_changed":False,"bulk_uF_nominal":539,"soft_start_ms_nominal":11,"scope":"Pad/net parity and local geometry only; no loop stability, thermal, EMC, safety, physical fit or native ERC/DRC approval."}
    json_file(HERE/"validation.json",summary)
    print(json.dumps({k:v for k,v in summary.items() if k!="local_clearance_issues"},indent=2))
    print("local clearance issues",len(issues))
    for i in issues:print(i["id"],i["net"],i["conflicts"])

if __name__=="__main__":main()
