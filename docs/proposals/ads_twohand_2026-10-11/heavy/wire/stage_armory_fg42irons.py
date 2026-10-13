"""FG 42 Irons as ITS OWN ARMORY ENTRY, the mod's way - through the generators, nothing generated is written by hand
(the rifle lane's recipe for the G 43 Irons, ..\\..\\rifles\\wire\\stage_armory_gen.py, whose scratch-repo machinery is
used here as a library; the anchors are the scoped FG 42's, roster id 39).

What is AUTHORED for the new gun (edited in a scratch copy of the repo, never in the real tree):
    docs/tools/loadout_weapons.tsv        one row: id 79, tile "FG 42 (IRON SIGHTS)", heavy tab, bars
    coop_mod/loadoutroster.scr            roster_get `case "79"` (the scoped FG 42's case with the new tik / name)
    coop_mod/loadoutskins.scr             finishes fid 1-7 of the new base tik (+ coop_skinN)
    coop_mod/xp.scr                       RANK 18 grants it: coop_xp_rankUnlockCnt[18] 0 -> 1, coop_xp_rankUnlock[18][0]
    coop_mod/itemhandler.scr              the two tik lists the scoped FG 42 is in
    coop_mod/recoil_table.txt             the 8 rows of recoil_table_fg42irons.txt
    ui/coop_loadout.urc                   tile79 + its lock label on the heavy tab, at the scoped FG 42's row (the list
                                          is in unlock order: rank 18 sits directly above rank 19); that row and every
                                          row below it move 19 px down
    ui/loadout/lktab0-5.cfg               the lock cvar of the new tile
    ubermode/get_player_weaponclass.scr, coop_mod/buildmode_catalog.scr, global/giveall.scr   the lists the scoped gun is in
What the GENERATORS then write (run as copies in the scratch repo; two of them patched):
    gen_loadout.py build      ui/loadout/p79 t79 w79_s1 w79_s2 req79 finp79_1..7 .cfg + loadoutroster.scr::roster_ids
    gen_skinbase.py           coop_mod/loadoutskins_base.scr       (finished tik -> its base)
    armory_unlocks.py --emit  coop_mod/unlockreq_gen.scr           ("Reach rank 18")
    gen_loadout.py check
  generator patches: armory_unlocks.py honours HZM_MOD (the rifle lane's patch, identical); gen_service_record.py
  REWARD_NAMES gets "FG 42 (Iron Sights)" (patched, NOT run - the rifle lane's finding: no Service Record row changes).

FINISHES: fid 1-7 are GLOBAL unlocks, not per gun - challenges.scr `fin_gold` (250 kills), `fin_chrome` (a mission
with no deaths), `fin_blued` (150 headshots), `fin_bloody` (150 melee kills), `fin_woodland` / `fin_winter` /
`fin_desert` (150 kills in the US campaign / on snow maps / in North Africa) put "finish_<key>" into the player's
unlock store, and loadoutpick.scr::loadout_finish asks only for that string and for a coop_skinGive row of the slot's
gun. So the irons' finishes unlock exactly as the scoped FG 42's do the moment its seven coop_skinGive rows exist.

    python stage_armory_fg42irons.py      -> gen/generators.patch   (apply to docs/tools)
                                             gen/armory_fg42irons.patch   every changed mod-tree file
                                             gen/new/               every new mod-tree file
                                             ../armory_ov/          the same game files for the private test install
                                             gen/report.txt
The patches are against the mod tree AS IT IS (without the G 43 Irons, id 78): both guns edit the roster count, the
lktab files and the tile list - apply one, then RE-RUN the other's script (every anchor is a name, each is asserted).
"""
import os, re, sys, shutil, difflib, subprocess, zipfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
RW = os.path.normpath(os.path.join(HERE, '..', '..', 'rifles', 'wire'))
sys.path.insert(0, RW)
import stage_armory_g43irons as OLD        # generic helpers only: one(), nl_of(), res_block()
import stage_armory_gen as GEN             # the scratch repo: seed(), rd(), wr(), tree(), scan()
one, nl_of, res_block, rd, wr = OLD.one, OLD.nl_of, OLD.res_block, GEN.rd, GEN.wr
REPO, MOD, TOOLS, RELEASED = GEN.REPO, GEN.MOD, GEN.TOOLS, GEN.RELEASED
ASSETS = os.path.normpath(os.path.join(HERE, '..', 'assets'))
OUT = os.path.join(HERE, 'gen')
OV = os.path.normpath(os.path.join(HERE, '..', 'armory_ov'))
SCRATCH = os.path.join(os.path.dirname(GEN.SCRATCH), 'adsheavy', 'armgen')

