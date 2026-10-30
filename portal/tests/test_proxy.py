"""Real Caddy/HTTP/TLS tests using loopback fixtures, never a customer controller."""
import base64
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
from wsgiref.simple_server import make_server

from portal.app import Portal
from portal.render import edge
from portal.tests.test_portal import inventory, SECRET

CADDY = Path(os.environ.get('CADDY_BIN', '.tools/caddy/' + ('caddy.exe' if os.name == 'nt' else 'caddy'))).resolve()


class Device(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', 'http://10.0.100.101/login?next=1')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        if not self.headers.get('Authorization'):
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="Controller"')
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length).decode() if length else ''
        data = json.dumps({'headers': dict(self.headers), 'body': body, 'path': self.path}).encode()
        self.send_response(200)
        self.send_header('Set-Cookie', 'device_login=fixture; Domain=10.0.100.101; Path=/; HttpOnly')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_POST = do_GET


class Identity(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.last_headers = dict(self.headers)
        valid = ('atlantis_session=fixture-sso-secret' in self.headers.get('Cookie', '') and
                 not self.headers.get('X-Forwarded-Host', '').startswith('other-customer'))
        self.send_response(200 if valid else 403)
        if valid:
            self.send_header('Remote-User', 'fixture-customer')
            self.send_header('Remote-Groups', 'customer-demo')
        self.send_header('Content-Length', '0')
        self.end_headers()


def serve(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


@unittest.skipUnless(CADDY.is_file(), 'Fetch the pinned validator with portal/tools/get_caddy.py')
class ProxyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        inv = cls.root/'sites.json'
        cls.data = inventory(inv)
        cls.identity = serve(ThreadingHTTPServer(('127.0.0.1', 0), Identity))
        cls.device = serve(ThreadingHTTPServer(('127.0.0.1', 0), Device))
        cls.portal = serve(make_server('127.0.0.1', 0, Portal(inv, SECRET)))
        openssl = shutil.which('openssl') or 'C:/Program Files/Git/usr/bin/openssl.exe'
        cls.cert, private = cls.root/'fixture.pem', cls.root/'fixture.key'
        subprocess.run([openssl, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=OpenWrt', '-addext', 'subjectAltName=DNS:OpenWrt',
                        '-keyout', str(private), '-out', str(cls.cert)],
                       check=True, capture_output=True, timeout=30)
        cls.tls_device = ThreadingHTTPServer(('127.0.0.1', 0), Device)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cls.cert, private)
        cls.tls_device.socket = context.wrap_socket(cls.tls_device.socket, server_side=True)
        serve(cls.tls_device)
        bad_cert, bad_key = cls.root/'untrusted.pem', cls.root/'untrusted.key'
        subprocess.run([openssl, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
                        '-subj', '/CN=OpenWrt', '-addext', 'subjectAltName=DNS:OpenWrt',
                        '-keyout', str(bad_key), '-out', str(bad_cert)],
                       check=True, capture_output=True, timeout=30)
        cls.untrusted = ThreadingHTTPServer(('127.0.0.1', 0), Device)
        bad_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        bad_context.load_cert_chain(bad_cert, bad_key)
        cls.untrusted.socket = bad_context.wrap_socket(cls.untrusted.socket, server_side=True)
        serve(cls.untrusted)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        config = edge(cls.data)
        config = re.sub(r'^([a-z0-9.-]+) \{$', lambda m: 'http://' + m[1] + ':' + str(cls.port) + ' {', config, flags=re.M)
        config = config.replace('127.0.0.1:9091', '127.0.0.1:' + str(cls.identity.server_port))
        config = config.replace('127.0.0.1:8767', '127.0.0.1:' + str(cls.portal.server_port))
        config = config.replace('https://10.203.0.3:443', 'https://127.0.0.1:' + str(cls.untrusted.server_port))
        config = re.sub(r'https://10\.203\.\d+\.\d+:443', 'https://127.0.0.1:' + str(cls.tls_device.server_port), config)
        config = re.sub(r'http://10\.203\.\d+\.\d+:810[1-4]', 'http://127.0.0.1:' + str(cls.device.server_port), config)
        config = re.sub(r'/etc/atlantis/pki/[a-z0-9-]+\.pem', json.dumps(cls.cert.as_posix()), config)
        config = config.replace('/var/log/atlantis/access.json', json.dumps((cls.root/'access.json').as_posix()))
        config = '{\n admin off\n auto_https off\n default_bind 127.0.0.1\n}\n' + config
        path = cls.root/'Caddyfile'
        path.write_text(config, newline='\n')
        cls.log = (cls.root/'caddy.log').open('wb')
        env = {**os.environ, 'ATLANTIS_EDGE_SECRET': SECRET}
        cls.process = subprocess.Popen([str(CADDY), 'run', '--config', str(path), '--adapter', 'caddyfile'],
                                       stdout=cls.log, stderr=cls.log, env=env)
        for _ in range(100):
            if cls.process.poll() is not None:
                cls.log.flush()
                raise AssertionError((cls.root/'caddy.log').read_text())
            try:
                with socket.create_connection(('127.0.0.1', cls.port), timeout=.2):
                    break
            except OSError:
                time.sleep(.1)
        else:
            raise AssertionError('Caddy did not start')

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate()
        cls.process.wait(timeout=10)
        cls.log.close()
        for server in (cls.identity, cls.device, cls.tls_device, cls.untrusted, cls.portal):
            server.shutdown()
            server.server_close()
        cls.temp.cleanup()

    def call(self, host='north-plant-c1', path='/', cookie=True, auth=None, method='GET', body=None, extra=None):
        headers = {'Host': host + '.access.example.test:' + str(self.port)}
        if cookie:
            headers['Cookie'] = 'device_cookie=fixture; atlantis_session=fixture-sso-secret; other_cookie=kept'
        if auth:
            headers['Authorization'] = auth
        headers.update(extra or {})
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_unauthenticated_and_spoofed_identity_are_denied(self):
        code, _, _ = self.call(cookie=False, extra={'Remote-User':'admin', 'Remote-Groups':'atlantis-admin'})
        self.assertEqual(code, 403)
        code, _, _ = self.call(host='other-customer-c1')
        self.assertEqual(code, 403)

    def test_controller_login_challenge_and_credentials_are_preserved(self):
        code, headers, _ = self.call()
        self.assertEqual(code, 401)
        self.assertEqual(headers['Www-Authenticate'], 'Basic realm="Controller"')
        authorization = 'Basic ' + base64.b64encode(b'fixture-user:fixture-password').decode()
        code, headers, body = self.call(auth=authorization, method='POST', body='setting=fixture')
        self.assertEqual(code, 200)
        echoed = json.loads(body)
        self.assertEqual(echoed['headers']['Authorization'], authorization)
        self.assertEqual(echoed['body'], 'setting=fixture')
        self.assertNotIn('fixture-sso-secret', echoed['headers']['Cookie'])
        self.assertIn('device_cookie=fixture', echoed['headers']['Cookie'])
        self.assertIn('other_cookie=kept', echoed['headers']['Cookie'])
        self.assertNotIn('Remote-User', echoed['headers'])
        self.assertNotIn('X-Atlantis-Edge', echoed['headers'])
        self.assertNotIn('Authorization', self.identity.last_headers)
        self.assertNotIn('Domain=', headers['Set-Cookie'])
        logs = (self.root/'access.json').read_text()
        self.assertNotIn('fixture-sso-secret', logs)
        self.assertNotIn(authorization, logs)
        self.assertNotIn('setting=fixture', logs)

    def test_private_ip_redirect_becomes_public_customer_origin(self):
        code, headers, _ = self.call(path='/redirect')
        self.assertEqual(code, 302)
        self.assertEqual(headers['Location'], 'https://north-plant-c1.access.example.test/login?next=1')

    def test_gateway_tls_pin_and_native_login_are_both_required(self):
        code, headers, _ = self.call(host='north-plant-gateway')
        self.assertEqual(code, 401)
        self.assertIn('Www-Authenticate', headers)

    def test_wrong_gateway_certificate_is_rejected(self):
        code, _, _ = self.call(host='south-plant-gateway')
        self.assertEqual(code, 502)

    def test_edge_authenticates_backend_and_filters_sites(self):
        code, _, body = self.call(host='portal', path='/api/sites')
        self.assertEqual(code, 200)
        self.assertEqual([s['id'] for s in json.loads(body)['sites']], ['north-plant','south-plant'])


if __name__ == '__main__':
    unittest.main()
