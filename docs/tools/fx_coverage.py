#!/usr/bin/env python3
"""fx_coverage.py - every smoke and fire asset the game can load, each marked upgraded / excluded / todo
(smoke & fire update, docs/proposals/smokefire_2026-11-24/PLAN.md; user 2026-11-24: "EVERY type of smoke covered").

    python docs/tools/fx_coverage.py report   # write docs/proposals/smokefire_2026-11-24/COVERAGE.md + coverage.json
    python docs/tools/fx_coverage.py check    # build gate: exit 1 on any FAIL (see below)
    python docs/tools/fx_coverage.py winner <path>   # which pak wins a file (and the whole chain)
    --strict  also fail while any asset is still todo (the end-of-update gate)
    options: --live (the user's install G:/mohaa-gl2, read only, instead of the shipped set)
             --with <pak> (add/replace one pak, e.g. a candidate build; repeatable)

THE SET. Shipped = retail GOG main/*.pk3, mainta/*.pk3, maintt/pak1-4 (basepath) + every home/maintt pak listed in
manifests/latest.json, resolved to the mod tree copy (what the next build ships) else the GOG maintt copy. The live
install is NOT the shipped set (dev-only paks skew audits - TRAPS); use --live only to compare.
Priority = FS_AddGameDirectory2: main < mainta < maintt, basepath < homepath, inside one dir case-insensitive byte
order, the LAST-sorted pak wins. Shader names: the definition in the highest-priority pak's file wins (bug-2228).

ASSETS (derived, never hand-listed): effect tiks under models/fx + models/emitters whose name or sprites say smoke /
fire / blast / steam / spark / dust (FAMILIES below); every sprite shader those tiks draw; the muzzle smoke inside
weapon tiks (one row per sprite, with the weapon count); the VSS smoke types; the converter-built disc effects.
STATUS (authored judgement, docs/tools/assets/fx/fx_coverage.json): ordered rules {match, status, reason, expect};
first match wins. `expect` = a regex the WINNING pak must match (so "upgraded" is verified, not claimed).

FAIL (check exits 1): an asset no rule classifies; an `upgraded` asset whose winning copy is not the expected pak
(fx_1025's grenade and bazooka lost to hd_fxfix from v1.10.37 on); an `upgraded` tik that is parse-broken
(unbalanced braces/parens - parse killers); a rule that matches nothing (stale registry).
"""
import io, json, os, re, struct, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import discstock_vfs as dv   # noqa: E402  (shader parser, image resolution)

GOG = r"G:/GOG/Medal of Honor - Allied Assault War Chest"
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
MANIFEST = os.path.join(ROOT, "manifests", "latest.json")
RULES = os.path.join(HERE, "assets", "fx", "fx_coverage.json")
OUTDIR = os.path.join(ROOT, "docs", "proposals", "smokefire_2026-11-24")
LIVE_BASE, LIVE_HOME = r"G:/mohaa-gl2", r"G:/mohaa-gl2/home"

FAMILIES = [   # (family, regex on the path after models/) - first match wins; order matters
    ("impacts", r"fx/(bh_|fs_)"),
    ("muzzle", r"(gunsmoke|barrelsmoke|snipesmoke|garandsmoke|muzzle\w*smoke|tankcanon)"),
    ("grenade", r"fx/(grenexp_|f1grenade|millsgrenade|m2fgrenade|riflegrenade|deadlygrenade|exp_grenade|fx_grenade_explosion|maingrenade|gren_exp)|emitters/gren_exp|fxp_gren"),
    ("smoke grenade", r"(smokegrenade|m18_smoke|rdg-1|rdg1|nebelhandgranate|signalsmoke|smokescreen|screensmoke|smoke_grenade)"),
    ("artillery", r"(mortar|nebel|exp_artshell|explosionartillery|hs_artillery|granatwerfer|heavyshellexp|smoke_airstrike|artillery)"),
    ("rocket/shell", r"fx/(bazooka|scriptbazooka|tankexp_|tankshell|explosiontiger|explosionking|explosionpanzer|explosionpzb|explosionpiat|shelldamage)|rocketgood"),
    ("vehicle/aircraft", r"(tank_explosion|exp_tank|explosion_tank|exp_truck|truck_explosion|supplytruck|bike_explosion|stuka|aircraft_explosion|c47_|planesmoke|plane_smoke|pe8_fleet|shermansmoke|tanksmoke|veltro|tankcrash|coop_wreck|smoketrail|firetrail)"),
    ("flak", r"flak|miniaa"),
    ("set-piece blast", r"(explosion|blast|exploder|banger|popper|mushroom|coop_blast)"),
    ("map fire", r"(fire|flame|torch|candle|lantern|inferno|burn|campfire|brazier|ember)"),
    ("smoke/steam", r"(smoke|steam|stack|chimney|mist|vapo|fume|breath)"),
    ("sparks", r"(spark|welding|electric|blowtorch|panelmelt|brokenlight)"),
    ("dust/debris", r"(dust|debris|dirt|jib|crete|plume|fallingdirt)"),
]
SMOKE_SPRITE = re.compile(r"(smoke|vss|puff|fire|flame|expl|boom|blast|spark|ember|soot|dust|steam|flak|campfire|bridgecharge|tehao|cfx_|candel|candl|mist|plume|cloud|haze)", re.I)
VSS_TYPES = ["mist", "greasefire", "steam", "heavy", "bulletimpact", "fire"]   # cg_volumetricsmoke.cpp:30-43


