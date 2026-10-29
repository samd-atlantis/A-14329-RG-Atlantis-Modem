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
        self.env.update(VALIDATED='1', FAIL_WRITE='0', ESIM_POPULATED='1')
        self.script = self.dir / 'harness.sh'
        text = (ROOT/'package/atech-gateway/files/usr/sbin/gateway-hardware').read_text()
        text = text.replace('/var/lock/gateway-hardware', self.posix+'/lock')
        mocks = '''
uci() {
 case "$*" in
  *hardware_validated*) echo "$VALIDATED";;
  *esim_populated*) echo "$ESIM_POPULATED";;
  *i2c_bus*) echo 0;;
  '-q get gateway.main.sim_slot') echo A;;
  *) echo "uci $*" >> "$TEST_LOG";;
 esac
}
i2cset() { echo "i2cset $*" >> "$TEST_LOG"; [ "$FAIL_WRITE" != 1 ]; }
i2cget() { echo 0x00; }
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

    def test_invalid_slot_rejected(self):
        p,log=self.run_script('select','B; echo unsafe')
        self.assertNotEqual(p.returncode,0)
        self.assertEqual(log,'')


if __name__=='__main__':
    unittest.main()
