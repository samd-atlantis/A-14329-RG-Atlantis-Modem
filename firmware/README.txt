ATECH / A-14329 gateway firmware, 0.1.0 development source
2026-10-27

WHAT IS INCLUDED
OpenWrt package with authenticated LuCI Overview, Site & Cellular and Controllers
pages; QMI EG25-GL configuration; per-unit WPA2 Wi-Fi setup; four Ethernet LAN
ports; LAN DHCP; cellular NAT/firewall; MCP23008 carrier-control script and RPC
methods; private unit provisioning generator; Linux source-build recipe; interactive
visual preview. The modem keeps Quectel firmware. There is no extra radio firmware.

FIRST CONNECTION (after a correctly built, provisioned image boots)
1. Plug a laptop into any Ethernet jack, using DHCP, OR join ATECH-<unit serial>
   with the unique password printed on that unit's label.
2. Browse to https://192.168.50.1 and sign in as root with that unit's unique
   administrator password. Production needs a trusted device certificate strategy;
   development LuCI uses its locally generated certificate.
3. Gateway -> Site & Cellular: enter the carrier APN and enable cellular.
4. Wi-Fi controllers can join the same WPA2 network and LAN as wired controllers.
   Change Wi-Fi settings through Network -> Wireless. Changing credentials
   disconnects Wi-Fi clients; use Ethernet while changing them.
5. Give controllers DHCP reservations and save their web IPs in Controllers.
   Existing fixed-IP controllers may need readdressing to 192.168.50.0/24, or change
   the gateway LAN subnet under Network -> Interfaces before connecting them.

All four physical jacks map to module PHY1..4, matching upstream HLK OpenWrt LAN
defaults. PHY0 is unused. Cellular is the upstream WAN. This version uses Wi-Fi as
an AP for setup/controllers; it does not implement automatic Wi-Fi-uplink failover.
The local setup UI works without a SIM or internet connection.

REMOTE WALCHEM ACCESS
Outbound controller cloud traffic is routed over cellular when configured. Cellular
internet does not automatically allow a browser elsewhere to reach controller IPs:
carrier CGNAT normally requires an outbound VPN or the controller's cloud service.
No WAN management/port forwards are added by this package. VPN integration and
Walchem-specific protocols need requirements and testing; no process-control logic
or guaranteed compatibility with an unspecified controller model is claimed.

BUILD
Use a supported Linux host with OpenWrt build prerequisites, git, Python3, OpenSSL
and sufficient disk/RAM. From this directory:
  python3 tools/provision.py --count 50 --output private
  bash build.sh "$PWD/private/AG26-0001.json"
The generator writes unique root/Wi-Fi credentials and labels.csv under private/.
Do not share private/, dist/, labels or built images publicly. The image contains
that unit's Wi-Fi key. For 50 production units, build a common approved image once
and inject per-unit configuration using a validated fixture procedure; the current
script uses per-unit image overlays for prototype convenience.

The build is pinned to OpenWrt v24.10.7, ramips/mt76x8, hilink_hlk-7628n (32MB
flash variant). Feed revisions are recorded in the build output; review/lock these
before production. The carrier patch enables I2C without changing flash partitions
or calibration. Never overwrite the module's bootloader, factory RF calibration or
MAC data with a generic dump from another unit.

No flash image has been compiled here: this Windows PC has no installed Linux/WSL
build environment. Source checks and mock application tests are not a cross-build.
A successful cross-build and hardware boot test remain required. Do not upload a
sysupgrade image into an arbitrary OEM web UI; OEM initial installation depends on
the module bootloader/partition layout. Keep UART/J7 recovery access available.

CARRIER CONTROLS / RELEASE GATES
MCP23008 address 0x20 from A2:A0 grounded. GP0=SIM_SELECT, GP1=MODEM_OFF,
GP2=MODEM_RESET_REQ; GP3..7 inputs. Hardware operations are disabled by default.
After a bench engineer confirms I2C bus and switch truth tables, set
gateway.main.hardware_validated=1 and gateway.main.i2c_bus to the detected bus.
Confirm SIM A/B polarity before selecting B. B may be a separate external SIM or
provisioned eSIM carrier; there is NO eSIM profile-download/LPA implementation.
Current switching is a deliberate rail power cycle; validate Quectel shutdown
requirements and replace with graceful shutdown before production release.
No automatic SIM failover or reset loops are enabled.
The script exposes power-cycle control; it intentionally does not guess a reset
pulse duration or SW3 GPIO0 ROM boot function. Both remain production test items.

BENCH ACCEPTANCE
Verify flash/RAM variant, backup calibration, bootloader recovery, UART baud,
I2C detection and reset topology. Test all 4 Ethernet jacks, DHCP and controller
web access; Wi-Fi setup and Wi-Fi controllers; APN/PIN/auth cases; USB enumeration;
each SIM path; power cycling; loss/restoration of cellular; saved configuration
after reboot; LAN-only admin access; invalid/unauthenticated RPC rejection; update
and recovery; brownout and power removal. Review US radio compliance and antenna
conditions separately. Current PCB still needs completed layout/electrical review.

PREVIEW
python -m http.server 8765 --bind 127.0.0.1 --directory preview
Open http://127.0.0.1:8765. This is an interactive visual design with clearly marked
sample data, not a live router session. It previews the intended product interface;
the supplied firmware pages currently run within the standard LuCI navigation.

PRIMARY REFERENCES
https://downloads.openwrt.org/releases/24.10.7/targets/ramips/mt76x8/
https://github.com/openwrt/openwrt/blob/v24.10.7/target/linux/ramips/dts/mt7628an_hilink_hlk-7628n.dts
https://github.com/openwrt/openwrt/blob/v24.10.7/target/linux/ramips/mt76x8/base-files/etc/board.d/02_network
https://openwrt.org/docs/guide-user/network/wan/wwan/ltedongle
