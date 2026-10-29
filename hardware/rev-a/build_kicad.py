"""Reproducible native KiCad 9 schematic generation with explicit pin/net audit.

Not a substitute for component, safety, firmware or PCB design review.
Library symbols are embedded and copied to a project-local library.
"""
from pathlib import Path
import sys, math, json, csv, copy, uuid, re, collections
from library_inspect import load, nodes, node, key
ROOT=Path(__file__).resolve().parent
WORK=ROOT.parents[1]
sys.path.insert(0,str(WORK/'.tools/python'))
import sexpdata as sx
OUT=ROOT/'kicad';OUT.mkdir(exist_ok=True)
PROJECT='walchem_gateway'
NS=uuid.UUID('0f959e01-7ef3-478d-9c10-e150004bab78')
def uid(s):return str(uuid.uuid5(NS,s))
def q(s):return json.dumps(str(s),ensure_ascii=False)
def f(n):return f'{n:.5f}'.rstrip('0').rstrip('.') if n else '0'
def ef(size=1.0,hide=False,justify=''):
 return f'(effects (font (size {size} {size}))'+(' (justify '+justify+')' if justify else '')+(' (hide yes)' if hide else '')+')'

LIB={}; META={}; BOM={}; AUDIT=[]; PARTS={}; sheets=[]
def standard(lib,name,alias=None):
 alias=alias or name
 n=load(lib,name);old=n[1];n[1]=alias
 for sub in nodes(n,'symbol'):sub[1]=alias+'_'+sub[1].rsplit('_',2)[-2]+'_'+sub[1].rsplit('_',2)[-1]
 LIB[alias]=n
 META[alias]={'source':f'KiCad 9.0.7 {lib}:{name}; manufacturer cross-check as documented','datasheet':next((p[2] for p in nodes(n,'property') if p[1]=='Datasheet'),'')}
 return alias

