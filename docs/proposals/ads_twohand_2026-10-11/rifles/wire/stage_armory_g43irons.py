"""Iron-sight G43 as ITS OWN ARMORY ENTRY (user 2026-10-13: "g43 shouldn't be a variant but its own rifle you unlock
honestly and pretty early on"). Supersedes wire_mv2_g43irons.patch (model variant 13 of the scoped G43).

Nothing is applied to the mod tree. One set of text transforms is run over TWO sources:
    the MOD TREE      -> armory_g43irons.patch (unified diff of every changed file) + armory_new/ (the new files)
    the RELEASED pak  -> ../armory_ov/  (what the private test install mounts; mkov_rifle.py --armory packs it)
The recipe is the scoped G43's (roster id 04) and the Johnson's (id 70, the last stand-alone rifle added):

  coop_mod/loadoutroster.scr   roster_get `case "78"` + the roster_ids index row (count + 1)
  coop_mod/loadoutskins.scr    finishes fid 1-7 of the new base tik
  coop_mod/loadoutskins_base.scr   the finished tiks -> their base (generated file: gen_skinbase.py re-emits it)
  coop_mod/xp.scr              rank unlock: RANK 2 (Technician Fifth Grade, 1200 XP)
  coop_mod/unlockreq_gen.scr   its requirement text (generated file: armory_unlocks.py re-emits it)
  coop_mod/itemhandler.scr     the two tik lists of rifle-ammo weapons
  coop_mod/recoil_table.txt    the 12 rows of recoil_table_g43irons.txt
  ui/coop_loadout.urc          tile78 + its lock label on the rifle tab, in UNLOCK order: between the M1 Carbine and the Kar98k (the rows below move down)
  ui/loadout/lktab0-5.cfg      the lock cvar of the new tile
  ui/loadout/p78 t78 w78_s1 w78_s2 req78 finp78_1..7 .cfg   (new; gen_loadout.py build writes the same from the TSV row)
  ui/hud_ammo_G43Irons.urc     the empty ammo HUD menu "hud_ammo_G 43 Irons" (menus are keyed by weapon NAME)
  docs/tools/loadout_weapons.tsv   the generator's row (build.ps1 runs `gen_loadout.py check` and blocks on drift)
The torso state row is player_torso_g43irons.patch (g43state.py).

    python stage_armory_g43irons.py
"""
import os, re, sys, difflib, zipfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
MOD = r"C:\mohaa-coop-dev\hzm-mohaa-coop-mod"
TSV = r"C:\mohaa-coop-dev\docs\tools\loadout_weapons.tsv"
RELEASED = 'G:/GOG/Medal of Honor - Allied Assault War Chest/maintt/zzzzzz_co-op_hzm_mod_code.pk3'     # read only
OV = os.path.normpath(os.path.join(HERE, '..', 'armory_ov'))
NEWDIR = os.path.join(HERE, 'armory_new')
PATCH = os.path.join(HERE, 'armory_g43irons.patch')

ID = '78'                                   # 73 is free in coop but 76 / 77 are the MP roster's: 78 is clear of both
TIK = 'models/weapons/coop_g43_irons.tik'
STEM = 'coop_g43_irons'
NAME = 'GEWEHR 43 (IRON SIGHTS)'
FIN_NAME = 'GEWEHR 43 IRONS'                # the finish previews add ' (GOLD)' etc.
DESC = '7.92MM / SEMI-AUTO / IRON SIGHTS'
RANK = 2
RANK_NAME = 'Technician Fifth Grade'
FIN = {1: 'gold', 2: 'chrome', 3: 'blued', 4: 'bloody', 5: 'camo_woodland', 6: 'camo_winter', 7: 'camo_desert'}
TILE_Y = None                               # set by urc(): the row of AFTER_TILE before it moves down
AFTER_TILE = '03'                           # the Kar98k (rank 3): the new tile takes its row
ROW = 19                                    # px between two rows of the list
BARS = ('8', '10')                          # ACC, MOB stat bars = the M1 Garand's (the tik carries the Garand's accuracy / movement rows); DMG / RPM stay the G43's.
                                            # The scoped G43's own row has ACC 0 (an empty bar on its panel too)
