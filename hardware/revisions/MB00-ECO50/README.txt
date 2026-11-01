A-14329-MB00 ECO50 - ENGINEERING REVISION - 2026-10-31

STATUS: LOCAL NATIVE DESIGN UPDATED; NOT RELEASED FOR FABRICATION.
This is a future-revision engineering candidate. It does not change the PCB or
assembly order already at JLC. Frozen hardware/releases/A-14329-MB00 is unchanged.
EasyEDA signed out during this session and returned "Failed to save the project
data". No successful cloud import/save or native ERC/DRC is claimed for ECO50.
The new native files must be imported/reviewed after sign-in. The existing PCB2
and paused portal changes were not edited.

DESIGN FILES
pcb-eco50-engineering.epro2        Complete native PCB plus component libraries.
schematic-eco50-engineering.epro2  Schematic, corrected Q3, new parts/polarity.
pcb-before-eco50.epro2            Download of working PCB1 before these edits.
ENGINEERING-BOM.csv / ENGINEERING-CPL.csv
                                101 exactly matching assembly designators.
                                Engineering purchasing review only.
usb-layout-review.png / modem-capacitor-review.png
                                Scaled views generated from the native records.
validation.json / geometry-checks.json / review-summary.json
                                Checks and their limits.
kicad-audit/                      AUDIT ONLY. NEVER FABRICATE THIS TRANSLATION.
                                CAD copy is local/regenerated; compact JSON
                                conversion and DRC evidence is committed.

CHANGES
1. U19 remains TPD2EUSB30DRTR / C97502, populated in this new revision.
   Moved from native (3600,325) to (3500,285) mil:
     old CPL center 91.440,8.255 mm; new 88.900,7.239 mm.
   A conservative 4.0 mm-wide U16 body and 1.1 mm U19 envelope have 0.879 mm
   horizontal clearance. Rerouted the ESD shunt branches, ground connection and
   interfering low-speed CONSOLE_TX segment. The USB signal main path is retained.
   This fixes the body interference; it is different from omitting U19 on the
   already-ordered prototype. Confirm actual courtyards and assembly DFM in EasyEDA.

2. Coordinated modem power TEST configuration (not a qualified production ECO):
   C25: GRM32ER61C476KE15L 47uF ceramic -> JIERR MA10V470M6X8,
        470uF, 10V, +/-20%, polymer, 20mOhm at 100kHz, C46550459.
        Authored 6.3x7.7 mm can / maximum 6.8 mm base footprint. Pad 1 POSITIVE
        connects 3V3_MODEM; pad 2 NEGATIVE connects GND_ISO. Added explicit '+'
        on schematic and PCB. Reserve 8.5 mm height; no verified 3D model assigned.
        Center moved to (4685.0394,1435) mil = (119.000001,36.449) mm.
        Assembly polarity: positive pad center (119.000001,33.999) mm;
        negative pad center (119.000001,38.899) mm in the exported CPL datum.
        Cap base stays outside the nominal 30 mm-wide card envelope by 0.457 mm;
        actual module/socket/base tolerances and card insertion need physical fit.
   L2: SWPA5040S2R2NT 2.2uH -> Sunlord MWSA0503S-1R0MT,
       1uH +/-20%, C408355. Replaced the land pattern as well as the part/value.
       Manufacturer recommended lands: 1.9 x 2.5 mm, 2.2 mm inner gap.
       The Sunlord table lists Isat columns 8A Max / 10A Typ and heat-rating
       current 7.8A Max / 8.5A Typ; do not call catalog 10A a guaranteed minimum.
       Actual inductance versus bias, ripple and temperature still need validation.
   C22: 0603B332K500CT 3.3nF -> Samsung CL10B223KB8NNNC,
        22nF 50V X7R +/-10% 0603, C21122. Nominal soft-start estimate 11 ms.
   C61: same original 1uF part, moved to (4685.0394,1660) mil to clear C25 lands.
   C23=22uF and C24=47uF retained: total nominal bulk now 539uF versus 116uF.
   The polymer +/-20% tolerance and MLCC bias mean 539uF is NOT a guaranteed
   minimum effective capacitance. C25 is a polarized replacement, not drop-in
   rework on the old 1210 footprint. Do not install C25 alone on the old board.

   WHY THIS IS STILL A TEST CONFIGURATION:
   Quectel specifies >=470uF low-ESR bypass for the Mini PCIe card. TI's adjacent
   1uH/400uF effective test point is more promising than the existing 2.2uH large
   bank, but the mixed 470uF polymer plus ceramics at 5V input is not a published
   guaranteed stability point. This design does NOT establish that the TPS62132
   loop is stable at all loads/temperatures. Compared with the earlier one-board
   P1 contingency, C25 replaces one 47uF MLCC rather than adding a new 470uF can;
   exact selected parts and capacitance differ and require their own validation.
   The next decision is measured engineering-board qualification or a regulator
   redesign with explicitly supported capacitance, not automatic batch assembly.

   Start without the modem. Scope 3V3_MODEM at J8 and 5V_ISO during startup,
   light load, approximately 0.1A->2.7A steps and load release, then LTE attach/
   upload/reconnect with router/Wi-Fi/Ethernet load and closed-enclosure heat.
   Reject sustained ringing, hiccups, current limiting, excessive temperature,
   overshoot above 3.6V, or card-side voltage below 3.0V after startup. Verify
   stability across load/temperature, preferably measured loop response. See
   hardware/audits/mb00-electrical/power-addendum.txt for the full test plan and
   20W PSU thermal budget. No switching simulation or bench measurement is claimed.

