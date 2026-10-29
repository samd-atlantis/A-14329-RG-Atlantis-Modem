import importlib.util
import os
from pathlib import Path
import unittest

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
        self.assertEqual(a['ssid'], 'ATECH-TEST-0001')

    def test_bad_serial_rejected(self):
        with self.assertRaises(ValueError):
            provision.make_unit('bad/serial')


if __name__ == '__main__':
    unittest.main()
