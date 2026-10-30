import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))
import commission
from cellmodem_record import create,scan_payload

AVAILABLE=all(importlib.util.find_spec(m) for m in ('PIL','qrcode','zxingcpp'))


@unittest.skipUnless(AVAILABLE,'Install firmware/commissioning/requirements-test.txt')
class CellRecordTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        if os.name=='nt':os.environ['PATH']=r'C:\Program Files\Git\usr\bin'+os.pathsep+os.environ['PATH']
        self.registry=self.root/'fleet.sqlite3'
        self.folder=commission.prepare(self.registry,self.root/'units','Test operator',prefix='TEST26')
        self.probe=self.root/'probe.json'
        self.probe.write_text(json.dumps({'schema':'mb00-device-probe-1','board_name':'hilink,hlk-7628n',
            'distribution':'OpenWrt','provisioned':'1','serial':self.folder.name,
            'wifi_mac':'00:11:22:33:A1:B2','ssid':'Atlantis-A1B2','lan_mac':'00:11:22:33:CC:DD'}))
        self.verification=self.folder/'readback.json'
        commission.verify(self.registry,self.folder/'unit.json',self.probe,self.folder.name,self.verification)
        self.ids=self.root/'identifiers.json'
        self.ids.write_text(json.dumps({'imei':'490154203237518','iccid':'89010000000000000001','apn':'fixture.apn'}))

    def tearDown(self):self.temp.cleanup()

    def test_decoded_scan_matches_the_existing_app_positional_parser(self):
        import zxingcpp
        from PIL import Image
        output=self.folder/'cell-input'
        draft=create(self.folder,self.verification,self.ids,output)
        payload=zxingcpp.read_barcodes(Image.open(output/'cellmodem-identity-scan.png'))[0].text
        fields=payload.split(';')
        # Actual callback: count(';') >= 4, len(split(';')) == 5,
        # then first colon removed from slots 0,1,2. Last two slots ignored.
        self.assertEqual(len(fields),5)
        serial,imei,lan=(f.partition(':')[2] if ':' in f else f for f in fields[:3])
        self.assertEqual((serial,imei,lan),(self.folder.name,'490154203237518','00112233CCDD'))
        self.assertNotEqual(lan,'00112233A1B2')
        self.assertEqual(draft['sap_fields']['U_ModSerNum'],self.folder.name)
        self.assertEqual(draft['sap_fields']['U_ModLanMac'],lan)
        self.assertEqual(draft['status'],'REVIEW_REQUIRED_NO_SAP_WRITE')
        self.assertNotIn(draft['sap_fields']['U_ModAdminPW'],payload)
        self.assertNotIn(draft['sap_fields']['U_ModWifiPW'],payload)

    def test_missing_lan_mac_cannot_be_substituted_with_wifi_mac(self):
        record=json.loads(self.verification.read_text());record.pop('lan_mac')
        self.verification.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'actual LAN MAC'):
            create(self.folder,self.verification,self.ids,self.folder/'cell-input')
        self.assertFalse((self.folder/'cell-input').exists())

    def test_bad_identifiers_cannot_change_the_legacy_parser_shape(self):
        for serial,imei,mac in [('bad;serial','490154203237518','00:11:22:33:CC:DD'),
                ('TEST-1','not-an-imei','00:11:22:33:CC:DD'),('TEST-1','490154203237518','01:11:22:33:CC:DD')]:
            with self.subTest(serial=serial,imei=imei,mac=mac),self.assertRaises(ValueError):scan_payload(serial,imei,mac)


if __name__=='__main__':unittest.main()
