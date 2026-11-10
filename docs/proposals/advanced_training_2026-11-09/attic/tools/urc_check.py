"""urc_check.py <urc> [<urc> ...] - parse gates for a hand/generator-touched .urc (the shapes that silently drop a menu or a
widget): brace depth never negative and 0 at the end, braces balanced, every quote paired per line (outside // comments),
one `resource / <Kind> / {` header per block, no duplicate widget names, the file ends with `end.`, ASCII only, one line-ending
style. For main.urc also: the atticscene scenehot list and every hotspot's caption / proxy index agree. [advtrain 2026-11-10]"""
import re, sys

bad = 0
for f in sys.argv[1:]:
    raw = open(f, "rb").read()
    crlf, lf = raw.count(b"\r\n"), raw.count(b"\n")
    t = raw.decode("latin-1").replace("\r\n", "\n")
    errs = []
    if crlf and crlf != lf:
        errs.append("mixed line endings (%d CRLF of %d)" % (crlf, lf))
    if any(c > 126 for c in raw):
        errs.append("non-ASCII bytes")
    d = 0
    for n, ln in enumerate(t.split("\n"), 1):
        code = ln if not ln.lstrip().startswith("//") else ""
        if code.count('"') % 2:
            errs.append("odd quotes line %d" % n)
        s = re.sub(r'"[^"]*"', "", code)
        d += s.count("{") - s.count("}")
        if d < 0:
            errs.append("depth < 0 line %d" % n)
            break
    if d != 0:
        errs.append("depth %d at end" % d)
    blocks = re.findall(r"(?m)^resource\n(\w+)\n\{\n", t)
    if len(blocks) != len(re.findall(r"(?m)^resource$", t)):
        errs.append("a resource header is malformed")
    names = re.findall(r'(?m)^name "([^"]+)"', t)
    dup = sorted({x for x in names if names.count(x) > 1})
    if dup:
        errs.append("duplicate names %s" % dup)
    if not t.rstrip().endswith("end."):
        errs.append("no end.")
    if 'name "atticscene"' in t:
        s0 = t.index('name "atticscene"')
        blk = t[s0:t.index("\n}\n", s0)]
        hots = re.findall(r'(?m)^scenehot "(\w+)" .*"hot_(\w+)"', blk)
        for i, (h, proxy) in enumerate(hots, 1):
            m = re.search(r'name "hot_%s"\n.*?hovercommand "set ui_scene_hot (\d+)"' % re.escape(proxy), t, re.S)
            if m and int(m.group(1)) != i:
                errs.append("hotspot %s is #%d but its proxy says %s" % (h, i, m.group(1)))
            c = re.search(r'name "atticsign_%s"\n.*?ui_scene_hot==(\d+)' % re.escape(proxy), t, re.S)
            if c and int(c.group(1)) != i:
                errs.append("hotspot %s is #%d but its caption says %s" % (h, i, c.group(1)))
        print("  atticscene hotspots: %s" % ", ".join("%d %s" % (i, h) for i, (h, _p) in enumerate(hots, 1)))
    print("%s: %d resources, %s" % (f, len(blocks), "; ".join(errs) if errs else "OK"))
    bad += bool(errs)
sys.exit(1 if bad else 0)
