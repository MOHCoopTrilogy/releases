"""Server-read animation rows: staged vs released (bug-3736). Exit 1 when a row the SERVER reads changed length.

    python srvrows.py <staged root> [--all] [--json out.json]

The server holds weapon state for the length of the weapon tik's rows (`reload` -> WEAPON_RELOADING until the clip
ends, `fire` -> ForceIdle at its end, `rechamber`, `reload_single`, `reload_end`, `raise`, `putaway` ...), runs the
`server { }` commands of every row, and runs the player's torso state machine on the rows of the PLAYER tiki
(models/player/base/anims_*.txt). A staged file may add client-only rows (the cgame picks them by name) but must not
change what the released game has under a name the server plays.

Checked, per staged weapon tik (released text = mod tree, else the live install's paks; read-only):
  FAIL  a row that exists in the released tik has another duration (frames x frame time), or is gone
  FAIL  the row's `server { }` block differs
  FAIL  a NEW row under a name the server plays on its own with a done event (fire_empty, rechamber, reload_single,
        reload_end, clear, charge ...)
  info  a new `idle_empty` (the server plays it for an emptied gun; an idle has no done event: no timing)
  info  new rows the cgame picks (reload_ads_*, reload_empty, fire_ads, *_ads)
and per staged player table (anims_*.txt = server + client; fps_anims_*.txt = client only, listed as info):
  FAIL  a row of the released table has another duration, or is gone
"""
import sys, os, re, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
R = gunskc.R
vfs = R.vfs
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
SERVER_NEW = ('fire', 'fire_empty', 'secondaryfire', 'secondaryfire_empty', 'rechamber', 'reload', 'reload_single', 'reload_end', 'clear',
              'charge', 'secondarycharge', 'raise', 'putaway', 'holster', 'idle', 'idle0', 'idle1', 'idle2')
# Server-side changes that were DECIDED (not side effects): reported as `decl`, never as FAIL. (file tail, row regex, why)
DECLARED = [
    ('m10_revolver.tik', r'reload|reload_end|reload_single',
     'S&W M10 loads round by round (revolver list A-C, 2026-10-12; listen-server runs tn2 / pa5 / pa12) - a per-round reload cannot be client-only'),
    ('webley_revolver.tik', r'reload|reload_end|reload_single',
     'Webley: open / close 0.53 -> 0.8 s, one round 0.53 -> 0.8 s (coordinator 2026-10-12, list item C "give them time and weight"; webslow.py; runs tl9 tn1 ts1)'),
    ('colt45_colt1911w.tik', r'reload|reload_end|reload_single',
     'Webley Mk VI: its own gun clips retimed onto the Webley decision (it wears the Webley hands and reload states; mk6.py, 2026-10-13)'),
    ('nagant_revolver.tik', r'reload_single', 'Nagant: one round 0.53 -> 0.9 s (same decision; runs tn3 tu1)'),
    ('anims_pistol.txt', r'nagantrev_reload_loop|webley_reload_end|webley_reload_loop', 'the torso rows of the two revolver decisions above'),
    ('anims_shared.txt', r'coop_reload_webley_start', 'the torso row of the Webley decision above'),
    ('anims_shared.txt', r'coop_prone_reload_pistol',
     'prone pistol reload as long as the standing one, 1.50 -> 2.43 s (coordinator 2026-10-12; patch_prone_reload.py; run tl8)'),
]
# staged text files that are SNAPSHOTS of a mod-tree file: (staged path, mod path, mod commit the snapshot was taken from).
# The mod file may have moved on since; shipping = a 3-way merge, and the merged text is what gets checked.
BASES = {
    'models/player/base/anims_shared.txt': ('models/player/base/anims_shared.txt', '6cf61e58'),
    'coop_mod/player_Torso.st': ('coop_mod/player_torso.st', '12e9faf6'),
}


