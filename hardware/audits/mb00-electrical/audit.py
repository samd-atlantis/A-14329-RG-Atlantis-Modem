"""Read-only audit of the frozen MB00 native files. No old concept data is used."""
import json, zipfile, math, hashlib, csv
from pathlib import Path
from collections import defaultdict, Counter
ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RELEASE = ROOT / "hardware/releases/A-14329-MB00"
def extract(path):
    docs=[]
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith(".epru"): continue
            head=None; rows={}
            for raw in archive.read(name).decode("utf-8-sig").splitlines():
                if not raw: continue
                a,b=raw.removesuffix("|").split("||",1)
                h=json.loads(a); body=json.loads(b) if b else None
                if h["type"]=="DOCHEAD":
                    if head: docs.append({"head":head,"records":[v for v in rows.values() if v["b"] is not None]})
                    head=body; rows={}
                else: rows[h["id"]]={"h":h,"b":body}
            if head: docs.append({"head":head,"records":[v for v in rows.values() if v["b"] is not None]})
    return docs

def attrs(rows):
    return {(r["b"]["parentId"],r["b"]["key"]):r["b"]["value"] for r in rows if r["h"]["type"]=="ATTR"}

def on_segment(x,y,b):
    a,c=b["startX"],b["startY"]; d,e=b["endX"],b["endY"]
    return abs((x-a)*(e-c)-(y-c)*(d-a))<1e-6 and min(a,d)-1e-6<=x<=max(a,d)+1e-6 and min(c,e)-1e-6<=y<=max(c,e)+1e-6

def schematic(docs):
    syms={d["head"]["uuid"]:d["records"] for d in docs if d["head"]["docType"]=="SYMBOL"}
    rows=next(d["records"] for d in docs if d["head"]["docType"]=="SCH_PAGE"); a=attrs(rows)
    wires=[r["b"] for r in rows if r["h"]["type"]=="LINE" and (r["b"].get("lineGroup"),"NET") in a]
    out=[]
    for r in rows:
        if r["h"]["type"]!="COMPONENT":continue
        c=r["b"]; cid=r["h"]["id"]; ref=a.get((cid,"Designator")); symbol=syms.get(a.get((cid,"Symbol")),[]); sa=attrs(symbol)
        if not ref:continue
        for pr in symbol:
            if pr["h"]["type"]!="PIN" or pr["b"].get("partId")!=c["partId"]: continue
            p=pr["b"]; pid=pr["h"]["id"]; x=p["x"];y=p["y"]
            if c.get("isMirror"): x=-x
            rad=math.radians(c.get("rotation",0)); co=round(math.cos(rad),12);si=round(math.sin(rad),12)
            x,y=c["x"]+co*x-si*y,c["y"]+si*x+co*y
            ns={a[(w["lineGroup"],"NET")] for w in wires if on_segment(x,y,w)}
            nc=a.get((cid+"-"+pid,"NO_CONNECT"))=="yes"
            out.append(dict(ref=ref,pin=sa.get((pid,"Pin Number")),name=sa.get((pid,"Pin Name")),net=next(iter(ns)) if len(ns)==1 else "",conflicts=sorted(ns) if len(ns)>1 else [],nc=nc,x=x,y=y))
    return out

def pcb(docs):
    rows=next(d["records"] for d in docs if d["head"]["docType"]=="PCB"); a=attrs(rows)
    fp={d["head"]["uuid"]:d["records"] for d in docs if d["head"]["docType"]=="FOOTPRINT"}
    pn={}
    for r in rows:
        if r["h"]["type"]=="PAD_NET":
            k=json.loads(r["h"]["id"]);pn[(k[1],k[3])]=r["b"]["padNet"]
    out=[]
    for r in rows:
        if r["h"]["type"]!="COMPONENT": continue
        cid=r["h"]["id"]; ref=a.get((cid,"Designator"))
        for pad in fp.get(a.get((cid,"Footprint")),[]):
            if pad["h"]["type"]!="PAD":continue
            out.append(dict(ref=ref,pin=pad["b"]["num"],net=pn.get((cid,pad["h"]["id"]),""),id=cid+":"+pad["h"]["id"]))
    # Recovery contacts are intentionally free pads, not pick-and-place components.
    for r in rows:
        if r["h"]["type"] != "PAD": continue
        b=r["b"]; label=str(b["num"])
        if label.startswith(("H1-","J12-")):
            ref,num=label.split("-",1)
        elif r["h"]["id"] in {"ed28120000000002","ed28120000000003","ed28120000000004","ed28120000000005"}:
            ref,num="J13",label
        else: continue
        out.append(dict(ref=ref,pin=num,net=b["netName"],id=r["h"]["id"],standalone=True))
    return out,rows


