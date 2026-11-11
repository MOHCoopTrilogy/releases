"""weapon_tik_values.py - read a weapon's GAME values (fire delay, bullet damage, pellets, clip) from the copy of its
.tik the engine really loads: main < mainta < maintt pk3s by name, the mod tree's files inside the
zzzzzz_co-op_hzm_mod_assets_tey pak's slot, later paks (wpnfix, late, stress ...) win; $include chains followed.
Coop runs g_gametype 2, so 'dm <key>' beats the bare key (sp / realism / dmrealism lines are ignored).

    from weapon_tik_values import values; values("mp40")  ->  {"firedelay": 0.08, "bulletdamage": 40, ...}
"""
import glob
import os
import re
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOD = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")
GOG = os.environ.get("HZM_GOG") or r"G:\GOG\Medal of Honor - Allied Assault War Chest"
TREE_PAK = "zzzzzz_co-op_hzm_mod_assets_tey.pk3"
_IDX = None


def index():
    global _IDX
    if _IDX is not None:
        return _IDX
    _IDX = {}
    for sub in ("main", "mainta", "maintt"):
        paks = {os.path.basename(p): p for p in glob.glob(os.path.join(GOG, sub, "*.pk3"))}
        if sub == "maintt":
            paks.setdefault(TREE_PAK, None)
        for name in sorted(paks, key=str.lower):
            if paks[name]:
                try:
                    z = zipfile.ZipFile(paks[name])
                    for n in z.namelist():
                        l = n.lower()
                        if l.startswith("models/weapons/") and (l.endswith(".tik") or l.endswith(".txt")):
                            _IDX[l] = ("pak", paks[name], n)
                except Exception:
                    pass
            if name == TREE_PAK:
                for f in glob.glob(os.path.join(MOD, "models", "weapons", "*")):
                    l = ("models/weapons/" + os.path.basename(f)).lower()
                    if l.endswith(".tik") or l.endswith(".txt"):
                        _IDX[l] = ("file", f, None)
    return _IDX


def read(path):
    hit = index().get(path.lower())
    if not hit:
        return None
    if hit[0] == "file":
        return open(hit[1], encoding="latin-1").read()
    return zipfile.ZipFile(hit[1]).read(hit[2]).decode("latin-1")


def where(path):
    hit = index().get(path.lower())
    return None if not hit else (hit[1] if hit[0] == "file" else os.path.basename(hit[1]))


def text_with_includes(path, depth=0):
    t = read(path)
    if t is None or depth > 6:
        return ""
    out = []
    for line in t.splitlines():
        m = re.match(r"\s*\$include\s+(\S+)", line)
        if m:
            out.append(text_with_includes(m.group(1), depth + 1))
        else:
            out.append(line)
    return "\n".join(out)


def values(stem):
    t = text_with_includes("models/weapons/%s.tik" % stem)
    if not t:
        return None
    vals, prio = {}, {}
    for line in t.splitlines():
        code = re.sub(r"//.*", "", line).split()
        if not code:
            continue
        mode = None
        if code[0].lower() in ("dm", "sp", "realism", "dmrealism", "mp"):
            mode, code = code[0].lower(), code[1:]
        if not code:
            continue
        key = code[0].lower()
        if mode is None and key.startswith("dm") and key[2:] in ("firedelay", "bulletdamage", "bulletcount", "clipsize"):
            mode, key = "dm", key[2:]          # the old one-word spelling (mg42portable.tik: dmfiredelay)
        if key not in ("firedelay", "bulletdamage", "bulletcount", "clipsize", "name", "firetype", "semiauto"):
            continue
        # once a firetype block switches to secondary the rest is the bash / alt fire: primary only
        p = {"dm": 3, None: 2, "mp": 1}.get(mode, -1)
        if p < 0:
            continue
        if key in vals and prio[key] > p:
            continue
        vals[key] = " ".join(code[1:]).strip('"') if key == "name" else (code[1] if len(code) > 1 else "1")
        prio[key] = p
        if key == "firedelay" and "secondary" in t[:t.find(line)].lower().split("primary")[-1]:
            pass
    out = {"name": vals.get("name")}
    for k in ("firedelay", "bulletdamage", "bulletcount", "clipsize"):
        try:
            out[k] = float(vals[k]) if k in vals else None
        except ValueError:
            out[k] = None
    out["semiauto"] = "semiauto" in vals
    out["tik"] = where("models/weapons/%s.tik" % stem)
    return out


if __name__ == "__main__":
    import sys
    for s in sys.argv[1:]:
        print(s, values(s))