def custom(name,left,right,footprint='',datasheet='',source='',ref='U'):
 """Entries: (physical pin number, name, electrical type). Left and right ordered top to bottom."""
 h=max(len(left),len(right))*3.81/2+2.54
 n=sx.loads(f'(symbol {q(name)} (pin_names (offset 0.8)) (exclude_from_sim no) (in_bom yes) (on_board yes) (property "Reference" {q(ref)} (at 0 {f(h+4)} 0) {ef(1.27)}) (property "Value" {q(name)} (at 0 {f(h+1.5)} 0) {ef(1.27)}) (property "Footprint" {q(footprint)} (at 0 0 0) {ef(hide=True)}) (property "Datasheet" {q(datasheet)} (at 0 0 0) {ef(hide=True)}) (symbol {q(name+"_0_1")} (rectangle (start -20.32 {f(h)}) (end 20.32 {f(-h)}) (stroke (width 0.254) (type default)) (fill (type background)))) )')
 pins=[sx.Symbol('symbol'),name+'_1_1']
 for side,entries in [(-1,left),(1,right)]:
  for i,(number,label,typ) in enumerate(entries):
   y=((len(entries)-1)//2)*3.81-i*3.81
   pins.append(sx.loads(f'(pin {typ} line (at {f(side*25.4)} {f(y)} {0 if side<0 else 180}) (length 5.08) (name {q(label)} {ef(1.0)}) (number {q(number)} {ef(1.0)}))'))
 n.append(pins);LIB[name]=n;META[name]={'source':source,'datasheet':datasheet}
 return name

class Sheet:
 def __init__(self,name,title,num):
  self.name=name;self.title=title;self.num=num;self.uuid=uid('sheet:'+name);self.parts=[];self.items=[];self.used=set();self.count=0
  sheets.append(self)
 def text(self,text,x,y,size=1.25):
  self.items.append(f'(text {q(text)} (at {f(x)} {f(y)} 0) {ef(size,justify="left")} (uuid {q(uid(self.name+text+str(x)+str(y)))}))')
 def wire(self,a,b):
  if a==b:return
  self.count+=1
  self.items.append(f'(wire (pts (xy {f(a[0])} {f(a[1])}) (xy {f(b[0])} {f(b[1])})) (stroke (width 0.1524) (type default)) (uuid {q(uid(self.name+"wire"+str(self.count)))}))')
 def label(self,net,at,angle=0):
  self.count+=1
  just='right' if angle==180 else 'left'
  self.items.append(f'(global_label {q(net)} (shape passive) (at {f(at[0])} {f(at[1])} {angle}) {ef(0.95,justify=just)} (uuid {q(uid(self.name+"label"+str(self.count)))}))')
 def part(self,name,ref,value,x,y,nets,footprint=None,mpn='',status='Selected; review required',unit=1,dnp=False):
  x=round(x/1.27)*1.27;y=round(y/1.27)*1.27
  n=LIB[name];self.used.add(name)
  props={p[1]:p[2] for p in nodes(n,'property')}
  fp=props.get('Footprint','') if footprint is None else footprint
  ident=uid(self.name+ref+str(unit));path=f'/{uid("root")}/{self.uuid}'
  # Custom symbols use a local body with a symmetric pin bank. Standard symbols use source geometry.
  pins=[]
  for sub in nodes(n,'symbol'):
   match=re.search(r'_(\d+)_(\d+)$',sub[1])
   if match and int(match[1]) in (0,unit):pins+=nodes(sub,'pin')
  highest=max([node(p,'at')[2] for p in pins]+[5])
  # Single pin flags use a compact title above; other titles sit above the highest pin.
  top=y-highest-5.08
  fields=''.join(f'(property {q(k)} {q(v)} (at {f(x)} {f(top+i*2.54 if k in ("Reference","Value") else y)} 0) {ef(1.1,hide=k not in ("Reference","Value"))})' for i,(k,v) in enumerate([('Reference',ref),('Value',value),('Footprint',fp),('Datasheet',META[name]['datasheet']),('MPN',mpn or value),('DesignStatus',status)]))
  self.parts.append(f'(symbol (lib_id {q("Gateway:"+name)}) (at {f(x)} {f(y)} 0) (unit {unit}) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp {"yes" if dnp else "no"}) (uuid {q(ident)}) {fields}'+''.join(f'(pin {q(node(p,"number")[1])} (uuid {q(uid(ident+str(node(p,"number")[1])))}))' for p in pins)+f'(instances (project {q(PROJECT)} (path {q(path)} (reference {q(ref)}) (unit {unit})))) )')
  occupied={}
  for p in pins:
   num=str(node(p,'number')[1]);pn=node(p,'name')[1];pt=node(p,'at');angle=pt[3]
   px=round(x+pt[1],5);py=round(y-pt[2],5)
   net=nets.get(num)
   typ=str(p[1])
   AUDIT.append(dict(sheet=self.name,reference=ref,unit=unit,pin=num,pin_name=pn,electrical_type=typ,net=net or 'NC',source=META[name]['source'],status=status))
   if net is None:
    if (px,py) not in occupied:
     self.items.append(f'(no_connect (at {f(px)} {f(py)}) (uuid {q(uid(ident+"nc"+num))}))')
     occupied[(px,py)]=None
   elif (px,py) in occupied:
    assert occupied[(px,py)]==net,(ref,num,'stacked pins conflicting')
   else:
    occupied[(px,py)]=net
    dx,dy={0:(-7.62,0),180:(7.62,0),90:(0,7.62),270:(0,-7.62)}[angle]
    end=(px+dx,py+dy);self.wire((px,py),end)
    if dx:self.label(net,end,180 if dx<0 else 0)
    else:self.label(net,end,0)
  if ref in BOM:
   assert BOM[ref]['value']==value
  else:BOM[ref]=dict(reference=ref,value=value,mpn=mpn or value,footprint=fp,status=status,DNP=dnp)
  PARTS[(ref,unit)]=dict(name=name,nets=nets,footprint=fp)
 def write(self):
  libs=''.join(sx.dumps(LIB[n]).replace(q(n),q('Gateway:'+n),1) for n in sorted(self.used))
  txt=f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid {q(self.uuid)}) (paper "A3") (title_block (title {q(self.title)}) (date "2026-10-27") (rev "A1 - Engineering review") (company "Walchem connectivity gateway") (comment 1 "Not released for fabrication; see design-review.md")) (lib_symbols {libs})'+''.join(self.items+self.parts)+')'
  (OUT/(self.name+'.kicad_sch')).write_text(txt,encoding='utf8')

# Project-local copies retain standard library graphic conventions and original pin numbers.
for lib,name in [('Device','R'),('Device','C'),('Device','L'),('Device','Fuse'),('Device','LED'),('Switch','SW_Push'),('power','PWR_FLAG'),('Connector_Generic','Conn_01x03'),('Connector_Generic','Conn_01x04'),('Connector_Generic','Conn_01x06'),('Converter_ACDC','IRM-20-5'),('Regulator_Switching','TPS62132'),('Interface_Expansion','MCP23008-xSO'),('Power_Protection','TPD2EUSB30')]:standard(lib,name)
standard('Transistor_FET','2N7002','Q_NMOS_GSD')

H='https://h.hlktech.com/download/HLK-7628N/1/HLK-7628N%E7%A1%AC%E4%BB%B6%E6%89%8B%E5%86%8CV2.6.pdf'
A='https://en.ai-thinker.com/Uploads/file/20220930/20220930121135_29921.pdf'
Q='https://www.quectel.com/product/lte-eg25-gl-mini-pcie/'
hp={1:'GND',2:'3V3',3:'3V3',4:'GND',5:'SPI_CS0',6:'REF_CLK0',7:'PERST_N',8:'WDT_RST_N',9:'EPHY_LED4',10:'EPHY_LED3',11:'EPHY_LED2',12:'EPHY_LED1',13:'EPHY_LED0',14:'PORST_N',15:'UART_TXD1',16:'UART_RXD1',17:'I2S_SDI',18:'I2S_SDO',19:'I2S_WS',20:'I2S_CLK',21:'GND',22:'ANT_UNLINKED',23:'GND',24:'I2C_SCLK',25:'I2C_SD',26:'SPI_CS1',27:'SPI_CLK',28:'SPI_MISO',29:'SPI_MOSI',30:'GPIO0',31:'UART_TXD0',32:'UART_RXD0',33:'WLED_N',34:'MDI_RP_P0',35:'MDI_RN_P0',36:'MDI_TP_P0',37:'MDI_TN_P0',38:'MDI_TP_P1',39:'MDI_TN_P1',40:'MDI_RP_P1',41:'MDI_RN_P1',42:'MDI_RP_P2',43:'MDI_RN_P2',44:'MDI_TP_P2',45:'MDI_TN_P2',46:'MDI_TP_P3',47:'MDI_TN_P3',48:'MDI_RP_P3',49:'MDI_RN_P3',50:'MDI_RP_P4',51:'MDI_RN_P4',52:'MDI_TP_P4',53:'MDI_TN_P4',54:'USB_DP',55:'USB_DM',56:'GND'}
def htyp(i):
 if hp[i]=='GND' or i in [2,3]:return 'power_in'
 if i in [15,31]:return 'output'
 if i in [14,16,32]:return 'input'
 return 'bidirectional'
