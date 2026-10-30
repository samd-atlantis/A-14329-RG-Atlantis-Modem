"""Generate reviewable hub/edge/router configuration; never deploy or enable it."""
import argparse
import json
import os
from pathlib import Path
import shlex

from .model import load, key, dns, HUB, CONTROLLERS, host


def router_script(data, site, server_key, endpoint, port):
    ip = site['tunnel_ip']
    commands = ["set network.atlantis=interface", "set network.atlantis.proto=wireguard",
        "set network.atlantis.auto='0'", "set network.atlantis.private_key='$private_key'",
        "add_list network.atlantis.addresses='" + ip + "/32'",
        "set network.atlantis.mtu='1380'", "set network.atlantis_peer=wireguard_atlantis",
        "set network.atlantis_peer.public_key='" + server_key + "'",
        "set network.atlantis_peer.endpoint_host='" + endpoint + "'",
        "set network.atlantis_peer.endpoint_port='" + str(port) + "'",
        "set network.atlantis_peer.persistent_keepalive='25'",
        "set network.atlantis_peer.route_allowed_ips='1'",
        "add_list network.atlantis_peer.allowed_ips='" + HUB + "/32'",
        "set firewall.atlantis=zone", "set firewall.atlantis.name=atlantis",
        "add_list firewall.atlantis.network=atlantis", "set firewall.atlantis.input=REJECT",
        "set firewall.atlantis.output=ACCEPT", "set firewall.atlantis.forward=REJECT",
        "set firewall.atlantis.family=ipv4", "set firewall.atlantis_gateway=rule",
        "set firewall.atlantis_gateway.name='Atlantis gateway HTTPS from hub'",
        "set firewall.atlantis_gateway.src=atlantis", "set firewall.atlantis_gateway.src_ip='" + HUB + "'",
        "set firewall.atlantis_gateway.dest_ip='" + ip + "'", "set firewall.atlantis_gateway.dest_port=443",
        "set firewall.atlantis_gateway.proto=tcp", "set firewall.atlantis_gateway.target=ACCEPT",
        "set firewall.atlantis_gateway.family=ipv4", "set gateway.remote=remote", "set gateway.remote.enabled='0'",
        "set gateway.remote.gateway_host='" + host(data, site, 'gateway') + "'"]
    for i, address in enumerate(CONTROLLERS, 1):
        name = 'firewall.atlantis_c' + str(i)
        if site['controllers'][i - 1]:
            commands += [f'set {name}=redirect', f"set {name}.name='Atlantis controller {i}'",
                f'set {name}.src=atlantis', f"set {name}.src_ip='{HUB}'", f"set {name}.src_dip='{ip}'",
                f'set {name}.src_dport={8100+i}', f'set {name}.dest=lan', f"set {name}.dest_ip='{address}'",
                f'set {name}.dest_port=80', f'set {name}.proto=tcp', f'set {name}.target=DNAT',
                f'set {name}.family=ipv4', f"set {name}.reflection='0'"]
        commands += [f"set gateway.remote.controller{i}_host='{host(data, site, 'c'+str(i))}'"]
    deletes = ['network.atlantis', 'network.atlantis_peer', 'firewall.atlantis', 'firewall.atlantis_gateway']
    deletes += ['firewall.atlantis_c' + str(i) for i in range(1, 5)]
    return '''#!/bin/sh
# Review/fixture install only. Does not start the tunnel. Device logins stay intact.
set -eu
[ "$(cat /usr/share/atech-gateway/remote-support 2>/dev/null)" = 1 ] || { echo 'Install the qualified remote-capable firmware first' >&2; exit 1; }
command -v wg >/dev/null || exit 1
[ "$(uci -q get gateway.main.provisioned)" = 1 ] || { echo 'Provision this unit first' >&2; exit 1; }
[ "$(uci -q get gateway.main.serial)" = SERIAL ] || { echo 'Wrong unit serial' >&2; exit 1; }
umask 077
# Generate this key locally on the router during enrollment, then register its
# public key in the inventory. This installer never overwrites a key.
[ -f /etc/gateway/wireguard.key ] || { echo 'Enroll the router public key first' >&2; exit 1; }
private_key="$(cat /etc/gateway/wireguard.key)" || exit 1
public_key="$(printf '%s\\n' "$private_key" | wg pubkey)" || exit 1
[ "$public_key" = PUBLIC_KEY ] || { echo 'Registered router key mismatch' >&2; exit 1; }
ifdown atlantis 2>/dev/null || true
''' .replace('SERIAL', shlex.quote(site['serial'])).replace('PUBLIC_KEY', shlex.quote(site['router_public_key'])) + \
        '\n'.join("uci -q delete " + name + ' || true' for name in deletes) + \
        '\nuci batch <<EOF\n' + '\n'.join(commands) + '''
EOF
chmod 600 /etc/config/network /etc/gateway/wireguard.key
uci commit network
uci commit firewall
uci commit gateway
/etc/init.d/firewall reload
echo 'Staged only. Verify hub, peer key, gateway TLS pin, controller gateway .7 and customer permissions before enabling.'
echo 'Qualified activation: uci set network.atlantis.auto=1; uci set gateway.remote.enabled=1; uci commit network; uci commit gateway; /etc/init.d/network reload'
'''


def auth_block():
    return '''    request_header -Remote-User
    request_header -Remote-Groups
    request_header -Remote-Email
    request_header -Remote-Name
    request_header -X-Atlantis-Edge
    forward_auth 127.0.0.1:9091 {
        uri /api/authz/forward-auth
        header_up -Authorization
        header_up -Proxy-Authorization
        copy_headers Remote-User Remote-Groups
    }
'''


