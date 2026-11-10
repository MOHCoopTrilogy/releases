"""read a game file the way the BT client resolves it: the mod's shipped paks (gen_wpnfix_pak.carriers, last wins), else the retail
paks (maintt > mainta > main, last-sorting pak wins). Read only."""
import os, sys, glob, zipfile, struct
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools")
sys.path.insert(0, r"C:\mohaa-coop-dev\docs\tools\weapon_hd")
import gen_wpnfix_pak as W

GOG = r"G:\GOG\Medal of Honor - Allied Assault War Chest"
_retail = None


def _index():
    global _retail
    if _retail is None:
        _retail = {}
        for d in ('main', 'mainta', 'maintt'):
            for p in sorted(glob.glob(os.path.join(GOG, d, 'pak*.pk3')), key=lambda s: s.lower()):
                with zipfile.ZipFile(p) as z:
                    for n in z.namelist():
                        _retail[n.lower()] = (p, n)
    return _retail


def read(rel, retail_only=False):
    if not retail_only:
        try:
            c = W.carriers(rel, exclude_self=False)
            if c:
                return c[-1][1]
        except Exception:
            pass
    p, n = _index()[rel.lower()]
    with zipfile.ZipFile(p) as z:
        return z.read(n)


def skd_bones(b):
    nB, oB = struct.unpack_from('<2i', b, 4 + 4 + 64 + 4)
    o = oB; out = []
    for i in range(nB):
        n, p = struct.unpack_from('<32s32s', b, o)
        d = struct.unpack_from('<5i', b, o + 64)[4]
        out.append((n.split(b'\0')[0].decode(), p.split(b'\0')[0].decode())); o += d
    return out


def skc(b):
    nc, o_ch, nf = struct.unpack_from('<3i', b, 36)
    chans = [b[o_ch + 32 * i:o_ch + 32 * i + 32].split(b'\0')[0].decode() for i in range(nc)]
    frames = []
    for f in range(nf):
        ov = struct.unpack_from('<i', b, 48 + 48 * f + 44)[0]
        frames.append([struct.unpack_from('<4f', b, ov + 16 * c) for c in range(nc)])
    return chans, frames
