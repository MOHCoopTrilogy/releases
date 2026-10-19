#!/usr/bin/env python3
"""gen_weapon_stats.py - derive the Armory stat table from the weapon .tik files (nothing hand-typed).

    python -I gen_weapon_stats.py            # writes armory_stats.json + armory_stats.tsv next to this file

Inputs (read only):
  docs/tools/loadout_weapons.tsv           which guns are in the Armory (id, tik, name, caliber line, tab)
  hzm-mohaa-coop-mod/models/weapons/*.tik  the gun definitions (+ $include chains); GAME-MODE values are the "dm" ones
                                           (coop runs g_gametype 2), then the bare line, never sp/realism/dmrealism
  hzm-mohaa-coop-mod/ui/loadout/req<id>.cfg  the unlock text the current menu already prints
  game pk3s (main, mainta, maintt) + the mod tree: the weapon's `reload` .skc, for the reload duration

Per-gun raw values (what the panel prints) and 0-100 scores (what the bars draw):
  dmg     bulletdamage per bullet (x bulletcount when a pellet weapon, bulletspread-wide)  score = dmg/DMG_CAP
  rate    60 / firedelay  rounds per minute                                           score = rpm/RPM_CAP
  acc     bulletspread min/max (world units at bulletrange; lower = tighter)
          spread_eff = 0.5*minspread + 0.5*maxspread                                  score = 100*(1 - spread_eff/ACC_CAP)
  mob     movementspeed (1.0 = full walk speed; absent = 1.0)                         score = (mob-0.5)/(1.1-0.5)
  reload  seconds = frames x frameTime of the .skc named by the tik's `reload` anim   score = 1 - (t-1.0)/(4.5-1.0)
  recoil  |pitch kick| of the first viewkick in the fire anim (extra; the panel's recoil row)

The caps are constants below, the SAME for every gun, so a bar is comparable across classes. Nothing per-gun is typed.
"""
import glob, io, json, os, re, struct, sys, zipfile

ROOT = r"C:\mohaa-coop-dev"
MOD = os.path.join(ROOT, "hzm-mohaa-coop-mod")
GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
TSV = os.path.join(ROOT, "docs", "tools", "loadout_weapons.tsv")
HERE = os.path.dirname(os.path.abspath(__file__))

DMG_CAP, RPM_CAP, ACC_CAP = 100.0, 800.0, 130.0
MOB_LO, MOB_HI = 0.5, 1.1
REL_LO, REL_HI = 1.0, 4.5

# ------------------------------------------------------------------ tik parsing
def read_text(p):
    with io.open(p, encoding="latin-1") as f:
        return f.read()

_TXT = None
def txt_index():
    """lower path -> (pk3, name) for .tik/.txt in the game paks (the mod tree is searched first and wins)"""
    global _TXT
    if _TXT is None:
        _TXT = {}
        for sub in ("main", "mainta", "maintt"):
            for pk in sorted(glob.glob(os.path.join(GOG, sub, "*.pk3"))):
                try:
                    for n in zipfile.ZipFile(pk).namelist():
                        l = n.lower()
                        if l.startswith("models/weapons/") and (l.endswith(".tik") or l.endswith(".txt")):
                            _TXT[l] = (pk, n)      # later paks override earlier ones
                except Exception:
                    pass
    return _TXT

def find_file(rel):
    """-> ('file', path) | ('zip', (pk3, name)) | None"""
    rel = rel.replace("\\", "/").lstrip("/")
    cand = os.path.join(MOD, rel.replace("/", os.sep))
    d0 = os.path.dirname(cand)
    if os.path.isdir(d0):
        for f in os.listdir(d0):
            if f.lower() == os.path.basename(cand).lower():
                return ("file", os.path.join(d0, f))
    hit = txt_index().get(rel.lower())
    return ("zip", hit) if hit else None

