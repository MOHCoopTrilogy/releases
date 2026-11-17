"""[flguns] read-only virtual file system over the player's MOHAA install, for the disc-gun stage (the base gun's TIK /
SKD / SKC / WAVs). Same priority rules as docs/proposals/ironsights_2026-09-28/tools/vfs.py (main < mainta < maintt, a
LATER pk3 in sort order wins, a later gamedir wins) - but the root is set by the converter at run time (setup()), never
bound at import, and the player's HOME pak folder is mounted after the basepath one (the engine's homepath beats its
basepath; a GOG layout keeps the mod paks only there). Paks the converter writes itself are never read back (a
re-conversion must not read its own previous output). Nothing is ever written."""
import os
import glob
import zipfile

ROOT = None
HOME = None
SKIP = ("zzzz_coop_fl_", "zzzz_fl_hd", "zzzzzzzzzzzzzzzzzzzz_byo_guns_")
GAMEDIRS = ("main", "mainta", "maintt")
_IDX = None


def setup(root, home=None):
    """root = the MOHAA install (fs_basepath); home = the folder the converted paks go to (the homepath maintt)"""
    global ROOT, HOME, _IDX
    ROOT, HOME, _IDX = root, home, None


def paks():
    out = []
    for d in GAMEDIRS:
        ps = glob.glob(os.path.join(ROOT, d, "*.pk3"))
        ps.sort(key=lambda p: os.path.basename(p).lower())
        out += ps
    if HOME and os.path.isdir(HOME) and os.path.normcase(os.path.abspath(HOME)) != \
            os.path.normcase(os.path.abspath(os.path.join(ROOT, "maintt"))):
        ps = glob.glob(os.path.join(HOME, "*.pk3"))
        ps.sort(key=lambda p: os.path.basename(p).lower())
        out += ps
    return [p for p in out if not os.path.basename(p).lower().startswith(SKIP)]


def _norm(p):
    return p.lower().replace(chr(92), "/")


def index():
    """lower-case path -> list of (pak, real name) in priority order (last = winner)."""
    global _IDX
    if _IDX is None:
        idx = {}
        for p in paks():
            try:
                with zipfile.ZipFile(p) as z:
                    for n in z.namelist():
                        if not n.endswith("/"):
                            idx.setdefault(_norm(n), []).append((p, n))
            except (OSError, zipfile.BadZipFile):
                continue
        _IDX = idx
    return _IDX


def winner(path):
    lst = index().get(_norm(path))
    return lst[-1] if lst else None


def read(path):
    w = winner(path)
    if not w:
        return None
    with zipfile.ZipFile(w[0]) as z:
        return z.read(w[1])


def pakname(p):
    return os.path.basename(os.path.dirname(p)) + "/" + os.path.basename(p)
