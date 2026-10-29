"""Inspect an MB00 legacy-uImage sysupgrade binary without flashing or executing it.

Standard Python only. Checks the manifest SHA256, uImage CRCs, fwtool CRC/metadata,
and the actual appended DTB after bounded LZMA decompression. This does not inspect
rootfs files, authenticate a signing key, prove source provenance, or test hardware.
The manifest itself must come from the trusted build being reviewed.

Format references:
https://github.com/openwrt/openwrt/blob/v25.12.6/target/linux/ramips/image/Makefile
https://github.com/openwrt/openwrt/blob/v25.12.6/include/image-commands.mk
https://github.com/openwrt/fwtool/blob/8f7fe925ca205c8e8e2d0d1b16218c1e148d5173/fwimage.h
https://github.com/openwrt/fwtool/blob/8f7fe925ca205c8e8e2d0d1b16218c1e148d5173/fwtool.c
https://devicetree-specification.readthedocs.io/en/stable/flattened-format.html
"""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import struct
import zlib

UIMAGE_MAGIC = 0x27051956
FDT_MAGIC = b'\xd0\x0d\xfe\xed'
FWTOOL_MAGIC = 0x46577830
MAX_IMAGE = 32 * 1024 * 1024
MAX_KERNEL = 64 * 1024 * 1024
PROFILE = 'hilink_hlk-7628n'
COMPATIBLE = 'hilink,hlk-7628n'


class InspectionError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InspectionError(message)


def cstring(data, offset, limit):
    require(0 <= offset < limit <= len(data), 'String offset is outside its block')
    end = data.find(b'\0', offset, limit)
    require(end >= 0, 'Unterminated FDT string')
    try:
        return data[offset:end].decode('ascii'), end + 1
    except UnicodeDecodeError as error:
        raise InspectionError('Non-ASCII FDT node/property name') from error


def string_list(value):
    if not value:
        return []
    require(value.endswith(b'\0'), 'Unterminated FDT string property')
    try:
        return value[:-1].decode('utf-8').split('\0')
    except UnicodeDecodeError as error:
        raise InspectionError('Invalid UTF-8 FDT property') from error