NOTE = '[g43 irons 2026-10-13]'


def nl_of(t):
    return '\r\n' if '\r\n' in t else '\n'


def one(rx, t, flags=re.M):
    m = list(re.finditer(rx, t, flags))
    assert len(m) == 1, (rx, len(m))
    return m[0]


def roster(t):
    nl = nl_of(t)
    assert 'case "%s":' % ID not in t
    m = one(r'^([ \t]*)case "04":.*?^[ \t]*break[ \t]*\r?\n', t, re.M | re.S)
    blk = m.group(0)
    new = blk.replace('case "04":', 'case "%s":\t//%s the iron-sight G43, its own entry' % (ID, NOTE)).replace('models/weapons/g43.tik', TIK).replace('"GEWEHR 43"', '"%s"' % NAME)
    assert new.count(TIK) == 1 and NAME in new
    t = t[:m.end()] + new + t[m.end():]
    n = int(one(r'level\.coop_loRosterN = (\d+)', t).group(1))
    t = re.sub(r'level\.coop_loRosterN = \d+', 'level.coop_loRosterN = %d' % (n + 1), t)
    m = one(r'^([ \t]*)level\.coop_loRosterTab\[%d\] = \d+[ \t]*\r?\n' % (n - 1), t)
    ind = m.group(1)
    rows = ''.join('%slevel.coop_loRoster%s[%d] = %s%s' % (ind, k, n, v, nl) for k, v in (('Id', '"%s"' % ID), ('Give', '"%s"' % TIK), ('Tab', '0')))
    return t[:m.end()] + rows + t[m.end():]


def skins(t):
    nl = nl_of(t)
    m = one(r'^([ \t]*)level\.coop_skinGive\["models/weapons/g43\.tik"\]\[7\] = [^\n]*\n', t)
    rows = ''.join('%slevel.coop_skinGive["%s"][%d] = "models/weapons/%s_%s.tik"%s' % (m.group(1), TIK, k, STEM, FIN[k], nl) for k in sorted(FIN))
    t = t[:m.end()] + rows + t[m.end():]
    n = int(one(r'level\.coop_skinN = (\d+)', t).group(1))
    return re.sub(r'level\.coop_skinN = \d+', 'level.coop_skinN = %d' % (n + len(FIN)), t)


def skinbase(t):
    """generated by gen_skinbase.py from loadoutskins.scr (finished tik -> its base). Without these rows a finished
    rifle is 'not on list' in itemhandler::getAmmoType (run rb35: four warnings per spawn)"""
    nl = nl_of(t)
    m = one(r'^([ \t]*)level\.coop_skinBase\["models/weapons/g43_camo_desert\.tik"\] = [^\n]*\n', t)
    rows = ''.join('%slevel.coop_skinBase["models/weapons/%s_%s.tik"] = "%s"%s' % (m.group(1), STEM, FIN[k], TIK, nl) for k in sorted(FIN))
    return t[:m.end()] + rows + t[m.end():]


def xp(t):
    nl = nl_of(t)
    m = one(r'^([ \t]*)level\.coop_xp_rankUnlockCnt\[%d\] = (\d+)[ \t]*\r?\n' % RANK, t)
    c = int(m.group(2))
    t = t[:m.start()] + '%slevel.coop_xp_rankUnlockCnt[%d] = %d%s' % (m.group(1), RANK, c + 1, nl) + t[m.end():]
    m = one(r'^([ \t]*)level\.coop_xp_rankUnlock\[%d\]\[%d\] = [^\n]*\n' % (RANK, c - 1), t)
    row = '%slevel.coop_xp_rankUnlock[%d][%d] = "%s"\t//%s early rifle unlock: after the carbine (rank 1), before the Kar98 (3) and the scoped G43 (5)%s' % (m.group(1), RANK, c, TIK, NOTE, nl)
    return t[:m.end()] + row + t[m.end():]