def critical_expectations():
    e={}
    def add(ref,mapping):
        e.update({(ref,str(pin)):net for pin,net in mapping.items()})
    add("U1",{1:"GND_ISO",2:"3V3_ROUTER",3:"3V3_ROUTER",4:"GND_ISO",14:"ROUTER_RESET_N",21:"GND_ISO",23:"GND_ISO",24:"I2C_SCL",25:"I2C_SDA",30:"ROUTER_GPIO0_N",31:"CONSOLE_TX",32:"CONSOLE_RX",54:"USB_HOST_DP",55:"USB_HOST_DM",56:"GND_ISO",57:"GND_ISO",58:"GND_ISO",59:"GND_ISO"})
    for port,pins in {1:[38,39,40,41],2:[44,45,42,43],3:[46,47,48,49],4:[52,53,50,51]}.items():
        add("U1",dict(zip(pins,[f"LAN{port}_TXP",f"LAN{port}_TXN",f"LAN{port}_RXP",f"LAN{port}_RXN"])))
        add("U1",{13-port:f"LAN{port}_LED_N"})
        add(f"J{port+1}",{1:f"LAN{port}_TXP",2:f"LAN{port}_TXN",3:f"LAN{port}_TX_CT",4:"",5:f"LAN{port}_RX_CT",6:f"LAN{port}_RXP",7:f"LAN{port}_RXN",8:"CHASSIS_PE",9:f"LAN{port}_GREEN_A",10:f"LAN{port}_LED_N",11:"",12:"",13:"CHASSIS_PE",14:"CHASSIS_PE"})
        add(f"C{40+port}",{1:f"LAN{port}_RX_CT",2:"GND_ISO"});add(f"C{50+port}",{1:f"LAN{port}_TX_CT",2:"GND_ISO"})
    modem={str(i):"" for i in range(1,53)}
    modem.update({str(i):"GND_ISO" for i in [4,9,15,18,21,26,27,29,34,35,37,40,43,50]})
    modem.update({str(i):"3V3_MODEM" for i in [2,39,41,52]})
    modem.update({"8":"USIM_VDD","10":"USIM_DATA","12":"USIM_CLK","14":"USIM_RST","22":"MODEM_PERST_N","36":"USB_MODEM_DM","38":"USB_MODEM_DP"})
    add("J8",modem)
    add("U6",{1:"I2C_SCL",2:"I2C_SDA",3:"GND_ISO",4:"GND_ISO",5:"GND_ISO",6:"ROUTER_RESET_N",9:"GND_ISO",10:"SIM_SELECT",11:"MODEM_OFF",12:"MODEM_RESET_REQ",18:"3V3_ROUTER"})
    add("U10",{1:"SIM_B_CLK",2:"USIM_CLK",3:"SIM_A_CLK",4:"GND_ISO",5:"SIM_B_RST",6:"USIM_RST",7:"SIM_A_RST",8:"SIM_SELECT",9:"SIM_B_IO",10:"USIM_DATA",11:"SIM_A_IO",12:"3V3_ROUTER",13:"SIM_B_VCC",14:"USIM_VDD",15:"SIM_A_VCC",16:"SIM_SELECT"})
    add("U8",{1:"USB_HOST_DP",2:"USB_HOST_DM",3:"USB_SERVICE_DP",4:"USB_SERVICE_DM",5:"GND_ISO",6:"MODEM_OFF",7:"USB_MODEM_DM",8:"USB_MODEM_DP",9:"MODEM_USB_SEL",10:"3V3_ROUTER"})
    add("U18",{1:"USB_UART_OE_N",2:"USB_UART_TX_BUF",3:"USB_UART_RX_BUF",4:"GND_ISO",5:"CONSOLE_TX",6:"CONSOLE_RX",7:"USB_UART_OE_N",8:"3V3_ROUTER"})
    add("U14",{1:"SIM_A_CLK",2:"GND_ISO",3:"SIM_A_RST",4:"SIM_A_IO",5:"SIM_A_VCC",6:""})
    add("U16",{1:"GND_ISO",2:"USB_UART_TX",3:"USB_UART_RX",4:"USB_UART_3V3",5:"USB_CONSOLE_DP",6:"USB_CONSOLE_DM",15:"GND_ISO",16:"USB_UART_3V3"})
    for ref,rail,sw,ss,en in [("U2","3V3_ROUTER","R_SW","R_SS","5V_ISO"),("U3","3V3_MODEM","M_SW","M_SS","MODEM_BUCK_EN")]:
        add(ref,{1:sw,2:sw,3:sw,4:"",5:"GND_ISO",6:"GND_ISO",7:"GND_ISO",8:"GND_ISO",9:ss,10:"5V_ISO",11:"5V_ISO",12:"5V_ISO",13:en,14:rail,15:"GND_ISO",16:"GND_ISO",17:"GND_ISO"})
    for ref,g,d in [("Q1","MODEM_OFF_GATE","MODEM_BUCK_EN"),("Q2","MODEM_RESET_GATE","MODEM_PERST_N"),("Q3","USB_DETECT_GATE","USB_UART_OE_N"),("Q4","MUSB_GATE","MUSB_DETECT_N"),("Q5","MUSB_DETECT_N","MODEM_USB_SEL")]:add(ref,{1:g,2:"GND_ISO",3:d})
    add("PS1",{1:"AC_N",2:"AC_L_FUSED",3:"5V_ISO",4:"GND_ISO"})
    add("F1",{1:"AC_L_IN",2:"AC_L_FUSED"})
    for ref in ["CN1","J15","J16"]:add(ref,{1:"AC_L_IN",2:"AC_N",3:"CHASSIS_PE"})
    return e