custom('HLK7628N',[(str(i),hp[i],htyp(i)) for i in range(1,29)]+[(f'EP{i}','THERMAL_GND','power_in') for i in range(1,4)],[(str(i),hp[i],htyp(i)) for i in range(29,57)],'Gateway:HLK7628N_56',H,'Hi-Link hardware manual PDF pp.11-13 and 16-17; physical 1-56 plus design-named unnumbered EP1-EP3 ground lands')
qp={1:'WAKE_N',2:'VCC_3V3',3:'RESERVED',4:'GND',5:'RESERVED',6:'NC',7:'RESERVED',8:'USIM_VDD',9:'GND',10:'USIM_DATA',11:'UART_RX',12:'USIM_CLK',13:'UART_TX',14:'USIM_RST',15:'GND',16:'RESERVED',17:'RI',18:'GND',19:'RESERVED',20:'W_DISABLE_N',21:'GND',22:'PERST_N',23:'UART_CTS',24:'RESERVED',25:'UART_RTS',26:'GND',27:'GND',28:'NC',29:'GND',30:'I2C_SCL',31:'DTR',32:'I2C_SDA',33:'RESERVED',34:'GND',35:'GND',36:'USB_DM',37:'GND',38:'USB_DP',39:'VCC_3V3',40:'GND',41:'VCC_3V3',42:'LED_WWAN_N',43:'GND',44:'USIM_PRESENCE',45:'PCM_CLK',46:'RESERVED',47:'PCM_DOUT',48:'NC',49:'PCM_DIN',50:'GND',51:'PCM_SYNC',52:'VCC_3V3'}
def qtyp(i):
 if qp[i] in ['GND','VCC_3V3']:return 'power_in'
 if qp[i] in ['NC','RESERVED']:return 'no_connect'
 if i==8:return 'power_out'
 if i in [12,14]:return 'output'
 if i in [20,22]:return 'input'
 return 'bidirectional'