def unlockreq(t):
    nl = nl_of(t)
    m = one(r'^([ \t]*)level\.coop_unlockReq\["models/weapons/carbine\.tik"\] = [^\n]*\n', t)
    return t[:m.end()] + '%slevel.coop_unlockReq["%s"] = "Reach rank %d"%s' % (m.group(1), TIK, RANK, nl) + t[m.end():]


def itemhandler(t):
    nl = nl_of(t)
    ms = list(re.finditer(r'^([ \t]*)case "models/weapons/g43\.tik":[ \t]*\r?\n', t, re.M))
    assert len(ms) >= 1, 'no g43 tik case'
    for m in reversed(ms):
        t = t[:m.end()] + '%scase "%s":%s' % (m.group(1), TIK, nl) + t[m.end():]
    return t


def recoil(t):
    nl = nl_of(t)
    rows = [l.strip() for l in open(os.path.join(HERE, 'recoil_table_g43irons.txt'), encoding='latin-1').read().splitlines() if l.strip() and not l.strip().startswith(('//', '#'))]
    assert len(rows) == 12 and all(r.startswith(STEM) for r in rows), rows[:2]
    assert not re.search(r'(?m)^%s\b' % STEM, t)
    return t.rstrip('\r\n') + nl + '// %s iron-sight G43: the G43\'s rows under its own tik names (coop_g43_irons resolves to no g43 row)' % NOTE + nl + nl.join(rows) + nl


def res_block(t, name):
    i = t.index('name "%s"' % name)
    a = t.rfind('resource', 0, i)
    b = re.compile(r'^\}[ \t]*\r?\n', re.M).search(t, i).end()
    return a, b


def urc(t):
    nl = nl_of(t)
    assert 'name "tile%s"' % ID not in t
    # the rifle tab lists its weapons in UNLOCK order (rank 0, 1, 3, 5, 7 ... then the challenge rifles): a rank-2
    # rifle belongs between the M1 Carbine and the Kar98k. Every rifle-tab tile from the Kar98k down moves one row
    # (19 px) lower, with its lock label; the new tile takes the Kar98k's old row.
    a, b = res_block(t, 'tile%s' % AFTER_TILE)
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
    assert AFTER_TILE in moved and '04' in moved and len(moved) >= 10, moved
    global TILE_Y
    TILE_Y = y_new
    a, b = res_block(t, 'tile04')
    tile = t[a:b]
    m = one(r'rect (\d+) (\d+) (\d+) (\d+)', tile)
    tile = tile.replace(m.group(0), 'rect %s %d %s %s' % (m.group(1), TILE_Y, m.group(3), m.group(4)))
    tile = tile.replace('"tile04"', '"tile%s"' % ID).replace('title "GEWEHR 43"', 'title "%s"' % NAME).replace('t04.cfg', 't%s.cfg' % ID).replace('req04.cfg', 'req%s.cfg' % ID)
    a2, b2 = res_block(t, 'tilelk04')
    lk = t[a2:b2]
    m2 = one(r'rect (\d+) (\d+) (\d+) (\d+)', lk)
    lk = lk.replace(m2.group(0), 'rect %s %d %s %s' % (m2.group(1), TILE_Y + 1, m2.group(3), m2.group(4))).replace('"tilelk04"', '"tilelk%s"' % ID).replace('coop_loLkV04', 'coop_loLkV%s' % ID)
    assert ID in tile and ID in lk and '04' not in tile.replace('0.84', '').replace('1.00', '').replace('0.90', '') and 'V04' not in lk
    _, e = res_block(t, 'tilelk70')
    return t[:e] + nl + '// %s the iron-sight G43, its own tile, between the M1 Carbine and the Kar98k' % NOTE + nl + tile + nl + lk + t[e:]


