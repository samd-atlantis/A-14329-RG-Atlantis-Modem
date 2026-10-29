"""Read an MB00 validation image's actual SquashFS using an existing 7-Zip.

Does not mount, execute, flash, or extract filesystem paths. Only a bounded
SquashFS slice, file inventory and JSON report are written below firmware/dist.
The reviewed source package is compared byte-for-byte (source CRLF normalized).
This is a static content check, not proof that first boot or hardware works.
Private per-unit images are deliberately outside this tool's scope.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile

from inspect_image import inspect, InspectionError, require

FIRMWARE = Path(__file__).resolve().parents[1]
PACKAGE = FIRMWARE / 'package/atech-gateway/files'
DIST = FIRMWARE / 'dist'
REQUIRED_PACKAGES = (
    'atech-gateway', 'luci-ssl', 'luci-proto-qmi', 'uqmi', 'i2c-tools', 'lrzsz',
    'kmod-i2c-mt7628', 'kmod-i2c-dev', 'kmod-usb-net-qmi-wwan',
    'kmod-usb-serial-option', 'kmod-usb2', 'wpad-basic-mbedtls',
    'rpcd', 'rpcd-mod-file', 'rpcd-mod-luci', 'jsonfilter', 'px5g-mbedtls',
    'firewall4', 'dnsmasq', 'dropbear', 'uhttpd', 'uhttpd-mod-ubus',
)
REQUIRED_MODULES = ('i2c-mt7621.ko', 'i2c-dev.ko', 'qmi_wwan.ko', 'cdc-wdm.ko',
                    'usbnet.ko', 'option.ko', 'usb_wwan.ko', 'usbserial.ko',
                    'ehci-hcd.ko', 'ehci-platform.ko', 'mt7603e.ko', 'mt76.ko')
REQUIRED_AUTOLOAD = ('i2c-mt7621', 'i2c-dev', 'qmi_wwan', 'option',
                     'ehci-platform', 'mt7603e')
REQUIRED_EXECUTABLES = (
    'sbin/uqmi', 'usr/sbin/i2cget', 'usr/sbin/i2cset', 'usr/bin/lrz',
    'sbin/rpcd', 'sbin/netifd', 'sbin/uci', 'bin/ubus', 'usr/bin/jsonfilter',
    'usr/sbin/uhttpd', 'usr/sbin/dropbear', 'usr/sbin/hostapd',
)
REQUIRED_FILES = ('lib/netifd/proto/qmi.sh', 'usr/lib/rpcd/file.so',
                  'lib/firmware/mt7628_e1.bin', 'lib/firmware/mt7628_e2.bin')
SERVICES = ('rpcd', 'dnsmasq', 'dropbear', 'firewall', 'wpad', 'uhttpd',
            'network', 'gateway-hardware')


def parse_inventory(text):
    """Parse 7z -slt, tolerating Windows CRLF but rejecting unsafe/duplicate names."""
    entries, current = {}, None
    for line in text.replace('\r', '').splitlines():
        if line.startswith('Path = '):
            name = line[7:].replace('\\', '/')
            require(name and not name.startswith('/') and ':' not in name and
                    all(p not in ('.', '..', '') for p in name.split('/')),
                    'Unsafe path in SquashFS inventory')
            require(name not in entries, 'Duplicate path in SquashFS inventory')
            current = entries[name] = {}
        elif current is not None and ' = ' in line:
            key, value = line.split(' = ', 1)
            current[key] = value
    require(entries and len(entries) <= 50000, 'Empty or excessive SquashFS inventory')
    return entries


def parse_packages(data):
    packages = {}
    for block in data.decode('utf-8').split('\n\n'):
        fields = dict(line.split(':', 1) for line in block.splitlines()
                      if line.startswith(('P:', 'V:')))
        if fields:
            require(set(fields) == {'P', 'V'} and fields['P'] not in packages,
                    'Malformed or duplicate APK installed-package record')
            packages[fields['P']] = fields['V']
    require(bool(packages), 'No APK installed-package records')
    return packages


class Archive:
    def __init__(self, sevenzip, rootfs, workspace):
        self.sevenzip, self.rootfs, self.workspace = str(sevenzip), str(rootfs), workspace
        listing = self.run(['l', '-slt', '-ba', '-sccUTF-8', self.rootfs], 8 * 1024 * 1024)
        self.entries = parse_inventory(listing.decode('utf-8'))
        (workspace / 'inventory.txt').write_bytes(listing)

    def run(self, arguments, limit):
        # Never extract archive paths. stdout goes to a temporary capture file.
        with tempfile.TemporaryFile(dir=self.workspace) as output:
            result = subprocess.run([self.sevenzip, *arguments], stdout=output,
                                    stderr=subprocess.PIPE, timeout=60, check=False)
            require(result.returncode == 0, '7-Zip inspection failed (exit %s)' % result.returncode)
            require(output.tell() <= limit, '7-Zip output exceeds inspection limit')
            output.seek(0)
            return output.read()

    def read(self, name, limit=1024 * 1024):
        item = self.entries.get(name)
        require(item is not None and item.get('Folder') == '-', 'Required file missing: ' + name)
        size = int(item.get('Size', '-1'))
        require(0 <= size <= limit, 'File exceeds inspection limit: ' + name)
        result = self.run(['x', '-so', '-spd', self.rootfs, name], limit)
        require(len(result) == size, 'Extracted file size does not match inventory: ' + name)
        return result


def check_contents(archive, package_source=PACKAGE):
    """Check contents via an archive interface; tests can supply recorded entries."""
    entries, failures, warnings = archive.entries, [], []
    def check(ok, message):
        if not ok:
            failures.append(message)
        return ok
    def read(name, limit=1024 * 1024):
        if name not in entries:
            failures.append('Missing file: ' + name)
            return b''
        return archive.read(name, limit)

    package_bytes = read('lib/apk/db/installed', 4 * 1024 * 1024)
    packages = parse_packages(package_bytes) if package_bytes else {}
    missing_packages = sorted(set(REQUIRED_PACKAGES) - packages.keys())
    check(not missing_packages, 'Missing installed packages: ' + ', '.join(missing_packages))
    modules = sorted(p for p in entries if p.startswith('lib/modules/') and p.endswith('.ko'))
    missing_modules = sorted(set(REQUIRED_MODULES) - {PurePosixPath(p).name for p in modules})
    check(not missing_modules, 'Missing kernel modules: ' + ', '.join(missing_modules))
    autoload = set()
    for name in entries:
        if name.startswith('etc/modules.d/') and entries[name].get('Folder') == '-':
            for line in read(name, 65536).decode('utf-8').splitlines():
                if line.strip() and not line.lstrip().startswith('#'):
                    autoload.add(line.split()[0])
    missing_autoload = sorted(set(REQUIRED_AUTOLOAD) - autoload)
    check(not missing_autoload, 'Missing module autoload entries: ' + ', '.join(missing_autoload))
    for name in REQUIRED_EXECUTABLES:
        item = entries.get(name, {})
        check(item.get('Folder') == '-' and 'x' in item.get('Mode', ''),
              'Missing/nonexecutable runtime file: ' + name)
    for name in REQUIRED_FILES:
        check(name in entries and entries[name].get('Folder') == '-', 'Missing runtime file: ' + name)

    custom = {}
    for source in sorted(package_source.rglob('*')):
        if not source.is_file():
            continue
        name = source.relative_to(package_source).as_posix()
        expected = source.read_bytes().replace(b'\r\n', b'\n')
        actual = read(name)
        same = actual == expected
        check(same, 'Custom package content differs from reviewed source: ' + name)
        executable = name in ('etc/uci-defaults/99-atech-gateway', 'etc/init.d/gateway-hardware',
                              'usr/sbin/gateway-hardware', 'usr/libexec/rpcd/atech.gateway')
        if executable:
            check('x' in entries.get(name, {}).get('Mode', ''), 'Custom script is not executable: ' + name)
        custom[name] = {'matches_reviewed_source': same, 'bytes': len(actual),
                        'sha256': hashlib.sha256(actual).hexdigest() if actual else None}
    require(bool(custom), 'No reviewed package source files found')

    service_links = {}
    for service in SERVICES:
        candidates = [p for p in entries if re.fullmatch(r'etc/rc\.d/S\d\d' + re.escape(service), p)]
        valid = len(candidates) == 1 and entries[candidates[0]].get('Mode', '').startswith('l')
        if valid:
            valid = read(candidates[0], 256).decode() == '../init.d/' + service
        check(valid, 'Missing/incorrect enabled service link: ' + service)
        service_links[service] = candidates
    rx = read('usr/bin/rx', 256)
    check(entries.get('usr/bin/rx', {}).get('Mode', '').startswith('l') and
          rx in (b'lrz', b'/usr/bin/lrz', b'../bin/lrz'), 'XMODEM rx alias does not point to lrz')

    unit_present = 'etc/gateway/unit.json' in entries
    check(not unit_present, 'Validation image unexpectedly contains per-unit credentials')
    shadow = read('etc/shadow', 65536)
    root_fields = [line.split(b':') for line in shadow.splitlines() if line.startswith(b'root:')]
    root_static = None
    if len(root_fields) == 1:
        password = root_fields[0][1]
        root_static = 'empty-before-firstboot' if not password else ('locked' if password.startswith((b'!', b'*')) else 'credential-present')
    check(root_static == 'locked', 'Validation image root account is not locked before first boot')
    check('etc/config/wireless' not in entries, 'Unexpected preconfigured Wi-Fi in validation image')
    check('etc/dropbear/authorized_keys' not in entries and 'root/.ssh/authorized_keys' not in entries,
          'Unexpected SSH authorized keys in validation image')

    gateway = read('etc/config/gateway').decode('utf-8')
    defaults = {}
    for option in ('hardware_validated', 'powercut_validated', 'esim_populated', 'sim_slot', 'serial'):
        match = re.findall(r"^\s*option\s+" + option + r"\s+'([^']*)'\s*$", gateway, re.M)
        defaults[option] = match[0] if len(match) == 1 else None
    check(defaults == {'hardware_validated': '0', 'powercut_validated': '0', 'esim_populated': '0',
                       'sim_slot': 'A', 'serial': 'UNPROVISIONED'}, 'Carrier default gates/SIM state differ from validation defaults')
    keep = read('lib/upgrade/keep.d/atech-gateway')
    check(b'/etc/gateway/unit.json' in keep.splitlines(), 'Sysupgrade preservation list omits unit.json')

    asu = {name: version for name, version in packages.items() if 'attendedsysupgrade' in name}
    if asu:
        warnings.append('Attended Sysupgrade is installed. Do not install upstream-generated images; they omit the MB00 carrier DTS changes and custom package.')
    return {'rootfs_checks_passed': not failures, 'failures': failures, 'warnings': warnings,
            'packages': packages, 'modules': modules, 'missing_packages': missing_packages,
            'missing_modules': missing_modules, 'module_autoload': sorted(autoload),
            'missing_autoload': missing_autoload, 'custom_package_files': custom,
            'enabled_service_links': service_links, 'carrier_defaults': defaults,
            'unit_record_present': unit_present, 'static_root_password_state': root_static,
            'attendedsysupgrade_packages': asu, 'inventory_entries': len(entries)}


def inspect_rootfs(image, manifest, sevenzip, output, package_source=PACKAGE):
    require(manifest.get('mode') == 'unprovisioned-validation',
            'This tool inspects credential-free validation images only')
    result = inspect(image, manifest)
    output = output.resolve()
    require(output.is_relative_to(DIST.resolve()) and output != DIST.resolve(),
            'Inspection directory must be a child of firmware/dist')
    require(not output.exists(), 'Choose a new inspection directory; existing output is not overwritten')
    output.mkdir(parents=True)
    data = image.read_bytes()
    start, size = result['squashfs']['offset'], result['squashfs']['bytes_used']
    require(96 <= size <= 32 * 1024 * 1024 and 0 <= start <= len(data) - size,
            'SquashFS extraction bounds exceed the verified image')
    rootfs = output / 'rootfs.squashfs'
    rootfs.write_bytes(data[start:start + size])
    report = check_contents(Archive(sevenzip, rootfs, output), package_source)
    report.update(schema='mb00-rootfs-inspection-1', image=image.name, sha256=result['sha256'],
                  source_revision=manifest.get('source_revision'),
                  reviewed_package_source=str(package_source.resolve()),
                  carrier_image_checks_passed=result['carrier_checks_passed'],
                  carrier_image_failures=result['failures'],
                  squashfs=result['squashfs'], programming_authorization=False, hardware_tested=False,
                  limitations=['Static inspection does not execute first boot, authenticate a build signature, or prove hardware operation.',
                               'Matching firstboot content links to source tests; it does not prove runtime fail-closed behavior.',
                               'The validation image must already lock root network authentication; physical fixture console remains available by upstream ttylogin policy.',
                               'Only listed packages/modules/files are checked; library linking and all service behavior require device testing.'])
    (output / 'rootfs-inspection.json').write_text(json.dumps(report, indent=2) + '\n', newline='\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--sevenzip', type=Path)
    parser.add_argument('--package-source', type=Path, default=PACKAGE,
                        help='Reviewed package files directory from the exact built source commit')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    sevenzip = args.sevenzip or shutil.which('7z') or FIRMWARE.parent / '.tools/7zip-full/7z.exe'
    try:
        require(Path(sevenzip).is_file(), 'Supply an existing 7-Zip executable with --sevenzip')
        require(args.package_source.is_dir(), 'Reviewed package source directory is missing')
        report = inspect_rootfs(args.image, json.loads(args.manifest.read_text()), sevenzip, args.output_dir,
                                args.package_source)
        print(json.dumps({key: report[key] for key in ('rootfs_checks_passed', 'carrier_image_checks_passed',
                                                     'failures', 'warnings', 'programming_authorization')}, indent=2))
        print('Report:', args.output_dir / 'rootfs-inspection.json')
        return 0 if report['rootfs_checks_passed'] and report['carrier_image_checks_passed'] else 1
    except (InspectionError, OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('Rootfs inspection failed:', error)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