custom('EG25GL_MiniPCIe',[(str(i),qp[i],qtyp(i)) for i in range(1,53,2)],[(str(i),qp[i],qtyp(i)) for i in range(2,53,2)],'',Q,'Quectel EG2x-GL Mini PCIe hardware design V1.1 PDF pp.16-19 (vendor-authored public mirror); confirm controlled copy',ref='J')
ap={1:'3V3',2:'EN',3:'IO14',4:'IO17',5:'IO3',6:'IO4',7:'IO2_FLASH',8:'IO8_NC',9:'GND',10:'IO5_SERVICE',11:'RXD',12:'TXD',13:'NC_GND_AMBIG',14:'IO1_FLASH',15:'RST_NC',16:'IO11',17:'IO12',18:'NC_GND_AMBIG'}
custom('AiWB2_13',[(str(i),ap[i],('power_in' if i in [1,9] else 'input' if i in [2,11] else 'output' if i==12 else 'bidirectional')) for i in range(1,10)],[(str(i),ap[i],('output' if i==12 else 'input' if i==11 else 'no_connect' if i in [13,15,18] else 'bidirectional')) for i in range(10,19)],'Gateway:AiWB2_13',A,'Ai-WB2-13 V1.1.0 PDF pp.10-12,16; NC/GND discrepancy on 13/18 is a release gate')
custom('SIM_MUX_TS3A44159PW', [('14','COM1_VCC','passive'),('2','COM2_CLK','passive'),('6','COM3_RST','passive'),('10','COM4_IO','passive'),('16','IN1_2','input'),('8','IN3_4','input'),('12','VCC','power_in'),('4','GND','power_in')], [('15','NC1_VCC','passive'),('3','NC2_CLK','passive'),('7','NC3_RST','passive'),('11','NC4_IO','passive'),('13','NO1_VCC','passive'),('1','NO2_CLK','passive'),('5','NO3_RST','passive'),('9','NO4_IO','passive')], 'Package_SO:TSSOP-16_4.4x5mm_P0.65mm','https://www.ti.com/lit/ds/symlink/ts3a44159.pdf','TI TS3A44159 SCDS225B p.3 PW package; COM->NC when controls low')
custom('TPS22918DBV',[('1','VIN','power_in'),('3','ON','input'),('2','GND','power_in')],[('6','VOUT','power_out'),('5','QOD','passive'),('4','CT','passive')],'Package_TO_SOT_SMD:SOT-23-6','https://www.ti.com/lit/ds/symlink/tps22918.pdf','TI TPS22918 DBV pin table')
custom('LVC2G125DCU',[('2','1A','input'),('5','2A','input'),('1','1OE_N','input'),('7','2OE_N','input')],[('6','1Y','tri_state'),('3','2Y','tri_state'),('8','VCC','power_in'),('4','GND','power_in')],'Package_SO:VSSOP-8_2.3x2mm_P0.5mm','https://www.ti.com/lit/ds/symlink/sn74lvc2g125.pdf','TI SCES204Q pp.4-5 DCU mapping, Ioff support')
custom('TS3USB221ARSE',[('8','D_PLUS','bidirectional'),('7','D_MINUS','bidirectional'),('6','OE_N','input'),('9','SELECT','input'),('10','VCC','power_in')],[('1','1D_PLUS','bidirectional'),('2','1D_MINUS','bidirectional'),('3','2D_PLUS','bidirectional'),('4','2D_MINUS','bidirectional'),('5','GND','power_in')],'Package_DFN_QFN:UQFN-10_1.4x1.8mm_P0.4mm','https://www.ti.com/lit/ds/symlink/ts3usb221a.pdf','TI SCDS277C p.3 RSE pin map; footprint must be replaced with verified RSE land pattern')
custom('NanoSIM_contacts',[('C1','VCC','power_in'),('C2','RST','input'),('C3','CLK','input')],[('C5','GND','power_in'),('C6','VPP_UNUSED','no_connect'),('C7','IO','bidirectional')],'','','ISO7816 contact designations only; mechanical socket SKU and contact-to-pad numbering unresolved',ref='J')
custom('eUICC_MFF2_ST4SIM200M',[('8','VCC','power_in'),('7','RESET','input'),('6','CLK','input'),('3','IO','bidirectional')],[('1','GND','power_in'),('2','SWIO_UNUSED','no_connect'),('4','NC','no_connect'),('5','NC','no_connect')],'','https://www.st.com/resource/en/data_brief/st4sim-200m.pdf','ST DB4082 Rev5 PDF p.14 VFDFPN8: top view; provider-specific ordering code not selected')
custom('MagJack7499010121A',[('1','RD_PLUS','passive'),('2','RX_CT','passive'),('3','RD_MINUS','passive'),('4','TD_PLUS','passive'),('5','TX_CT','passive'),('6','TD_MINUS','passive')],[('7','NC','no_connect'),('8','SHIELD_RETURN','passive'),('9','GREEN_A','passive'),('10','GREEN_K','passive'),('11','YELLOW_A','passive'),('12','YELLOW_K','passive'),('SH','SHIELD','passive')],'Connector_RJ:RJ45_Wuerth_7499010121A_Horizontal','https://www.we-online.com/components/products/datasheet/7499010121A.pdf','Wurth 7499010121A rev003.001 p.2; RX/TX names corrected against vendor, not old KiCad symbol',ref='J')
custom('TPD4E001DBV',[('1','IO1','passive'),('3','IO2','passive'),('4','IO3','passive')],[('6','IO4','passive'),('5','VCC','power_in'),('2','GND','power_in')],'Package_TO_SOT_SMD:SOT-23-6','https://www.ti.com/lit/ds/symlink/tpd4e001.pdf','TI TPD4E001 SLLS682P p3 DBV pin map; switched-SIM supply referenced clamps')

RFP='Resistor_SMD:R_0603_1608Metric';CFP='Capacitor_SMD:C_0603_1608Metric'
def rc(s,kind,ref,value,x,y,a,b,footprint=None,dnp=False):
 fp=footprint or (RFP if kind=='R' else CFP)
 s.part(kind,ref,value,x,y,{'1':a,'2':b},footprint=fp,dnp=dnp)
def cap(s,ref,value,x,y,a,b='GND_ISO',fp=None,dnp=False):rc(s,'C',ref,value,x,y,a,b,fp,dnp)
def res(s,ref,value,x,y,a,b,dnp=False):rc(s,'R',ref,value,x,y,a,b,dnp=dnp)

