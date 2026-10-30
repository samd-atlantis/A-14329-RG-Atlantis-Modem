import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1]/'tools'
sys.path.insert(0, str(TOOLS))
import commission
from serial_registry import open_registry, reserve, reserve_named


class CommissionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root/'private/fleet.sqlite3'
        if os.name == 'nt':
            os.environ['PATH'] = r'C:\Program Files\Git\usr\bin' + os.pathsep + os.environ['PATH']

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, **kwargs):
        return commission.prepare(self.registry, self.root/'units', 'Fixture operator', prefix='TEST26', **kwargs)

    def probe(self, folder, mac='00:11:22:33:A1:B2'):
        path = self.root/'probe.json'
        path.write_text(json.dumps({'schema':'mb00-device-probe-1', 'board_name':'hilink,hlk-7628n',
            'distribution':'OpenWrt', 'provisioned':'1', 'serial':folder.name,
            'wifi_mac':mac, 'ssid':'Atlantis-'+mac.replace(':','')[-4:].upper()}))
        return path

    def test_reservations_are_unique_between_parallel_stations_and_never_reused(self):
        reserve(self.registry, 'TEST26')  # initialize before concurrent callers
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            batches = list(pool.map(lambda _: reserve(self.registry, 'TEST26', 4), range(6)))
        values = [s for b in batches for s in b]
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(reserve(self.registry, 'TEST26')[0], 'TEST26-000026')
        con = open_registry(self.registry)
        try:
            for sql in ('DELETE FROM serial_registry', "UPDATE serial_registry SET serial='changed'"):
                with self.assertRaises(sqlite3.IntegrityError):
                    con.execute(sql)
        finally:
            con.close()

    def test_preparation_ties_unit_acceptance_and_public_label_to_one_serial(self):
        a, b = self.prepare(), self.prepare()
        unit = json.loads((a/'unit.json').read_text())
        self.assertNotEqual(a.name, b.name)
        self.assertEqual(unit['serial'], a.name)
        self.assertEqual(json.loads((a/'acceptance.json').read_text())['serial'], a.name)
        self.assertEqual(json.loads((a/'acceptance.json').read_text())['status'], 'NOT_TESTED')
        public = (a/'enclosure-label.txt').read_text()
        self.assertIn(a.name, public)
        self.assertNotIn(unit['wifi_password'], public)
        self.assertNotIn('root_hash', public)
        self.assertIn(unit['wifi_password'], (a/'credentials.csv').read_text())
        self.assertFalse(json.loads((a/'identity.json').read_text())['hardware_tested'])

    def test_existing_configurator_serial_is_preserved_and_case_duplicate_rejected(self):
        folder = self.prepare(serial='FACTORY-12345')
        self.assertEqual(folder.name, 'FACTORY-12345')
        self.assertEqual(json.loads((folder/'identity.json').read_text())['serial_source'], 'factory-configurator')
        with self.assertRaises(sqlite3.IntegrityError):
            reserve_named(self.registry, 'factory-12345')

    def test_invalid_station_inputs_do_not_allocate_a_serial(self):
        for kwargs in ({'wifi_mac':'invalid'}, {'serial':'../bad'}):
            with self.assertRaises(ValueError):
                self.prepare(**kwargs)
        self.assertFalse(self.registry.exists())

    def test_permanent_address_is_saved_with_identity_and_cannot_be_reassigned(self):
        folder=self.prepare()
        expected='https://connect.atlantisllc.com/u/'+folder.name
        identity=json.loads((folder/'identity.json').read_text())
        self.assertEqual(identity['remote_url'],expected)
        self.assertEqual(identity['remote_service_status'],'NOT_DEPLOYED')
        self.assertIn(expected,(folder/'enclosure-label.txt').read_text())
        con=open_registry(self.registry)
        try:
            self.assertEqual(con.execute('SELECT url FROM unit_addresses WHERE serial=?',(folder.name,)).fetchone()[0],expected)
            for sql in ("UPDATE unit_addresses SET url='https://other.example.test'",'DELETE FROM unit_addresses'):
                with self.assertRaises(sqlite3.IntegrityError):con.execute(sql)
        finally:con.close()

    def test_imported_factory_number_advances_the_local_counter_without_reusing_it(self):
        reserve_named(self.registry,'TEST26-000040')
        self.assertEqual(reserve(self.registry,'TEST26')[0],'TEST26-000041')

    def test_captured_identity_readback_records_final_mac_and_ssid_only(self):
        folder = self.prepare()
        report = commission.verify(self.registry, folder/'unit.json', self.probe(folder), folder.name, folder/'readback.json')
        self.assertEqual(report['ssid'], 'Atlantis-A1B2')
        self.assertEqual(report['identity_status'], 'CAPTURED_PROBE_MATCH')
        self.assertFalse(report['production_approved'])
        self.assertFalse(report['hardware_acceptance_complete'])
        con = open_registry(self.registry)
        try:
            self.assertEqual(con.execute('SELECT wifi_mac FROM commissioning WHERE serial=?', (folder.name,)).fetchone()[0], '00:11:22:33:A1:B2')
        finally:
            con.close()

    def test_wrong_enclosure_wrong_router_ssid_and_unprovisioned_probe_are_rejected(self):
        folder = self.prepare()
        probe = self.probe(folder)
        original = json.loads(probe.read_text())
        for change in ({'serial':'other'}, {'provisioned':'0'}, {'wifi_mac':'01:11:22:33:A1:B2'}, {'ssid':'Atlantis-FFFF'}, {'board_name':'other'}):
            probe.write_text(json.dumps({**original, **change}))
            with self.subTest(change=change), self.assertRaises(ValueError):
                commission.verify(self.registry, folder/'unit.json', probe, folder.name, folder/'readback.json')
        probe.write_text(json.dumps(original))
        with self.assertRaises(ValueError):
            commission.verify(self.registry, folder/'unit.json', probe, 'WRONG-LABEL', folder/'readback.json')
        self.assertFalse((folder/'readback.json').exists())

    def test_duplicate_radio_on_another_enclosure_and_changed_private_record_are_rejected(self):
        a, b = self.prepare(), self.prepare()
        commission.verify(self.registry, a/'unit.json', self.probe(a), a.name, a/'readback.json')
        with self.assertRaisesRegex(ValueError, 'different enclosure'):
            commission.verify(self.registry, b/'unit.json', self.probe(b), b.name, b/'readback.json')
        unit = json.loads((b/'unit.json').read_text())
        unit['wifi_password'] = 'changed-private-record'
        (b/'unit.json').write_text(json.dumps(unit))
        with self.assertRaisesRegex(ValueError, 'differs'):
            commission.verify(self.registry, b/'unit.json', self.probe(b, '00:11:22:33:CC:DD'), b.name, b/'readback.json')

    def test_recommissioning_does_not_silently_replace_an_existing_router_binding(self):
        folder = self.prepare()
        commission.verify(self.registry, folder/'unit.json', self.probe(folder), folder.name, folder/'readback.json')
        with self.assertRaisesRegex(ValueError, 'another router'):
            commission.verify(self.registry, folder/'unit.json', self.probe(folder, '00:11:22:33:CC:DD'), folder.name, folder/'new-readback.json')
        self.assertFalse((folder/'new-readback.json').exists())


if __name__ == '__main__':
    unittest.main()
