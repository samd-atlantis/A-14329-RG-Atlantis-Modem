"""Generate per-unit secrets locally. Output is private and must not be committed."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import secrets
import subprocess


def make_unit(serial, wifi_mac=None):
    if not re.fullmatch(r"[A-Za-z0-9-]{1,24}", serial):
        raise ValueError("Serial must be 1–24 letters, digits or hyphens")
    ssid = 'Atlantis-AUTO'
    if wifi_mac is not None:
        if not re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}', wifi_mac):
            raise ValueError('Invalid Wi-Fi MAC address')
        compact = wifi_mac.replace(':', '').upper()
        if int(compact[:2], 16) & 1 or compact == '000000000000':
            raise ValueError('Wi-Fi MAC must be a nonzero unicast address')
        ssid = 'Atlantis-' + compact[-4:]
    wifi_password = secrets.token_hex(12)
    admin_password = secrets.token_hex(12)
    # Password is stdin, never a command-line argument.
    hashed = subprocess.run(["openssl", "passwd", "-6", "-stdin"],
                            input=admin_password + "\n", text=True,
                            capture_output=True, check=True).stdout.strip()
    if not hashed.startswith("$6$"):
        raise ValueError("Expected SHA512-crypt password hash")
    return {"serial": serial, "ssid": ssid,
            "wifi_password": wifi_password, "root_hash": hashed}, admin_password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="AG26")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--wifi-mac", help="Actual Wi-Fi MAC for one unit; --count must be 1")
    parser.add_argument("--output", type=Path, default=Path("private"))
    args = parser.parse_args()
    if not 1 <= args.count <= 10000:
        parser.error("count must be 1..10000")
    if args.wifi_mac and args.count != 1:
        parser.error('--wifi-mac requires --count 1')
    args.output.mkdir(parents=True, exist_ok=True)
    os.chmod(args.output, 0o700)
    # Exclusive creation prevents inadvertently replacing an existing credential set.
    with (args.output / "labels.csv").open("x", newline="", encoding="utf-8") as labels:
        os.chmod(args.output / "labels.csv", 0o600)
        writer = csv.writer(labels)
        writer.writerow(["serial", "ssid", "wifi_password", "admin_username", "admin_password", "setup_url"])
        for number in range(args.start, args.start + args.count):
            unit, password = make_unit(f"{args.prefix}-{number:04d}", args.wifi_mac)
            path = args.output / (unit["serial"] + ".json")
            with path.open("x", encoding="utf-8") as file:
                json.dump(unit, file, indent=2)
            os.chmod(path, 0o600)
            label_ssid = unit['ssid'] if args.wifi_mac else 'PENDING: Atlantis-<Wi-Fi MAC suffix>'
            writer.writerow([unit["serial"], label_ssid, unit["wifi_password"], "root", password, "https://10.0.100.7"])
    print(f"Created {args.count} unit records. Credentials are in {args.output}; do not publish them.")


if __name__ == "__main__":
    main()
