"""Binary-format fixtures test the parser, not whether a kernel can execute.

The tool was also exercised against the official OpenWrt 25.12.6 HLK image;
its disabled I2C and inherited keys/LEDs correctly fail the MB00 carrier checks.
"""
import hashlib
import importlib.util
import json
import lzma
from pathlib import Path
import struct
import tempfile
import unittest
import zlib

TOOL = Path(__file__).resolve().parents[1] / 'tools/inspect_image.py'
SPEC = importlib.util.spec_from_file_location('inspect_image', TOOL)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def cstr(text):
    return text.encode() + b'\0'


def cell(*values):
    return struct.pack('>' + 'I' * len(values), *values)


def fdt(i2c='okay', extra_nodes=False, pin_function='i2c', firmware_offset=0x50000,
        board='hilink,hlk-7628n', conflicting_gpio=False):
    # FDT v17: real structure tokens, property strings, and phandle references.
    partitions = []
    for name, offset, size, ro in [('u-boot', 0, 0x30000, True),
                                   ('u-boot-env', 0x30000, 0x10000, True),
                                   ('factory', 0x40000, 0x10000, True),
                                   ('firmware', firmware_offset, 0x1fb0000, False)]:
        props = {'label': cstr(name), 'reg': cell(offset, size)}
        if ro:
            props['read-only'] = b''
        partitions.append(('partition@' + format(offset, 'x'), props, []))
    children = [
        ('palmbus@10000000', {}, [
            ('i2c@900', {'compatible': cstr('mediatek,mt7621-i2c'),
                         'status': cstr(i2c), 'pinctrl-0': cell(1)}, []),
            ('spi@b00', {}, [('flash@0', {}, [('partitions', {}, partitions)])]),
        ]),
        ('pinctrl', {}, [('i2c_pins', {'phandle': cell(1)}, [
            ('i2c', {'groups': cstr('i2c'), 'function': cstr(pin_function)}, []),
        ])]),
    ]
    if extra_nodes:
        children.extend([('keys', {'compatible': cstr('gpio-keys')}, []),
                         ('leds', {'compatible': cstr('gpio-leds')}, [])])
    if conflicting_gpio:
        children.append(('pinctrl_default', {'groups': cstr('i2c'), 'function': cstr('gpio')}, []))
    root = ('', {'compatible': cstr(board) + cstr('mediatek,mt7628an-soc')}, children)
    strings, names = bytearray(), {}
    structure = bytearray()

    def padded(data):
        return data + b'\0' * (-len(data) % 4)

    def node(record):
        name, props, children = record
        structure.extend(cell(1) + padded(cstr(name)))
        for key, value in props.items():
            if key not in names:
                names[key] = len(strings)
                strings.extend(cstr(key))
            structure.extend(cell(3, len(value), names[key]) + padded(value))
        for child in children:
            node(child)
        structure.extend(cell(2))

    node(root)
    structure.extend(cell(9))
    total = 56 + len(structure) + len(strings)
    header = cell(0xd00dfeed, total, 56, 56 + len(structure), 40, 17, 16, 0,
                  len(strings), len(structure))
    return header + b'\0' * 16 + structure + strings


def image_bytes(tree=None, arch=5, version='25.12.6', profile='hilink_hlk-7628n',
                bad_header_crc=False, bad_payload_crc=False, signature=False,
                trailing_kernel=b''):
    tree = tree if tree is not None else fdt()
    kernel = b'Binary parser fixture; not an executable kernel.\0' + tree + trailing_kernel
    payload = lzma.compress(kernel, format=lzma.FORMAT_ALONE)
    data_crc = zlib.crc32(payload) ^ int(bad_payload_crc)
    header = struct.pack('>7I4B32s', 0x27051956, 0, 0, len(payload),
                         0x80000000, 0x80000000, data_crc, 5, arch, 2, 3,
                         b'TEST FORMAT ONLY')
    header_crc = zlib.crc32(header) ^ int(bad_header_crc)
    header = header[:4] + cell(header_crc) + header[8:]
    # Only the superblock is needed for the scope of this inspector. No rootfs
    # contents are claimed to be valid or inspected.
    squashfs = struct.pack('<5I6H8Q', 0x73717368, 1, 0, 131072, 0,
                           4, 17, 0, 1, 4, 0, 0, 96, 0, 0, 0, 0, 0, 0)
    metadata = {'metadata_version': '1.1', 'compat_version': '1.0',
                'supported_devices': ['hilink,hlk-7628n'],
                'version': {'dist': 'OpenWrt', 'version': version, 'revision': 'fixture',
                            'target': 'ramips/mt76x8', 'board': profile}}
    payload_json = b'\0' * 8 + json.dumps(metadata).encode()
    image = header + payload + squashfs + payload_json
    image += struct.pack('>IIB3xI', 0x46577830, zlib.crc32(image) ^ 0xffffffff,
                         1, len(payload_json) + 16)
    if signature:
        image += b'fixture-signature-not-authenticated'
        image += struct.pack('>IIB3xI', 0x46577830, zlib.crc32(image) ^ 0xffffffff,
                             0, len(b'fixture-signature-not-authenticated') + 16)
    return image


