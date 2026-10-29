# Walchem cellular gateway — Rev A preliminary design

Date: 2026-10-27. Status: Rev A1 native KiCad capture available; not fabrication release.

## Native KiCad update

Open [the KiCad project](kicad/walchem_gateway.kicad_pro) or [native schematic review](kicad/review.html). The native root plus seven child sheets, pin-map CSV, local libraries, netlist, BOM and actual KiCad ERC report supersede the functional SVGs for connectivity. See [engineering review and layout gates](kicad/design-review.md) and `kicad/exports/verification.json` for the completed checks and unresolved physical choices.

The sections below describe the original concept and numerical model; they are retained as history. In particular, the earlier statement that no CAD executable was available is superseded by the project-local KiCad 9.0.7 validation runtime. The original TXS02326A candidate is replaced in the native design by TS3A44159PW.

## Confirmed requirements

- United States installation; 120 VAC, 60 Hz input.
- Four external 10/100 Ethernet LAN ports.
- Quectel EG25-GL Mini PCIe cellular modem.
- Physical nano-SIM plus provider-provisioned eUICC, one active at a time.
- Ai-Thinker Ai-WB2-13 retained for Wi-Fi and BLE setup.
- Wi-Fi connectivity for compatible controllers is required.
- No LoRa radio, antenna, or related power load in this revision.
- Initial production quantity: 50.

## Deliverables and limitations

Run `python generate.py` from this directory. It generates three SVG functional schematic sheets, an HTML review package, power-budget CSV and a modem load-step sensitivity sweep. Python standard library only.

The sheets show named nets and functional circuits. They are NOT KiCad electrical schematics, contain no validated package pin numbers, and have not passed ERC. Device footprints, connector pin mapping, component ratings, and exact support circuits must be completed against controlled manufacturer documentation before layout. No CAD or SPICE executable was found in the checked environment. The numerical simulation is an explicitly assumed charge-deficit model, not a switching-regulator simulation.

## Architecture and design decisions

PS1: Mean Well IRM-20-5 candidate, isolated 5 V / 20 W. Retain a 30 W alternative until temperature derating and measured simultaneous loads are known. Mains input: J1 L/N, fuse F1 on line, coordinated surge protection after fuse across L/N, filtering as required. Primary and secondary grounds never connect. Protective earth/chassis arrangement is enclosure dependent. Creepage/clearance, surge category, pollution degree, altitude, fuse interrupt rating and accessible connector protection remain release gates.

U1: Hi-Link HLK-7628N candidate, ordered as 128 MB RAM / 32 MB flash. Four LAN MDI channels connect to four matching MagJacks. Fifth Ethernet channel unused; do not connect termination by assumption. USB host connects directly to modem USB with low-capacitance ESD. Native Wi-Fi is also available on this router module; use it as the primary candidate for IP controller networking. Disable its radio if a validated alternative replaces it.

U2/U3: separate TI TPS62132 fixed 3.3 V, 3 A buck candidates for router and modem. TPS62133 is a 5 V variant and must NOT be substituted. Use manufacturer reference power-stage values, layout and approved output-capacitance range. High bulk-capacitance sweep results do not authorize arbitrary capacitance additions. Modem rail enable allows independent recovery; ensure no GPIO/SIM/USB back-power when disabled. Exact Mini PCIe supply limits and start/reset timing are pending verification against Quectel EG2x-GL Mini PCIe Hardware Design V1.1.

U4: EG25-GL Mini PCIe, exact carrier-approved ordering code pending. Connect main and diversity antenna ports to matching coax/SMA assemblies. GNSS not populated. Do not apply raw-module VBAT assumptions to a Mini PCIe card.