ID = '79'
HOSTID = '39'                               # the scoped FG 42
HOST_TIK = 'models/weapons/fg42.tik'
TIK = 'models/weapons/coop_fg42_irons.tik'
STEM = 'coop_fg42_irons'
NAME = 'FG 42 (IRON SIGHTS)'
DESC = '7.92MM / AUTOMATIC / IRON SIGHTS'   # 32 characters as the G 43 Irons' line; '... AUTOMATIC RIFLE / IRON SIGHTS' was cut on both sides (run hj34)
TAB = 3                                     # heavy
RANK = 18
FIN = {1: 'gold', 2: 'chrome', 3: 'blued', 4: 'bloody', 5: 'camo_woodland', 6: 'camo_winter', 7: 'camo_desert'}
ROW = 19
NOTE = '[fg42 irons 2026-10-13]'


def roster_case(t):
    assert 'case "%s":' % ID not in t
    m = one(r'^([ \t]*)case "%s":.*?^[ \t]*break[ \t]*\r?\n' % HOSTID, t, re.M | re.S)
    new = m.group(0).replace('case "%s":' % HOSTID, 'case "%s":\t//%s the iron-sight FG 42, its own entry' % (ID, NOTE)).replace(HOST_TIK, TIK).replace('"FG 42"', '"%s"' % NAME)
    assert new.count(TIK) == 1 and NAME in new
    return t[:m.end()] + new + t[m.end():]


def skins(t):
    nl = nl_of(t)
    m = one(r'^([ \t]*)level\.coop_skinGive\["models/weapons/fg42\.tik"\]\[7\] = [^\n]*\n', t)
    rows = ''.join('%slevel.coop_skinGive["%s"][%d] = "models/weapons/%s_%s.tik"%s' % (m.group(1), TIK, k, STEM, FIN[k], nl) for k in sorted(FIN))
    t = t[:m.end()] + rows + t[m.end():]
    n = int(one(r'level\.coop_skinN = (\d+)', t).group(1))
    return re.sub(r'level\.coop_skinN = \d+', 'level.coop_skinN = %d' % (n + len(FIN)), t)


def xp(t):
    nl = nl_of(t)
    m = one(r'^([ \t]*)level\.coop_xp_rankUnlockCnt\[%d\] = (\d+)[ \t]*\r?\n' % RANK, t)
    c = int(m.group(2))
    assert c == 0 and not re.search(r'level\.coop_xp_rankUnlock\[%d\]\[0\] = ' % RANK, t), 'rank %d already has a base grant: extend this' % RANK
    row = ('%slevel.coop_xp_rankUnlockCnt[%d] = 1%s' % (m.group(1), RANK, nl)
           + '%slevel.coop_xp_rankUnlock[%d][0] = "%s"\t//%s the rank before the scoped FG 42 (19)%s' % (m.group(1), RANK, TIK, NOTE, nl))
    return t[:m.start()] + row + t[m.end():]


def itemhandler(t):
    nl = nl_of(t)
    ms = list(re.finditer(r'^([ \t]*)case "models/weapons/fg42\.tik":[ \t]*\r?\n', t, re.M))
    assert len(ms) == 2, len(ms)
    for m in reversed(ms):
        t = t[:m.end()] + '%scase "%s":%s' % (m.group(1), TIK, nl) + t[m.end():]
    return t


def recoil(t):
    nl = nl_of(t)
    rows = [l.strip() for l in open(os.path.join(HERE, 'recoil_table_fg42irons.txt'), encoding='latin-1').read().splitlines() if l.strip() and not l.strip().startswith(('//', '#'))]
    assert len(rows) == 8 and all(r.startswith(STEM) for r in rows), rows[:2]
    assert not re.search(r'(?m)^%s\b' % STEM, t)
    return t.rstrip('\r\n') + nl + '// %s iron-sight FG 42: the FG 42\'s rows under its own tik names' % NOTE + nl + nl.join(rows) + nl


