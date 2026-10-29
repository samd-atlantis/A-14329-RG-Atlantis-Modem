import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'


def module(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / (name + '.py'))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


build = module('build_support')
preflight = module('preflight')


class BuildToolsTest(unittest.TestCase):
    def test_unit_validation_rejects_injection_or_mismatched_identity(self):
        unit = dict(serial='TEST-0001', ssid='ATECH-TEST-0001',
                    wifi_password='a' * 24, root_hash='$6$salt$' + 'A' * 86)
        self.assertEqual(build.validate_unit(unit), 'TEST-0001')
        for key, value in [('serial', '../escape'), ('ssid', 'different'),
                           ('root_hash', '$6$salt$bad\nroot::0'),
                           ('wifi_password', 'shared-password'), ('serial', 1)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                build.validate_unit({**unit, key: value})

    def test_preflight_rejects_wrong_board_layout_unit_or_corrupt_image(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'test-sysupgrade.bin'
            image.write_bytes(b'not-a-real-image-test-fixture')
            probe = {'schema': 'mb00-device-probe-1', 'board_name': 'hilink,hlk-7628n',
                     'distribution': 'OpenWrt', 'provisioned': '1', 'serial': 'TEST-0001',
                     'mtd': '\n'.join(['mtd0: 00030000 00010000 "u-boot"',
                                       'mtd1: 00010000 00010000 "u-boot-env"',
                                       'mtd2: 00010000 00010000 "factory"',
                                       'mtd3: 01fb0000 00010000 "firmware"'])}
            manifest = {'board': 'A-14329-MB00', 'profile': 'hilink_hlk-7628n',
                        'mode': 'private-unit-development', 'unit_serial': 'TEST-0001',
                        'openwrt_release': build.lock()['release'],
                        'requires_confirmed_flash_bytes': 33554432,
                        'artifacts': [{'file': image.name, 'bytes': image.stat().st_size,
                                       'sha256': hashlib.sha256(image.read_bytes()).hexdigest()}]}
            self.assertEqual(preflight.assess(probe, manifest, image), [])
            for bad in [{**probe, 'board_name': 'different'},
                        {**probe, 'mtd': probe['mtd'].replace('01fb0000', '00fb0000')},
                        {**probe, 'serial': 'OTHER-0001'}]:
                self.assertTrue(preflight.assess(bad, manifest, image))
            for bad in [{**manifest, 'mode': 'unprovisioned-validation'},
                        {**manifest, 'openwrt_release': 'v24.10.7'},
                        {**manifest, 'openwrt_release': None},
                        {**manifest, 'unit_serial': ''}]:
                self.assertTrue(preflight.assess(probe, bad, image))
            image.write_bytes(b'corrupted')
            self.assertTrue(preflight.assess(probe, manifest, image))


if __name__ == '__main__':
    unittest.main()