def lktab(t, tab0):
    nl = nl_of(t)
    assert 'coop_loLkV%s' % ID not in t
    ms = list(re.finditer(r'^set coop_loLkV7[0-9] 0[ \t]*\r?\n', t, re.M))
    assert ms
    m = ms[-1]
    t = t[:m.end()] + 'set coop_loLkV%s 0%s' % (ID, nl) + t[m.end():]
    if tab0:
        m = one(r'^vstr coop_loLkA70[ \t]*\r?\n', t)
        t = t[:m.end()] + 'vstr coop_loLkA%s%s' % (ID, nl) + t[m.end():]
    return t


def cfgs(read):
    out = {}
    p04, p70 = read('ui/loadout/p04.cfg'), read('ui/loadout/p70.cfg')
    nl = nl_of(p04)
    head = [l for l in p70.splitlines() if l.startswith(('set coop_loMvOn', 'set coop_loMvReqCur', 'set coop_loMvPN_'))]
    assert len(head) == 6, head
    body = [l for l in p04.splitlines() if not l.startswith(('set coop_loMvOn', 'set coop_loMvReqCur', 'set coop_loMvPN_'))]
    p = nl.join(head + body) + nl
    p = p.replace('finp04_', 'finp%s_' % ID).replace('models/weapons/g43.tik', TIK).replace('set coop_loPrevId "04"', 'set coop_loPrevId "%s"' % ID)
    p = p.replace('set coop_loNm "GEWEHR 43"', 'set coop_loNm "%s"' % NAME).replace('set coop_loCd "7.92MM / SEMI-AUTO"', 'set coop_loCd "%s"' % DESC)
    p = p.replace('w04_s', 'w%s_s' % ID)
    for key, val in (('coop_loB2', BARS[0]), ('coop_loB3', BARS[1])):
        mm = one(r'set %s "textures/hud/coop_bf\d+"' % key, p)
        p = p.replace(mm.group(0), 'set %s "textures/hud/coop_bf%s"' % (key, val))
    assert '04' not in p and TIK in p and NAME in p and DESC in p, [l for l in p.splitlines() if '04' in l]
    out['ui/loadout/p%s.cfg' % ID] = p
    out['ui/loadout/t%s.cfg' % ID] = read('ui/loadout/t04.cfg').replace('p04.cfg', 'p%s.cfg' % ID).replace('coop_loCmt04', 'coop_loCmt%s' % ID)
    for s in (1, 2):
        w = read('ui/loadout/w04_s%d.cfg' % s)
        w2 = w.replace('"04"', '"%s"' % ID).replace('"GEWEHR 43"', '"%s"' % NAME).replace('models/weapons/g43.tik', TIK).replace(',w%d04' % s, ',w%d%s' % (s, ID)).replace('p04.cfg', 'p%s.cfg' % ID)
        assert '04' not in w2 and w2.count(ID) >= 3, w2
        out['ui/loadout/w%s_s%d.cfg' % (ID, s)] = w2
    out['ui/loadout/req%s.cfg' % ID] = 'set coop_loReq "UNLOCK: Rank: %s"%sset coop_loReq2 ""%s' % (RANK_NAME, nl, nl)
    for k in sorted(FIN):
        f = read('ui/loadout/finp04_%d.cfg' % k)
        m = one(r'set coop_loNm "GEWEHR 43 \(([^"]*)\)"', f)
        f2 = f.replace('models/weapons/g43_%s.tik' % FIN[k], 'models/weapons/%s_%s.tik' % (STEM, FIN[k])).replace(m.group(0), 'set coop_loNm "%s (%s)"' % (FIN_NAME, m.group(1)))
        assert STEM in f2 and FIN_NAME in f2, f
        out['ui/loadout/finp%s_%d.cfg' % (ID, k)] = f2
    hud = read('ui/hud_ammo_G43.urc')
    assert hud.count('"hud_ammo_G 43"') == 1
    out['ui/hud_ammo_G43Irons.urc'] = hud.replace('"hud_ammo_G 43"', '"hud_ammo_G 43 Irons"')
    return out


