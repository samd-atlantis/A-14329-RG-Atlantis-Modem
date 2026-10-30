import base64
import io
import json
from pathlib import Path
import tempfile
import time
import unittest

from portal.app import Portal
from portal.model import load, site_view
from portal.render import render, authorization

ROOT = Path(__file__).resolve().parents[1]
SECRET = 'fixture-edge-secret-' + 'x' * 32


def inventory(path):
    data = json.loads((ROOT/'sites.example.json').read_text())
    for i, site in enumerate(data['sites']):
        site['router_public_key'] = base64.b64encode(bytes([i+1])*32).decode()
    path.write_text(json.dumps(data))
    return data


def request(app, path='/', **headers):
    result = {}
    def start(status, response_headers):
        result.update(status=int(status[:3]), headers=dict(response_headers))
    body = b''.join(app({'PATH_INFO': path, 'REQUEST_METHOD': 'GET',
                        'REMOTE_ADDR': '127.0.0.1', 'wsgi.input': io.BytesIO(), **headers}, start))
    return result, body


class PortalTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root/'sites.json'
        self.data = inventory(self.path)
        self.app = Portal(self.path, SECRET)
        self.headers = {'HTTP_X_ATLANTIS_EDGE': SECRET, 'HTTP_REMOTE_USER': 'customer-a',
                        'HTTP_REMOTE_GROUPS': 'customer-demo'}

    def tearDown(self):
        self.temp.cleanup()

    def test_header_spoofing_or_missing_login_cannot_read_sites(self):
        for headers in ({}, {'HTTP_REMOTE_USER': 'admin', 'HTTP_REMOTE_GROUPS': 'atlantis-admin'},
                        {'HTTP_X_ATLANTIS_EDGE': SECRET}):
            result, body = request(self.app, '/api/sites', **headers)
            self.assertIn(result['status'], (401, 403))
            self.assertNotIn(b'North Plant', body)

    def test_customer_only_sees_assigned_sites_and_no_tunnel_inventory(self):
        result, body = request(self.app, '/api/sites', **self.headers)
        data = json.loads(body)
        self.assertEqual(result['status'], 200)
        self.assertEqual([s['id'] for s in data['sites']], ['north-plant', 'south-plant'])
        self.assertNotIn(b'Other Customer', body)
        self.assertNotIn(b'router_public_key', body)
        self.assertNotIn(b'10.203.', body)
        self.assertEqual(data['sites'][0]['controllers'][3]['url'],
                         'https://north-plant-c4.access.example.test')
        result, body = request(self.app, '/sites/other-customer', **self.headers)
        self.assertEqual(result['status'], 403)

    def test_admin_and_shared_customer_link_require_identity(self):
        result, _ = request(self.app, '/sites/north-plant', **self.headers)
        self.assertEqual(result['status'], 200)
        headers = {**self.headers, 'HTTP_REMOTE_GROUPS': 'atlantis-admin'}
        _, body = request(self.app, '/api/sites', **headers)
        self.assertEqual(len(json.loads(body)['sites']), 3)
        result, _ = request(self.app, '/sites/north-plant')
        self.assertEqual(result['status'], 403)

    def test_demo_is_loopback_only_and_never_claims_hardware_online(self):
        app = Portal(self.path, demo=True)
        result, body = request(app, '/api/sites')
        self.assertEqual(result['status'], 200)
        self.assertTrue(all(s['status'] == 'demo' for s in json.loads(body)['sites']))
        result, _ = request(app, '/api/sites', REMOTE_ADDR='192.0.2.10')
        self.assertEqual(result['status'], 403)

    def test_stale_status_is_unknown_not_online(self):
        path = self.root/'status.json'
        self.app.status_file = path
        path.write_text(json.dumps({'collected_at': time.time()-1000,
                                   'peers': {'north-plant': time.time()}}))
        self.assertEqual(self.app.status(self.data['sites'][0]), 'unknown')
        path.write_text(json.dumps({'collected_at': time.time(),
                                   'peers': {'north-plant': time.time()-10}}))
        self.assertEqual(self.app.status(self.data['sites'][0]), 'online')

    def test_no_proxy_url_or_filesystem_traversal_endpoint(self):
        for path in ('/../sites.example.json', '/%2e%2e/sites.example.json',
                     '/proxy/http://127.0.0.1', '/private', '/atlantis-logo.svg/../app.py'):
            result, _ = request(self.app, path, **self.headers)
            self.assertEqual(result['status'], 404)

    def test_duplicate_routes_keys_and_injection_are_rejected(self):
        for field, value in [('id', 'north-plant'), ('id', 'evil\nroute'),
                             ('tunnel_ip', '10.203.0.2'), ('tunnel_ip', '10.0.100.101'),
                             ('router_public_key', self.data['sites'][0]['router_public_key'])]:
            with self.subTest(field=field):
                data = json.loads(json.dumps(self.data))
                data['sites'][1][field] = value
                self.path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    load(self.path, deployment=True)

    def test_render_separates_overlapping_lans_and_keeps_access_disabled(self):
        out = self.root/'generated'
        render(self.path, out, base64.b64encode(bytes([99])*32).decode(), 'vpn.example.test')
        hub = (out/'wg-atlantis.conf.template').read_text()
        self.assertNotIn('AllowedIPs = 10.0.100', hub)
        self.assertIn('AllowedIPs = 10.203.0.2/32', hub)
        script = (out/'north-plant-router.sh').read_text()
        self.assertIn("set network.atlantis.auto='0'", script)
        self.assertIn("set gateway.remote.enabled='0'", script)
        self.assertNotIn('0.0.0.0/0', script)
        for number in range(1, 5):
            self.assertIn(f'firewall.atlantis_c{number}.src_dport={8100+number}', script)
            self.assertIn(f"firewall.atlantis_c{number}.dest_ip='10.0.100.{100+number}'", script)
        self.assertNotIn('src=wan', script)
        self.assertNotIn('atlantis_c3=redirect', (out/'south-plant-router.sh').read_text())
        edge = (out/'Caddyfile').read_text()
        self.assertNotIn('tls_insecure_skip_verify', edge)
        self.assertIn('tls_trust_pool file', edge)
        self.assertNotIn('header_up -Authorization\n        header_up -Remote', edge)
        acl = authorization(self.data)
        self.assertEqual(acl['default_policy'], 'deny')
        self.assertTrue(all(r['policy'] == 'two_factor' for r in acl['rules']))
        self.assertEqual(acl['rules'][0]['subject'], ['group:atlantis-admin','group:customer-demo'])


if __name__ == '__main__':
    unittest.main()
