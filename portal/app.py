"""WSGI portal. Production identity comes only from the authenticated local edge.

Local --demo binds loopback and never contacts a device. Production: gunicorn,
Caddy and Authelia; there is no built-in password or bypass login endpoint.
"""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import time
from urllib.parse import unquote

from .model import load, allowed, site_view

ROOT = Path(__file__).parent


class Portal:
    def __init__(self, inventory, secret=None, demo=False, status_file=None):
        self.inventory = load(inventory)
        self.demo, self.secret, self.status_file = demo, secret, status_file
        if not demo and (not secret or len(secret) < 32):
            raise ValueError('Production requires a private edge secret of at least 32 characters')

    def status(self, site):
        if self.demo:
            return 'demo'
        try:
            path = Path(self.status_file)
            if path.stat().st_size > 1024 * 1024:
                return 'unknown'
            data = json.loads(path.read_text())
            if not isinstance(data, dict) or not isinstance(data.get('peers'), dict):
                return 'unknown'
            age = time.time() - data['collected_at']
            if not 0 <= age <= 90:
                return 'unknown'
            handshake = data['peers'].get(site['id'], 0)
            return 'online' if 0 < time.time() - handshake < 180 else 'offline'
        except (OSError, ValueError, TypeError, KeyError):
            return 'unknown'

    def __call__(self, env, start_response):
        path = unquote(env.get('PATH_INFO', '/'))
        def respond(code, data, kind='application/json'):
            if not isinstance(data, bytes):
                data = json.dumps(data).encode()
            headers = [('Content-Type', kind), ('Content-Length', str(len(data))),
                       ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'),
                       ('Referrer-Policy', 'no-referrer'),
                       ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")]
            start_response(code, headers)
            return [data]
        if env.get('REQUEST_METHOD', 'GET') != 'GET':
            return respond('405 Method Not Allowed', {'error': 'Read-only portal'})
        if self.demo:
            if env.get('REMOTE_ADDR') not in ('127.0.0.1', '::1') or any(env.get(h) for h in (
                    'HTTP_X_FORWARDED_FOR', 'HTTP_X_FORWARDED_HOST', 'HTTP_X_FORWARDED_PROTO',
                    'HTTP_FORWARDED', 'HTTP_X_ATLANTIS_EDGE')):
                return respond('403 Forbidden', {'error': 'Loopback preview only'})
            user, groups = 'Demo customer', {'customer-demo'}
        else:
            supplied = env.get('HTTP_X_ATLANTIS_EDGE', '')
            if not hmac.compare_digest(hashlib.sha256(supplied.encode()).digest(),
                                       hashlib.sha256(self.secret.encode()).digest()):
                return respond('403 Forbidden', {'error': 'Authenticated edge required'})
            user = env.get('HTTP_REMOTE_USER', '')
            groups = {g.strip() for g in env.get('HTTP_REMOTE_GROUPS', '').split(',') if g.strip()}
            if not user:
                return respond('401 Unauthorized', {'error': 'Login required'})
        sites = [s for s in self.inventory['sites'] if allowed(s, groups)]
        selected = None
        if path.startswith('/sites/'):
            selected = path[len('/sites/'):]
            if not any(s['id'] == selected for s in sites):
                return respond('403 Forbidden', {'error': 'Site access denied'})
        if path == '/api/sites':
            return respond('200 OK', {'user': user, 'demo': self.demo,
                'sites': [site_view(self.inventory, s, self.status(s)) for s in sites]})
        assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                  '/app.js': ('app.js', 'application/javascript'),
                  '/style.css': ('style.css', 'text/css'),
                  '/atlantis-logo.svg': ('atlantis-logo.svg', 'image/svg+xml')}
        asset = assets.get('/' if selected is not None else path)
        if not asset:
            return respond('404 Not Found', {'error': 'Not found'})
        return respond('200 OK', (ROOT / 'static' / asset[0]).read_bytes(), asset[1])


def production():
    return Portal(os.environ['ATLANTIS_SITES'], os.environ.get('ATLANTIS_EDGE_SECRET'),
                  status_file=os.environ.get('ATLANTIS_STATUS_FILE'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true', required=True)
    parser.add_argument('--port', type=int, default=8767)
    args = parser.parse_args()
    from wsgiref.simple_server import make_server
    app = Portal(ROOT / 'sites.example.json', demo=True)
    print('Atlantis portal preview: http://127.0.0.1:%s (sample data; no device access)' % args.port, flush=True)
    make_server('127.0.0.1', args.port, app).serve_forever()


if __name__ == '__main__':
    main()
