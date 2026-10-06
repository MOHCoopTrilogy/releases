"""Download / VRAM estimate for the full weapon HD set, from inventory.json (same grouping as audit.py).

Target sizes (DXT1, full mips = w*h/2 * 4/3 bytes):
  main sheet of a base gun (its largest)       : min(4096, 4 x source long side), POT
  other sheets of a base gun (clips, sights...) : min(2048, 4 x source long side)
  skin-variant sheets (coop_v3 / Hobbs / LV...) : min(2048, 4 x source)
  baked finishes (bloody + 3 camo)              : options A 1024 / B 2048
Source = HRRTM lossless size when it exists (else the loaded image). Shared sheets are counted once.
"""
import json, os, math, collections
HERE = os.path.dirname(os.path.abspath(__file__))
inv = json.load(open(os.path.join(HERE, "inventory.json")))
HRR = {"kar98/kar98": 1536, "thompsonsmg/thompsonsmg": 1536, "colt45/colt45": 1536, "m1garand/garand": 1536,
       "mp40/mp40": 1280, "mp44/mp44": 1536, "p38/p38": 1536, "panzerschreck/pschreck": 1280,
       "springfield/springfield": 1792, "winchester/winchester": 1536, "bar/bar": 1536}
SKIP = ("/common/", "textures/effects/", "env_sheen", "models/crates/", "/k5", "howitzer")


def pot(n):
    return 1 << max(0, int(math.ceil(math.log2(max(n, 1)))))


def dxt1(w, h):
    return int(w * h / 2 * 4 / 3)


main, other, var, fin = {}, {}, {}, {}
for t in inv:
    if not t["weapon"]:
        continue
    k = t["tik"].split("/")[-1][:-4].lower()
    is_var = k.count("_") and any(s in k for s in ("_hobbs", "_guan", "_lv_", "_dh", "_coltpa", "_pagarand", "_pabar", "_colt1911w",
                                                     "_bloodyeic", "_covert", "_drbond", "_m1a1dk", "_authwinch",
                                                     "_g98", "_mp18", "_mp40r2", "_mp44strap", "_c96trench", "_bar1918",
                                                     "_famastommy", "_tommy", "_ttc", "_98ks", "_p14", "_ofenrohr", "_hobbs"))
    sheets = []
    for s in t["surfaces"]:
        for x in s["textures"]:
            p = x["loads"]
            if not p or any(z in p for z in SKIP):
                continue
            i = x["info"] or {}
            sheets.append((p, max(i.get("w") or 0, i.get("h") or 0)))
    if not sheets:
        continue
    if t["finish"]:
        for p, m in sheets:
            if "coop_skins/" in p:
                fin[p] = m
        continue
    target = var if is_var else None
    big = max(sheets, key=lambda s: s[1])
    for p, m in sheets:
        key = p.replace("textures/models/weapons/", "").rsplit(".", 1)[0].lower()
        src = HRR.get(key, m)
        if target is var:
            if p not in main and p not in other:
                var[p] = min(2048, pot(4 * src))
        elif p == big[0]:
            main[p] = max(main.get(p, 0), min(4096, pot(4 * src)))
        else:
            other.setdefault(p, min(2048, pot(4 * src)))
for p in list(other):
    if p in main:
        del other[p]
for p in list(var):
    if p in main or p in other:
        del var[p]


def tot(d, cap=None):
    return sum(dxt1(min(s, cap or s), min(s, cap or s)) for s in d.values())


Z = 0.92      # measured zip ratio on the pilot DXT1 sheets is filled in by the report (DXT1 barely deflates)
rows = [("main sheets (<=4096)", len(main), tot(main)), ("other sheets (<=2048)", len(other), tot(other)),
        ("skin variants (<=2048)", len(var), tot(var)), ("baked finishes @1024", len(fin), tot({k: 1024 for k in fin})),
        ("baked finishes @2048", len(fin), tot({k: 2048 for k in fin}))]
for n, c, b in rows:
    print("%-26s %4d sheets  %7.0f MB on disk/VRAM-if-all-loaded  ~%5.0f MB zipped" % (n, c, b / 1e6, b * Z / 1e6))
cap2048 = tot(main, 2048) + tot(other) + tot(var)
print("ALT all main sheets capped at 2048:  %7.0f MB" % (cap2048 / 1e6))
print("main-sheet size histogram:", collections.Counter(main.values()))
json.dump(dict(main=main, other=other, var=var, fin=list(fin)), open(os.path.join(HERE, "estimate.json"), "w"), indent=1)
