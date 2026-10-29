"""Prepare a PRIVATE per-unit config bundle for a common development image.

No flash operation. Intended only for a verified OpenWrt initial-provisioning
fixture using sysupgrade -f; this replaces site configuration, not a routine update.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile

from build_support import validate_unit


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create(unit_path, manifest_path, image, output):
    unit = json.loads(unit_path.read_text())
    serial = validate_unit(unit)
    manifest = json.loads(manifest_path.read_text())
    if (manifest.get('board'), manifest.get('profile'), manifest.get('mode')) != (
            'A-14329-MB00', 'hilink_hlk-7628n', 'unprovisioned-validation'):
        raise ValueError('Expected the common MB00 unprovisioned development image')
    if 'sysupgrade' not in image.name:
        raise ValueError('A sysupgrade image is required')
    entries = [a for a in manifest.get('artifacts', []) if a.get('file') == image.name]
    if len(entries) != 1 or entries[0].get('sha256') != digest(image) or entries[0].get('bytes') != image.stat().st_size:
        raise ValueError('Image does not match build manifest')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(output, 0o700)
    payload = (json.dumps(unit, indent=2) + '\n').encode()
    config = output / 'unit-config.tar.gz'
    with config.open('xb') as target:
        os.chmod(config, 0o600)
        with tarfile.open(fileobj=target, mode='w:gz', format=tarfile.USTAR_FORMAT) as archive:
            entry = tarfile.TarInfo('etc/gateway/unit.json')
            entry.size = len(payload)
            entry.mode = 0o600
            entry.uid = entry.gid = 0
            entry.mtime = 0
            archive.addfile(entry, io.BytesIO(payload))
    bundle = {'schema': 'mb00-factory-bundle-1', 'unit_serial': serial,
              'image_file': image.name, 'image_sha256': digest(image),
              'image_source_revision': manifest.get('source_revision'),
              'config_file': config.name, 'config_sha256': digest(config),
              'operation': 'initial_provisioning_replaces_site_configuration',
              'hardware_tested': False, 'fixture_qualified': False}
    path = output / 'bundle.json'
    with path.open('x') as file:
        os.chmod(path, 0o600)
        json.dump(bundle, file, indent=2)
        file.write('\n')
    return bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--unit', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    bundle = create(args.unit, args.manifest, args.image, args.output)
    print('Created private first-provisioning bundle for ' + bundle['unit_serial'])
    print('No device accessed or programmed. Keep this folder private; qualify fixture on the first board.')


if __name__ == '__main__':
    main()