def declared(rel, nm):
    for tail, rx, why in DECLARED:
        fam = tail[:-4] + '_' if tail.endswith('.tik') else None          # a declared gun's finish tiks (<base>_<finish>.tik) too
        if (rel.lower().endswith(tail) or (fam and os.path.basename(rel).lower().startswith(fam))) and re.fullmatch(rx, nm):
            return why
    return None


def merged(root, rel, res, emit=None):
    """the staged file 3-way merged with the mod tree's current file (base = the commit it was snapshot from)"""
    import subprocess, tempfile
    st = staged(root, rel)
    if rel not in BASES:
        return st
    modp, rev = BASES[rel]
    cur = os.path.join(MOD, rel.replace('/', os.sep))
    base = subprocess.run(['git', '-C', MOD, 'show', '%s:%s' % (rev, modp)], capture_output=True).stdout
    theirs = open(cur, 'rb').read()
    if base == theirs:
        return st
    d = tempfile.mkdtemp()
    fs = []
    for nm, b in (('ours', st), ('base', base), ('theirs', theirs)):
        f = os.path.join(d, nm); open(f, 'wb').write(b); fs.append(f)
    r = subprocess.run(['git', 'merge-file', '-p'] + fs, capture_output=True)
    if r.returncode != 0:
        res['fail'].append('%s: the mod file changed since %s and the 3-way merge has %d conflict(s)' % (rel, rev, r.returncode))
        return st
    res['info'].append('%s: snapshot of mod %s, the mod file has changed since - 3-way merge clean (%+d bytes); the MERGED text is checked and is what ships'
                       % (rel, rev, len(r.stdout) - len(st)))
    if emit:
        f = os.path.join(emit, rel.replace('/', os.sep)); os.makedirs(os.path.dirname(f), exist_ok=True); open(f, 'wb').write(r.stdout)
    return r.stdout


CLIENT_OK = re.compile(r'^(reload_ads_loaded|reload_ads_empty|reload_empty|fire_ads|reload_end_ads|reload_single_ads|rechamber_ads|reload_ads_\w+)$')


_rel = {}


def released(p):
    if p not in _rel:
        _rel[p] = _released(p)
    return _rel[p]


def _released(p):
    f = os.path.join(MOD, p.replace('/', os.sep))
    if os.path.isfile(f):
        return open(f, 'rb').read(), 'mod'
    b = vfs.read(p)
    return b, 'pak'


def staged(root, p):
    f = os.path.join(root, p.replace('/', os.sep))
    return open(f, 'rb').read() if os.path.isfile(f) else None


_dur = {}


def dur(raw):
    """(frames, seconds) of a clip"""
    k = hash(raw)
    if k not in _dur:
        import struct                                         # header only (v13: fixed header; v14: packed message)
        assert raw[0:4] == b'SKAN', raw[0:4]
        ver = struct.unpack_from('<i', raw, 4)[0]
        if ver == 14:
            sys.path.insert(0, r'C:\mohaa-coop-dev\docs\proposalsds_bolt_2026-10-04	ools')
            import skc14
            m = skc14.Msg(raw[8:]); m.short(); m.long(); ft = m.float(); [m.float() for _ in range(4)]; nf = m.long()
        else:
            ft = struct.unpack_from('<f', raw, 16)[0]; nf = struct.unpack_from('<i', raw, 44)[0]
        assert 0 < nf < 100000 and 0.0 < ft < 10.0, (ver, nf, ft)
        _dur[k] = (int(nf), round(nf * float(ft), 4))
    return _dur[k]


def strip(s):
    return '\n'.join(l.split('//')[0].rstrip() for l in s.replace('\r\n', '\n').split('\n'))


