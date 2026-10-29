"""Exercise carrier script against fake UCI/I2C, never real hardware."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash') or r'C:/Program Files/Git/bin/bash.exe'


class CarrierTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT)
        self.dir = Path(self.tmp.name)
        self.posix = str(self.dir).replace('\\', '/')
        if os.name == 'nt':
            self.posix = '/' + self.posix[0].lower() + self.posix[2:]
        self.env = os.environ.copy()
        self.env.update(VALIDATED='1', FAIL_WRITE='0', ESIM_POPULATED='1',
                        POWERCUT_VALIDATED='1', CELLULAR_AUTO='1',
                        GPIO='0x00', IODIR='0xf8', OLAT='0x00')
        self.script = self.dir / 'harness.sh'
        text = (ROOT/'package/atech-gateway/files/usr/sbin/gateway-hardware').read_text()
        text = text.replace('/var/lock/gateway-hardware', self.posix+'/lock')
        mocks = '''
uci() {
 case "$*" in
  *hardware_validated*) echo "$VALIDATED";;
  *powercut_validated*) echo "$POWERCUT_VALIDATED";;
  *esim_populated*) echo "$ESIM_POPULATED";;
  *i2c_bus*) echo 0;;
  *network.cellular.auto*) echo "$CELLULAR_AUTO";;
  '-q get gateway.main.sim_slot') echo A;;
  *) echo "uci $*" >> "$TEST_LOG";;
 esac
}
i2cset() { echo "i2cset $*" >> "$TEST_LOG"; [ "$FAIL_WRITE" != 1 ]; }
i2cget() {
 case "$4" in
  0x00) echo "$IODIR";;
  0x09) echo "$GPIO";;
  0x0a) echo "$OLAT";;
 esac
}
ifdown() { echo down >> "$TEST_LOG"; }
ifup() { echo up >> "$TEST_LOG"; }
sleep() { echo "sleep $*" >> "$TEST_LOG"; }
'''
        self.script.write_text(text.replace('set -eu', 'set -eu\n'+mocks), newline='\n')
        self.env['TEST_LOG'] = self.posix+'/log'

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args):
        p = subprocess.run([BASH, str(self.script), *args], env=self.env,
                           text=True, capture_output=True)
        log = self.dir/'log'
        return p, log.read_text() if log.exists() else ''

    def test_unvalidated_never_touches_i2c(self):
        self.env['VALIDATED']='0'
        p,log=self.run_script('select','B')
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(log,'')

    def test_init_latch_precedes_direction(self):
        p,log=self.run_script('init')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertLess(log.index('0x0a 0'),log.index('0x00 0xf8'))

    def test_init_never_hot_switches_an_already_powered_modem(self):
        p,log=self.run_script('init','B')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('Live carrier control levels differ',p.stderr)
        self.assertEqual(log,'')

    def test_init_preserves_live_b_selection_after_warm_reboot(self):
        self.env['GPIO']='0x01'
        p,log=self.run_script('init','B')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('0x0a 1',log)

    def test_init_never_releases_asserted_off_or_reset_controls(self):
        for gpio in ['0x02','0x04']:
            with self.subTest(gpio=gpio):
                self.env['GPIO']=gpio
                p,log=self.run_script('init','A')
                self.assertNotEqual(p.returncode,0)
                self.assertEqual(log,'')

    def test_unvalidated_powercut_never_disconnects(self):
        self.env['POWERCUT_VALIDATED']='0'
        p,log=self.run_script('powercycle','A')
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(log,'')

    def test_uninitialized_outputs_never_disconnect(self):
        self.env['IODIR']='0xff'
        p,log=self.run_script('select','B')
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(log,'')

    def test_invalid_i2c_read_never_disconnects(self):
        self.env['OLAT']='invalid'
        p,log=self.run_script('powercycle','A')
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(log,'')

    def test_mb00_absent_esim_cannot_switch(self):
        self.env['ESIM_POPULATED']='0'
        p,log=self.run_script('select','B')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('not populated',p.stderr)
        self.assertEqual(log,'')

    def test_mb00_physical_sim_initializes_without_esim(self):
        self.env['ESIM_POPULATED']='0'
        p,log=self.run_script('init','A')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('0x0a 0',log)

    def test_sim_switch_sequence(self):
        p,log=self.run_script('select','B')
        self.assertEqual(p.returncode,0,p.stderr)
        ordered=['down','0x0a 2','sleep 3','0x0a 3','sleep 1','0x0a 1','sim_slot=B','sleep 12','up']
        cursor=0
        for item in ordered:
            cursor=log.index(item,cursor)+len(item)

    def test_failed_cut_does_not_switch_or_reconnect(self):
        self.env['FAIL_WRITE']='1'
        p,log=self.run_script('select','B')
        self.assertNotEqual(p.returncode,0)
        self.assertNotIn('0x0a 3',log)
        self.assertNotIn('\nup',log)
        self.assertFalse((self.dir/'lock').exists())

    def test_disabled_cellular_stays_disabled_after_recovery(self):
        self.env['CELLULAR_AUTO']='0'
        p,log=self.run_script('powercycle','A')
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('down',log)
        self.assertNotIn('\nup',log)

    def test_overlapping_recovery_does_not_touch_hardware(self):
        (self.dir/'lock').mkdir()
        p,log=self.run_script('powercycle','A')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('already running',p.stderr)
        self.assertEqual(log,'')

    def test_invalid_slot_rejected(self):
        p,log=self.run_script('select','B; echo unsafe')
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(log,'')


if __name__=='__main__':
    unittest.main()