s=Sheet('01_ac_input','01 - 120 VAC input and isolated 5 V supply',2)
s.text('PRIMARY MAINS                                      ISOLATION BOUNDARY                              SECONDARY',25,25,1.8)
s.part('Conn_01x03','J1','AC L / N / PE',60,75,{'1':'AC_L_IN','2':'AC_N','3':'CHASSIS_PE'},footprint='',status='Mains-rated touch-safe terminal and enclosure earth arrangement unresolved')
s.part('Fuse','F1','T1A 250VAC - REVIEW',115,65,{'1':'AC_L_IN','2':'AC_L_FUSED'},footprint='',status='Fuse interrupt rating / inrush coordination and holder unresolved')
s.part('IRM-20-5','PS1','IRM-20-5',235,80,{'1':'AC_L_FUSED','2':'AC_N','3':'GND_ISO','4':'5V_ISO'},status='Pin map verified; thermal and mains integration review pending')
cap(s,'C1','47u 16V',300,100,'5V_ISO',fp='Capacitor_SMD:C_1210_3225Metric')
cap(s,'C2','100n 16V',330,100,'5V_ISO')
for i,net in enumerate(['AC_L_FUSED','AC_N','CHASSIS_PE']):s.part('PWR_FLAG',f'#FLG0{i+1}','PWR_FLAG',70+i*50,150,{'1':net},footprint='')
s.text('No copper or secondary signal may cross the primary-secondary isolation region.',25,195)
s.text('Do not bond GND_ISO to AC neutral or protective earth by assumption.',25,205)
s.text('Surge/EMI protection network and fuse are release gates; protection is not silently assumed complete.',25,215)
s.text('PS1 physical pins: 1 AC/L, 2 AC/N, 3 -V, 4 +V (Mean Well drawing).',25,225)
s.text('20 W is a candidate. Recheck enclosure derating, altitude, pollution degree and installation category.',25,235)

s=Sheet('02_dc_power','02 - Separate 3.3 V router and modem supplies',3)
for idx,(x,ref,rail) in enumerate([(85,'U2','3V3_ROUTER'),(280,'U3','3V3_MODEM')]):
 pre='R' if idx==0 else 'M';sw=f'{pre}_SW';ss=f'{pre}_SS';en='5V_ISO' if idx==0 else 'MODEM_BUCK_EN'
 nets={'10':'5V_ISO','11':'5V_ISO','12':'5V_ISO','13':en,'9':ss,'8':'GND_ISO','7':'GND_ISO','6':'GND_ISO','15':'GND_ISO','16':'GND_ISO','17':'GND_ISO','1':sw,'2':sw,'3':sw,'14':rail,'5':'GND_ISO'}
 s.part('TPS62132',ref,'TPS62132RGTR',x,75,nets,status='Pin map/reference topology verified; load transient and exact L/C qualification pending')
 s.part('L',f'L{idx+1}','2.2uH / >=4A Isat',x+55,65,{'1':sw,'2':rail},footprint='Inductor_SMD:L_Coilcraft_XxL4020',mpn='XFL4020-222MEB',status='Reference family; hot Isat and DCR review pending')
 cap(s,f'C{10+idx*10}','10u 16V X7R',x-35,140,'5V_ISO',fp='Capacitor_SMD:C_0805_2012Metric')
 cap(s,f'C{11+idx*10}','100n 16V',x-10,140,'5V_ISO')
 cap(s,f'C{12+idx*10}','3.3n 25V',x+20,140,ss)
 cap(s,f'C{13+idx*10}','22u 10V X7R',x+55,140,rail,fp='Capacitor_SMD:C_0805_2012Metric')
 if idx:
  cap(s,'C24','47u 10V X7R',x+85,140,rail,fp='Capacitor_SMD:C_1210_3225Metric')
  cap(s,'C25','47u 10V X7R',x+110,140,rail,fp='Capacitor_SMD:C_1210_3225Metric')
  res(s,'R20','100k',x-25,190,'5V_ISO','MODEM_BUCK_EN')
  s.part('Q_NMOS_GSD','Q1','2N7002',x+25,195,{'1':'MODEM_OFF_GATE','2':'GND_ISO','3':'MODEM_BUCK_EN'},footprint='Package_TO_SOT_SMD:SOT-23',mpn='2N7002',status='Gate1/source2/drain3; EN open-drain pull-down')
  res(s,'R21','1k',x-35,230,'MODEM_OFF','MODEM_OFF_GATE');res(s,'R22','100k',x+20,230,'MODEM_OFF_GATE','GND_ISO')
 else:s.part('PWR_FLAG','#FLG04','PWR_FLAG',x,190,{'1':rail},footprint='')
 if idx:s.part('PWR_FLAG','#FLG05','PWR_FLAG',x+75,190,{'1':rail},footprint='')
s.text('MODEM_OFF=1 disables USB and pulls U3 EN low. Default input/pulldown keeps modem ON.',25,258)
s.text('Fixed-output variant: FB, DEF and FSW to GND; VOS Kelvin sense after inductor. All grounds + EP17 connected.',25,266)
s.text('116uF nominal modem capacitance is a starting point inside the vendor LC range; measure transient response.',25,274)

s=Sheet('03_router_control','03 - Router module and I2C management',4)
hn={str(i):'GND_ISO' for i in [1,4,21,23,56]};hn.update({'2':'3V3_ROUTER','3':'3V3_ROUTER','14':'ROUTER_RESET_N','15':'UART1_HOST_TX','16':'UART1_HOST_RX','24':'I2C_SCL','25':'I2C_SDA','31':'CONSOLE_TX','32':'CONSOLE_RX','54':'USB_HOST_DP','55':'USB_HOST_DM'})
hn.update({f'EP{i}':'GND_ISO' for i in range(1,4)})
for i in range(1,5):hn[str(13-i)]=f'LAN{i}_LED_N'
channels={1:{'TXP':38,'TXN':39,'RXP':40,'RXN':41},2:{'TXP':44,'TXN':45,'RXP':42,'RXN':43},3:{'TXP':46,'TXN':47,'RXP':48,'RXN':49},4:{'TXP':52,'TXN':53,'RXP':50,'RXN':51}}
for ch,ps in channels.items():
 for name,pin in ps.items():hn[str(pin)]=f'LAN{ch}_{name}'