def load_tik(rel, depth=0):
    """tik text with $include chains flattened (comments stripped)"""
    p = find_file(rel)
    if not p or depth > 6:
        return ""
    out = []
    raw = read_text(p[1]) if p[0] == "file" else zipfile.ZipFile(p[1][0]).read(p[1][1]).decode("latin-1")
    for ln in raw.splitlines():
        ln = ln.split("//")[0].rstrip()
        m = re.match(r"\s*\$include\s+(\S+)", ln)
        if m:
            out.append(load_tik(m.group(1), depth + 1))
        else:
            out.append(ln)
    return "\n".join(out)

PREFIXES = ("sp", "dm", "realism", "sprealism", "dmrealism")

def server_values(text):
    """{key: value-string} for the dm game mode; dm-prefixed lines beat bare lines, other modes ignored, 'secondary' ignored"""
    head = text.split("\nanimations", 1)[0]
    bare, dm = {}, {}
    for ln in head.splitlines():
        t = ln.split()
        if len(t) < 2:
            continue
        pre = None
        if t[0] in PREFIXES:
            pre, t = t[0], t[1:]
        if len(t) < 2 or t[0] in ("secondary",):
            continue
        key, val = t[0].lower(), " ".join(t[1:])
        if pre is None:
            bare[key] = val
        elif pre == "dm":
            dm[key] = val
    bare.update(dm)
    return bare, head

def num(v, default=None):
    try:
        return float(v.split()[0])
    except Exception:
        return default

# ------------------------------------------------------------------ reload duration from the .skc
_SKC = None
def skc_index():
    global _SKC
    if _SKC is not None:
        return _SKC
    idx = {}   # lower path -> ('zip', pk3, name) | ('file', path)
    for sub in ("main", "mainta", "maintt"):
        for pk in sorted(glob.glob(os.path.join(GOG, sub, "*.pk3"))):
            try:
                for n in zipfile.ZipFile(pk).namelist():
                    if n.lower().endswith(".skc"):
                        idx.setdefault(n.lower(), ("zip", pk, n))
            except Exception:
                pass
    for d, _s, fs in os.walk(os.path.join(MOD, "models", "weapons")):
        for f in fs:
            if f.lower().endswith(".skc"):
                p = os.path.join(d, f)
                idx[os.path.relpath(p, MOD).replace("\\", "/").lower()] = ("file", p)
    _SKC = idx
    return idx

def skc_seconds(path_dir, fname):
    idx = skc_index()
    want = (path_dir.rstrip("/") + "/" + fname).lower()
    hit = idx.get(want)
    if hit is None:
        base = "/" + os.path.basename(fname).lower()
        for k, v in idx.items():
            if k.startswith("models/weapons/") and k.endswith(base):
                hit = v
                break
    if hit is None:
        return None
    if hit[0] == "zip":
        data = zipfile.ZipFile(hit[1]).read(hit[2])
    else:
        data = open(hit[1], "rb").read()
    if data[:4] != b"SKAN":
        return None
    if struct.unpack_from("<i", data, 4)[0] != 13:
        return None          # v14 = "processed" (MSG-coded) anim: not decoded here, see the build note
    ft = struct.unpack_from("<f", data, 16)[0]
    frames = struct.unpack_from("<i", data, 44)[0]
    t = frames * ft
    return round(t, 2) if 0.2 <= t <= 12 else None

def reload_seconds(text):
    pm = re.search(r"^\s*path\s+(\S+)", text, re.M)
    path = pm.group(1) if pm else ""
    anim = text.split("\nanimations", 1)[1] if "\nanimations" in text else ""
    m = re.search(r"^\s*reload\s+(\S+\.skc)", anim, re.M | re.I)
    if not m:
        return None
    return skc_seconds(path, m.group(1))

def first_kick(text):
    anim = text.split("\nanimations", 1)[1] if "\nanimations" in text else ""
    fire = anim.split("\n\tfire", 1)
    seg = fire[1] if len(fire) > 1 else anim
    m = re.search(r"entry\s+viewkick\s+(-?[\d.]+)\s+(-?[\d.]+)", seg)
    return abs(float(m.group(1))) if m else None

# ------------------------------------------------------------------ main
def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))

def spread_pair(v):
    n = [float(x) for x in v.split()[:4]]
    return (n[0] + n[1]) / 2, (n[2] + n[3]) / 2

