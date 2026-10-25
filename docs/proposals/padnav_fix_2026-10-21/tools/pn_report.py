"""pn_report.py <qconsole.log> - per-page focus-trap report from a pn_client.py sweep run.

For every `^~^~^ PAGE <name>` section: the candidate widgets (PADCAND lines, first press), the widgets focus actually
reached (PADNAV ... moved ... widget 'x' and 'dpad -> slider' hits), the presses a focused widget swallowed
('eaten by'), presses that found nothing ('none'), and the verdict (REACHED ALL / unreached list).
"""
import re, sys, collections

txt = open(sys.argv[1], encoding="latin-1").read()
secs = re.split(r"\^~\^~\^ PAGE (\S+)", txt)
rows = []
for i in range(1, len(secs), 2):
    name, body = secs[i], secs[i + 1]
    cands = []
    for m in re.finditer(r"\^~\^~\^ PADCAND (\S+) (-?\d+) (-?\d+)", body):
        if m.group(1) not in cands:
            cands.append(m.group(1))
    moved = collections.OrderedDict()
    none = eaten = presses = 0
    eatby = collections.Counter()
    for m in re.finditer(r"\^~\^~\^ PADNAV (.*)", body):
        L = m.group(1)
        if L.startswith("dir"):
            presses += 1
            mm = re.search(r"-> moved .* widget '([^']*)'", L)
            if mm:
                moved[mm.group(1)] = 1
            else:
                none += 1
        elif "eaten by" in L and not L.startswith("key"):
            eaten += 1
            eatby[re.search(r"eaten by '([^']*)'", L).group(1)] += 1
        elif L.startswith("key") and "eaten by" in L:
            eaten += 1
            eatby[re.search(r"eaten by '([^']*)'", L).group(1)] += 1
        elif "-> slider" in L:
            pass
    # offline model of PadNavigate (same scoring: fwd + 2*lateral, fwd >= 2) over the PADCAND centres: is every
    # candidate reachable from every other with the 4 directions?  (the dynamic snake walk below cannot prove that)
    pts = {}
    for m in re.finditer(r"\^~\^~\^ PADCAND (\S+) (-?\d+) (-?\d+)", body):
        pts.setdefault(m.group(1), (int(m.group(2)), int(m.group(3))))
    def step(a, d):
        ax, ay = pts[a]; best = None
        for b, (bx, by) in pts.items():
            if b == a:
                continue
            fwd = (bx - ax) * d[0] + (by - ay) * d[1]
            lat = abs(by - ay) if d[0] else abs(bx - ax)
            if fwd < 2:
                continue
            sc = fwd + lat * 2
            if best is None or sc < best[0]:
                best = (sc, b)
        return best[1] if best else None
    graph = {a: [step(a, d) for d in ((0, -1), (0, 1), (-1, 0), (1, 0))] for a in pts}
    cut = []
    for a in pts:
        seen = {a}; todo = [a]
        while todo:
            x = todo.pop()
            for y in graph[x]:
                if y and y not in seen:
                    seen.add(y); todo.append(y)
        if len(seen) < len(pts):
            cut.append("%s(sees %d of %d)" % (a, len(seen), len(pts)))
    unreached = cut
    rows.append((name, len(cands), len(moved), unreached, eaten, dict(eatby), none, presses))
print("%-18s %5s %7s %6s %5s  %s" % ("page", "cands", "reached", "eaten", "none", "candidates that cannot reach all others (offline model) / swallowing widgets"))
bad = 0
for name, nc, nm, un, ea, eb, no, pr in rows:
    flag = "OK " if not un and not ea else "BAD"
    bad += flag == "BAD"
    print("%s %-14s %5d %7d %6d %5d  %s%s" % (flag, name, nc, nm, ea, no, ",".join(un[:12]), ("  EATEN " + str(eb)) if eb else ""))
print("pages", len(rows), "with a trap", bad)
