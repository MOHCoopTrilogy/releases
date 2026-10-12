"""Append entries to .wolf/buglog.json WITHOUT rewriting it (several agents write it at the same time): the highest
numeric id is read right before the write, the closing `]` is replaced in place by `,<entries>]`, everything before
it stays byte-identical. Entries come from a JSON file (a list of dicts without id / timestamps).

    python buglog_append.py <entries.json>
"""
import io, json, os, re, sys, time
P = r'C:\mohaa-coop-dev\.wolf\buglog.json'
new = json.load(io.open(sys.argv[1], encoding='utf-8'))
ts = time.strftime('%Y-%m-%dT%H:%M:%S') + '-06:00'
with open(P, 'r+b') as f:
    raw = f.read()
    ids = [int(x) for x in re.findall(rb'"id":\s*"bug-(\d+)"', raw)]
    n = max(ids) + 1
    end = raw.rstrip().rfind(b']')
    assert end > 0 and raw[end:].strip() == b']'
    body = raw[:end].rstrip()
    assert body.endswith(b'}')
    nl = b'\r\n' if raw[-2:] == b'\r\n' else b'\n'
    out = b''
    got = []
    for i, b in enumerate(new):
        e = dict(id='bug-%d' % (n + i), timestamp=ts)
        e.update(b)
        e.setdefault('tags', []); e.setdefault('related_bugs', []); e.setdefault('occurrences', 1); e['last_seen'] = ts
        txt = json.dumps(e, indent=2, ensure_ascii=False)
        txt = '\n'.join('  ' + ln for ln in txt.split('\n'))
        out += b',' + nl + txt.replace('\n', nl.decode()).encode('utf-8')
        got.append(e['id'])
    f.seek(len(body))
    f.truncate()
    f.write(out + nl + b']' + nl)
json.load(io.open(P, encoding='utf-8'))          # still valid JSON
print('appended', got)
