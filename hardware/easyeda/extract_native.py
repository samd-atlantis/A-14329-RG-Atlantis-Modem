import json
import sys
import zipfile
from pathlib import Path

source, output = map(Path, sys.argv[1:])
documents = []
with zipfile.ZipFile(source) as archive:
    for name in archive.namelist():
        if not name.endswith('.epru'):
            continue
        head = None
        rows = {}
        for line in archive.read(name).decode('utf-8-sig').split('\n'):
            line = line.rstrip('\r')
            if not line:
                continue
            if line.endswith('|'):
                line = line[:-1]
            a, b = line.split('||', 1)
            h = json.loads(a)
            body = json.loads(b) if b else None
            if h['type'] == 'DOCHEAD':
                if head:
                    documents.append({'head': head, 'records': [r for r in rows.values() if r['b'] is not None]})
                head = {'h': h, 'b': body}
                rows = {}
            else:
                rows[h['id']] = {'h': h, 'b': body}
        if head:
            documents.append({'head': head, 'records': [r for r in rows.values() if r['b'] is not None]})
output.write_text(json.dumps(documents, ensure_ascii=False), encoding='utf-8')
print(len(documents), 'documents extracted')
