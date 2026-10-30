Atlantis A-14329-MB00 commissioning and labels
2026-10-30 - host-side candidate; not demonstrated on an arriving board

The commissioning routine assigns a permanent enclosure serial, generates that
unit's private firmware record, then compares a captured post-boot readback with
the enclosure label. It never flashes a router or approves hardware acceptance.
The public serial belongs to the enclosure/assembly, not to its SIM, IMEI, IP,
customer, facility, or replaceable cellular card. Never recycle it.

EXISTING ATLANTIS TOOLS
The supplied ESP32 Configurator - Rev 2.exe was inspected without executing it.
Its print_esp32_software_label uses a 2000x3000 canvas, two QR sections, CCW print
rotation, Windows GDI printing and two copies to \\Atech-DC.atechllc.local\Label 1.
The companion commission_labels.py follows that layout and printer workflow,
using the supplied executable's Atlantis logo, adding the permanent serial and
the router's HTTPS URL/root login. Font rendering uses installed Arial on Windows;
it is a maintained companion implementation, not a patched executable.

The original program uses esptool and ESP flash offsets. It CANNOT flash this
HLK-7628N/MediaTek router. Do not add an OpenWrt binary to its ESP catalog with
invented offsets. The actual OEM bootloader/RAM-boot/install/recovery procedure
still needs the first board. No universal USB-DFU loader is claimed.

CellModemInput 260924.exe is the current RUT241 record-entry application. Its
qrsplitcallback reads five semicolon-delimited fields and uses serial, IMEI and
LAN MAC in the first three. cellmodem_record.py produces compatible scan artwork
and a private draft with the existing U_ModSerNum/U_ModIMEI/U_ModLanMac and
credential field names. It performs NO SAP/Telnyx/API/database writes or SIM
activation. The existing application has one controller field set; four-controller
customer records require a later reviewed extension. Keep that work separate from
getting this router qualified. Manufacturer/model selections in the existing app
may need approved Atlantis/A-14329-MB00 entries in its local configuration.

PERMANENT REMOTE ADDRESS - selected by the user on 2026-10-30:
  https://connect.atlantisllc.com/u/<permanent-enclosure-serial>
For example: https://connect.atlantisllc.com/u/AG26-000001
The public enclosure label shows the human-readable URL and its QR code. The
private setup label also shows that same remote URL, with its local setup QR
clearly identified as LOCAL LOGIN. The URL/serial pairing is saved once in the
registry and identity/readback records; changing or deleting it is refused.
Keep this hostname and /u/serial path permanent, including across later portal
redesigns. SIM, cellular IP, replacement cellular card, customer or facility changes
must never require another enclosure address. Public links still require login
and permission checks; scanning the QR never grants access by itself.

The selected address is NOT LIVE: DNS, HTTPS hosting and remote access still need
deployment when the user resumes the paused portal/server work. Label creation
does not configure DNS, publish a site or establish a tunnel. Do not represent it
as working remote access or ship without testing the actual end-to-end link.
The CellModemInput identity QR, Wi-Fi connection QR and enclosure remote URL QR
have separate purposes; keep their labels distinct.

SOURCE PROVENANCE (only reviewed label behavior/logo were reused)
ESP executable SHA256:
  08a49b759aec01d64b2cc153399d97ef31956aa8991d70132770664709995495
CellModemInput executable SHA256:
  a8030ff73f9bd5ea6152dcafabaeabbd26fd50588307d74e7f5d750bfa304c5f
Both are Python 3.11 PyInstaller packages. Their main programs, credential
constants, packaged runtime and full extracted code are not copied into this
repository. The supplied executables stay local and are ignored by Git.

HOST SETUP
Use a trusted configuration PC with Python, Git for Windows/OpenSSL, and the
existing Label 1 Windows driver/media settings. In the repository root:
  python -m venv .tools/commissioning-env
  .tools/commissioning-env/Scripts/python.exe -m pip install -r firmware/commissioning/requirements.txt
Use that interpreter for the commands below. On Windows put Git's usr/bin folder
on PATH if openssl is unavailable. Source/QR tests also require requirements-test.txt.
No label/printing packages are added to the router firmware itself.

1. ASSIGN SERIAL AND PREPARE PRIVATE IDENTITY
Use ONE authoritative, backed-up private fleet.sqlite3 for all configuration
stations. Do not initialize independent production registries or copy an old
registry snapshot onto another active station. A transaction prevents duplicate
allocation by concurrent callers sharing the same registry. Store it on the
authoritative factory host with its local SQLite storage; do not assume a network
share supports safe SQLite locking. Back up the registry and private unit records
with the manufacturing backup process. Archive the numbering prefix and history.

  python firmware/tools/commission.py prepare --registry firmware/private/fleet.sqlite3 --output firmware/private/units --operator Sam

The example local allocator uses AG26-000001, AG26-000002, etc. A different approved
prefix can be supplied with --prefix. No production IDs were issued during tests.
If an existing factory configurator already allocated the permanent serial:
  python firmware/tools/commission.py prepare --registry firmware/private/fleet.sqlite3 --output firmware/private/units --operator Sam --serial YOUR-EXISTING-ID

The ID is preserved exactly, duplicate registration is refused, and IDs are never
deleted/recycled. Use letters, digits and hyphens, maximum 24 characters, matching
the router's validated unit-record format. A failed/interrupted job may leave a
gap; do not fill gaps by recycling numbers. Preparation creates:
  unit.json              serial + unique Wi-Fi key + root password hash
  credentials.csv        private setup credentials; SSID pending until readback
  identity.json          registry/file binding; PREPARED_NOT_VERIFIED
  acceptance.json        serial/operator filled; physical tests remain NOT_TESTED
  enclosure-label.txt    public model + serial + permanent remote URL, no credentials