def cells(value):
    require(len(value) % 4 == 0, 'Invalid FDT cell property length')
    return struct.unpack('>' + 'I' * (len(value) // 4), value)


def parse_fdt(data):
    require(len(data) >= 40, 'Truncated FDT header')
    magic, total, structure, strings, reserve, version, compatible, cpu, strings_size, structure_size = struct.unpack_from('>10I', data)
    require(magic == int.from_bytes(FDT_MAGIC, 'big'), 'Not a flattened device tree')
    require(40 <= total <= len(data) and total <= 4 * 1024 * 1024, 'Invalid FDT total size')
    require(version == 17 and compatible <= 17, 'Unsupported FDT version')
    require(40 <= structure < total and structure % 4 == 0 and structure_size <= total - structure, 'Invalid FDT structure bounds')
    require(40 <= strings < total and strings_size <= total - strings, 'Invalid FDT strings bounds')
    require(structure + structure_size <= strings or strings + strings_size <= structure, 'Overlapping FDT blocks')
    require(40 <= reserve <= total - 16 and reserve % 8 == 0, 'Invalid FDT reservation table')
    nodes, stack = {}, []
    at, stop = structure, structure + structure_size
    ended = False
    while at + 4 <= stop:
        token, = struct.unpack_from('>I', data, at)
        at += 4
        if token == 1:  # FDT_BEGIN_NODE
            name, at = cstring(data, at, stop)
            at = (at + 3) & ~3
            require('/' not in name, 'Invalid FDT node name')
            if not stack:
                require(name == '' and not nodes, 'Invalid or duplicate FDT root')
                path = '/'
            else:
                require(name != '', 'Empty child node name')
                path = stack[-1].rstrip('/') + '/' + name
            require(path not in nodes, 'Duplicate FDT node')
            nodes[path] = {}
            stack.append(path)
        elif token == 2:  # FDT_END_NODE
            require(bool(stack), 'Unbalanced FDT end node')
            stack.pop()
        elif token == 3:  # FDT_PROP
            require(bool(stack) and at + 8 <= stop, 'Truncated FDT property header')
            length, name_offset = struct.unpack_from('>II', data, at)
            at += 8
            require(length <= stop - at and name_offset < strings_size, 'FDT property exceeds block bounds')
            name, _ = cstring(data, strings + name_offset, strings + strings_size)
            require(name not in nodes[stack[-1]], 'Duplicate FDT property')
            nodes[stack[-1]][name] = data[at:at + length]
            at = (at + length + 3) & ~3
        elif token == 4:  # FDT_NOP
            continue
        elif token == 9:  # FDT_END
            require(not stack and bool(nodes), 'Unbalanced or empty FDT')
            ended = True
            break
        else:
            raise InspectionError('Unknown FDT structure token')
    require(ended, 'FDT has no end token')
    return nodes, total


def appended_dtb(kernel):
    matches, offset = [], 0
    while True:
        offset = kernel.find(FDT_MAGIC, offset)
        if offset < 0:
            break
        try:
            nodes, total = parse_fdt(kernel[offset:])
            if COMPATIBLE in string_list(nodes['/'].get('compatible', b'')):
                matches.append((offset, nodes, total))
        except (InspectionError, KeyError):
            pass  # Kernel machine code can contain the FDT magic as a constant.
        offset += 4
    require(len(matches) == 1, 'Expected exactly one valid appended HLK-7628N device tree')
    offset, nodes, total = matches[0]
    require(offset + total == len(kernel), 'HLK device tree is not at the end of the kernel payload')
    return nodes, {'offset_in_decompressed_kernel': offset, 'bytes': total}


def read_uimage(data):
    require(len(data) >= 64, 'Truncated uImage header')
    values = struct.unpack_from('>7I4B32s', data)
    magic, header_crc, timestamp, size, load, entry, payload_crc, os_id, arch, kind, compression, name = values
    require(magic == UIMAGE_MAGIC, 'Unsupported image format; expected legacy uImage, not FIT or a flash dump')
    header = data[:4] + b'\0' * 4 + data[8:64]
    require(zlib.crc32(header) == header_crc, 'uImage header CRC32 mismatch')
    require((os_id, arch, kind, compression) == (5, 5, 2, 3), 'Expected Linux/MIPS/kernel/LZMA uImage')
    require(0 < size <= len(data) - 64, 'uImage payload length exceeds the file')
    payload = data[64:64 + size]
    require(zlib.crc32(payload) == payload_crc, 'uImage payload CRC32 mismatch')
    try:
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE, memlimit=MAX_KERNEL)
        kernel = decoder.decompress(payload, max_length=MAX_KERNEL + 1)
    except lzma.LZMAError as error:
        raise InspectionError('Invalid or excessive LZMA kernel stream') from error
    require(len(kernel) <= MAX_KERNEL and decoder.eof and not decoder.unused_data, 'Truncated, oversized or concatenated LZMA kernel stream')
    return kernel, 64 + size, {
        'architecture': 'MIPS', 'os': 'Linux', 'type': 'kernel', 'compression': 'LZMA',
        'name': name.rstrip(b'\0').decode('ascii', errors='replace'),
        'payload_bytes': size, 'decompressed_bytes': len(kernel),
        'load_address': hex(load), 'entry_point': hex(entry), 'timestamp': timestamp,
        'header_crc32_verified': True, 'payload_crc32_verified': True,
    }


def read_metadata(data):
    end, chunks = len(data), []
    for _ in range(4):
        require(end >= 16, 'Missing fwtool metadata trailer')
        magic, crc, kind, size = struct.unpack_from('>IIB3xI', data, end - 16)
        require(magic == FWTOOL_MAGIC, 'Missing fwtool metadata trailer')
        require(16 <= size <= min(end, 32 * 1024), 'Invalid fwtool chunk length')
        # fwtool uses initial 0xffffffff and no final XOR; zlib applies that XOR.
        require((zlib.crc32(data[:end - 16]) ^ 0xffffffff) == crc, 'fwtool whole-prefix CRC32 mismatch')
        start = end - size
        chunks.append({'type': kind, 'bytes': size, 'crc32_verified': True})
        if kind == 1:
            require(size >= 24 and data[start:start + 8] == b'\0' * 8, 'Unsupported fwtool metadata header')
            try:
                metadata = json.loads(data[start + 8:end - 16])
            except (ValueError, UnicodeDecodeError) as error:
                raise InspectionError('Invalid fwtool JSON metadata') from error
            require(isinstance(metadata, dict), 'fwtool metadata must be an object')
            return metadata, start, chunks
        require(kind == 0, 'Unsupported fwtool trailer type')
        end = start
    raise InspectionError('Too many fwtool signature chunks')


def inspect(image, manifest, expected_version=None):
    if expected_version is None:
        expected_version = json.loads((Path(__file__).resolve().parents[1] / 'build-lock.json').read_text())['release'].removeprefix('v')
    require(manifest.get('board') == 'A-14329-MB00' and manifest.get('profile') == PROFILE,
            'Manifest is for a different board or profile')
    require(manifest.get('openwrt_release') == 'v' + expected_version,
            'Manifest release does not match the expected OpenWrt release')
    require(0 < image.stat().st_size <= MAX_IMAGE, 'Image is empty or exceeds 32 MB')
    data = image.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    records = [a for a in manifest.get('artifacts', []) if a.get('file') == image.name]
    require(len(records) == 1 and records[0].get('bytes') == len(data) and records[0].get('sha256') == digest,
            'Image does not match the manifest size/SHA256')
    metadata, body_end, chunks = read_metadata(data)
    version = metadata.get('version', {})
    require(isinstance(version, dict), 'Missing image version metadata')
    supported = metadata.get('supported_devices', [])
    require(isinstance(supported, list) and COMPATIBLE in supported, 'Image metadata does not support HLK-7628N')
    require(version.get('target') == 'ramips/mt76x8' and version.get('board') == PROFILE,
            'Image metadata has the wrong target/profile')
    require(version.get('dist') == 'OpenWrt' and version.get('version') == expected_version,
            'Image metadata has the wrong OpenWrt distribution/version')
    kernel, kernel_end, header = read_uimage(data[:body_end])
    nodes, dtb = appended_dtb(kernel)
    require(kernel_end + 96 <= body_end and data[kernel_end:kernel_end + 4] == b'hsqs',
            'Expected SquashFS immediately after the uImage kernel')
    squashfs = struct.unpack_from('<5I6H8Q', data, kernel_end)
    require(squashfs[9:11] == (4, 0), 'Expected SquashFS version 4.0')
    require(96 <= squashfs[12] <= body_end - kernel_end, 'SquashFS bytes-used exceeds image body')
    failures = []
    i2c_nodes = [(p, v) for p, v in nodes.items()
                 if 'mediatek,mt7621-i2c' in string_list(v.get('compatible', b''))]
    require(len(i2c_nodes) == 1, 'Expected exactly one MT7628 I2C controller')
    i2c_path, i2c = i2c_nodes[0]
    status = string_list(i2c.get('status', b'okay\0'))
    if status not in (['okay'], ['ok']):
        failures.append('Carrier I2C controller is not enabled')
    handles = {}
    for path, props in nodes.items():
        if 'phandle' in props:
            handle = cells(props['phandle'])
            require(len(handle) == 1 and handle[0] not in (0, 0xffffffff) and handle[0] not in handles,
                    'Invalid or duplicate FDT phandle')
            handles[handle[0]] = (path, props)
    pin_groups = []
    for handle in cells(i2c.get('pinctrl-0', b'')):
        require(handle in handles, 'I2C pinctrl references an unknown phandle')
        parent, _ = handles[handle]
        pin_groups += [v for p, v in nodes.items() if p == parent or p.startswith(parent + '/')]
    if not any(string_list(p.get('groups', b'')) == ['i2c'] and
               string_list(p.get('function', b'')) == ['i2c'] for p in pin_groups):
        failures.append('I2C controller is not assigned its peripheral pin function')
    if any('i2c' in string_list(p.get('groups', b'')) and
           string_list(p.get('function', b'')) == ['gpio'] for p in nodes.values()):
        failures.append('Device tree retains a conflicting GPIO assignment for the I2C pin group')
    if '/keys' in nodes:
        failures.append('Inherited GPIO38 reset-key node is still present')
    if '/leds' in nodes:
        failures.append('Inherited GPIO44 LED node is still present')
    partitions = {}
    for path, props in nodes.items():
        if 'label' in props and 'reg' in props and '/partitions/' in path:
            label = string_list(props['label'])
            reg = cells(props['reg'])
            if len(label) == 1 and len(reg) == 2:
                partitions[label[0]] = {'offset': reg[0], 'bytes': reg[1], 'read_only': 'read-only' in props}
    expected = {'u-boot': (0, 0x30000), 'u-boot-env': (0x30000, 0x10000),
                'factory': (0x40000, 0x10000), 'firmware': (0x50000, 0x1fb0000)}
    for label, (offset, length) in expected.items():
        part = partitions.get(label, {})
        if (part.get('offset'), part.get('bytes')) != (offset, length):
            failures.append('Unexpected compiled flash partition: ' + label)
        if label != 'firmware' and not part.get('read_only'):
            failures.append('Boot/calibration partition is not read-only: ' + label)
    return {
        'schema': 'mb00-image-inspection-1', 'file': image.name, 'bytes': len(data),
        'sha256': digest, 'manifest_sha256_verified': True,
        'manifest_source_revision': manifest.get('source_revision'),
        'openwrt_metadata': metadata, 'fwtool_chunks': chunks, 'uimage': header,
        'dtb': dict(dtb, compatible=string_list(nodes['/'].get('compatible', b'')),
                    i2c_node=i2c_path, i2c_status=status, keys_present='/keys' in nodes,
                    leds_present='/leds' in nodes, partitions=partitions),
        'squashfs': {'offset': kernel_end, 'bytes_used': squashfs[12], 'compression_id': squashfs[5]},
        'carrier_checks_passed': not failures, 'failures': failures,
        'programming_authorization': False, 'hardware_tested': False,
        'limitations': ['Manifest SHA256 is an integrity check, not a trusted signature.',
                        'Source revision is supplied by the manifest, not proven from machine code.',
                        'Rootfs file contents and package behavior are not inspected.',
                        'Actual flash size, bootloader compatibility and hardware operation are not tested.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--expected-version', help='Default: release from firmware/build-lock.json')
    args = parser.parse_args()
    if args.output and args.output.resolve() in (args.image.resolve(), args.manifest.resolve()):
        parser.error('Report output must not overwrite the image or manifest')
    try:
        report = inspect(args.image, json.loads(args.manifest.read_text()), args.expected_version)
    except (InspectionError, OSError, ValueError) as error:
        report = {'schema': 'mb00-image-inspection-1', 'carrier_checks_passed': False,
                  'failures': [str(error)], 'programming_authorization': False}
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.write_text(text, newline='\n')
    print(text, end='')
    raise SystemExit(0 if report['carrier_checks_passed'] else 1)


if __name__ == '__main__':
    main()
