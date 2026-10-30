A-14329-MB00 development firmware - updated 2026-10-29

START HERE
PROGRAMMING-MB00.txt: first-board identification, backup, programming and setup.
FACTORY-PROVISIONING.txt: common-image/per-unit-bundle candidate for a 50-unit fixture.
VALIDATION-MB00.txt: actual test/build status; source checks do not prove hardware.
HLK-FACTORY-RECOVERY.txt: sourced, conditional OEM installation/recovery paths.
../hardware/audits/: independent electrical and current-geometry KiCad audit.

TARGET
HLK-7628N router (BOM C209920). The C209920-linked manufacturer datasheet specifies
32 MB flash / 128 MB RAM as the default, supporting the chosen 32 MB flash profile.
It also allows custom memory options. Verify actual flash, RAM, bootloader and
partition offsets before programming; see ../hardware/audits/hlk-memory-evidence.txt.
Ordered modem is Quectel EC25AFFA-MINIPCIE. It keeps its own Quectel firmware.
No extra Bluetooth/LoRa radio firmware is required.
Physical hinged J9 socket takes a nano-SIM. U20 eSIM is absent and not needed.

LOCAL SETUP AFTER A PROVISIONED IMAGE BOOTS
Use DHCP on any of the four Ethernet jacks, or join Atlantis-<MAC4> with the unit's
unique Wi-Fi password. Open https://10.0.100.7 and sign in as root using the
unique administrator password on its private label. Development HTTPS uses a
locally generated certificate. Production certificate management remains a task.
Gateway -> Site & Cellular sets carrier APN and enables cellular; it starts disabled.
Gateway -> Controllers stores controller web addresses. Wi-Fi controllers
join the same LAN as wired controllers. Existing static-IP controllers may need
readdressing or a gateway LAN-subnet change. Setup works without internet or a SIM.
All four jacks use module PHY1..4; PHY0 is unused. This is a setup/controller AP,
not automatic Wi-Fi-uplink failover. Keep modem-service J17 USB unplugged in normal
use so the router is the modem's USB host. J14 is the router serial console.

For four controllers with manually fixed addresses, a suggested default is
10.0.100.101 through 10.0.100.104, mask 255.255.254.0, gateway/DNS 10.0.100.7.
These are outside the default DHCP pool (.150-.199). Configure each controller
itself, or use distinct DHCP reservations for DHCP clients. Directory entries
are bookmarks; they do not assign an address. Adjust this plan if changing the
gateway LAN subnet or integrating with another existing network.

The default controller directory contains four HTTP bookmarks for those addresses.
Set controllers 2-4 to .102, .103 and .104 before connecting them together; factory
controllers sharing .101 cannot coexist on this LAN. A bookmark does not change
the controller's settings. The router LAN is 10.0.100.7/23; DHCP is .150-.199.

Wi-Fi name: Atlantis- plus the final four uppercase hexadecimal characters of the
internal Wi-Fi radio MAC, without colons (00:11:22:33:A1:B2 -> Atlantis-A1B2).
First boot reads phy0's permanent MAC and uses it as the setup AP BSSID. Missing
or invalid MAC data leaves provisioning locked for fixture recovery. Previously
provisioned site settings are preserved on routine upgrades.

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
After a successful main-branch build, MB00 compiled-image checks independently
inspects the actual filesystem against that build's package source. Both workflow
results must pass. It verifies packaged files and defaults without executing them;
this still does not prove hardware operation.
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
tools/inspect_rootfs.py can inspect a validation sysupgrade image using an existing
7-Zip executable. Supply --image, --manifest and a new --output-dir below firmware/dist;
--sevenzip selects the executable when it is not on PATH or in .tools/7zip-full.
It checks actual SquashFS files, packages, modules, service links and carrier defaults.
It does not execute first boot or authorize programming. Per-unit images are excluded.
Use only reviewed MB00 builds for updates. Stock OpenWrt and Attended Sysupgrade
images omit our carrier changes; the upstream HLK profile name is insufficient.
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