def transform(read):
    """read(game path) -> text; returns {game path: new text} of every changed or new file"""
    out = {}
    for path, fn in (('coop_mod/loadoutroster.scr', roster), ('coop_mod/loadoutskins.scr', skins), ('coop_mod/loadoutskins_base.scr', skinbase), ('coop_mod/xp.scr', xp),
                     ('coop_mod/unlockreq_gen.scr', unlockreq), ('coop_mod/itemhandler.scr', itemhandler),
                     ('coop_mod/recoil_table.txt', recoil), ('ui/coop_loadout.urc', urc)):
        out[path] = fn(read(path))
    for k in range(6):
        out['ui/loadout/lktab%d.cfg' % k] = lktab(read('ui/loadout/lktab%d.cfg' % k), k == 0)
    out.update(cfgs(read))
    for path, t in out.items():
        if path.endswith(('.scr', '.urc')):
            d = 0
            for ln in t.splitlines():
                c = ln.split('//')[0]
                d += c.count('{') - c.count('}')
            assert d == 0, (path, d)
            assert '\u2014' not in t and not t.startswith('\ufeff'), path
    return out


def tsv_row():
    raw = open(TSV, 'rb').read().decode('latin-1')
    rows = [l for l in raw.splitlines() if l.split('\t')[0] == '04']
    assert len(rows) == 1
    c = rows[0].split('\t')
    assert c[1] == 'models/weapons/g43.tik' and 'GEWEHR 43' in c and '7.92MM / SEMI-AUTO' in c, c
    c[0] = ID; c[1] = TIK
    c[2] = TIK if c[2] else c[2]
    c[c.index('GEWEHR 43')] = NAME
    i = c.index('7.92MM / SEMI-AUTO')
    c[i] = DESC
    assert c[i + 1:i + 5] == ['5', '4', '0', '5'], c[i + 1:i + 5]
    c[i + 3], c[i + 4] = BARS
    nl = nl_of(raw)
    return raw, raw.rstrip('\r\n') + nl + '\t'.join(c) + nl


def main():
    # 1. the mod tree: patch + new files
    def rd_mod(p):
        return open(os.path.join(MOD, p.replace('/', os.sep)), 'rb').read().decode('latin-1')
    out = transform(rd_mod)
    diff, new = [], []
    if os.path.isdir(NEWDIR):
        shutil.rmtree(NEWDIR)
    for p in sorted(out):
        f = os.path.join(MOD, p.replace('/', os.sep))
        if os.path.isfile(f):
            diff += list(difflib.unified_diff(rd_mod(p).splitlines(True), out[p].splitlines(True), 'a/hzm-mohaa-coop-mod/' + p, 'b/hzm-mohaa-coop-mod/' + p, n=2))
        else:
            d = os.path.join(NEWDIR, p.replace('/', os.sep))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            open(d, 'wb').write(out[p].encode('latin-1'))
            new.append(p)
    a, b = tsv_row()
    diff += list(difflib.unified_diff(a.splitlines(True), b.splitlines(True), 'a/docs/tools/loadout_weapons.tsv', 'b/docs/tools/loadout_weapons.tsv', n=1))
    open(PATCH, 'w', newline='', encoding='latin-1').write(''.join(diff))
    print('mod tree: %d files changed -> %s; %d new files -> %s' % (len(out) - len(new), os.path.basename(PATCH), len(new), NEWDIR))
    for p in sorted(out):
        print('   %s %s' % ('NEW' if p in new else 'mod', p))
    # 2. the released pak: the harness overlay
    z = zipfile.ZipFile(RELEASED)
    names = {n.lower(): n for n in z.namelist()}

    def rd_rel(p):
        assert p.lower() in names, 'not in the released pak: ' + p
        return z.read(names[p.lower()]).decode('latin-1')
    rel = transform(rd_rel)
    if os.path.isdir(OV):
        shutil.rmtree(OV)
    for p, t in rel.items():
        d = os.path.join(OV, p.replace('/', os.sep))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        open(d, 'wb').write(t.encode('latin-1'))
    same = sum(1 for p in out if rel.get(p) == out[p])
    print('released pak: %d files -> %s (%d identical to the mod-tree result)' % (len(rel), OV, same))


if __name__ == '__main__':
    main()
