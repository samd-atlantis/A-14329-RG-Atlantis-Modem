"""Run first-boot shell logic with fake UCI/system services; no router required."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash') or r'C:/Program Files/Git/bin/bash.exe'


class FirstBootTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.dir = Path(self.tmp.name)
        posix = self.dir.as_posix()
        if os.name == 'nt':
            posix = '/' + posix[0].lower() + posix[2:]
        self.env = os.environ.copy()
        self.env.update(TEST_DIR=posix, PROVISIONED='0', SERIAL='BENCH-0001',
                        SSID='ATECH-BENCH-0001', KEY='0123456789abcdef01234567',
                        HASH='$6$testsalt$' + 'a'*86, FAIL_CONFIG='0', WAN_ZONE='wan')
        (self.dir/'unit.json').write_text('{}')
        (self.dir/'shadow').write_text('root:*:0:0:99999:7:::\ndaemon:*:0:0:99999:7:::\n')
        source = (ROOT/'package/atech-gateway/files/etc/uci-defaults/99-atech-gateway').read_text()
        source = source.replace('/etc/gateway/unit.json', posix+'/unit.json')
        source = source.replace('/etc/shadow', posix+'/shadow')
        mocks = '''
uci() {
 case "$*" in
  '-q get gateway.main.provisioned') echo "$PROVISIONED";;
  'show firewall') echo 'firewall.@zone[1]=zone';;
  '-q get firewall.@zone[1].name') echo "$WAN_ZONE";;
  '-q show wireless') printf 'wireless.radio0=wifi-device\nwireless.radio1=wifi-device\n';;
  *)
   echo "uci $*" >> "$TEST_DIR/log"
   if [ "$FAIL_CONFIG" = 1 ] && [ "$*" = 'set uhttpd.main.redirect_https=1' ]; then return 1; fi
   ;;
 esac
}
jsonfilter() {
 case "$4" in
  '@.serial') echo "$SERIAL";;
  '@.ssid') echo "$SSID";;
  '@.wifi_password') echo "$KEY";;
  '@.root_hash') echo "$HASH";;
 esac
}
passwd() { echo "passwd $*" >> "$TEST_DIR/log"; }
logger() { echo "logger $*" >> "$TEST_DIR/log"; }
wifi() { echo "wifi $*" >> "$TEST_DIR/log"; }
'''
        self.script = self.dir/'firstboot.sh'
        self.script.write_text(source.replace('set -eu', 'set -eu\n'+mocks), newline='\n')

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self):
        proc = subprocess.run([BASH, str(self.script)], env=self.env,
                              text=True, capture_output=True)
        path = self.dir/'log'
        return proc, path.read_text() if path.exists() else ''

    def assert_failed_closed(self, proc, log):
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('passwd -l root', log)
        self.assertIn('set wireless.radio0.disabled=1', log)
        self.assertIn('set wireless.radio1.disabled=1', log)
        self.assertIn('wifi down', log)
        self.assertNotIn('gateway.main.provisioned=1', log)

    def test_success_sets_credentials_and_lan_only_defaults(self):
        proc, log = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('set network.cellular.auto=0', log)
        self.assertIn('set dropbear.@dropbear[0].Interface=lan', log)
        self.assertIn('set system.@system[0].ttylogin=1', log)
        self.assertIn('set firewall.@zone[1].input=REJECT', log)
        self.assertIn('set gateway.main.provisioned=1', log)
        self.assertIn('root:'+self.env['HASH']+':', (self.dir/'shadow').read_text())
        self.assertNotIn('wifi down', log)

    def test_missing_unit_locks_root_and_disables_every_radio(self):
        (self.dir/'unit.json').unlink()
        proc, log = self.run_script()
        self.assert_failed_closed(proc, log)
        # The secret-free validation image retains the upstream local fixture
        # console; this is not network access and is never customer firmware.
        self.assertNotIn('ttylogin=1', log)

    def test_bad_hash_does_not_configure_wifi(self):
        self.env['HASH']='$6$not-a-valid-hash'
        proc, log = self.run_script()
        self.assert_failed_closed(proc, log)
        self.assertNotIn('disabled=0', log)

    def test_bad_ssid_does_not_configure_wifi(self):
        self.env['SSID']='shared-default'
        self.assert_failed_closed(*self.run_script())

    def test_missing_wan_zone_does_not_enable_wifi(self):
        self.env['WAN_ZONE']='lan'
        proc, log = self.run_script()
        self.assert_failed_closed(proc, log)
        self.assertNotIn('disabled=0', log)

    def test_mid_setup_failure_locks_root_and_overrides_wifi_enable(self):
        self.env['FAIL_CONFIG']='1'
        proc, log = self.run_script()
        self.assert_failed_closed(proc, log)
        self.assertGreater(log.rindex('set wireless.radio0.disabled=1'),
                           log.index('set wireless.radio0.disabled=0'))
        self.assertIn('root:*:', (self.dir/'shadow').read_text())

    def test_sysupgrade_does_not_overwrite_site_config(self):
        self.env['PROVISIONED']='1'
        (self.dir/'unit.json').unlink()
        proc, log = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(log, '')


if __name__ == '__main__':
    unittest.main()