U5: Ai-WB2-13 on a dedicated switched 3.3 V branch, UART TX/RX to the router, reset/boot service pads and GPIO control. UART pin availability and voltage compatibility on the exact router-module revision must be checked. BLE setup and Wi-Fi setup need application firmware; neither exists merely because the module is fitted. Do not use UART transparent mode as an assumed Ethernet/IP bridge. Router-native Wi-Fi is the initial path for controller IP traffic; Ai-WB2-13 provides BLE/local provisioning, with integration to the router through authenticated setup commands. Concurrent AP/STA operation, controller client count, isolation and channel behavior need bench testing. Ai-WB2-13 has an onboard antenna: provide antenna keepout and a nonmetallic RF window. Metal enclosures require reconsidering antenna/module variant.

U6: SIM selector functional placeholder. Route SIM_VCC, CLK, RST and bidirectional IO to only the selected SIM; inactive branch must be unpowered and isolated. Do not wire two SIMs in parallel. TI TXS02326A is a candidate architecture requiring full interface review (its local LDO/baseband interface is not a drop-in four-pole passive switch). Exact selector and eUICC are deliberately not released. Firmware must detach modem, disable SIM power, select branch and reinitialize using verified manufacturer sequence. Carrier failover is distinct from eSIM profile provisioning. No simultaneous dual-cellular service.

## Numerical model assumptions

Power budgets: modem 0.2/1.0/2.0 A, router 0.25/0.6/1.0 A, Ai-WB2-13 0.08/0.2/0.35 A at 3.3 V for idle/working/coincident peak. All are design allowances, not measurements. Router manual specifies >=1 A supply and lists 850 mA peak; external loading and margins remain to be validated. Buck efficiency 88%, auxiliary 5 V load 0.5 W. Separate 5 V current budget is compared with 20 W supply at assumed 70% usable rating; this is a sensitivity allowance, not a manufacturer's temperature curve.

Transient model: 1.8 A modem load increment, 3.3 V initial nominal or -2%, 20 mOhm ESR plus interconnect allowance, capacitor tolerance -20%, regulator incremental current approaches load exponentially with assumed tau 25/100/250 us. Integrated charge deficit is dI*tau*(1-exp(-t/tau)); terminal voltage deducts charge/C and instantaneous residual-current ESR. No restoration model; not intended to predict recovery, loop stability, current limit, soft start, switching ripple or EMI. 3.10 V threshold is an internal screening target, NOT a verified Quectel operating minimum. Sweep 470–3300 uF is sensitivity analysis, not approved BOM capacitance. Confirm source impedance, tolerance, ESR, DC bias and actual load waveform in hardware.

## Required engineering completion

1. Obtain controlled exact-SKU Quectel hardware guide, host/firmware interface guide and carrier approval evidence.
2. Pin-map all symbols, choose actual MagJacks and support circuits, select eUICC/provider and SIM selector.
3. Validate supported current Linux/OpenWrt build for router, QMI/USB, firewall, VPN and update/recovery. Manufacturer's old SDK is not a production firmware baseline.
4. Demonstrate BLE provisioning and Wi-Fi controller connectivity, including simultaneous setup AP if required.
5. Complete native CAD schematics, footprints, ERC, stackup, constraints and layout review.
6. Run regulator manufacturer transient models in supported simulator, then test load steps and modem attach at weak signal; perform startup, thermal, mains safety and EMC testing.
7. Production test must verify four LAN ports, USB modem, both SIM paths, eSIM provisioning, Wi-Fi/BLE and independent modem recovery.

## Primary references

- Quectel EG25-GL Mini PCIe: https://www.quectel.com/product/lte-eg25-gl-mini-pcie/
- Hi-Link hardware manual: https://h.hlktech.com/download/HLK-7628N/1/HLK-7628N%E7%A1%AC%E4%BB%B6%E6%89%8B%E5%86%8CV2.6.pdf
- Mean Well: https://www.meanwell.com/Upload/PDF/IRM-20/IRM-20-SPEC.PDF
- TI TPS62132 and vendor SPICE models: https://www.ti.com/product/TPS62132
- TI SIM selector candidate: https://www.ti.com/product/TXS02326A
- Ai-Thinker module: https://en.ai-thinker.com/pro_view-111.html
- Walchem network requirements: https://www.walchem.com/TechSupport/Walchem-Controller-and-Walchem-Fluent-Security-Profile.pdf
