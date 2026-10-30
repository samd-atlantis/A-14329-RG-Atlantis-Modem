import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS=Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0,str(TOOLS))
import commission
import commission_labels as labels

AVAILABLE=all(importlib.util.find_spec(m) for m in ('PIL','qrcode','zxingcpp'))


@unittest.skipUnless(AVAILABLE,'Install firmware/commissioning/requirements-test.txt')
class LabelTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        if os.name=='nt':os.environ['PATH']=r'C:\Program Files\Git\usr\bin'+os.pathsep+os.environ['PATH']
        self.registry=self.root/'fleet.sqlite3'
        self.folder=commission.prepare(self.registry,self.root/'units','Test operator',prefix='TEST26')
        self.probe=self.root/'probe.json'
        self.probe.write_text(json.dumps({'schema':'mb00-device-probe-1','board_name':'hilink,hlk-7628n',
            'distribution':'OpenWrt','provisioned':'1','serial':self.folder.name,
            'wifi_mac':'00:11:22:33:A1:B2','ssid':'Atlantis-A1B2'}))
        self.verification=self.folder/'readback.json'
        commission.verify(self.registry,self.folder/'unit.json',self.probe,self.folder.name,self.verification)

    def tearDown(self):self.temp.cleanup()

    def test_setup_labels_decode_exact_verified_wifi_and_https_on_rotated_canvas(self):
        import zxingcpp
        data=labels.verified_data(self.folder,self.verification)
        image=labels.setup_label(data)
        self.assertEqual(image.size,(2000,3000))
        codes={r.text for r in zxingcpp.read_barcodes(image)}
        self.assertEqual(codes,{labels.wifi_payload('Atlantis-A1B2',data['wifi_password']),'https://10.0.100.7'})
        rotated=image.rotate(90,expand=True)
        self.assertEqual(rotated.size,(3000,2000))
        self.assertEqual({r.text for r in zxingcpp.read_barcodes(rotated)},codes)

    def test_public_identity_has_only_permanent_url_and_no_credential_qr(self):
        import zxingcpp
        data=labels.verified_data(self.folder,self.verification)
        self.assertFalse(zxingcpp.read_barcodes(labels.enclosure_label(data)))
        image=labels.enclosure_label(data,'https://portal.example.test')
        self.assertEqual([r.text for r in zxingcpp.read_barcodes(image)],['https://portal.example.test/u/'+data['serial']])
        for url in ('http://portal.example.test','https://user:pass@portal.example.test','https://portal.example.test/?key=secret'):
            with self.subTest(url=url),self.assertRaises(ValueError):labels.enclosure_label(data,url)

    def test_labels_reject_pending_wrong_unit_ssid_and_credential_sheet(self):
        record=json.loads(self.verification.read_text())
        for change in ({'identity_status':'PREPARED_NOT_VERIFIED'},{'serial':'wrong'},{'ssid':'Atlantis-AUTO'},{'unit_sha256':'0'*64}):
            self.verification.write_text(json.dumps({**record,**change}))
            with self.subTest(change=change),self.assertRaises(ValueError):labels.verified_data(self.folder,self.verification)
        self.verification.write_text(json.dumps(record))
        path=self.folder/'credentials.csv'
        text=path.read_text()
        unit=json.loads((self.folder/'unit.json').read_text())
        text=text.replace(unit['wifi_password'],'wrong-password')
        path.write_text(text)
        with self.assertRaisesRegex(ValueError,'credential sheet'):labels.verified_data(self.folder,self.verification)

    def test_verify_renders_without_printing_unless_operator_selects_print_labels(self):
        # New evidence filenames allow re-reading this same unit without replacing
        # its permanent identity. The printer is mocked: no real job is submitted.
        for do_print in (False,True):
            evidence=self.folder/('second-readback.json' if do_print else 'first-readback.json')
            output=self.folder/('printed-labels' if do_print else 'preview-labels')
            argv=['commission.py','verify','--registry',str(self.registry),'--unit',str(self.folder/'unit.json'),
                '--probe',str(self.probe),'--label-serial',self.folder.name,'--output',str(evidence),'--labels-dir',str(output)]
            if do_print:argv+=['--print-labels']
            with patch.object(sys,'argv',argv),patch('commission_labels.print_windows') as printer:
                commission.main()
            self.assertTrue((output/'setup-private.png').is_file())
            if do_print:
                self.assertEqual(printer.call_count,1)
                self.assertEqual(printer.call_args.args[1:],(labels.DEFAULT_PRINTER,2,self.folder.name))
            else:printer.assert_not_called()


if __name__=='__main__':unittest.main()
