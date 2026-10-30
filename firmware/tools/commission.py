"""Prepare permanent identity and verify a captured post-boot probe. Never flash.

These are fixture/operator tools, not a network service. No hardware connection,
bootloader operation, GPIO control or acceptance approval is performed here.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time

from provision import make_unit
from serial_registry import open_registry, reserve, reserve_named
from device_address import unit_url

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_private(path, value):
    with Path(path).open('x', encoding='utf-8') as file:
        os.chmod(path, 0o600)
        json.dump(value, file, indent=2)
        file.write('\n')


def prepare(registry, output, operator, prefix='AG26', wifi_mac=None, serial=None):
    if not isinstance(operator, str) or not operator.strip() or len(operator) > 100:
        raise ValueError('Commissioning operator required')
    # Credential generation/validation precedes reservation, so an invalid MAC or
    # missing OpenSSL does not consume an ID. Secrets stay on the fixture only.
    unit, password = make_unit('PENDING', wifi_mac)
    source = 'factory-configurator' if serial else 'local-reservation'
    serial = reserve_named(registry, serial) if serial else reserve(registry, prefix)[0]
    unit['serial'] = serial
    remote_url = unit_url(serial)
    folder = Path(output)/serial
    folder.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(folder, 0o700)
    write_private(folder/'unit.json', unit)
    with (folder/'credentials.csv').open('x', newline='', encoding='utf-8') as file:
        os.chmod(folder/'credentials.csv', 0o600)
        writer = csv.writer(file)
        writer.writerow(['serial', 'ssid', 'wifi_password', 'admin_username', 'admin_password', 'setup_url'])
        writer.writerow([serial, unit['ssid'] if wifi_mac else 'PENDING: actual Wi-Fi MAC required',
                         unit['wifi_password'], 'root', password, 'https://10.0.100.7'])
    acceptance = json.loads((ROOT/'acceptance-template.json').read_text())
    acceptance.update(serial=serial, operator=operator, date=datetime.now(timezone.utc).date().isoformat())
    write_private(folder/'acceptance.json', acceptance)
    write_private(folder/'identity.json', {'schema':'mb00-commissioning-1', 'serial':serial,
        'model':'A-14329-MB00', 'operator':operator, 'serial_source':source, 'unit_sha256':digest(folder/'unit.json'),
        'remote_url':remote_url, 'remote_service_status':'NOT_DEPLOYED',
        'identity_status':'PREPARED_NOT_VERIFIED', 'hardware_tested':False, 'production_approved':False})
    # Public enclosure artwork contains identity only. Wi-Fi/admin credentials
    # belong on a separate controlled setup record; no public QR is a password.
    (folder/'enclosure-label.txt').write_text('ATLANTIS\nA-14329-MB00\nSERIAL: '+serial+'\nREMOTE ACCESS: '+remote_url+'\n', encoding='utf-8')
    con = open_registry(registry)
    try:
        with con:
            con.execute('INSERT INTO commissioning(serial,unit_sha256,operator) VALUES(?,?,?)',
                        (serial, digest(folder/'unit.json'), operator))
            con.execute('INSERT INTO unit_addresses VALUES(?,?)', (serial, remote_url))
    finally:
        con.close()
    return folder


def verify(registry, unit_path, probe_path, label_serial, output):
    unit = json.loads(Path(unit_path).read_text())
    probe = json.loads(Path(probe_path).read_text())
    serial = unit.get('serial')
    if not isinstance(serial, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,24}', serial) or label_serial != serial:
        raise ValueError('Physical enclosure serial does not match its unit record')
    if (probe.get('schema'), probe.get('board_name'), probe.get('distribution'), probe.get('provisioned'), probe.get('serial')) != (
            'mb00-device-probe-1', 'hilink,hlk-7628n', 'OpenWrt', '1', serial):
        raise ValueError('Captured router identity does not match this commissioned unit')
    mac = probe.get('wifi_mac', '')
    if not isinstance(mac, str) or not re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', mac):
        raise ValueError('Missing or invalid permanent Wi-Fi MAC')
    compact = mac.replace(':', '').upper()
    if int(compact[:2], 16) & 1 or compact == '000000000000':
        raise ValueError('Invalid permanent Wi-Fi MAC')
    ssid = 'Atlantis-' + compact[-4:]
    if probe.get('ssid') != ssid or unit.get('ssid') not in ('Atlantis-AUTO', ssid):
        raise ValueError('SSID does not match the permanent Wi-Fi MAC and unit record')
    path = Path(output)
    if path.exists():
        raise ValueError('Verification evidence already exists; select a new record filename')
    report = {'schema':'mb00-identity-verification-1', 'serial':serial,
        'wifi_mac':mac.upper(), 'ssid':ssid, 'unit_sha256':digest(unit_path),
        'probe_sha256':digest(probe_path), 'identity_status':'CAPTURED_PROBE_MATCH',
        'verified_at_utc':datetime.now(timezone.utc).isoformat(),
        'hardware_acceptance_complete':False, 'production_approved':False,
        'scope':'Captured identity comparison only; operator must prove probe came from this physical unit.'}
    lan = probe.get('lan_mac', '')
    if isinstance(lan, str) and re.fullmatch(r'(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}', lan) and not int(lan[:2],16)&1 and lan.lower()!='00:00:00:00:00:00':
        report['lan_mac'] = lan.upper()
    con = open_registry(registry)
    try:
        with con:
            con.execute('BEGIN IMMEDIATE')
            record = con.execute('SELECT unit_sha256,wifi_mac FROM commissioning WHERE serial=?', (serial,)).fetchone()
            if not record or record[0] != digest(unit_path):
                raise ValueError('Unit record is absent from or differs from the commissioning registry')
            address = con.execute('SELECT url FROM unit_addresses WHERE serial=?', (serial,)).fetchone()
            if not address or address[0] != unit_url(serial):
                raise ValueError('Permanent unit URL is missing or conflicts with the assigned serial')
            report['remote_url'] = address[0]
            if record[1] is not None and record[1] != mac.upper():
                raise ValueError('This enclosure is already bound to another router; use a controlled service procedure')
            other = con.execute('SELECT serial FROM commissioning WHERE wifi_mac=? AND serial<>?', (mac.upper(), serial)).fetchone()
            if other:
                raise ValueError('This router MAC is already bound to a different enclosure')
            con.execute('UPDATE commissioning SET wifi_mac=?,verified_at=?,probe_sha256=? WHERE serial=?',
                        (mac.upper(), int(time.time()), digest(probe_path), serial))
            # An evidence write failure rolls back the database update. On later
            # commit failure the report remains only a captured comparison.
            write_private(path, report)
    finally:
        con.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare', help='Reserve a serial and create private per-unit commissioning records')
    prep.add_argument('--registry', type=Path, required=True)
    prep.add_argument('--output', type=Path, required=True)
    prep.add_argument('--operator', required=True)
    prep.add_argument('--prefix', default='AG26')
    prep.add_argument('--serial', help='Permanent ID allocated by the existing factory configurator; overrides local numbering')
    prep.add_argument('--wifi-mac')
    check = sub.add_parser('verify', help='Compare a captured probe with the enclosure and registered unit record')
    for arg in ('registry', 'unit', 'probe', 'output'):
        check.add_argument('--'+arg, type=Path, required=True)
    check.add_argument('--label-serial', required=True)
    check.add_argument('--labels-dir', type=Path, help='Render private setup and public enclosure labels after readback matches')
    check.add_argument('--print-labels', action='store_true', help='Also submit two setup labels to the existing Windows printer')
    check.add_argument('--print-kind', choices=('setup','enclosure'), default='setup', help='Choose private setup or public permanent-address labels')
    check.add_argument('--printer', help='Override the ESP configurator Label 1 queue')
    args = parser.parse_args()
    if args.command == 'verify' and args.print_labels and not args.labels_dir:
        parser.error('--print-labels requires --labels-dir')
    try:
        if args.command == 'prepare':
            folder = prepare(args.registry, args.output, args.operator, args.prefix, args.wifi_mac)
            print('Prepared '+folder.name+' in '+str(folder)+'. No router programmed; keep credentials private.')
        else:
            report = verify(args.registry, args.unit, args.probe, args.label_serial, args.output)
            print('Captured identity matched '+report['serial']+'; Wi-Fi '+report['ssid']+'. Physical acceptance remains required.')
            if args.labels_dir:
                from commission_labels import verified_data, setup_label, enclosure_label, print_selected, DEFAULT_PRINTER
                data = verified_data(args.unit.parent, args.output)
                setup, enclosure = setup_label(data), enclosure_label(data)
                args.labels_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
                os.chmod(args.labels_dir, 0o700)
                setup.save(args.labels_dir/'setup-private.png')
                os.chmod(args.labels_dir/'setup-private.png', 0o600)
                enclosure.save(args.labels_dir/'enclosure-public.png')
                if args.print_labels:
                    print_selected(setup,enclosure,args.print_kind,args.printer or DEFAULT_PRINTER,2,report['serial'])
                    print('Selected label submitted. Operator must confirm the physical print and scans.')
                else:
                    print('Created label artwork; no print job submitted.')
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, 'STOP: '+str(error)+'\n')


if __name__ == '__main__':
    main()
