# Atlantis remote-access portal

Local implementation of customer site links, a tenant-filtered site directory,
Gateway/Controller 1–4 links, and generated WireGuard/Caddy/Authelia configuration.
Hosting is intentionally deferred at the user's request. No customer router,
server, DNS record or public firewall has been changed.

## Local preview

From the repository root:

```powershell
python -m portal.app --demo --port 8767
```

Open <http://127.0.0.1:8767/>. The preview binds loopback, labels every site as
demo, and shows device details instead of connecting to equipment. The sample
customer can see North Plant and South Plant; Other Customer is filtered out.

## Customer experience after deployment

Example domains below are placeholders; no production domain has been selected.
Plan DNS and wildcard/shared certificate issuance for the fleet before bulk rollout.

| Link | Purpose |
|---|---|
| `https://portal.access.example.test/sites/north-plant` | Stable customer site link; portal login/MFA and site permission required |
| `https://north-plant-gateway.access.example.test` | Gateway web interface; its native login remains required |
| `https://north-plant-c1.access.example.test` | Controller 1; its native login remains required |
| `https://north-plant-c2.access.example.test` | Controller 2 |
| `https://north-plant-c3.access.example.test` | Controller 3 |
| `https://north-plant-c4.access.example.test` | Controller 4 |

This replaces typing a cellular public IP and `:8585`. The browser uses HTTPS
on port 443 to the central service. Cellular IPs may change. Each router
initiates WireGuard to the hub with a 25-second keepalive. The cellular plan
must allow outbound UDP to the selected hub port.

Every site retains controller IPs `10.0.100.101–104`, mask `255.255.254.0`, and
gateway `10.0.100.7`. Each router has a different tunnel `/32`. Hub peer routes
contain only those unique tunnel addresses, never the overlapping controller LANs.
The gateway maps tunnel TCP ports 8101–8104 to its own controllers' HTTP port 80.
Only the hub tunnel IP can use those mappings or gateway HTTPS. There is no
general inter-site forwarding, SSH access, or cellular WAN port forwarding.

## What is implemented

- Read-only WSGI directory with authenticated-edge verification and per-site
  customer/admin authorization. Site data is filtered server-side. URLs and
  upstream destinations come from operator-owned inventory, never request parameters.
- Caddy reverse proxy configuration with Authelia forward authentication and
  default-deny, per-site, two-factor access policy. Native device Authorization,
  WWW-Authenticate, request bodies and cookies are preserved; the portal session
  cookie and identity headers are stripped before requests reach devices.
- One origin per device, root paths retained, known private-IP Location redirects
  rewritten, and device cookies made host-only. Device pages are not framed.
- Gateway TLS verification using that specific unit's trusted certificate and
  certificate DNS name. Verification is never disabled.
- Access audit records with authenticated principal, site/device and outcome.
  Request URI/query, all request headers and response headers are removed from
  these logs; device passwords, cookies and form bodies are not logged.
- Read-only WireGuard handshake collection. Old/missing snapshots show Unknown;
  tunnel handshake status does not claim controller/application health.
- Staged per-unit OpenWrt installer checking serial and registered router key.
  It does not start a tunnel. Firmware includes WireGuard packages and LuCI support,
  with `gateway.remote.enabled=0` by default.
- Gateway controller bookmarks select public HTTPS device origins when opened
  through the configured remote gateway host. Local access retains local HTTP IPs.

## Enrollment and server preparation

Use a private copy of `sites.example.json`; keep inventory, generated files,
secrets and certificate pins under `portal/private/` or private server storage.
The example has no working keys and cannot be rendered as a deployment.

1. Qualify the hardware/power and initial OpenWrt installation as described in
   `firmware/PROGRAMMING-MB00.txt`. Complete unique local provisioning first.
2. On each qualified router, create its WireGuard key locally under umask 077,
   mode 0600, at `/etc/gateway/wireguard.key`; register only `wg pubkey` output
   in its inventory entry. Never clone router private keys or put them in Git.
   Save the unit's exact serial and assign a unique `10.203.0.x/32` address.
3. Enroll a hub public key, endpoint DNS name and UDP port. Keep the hub private
   key on the Linux hub. Generate staged configuration:

   ```text
   python -m portal.render --inventory portal/private/sites.json --output portal/private/generated --server-public-key HUB_PUBLIC_KEY --endpoint vpn.your-domain.example
   ```