Keep the setup password sheet inside controlled commissioning storage/the inside
of the enclosure. Do not publish it on the outside serial label or in Git.

2. QUALIFY AND LOAD THE ROUTER
Follow PROGRAMMING-MB00.txt and FACTORY-PROVISIONING.txt: power/capacitor hold,
actual memory/bootloader, this unit's backups and recovery, then a qualified
installation and first boot. Choose the exact inspected candidate in HANDOFF-MB00.
The running r10 cross-build is NOT replaced just for these host-only tools.

Supply the newly prepared unit.json to make_factory_bundle.py or the private-image
recipe. Example once the matching common image/manifest have passed inspection:
  python firmware/tools/make_factory_bundle.py --unit firmware/private/units/AG26-000001/unit.json --manifest manifest.json --image IMAGE-squashfs-sysupgrade.bin --output firmware/private/units/AG26-000001/factory

This stages the same serial into gateway.main.serial during the existing first-boot
routine. No hand-entered second serial is needed. J14 USB-C is the router UART;
Ethernet is preferred for transferring firmware once compatible OpenWrt boots.
J17 is the modem USB connection; unplug it for normal router/modem operation.

3. CAPTURE READBACK AND VERIFY THE ENCLOSURE
Run the current tools/collect-device.sh on this router over the authenticated
console/SSH and save its JSON privately beside this unit's records as device.json.
It reads the permanent internal Wi-Fi MAC and the separate effective LAN MAC.
It does not query or change SIM subscriptions, modem power, GPIOs or flash.
Scan/type the actual enclosure serial, rather than blindly copying the expected
value from the unit file. Match the serial, valid router identity, provisioned
state, actual Wi-Fi MAC and Atlantis-<MAC4> SSID:
  python firmware/tools/commission.py verify --registry firmware/private/fleet.sqlite3 --unit firmware/private/units/AG26-000001/unit.json --probe firmware/private/units/AG26-000001/device.json --label-serial AG26-000001 --output firmware/private/units/AG26-000001/readback.json --labels-dir firmware/private/units/AG26-000001/labels

This renders the private setup label and public serial label after readback.
It does not print unless --print-labels is added. That option submits two setup
labels to the existing Label 1 queue; --printer overrides the exact queue name.
To print the public enclosure label with its permanent remote URL/QR instead,
add --print-labels --print-kind enclosure. Reprints can also use:
  python firmware/tools/commission_labels.py --unit-directory firmware/private/units/AG26-000001 --verification firmware/private/units/AG26-000001/readback.json --output firmware/private/units/AG26-000001/reprint --print --print-kind enclosure
The public label contains no Wi-Fi/admin password; the private setup label does.
No print job was submitted during development/testing. Windows queue acceptance
does not prove paper output: verify the media/orientation, scan both QR codes,
check that Wi-Fi and HTTPS reach the unit and authenticate with its unique login.

The setup label must show the final SSID, never Atlantis-AUTO. Readback.json records
the captured evidence hashes. It proves comparison only, not how the probe was
obtained, physical boot, successful login, cellular data or full acceptance.
The operator must capture it from the connected unit and complete acceptance.json.

4. PREPARE THE EXISTING RUT241 RECORD-ENTRY WORKFLOW
After modem/power qualification, scan the actual cellular card's IMEI and physical
SIM ICCID into a private identifiers.json, e.g. keys imei, iccid, apn (strings).
Do not substitute the Wi-Fi MAC for the LAN MAC or the IMEI for the enclosure ID.
  python firmware/tools/cellmodem_record.py --unit-directory firmware/private/units/AG26-000001 --verification firmware/private/units/AG26-000001/readback.json --identifiers firmware/private/units/AG26-000001/identifiers.json --output firmware/private/units/AG26-000001/cell-record

Scan cellmodem-identity-scan.png into the existing application's Serial Number
field. The QR contains serial/IMEI/LAN MAC/model only, no passwords. Verify all
three resulting values in the app. Review the private JSON draft before any manual
record entry. It is not an automatic import endpoint, a completed sales order or
a production approval. Customer/order/SIM/controller mapping is not guessed.

REPRINT, RESET AND REPAIR
Reprint with commission_labels.py using the existing unit directory and readback;
never allocate another serial merely to reprint. Reuse the original unit record
for an authorized recovery. Routine upgrades preserve it. A full factory reset of
the common-image overlay erases the device's copy and requires restoring that
original private record; the physical label and authoritative registry remain.
Do not enable a customer full-reset feature until retained identity is qualified.
Changing the SIM or cellular card never changes the enclosure serial; record the
new ICCID/IMEI and replace the separate record-entry label as needed. A router-board
replacement changes its MAC and needs a controlled service record/rebinding; the
tool deliberately refuses to silently bind an existing serial to another radio.

TEST SCOPE
Automated tests check concurrent allocation, duplicate/replacement rejection,
private-record integrity, captured readback, label gates, actual QR decode before
and after rotation, the legacy positional scan contract and mocked printer calls.
They do not contact a router, queue, SAP, Telnyx or customer controller. Physical
printing/scanning, authentication, flash/recovery, Ethernet/Wi-Fi/cellular and
power/thermal tests still have to be performed when the first boards arrive.
