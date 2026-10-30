"""Read WireGuard handshakes into an atomic portal status snapshot (no keys written)."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from .model import load


def collect(inventory, output):
    data = load(inventory, deployment=True)
    if Path(output).resolve() == Path(inventory).resolve():
        raise ValueError('Status output must not replace inventory')
    result = subprocess.run(['wg', 'show', 'wg-atlantis', 'latest-handshakes'],
                            text=True, capture_output=True, check=True, timeout=10)
    handshakes = {key: int(timestamp) for key, timestamp in
                  (line.split() for line in result.stdout.splitlines() if line.strip())}
    snapshot = {'collected_at': time.time(), 'peers':
                {s['id']: handshakes.get(s['router_public_key'], 0) for s in data['sites']}}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=output.parent, delete=False) as temp:
        json.dump(snapshot, temp)
        temp.write('\n')
        name = temp.name
    os.chmod(name, 0o600)
    os.replace(name, output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    collect(args.inventory, args.output)


if __name__ == '__main__':
    main()
