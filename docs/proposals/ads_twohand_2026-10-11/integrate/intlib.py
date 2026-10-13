"""intlib.py - shared helpers of the ADS integration (integrate_ads.py, rowlen_check.py).

A read-only model of what the engine loads (qcommon/files.cpp FS_AddGameDirectory2: paks of one directory sorted by
FS_PathCmp, the last one wins; main < mainta < maintt), with two stand-ins:
  * the mod tree `hzm-mohaa-coop-mod` stands for the three `zzzzzz_co-op_hzm_mod_*` paks (it is their source),
  * a FIXES DIRECTORY stands for `zzzzzzzzzz_coop_fixes.pk3` - either the working copy `docs/tools/assets/fixes`
    (the integrated state) or the same folder at a git revision (the released state).
Nothing here writes outside the scratch cache.
"""
import hashlib, json, os, re, struct, subprocess, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)                                   # docs/proposals/ads_twohand_2026-10-11
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(PROP)))  # C:/mohaa-coop-dev
MOD = os.path.join(ROOT, 'hzm-mohaa-coop-mod')
FIX = os.path.join(ROOT, 'docs', 'tools', 'assets', 'fixes')
FIXBASE = os.path.join(ROOT, 'docs', 'tools', 'assets', 'fixes_base')
MAN = os.path.join(FIX, 'fixes_manifest.json')
GOG = r'G:/GOG/Medal of Honor - Allied Assault War Chest'
GAMEDIRS = ('main', 'mainta', 'maintt')
FIXPAK = 'zzzzzzzzzz_coop_fixes.pk3'
MODPAK = 'zzzzzz_co-op_hzm_mod_assets_tex.pk3'
EPOCH_TICKS = 621355968000000000
RELEASED_REV = '806c4ae'          # docs repo commit whose docs/tools/assets/fixes is the RELEASED fixes pak (v1.10.21)
CACHE = os.path.join(os.environ.get('INTEG_CACHE', os.path.join(os.environ.get('TEMP', '.'), 'integ_ads_cache')))
MOD_ASSET_DIRS = ('models', 'textures', 'gfx', 'env', 'scripts', 'sound', 'coop_mod', 'global', 'ui', 'maps', 'anim')


def md5(b):
    return hashlib.md5(b).hexdigest()


def pathcmp_key(s):
    return [ord('/') if c in '\\:' else ord(c.lower()) for c in s]


def _pak_index():
    os.makedirs(CACHE, exist_ok=True)
    cf = os.path.join(CACHE, 'pakindex.json')
    stamp = {}
    for d in GAMEDIRS:
        for f in sorted(os.listdir(os.path.join(GOG, d))):
            if f.lower().endswith('.pk3'):
                st = os.stat(os.path.join(GOG, d, f))
                stamp[d + '/' + f] = [st.st_size, st.st_mtime_ns]
    if os.path.isfile(cf):
        c = json.load(open(cf))
        if c.get('stamp') == stamp:
            return c['idx']
    idx = {}
    for k in stamp:
        with zipfile.ZipFile(os.path.join(GOG, k)) as z:
            idx[k] = [n for n in z.namelist() if not n.endswith('/')]
    json.dump({'stamp': stamp, 'idx': idx}, open(cf, 'w'))
    return idx


def _mod_index():
    out = {}
    for top in MOD_ASSET_DIRS:
        for dp, _dn, fn in os.walk(os.path.join(MOD, top)):
            for f in fn:
                rel = os.path.relpath(os.path.join(dp, f), MOD).replace(os.sep, '/')
                out[rel.lower()] = rel
    return out