s.part('HLK7628N','U1','HLK-7628N 128M/32M',95,105,hn,status='Physical pins verified; boot-straps left unloaded; footprint verification pending')
mn={'1':'I2C_SCL','2':'I2C_SDA','3':'GND_ISO','4':'GND_ISO','5':'GND_ISO','6':'ROUTER_RESET_N','9':'GND_ISO','18':'3V3_ROUTER','10':'SIM_SELECT','11':'MODEM_OFF','12':'MODEM_RESET_REQ','13':'WIFI_AUX_EN','14':'WIFI_BUF_DISABLE'}
s.part('MCP23008-xSO','U6','MCP23008-E/SO',270,75,mn,status='18-pin SOIC mapping verified; address 0x20; power-on GPIO inputs')
res(s,'R30','4.7k',220,140,'3V3_ROUTER','I2C_SCL');res(s,'R31','4.7k',260,140,'3V3_ROUTER','I2C_SDA')
res(s,'R32','100k',300,140,'SIM_SELECT','GND_ISO');res(s,'R33','100k',340,140,'MODEM_OFF','GND_ISO')
res(s,'R34','100k',220,180,'WIFI_AUX_EN','GND_ISO');res(s,'R35','100k',260,180,'MODEM_RESET_REQ','GND_ISO')
cap(s,'C30','100n',300,180,'3V3_ROUTER');cap(s,'C31','22u 10V',340,180,'3V3_ROUTER',fp='Capacitor_SMD:C_0805_2012Metric')
s.part('SW_Push','SW1','ROUTER RESET',180,225,{'1':'ROUTER_RESET_N','2':'GND_ISO'},footprint='Button_Switch_SMD:SW_SPST_TL3342')
s.part('Conn_01x03','J7','CONSOLE 3V3 TTL',265,225,{'1':'GND_ISO','2':'CONSOLE_TX','3':'CONSOLE_RX'},footprint='Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical')
s.text('I2C controller pins 24/25; UART1 pins 15/16; UART0 pins 31/32. All module IO: 3.3 V.',25,265)
s.text('Unloaded boot-sensitive pins: 7,18,26,27,29,31 (console TX has no external pull). Use on-module RF connector.',25,273)

s=Sheet('04_ethernet','04 - Four 10/100 LAN ports with integrated magnetics',5)
for ch,(x,y) in enumerate([(95,75),(285,75),(95,190),(285,190)],1):
 ns={'1':f'LAN{ch}_RXP','2':f'LAN{ch}_RX_CT','3':f'LAN{ch}_RXN','4':f'LAN{ch}_TXP','5':f'LAN{ch}_TX_CT','6':f'LAN{ch}_TXN','8':'CHASSIS_PE','SH':'CHASSIS_PE','9':f'LAN{ch}_GREEN_A','10':f'LAN{ch}_LED_N'}
 s.part('MagJack7499010121A',f'J{ch+1}','7499010121A',x,y,ns,status='Vendor latest RX/TX names used; PHY CT bias and shield scheme are layout release gates')
 res(s,f'R4{ch}','470',x+55,y+10,'3V3_ROUTER',f'LAN{ch}_GREEN_A')
 # CT to AC ground is a deliberately reviewable candidate, not an assertion of PHY bias requirements.
 cap(s,f'C4{ch}','100n - DNP CT OPTION',x-35,y+42,f'LAN{ch}_RX_CT',dnp=True)
 cap(s,f'C5{ch}','100n - DNP CT OPTION',x+10,y+42,f'LAN{ch}_TX_CT',dnp=True)
s.text('Hi-Link KIT V2.5 leaves PHY-side CTs floating. C41-44/C51-54 are DNP options; verify selected jack on bench.',25,266)
s.text('Pin8 is cable-side termination return; shield tabs SH go to chassis/PE. No automatic GND_ISO bond.',25,274)

