"""Read-only check of a captured device probe and a private-unit image manifest.

Does not connect to a router or flash anything. Passing permits the NEXT step,
on-device sysupgrade -T; it is not permission to bypass initial-install checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def assess(probe, manifest, image):
    blockers = []
    if probe.get("schema") != "mb00-device-probe-1":
        blockers.append("Unrecognized device-probe format")
    if probe.get("board_name") != "hilink,hlk-7628n":
        blockers.append("Board identity is not upstream HLK-7628N")
    if probe.get("distribution") != "OpenWrt":
        blockers.append("OEM/unknown firmware needs a separately verified initial-install procedure")
    parts = {}
    for line in str(probe.get("mtd", "")).splitlines():
        match = re.fullmatch(r'mtd\d+:\s+([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+"([^"]+)"', line.strip())
        if match:
            if match[2] in parts:
                blockers.append("Duplicate MTD partition label: " + match[2])
            parts[match[2]] = int(match[1], 16)
    for name, size in {"u-boot": 0x30000, "u-boot-env": 0x10000,
                       "factory": 0x10000, "firmware": 0x1fb0000}.items():
        if parts.get(name) != size:
            blockers.append("Unverified 32MB flash layout: " + name)
    if manifest.get("board") != "A-14329-MB00" or manifest.get("profile") != "hilink_hlk-7628n":
        blockers.append("Manifest is for a different board/profile")
    release = json.loads((Path(__file__).resolve().parents[1] / "build-lock.json").read_text())["release"]
    if manifest.get("openwrt_release") != release:
        blockers.append("Image does not match the current locked OpenWrt security baseline: " + release)
    if manifest.get("mode") != "private-unit-development":
        blockers.append("Validation-only images have no unit credentials and must not be programmed")
    if manifest.get("requires_confirmed_flash_bytes") != 33554432:
        blockers.append("Unexpected image flash capacity")
    if not re.fullmatch(r"[A-Za-z0-9-]{1,24}", manifest.get("unit_serial", "")):
        blockers.append("Image manifest is missing its unit serial")
    elif probe.get("provisioned") == "1" and probe.get("serial") != manifest["unit_serial"]:
        blockers.append("Image belongs to a different provisioned unit")
    if "sysupgrade" not in image.name:
        blockers.append("Select the sysupgrade image; initramfs is not a flash-upgrade image")
    entries = [a for a in manifest.get("artifacts", []) if a.get("file") == image.name]
    if len(entries) != 1:
        blockers.append("Image is absent or duplicated in the build manifest")
    else:
        item = entries[0]
        if image.stat().st_size != item.get("bytes") or hashlib.sha256(image.read_bytes()).hexdigest() != item.get("sha256"):
            blockers.append("Image size or SHA256 does not match the manifest")
    return blockers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    args = parser.parse_args()
    blockers = assess(json.loads(args.probe.read_text()), json.loads(args.manifest.read_text()), args.image)
    if blockers:
        print("STOP: do not program this image.")
        for blocker in blockers:
            print("- " + blocker)
        raise SystemExit(1)
    print("Read-only preflight passed. Next: verify this unit's flash/calibration backup and recovery,")
    print("confirm actual flash chip/partition offsets, then run sysupgrade -T on the device.")
    print("MTD sizes alone do not prove partition offsets or OEM bootloader compatibility.")
    print("No flash write performed. Prototype hardware and firmware acceptance remain required.")


if __name__ == "__main__":
    main()