3. Applied the four-record Q3 schematic wire correction prepared by the previous
   audit: drain wire exits upward, source wire downward, with labels following.
   All 544 schematic pin keys now agree unambiguously with PCB pad assignments.
   No Q3 copper net reassignment was necessary.

4. Removed the isolated 0.001814 mm USB_HOST_DP fragment 458618fd5813397f.
   The functional router-to-USB-mux connection is retained.

5. Added explicit AC_L_IN / AC_L_FUSED / AC_N to GND_ISO rule selectors using
   PRIMARY_GROUND_9MM. Moved the inner ground plane boundary near the primary
   region from y=1500 to y=1550 mil. Conservative distance from primary copper
   to the entire planned plane outline is 9.09216 mm on each inner layer, before
   any native cutouts/clearances. This is CAD geometry, not a safety certification.
   Removed both stale cached fills. Rebuild pours and verify actual resulting
   copper/return paths in native EasyEDA. The new ground connections rely on that
   rebuild. Existing primary-secondary signal spacing target remains 8 mm.

COMPONENT SOURCING OBSERVATIONS (not reserved inventory)
C408355: EasyEDA system library showed 3,445 JLC parts during this session.
C21122: JLC listing showed >1 million available.
C46550459: JLC indexed listing showed >87,000 available; recheck at order time.
The new cap/inductor footprints are locally authored from manufacturer drawings.
JLC must review the selected part/footprint match and C25 polarity/rotation;
do not treat matching CSV designators as assembly approval.

VALIDATION
285 critical pin/net expectations: pass.
544 schematic pin keys: exact agreement, no overlapping-label conflicts.
Moved/new pads versus all routed copper and other pads: no detected conflicts
under the local conservative screen. Edited signal nets have no pad-bearing opens.
KiCad 9.0.7 audit translation: zero copper-short/clearance/drill errors under
translated rules. 21 warnings remain (14 dangling tracks, 6 dangling vias,
1 generic copper sliver); all 7 unconnected reports are GND_ISO with native pours
omitted. This is not "zero DRC" or evidence that final ground copper is connected.
The new device data/schematic symbol, manufacturing courtyards, mask/paste,
filled planes and 3D are not validated by that translation. Native ERC/DRC,
rebuilt planes, polarity/DFM review and actual power/mechanical tests remain open.
All frozen-release manifest hashes verified unchanged.

ALREADY-ORDERED BUILD
JLC's email concerns U19 interference with U16 on the existing PCB. U19 may be
omitted without a jumper because it is shunt USB ESD protection; this removes
the added protection from J14, not the USB data path. Actual JLC disposition
has not been submitted/confirmed by this work. Do not send ECO50 BOM/CPL with
assembly49 Gerbers. The larger capacitor and changed footprint require a new
layout revision or separately engineered and validated prototype rework.

OTHER FINDINGS THAT CANNOT BE CLOSED BY THESE EDITS
10A applies to TOTAL CN1 input including PS1. Terminal/copper heating, protective
earth, upstream protection and mains isolation remain physical qualification
items. F1 protects only the PSU branch. No fixed external-feed current allowance
is established. IRM-20-5 enclosed thermal derating, actual HLK memory/bootloader,
own flash/RF calibration backup/recovery, NT4 supports, real Ethernet/Wi-Fi/LTE,
enclosure/cable fit and full functional acceptance remain open.
No firmware package, frozen manufacturing release, JLC order, paid transaction,
portal/server, production serial or external service was changed here.

REPRODUCE
python hardware/revisions/MB00-ECO50/build_eco50.py
python hardware/revisions/MB00-ECO50/check_eco50.py
python hardware/revisions/MB00-ECO50/plane_envelope.py
& .tools/kicad/bin/python.exe hardware/revisions/MB00-ECO50/check_eco50.py --convert-only
& .tools/kicad/bin/kicad-cli.exe pcb drc hardware/revisions/MB00-ECO50/kicad-audit/mb00-audit-only.kicad_pcb --format json --severity-all --output hardware/revisions/MB00-ECO50/kicad-audit/kicad-drc.json
python hardware/revisions/MB00-ECO50/export_review.py
Review exports need Pillow from the existing .tools/commission-deps directory;
the native geometry screen uses only Python standard library and existing repo
geometry helpers. The plane-envelope calculation additionally uses Shapely2.

PRIMARY / SUPPLIER REFERENCES
TI TPS62132 and LC/SS design:
https://www.ti.com/lit/ds/symlink/tps62132.pdf
https://www.ti.com/lit/an/slva463a/slva463a.pdf
Quectel EC25 Mini PCIe V2.6, section 3.5:
https://forums.quectel.com/uploads/short-url/hOpbQpopPcLwn4bwSMFRSpJa2kk.pdf
JIERR MA-series, package drawing p2 and exact part p3:
https://atta.szlcsc.com/upload/public/pdf/source/20260306/24758A4FC016E80367B87853635CDCC1.pdf
Sunlord MWSA-S, package/recommended lands p2 and 0503 electrical table p4:
https://atta.szlcsc.com/upload/public/pdf/source/20231024/D9DB0CBBB5804BFBC9233D4A02F4216A.pdf
https://jlcpcb.com/partdetail/Sunlord-MWSA0503S1R0MT/C408355
https://jlcpcb.com/partdetail/jieerrui-MA10V470M6X8/C46550459
https://jlcpcb.com/partdetail/21834-CL10B223KB8NNNC/C21122