def urc(t):
    nl = nl_of(t)
    assert 'name "tile%s"' % ID not in t
    a, b = res_block(t, 'tile' + HOSTID)
    y_new = int(one(r'rect \d+ (\d+) \d+ \d+', t[a:b]).group(1))
    tab = one(r'enabledcvar "([^"]+)"', t[a:b]).group(1)
    moved = []
    for nm in re.findall(r'name "tile(\d+)"', t):
        a, b = res_block(t, 'tile' + nm)
        blk = t[a:b]
        if one(r'enabledcvar "([^"]+)"', blk).group(1) != tab:
            continue
        m = one(r'rect (\d+) (\d+) (\d+) (\d+)', blk)
        if int(m.group(2)) < y_new:
            continue
        t = t[:a] + blk.replace(m.group(0), 'rect %s %d %s %s' % (m.group(1), int(m.group(2)) + ROW, m.group(3), m.group(4))) + t[b:]
        a, b = res_block(t, 'tilelk' + nm)
        blk = t[a:b]
        m = one(r'rect (\d+) (\d+) (\d+) (\d+)', blk)
        t = t[:a] + blk.replace(m.group(0), 'rect %s %d %s %s' % (m.group(1), int(m.group(2)) + ROW, m.group(3), m.group(4))) + t[b:]
        moved.append(nm)
    assert HOSTID in moved and len(moved) >= 8, moved
    a, b = res_block(t, 'tile' + HOSTID)
    tile = t[a:b]
    m = one(r'rect (\d+) (\d+) (\d+) (\d+)', tile)
    tile = tile.replace(m.group(0), 'rect %s %d %s %s' % (m.group(1), y_new, m.group(3), m.group(4)))
    tile = tile.replace('"tile%s"' % HOSTID, '"tile%s"' % ID).replace('title "FG 42"', 'title "%s"' % NAME).replace('t%s.cfg' % HOSTID, 't%s.cfg' % ID).replace('req%s.cfg' % HOSTID, 'req%s.cfg' % ID)
    a2, b2 = res_block(t, 'tilelk' + HOSTID)
    lk = t[a2:b2]
    m2 = one(r'rect (\d+) (\d+) (\d+) (\d+)', lk)
    lk = lk.replace(m2.group(0), 'rect %s %d %s %s' % (m2.group(1), y_new + 1, m2.group(3), m2.group(4))).replace('"tilelk%s"' % HOSTID, '"tilelk%s"' % ID).replace('coop_loLkV' + HOSTID, 'coop_loLkV' + ID)
    assert tile.count(ID) == 3 and NAME in tile and 'coop_loLkV' + ID in lk and '"tilelk%s"' % ID in lk
    return t[:b2] + nl + '// %s the iron-sight FG 42, its own tile, directly above the scoped FG 42 (unlock order)' % NOTE + nl + tile + nl + lk + t[b2:], moved, y_new


def lktab(t, tab0):
    nl = nl_of(t)
    assert 'coop_loLkV%s' % ID not in t
    ms = list(re.finditer(r'^set coop_loLkV7[0-9] 0[ \t]*\r?\n', t, re.M))
    assert ms
    m = ms[-1]
    t = t[:m.end()] + 'set coop_loLkV%s 0%s' % (ID, nl) + t[m.end():]
    if tab0:        # the tile's OWN tab file re-applies its lock (run hj34: with the vstr in lktab0 the heavy tab showed no padlock)
        ms = list(re.finditer(r'^vstr coop_loLkA\d+[ \t]*\r?\n', t, re.M))
        assert ms
        m = ms[-1]
        t = t[:m.end()] + 'vstr coop_loLkA%s%s' % (ID, nl) + t[m.end():]
    return t


def weaponclass(t):
    m = one(r'^([ \t]*)local\.classes\["models/weapons/fg42\.tik"\] = "rifle"[ \t]*\r?\n', t)
    return t[:m.end()] + '%slocal.classes["%s"] = "rifle"\t//%s%s' % (m.group(1), TIK, NOTE, nl_of(t)) + t[m.end():]


def buildmode(t):
    m = one(r'^([ \t]*)level\.coop_build_itemcount\[8\] = (\d+)[ \t]*\r?\n', t)
    n = int(m.group(2)); nl = nl_of(t)
    assert 'coop_build_item[8][%d]' % n in t and 'coop_build_item[8][%d]' % (n + 1) not in t
    return t[:m.start()] + '%slevel.coop_build_item[8][%d] = "%s"\t//%s%s%slevel.coop_build_itemcount[8] = %d%s' % (m.group(1), n + 1, TIK, NOTE, nl, m.group(1), n + 1, nl) + t[m.end():]


def giveall(t):
    m = one(r'^weapon weapons/FG42\.tik[ \t]*\r?\n', t)
    return t[:m.end()] + 'weapon weapons/%s.tik\t//%s%s' % (STEM, NOTE, nl_of(t)) + t[m.end():]