def pathkey(s):
    return [ord("/") if c in "\\:" else ord(c.lower()) for c in os.path.basename(s)]


class PakVFS(dv.VFS):
    """dv.VFS over an explicit pak list (low -> high priority)."""
    def __init__(self, paks):
        self.paks, self.index, self._zips = list(paks), {}, {}
        for prio, p in enumerate(self.paks):
            try:
                z = zipfile.ZipFile(p)
            except Exception as e:
                print("fx_coverage: cannot open %s (%s)" % (p, e))
                continue
            for zi in z.infolist():
                if not zi.is_dir():
                    self.index.setdefault(zi.filename.lower().replace("\\", "/"), []).append((prio, p, zi.filename, zi.file_size))


def retail_paks():
    out = []
    for gd in ("main", "mainta", "maintt"):
        d = os.path.join(GOG, gd)
        names = [f for f in os.listdir(d) if f.lower().endswith(".pk3")]
        if gd == "maintt":
            names = [f for f in names if re.match(r"(?i)pak\d+\.pk3$", f)]
        out += [os.path.join(d, f) for f in sorted(names, key=pathkey)]
    return out


def shipped_paks(extra=()):
    man = json.load(open(MANIFEST, encoding="utf-8-sig"))
    names = [f["path"].split("/")[-1] for f in man["files"] if f["path"].lower().startswith("home/maintt/") and f["path"].lower().endswith(".pk3")]
    extra_by = {os.path.basename(p).lower(): p for p in extra}
    home, missing = [], []
    for n in names:
        if n.lower() in extra_by:
            home.append(extra_by.pop(n.lower()))
            continue
        for cand in (os.path.join(MOD, n), os.path.join(GOG, "maintt", n)):
            if os.path.isfile(cand):
                home.append(cand)
                break
        else:
            missing.append(n)
    home += list(extra_by.values())
    return retail_paks() + sorted(home, key=pathkey), man.get("version"), missing


def live_paks(extra=()):
    out = []
    for gd in ("main", "mainta", "maintt"):
        for root in (LIVE_BASE, LIVE_HOME):
            d = os.path.join(root, gd)
            if os.path.isdir(d):
                out += [os.path.join(d, f) for f in sorted((f for f in os.listdir(d) if f.lower().endswith(".pk3")), key=pathkey)]
    return out + list(extra), "live", []


_COMMENT = re.compile(r"//[^\n]*|/\*.*?(\*/|\Z)", re.S)


def strip(t):
    """one left-to-right pass like the script tokenizer: whichever of // and /* comes first wins, so a '//****'
    banner line is a line comment, not the start of a block comment (two passes swallowed whole emitters)"""
    return _COMMENT.sub(lambda m: " " if m.group(0).startswith("/*") else "", t)


