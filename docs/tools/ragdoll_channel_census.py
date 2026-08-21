"""Ragdoll P0 census (ragdoll_plan.md v3 §6/P0): per-HUMAN-TIK bone-channel union.

The ragdoll override table stores one matrix per CHANNEL of a corpse's tiki (the renderer
bone cache is absolute per-channel - a partial override tears the mesh, vet1). This measures
the real per-tik union: every `skelmodel` a human tik (plus its $include chain) loads, each
skd's bone list unioned. The MAX across the roster sizes the per-slot matrix array; the
capture-time assert uses the same number. SKMD layout borrowed from count_skel_channels.py
(bug-1803 tooling): numBones/ofsBones at +76, bone records name[32] + 52 bytes.

Vet3 implementer note honored: this measures the per-TIK union (what TIKI_GetNumChannels
sees), NOT the per-SKD TIKI_MAX_BONES cap.
"""
import zipfile, glob, os, re, struct, sys

ROOTS = [
    "G:/GOG/Medal of Honor - Allied Assault War Chest/main",
    "G:/GOG/Medal of Honor - Allied Assault War Chest/mainta",
    "G:/GOG/Medal of Honor - Allied Assault War Chest/maintt",
]
MOD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "hzm-mohaa-coop-mod")


def cstr(b):
    i = b.find(b"\0")
    return (b[:i] if i >= 0 else b).decode("latin-1", "replace")


def build_index():
    """path(lower) -> (pk3path, member). Later pk3s override earlier (mount order)."""
    idx = {}
    pk3s = []
    for root in ROOTS:
        pk3s += sorted(glob.glob(os.path.join(root, "*.pk3")), key=str.lower)
    for pk in pk3s:
        try:
            with zipfile.ZipFile(pk) as z:
                for n in z.namelist():
                    idx[n.lower().replace("\\", "/")] = (pk, n)
        except Exception:
            pass
    # loose mod tree wins over everything (it is what gets packed)
    for dirpath, _, files in os.walk(MOD):
        if ".git" in dirpath:
            continue
        for f in files:
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, MOD).replace("\\", "/").lower()
            idx[rel] = (None, full)
    return idx


_zipcache = {}

def read_file(idx, path):
    ent = idx.get(path.lower().replace("\\", "/"))
    if not ent:
        return None
    pk, member = ent
    if pk is None:
        return open(member, "rb").read()
    z = _zipcache.get(pk)
    if z is None:
        z = _zipcache[pk] = zipfile.ZipFile(pk)
    return z.read(member)


def skd_bones(data):
    out = set()
    if not data or len(data) < 100 or data[:4] != b"SKMD":
        return out
    numBones, ofsBones = struct.unpack_from("<ii", data, 76)
    if not (0 <= numBones < 100000) or not (0 < ofsBones <= len(data)):
        return out
    o = ofsBones
    for _ in range(numBones):
        if o + 84 > len(data):
            break
        nm = cstr(data[o:o + 32]).strip()
        if nm:
            out.add(nm)
        o += 84
    return out


def tik_skelmodels(idx, tikpath, seen):
    """skelmodel paths from a tik + its $include chain, path-resolved like the engine."""
    key = tikpath.lower()
    if key in seen:
        return []
    seen.add(key)
    raw = read_file(idx, tikpath)
    if raw is None:
        return []
    txt = raw.decode("latin-1", "replace")
    path_prefix = ""
    out = []
    for line in txt.splitlines():
        ls = line.strip()
        low = ls.lower()
        if low.startswith("path "):
            path_prefix = ls.split(None, 1)[1].strip().rstrip("/") + "/"
        elif low.startswith("skelmodel "):
            sm = ls.split(None, 1)[1].strip()
            out.append(sm if "/" in sm else path_prefix + sm)
        elif low.startswith("$include "):
            out += tik_skelmodels(idx, ls.split(None, 1)[1].strip(), seen)
    return out


def main():
    idx = build_index()
    human_tiks = sorted({p for p in idx if p.startswith("models/human/") and p.endswith(".tik")
                         and "/animation/" not in p and "/heads/" not in p})
    rows = []
    for tik in human_tiks:
        bones = set()
        for sm in tik_skelmodels(idx, tik, set()):
            bones |= skd_bones(read_file(idx, sm))
        if bones:
            rows.append((len(bones), tik))
    rows.sort(reverse=True)
    print("ragdoll channel census: %d human tiks with resolvable skds" % len(rows))
    for n, t in rows[:12]:
        print("  %4d  %s" % (n, t))
    if rows:
        mx = rows[0][0]
        print("MAX per-tik bone union = %d  ->  slot matrix array size (with margin): %d" % (mx, mx + 8))
    else:
        print("ERROR: no rows - index or parsing failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
