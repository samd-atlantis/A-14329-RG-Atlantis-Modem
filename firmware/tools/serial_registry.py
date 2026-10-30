"""One authoritative, backed-up registry for permanent Atlantis enclosure IDs."""
import os
from pathlib import Path
import re
import sqlite3
import time


def open_registry(path, create=False):
    path = Path(path).resolve()
    if not create and not path.is_file():
        raise ValueError('The authoritative serial registry is missing')
    if create:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    con = sqlite3.connect(path.as_uri() + ('?mode=rwc' if create else '?mode=rw'), uri=True, timeout=30)
    con.execute('PRAGMA foreign_keys=ON')
    if create:
        os.chmod(path, 0o600)
        con.executescript('''
            CREATE TABLE IF NOT EXISTS serial_counters(prefix TEXT PRIMARY KEY, next_value INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS serial_registry(serial TEXT PRIMARY KEY COLLATE NOCASE, model TEXT NOT NULL, reserved_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS commissioning(serial TEXT PRIMARY KEY REFERENCES serial_registry(serial), unit_sha256 TEXT NOT NULL, operator TEXT NOT NULL, wifi_mac TEXT UNIQUE, verified_at INTEGER, probe_sha256 TEXT);
            CREATE TRIGGER IF NOT EXISTS immutable_serial_update BEFORE UPDATE ON serial_registry BEGIN SELECT RAISE(ABORT,'Permanent serials cannot change'); END;
            CREATE TRIGGER IF NOT EXISTS immutable_serial_delete BEFORE DELETE ON serial_registry BEGIN SELECT RAISE(ABORT,'Permanent serials cannot be reused'); END;
        ''')
    return con


def reserve(registry, prefix, count=1):
    if not re.fullmatch(r'[A-Z][A-Z0-9]{1,11}', prefix) or type(count) is not int or not 1 <= count <= 10000:
        raise ValueError('Use an uppercase prefix and count 1..10000')
    con = open_registry(registry, create=True)
    try:
        with con:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute('SELECT next_value FROM serial_counters WHERE prefix=?', (prefix,)).fetchone()
            start = row[0] if row else 1
            if start + count > 1000000:
                raise ValueError('Prefix exhausted; choose a new approved prefix')
            serials = [f'{prefix}-{n:06d}' for n in range(start, start+count)]
            con.executemany('INSERT INTO serial_registry VALUES(?,?,?)', [(s, 'A-14329-MB00', int(time.time())) for s in serials])
            con.execute('INSERT INTO serial_counters VALUES(?,?) ON CONFLICT(prefix) DO UPDATE SET next_value=excluded.next_value', (prefix, start+count))
        return serials
    finally:
        con.close()


def reserve_named(registry, serial):
    """Register an ID allocated by the existing authorized factory configurator."""
    if not isinstance(serial, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,24}', serial):
        raise ValueError('Serial must be 1..24 letters, digits or hyphens')
    con = open_registry(registry, create=True)
    try:
        with con:
            con.execute('INSERT INTO serial_registry VALUES(?,?,?)', (serial, 'A-14329-MB00', int(time.time())))
            numbered = re.fullmatch(r'([A-Z][A-Z0-9]{1,11})-([0-9]{6})', serial.upper())
            if numbered:
                con.execute('INSERT INTO serial_counters VALUES(?,?) ON CONFLICT(prefix) DO UPDATE SET next_value=max(next_value,excluded.next_value)',
                            (numbered[1], int(numbered[2])+1))
        return serial
    finally:
        con.close()