def tik_text(vfs, path, depth=0):
    """the tik with its $include files expanded (MOHAA TIKI include)"""
    raw = vfs.read_name(path)
    if raw is None:
        return None
    t = strip(raw.decode("latin-1"))
    if depth < 3:
        d = os.path.dirname(path)
        def inc(m):
            p = m.group(1).replace("\\", "/")
            for c in (p, d + "/" + p):
                s = tik_text(vfs, c.lower(), depth + 1)
                if s is not None:
                    return s
            return "\n// MISSINGINCLUDE %s\n" % p
        t = re.sub(r"(?im)^\s*\$include\s+(\S+)", inc, t)
    return t


def health(t):
    b = neg = 0
    for ch in t:
        if ch == "{":
            b += 1
        elif ch == "}":
            b -= 1
            neg = neg or b < 0
    p = t.count("(") - t.count(")")
    bad = ["missing $include %s" % m for m in re.findall(r"// MISSINGINCLUDE (\S+)", t)]
    if b or neg:
        bad.append("braces %+d%s" % (b, " (negative)" if neg else ""))
    if p:
        bad.append("parens %+d" % p)
    return bad


def sprites_of(t):
    return sorted(set(m.lower() for m in re.findall(r"\bmodel\s+\"?([\w\-/\.]+?)\.spr\b", t, re.I)))


def surface_shaders(t):
    """shaders on a tik's own surfaces (unitsquare / spritebeam style effects draw these, not .spr)"""
    return sorted(set(m.lower() for m in re.findall(r"(?im)^\s*surface\s+\S+\s+shader\s+\"?([\w\-/\.]+)", t)))


def family(path, spr, t):
    s = path.split("models/", 1)[1]
    for n, rx in FAMILIES:
        if re.search(rx, s, re.I):
            return n
    if "volumetric" in t.lower() or any(SMOKE_SPRITE.search(x) for x in spr):
        return "other smoke/fire (by content)"
    return None


def kind(pak):
    l = os.path.basename(pak).lower()
    if re.match(r"pak\d", l):
        return "retail"
    if "coop" in l or "hzm" in l:
        return "ours"
    return "3rd-party"


def sprite_size(vfs, sh, name):
    """(world size units, image w, spritescale, frames, blend) of a sprite shader under this VFS"""
    d = sh.get(name)
    imgs = sh.images(name)
    body = d[4] if d else ""
    first = imgs[0][1] if imgs else name
    fn, e = vfs.resolve_image(first)
    w = (vfs.image_size(e) or (None,))[0] if e else None
    sc = dv.shader_spritescale(body) if d else None
    frames = sum(1 for k, _ in imgs if k.startswith("animmap") or k == "clampanimmap") or 1
    bm = re.search(r"(?im)^\s*blendfunc\s+(.+)$", body)
    return (w * (sc if sc else 1.0) if w else None, w, sc, frames, bm.group(1).strip().lower() if bm else "", fn, e)


