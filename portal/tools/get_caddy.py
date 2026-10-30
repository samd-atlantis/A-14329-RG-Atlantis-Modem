"""Fetch one pinned official Caddy validator; check vendor SHA512 and API SHA256."""
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import urllib.request
import zipfile

VERSION = '2.11.7'


def main():
    def read(url):
        headers = {'User-Agent': 'Atlantis-config-validation'}
        if url.startswith('https://api.github.com/') and os.environ.get('GH_TOKEN'):
            headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    release = json.loads(read('https://api.github.com/repos/caddyserver/caddy/releases/tags/v' + VERSION))
    suffix = 'windows_amd64.zip' if os.name == 'nt' else 'linux_amd64.tar.gz'
    asset = next(a for a in release['assets'] if a['name'].endswith(suffix))
    checksum = next(a for a in release['assets'] if a['name'].endswith('checksums.txt'))
    expected = next(line.split()[0] for line in read(checksum['browser_download_url']).decode().splitlines()
                    if line.split()[-1].lstrip('*') == asset['name'])
    content = read(asset['browser_download_url'])
    if hashlib.sha512(content).hexdigest() != expected or 'sha256:' + hashlib.sha256(content).hexdigest() != asset['digest']:
        raise SystemExit('Official validator checksum mismatch')
    filename = 'caddy.exe' if os.name == 'nt' else 'caddy'
    if os.name == 'nt':
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            binary = archive.read(filename)
    else:
        with tarfile.open(fileobj=io.BytesIO(content), mode='r:gz') as archive:
            binary = archive.extractfile(filename).read()
    folder = Path('.tools/caddy')
    folder.mkdir(parents=True, exist_ok=True)
    (folder/filename).write_bytes(binary)
    os.chmod(folder/filename, 0o700)
    (folder/'source.json').write_text(json.dumps({'version': VERSION, 'asset': asset['browser_download_url'],
        'archive_sha256': hashlib.sha256(content).hexdigest(), 'archive_sha512': expected}, indent=2))
    print('Verified Caddy ' + VERSION + ': ' + str(folder/filename))


if __name__ == '__main__':
    main()
