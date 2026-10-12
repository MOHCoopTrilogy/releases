"""Append entries to .wolf/buglog.json (schema kept; ids = the file's highest numeric id + 1 read at write time;
existing bytes untouched; the result is parsed before it is written).

    python buglog_add.py <entries.json> [timestamp]      entries: [{error_message, file, root_cause, fix, tags}, ...]
"""
import re, json, sys, time
p = r'C:\mohaa-coop-dev\.wolf\buglog.json'
E = json.load(open(sys.argv[1], encoding='utf-8'))
TS = sys.argv[2] if len(sys.argv) > 2 else time.strftime('%Y-%m-%dT%H:%M:%S-06:00')
s = open(p, 'rb').read().decode('utf-8')
n = max(int(x) for x in re.findall(r'"id":\s*"bug-(\d+)"', s))
out = ''
for i, e in enumerate(E):
    d = dict(id='bug-%d' % (n + 1 + i), timestamp=TS, error_message=e['error_message'], file=e['file'], root_cause=e['root_cause'],
             fix=e['fix'], tags=e['tags'], related_bugs=e.get('related_bugs', []), occurrences=1, last_seen=TS)
    body = json.dumps(d, indent=2, ensure_ascii=False)
    out += ',\n' + '\n'.join('  ' + l for l in body.split('\n'))
k = s.rstrip().rfind(']')
head = s[:k].rstrip()
assert head.endswith('}')
new = head + out + '\n]\n'
json.loads(new)
open(p, 'wb').write(new.encode('utf-8'))
print('added', ' '.join('bug-%d' % (n + 1 + i) for i in range(len(E))))