s=Sheet('05_cellular_usb','05 - EG25-GL socket, USB isolation and reset',6)
qn={str(i):'GND_ISO' for i,nm in qp.items() if nm=='GND'}
qn.update({str(i):'3V3_MODEM' for i in [2,39,41,52]});qn.update({'8':'USIM_VDD','10':'USIM_DATA','12':'USIM_CLK','14':'USIM_RST','22':'MODEM_PERST_N','36':'USB_MODEM_DM','38':'USB_MODEM_DP'})
s.part('EG25GL_MiniPCIe','J8','EG25-GL Mini PCIe socket',105,105,qn,status='52-pin modem map verified; exact connector footprint + controlled modem guide are release gates')
un={'8':'USB_HOST_DP','7':'USB_HOST_DM','6':'MODEM_OFF','9':'GND_ISO','10':'3V3_ROUTER','1':'USB_MODEM_DP','2':'USB_MODEM_DM','5':'GND_ISO'}
s.part('TS3USB221ARSE','U8','TS3USB221ARSER',280,75,un,footprint='',status='Pin map verified; USB disconnect on MODEM_OFF; RSE footprint must be selected')
s.part('TPD2EUSB30','U9','TPD2EUSB30DRTR',280,135,{'1':'USB_MODEM_DP','2':'USB_MODEM_DM','3':'GND_ISO'})
cap(s,'C60','100n',350,100,'3V3_ROUTER');cap(s,'C61','100n',350,140,'3V3_MODEM')
s.part('Q_NMOS_GSD','Q2','2N7002',270,200,{'1':'MODEM_RESET_GATE','2':'GND_ISO','3':'MODEM_PERST_N'},footprint='Package_TO_SOT_SMD:SOT-23')
res(s,'R60','1k',220,225,'MODEM_RESET_REQ','MODEM_RESET_GATE');res(s,'R61','100k',310,225,'MODEM_RESET_GATE','GND_ISO')
s.text('Only USB data are connected: Mini PCIe is the mechanical form factor, not a PCIe data link.',25,258)
s.text('PERST# open-drain control only; no external pull-up on modem pins. Disable SIM hot-detect in firmware.',25,266)
s.text('LTE main/diversity use modem RF connectors and coax pigtails; GNSS not populated.',25,274)

s=Sheet('06_sim_selection','06 - Switched physical SIM and eUICC (one active)',7)
sim={'14':'USIM_VDD','2':'USIM_CLK','6':'USIM_RST','10':'USIM_DATA','16':'SIM_SELECT','8':'SIM_SELECT','12':'3V3_ROUTER','4':'GND_ISO','15':'SIM_A_VCC','3':'SIM_A_CLK','7':'SIM_A_RST','11':'SIM_A_IO','13':'SIM_B_VCC','1':'SIM_B_CLK','5':'SIM_B_RST','9':'SIM_B_IO'}
s.part('SIM_MUX_TS3A44159PW','U10','TS3A44159PWR',105,80,sim,status='Four-pole break-before-make selector; current/capacitance and power-down sequencing require qualification')
s.part('NanoSIM_contacts','J9','NANO SIM - SOCKET TBD',290,65,{'C1':'SIM_A_VCC','C2':'SIM_A_RST','C3':'SIM_A_CLK','C5':'GND_ISO','C7':'SIM_A_IO'},status='ISO contact mapping complete; manufacturer pad mapping unresolved')
s.part('eUICC_MFF2_ST4SIM200M','U11','ST4SIM-200M provider SKU TBD',290,150,{'8':'SIM_B_VCC','7':'SIM_B_RST','6':'SIM_B_CLK','3':'SIM_B_IO','1':'GND_ISO'},status='MFF2 top-view pins mapped; provider ordering code/provisioning agreement not selected')
cap(s,'C70','100n',60,155,'3V3_ROUTER')
cap(s,'C71','100n',220,215,'SIM_A_VCC');cap(s,'C72','100n',280,215,'SIM_B_VCC')
s.part('PWR_FLAG','#FLG06','SWITCHED SIM POWER',220,170,{'1':'SIM_A_VCC'},footprint='',status='ERC source annotation only: supplied through passive SIM selector, not an independent source')
s.part('PWR_FLAG','#FLG07','SWITCHED SIM POWER',355,215,{'1':'SIM_B_VCC'},footprint='',status='ERC source annotation only: supplied through passive SIM selector, not an independent source')
res(s,'R70','15k',90,205,'USIM_VDD','USIM_DATA')
s.part('TPD4E001DBV','U14','TPD4E001DBVR',105,150,{'1':'SIM_A_CLK','3':'SIM_A_RST','4':'SIM_A_IO','5':'SIM_A_VCC','2':'GND_ISO'},status='Physical SIM ESD array; locate at selected socket, referenced to switched SIM_A_VCC')
s.text('SIM_SELECT low = physical SIM; high = eUICC. All four nets switch; no parallel SIM connection.',25,250)
s.text('Detach and power modem down before changing SELECT. Discharge SIM supply, then re-enable and attach.',25,258)
s.text('Provider-specific eUICC is not a generic blank chip. SGP.02 versus consumer/IoT provisioning must be agreed.',25,266)
s.text('Release gates: exact SIM socket, ESD layout, profile provider and modem/APDU firmware qualification.',25,274)

