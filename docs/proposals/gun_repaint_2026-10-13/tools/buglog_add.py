"""Append this lane's defects to .wolf/buglog.json (ids from the file's tail at the moment of writing; the bytes
already there are not re-encoded). Run ONCE per entries file; the ids it wrote are stored next to it (<file>.done).

    python buglog_add.py <entries.json>      entries: [{error_message, file, root_cause, fix, tags, related_bugs?}]
"""
import json, re, sys, time, os
P = r"C:\mohaa-coop-dev\.wolf\buglog.json"


def main():
    src = sys.argv[1]
    if os.path.exists(src + ".done"):
        print("already appended:", open(src + ".done").read()); return
    E = json.load(open(src, encoding="utf-8"))
    ts = time.strftime("%Y-%m-%dT%H:%M:%S-06:00")
    txt = open(P, "rb").read().decode("utf-8")
    n = max(int(x) for x in re.findall(r'"id":\s*"bug-(\d+)"', txt)) + 1
    first = n
    out = []
    for e in E:
        d = dict(id="bug-%d" % n, timestamp=ts, error_message=e["error_message"], file=e["file"], root_cause=e["root_cause"],
                 fix=e["fix"], tags=e["tags"], related_bugs=e.get("related_bugs", []), occurrences=1, last_seen=ts)
        out.append("\n".join("  " + l for l in json.dumps(d, indent=2, ensure_ascii=False).splitlines()))
        n += 1
    k = txt.rstrip().rfind("]")
    new = txt[:k].rstrip() + ",\n" + ",\n".join(out) + "\n]\n"
    json.loads(new)
    open(P, "wb").write(new.encode("utf-8"))
    msg = "bug-%d .. bug-%d" % (first, n - 1)
    open(src + ".done", "w").write(msg)
    print("appended", msg)


if __name__ == "__main__":
    main()