def derive(tikrel):
    text = load_tik(tikrel)
    kv, head = server_values(text)
    r = {"tik": tikrel}
    wt = kv.get("weapontype", "")
    r["weapontype"] = wt
    dmg = num(kv.get("bulletdamage", ""))
    bc = int(num(kv.get("bulletcount", "1"), 1) or 1)
    spread = kv.get("bulletspread")
    pellets = bc >= 6          # shotgun-style: one trigger pull = many pellets
    r["bulletcount"] = bc
    if dmg is not None:
        total = dmg * (bc if pellets else 1)
        r["dmg"] = round(total, 1)
        r["dmg_score"] = round(clamp(total / DMG_CAP * 100))
    fd = num(kv.get("firedelay", ""))
    if fd:
        r["rpm"] = round(60.0 / fd)
        r["rate_score"] = round(clamp(60.0 / fd / RPM_CAP * 100))
    if spread:
        lo, hi = spread_pair(spread)
        eff = 0.5 * lo + 0.5 * hi
        zm = num(kv.get("zoomspreadmult", ""))
        if zm:                 # scoped weapon: the aimed shot is what the player buys it for
            eff *= zm
            r["scoped"] = True
            r["zoomspreadmult"] = zm
        r["spread"] = [round(lo, 1), round(hi, 1)]
        r["acc_score"] = round(clamp(100 * (1 - eff / ACC_CAP)))
    mob = num(kv.get("movementspeed", ""), 1.0)
    r["mob"] = mob
    r["mob_score"] = round(clamp((mob - MOB_LO) / (MOB_HI - MOB_LO) * 100))
    rl = reload_seconds(text)
    if rl:
        r["reload_s"] = rl
        r["reload_score"] = round(clamp(100 * (1 - (rl - REL_LO) / (REL_HI - REL_LO))))
    k = first_kick(text)
    if k is not None:
        r["kick"] = k
    cs = num(kv.get("clipsize", ""))
    if cs:
        r["clip"] = int(cs)
    rk = kv.get("rank")
    if rk:
        r["rank_tik"] = rk
    return r

def req_text(wid):
    p = os.path.join(MOD, "ui", "loadout", "req%s.cfg" % wid)
    if not os.path.isfile(p):
        return "", ""
    t = read_text(p)
    a = re.search(r'coop_loReq "([^"]*)"', t)
    b = re.search(r'coop_loReq2 "([^"]*)"', t)
    return (a.group(1) if a else ""), (b.group(1) if b else "")

def main():
    rows = []
    for ln in read_text(TSV).splitlines():
        if ln.startswith("#") or ln.startswith("id\t") or not ln.strip():
            continue
        c = ln.split("\t")
        rows.append({"id": c[0], "tik": c[1], "give": c[2], "cls": c[5], "tab": c[6], "name": c[7], "cd": c[8]})
    seen, out = set(), []
    for w in rows:
        if w["id"] in seen:
            continue
        seen.add(w["id"])
        d = derive(w["tik"])
        if w["tab"] == "5":
            d = derive(w["give"])
        w.update(d)
        w["req"], w["req2"] = req_text(w["id"])
        out.append(w)
    json.dump(out, open(os.path.join(HERE, "armory_stats.json"), "w"), indent=1)
    cols = ["id", "name", "tab", "dmg", "rpm", "spread", "mob", "reload_s", "kick", "clip",
            "dmg_score", "rate_score", "acc_score", "mob_score", "reload_score", "req"]
    with io.open(os.path.join(HERE, "armory_stats.tsv"), "w", newline="\n") as f:
        f.write("\t".join(cols) + "\n")
        for w in out:
            f.write("\t".join(str(w.get(c, "")) for c in cols) + "\n")
    miss = [(w["id"], w["name"], [k for k in ("dmg", "rpm", "spread", "reload_s") if k not in w]) for w in out
            if any(k not in w for k in ("dmg", "rpm", "spread", "reload_s")) and w["tab"] != "5"]
    print("guns", len(out), "with missing fields", len(miss))
    for m in miss:
        print("  ", m)

if __name__ == "__main__":
    main()
