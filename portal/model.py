"""Validate operator-owned inventory; never accept proxy destinations from requests."""
import base64
import ipaddress
import json
import re
from pathlib import Path

HUB = '10.203.0.1'
TUNNEL = ipaddress.ip_network('10.203.0.0/16')
CONTROLLERS = tuple('10.0.100.' + str(i) for i in range(101, 105))


def dns(value):
    if not isinstance(value, str) or len(value) > 253 or not re.fullmatch(
            r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', value):
        raise ValueError('Invalid DNS name')
    if any(not label or len(label) > 63 or label.startswith('-') or label.endswith('-') for label in value.split('.')):
        raise ValueError('Invalid DNS label')
    return value


def key(value):
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise ValueError('Invalid WireGuard public key') from None
    if len(raw) != 32 or not any(raw):
        raise ValueError('Invalid WireGuard public key')
    return value


def load(path, deployment=False):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    dns(data['domain'])
    ids, addresses, public_keys = set(), set(), set()
    for site in data['sites']:
        slug = site['id']
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,31}', slug) or slug.endswith('-') or slug in ids:
            raise ValueError('Invalid or duplicate site id')
        ids.add(slug)
        # Reserve portal/auth hostnames and all device hostnames against collisions.
        ip = ipaddress.ip_address(site['tunnel_ip'])
        if ip not in TUNNEL or str(ip) == HUB or int(ip) & 255 in (0, 255) or str(ip) in addresses:
            raise ValueError('Invalid or duplicate site tunnel address')
        addresses.add(str(ip))
        if not isinstance(site['name'], str) or not 1 <= len(site['name']) <= 100:
            raise ValueError('Invalid site name')
        if not re.fullmatch(r'[A-Za-z0-9-]{1,24}', site['serial']):
            raise ValueError('Invalid unit serial')
        if not isinstance(site['groups'], list) or not site['groups'] or any(not isinstance(g, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,47}', g) for g in site['groups']):
            raise ValueError('Invalid site access group')
        if len(site['controllers']) != 4 or any(type(v) is not bool for v in site['controllers']):
            raise ValueError('Exactly four controller presence flags required')
        if deployment:
            dns(site['gateway_tls_name'].lower())
            public_key = key(site['router_public_key'])
            if public_key in public_keys:
                raise ValueError('Duplicate router public key')
            public_keys.add(public_key)
    return data


def allowed(site, groups):
    return 'atlantis-admin' in groups or bool(set(site['groups']) & set(groups))


def host(data, site, device):
    return site['id'] + '-' + device + '.' + data['domain']


def site_view(data, site, online=None):
    return {'id': site['id'], 'name': site['name'], 'serial': site.get('serial', ''),
            'url': 'https://portal.' + data['domain'] + '/sites/' + site['id'],
            'status': online or 'unknown', 'gateway': 'https://' + host(data, site, 'gateway'),
            'controllers': [{'number': i + 1, 'ip': ip, 'enabled': site['controllers'][i],
                             'url': 'https://' + host(data, site, 'c' + str(i + 1))}
                            for i, ip in enumerate(CONTROLLERS)]}
