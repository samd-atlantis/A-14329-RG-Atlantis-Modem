import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
from make_factory_bundle import create


class FactoryBundleTest(unittest.TestCase):
    def test_private_bundle_only_contains_this_units_record(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            unit = {'serial': 'TEST-0001', 'ssid': 'ATECH-TEST-0001',
                    'wifi_password': 'a' * 24, 'root_hash': '$6$salt$' + 'A' * 86}
            (root/'unit.json').write_text(json.dumps(unit))
            image = root/'test-sysupgrade.bin'
            image.write_bytes(b'fixture-image')
            manifest = {'board': 'A-14329-MB00', 'profile': 'hilink_hlk-7628n',
                        'mode': 'unprovisioned-validation', 'source_revision': 'test',
                        'artifacts': [{'file': image.name, 'bytes': image.stat().st_size,
                                       'sha256': hashlib.sha256(image.read_bytes()).hexdigest()}]}
            (root/'manifest.json').write_text(json.dumps(manifest))
            output = root/'private'/'TEST-0001'
            result = create(root/'unit.json', root/'manifest.json', image, output)
            self.assertEqual(result['unit_serial'], unit['serial'])
            with tarfile.open(output/'unit-config.tar.gz') as archive:
                members = archive.getmembers()
                self.assertEqual([m.name for m in members], ['etc/gateway/unit.json'])
                self.assertEqual(members[0].mode, 0o600)
                self.assertEqual(members[0].uid, 0)
                self.assertEqual(json.load(archive.extractfile(members[0])), unit)
            self.assertNotIn(unit['wifi_password'], (output/'bundle.json').read_text())
            with self.assertRaises(FileExistsError):
                create(root/'unit.json', root/'manifest.json', image, output)
            image.write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                create(root/'unit.json', root/'manifest.json', image, root/'rejected')
            self.assertFalse((root/'rejected').exists())


if __name__ == '__main__':
    unittest.main()