def tsv(t):
    nl = nl_of(t)
    rows = t.split(nl)
    ih = [i for i, l in enumerate(rows) if l.split('\t')[0] == HOSTID]
    ib = [i for i, l in enumerate(rows) if l.split('\t')[0] == '36']
    assert len(ih) == 1 and len(ib) == 1 and not any(l.split('\t')[0] == ID for l in rows)
    c = rows[ih[0]].split('\t'); bar = rows[ib[0]].split('\t')
    k = c.index('7.92MM / AUTOMATIC RIFLE')
    assert c[1] == HOST_TIK and c[k - 1] == 'FG 42' and c[k + 1:k + 5] == ['10', '9', '0', '5'] and bar[1] == 'models/weapons/bar.tik', c
    n = list(c)
    n[0] = ID; n[1] = TIK; n[2] = TIK if c[2] else c[2]
    n[k - 1] = NAME; n[k] = DESC
    n[k + 3], n[k + 4] = bar[k + 3], bar[k + 4]       # ACC / MOB: the BAR's (the tik carries the BAR's accuracy and movement rows)
    assert n[k + 7] == 'fg42', n
    n[k + 7] = STEM                                   # the finish tiks' stem
    while rows and rows[-1] == '':
        rows.pop()
    return nl.join(rows + ['\t'.join(n)]) + nl


SOURCES = (('hzm-mohaa-coop-mod/coop_mod/loadoutroster.scr', roster_case), ('hzm-mohaa-coop-mod/coop_mod/loadoutskins.scr', skins),
           ('hzm-mohaa-coop-mod/coop_mod/xp.scr', xp), ('hzm-mohaa-coop-mod/coop_mod/itemhandler.scr', itemhandler),
           ('hzm-mohaa-coop-mod/coop_mod/recoil_table.txt', recoil),
           ('hzm-mohaa-coop-mod/ubermode/get_player_weaponclass.scr', weaponclass), ('hzm-mohaa-coop-mod/coop_mod/buildmode_catalog.scr', buildmode),
           ('hzm-mohaa-coop-mod/global/giveall.scr', giveall), ('docs/tools/loadout_weapons.tsv', tsv))


def edit_sources(root, log):
    for rel, fn in SOURCES:
        p = os.path.join(root, rel.replace('/', os.sep))
        wr(p, fn(rd(p)))
    p = os.path.join(root, 'hzm-mohaa-coop-mod', 'ui', 'coop_loadout.urc')
    t, moved, y = urc(rd(p)); wr(p, t)
    log.append('tile%s at y %d on the heavy tab; moved one row down: %s' % (ID, y, ' '.join(moved)))
    for k in range(6):
        p = os.path.join(root, 'hzm-mohaa-coop-mod', 'ui', 'loadout', 'lktab%d.cfg' % k)
        wr(p, lktab(rd(p), k == TAB))
    w = os.path.join(ASSETS, 'models', 'weapons')
    for f in os.listdir(w):
        if f.lower().startswith(STEM) and f.lower().endswith('.tik'):
            shutil.copyfile(os.path.join(w, f), os.path.join(root, 'hzm-mohaa-coop-mod', 'models', 'weapons', f))


def patch_generators(root, new):
    t = os.path.join(root, 'docs', 'tools')
    p = os.path.join(t, 'armory_unlocks.py'); s = rd(p)
    old = "MOD = r'C:\\mohaa-coop-dev\\hzm-mohaa-coop-mod'"
    if 'HZM_MOD' not in s:                  # the rifle lane's patch, identical (skipped once it is in the real tool)
        assert s.count(old) == 1
        s = s.replace(old, "MOD = os.environ.get('HZM_MOD') or r'C:\\mohaa-coop-dev\\hzm-mohaa-coop-mod'   # HZM_MOD: a scratch / staged tree (as gen_loadout.py)")
        wr(p, s)
    if not new:
        return
    p = os.path.join(t, 'gen_service_record.py'); s = rd(p)
    nl = '\r\n' if '\r\n' in s else '\n'
    m = one(r'^    "models/weapons/bar\.tik": "[^"]*",[ \t]*\r?\n', s)
    s = s[:m.start()] + '    "%s": "FG 42 (Iron Sights)",' % TIK + nl + s[m.start():]
    wr(p, s)