s=Sheet('07_wifi_ble','07 - Ai-WB2-13 Wi-Fi/BLE and isolated UART',8)
s.part('TPS22918DBV','U12','TPS22918DBVR',90,65,{'1':'3V3_ROUTER','2':'GND_ISO','3':'WIFI_AUX_EN','6':'3V3_AUX','5':'WIFI_QOD','4':'WIFI_CT'})
res(s,'R80','100',150,105,'WIFI_QOD','3V3_AUX');cap(s,'C80','1n',65,110,'WIFI_CT')
cap(s,'C81','1u',35,150,'3V3_ROUTER');cap(s,'C82','10u 10V',100,150,'3V3_AUX',fp='Capacitor_SMD:C_0805_2012Metric')
cap(s,'C83','100n',150,150,'3V3_AUX')
s.part('AiWB2_13','U5','Ai-WB2-13',290,100,{'1':'3V3_AUX','2':'WIFI_EN','9':'GND_ISO','10':'WIFI_SERVICE','11':'WIFI_UART_RX','12':'WIFI_UART_TX'},status='Pins verified except 13/18 vendor NC/GND ambiguity; reset15 not used')
res(s,'R81','10k',230,180,'3V3_AUX','WIFI_EN');res(s,'R82','10k - DNP SERVICE',280,180,'WIFI_SERVICE','GND_ISO',dnp=True)
s.part('SW_Push','SW2','WIFI SERVICE - DNP',340,180,{'1':'WIFI_SERVICE','2':'3V3_AUX'},footprint='Button_Switch_SMD:SW_SPST_TL3342',dnp=True,status='Optional GPIO5 service button; download strap behavior not assumed')
s.part('LVC2G125DCU','U13','SN74LVC2G125DCUR',105,220,{'2':'UART1_HOST_TX','6':'WIFI_UART_RX','5':'WIFI_UART_TX','3':'UART1_HOST_RX','1':'WIFI_BUF_DISABLE','7':'WIFI_BUF_DISABLE','8':'3V3_AUX','4':'GND_ISO'})
res(s,'R83','100k',215,230,'3V3_AUX','WIFI_BUF_DISABLE');cap(s,'C84','100n',280,230,'3V3_AUX')
s.part('Conn_01x04','J10','AUX UART / SERVICE',350,225,{'1':'GND_ISO','2':'3V3_AUX','3':'WIFI_UART_RX','4':'WIFI_UART_TX'},footprint='Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',status='3.3V TTL service header; disable host UART buffer before external programming; no 5V adapter')
s.text('U13 Ioff prevents UART back-power when auxiliary module is off. Firmware enables buffer after router boot.',25,260)
s.text('Native router Wi-Fi carries controller IP traffic; Ai-WB2 supplies BLE / Wi-Fi provisioning application.',25,268)
s.text('Module pin15 is NC by default. Pins13/18 labelled NC but table says Ground: obtain vendor clarification.',25,276)

for s in sheets:s.write()
# Root hierarchy: all inter-sheet connections use named global labels.
root=f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid {q(uid("root"))}) (paper "A3") (title_block (title "Walchem cellular gateway - schematic index") (date "2026-10-27") (rev "A1 - Engineering review") (comment 1 "120 VAC / EG25-GL / 4 LAN / Wi-Fi + BLE / NO LoRa")) (lib_symbols)'
for i,s in enumerate(sheets):
 x=40+(i%2)*190;y=45+(i//2)*50
 root+=f'(sheet (at {x} {y}) (size 150 25) (fields_autoplaced) (stroke (width 0.1524) (type default)) (fill (color 0 0 0 0)) (uuid {q(s.uuid)}) (property "Sheetname" {q(s.title)} (at {x} {y-2} 0) {ef(1.1,justify="left bottom")}) (property "Sheetfile" {q(s.name+".kicad_sch")} (at {x} {y+27} 0) {ef(1.0,justify="left top")}))'
root+='(text "Engineering review: exact connector footprints, Ethernet PHY bias, SIM provider and mains integration remain gates.\\nSee design-review.md and pin-map.csv. No fabrication release implied by ERC." (at 40 262 0) (effects (font (size 1.25 1.25)) (justify left)) (uuid '+q(uid('rootnote'))+'))'
(OUT/(PROJECT+'.kicad_sch')).write_text(root+')',encoding='utf8')
settings={'meta':{'filename':PROJECT+'.kicad_pro','version':1},'schematic':{'meta':{'version':1}},'net_settings':{'classes':[{'name':'Default','clearance':.2,'track_width':.25,'via_diameter':.6,'via_drill':.3,'diff_pair_width':.2,'diff_pair_gap':.15,'diff_pair_via_gap':.25}],'meta':{'version':3}}}
demo=json.loads((WORK/'.tools/kicad/share/kicad/demos/complex_hierarchy/complex_hierarchy.kicad_pro').read_text())
settings['erc']=demo['erc'];settings['schematic']=demo['schematic']
(OUT/(PROJECT+'.kicad_pro')).write_text(json.dumps(settings,indent=2),encoding='utf8')
lib='(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")'+''.join(sx.dumps(n) for n in LIB.values())+')'
(OUT/'Gateway.kicad_sym').write_text(lib,encoding='utf8')
(OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Gateway") (type "KiCad") (uri "${KIPRJMOD}/Gateway.kicad_sym") (options "") (descr "Project-local verified/custom symbols")))',encoding='utf8')
for name,rows in [('pin-map.csv',AUDIT),('bom.csv',list(BOM.values()))]:
 with (OUT/name).open('w',newline='',encoding='utf8') as file:
  w=csv.DictWriter(file,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(OUT/'design-data.json').write_text(json.dumps({'bom':list(BOM.values()),'pins':AUDIT},indent=2),encoding='utf8')
print(f'Generated root + {len(sheets)} native KiCad sheets; {len(BOM)} references; {len(AUDIT)} physical pins.')