class ImageInspectionTest(unittest.TestCase):
    def inspect_bytes(self, data, wrong_hash=False, manifest_release='v25.12.6'):
        with tempfile.TemporaryDirectory(dir=TOOL.parents[1]) as folder:
            image = Path(folder)/'fixture-sysupgrade.bin'
            image.write_bytes(data)
            manifest = {'board': 'A-14329-MB00', 'profile': 'hilink_hlk-7628n',
                        'source_revision': 'fixture-only',
                        'openwrt_release': manifest_release,
                        'artifacts': [{'file': image.name, 'bytes': len(data),
                                       'sha256': '0'*64 if wrong_hash else hashlib.sha256(data).hexdigest()}]}
            return MODULE.inspect(image, manifest, expected_version='25.12.6')

    def test_valid_binary_structure_reports_only_scoped_checks(self):
        report = self.inspect_bytes(image_bytes())
        self.assertTrue(report['carrier_checks_passed'])
        self.assertFalse(report['programming_authorization'])
        self.assertFalse(report['hardware_tested'])
        self.assertEqual(report['uimage']['architecture'], 'MIPS')
        self.assertEqual(report['openwrt_metadata']['version']['version'], '25.12.6')
        self.assertEqual(report['dtb']['partitions']['factory']['offset'], 0x40000)

    def test_upstream_carrier_omissions_are_reported(self):
        report = self.inspect_bytes(image_bytes(fdt(i2c='disabled', extra_nodes=True)))
        self.assertFalse(report['carrier_checks_passed'])
        self.assertEqual(len(report['failures']), 3)

    def test_i2c_pinmux_gpio_fails_even_when_controller_enabled(self):
        report = self.inspect_bytes(image_bytes(fdt(pin_function='gpio')))
        self.assertIn('I2C controller is not assigned its peripheral pin function', report['failures'])

    def test_conflicting_gpio_assignment_is_not_overlooked(self):
        report = self.inspect_bytes(image_bytes(fdt(conflicting_gpio=True)))
        self.assertIn('Device tree retains a conflicting GPIO assignment for the I2C pin group', report['failures'])

    def test_changed_partition_is_not_approved(self):
        report = self.inspect_bytes(image_bytes(fdt(firmware_offset=0x60000)))
        self.assertIn('Unexpected compiled flash partition: firmware', report['failures'])

    def test_manifest_hash_mismatch_rejected(self):
        with self.assertRaisesRegex(MODULE.InspectionError, 'SHA256'):
            self.inspect_bytes(image_bytes(), wrong_hash=True)

    def test_manifest_release_mismatch_or_missing_rejected(self):
        for release in ['v24.10.7', None]:
            with self.subTest(release=release):
                with self.assertRaisesRegex(MODULE.InspectionError, 'Manifest release'):
                    self.inspect_bytes(image_bytes(), manifest_release=release)

    def test_header_checksum_rejected(self):
        with self.assertRaisesRegex(MODULE.InspectionError, 'header CRC32'):
            self.inspect_bytes(image_bytes(bad_header_crc=True))

    def test_payload_checksum_rejected(self):
        with self.assertRaisesRegex(MODULE.InspectionError, 'payload CRC32'):
            self.inspect_bytes(image_bytes(bad_payload_crc=True))

    def test_wrong_architecture_rejected_with_valid_checksums(self):
        with self.assertRaisesRegex(MODULE.InspectionError, 'Linux/MIPS'):
            self.inspect_bytes(image_bytes(arch=2))

    def test_wrong_metadata_profile_rejected(self):
        with self.assertRaisesRegex(MODULE.InspectionError, 'target/profile'):
            self.inspect_bytes(image_bytes(profile='another_board'))

    def test_wrong_metadata_release_rejected(self):
        with self.assertRaisesRegex(MODULE.InspectionError, 'distribution/version'):
            self.inspect_bytes(image_bytes(version='24.10.7'))

    def test_wrong_device_tree_rejected(self):
        with self.assertRaisesRegex(MODULE.InspectionError, 'HLK-7628N device tree'):
            self.inspect_bytes(image_bytes(fdt(board='other,device')))

    def test_truncated_fdt_rejected(self):
        with self.assertRaisesRegex(MODULE.InspectionError, 'HLK-7628N device tree'):
            self.inspect_bytes(image_bytes(fdt()[:-8]))

    def test_dtb_must_be_appended_to_kernel(self):
        with self.assertRaisesRegex(MODULE.InspectionError, 'end of the kernel'):
            self.inspect_bytes(image_bytes(trailing_kernel=b'unexpected-data'))

    def test_metadata_crc_rejected(self):
        data = bytearray(image_bytes())
        data[-12] ^= 1
        with self.assertRaisesRegex(MODULE.InspectionError, 'whole-prefix CRC32'):
            self.inspect_bytes(data)

    def test_signature_chunk_is_parsed_but_not_authenticated(self):
        report = self.inspect_bytes(image_bytes(signature=True))
        self.assertEqual([c['type'] for c in report['fwtool_chunks']], [0, 1])
        self.assertIn('Manifest SHA256 is an integrity check, not a trusted signature.', report['limitations'])


if __name__ == '__main__':
    unittest.main()
