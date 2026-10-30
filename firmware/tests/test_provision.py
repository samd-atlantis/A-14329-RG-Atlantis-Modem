import importlib.util
import os
from pathlib import Path
import unittest
import tempfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('provision', ROOT/'tools/provision.py')
provision = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provision)


class ProvisionTest(unittest.TestCase):
    def test_unique_credentials_and_no_plain_admin_on_unit(self):
        # OpenSSL is preinstalled with Git for Windows on this host.
        if os.name == 'nt':
            os.environ['PATH'] = r'C:\Program Files\Git\usr\bin' + os.pathsep + os.environ['PATH']
        a, password_a = provision.make_unit('TEST-0001')
        b, password_b = provision.make_unit('TEST-0002')
        self.assertNotEqual(a['wifi_password'], b['wifi_password'])
        self.assertNotEqual(password_a, password_b)
        self.assertNotIn(password_a, str(a))
        self.assertTrue(a['root_hash'].startswith('$6$'))
        self.assertEqual(a['ssid'], 'Atlantis-AUTO')

    def test_explicit_mac_generates_label_ssid_and_rejects_bad_macs(self):
        if os.name == 'nt':
            os.environ['PATH'] = r'C:\Program Files\Git\usr\bin' + os.pathsep + os.environ['PATH']
        unit, _ = provision.make_unit('TEST-0001', '00:11:22:33:a1:b2')
        self.assertEqual(unit['ssid'], 'Atlantis-A1B2')
        for mac in ('00:00:00:00:00:00', '01:11:22:33:A1:B2', 'invalid'):
            with self.subTest(mac=mac), self.assertRaises(ValueError):
                provision.make_unit('TEST-0001', mac)

    def test_bad_serial_rejected(self):
        with self.assertRaises(ValueError):
            provision.make_unit('bad/serial')

    def test_reserved_serial_file_rejects_duplicates_and_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'serials.txt'
            path.write_text('FACTORY-001\nFACTORY-002\n')
            self.assertEqual(provision.serial_batch(path), ['FACTORY-001', 'FACTORY-002'])
            for value in ('FACTORY-001\nfactory-001\n', '../bad\n', '', '\n', 'valid\n\n'):
                path.write_text(value)
                with self.subTest(value=value), self.assertRaises(ValueError):
                    provision.serial_batch(path)


if __name__ == '__main__':
    unittest.main()
