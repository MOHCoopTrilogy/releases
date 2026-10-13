"""Append the entries of a lane bug file to .wolf/buglog.json. The next id is read from the log's tail right before the
write; the log is edited as BYTES (it has mixed LF / CRLF line endings - a text-mode rewrite would touch every line).

    python append_bugs.py bugs_g43irons4.json [--dry]
"""
import json, re, sys, time
LOG = r'C:\mohaa-coop-dev\.wolf\buglog.json'
src = json.load(open(sys.argv[1], encoding='utf-8'))
raw = open(LOG, 'rb').read()
n = max(int(m) for m in re.findall(rb'"id":\s*"bug-(\d+)"', raw))
k = raw.rstrip().rfind(b']')
nl = b'\r\n' if raw[:k].rstrip(b' \t').endswith(b'\r\n') else b'\n'
ts = time.strftime('%Y-%m-%dT%H:%M:%S-06:00')
add = b''
ids = []
for e in src:
    n += 1
    ent = {"id": "bug-%d" % n, "timestamp": ts, "error_message": e["error_message"], "file": e["file"], "root_cause": e["root_cause"],
           "fix": e["fix"], "tags": e["tags"], "related_bugs": e.get("related_bugs", []), "occurrences": 1, "last_seen": ts}
    body = "\n".join("  " + l for l in json.dumps(ent, indent=2, ensure_ascii=True).split("\n"))
    add += b',' + nl + body.replace("\n", nl.decode()).encode('ascii')
    ids.append(ent["id"])
out = raw[:k].rstrip() + add + nl + b']' + nl
json.loads(out.decode('utf-8'))
if '--dry' in sys.argv:
    print('dry:', ids)
else:
    open(LOG, 'wb').write(out)
    print('appended', ids[0], '..', ids[-1])
