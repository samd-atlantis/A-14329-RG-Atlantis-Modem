# A-14329 RG Atlantis Modem

Hardware and development firmware for the Atlantis cellular gateway for Walchem controllers. The first ordered main board is **A-14329-MB00**.

The carrier combines an HLK-7628N Wi-Fi/router module, four Ethernet ports, a removable Quectel Mini PCIe cellular modem, USB-C service access and isolated AC power with parallel controller power terminals. Bluetooth and LoRa are omitted. MB00 uses the physical SIM; onboard eSIM U20 is an unpopulated future option.

## Current hardware snapshot

Start with `hardware/releases/A-14329-MB00/`. Its manifest identifies and hashes the latest saved EasyEDA schematic, PCB, assembly BOM/CPL and review evidence. The capture is the working design saved before this repository handoff; it is **not yet a verified copy of the exact files submitted with the PCB order**. Archive the actual order Gerbers, assembly selections and JLC order confirmation there when available.

`hardware/easyeda/` retains the full design history, routing scripts, references and intermediate exports for traceability. Proposed and intermediate files are not production inputs. `hardware/rev-a/kicad/` is an earlier concept and is not synchronized to MB00; do not fabricate it or treat its ERC as validation of the current board.

## Firmware

Start with [the programming procedure](firmware/PROGRAMMING-MB00.txt) and [firmware overview](firmware/README.txt). Source includes authenticated LuCI setup, QMI cellular networking, per-unit provisioning, four controller links and a visual preview. The separate GitHub cross-build produces credential-free development images; check its actual result and [validation record](firmware/VALIDATION-MB00.txt). No hardware boot test or production qualification is claimed. The target remains HLK-7628N, ramips/mt76x8, **32 MB flash**; confirm the fitted module's memory and partition layout before flashing.

[Factory provisioning](firmware/FACTORY-PROVISIONING.txt) prepares a private identity bundle for each unit using one common image. The fixture still needs first-board testing. Routine updates preserve identity and site configuration; factory reset of a common-image unit erases its writable identity and requires reprovisioning.

Run source checks:

```sh
python3 -m unittest discover -s firmware/tests -p 'test_*.py' -v
node firmware/tests/check.js
```

GitHub Actions runs these checks on Linux. They exercise mocked carrier control and UI behavior, not RF performance or physical hardware. The OpenWrt image build is a separate Linux build described in `firmware/README.txt`.

The build now pins OpenWrt **25.12.6**. After compilation, separate image checks inspect the actual kernel/device tree and installed filesystem against the exact build source. Check both workflow results; passing source tests alone does not establish a usable firmware image. The [factory recovery notes](firmware/HLK-FACTORY-RECOVERY.txt) distinguish USB serial console access from the arriving module's still-to-be-qualified initial loading procedure.

## Bring-up and release status

- Ordered modem is **EC25AFFA-MINIPCIE**. Its used interface pins match the carrier. J9 takes a **nano-SIM**; U20 remains absent. Actual carrier activation and modem firmware still need bench verification.
- Independent saved-design audit is complete: see [audit disposition](hardware/audits/AUDIT-MB00.txt). 285 critical pin checks passed; routed pad-bearing nets and native ground fills are connected. The current-geometry KiCad check found no short/clearance/drill errors under the translated rules, with documented warnings and translation limits.
- Q3's overlapping schematic wires have a separate corrected native candidate. The saved PCB assigns those pins correctly; frozen order-handoff files are unchanged. Import/review/ERC of the candidate remains necessary before a future schematic-to-PCB sync.
- Modem supply reserve remains a prototype hold: 116 µF nominal fitted versus Quectel's ≥470 µF Mini PCIe recommendation. The [power review](hardware/audits/mb00-electrical/power-addendum.txt) explains why blindly adding a capacitor is also inappropriate and gives the measurement/ECO plan.
- Validate physical-SIM default, USB host selection, regulator stability, LTE transmit supply droop, Ethernet center taps, all ports, Wi-Fi and recovery access.
- User confirmed 4 layers, 1.6 mm, 1 oz outer copper and JLC04161H-7628. Actual submitted Gerbers/BOM/CPL are still not reconciled. Verify 10 A temperature rise, terminal soldering/fit, isolation and enclosure fit before production release; the mains buses measure 4.064 mm with 1.7 mm terminal stems.
- ST1/ST2 JAE NT4R1600 supports are currently separate-source mechanical hardware, absent from JLC assembly BOM/CPL. Their conversion into actual assembly components is outstanding.
- [Atlantis portal](portal/README.md) now has a local customer preview, server-side site permissions, proxy configuration and staged WireGuard enrollment. Firmware source includes WireGuard; remote access remains disabled until a hub and unit keys are configured. No public WAN device ports are opened. Hosting, actual account/MFA enrollment and real-controller acceptance remain pending.

Keep per-unit passwords, SIM credentials, VPN keys, RF-calibration backups and provisioned images private. They are not repository deliverables. Third-party datasheets and libraries retain their original owners' rights; no blanket redistribution license is asserted.
