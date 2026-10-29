A-14329-MB00 development firmware - updated 2026-10-29

START HERE
PROGRAMMING-MB00.txt: first-board identification, backup, programming and setup.
FACTORY-PROVISIONING.txt: common-image/per-unit-bundle candidate for a 50-unit fixture.
VALIDATION-MB00.txt: actual test/build status; source checks do not prove hardware.
../hardware/audits/: independent electrical and current-geometry KiCad audit.

TARGET
HLK-7628N router (BOM C209920), provisional 32 MB flash profile. Verify actual flash,
RAM, bootloader and partition offsets before programming; family name alone does
not establish memory size. Ordered modem is Quectel EC25AFFA-MINIPCIE. It keeps
its own Quectel firmware. No extra Bluetooth/LoRa radio firmware is required.
Physical hinged J9 socket takes a nano-SIM. U20 eSIM is absent and not needed.

LOCAL SETUP AFTER A PROVISIONED IMAGE BOOTS
Use DHCP on any of the four Ethernet jacks, or join ATECH-<serial> with the unit's
unique Wi-Fi password. Open https://192.168.50.1 and sign in as root using the
unique administrator password on its private label. Development HTTPS uses a
locally generated certificate. Production certificate management remains a task.
Gateway -> Site & Cellular sets carrier APN and enables cellular; it starts disabled.
Gateway -> Controllers stores controller web addresses. Wi-Fi controllers
join the same LAN as wired controllers. Existing static-IP controllers may need
readdressing or a gateway LAN-subnet change. Setup works without internet or a SIM.
All four jacks use module PHY1..4; PHY0 is unused. This is a setup/controller AP,
not automatic Wi-Fi-uplink failover. Keep modem-service J17 USB unplugged in normal
use so the router is the modem's USB host. J14 is the router serial console.

WHAT IS IMPLEMENTED
Authenticated LuCI pages; QMI cellular networking; four-port LAN/DHCP/NAT; LAN-only
administration; per-unit credential generation; guarded MCP23008 controls; source
and mock tests; pinned OpenWrt build; read-only device/image preflight; private
factory-bundle generation and commissioning record template. Successful provisioning
enables password authentication on the USB serial console. Routine upgrades
preserve the unit identity and site configuration.

BUILD AND CREDENTIALS
Use a supported Linux host with OpenWrt prerequisites. No Linux/WSL is installed
on this Windows PC. From repository root:
  python3 firmware/tools/provision.py --count 1 --output firmware/private
  bash firmware/build.sh "$PWD/firmware/private/AG26-0001.json"
Use a fresh OPENWRT_TREE per private unit; stale overlays are rejected. Keep private/,
dist/, labels, backups and images secret. Images contain the per-unit Wi-Fi key.
The build locks v25.12.6, source tag and all feed commits in build-lock.json. It
retains upstream flash/calibration partitions, enables carrier I2C, removes the
unwired GPIO38 reset-key and GPIO44 LED assignments, and records SHA256 artifacts.
Never clone another module's bootloader, RF-calibration, MAC or unit credentials.

GitHub Actions -> OpenWrt MB00 cross-build -> Run workflow compiles an unprovisioned
validation image without secrets. Check its actual run result and artifact manifest.
It locks network login and disables Wi-Fi setup; the physical console remains
available for fixture work. Do not program that image alone to a customer unit.
FACTORY-PROVISIONING.txt explains a separate private unit-config bundle candidate.
Common-image unit records live in writable overlay and are erased by factory reset;
per-unit images bake their identity into SquashFS and retain it across factory reset.

CARRIER CONTROLS
Assembly49 pin audit verified MCP23008 address 0x20, GP0 SIM_SELECT, GP1 MODEM_OFF,
GP2 MODEM_RESET_REQ. Passive hardware defaults already power the modem and select
physical SIM A. Normal Wi-Fi/LAN/cellular operation does not need software GPIOs.
hardware_validated=0 stays until actual bus/polarity/levels are bench-tested. Startup
refuses to change a live SIM/power/reset level. powercut_validated=0 separately
blocks disruptive emergency rail cycling pending shutdown/sequence validation.
There is no automatic power-cycle loop or graceful modem shutdown implementation.
esim_populated=0 blocks SIM B before any disruption. No eSIM LPA/profile download.
SW1 is router hardware reset; SW4 modem reset. SW3 is pin 30 / SoC GPIO11; no ROM boot
function or Linux factory-reset action is assumed. TC2050 controls are custom.

REMOTE ACCESS
No WAN administration or controller port forwarding is enabled. Outbound cellular
internet alone does not make private controller IPs remotely reachable. A secure
outbound VPN/cloud fleet-management replacement for RMS remains unimplemented.
Do not deploy customer remote access based on this starter's local UI alone.

VALIDATION AND PREVIEW
From repository root:
  python3 -m unittest discover -s firmware/tests -p 'test_*.py' -v
  node firmware/tests/check.js
Tests cover source/mocked behavior, not RF, USB timing, regulators or actual flash.
Use acceptance-template.json for real first-board/fixture results, saved privately.
For a visual concept only:
  python -m http.server 8765 --bind 127.0.0.1 --directory firmware/preview
The preview uses sample data. Real pages are integrated into standard LuCI navigation.

PRIMARY REFERENCES
https://downloads.openwrt.org/releases/25.12.6/targets/ramips/mt76x8/
https://github.com/openwrt/openwrt/blob/v25.12.6/target/linux/ramips/dts/mt7628an_hilink_hlk-7628n.dts
https://github.com/openwrt/openwrt/blob/v25.12.6/target/linux/ramips/mt76x8/base-files/etc/board.d/02_network
https://raw.githubusercontent.com/openwrt/openwrt/v25.12.6/package/base-files/files/sbin/sysupgrade
https://raw.githubusercontent.com/openwrt/openwrt/v25.12.6/package/base-files/files/usr/libexec/login.sh