def build(live=False, extra=()):
    paks, ver, missing = (live_paks if live else shipped_paks)(extra)
    vfs = PakVFS(paks)
    rvfs = PakVFS(retail_paks())
    sh, rsh = dv.Shaders(vfs), dv.Shaders(rvfs)
    assets = []   # dict(id, kind, family, winner, chain, detail, health)

    def add(aid, akind, fam, entry_name, detail, bad=()):
        ents = vfs.all(entry_name) if entry_name else []
        assets.append(dict(id=aid, kind=akind, family=fam, winner=os.path.basename(ents[-1][1]) if ents else "",
                           winkind=kind(ents[-1][1]) if ents else "", chain=[os.path.basename(e[1]) for e in ents],
                           detail=detail, health=list(bad)))

    used_spr, used_surf = {}, {}
    for k in sorted(x for x in vfs.index if re.match(r"models/(fx|emitters)/.+\.tik$", x)):
        t = tik_text(vfs, k) or ""
        spr = sprites_of(t)
        fam = family(k, spr, t)
        if not fam:
            continue
        for s in spr:
            used_spr.setdefault(s, set()).add(fam)
        dl = len(re.findall(r"dlight|firelight", t, re.I))
        vss = sorted(set(m.lower() for m in re.findall(r"(?is)\bvolumetric\b.*?\bmodel\s+\"?(\w+)", t)))
        surf = surface_shaders(t)
        for s in surf:
            used_surf.setdefault(s, set()).add(fam)
        kids = sorted(set(m.lower() for m in re.findall(r"\b([\w\-/]+\.tik)\b", t, re.I)) - {k, k.split("/", 1)[1]})
        ex = sorted(set(m.lower() for m in re.findall(r"(?i)\bexplosioneffect\s+(\w+)", t)))
        det = "sprites %s" % (",".join(spr[:4]) + ("..." if len(spr) > 4 else ""))
        det += "".join(["; vss %s" % ",".join(vss) if vss else "", "; surfaces %s" % ",".join(surf) if surf else "", "; spawns %s" % ",".join(os.path.basename(x) for x in kids[:3]) if kids else "",
                        "; explosioneffect %s" % ",".join(ex) if ex else "", "; lights %d" % dl if dl else ""])
        add("tik:" + k, "tik", fam, k, det, health(t))

    # muzzle smoke inside weapon tiks: one row per sprite, counted
    wsm = {}
    for k in (x for x in vfs.index if x.startswith("models/weapons/") and x.endswith(".tik")):
        t = tik_text(vfs, k) or ""
        for s in sprites_of(t):
            if SMOKE_SPRITE.search(s):
                wsm.setdefault(s, []).append(k)
    for s, ws in sorted(wsm.items()):
        used_spr.setdefault(s, set()).add("muzzle")
        add("weaponsmoke:" + s, "weapon smoke", "muzzle", None, "%d weapon tiks, e.g. %s" % (len(ws), os.path.basename(sorted(ws)[0])))

    for v in VSS_TYPES:
        add("vss:" + v, "vss type", "volumetric smoke", None, "renders VSSSource.spr / VSSSource2.spr (cg_volumetricsmoke.cpp:1167)")
    for s in ("vsssource", "vsssource2"):
        used_spr.setdefault(s, set()).add("volumetric smoke")

    rows = [("sprite", s, f) for s, f in used_spr.items()] + [("surface", s, f) for s, f in used_surf.items() if s not in used_spr]
    for pre, s, fams in sorted(rows):
        d = sh.get(s)
        size, w, sc, fr, bl, fn, e = sprite_size(vfs, sh, s)
        rsize = sprite_size(rvfs, rsh, s)[0] if rsh.get(s) or rvfs.resolve_image(s)[1] else None
        bad = []
        isspr = pre == "sprite" or (d is not None and re.search(r"(?i)\bspritegen\b", d[4]))
        if isspr and size and rsize and size / rsize > 1.5:
            bad.append("draws %.1fx retail size" % (size / rsize))
        if d is None and not e:
            bad.append("missing shader and image")
        detail = "%s; %s px%s, %d fr, %s; img %s" % ("/".join(sorted(fams)), w or "?", " x%.3g" % sc if sc else "", fr, bl or "-",
                                                      os.path.basename(e[1]) if e else "MISSING")
        ents = [] if d is None else [(None, d[2])]
        assets.append(dict(id=pre + ":" + s, kind=pre + " shader", family="sprites" if pre == "sprite" else "surfaces",
                           winner=os.path.basename(d[2]) if d else (os.path.basename(e[1]) if e else ""),
                           winkind=kind(d[2]) if d else (kind(e[1]) if e else ""), chain=[], detail=detail, health=bad))

    for conv, what in (("fl:flpfx", "Frontline particle systems (docs/tools/frontline/flpfx.py) - built on the player's PC"),
                       ("ea:eafx", "Euro Assault effect packages (docs/tools/ea/eafx.py) - built on the player's PC")):
        assets.append(dict(id="disc:" + conv, kind="disc converter", family="disc missions", winner="(player's converted pak)",
                           winkind="disc", chain=[], detail=what, health=[]))
    return assets, ver, missing, paks


