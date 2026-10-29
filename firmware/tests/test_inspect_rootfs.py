"""Static audit tests; fixture files are not an executable router filesystem."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('inspect_rootfs', TOOLS / 'inspect_rootfs.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class Files:
    def __init__(self):
        self.entries, self.contents = {}, {}

    def add(self, name, data=b'fixture', mode='-rwxr-xr-x'):
        self.contents[name] = data
        self.entries[name] = {'Folder': '-', 'Mode': mode, 'Size': str(len(data))}

    def read(self, name, limit=1024 * 1024):
        return self.contents[name]


def good_fixture():
    files = Files()
    for name in audit.REQUIRED_EXECUTABLES + audit.REQUIRED_FILES:
        files.add(name)
    for name in audit.REQUIRED_MODULES:
        files.add('lib/modules/fixture/' + name)
    files.add('etc/modules.d/fixture', ('\n'.join(audit.REQUIRED_AUTOLOAD) + '\n').encode())
    files.add('lib/apk/db/installed', ''.join('P:' + name + '\nV:fixture\n\n'
                                            for name in audit.REQUIRED_PACKAGES).encode())
    for source in audit.PACKAGE.rglob('*'):
        if source.is_file():
            files.add(source.relative_to(audit.PACKAGE).as_posix(), source.read_bytes().replace(b'\r\n', b'\n'))
    for service in audit.SERVICES:
        files.add('etc/rc.d/S25' + service, ('../init.d/' + service).encode(), 'lrwxrwxrwx')
    files.add('usr/bin/rx', b'lrz', 'lrwxrwxrwx')
    files.add('etc/shadow', b'root:!:0:0:99999:7:::\n', '-rw-------')
    return files


class RootfsTests(unittest.TestCase):
    def test_complete_content_is_static_only(self):
        result = audit.check_contents(good_fixture())
        self.assertTrue(result['rootfs_checks_passed'], result['failures'])
        self.assertEqual(result['static_root_password_state'], 'locked')
        self.assertFalse(result['unit_record_present'])

    def test_mutated_firstboot_is_rejected(self):
        files = good_fixture()
        name = 'etc/uci-defaults/99-atech-gateway'
        files.add(name, files.read(name).replace(b'passwd -l root', b'passwd -u root'))
        self.assertTrue(any('differs' in x and name in x for x in audit.check_contents(files)['failures']))

    def test_comparison_can_use_exact_built_source_in_separate_checkout(self):
        files = good_fixture()
        name = 'etc/uci-defaults/99-atech-gateway'
        files.add(name, files.read(name) + b'# earlier reviewed build\n')
        self.assertFalse(audit.check_contents(files)['rootfs_checks_passed'])
        with tempfile.TemporaryDirectory(dir=TOOLS.parent) as directory:
            source = Path(directory)
            for original in audit.PACKAGE.rglob('*'):
                if original.is_file():
                    relative = original.relative_to(audit.PACKAGE)
                    target = source / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(files.read(relative.as_posix()))
            result = audit.check_contents(files, source)
            self.assertTrue(result['rootfs_checks_passed'], result['failures'])

    def test_unsafe_gates_rejected_even_if_other_files_match(self):
        files = good_fixture()
        name = 'etc/config/gateway'
        files.add(name, files.read(name).replace(b"hardware_validated '0'", b"hardware_validated '1'"))
        result = audit.check_contents(files)
        self.assertFalse(result['rootfs_checks_passed'])
        self.assertIn('Carrier default gates/SIM state differ from validation defaults', result['failures'])

    def test_missing_package_and_module(self):
        files = good_fixture()
        files.add('lib/apk/db/installed', files.read('lib/apk/db/installed').replace(b'P:uqmi\nV:fixture\n\n', b''))
        del files.entries['lib/modules/fixture/qmi_wwan.ko']
        result = audit.check_contents(files)
        self.assertIn('uqmi', result['missing_packages'])
        self.assertIn('qmi_wwan.ko', result['missing_modules'])

    def test_service_alias_and_mode_must_match(self):
        for change in ('target', 'mode', 'duplicate'):
            with self.subTest(change=change):
                files = good_fixture()
                if change == 'target':
                    files.add('etc/rc.d/S25gateway-hardware', b'../init.d/other', 'lrwxrwxrwx')
                elif change == 'mode':
                    files.entries['etc/rc.d/S25gateway-hardware']['Mode'] = '-rwxr-xr-x'
                else:
                    files.add('etc/rc.d/S26gateway-hardware', b'../init.d/gateway-hardware', 'lrwxrwxrwx')
                self.assertFalse(audit.check_contents(files)['rootfs_checks_passed'])

    def test_validation_image_rejects_embedded_credentials_without_reading_them(self):
        files = good_fixture()
        files.entries['etc/gateway/unit.json'] = {'Folder': '-', 'Mode': '-rw-------', 'Size': '500'}
        files.add('etc/shadow', b'root:$6$not-for-validation:0:0:99999:7:::\n')
        result = audit.check_contents(files)
        self.assertFalse(result['rootfs_checks_passed'])
        self.assertTrue(result['unit_record_present'])
        self.assertEqual(result['static_root_password_state'], 'credential-present')
        self.assertNotIn('$6$', str(result))

    def test_validation_image_empty_root_password_is_rejected(self):
        files = good_fixture()
        files.add('etc/shadow', b'root::0:0:99999:7:::\n', '-rw-------')
        result = audit.check_contents(files)
        self.assertFalse(result['rootfs_checks_passed'])
        self.assertEqual(result['static_root_password_state'], 'empty-before-firstboot')

    def test_missing_module_autoload_is_rejected(self):
        files = good_fixture()
        files.add('etc/modules.d/fixture', b'mt7603e\n')
        result = audit.check_contents(files)
        self.assertFalse(result['rootfs_checks_passed'])
        self.assertIn('i2c-mt7621', result['missing_autoload'])

    def test_attended_upgrade_is_warning_not_failure(self):
        files = good_fixture()
        files.add('lib/apk/db/installed', files.read('lib/apk/db/installed') + b'P:luci-app-attendedsysupgrade\nV:1\n\n')
        result = audit.check_contents(files)
        self.assertTrue(result['rootfs_checks_passed'])
        self.assertEqual(len(result['warnings']), 1)

    def test_missing_preservation_rule_and_nonexecutable_script(self):
        files = good_fixture()
        files.add('lib/upgrade/keep.d/atech-gateway', b'')
        files.entries['usr/sbin/gateway-hardware']['Mode'] = '-rw-r--r--'
        result = audit.check_contents(files)
        self.assertTrue(any('preservation' in x for x in result['failures']))
        self.assertTrue(any('not executable' in x for x in result['failures']))

    def test_inventory_windows_normalization_and_path_safety(self):
        result = audit.parse_inventory('Path = etc\\shadow\r\nFolder = -\r\nSize = 20\r\nMode = -rw-------\r\n')
        self.assertIn('etc/shadow', result)
        for path in ('lib/network/wwan/0421:03a7', 'lib\\network\\wwan\\2c7c:0125'):
            self.assertIn(path.replace('\\', '/'), audit.parse_inventory('Path = ' + path + '\n'))
        for path in ('../outside', '/outside', 'C:\\outside', 'etc//file', './file',
                     'etc/shadow:stream', 'lib/network/wwan/2c7c:0125:stream',
                     'lib/network/wwan/../2c7c:0125', 'lib/network/wwan/C:outside'):
            with self.subTest(path=path), self.assertRaises(audit.InspectionError):
                audit.parse_inventory('Path = ' + path + '\n')
        with self.assertRaises(audit.InspectionError):
            audit.parse_inventory('Path = etc/file\nPath = etc/file\n')

    def test_package_database_duplicate_or_incomplete_rejected(self):
        for data in (b'P:one\n', b'P:one\nV:1\n\nP:one\nV:2\n', b''):
            with self.subTest(data=data), self.assertRaises(audit.InspectionError):
                audit.parse_packages(data)

    def test_private_image_rejected_before_image_or_output_access(self):
        with self.assertRaisesRegex(audit.InspectionError, 'credential-free'):
            audit.inspect_rootfs(Path('does-not-exist'), {'mode': 'private-unit-development'},
                                 Path('7z'), Path('no-output'))


if __name__ == '__main__':
    unittest.main()
