"""Enable the carrier I2C controller; retain upstream flash/calibration partitions."""
from pathlib import Path
import sys

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
 * SW3 / GPIO0 recovery behaviour is deliberately not assumed here.
 */
&i2c {
	status = "okay";
};'''
if old not in text:
    if new in text:
        sys.exit(0)
    raise SystemExit("Upstream DTS changed: inspect pinmux before patching")
path.write_text(text.replace(old, new))