def tik_rows(tx):
    """{row: (clip, server block text)} and the tik's path"""
    s = strip(tx)
    pm = re.search(r'(?im)^\s*path\s+(\S+)', s)
    path = pm.group(1) if pm else ''
    m = re.search(r'(?im)^animations\s*\n?\{', s)
    rows = {}
    if not m:
        return path, rows
    i = m.end(); d = 1; body_start = i
    lines = s[i:].split('\n')
    cur = None
    for ln in lines:
        t = ln.strip()
        if d == 1:
            mm = re.match(r'^(\S+)\s+(\S+\.skc)\b', t, re.I)
            if mm:
                cur = mm.group(1).lower()
                rows[cur] = [mm.group(2), '']
        if cur and d >= 2:
            rows[cur][1] += t + '\n'
        d += t.count('{') - t.count('}')
        if cur and d >= 2 and rows[cur][1] == '':
            rows[cur][1] = ''
        if d <= 0:
            break
    out = {}
    for k, (clip, blk) in rows.items():
        sm = re.search(r'(?is)\bserver\s*\{(.*?)\}', blk)
        out[k] = (clip, re.sub(r'\s+', ' ', sm.group(1)).strip() if sm else '')
    return path, out


def clip_bytes(root, path, clip, side):
    p = '%s/%s' % (path.strip('/'), clip)
    if side == 'staged':
        b = staged(root, p)
        if b is not None:
            return b
    return released(p)[0]


class _Res(dict):
    """res['fail'].append(line) lands in res['decl'] when the line names a declared (file, row)"""


class _Fail(list):
    def __init__(self, res):
        self.res = res

    def append(self, line):
        m = re.match(r'(\S+): (?:NEW )?row `([^`]+)`', line)
        why = declared(m.group(1), m.group(2)) if m else None
        if why:
            self.res['decl'].append((line, why))
        else:
            list.append(self, line)


def check_tik(root, rel, res, verbose):
    st = staged(root, rel).decode('latin-1')
    rb, src = released(rel)
    if rb is None:
        res['info'].append('%s: NEW tik (no released file)' % rel)
        return
    sp, srows = tik_rows(st)
    rp, rrows = tik_rows(rb.decode('latin-1'))
    for nm, (clip, srv) in sorted(rrows.items()):
        if nm not in srows:
            res['fail'].append('%s: row `%s` is GONE' % (rel, nm))
            continue
        if clip.lower() == srows[nm][0].lower() and rp.lower().strip('/') == sp.lower().strip('/') and staged(root, '%s/%s' % (sp.strip('/'), clip)) is None:
            if srv != srows[nm][1]:
                res['fail'].append('%s: row `%s`: server block differs: [%s] -> [%s]' % (rel, nm, srv[:80], srows[nm][1][:80]))
            continue                                             # same clip name, not staged: the released file itself
        try:
            d0 = dur(clip_bytes(root, rp, clip, 'released'))
            d1 = dur(clip_bytes(root, sp, srows[nm][0], 'staged'))
        except Exception as e:                                    # a clip that cannot be read
            res['fail'].append('%s: row `%s`: clip unreadable (%s)' % (rel, nm, e))
            continue
        if abs(d0[1] - d1[1]) > 0.001:
            res['fail'].append('%s: row `%s` %s %d fr %.3f s -> %s %d fr %.3f s' % (rel, nm, clip, d0[0], d0[1], srows[nm][0], d1[0], d1[1]))
        elif verbose:
            res['same'].append('%s: `%s` %.3f s' % (rel, nm, d0[1]))
        if srv != srows[nm][1]:
            res['fail'].append('%s: row `%s`: server block differs: [%s] -> [%s]' % (rel, nm, srv[:80], srows[nm][1][:80]))
    for nm in sorted(set(srows) - set(rrows)):
        if nm == 'idle_empty':
            res['info'].append('%s: new idle_empty (%s) - an idle, no done event' % (rel, srows[nm][0]))
        elif nm in SERVER_NEW:
            res['fail'].append('%s: NEW row `%s` under a name the server plays' % (rel, nm))
        elif CLIENT_OK.match(nm):
            res['client'][nm] = res['client'].get(nm, 0) + 1
        else:
            res['info'].append('%s: new row `%s` (%s)' % (rel, nm, srows[nm][0]))
    res['tiks'] += 1


def table_rows(tx):
    rows = {}
    for ln in strip(tx).split('\n'):
        m = re.match(r'^\s*(\S+)\s+(\S+\.skc)\b', ln, re.I)
        if m:
            rows[m.group(1).lower()] = m.group(2)
    return rows


