"""Read-only virtual filesystem over the shipped pak set, in engine priority order (last wins).

main/*.pk3 < mainta/*.pk3 < maintt/*.pk3, each dir sorted by name (ASCII, case-sensitive like the
engine's sort). Only reads; never writes into the install.
"""
import glob, os, zipfile, io
GOG = r"G:/GOG/Medal of Honor - Allied Assault War Chest"
_idx = None
_zips = {}
def paks():
    out = []
    for d in ("main", "mainta", "maintt"):
        ps = [p for p in glob.glob(os.path.join(GOG, d, "*.pk3"))]
        ps.sort(key=lambda p: os.path.basename(p).lower())
        out += ps
    return out
def index():
    """lower vpath -> list of (pakpath, realname) in priority order (last = winner)"""
    global _idx
    if _idx is not None: return _idx
    _idx = {}
    for p in paks():
        try: z = zipfile.ZipFile(p)
        except Exception: continue
        _zips[p] = z
        for n in z.namelist():
            if n.endswith("/"): continue
            _idx.setdefault(n.lower().replace("\\", "/"), []).append((p, n))
    return _idx
def winner(vpath):
    l = index().get(vpath.lower())
    return l[-1] if l else None
def read(vpath, which=-1):
    l = index().get(vpath.lower())
    if not l: return None
    p, n = l[which]
    return _zips[p].read(n)
def resolve_image(stem):
    """engine order: .dds first (compression on), then .jpg, then .tga; across ALL paks the
    probe is per-extension, so a .dds anywhere beats a .jpg anywhere."""
    stem = os.path.splitext(stem.lower())[0]
    for ext in (".dds", ".jpg", ".tga", ".png"):
        w = winner(stem + ext)
        if w: return stem + ext, w
    return None, None
