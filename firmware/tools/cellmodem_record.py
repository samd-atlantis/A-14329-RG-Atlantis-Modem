"""Prepare private CellModemInput-compatible identity data, without SAP access.

The existing app's QR callback consumes exactly five semicolon-separated fields:
serial, IMEI, LAN MAC, ignored fourth field, ignored fifth field. It strips the
first colon from each of the first three fields. This is not a portal URL QR.
"""
import argparse
import json
import os
from pathlib import Path
import re

from commission_labels import verified_data, paste_qr, fitted


def scan_payload(serial, imei, lan_mac):
    if not re.fullmatch(r'[A-Za-z0-9-]{1,24}',serial):raise ValueError('Invalid enclosure serial')
    if not re.fullmatch(r'[0-9]{15}',imei):raise ValueError('Scan the actual 15-digit cellular-card IMEI')
    mac=lan_mac.replace(':','').upper()
    if not re.fullmatch(r'[0-9A-F]{12}',mac) or int(mac[:2],16)&1 or mac=='000000000000':
        raise ValueError('Invalid captured LAN MAC')
    return f'S/N:{serial};IMEI:{imei};MAC:{mac};MODEL:A-14329-MB00;'


def create(folder, verification, identifiers, output):
    data=verified_data(folder,verification)
    readback=json.loads(Path(verification).read_text())
    ids=json.loads(Path(identifiers).read_text())
    lan=readback.get('lan_mac')
    if not lan:raise ValueError('Capture the actual LAN MAC with the updated collect-device.sh first')
    imei=ids.get('imei','')
    if not isinstance(imei,str):raise ValueError('IMEI must be a scanned string')
    payload=scan_payload(data['serial'],imei,lan)
    iccid,apn=ids.get('iccid',''),ids.get('apn','')
    if not isinstance(iccid,str) or iccid and not re.fullmatch(r'[0-9]{18,22}',iccid):
        raise ValueError('Invalid scanned physical-SIM ICCID')
    if not isinstance(apn,str) or len(apn)>100 or any(ord(c)<32 for c in apn):raise ValueError('Invalid APN')
    draft={'schema':'mb00-cellmodeminput-draft-1','status':'REVIEW_REQUIRED_NO_SAP_WRITE',
        'serial':data['serial'],'remote_url':data['remote_url'],'unit_record_sha256':readback['unit_sha256'],
        'sap_fields':{'U_ModSerNum':data['serial'],'U_ModIMEI':imei,'U_ModLanMac':lan.replace(':',''),
            'U_ModManu':'Atlantis','U_ModModNum':'A-14329-MB00','U_ModAdminPW':data['admin_password'],
            'U_ModWifiPW':data['wifi_password'],'U_ModAPN':apn,'U_SimICCID':iccid},
        'scan_payload':payload,
        'unresolved':['customer/order/facility assignment','SIM activation and actual data connection',
                      'four-controller record mapping; existing CellModemInput has one controller field set'],
        'hardware_acceptance_complete':False,'production_approved':False}
    output=Path(output);output.mkdir(parents=True,exist_ok=False,mode=0o700);os.chmod(output,0o700)
    with (output/'cellmodem-draft-private.json').open('x') as file:
        os.chmod(file.name,0o600);json.dump(draft,file,indent=2);file.write('\n')
    (output/'identity-scan.txt').write_text(payload+'\n',encoding='utf-8')
    from PIL import Image,ImageDraw
    image=Image.new('RGB',(2000,1200),'white');draw=ImageDraw.Draw(image)
    fitted(draw,(50,35,1950,180),'ATLANTIS · A-14329-MB00',90)
    fitted(draw,(50,200,1240,390),'S/N '+data['serial'],100)
    fitted(draw,(50,410,1240,560),'IMEI '+imei,72)
    fitted(draw,(50,590,1240,740),'LAN '+lan,68)
    fitted(draw,(50,850,1240,1040),'RECORD ENTRY',70)
    paste_qr(image,(1260,240,1970,950),payload)
    image.save(output/'cellmodem-identity-scan.png')
    return draft


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit-directory',type=Path,required=True)
    parser.add_argument('--verification',type=Path,required=True)
    parser.add_argument('--identifiers',type=Path,required=True,help='Private scanned imei, optional iccid/apn JSON')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    create(args.unit_directory,args.verification,args.identifiers,args.output)
    print('Created private review draft and identity-scan artwork. No SAP, SIM-provider or customer-system requests made.')


if __name__=='__main__':main()