def check_table(root, rel, res, client, emit=None):
    st = merged(root, rel, res, emit).decode('latin-1')
    rb, src = released(rel)
    if rb is None:
        res['info'].append('%s: NEW table' % rel)
        return
    srows, rrows = table_rows(st), table_rows(rb.decode('latin-1'))
    base = 'models/human/animation'
    n = 0
    for nm, clip in sorted(rrows.items()):
        key = 'info' if client else 'fail'
        if nm not in srows:
            res[key].append('%s: row `%s` is GONE' % (rel, nm))
            continue
        if clip == srows[nm]:
            sb = staged(root, '%s/%s' % (base, clip))
            if sb is None:
                continue                                         # same name, clip not staged: untouched
        try:
            d0 = dur(released('%s/%s' % (base, clip))[0])
            d1 = dur(clip_bytes(root, base, srows[nm], 'staged'))
        except Exception as e:
            res['info'].append('%s: row `%s`: clip unreadable (%s)' % (rel, nm, e))
            continue
        if abs(d0[1] - d1[1]) > 0.001:
            n += 1
            res[key].append('%s: row `%s` %s %d fr %.3f s -> %s %d fr %.3f s%s' % (rel, nm, clip, d0[0], d0[1], srows[nm], d1[0], d1[1], ' (client table)' if client else ''))
    res['info'].append('%s: %d released rows, %d staged (+%d new), %d changed length%s' % (rel, len(rrows), len(srows), len(set(srows) - set(rrows)), n,
                                                                                      ' - CLIENT table' if client else ''))


def main():
    root = os.path.abspath(sys.argv[1])
    verbose = '--all' in sys.argv
    res = dict(info=[], same=[], client={}, tiks=0, decl=[])
    res['fail'] = _Fail(res)
    emit = sys.argv[sys.argv.index('--emit-merged') + 1] if '--emit-merged' in sys.argv else None
    wd = os.path.join(root, 'models', 'weapons')
    for fn in sorted(os.listdir(wd)):
        if fn.lower().endswith('.tik'):
            check_tik(root, 'models/weapons/' + fn, res, verbose)
    pd = os.path.join(root, 'models', 'player', 'base')
    if os.path.isdir(pd):
        for fn in sorted(os.listdir(pd)):
            if fn.lower().endswith('.txt'):
                check_table(root, 'models/player/base/' + fn, res, fn.lower().startswith('fps_'), emit)
    stf = os.path.join(root, 'coop_mod', 'player_Torso.st')
    if os.path.isfile(stf):
        rb, _ = released('coop_mod/player_Torso.st')
        a = strip(merged(root, 'coop_mod/player_Torso.st', res, emit).decode('latin-1')).split('\n')
        b = strip(rb.decode('latin-1')).split('\n') if rb else []
        import difflib
        nd = sum(1 for l in difflib.unified_diff(b, a, lineterm='', n=0) if l[:1] in '+-' and l[:3] not in ('+++', '---'))
        res['info'].append('coop_mod/player_Torso.st: %d changed lines against the released file (the server runs it: its own test, not a row length)' % nd)
    if verbose:
        for l in res['same']:
            print('same  ' + l)
    for l in res['info']:
        print('info  ' + l)
    print('info  client-picked new rows: ' + ', '.join('%s x%d' % kv for kv in sorted(res['client'].items())))
    seen = set()
    for l, why in res['decl']:
        print('decl  ' + l)
        if why not in seen:
            seen.add(why); print('      = ' + why)
    for l in res['fail']:
        print('FAIL  ' + l)
    print('%d weapon tiks checked, %d declared server-side changes, %d FAIL' % (res['tiks'], len(res['decl']), len(res['fail'])))
    if '--json' in sys.argv:
        json.dump(dict(res, fail=list(res['fail'])), open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)
    sys.exit(1 if res['fail'] else 0)


if __name__ == '__main__':
    main()