def run_gens(root, log):
    env = dict(os.environ, HZM_MOD=os.path.join(root, 'hzm-mohaa-coop-mod'), PYTHONIOENCODING='utf-8')
    t = os.path.join(root, 'docs', 'tools')
    for cmd in (['gen_loadout.py', 'build'], ['gen_skinbase.py'], ['armory_unlocks.py', '--emit'], ['gen_loadout.py', 'check']):
        r = subprocess.run([sys.executable, os.path.join(t, cmd[0])] + cmd[1:], cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        tail = (r.stdout.strip().splitlines() or ['(no output)'])[-1]
        log.append('%-28s exit %d  %s' % (' '.join(cmd), r.returncode, tail[:150]))
        assert r.returncode == 0, (cmd, r.stdout[-1500:], r.stderr[-1500:])
        for p in (r.stdout + r.stderr).splitlines():
            assert REPO.lower() + '\\hzm-mohaa-coop-mod' not in p.lower() and REPO.lower() + '\\docs' not in p.lower(), 'a generator named the REAL tree: ' + p


def main():
    stamp = time.strftime('%Y%m%d_%H%M%S')
    base, new = os.path.join(SCRATCH, stamp, 'base'), os.path.join(SCRATCH, stamp, 'new')
    log = []
    GEN.seed(base); patch_generators(base, False); log.append('--- BASE (mod tree as it is)'); run_gens(base, log)
    GEN.seed(new); patch_generators(new, True); log.append('--- NEW (sources edited, generators patched)'); edit_sources(new, log); run_gens(new, log)
    B = dict(GEN.tree(base, 'hzm-mohaa-coop-mod'), **GEN.tree(base, 'docs'))
    N = dict(GEN.tree(new, 'hzm-mohaa-coop-mod'), **GEN.tree(new, 'docs'))
    real = lambda rel: os.path.join(REPO, rel.replace('/', os.sep))
    drift = sorted(r for r in B if os.path.isfile(real(r)) and open(real(r), 'rb').read() != B[r] and not r.endswith('armory_unlocks.py'))
    changed = sorted(r for r in N if r in B and N[r] != B[r])
    added = sorted(r for r in N if r not in B and not r.lower().startswith('hzm-mohaa-coop-mod/models/weapons/'))
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    gp, mp = [], []
    for r in changed + ['docs/tools/armory_unlocks.py']:
        a = rd(real(r)); b = N[r].decode('latin-1')
        if a == b:
            continue
        (gp if r.startswith('docs/') else mp).extend(difflib.unified_diff(a.splitlines(True), b.splitlines(True), 'a/' + r, 'b/' + r, n=2))
    open(os.path.join(OUT, 'generators.patch'), 'w', newline='', encoding='latin-1').write(''.join(gp))
    open(os.path.join(OUT, 'armory_fg42irons.patch'), 'w', newline='', encoding='latin-1').write(''.join(mp))
    for r in added:
        wr(os.path.join(OUT, 'new', r.replace('/', os.sep)), N[r].decode('latin-1'))
    z = zipfile.ZipFile(RELEASED)
    names = {n.lower(): n for n in z.namelist()}
    notrel, ovfiles = [], []
    if os.path.isdir(OV):
        shutil.rmtree(OV)
    for r in changed + added:
        if not r.startswith('hzm-mohaa-coop-mod/'):
            continue
        g = r[len('hzm-mohaa-coop-mod/'):]
        GEN.scan(g, N[r].decode('latin-1'))
        if r in changed:
            relb = z.read(names[g.lower()]) if g.lower() in names else None
            if relb != open(real(r), 'rb').read():
                notrel.append(g + (' (not in the released code pak)' if relb is None else ' (the mod tree is ahead of the release)'))
        wr(os.path.join(OV, g.replace('/', os.sep)), N[r].decode('latin-1'))
        ovfiles.append(g)
    rep = ['stage_armory_fg42irons.py %s   scratch: %s' % (stamp, os.path.join(SCRATCH, stamp))] + log
    rep += ['', 'generator drift already in the tree (BASE differs from the real file; NOT staged): %d' % len(drift)] + ['   ' + r for r in drift]
    rep += ['', 'changed by this weapon: %d' % len(changed)] + ['   ' + r for r in changed]
    rep += ['', 'new files: %d' % len(added)] + ['   ' + r for r in added]
    rep += ['', 'overlay files whose mod-tree original is NOT the released file (check before a harness run): %d' % len(notrel)] + ['   ' + r for r in notrel]
    open(os.path.join(OUT, 'report.txt'), 'w', newline='\n').write('\n'.join(rep) + '\n')
    wr(os.path.join(OV, 'MANIFEST.txt'), '\n'.join(sorted(ovfiles)) + '\n')
    print('\n'.join(rep))


if __name__ == '__main__':
    main()