class Vfs:
    """fixes = a directory path, or ('git', rev) for docs/tools/assets/fixes at that docs-repo revision, or None."""

    def __init__(self, fixes=FIX):
        self.idx = _pak_index()
        self.mod = _mod_index()
        self.fixes = fixes
        self.fixnames = {}
        if isinstance(fixes, tuple):
            out = subprocess.run(['git', '-C', ROOT, 'ls-tree', '-r', '--name-only', fixes[1], 'docs/tools/assets/fixes/'],
                                 capture_output=True, text=True, check=True).stdout
            for ln in out.splitlines():
                rel = ln[len('docs/tools/assets/fixes/'):]
                if rel != 'fixes_manifest.json':
                    self.fixnames[rel.lower()] = rel
        elif fixes:
            for dp, _dn, fn in os.walk(fixes):
                for f in fn:
                    if f != 'fixes_manifest.json':
                        rel = os.path.relpath(os.path.join(dp, f), fixes).replace(os.sep, '/')
                        self.fixnames[rel.lower()] = rel
        # layers, lowest first: (dir rank, pak name)
        self.layers = []
        for rank, d in enumerate(GAMEDIRS):
            names = sorted({k.split('/', 1)[1] for k in self.idx if k.startswith(d + '/')}
                           | ({MODPAK, FIXPAK} if d == 'maintt' else set()), key=pathcmp_key)
            for n in names:
                if d == 'maintt' and n.lower().startswith('zzzzzz_co-op_hzm_mod_') and n != MODPAK:
                    continue
                self.layers.append((d, n))
        self._low = {}
        for k, names in self.idx.items():
            self._low[k] = {n.lower(): n for n in names}

    def holders(self, rel):
        """every layer that carries rel, lowest first: [(dir, pak)]"""
        r = rel.lower().replace('\\', '/')
        out = []
        for d, n in self.layers:
            if d == 'maintt' and n == MODPAK:
                if r in self.mod:
                    out.append((d, n))
            elif d == 'maintt' and n == FIXPAK:
                if r in self.fixnames:
                    out.append((d, n))
            elif r in self._low.get(d + '/' + n, {}):
                out.append((d, n))
        return out

    def winner(self, rel):
        h = self.holders(rel)
        return h[-1] if h else None

    def read_from(self, layer, rel):
        d, n = layer
        r = rel.lower().replace('\\', '/')
        if d == 'maintt' and n == MODPAK:
            return open(os.path.join(MOD, *self.mod[r].split('/')), 'rb').read()
        if d == 'maintt' and n == FIXPAK:
            if isinstance(self.fixes, tuple):
                return subprocess.run(['git', '-C', ROOT, 'show', '%s:docs/tools/assets/fixes/%s' % (self.fixes[1], self.fixnames[r])],
                                      capture_output=True, check=True).stdout
            return open(os.path.join(self.fixes, *self.fixnames[r].split('/')), 'rb').read()
        with zipfile.ZipFile(os.path.join(GOG, d, n)) as z:
            return z.read(self._low[d + '/' + n][r])

    def read(self, rel):
        w = self.winner(rel)
        return self.read_from(w, rel) if w else None

    def below_fixes(self, rel):
        """the winner when the fixes pak is ignored (= the base an override replaces), and any layer ABOVE the fixes pak"""
        h = self.holders(rel)
        fi = self.layers.index(('maintt', FIXPAK))
        below = [x for x in h if self.layers.index(x) < fi]
        above = [x for x in h if self.layers.index(x) > fi]
        return (below[-1] if below else None), above


def skc_info(b):
    """(frames, frame time s) of a .skc"""
    if b is None or len(b) < 48 or b[:4] != b'SKAN':
        return None
    ver = struct.unpack_from('<i', b, 4)[0]
    ft = struct.unpack_from('<f', b, 16)[0]
    nf = struct.unpack_from('<i', b, 44)[0]
    assert ver in (13, 14), ver
    if not (0 < nf < 100000 and 0.0 < ft <= 1.0):
        return None          # a packed v14 clip of the Breakthrough paks: header not readable here
    return nf, ft


def tik_rows(text):
    """animation rows of a tik / anims txt: [(row, clip token, path in force)] - `path` lines set the folder"""
    rows, path, depth, in_anim = [], '', 0, False
    for raw in text.splitlines():
        ln = raw.split('//')[0].strip()
        if not ln:
            continue
        tok = ln.split()
        if tok[0].lower() == 'path' and len(tok) > 1:
            path = tok[1].strip('"').replace('\\', '/').rstrip('/')
        if len(tok) >= 2 and tok[1].lower().endswith(('.skc', '.ska')) and tok[0] not in ('{', '}'):
            rows.append((tok[0], tok[1].replace('\\', '/'), path))
    return rows


def tik_name(text):
    m = re.search(r'(?mi)^\s*name\s+"([^"]+)"', text)
    return m.group(1) if m else None


def clip_path(row):
    _n, clip, path = row
    return clip if clip.lower().startswith('models/') else (path + '/' + clip if path else clip)


def ticks_of(path):
    return os.stat(path).st_mtime_ns // 100 + EPOCH_TICKS
