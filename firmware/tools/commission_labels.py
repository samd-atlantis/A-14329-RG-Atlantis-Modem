"""ESP Rev 2 style setup labels for verified Atlantis HLK router identities.

Uses the same 2000x3000 logical canvas, two QR sections, CCW print rotation,
Windows GDI printer path and default two copies. No ESP flash code is executed.
Rendering is separate from printing. The copied executable is never imported.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
from build_support import validate_unit
from device_address import unit_url, REMOTE_ORIGIN

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRINTER = r'\\Atech-DC.atechllc.local\Label 1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wifi_payload(ssid, password):
    def escape(value):
        return re.sub(r'([\\;,:\"])', r'\\\1', value)
    return 'WIFI:T:WPA;S:'+escape(ssid)+';P:'+escape(password)+';;'


def verified_data(folder, verification):
    folder, verification = Path(folder), Path(verification)
    unit_path = folder/'unit.json'
    unit = json.loads(unit_path.read_text())
    validate_unit(unit)
    record = json.loads(verification.read_text())
    serial, mac = record.get('serial'), record.get('wifi_mac', '')
    if (record.get('schema'), record.get('identity_status'), serial, record.get('unit_sha256')) != (
            'mb00-identity-verification-1', 'CAPTURED_PROBE_MATCH', unit.get('serial'), digest(unit_path)):
        raise ValueError('A matching commissioning identity readback is required before labels')
    if not isinstance(mac, str) or not re.fullmatch(r'(?:[0-9A-F]{2}:){5}[0-9A-F]{2}', mac) or int(mac[:2],16)&1 or mac=='00:00:00:00:00:00':
        raise ValueError('Invalid verified radio MAC')
    if record.get('ssid') != 'Atlantis-'+mac.replace(':','')[-4:] or unit.get('ssid') not in ('Atlantis-AUTO', record['ssid']):
        raise ValueError('Wi-Fi label must match the verified internal radio MAC')
    if record.get('remote_url') != unit_url(serial):
        raise ValueError('Permanent unit URL must match the commissioning record and enclosure serial')
    with (folder/'credentials.csv').open(newline='', encoding='utf-8') as file:
        credentials = list(csv.DictReader(file))
    if len(credentials)!=1 or credentials[0].get('serial')!=serial or credentials[0].get('wifi_password')!=unit.get('wifi_password'):
        raise ValueError('Wrong commissioning credential sheet')
    credentials = credentials[0]
    # Check that the printable root password is actually the unit's root hash.
    # The hash itself is not a label, and passwords are never command arguments.
    import subprocess
    import hmac
    hashed = subprocess.run(['openssl','passwd','-6','-salt',unit['root_hash'].split('$')[2],'-stdin'],
        input=credentials['admin_password']+'\n', text=True,capture_output=True,check=True).stdout.strip()
    if not hmac.compare_digest(hashed,unit['root_hash']):
        raise ValueError('Admin credential does not match this unit')
    return {'serial':serial,'ssid':record['ssid'],'wifi_password':unit['wifi_password'],
        'username':'root','admin_password':credentials['admin_password'],'setup_url':'https://10.0.100.7',
        'remote_url':record['remote_url']}


def font(size, bold=True):
    from PIL import ImageFont
    windows = Path(os.environ.get('WINDIR', 'C:/Windows'))/'Fonts'/('arialbd.ttf' if bold else 'arial.ttf')
    linux = Path('/usr/share/fonts/truetype/dejavu')/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')
    for path in (windows, linux):
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


def fitted(draw, box, text, size=90, bold=True, anchor='mm'):
    left,top,right,bottom=box
    for n in range(size, 17, -2):
        face=font(n,bold)
        bounds=draw.textbbox((0,0),text,font=face)
        if bounds[2]-bounds[0]<=right-left-20 and bounds[3]-bounds[1]<=bottom-top-10:
            draw.text(((left+right)//2,(top+bottom)//2),text,fill='black',font=face,anchor=anchor)
            return
    raise ValueError('Label text does not fit; check commissioning record')


def paste_qr(image, box, payload):
    import qrcode
    from PIL import Image
    qr=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,border=4,box_size=1)
    qr.add_data(payload);qr.make(fit=True)
    matrix=qr.get_matrix()
    cell=min(box[2]-box[0],box[3]-box[1])//len(matrix)
    if cell<4:
        raise ValueError('QR is too dense for this label')
    qr_image=qr.make_image().convert('RGB').resize((len(matrix)*cell,)*2,Image.Resampling.NEAREST)
    image.paste(qr_image,(box[0]+(box[2]-box[0]-qr_image.width)//2,box[1]+(box[3]-box[1]-qr_image.height)//2))


def setup_label(data, sample=False):
    from PIL import Image,ImageDraw
    image=Image.new('RGB',(2000,3000),'white');draw=ImageDraw.Draw(image)
    logo=Image.open(ROOT/'commissioning/assets/atlantis-bw.png').convert('RGBA')
    logo.thumbnail((980,210))
    draw.rounded_rectangle(((2000-logo.width)//2-16,10,(2000+logo.width)//2+16,240),radius=12,fill='black')
    image.paste(logo,((2000-logo.width)//2,25),logo)
    fitted(draw,(50,245,1950,380),'MODEM SETUP',120)
    fitted(draw,(70,395,1930,500),'S/N '+data['serial'],95)
    for y,title in ((580,'1  WI-FI'),(1610,'2  LOCAL LOGIN')):
        draw.rounded_rectangle((50,y,1950,y+980),radius=45,outline='black',width=12)
        fitted(draw,(90,y+20,1260,y+150),title,100)
        draw.line((90,y+640,1910,y+640),fill='black',width=8)
    fitted(draw,(90,780,1300,930),'SSID',68)
    fitted(draw,(90,940,1300,1120),data['ssid'],94)
    paste_qr(image,(1360,680,1900,1220),wifi_payload(data['ssid'],data['wifi_password']))
    fitted(draw,(90,1240,1910,1340),'WI-FI PASSWORD',52)
    fitted(draw,(90,1340,1910,1510),data['wifi_password'],94)
    fitted(draw,(90,1790,1300,1990),data['setup_url'],82)
    fitted(draw,(90,2010,1300,2160),'USER  '+data['username'],76)
    paste_qr(image,(1360,1710,1900,2250),data['setup_url'])
    fitted(draw,(90,2270,1910,2370),'ADMIN PASSWORD',52)
    fitted(draw,(90,2370,1910,2530),data['admin_password'],94)
    fitted(draw,(70,2620,1930,2720),'A-14329-MB00 · REMOTE ACCESS',60)
    fitted(draw,(70,2730,1930,2840),data.get('remote_url') or unit_url(data['serial']),72)
    fitted(draw,(70,2850,1930,2950),'SAMPLE · NOT A DEVICE' if sample else 'LOGIN REQUIRED',48)
    return image


def enclosure_label(data, portal_base=None, sample=False):
    from PIL import Image,ImageDraw
    if portal_base and portal_base.rstrip('/') != REMOTE_ORIGIN:
        raise ValueError('Reprints must use the permanent commissioned origin '+REMOTE_ORIGIN)
    remote = data.get('remote_url') or unit_url(data['serial'])
    if remote != unit_url(data['serial']):
        raise ValueError('Permanent URL and enclosure serial do not match')
    image=Image.new('RGB',(2000,1100),'white');draw=ImageDraw.Draw(image)
    right=1310
    logo=Image.open(ROOT/'commissioning/assets/atlantis-bw.png').convert('RGBA');logo.thumbnail((right-80,180))
    draw.rounded_rectangle(((right-logo.width)//2-16,20,(right+logo.width)//2+16,230),radius=12,fill='black')
    image.paste(logo,((right-logo.width)//2,35),logo)
    fitted(draw,(30,255,right,360),'A-14329-MB00',74)
    fitted(draw,(30,385,right,540),'S/N '+data['serial'],100)
    fitted(draw,(30,560,right,660),'REMOTE ACCESS',78)
    fitted(draw,(30,675,right,790),'https://connect.atlantisllc.com',78)
    fitted(draw,(30,795,right,920),'/u/'+data['serial'],92)
    paste_qr(image,(1340,300,1980,940),remote)
    fitted(draw,(30,970,1970,1070),'SAMPLE · SERVICE NOT LIVE' if sample else 'LOGIN REQUIRED',54)
    return image


def print_windows(image, printer, copies=2, serial=''):
    if os.name!='nt':raise OSError('Windows printer required')
    if type(copies) is not int or not 1<=copies<=10:raise ValueError('Copies must be 1..10')
    from PIL import ImageWin
    import win32ui
    import win32con
    # Same driver/DC approach as the original LabelImage.print_image, retaining
    # the roll orientation. Fit uniformly so QR squares cannot be stretched.
    dc=win32ui.CreateDC();started=False
    try:
        dc.CreatePrinterDC(printer)
        width,height=dc.GetDeviceCaps(win32con.HORZRES),dc.GetDeviceCaps(win32con.VERTRES)
        scale=min(width/image.width,height/image.height)
        size=(round(image.width*scale),round(image.height*scale))
        box=((width-size[0])//2,(height-size[1])//2)
        dc.StartDoc('Atlantis MB00 '+serial);started=True
        printable=image.convert('RGB').copy();printable.putpixel((0,0),(0,0,0))
        for _ in range(copies):
            dc.StartPage()
            ImageWin.Dib(printable).draw(dc.GetHandleOutput(),(*box,box[0]+size[0],box[1]+size[1]))
            dc.EndPage()
        dc.EndDoc();started=False
    finally:
        if started:dc.AbortDoc()
        dc.DeleteDC()


def print_selected(setup, enclosure, kind, printer, copies, serial):
    if kind not in ('setup','enclosure'):
        raise ValueError('Choose setup or enclosure label')
    image = setup.rotate(90,expand=True) if kind=='setup' else enclosure
    print_windows(image,printer,copies,serial)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit-directory',type=Path,required=True)
    parser.add_argument('--verification',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True,help='New private label directory')
    parser.add_argument('--portal-base',help='Optional explicit confirmation of https://connect.atlantisllc.com; other origins are rejected')
    parser.add_argument('--print',dest='print_label',action='store_true',help='Submit setup label to the selected Windows printer')
    parser.add_argument('--print-kind',choices=('setup','enclosure'),default='setup',help='Select the private setup label or public permanent-address label')
    parser.add_argument('--printer',default=DEFAULT_PRINTER)
    parser.add_argument('--copies',type=int,default=2)
    args=parser.parse_args()
    data=verified_data(args.unit_directory,args.verification)
    setup=setup_label(data);enclosure=enclosure_label(data,args.portal_base)
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700);os.chmod(args.output,0o700)
    setup.save(args.output/'setup-private.png');os.chmod(args.output/'setup-private.png',0o600)
    enclosure.save(args.output/'enclosure-public.png')
    if args.print_label:
        print_selected(setup,enclosure,args.print_kind,args.printer,args.copies,data['serial'])
        print('Selected label submitted to Windows. Operator must confirm physical print and scan; no acceptance recorded automatically.')
    else:print('Created matching setup/enclosure label artwork. No print job submitted; keep the setup label private.')


if __name__=='__main__':main()