def main():
    sch=schematic(extract(RELEASE/"schematic-assembly49.epro2")); pads,rows=pcb(extract(RELEASE/"pcb-assembly49.epro2"))
    sm={(x["ref"],x["pin"]):x for x in sch}; pm=defaultdict(set)
    for x in pads: pm[x["ref"],x["pin"]].add(x["net"])
    expectations=critical_expectations()
    critical_errors=[dict(ref=k[0],pin=k[1],expected=v,pcb=sorted(pm.get(k,set()))) for k,v in expectations.items() if pm.get(k)!={v}]
    OUT.joinpath("critical-pins.json").write_text(json.dumps([dict(ref=k[0],pin=k[1],expected_net=v,pcb_nets=sorted(pm.get(k,set())),passes=pm.get(k)=={v}) for k,v in expectations.items()],indent=2),encoding="utf-8")
    mismatches=[]; missing=[]; unlabelled=[]
    for k,s in sm.items():
        if not s["net"] and not s["nc"]:unlabelled.append(s)
        if k not in pm: missing.append(s);continue
        if pm[k]!={s["net"]}: mismatches.append(dict(ref=k[0],pin=k[1],schematic=s["net"],pcb=sorted(pm[k])))
    extras=[dict(ref=k[0],pin=k[1],nets=sorted(n)) for k,n in pm.items() if k not in sm]
    for name,data in [("schematic-pins.json",sch),("pcb-pad-nets.json",pads)]: OUT.joinpath(name).write_text(json.dumps(data,indent=2),encoding="utf-8")
    result=dict(critical_pin_checks=len(expectations),critical_pin_errors=critical_errors,sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [RELEASE/"schematic-assembly49.epro2",RELEASE/"pcb-assembly49.epro2"]},schematic_pins=len(sch),pcb_physical_pads=len(pads),matched_keys=len(set(sm)&set(pm)),mismatches=mismatches,schematic_pins_without_component_pad=missing,pcb_pads_without_symbol_pin=extras,unlabelled_without_NC=unlabelled,conflicting_labels=[s for s in sch if s["conflicts"]],limitations=["Pad NET and wire labels, not electrical continuity through routed copper.","Standalone H1/J12 pads mapped by explicit names; J13 by recorded native IDs. Mechanical/contact fit not assessed here.","Part pin expectations and physical checks are separate from schematic-vs-PCB agreement."])
    OUT.joinpath("native-pin-comparison.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k not in ["schematic_pins_without_component_pad","pcb_pads_without_symbol_pin","unlabelled_without_NC"]},indent=2))
    print("missing",len(missing),"extra",len(extras),"unlabelled",len(unlabelled))
if __name__=="__main__":main()
