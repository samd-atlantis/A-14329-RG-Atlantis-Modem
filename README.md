# A-14329 RG Atlantis Modem

Hardware and development firmware for the Atlantis cellular gateway for Walchem controllers. The first ordered main board is **A-14329-MB00**.

The carrier combines an HLK-7628N Wi-Fi/router module, four Ethernet ports, a removable Quectel Mini PCIe cellular modem, USB-C service access and isolated AC power with parallel controller power terminals. Bluetooth and LoRa are omitted. MB00 uses the physical SIM; onboard eSIM U20 is an unpopulated future option.

## Current hardware snapshot

Start with `hardware/releases/A-14329-MB00/`. Its manifest identifies and hashes the latest saved EasyEDA schematic, PCB, assembly BOM/CPL and review evidence. The capture is the working design saved before this repository handoff; it is **not yet a verified copy of the exact files submitted with the PCB order**. Archive the actual order Gerbers, assembly selections and JLC order confirmation there when available.

`hardware/easyeda/` retains the full design history, routing scripts, references and intermediate exports for traceability. Proposed and intermediate files are not production inputs. `hardware/rev-a/kicad/` is an earlier concept and is not synchronized to MB00; do not fabricate it or treat its ERC as validation of the current board.

## Firmware

See `firmware/README.txt`, `firmware/MB00-bringup.txt` and `firmware/USB-C-service.txt`. Source includes an OpenWrt package, authenticated LuCI setup, cellular QMI configuration, per-unit provisioning, four controller links and a visual preview. No working flashable image or hardware boot test is claimed. The target is provisionally HLK-7628N, ramips/mt76x8, 32 MB flash; confirm the fitted module before building/flashing.

Run source checks:

```sh
python3 -m unittest discover -s firmware/tests -p 'test_*.py' -v
node firmware/tests/check.js
```

GitHub Actions runs these checks on Linux. They exercise mocked carrier control and UI behavior, not RF performance or physical hardware. The OpenWrt image build is a separate Linux build described in `firmware/README.txt`.

## Bring-up and release status

- Modem remains a separately sourced card. EG25-GL was the design reference; EC25-AF/AFDL Mini PCIe is under consideration. No replacement is approved until its exact pinout, reset behavior, firmware and carrier activation are checked.
- Latest saved EasyEDA DRC reports zero errors over 124 checks. Independent electrical audit and prototype verification remain incomplete.
- Validate physical-SIM default, USB host selection, regulator stability, LTE transmit supply droop, Ethernet center taps, all ports, Wi-Fi and recovery access.
- Verify 10 A distribution temperature rise, terminal soldering/fit, isolation and enclosure fit before production release.
- ST1/ST2 JAE NT4R1600 supports are currently separate-source mechanical hardware, absent from JLC assembly BOM/CPL. Their conversion into actual assembly components is outstanding.
- Remote fleet management/VPN equivalent to RMS is planned, not implemented. No WAN administration or controller port forwarding is enabled by the starter.

Keep per-unit passwords, SIM credentials, VPN keys, RF-calibration backups and provisioned images private. They are not repository deliverables. Third-party datasheets and libraries retain their original owners' rights; no blanket redistribution license is asserted.