4. Verify the gateway certificate from a trusted fixture/local connection and
   retain its SHA256 fingerprint. Copy the PEM certificate to
   `/etc/atlantis/pki/<site-id>.pem` on the hub. Set `gateway_tls_name` to its
   actual DNS SAN, normally `OpenWrt` for the generated development certificate.
   If the source certificate is DER, convert it to PEM with OpenSSL. A regenerated
   certificate requires re-verification and pin replacement; do not skip TLS checks.
5. Install the reviewed WireGuard hub template as `wg-atlantis`, replacing its
   private-key placeholder. Peer AllowedIPs must remain unique `/32`s. The hub
   terminates proxy connections locally; keep IP forwarding disabled and reject
   peer-to-peer forwarding. Public listeners are only chosen WireGuard UDP,
   HTTPS 443 and any explicitly required ACME HTTP 80.
6. Install Caddy 2.11.7 and Authelia 4.39.28, rechecking security updates before a
   production freeze. Pin downloaded packages/images to verified hashes/digests.
   Generated `authelia-configuration.json` uses loopback and a filesystem notifier
   for staging. Configure real customer accounts (Argon2id hashes), TOTP enrollment,
   SMTP, storage permissions/backups, session and storage-encryption secrets before
   production. It is deliberately incomplete without those secrets and users.
   Supply secrets through Authelia's documented secret-file/environment support.
   Account group membership must match inventory groups. `atlantis-admin` grants
   access across sites and must be restricted to authorized Atlantis staff.
7. Run the portal backend on the same host and loopback as Caddy:

   ```text
   python3 -m venv .venv
   .venv/bin/pip install -r portal/requirements.txt
   # Provide private ATLANTIS_SITES, ATLANTIS_STATUS_FILE and ATLANTIS_EDGE_SECRET.
   .venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8767 'portal.app:production()'
   ```

   Use one independently generated edge secret of at least 32 characters in Caddy
   and the backend. It never goes to browsers or routers. Do not expose backend
   8767, Authelia 9091, status files, inventory or secrets publicly. Caddy must
   strip incoming identity/edge headers before authenticating and injecting its
   own. Preserve its generated `route` ordering. Validate configuration before start.
8. Run `python -m portal.status --inventory ... --output ...` with read-only
   WireGuard inspection privileges every 30 seconds through a reviewed systemd
   timer; the backend needs read access only to its filtered status snapshot.
9. Review the generated router installer, execute on its matching unit, confirm
   all controller gateways are `.7`, then enable only after the hub, certificate
   pin, account permissions and customer links are ready. The printed activation
   command reloads network configuration; use a maintenance/fixture session.

## Tests and current limits

```text
python portal/tools/get_caddy.py
python -m unittest discover -s portal/tests -v
node --check portal/static/app.js
```

The validator downloads pinned official Caddy 2.11.7 and verifies vendor SHA512
plus the release API SHA256. Tests use local HTTP/TLS fixtures and sample keys;
they do not contact customer equipment. They cover tenant isolation, spoofed
headers, original device login challenges and POST data, SSO-cookie removal,
gateway certificate verification, redirect rewriting and log redaction.
CI runs the same tests on Linux. Identity-provider responses in proxy tests are
fixtures; actual Authelia account/MFA enrollment still needs deployment validation.

The real Walchem interface and a real router must still be tested through the
complete stack: form/Basic/Digest login, redirects, cookies, AJAX, CSRF, WebSockets,
session expiry, logout, reconnect and permission revocation. Embedded absolute
URLs inside vendor JavaScript are not rewritten; if observed, handle that exact
model after testing. Generic text replacement could break controller operations.
There is no production hosting, DNS, customer account database, live tunnel,
remote firmware update service or demonstrated controller access yet.

Primary implementation references:

- https://www.wireguard.com/quickstart/
- https://www.authelia.com/integration/proxies/caddy/
- https://www.authelia.com/configuration/security/access-control/
- https://caddyserver.com/docs/caddyfile/directives/reverse_proxy
- https://caddyserver.com/docs/caddyfile/directives/forward_auth