def classify(assets):
    rules = json.load(open(RULES, encoding="utf-8"))["rules"]
    hits = [0] * len(rules)
    fails = []
    for a in assets:
        for i, r in enumerate(rules):
            if re.search(r["match"], a["id"], re.I) and (not r.get("family") or re.search(r["family"], a["family"], re.I))                     and (not r.get("detail") or re.search(r["detail"], a["detail"], re.I)):
                hits[i] += 1
                a["status"], a["reason"] = r["status"], r.get("reason", "")
                if r["status"] == "excluded" and a["health"] and a["kind"] == "tik":
                    # a parse-broken tik is never "left alone on purpose": what it should draw is unknown until repaired
                    a["status"], a["reason"] = "todo", "parse-broken - repair first (PLAN D3/D4); rule said: " + a["reason"]
                if r["status"] == "upgraded":
                    exp = r.get("expect")
                    if exp and not re.search(exp, a["winner"], re.I):
                        fails.append("%s: marked upgraded (%s) but the winning copy is %s (chain %s)" % (a["id"], r.get("reason", ""), a["winner"], " < ".join(a["chain"])))
                    if a["health"] and a["kind"] == "tik":
                        fails.append("%s: marked upgraded but parse-broken (%s)" % (a["id"], "; ".join(a["health"])))
                break
        else:
            a["status"], a["reason"] = "UNCLASSIFIED", ""
            fails.append("%s: no rule classifies it (add it to %s)" % (a["id"], os.path.relpath(RULES, ROOT)))
    for i, r in enumerate(rules):
        if not hits[i]:
            fails.append("rule %d (%s) matches nothing - stale registry" % (i, r["match"]))
    return fails


def report(assets, fails, ver, missing, paks):
    os.makedirs(OUTDIR, exist_ok=True)
    cnt = {}
    for a in assets:
        cnt.setdefault(a["family"], {}).setdefault(a["status"], 0)
        cnt[a["family"]][a["status"]] += 1
    L = ["# Smoke and fire coverage (DERIVED - `python docs/tools/fx_coverage.py report`; do not edit)", "",
         "Set: shipped v%s (%d paks)%s. Status rules: `docs/tools/assets/fx/fx_coverage.json`." % (ver, len(paks), "; MISSING locally: " + ", ".join(missing) if missing else ""), "",
         "## Totals", "", "| family | upgraded | excluded | todo | other |", "|---|---:|---:|---:|---:|"]
    for f in sorted(cnt):
        c = cnt[f]
        L.append("| %s | %d | %d | %d | %d |" % (f, c.get("upgraded", 0), c.get("excluded", 0), c.get("todo", 0),
                                                sum(v for k, v in c.items() if k not in ("upgraded", "excluded", "todo"))))
    L += ["", "## FAIL (%d)" % len(fails), ""] + ["- " + x for x in fails] + ["", "## Defects seen (any status)", ""]
    for a in assets:
        if a["health"]:
            L.append("- `%s` (%s, winner %s): %s" % (a["id"], a["status"], a["winner"], "; ".join(a["health"])))
    L += ["", "## Every asset", "", "| asset | family | status | winner | detail / reason |", "|---|---|---|---|---|"]
    for a in sorted(assets, key=lambda a: (a["family"], a["status"], a["id"])):
        L.append("| `%s` | %s | %s | %s | %s%s |" % (a["id"], a["family"], a["status"], a["winner"], a["detail"].replace("|", "/"),
                                                    (" - " + a["reason"]) if a["reason"] else ""))
    open(os.path.join(OUTDIR, "COVERAGE.md"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
    json.dump(assets, open(os.path.join(OUTDIR, "coverage.json"), "w", encoding="utf-8"), indent=0, sort_keys=True)


def main(argv):
    live = "--live" in argv
    extra = [argv[i + 1] for i, a in enumerate(argv) if a == "--with"]
    cmd = argv[1] if len(argv) > 1 else "check"
    if cmd == "winner":
        paks, _, _ = (live_paks if live else shipped_paks)(extra)
        v = PakVFS(paks)
        for p in argv[2:]:
            if p.startswith("--") or p in extra:
                continue
            print(p, "->", " < ".join(os.path.basename(e[1]) for e in v.all(p)) or "NOT FOUND")
        return 0
    assets, ver, missing, paks = build(live, extra)
    fails = classify(assets)
    if missing:
        fails.append("manifest paks missing locally: %s" % ", ".join(missing))
    if cmd == "report":
        report(assets, fails, ver, missing, paks)
    todo = sum(1 for a in assets if a["status"] == "todo")
    print("fx_coverage: %d assets, %d upgraded, %d excluded, %d todo, %d FAIL" % (
        len(assets), sum(a["status"] == "upgraded" for a in assets), sum(a["status"] == "excluded" for a in assets), todo, len(fails)))
    for f in fails[:40]:
        print("  FAIL " + f)
    if "--strict" in argv and todo:
        print("  FAIL --strict: %d assets still todo" % todo)
        return 1
    return 1 if fails and cmd == "check" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
