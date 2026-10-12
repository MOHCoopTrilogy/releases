"""Append entries to .wolf/buglog.json WITHOUT rewriting it: only the closing bracket is replaced (the file is mixed
LF / CRLF and four lanes append to it). The highest numeric id is read right before the write.

    python buglog_add.py <entries.json>      entries = a list of objects WITHOUT "id" (error_message, file, root_cause, fix, tags)
"""
import sys, os, re, json, time
LOG = r'C:\mohaa-coop-dev\.wolf\buglog.json'
ents = json.load(open(sys.argv[1], encoding='utf-8'))
now = time.strftime('%Y-%m-%dT%H:%M:%S') + '-06:00'
with open(LOG, 'r+b') as f:
    raw = f.read()
    top = max(int(x) for x in re.findall(rb'"id":\s*"bug-(\d+)"', raw))
    k = raw.rstrip().rfind(b']')
    assert raw[k:].strip() == b']'
    j = k
    while raw[j - 1:j] in (b'\n', b'\r', b' ', b'\t'):
        j -= 1
    assert raw[j - 1:j] == b'}'
    out = []
    for i, e in enumerate(ents):
        o = {'id': 'bug-%d' % (top + 1 + i), 'timestamp': now}
        o.update(e)
        o.setdefault('related_bugs', []); o.setdefault('occurrences', 1); o.setdefault('last_seen', now)
        txt = json.dumps(o, indent=2, ensure_ascii=False)
        out.append('\n'.join('  ' + l for l in txt.split('\n')))
    f.seek(j)
    f.truncate()
    f.write((',\n' + ',\n'.join(out) + '\n]\n').encode('utf-8'))
print('appended', ['bug-%d' % (top + 1 + i) for i in range(len(ents))])
json.load(open(LOG, encoding='utf-8'))