def audit_block(site, device):
    return '''    log {
        output file /var/log/atlantis/access.json
        format filter {
            wrap json
            fields {
                request delete
                resp_headers delete
            }
        }
    }
    log_append principal {http.request.header.Remote-User}
    log_append site ''' + site + '\n    log_append device ' + device + '\n'


def edge(data):
    domain = data['domain']
    text = '# Generated configuration; review DNS, TLS pins and Authelia before deployment.\n'
    text += 'auth.' + domain + ' {\n    reverse_proxy 127.0.0.1:9091\n}\n\n'
    text += 'portal.' + domain + ' {\n' + audit_block('portal', 'directory') + '    route {\n' + auth_block() + '''    reverse_proxy 127.0.0.1:8767 {
        header_up X-Atlantis-Edge {$ATLANTIS_EDGE_SECRET}
    }
    }
}\n'''
    for site in data['sites']:
        devices = [('gateway', 443, None)] + [('c' + str(i), 8100+i, ip)
            for i, ip in enumerate(CONTROLLERS, 1) if site['controllers'][i-1]]
        for device, port, address in devices:
            hostname = host(data, site, device)
            text += '\n' + hostname + ' {\n' + audit_block(site['id'], device) + '    route {\n' + auth_block()
            upstream = ('https://' if device == 'gateway' else 'http://') + site['tunnel_ip'] + ':' + str(port)
            text += '    reverse_proxy ' + upstream + ' {\n'
            # Blank only the edge SSO cookie; preserve native controller cookies,
            # Basic/Digest Authorization and WWW-Authenticate response headers.
            text += '''        header_up Cookie "(^|;[ ]*)atlantis_session=[^;]*" "$1"
        header_up -Remote-User
        header_up -Remote-Groups
        header_up -X-Atlantis-Edge
        header_down Set-Cookie "(?i);[ ]*Domain=[^;]*" ""
'''
            if device == 'gateway':
                text += '''        transport http {
            tls
            tls_server_name ''' + site['gateway_tls_name'] + '''
            tls_trust_pool file /etc/atlantis/pki/''' + site['id'] + '''.pem
        }
'''
                address = '10.0.100.7'
            pattern = '^https?://' + address.replace('.', '[.]') + '(?::[0-9]+)?(/.*)?$'
            text += '        header_down Location ' + json.dumps(pattern) + ' "https://' + hostname + '$1"\n'
            text += '    }\n    }\n}\n'
    return text


def authorization(data):
    rules = []
    for site in data['sites']:
        domains = [host(data, site, 'gateway')] + [host(data, site, 'c'+str(i+1))
                    for i, enabled in enumerate(site['controllers']) if enabled]
        rules.append({'domain': domains, 'policy': 'two_factor',
                      'subject': ['group:atlantis-admin'] + ['group:' + g for g in site['groups']]})
    rules.append({'domain': 'portal.' + data['domain'], 'policy': 'two_factor'})
    return {'default_policy': 'deny', 'rules': rules}


def identity_config(data):
    return {'server': {'address': 'tcp://127.0.0.1:9091/'}, 'theme': 'light',
            'totp': {'issuer': 'Atlantis'},
            'authentication_backend': {'password_reset': {'disable': True},
                                       'file': {'path': '/etc/atlantis/users.yml'}},
            'access_control': authorization(data),
            'session': {'name': 'atlantis_session', 'same_site': 'lax', 'inactivity': '5m',
                        'expiration': '1h', 'remember_me': '0', 'cookies': [
                            {'domain': data['domain'], 'authelia_url': 'https://auth.'+data['domain']}]},
            'storage': {'local': {'path': '/var/lib/atlantis/authelia.sqlite3'}},
            'notifier': {'filesystem': {'filename': '/var/lib/atlantis/notifications.txt'}}}


def render(inventory, output, server_key, endpoint, port=51820):
    data = load(inventory, deployment=True)
    key(server_key)
    if any(site['router_public_key'] == server_key for site in data['sites']):
        raise ValueError('Hub and router must use different keys')
    dns(endpoint)
    if not 1 <= port <= 65535:
        raise ValueError('Invalid UDP port')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(output, 0o700)
    (output/'Caddyfile').write_text(edge(data), newline='\n')
    (output/'authelia-access.json').write_text(json.dumps({'access_control': authorization(data)}, indent=2)+'\n', newline='\n')
    (output/'authelia-configuration.json').write_text(json.dumps(identity_config(data), indent=2)+'\n', newline='\n')
    hub = '[Interface]\nAddress = ' + HUB + '/32\nListenPort = ' + str(port) + '\nPrivateKey = REPLACE_WITH_HUB_PRIVATE_KEY\n'
    for site in data['sites']:
        hub += '\n# ' + site['id'] + '\n[Peer]\nPublicKey = ' + site['router_public_key'] + '\nAllowedIPs = ' + site['tunnel_ip'] + '/32\n'
        (output/(site['id']+'-router.sh')).write_text(router_script(data, site, server_key, endpoint, port), newline='\n')
    (output/'wg-atlantis.conf.template').write_text(hub, newline='\n')
    for path in output.iterdir():
        os.chmod(path, 0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--server-public-key', required=True)
    parser.add_argument('--endpoint', required=True)
    args = parser.parse_args()
    render(args.inventory, args.output, args.server_public_key, args.endpoint)
    print('Created staged configuration. No server or router was modified.')


if __name__ == '__main__':
    main()
