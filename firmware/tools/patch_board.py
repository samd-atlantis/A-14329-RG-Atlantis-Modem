"""Enable the carrier I2C controller; retain upstream flash/calibration partitions."""
from pathlib import Path
import sys
import subprocess

path = Path(sys.argv[1]) / "target/linux/ramips/dts/mt7628an_hilink_hlk-7628n.dts"
text = path.read_text()
old = '''&state_default {
	gpio {
		groups = "i2c";
		function = "gpio";
	};
};'''
new = '''/* A-14329 carrier: I2C on module pins 24/25, MCP23008 at 0x20.
 * Leave the I2C pin group in its peripheral function, not GPIO mode.
 * SW3 is module pin30 (MT7628 GPIO11); recovery behaviour is not assumed.
 */
&i2c {
	status = "okay";
};'''
baseline = subprocess.check_output([
    'git', '-C', sys.argv[1], 'show',
    'HEAD:target/linux/ramips/dts/mt7628an_hilink_hlk-7628n.dts'
], text=True)
if baseline.count(old) != 1:
    raise SystemExit("Upstream DTS changed: inspect pinmux before patching")
expected = baseline.replace(old, new)
# Upstream reference-carrier reset/LED pins are NC on A-14329-MB00.
# Remove the reset handler so floating GPIO38 cannot trigger a factory reset.
expected += '''
/* MB00 SW1 is hardware PORST_N. No Linux reset key is assigned to SW3. */
&{/} {
    /delete-node/ keys;
    /delete-node/ leds;
};
'''
if text not in (baseline, expected):
    raise SystemExit("DTS has unrelated edits; refusing to preserve unreviewed partition/pinmux changes")
path.write_text(expected)
