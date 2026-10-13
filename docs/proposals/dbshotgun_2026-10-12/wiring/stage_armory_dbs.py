"""The double barrel as ITS OWN ARMORY ENTRY with its own unlock path, the mod's way - through the generators, nothing
generated is written by hand. REPLACES wiring option A (the switch on the trench gun's page: superseded/).
The recipe is the rifle lane's for the G 43 Irons (ads_twohand_2026-10-11/rifles/wire/stage_armory_gen.py, whose
scratch-repo machinery is used here as a library) and the heavy lane's for the FG 42 Irons; the anchors are the trench
gun's (roster id 44).

    python wiring/stage_armory_dbs.py [--sr]
        gen/generators.patch      the generator + TSV patches            (apply to docs/tools)
        gen/armory_dbs.patch      every changed mod-tree file            (apply, or edit the sources and re-run the generators)
        gen/new/                  every new mod-tree file
        gen/report.txt            what ran, what changed, drift
        ../armory_ov/             the same game files for the private test install (tools/mkov_dbs.py --armory)
        --sr: also run the (patched) Service Record generator in both scratch trees and stage what it changes for the
              test install only (../armory_ov/, listed in the report) - at integration build.ps1 runs it anyway.

AUTHORED for the new gun (edited in a scratch copy of the repo, never in the real tree):
    docs/tools/loadout_weapons.tsv   one row: id 80, tile "DOUBLE BARREL", heavy tab, "12 GAUGE / BREAK-ACTION", bars
                                     DMG 10 / RPM 3 / ACC 6 / MOB 10, 2 rounds (new picture textures/hud/clip/clip_2.tga)
    coop_mod/loadoutroster.scr       roster_get `case "80"` (the trench gun's case with the new tik / name)
    coop_mod/loadoutskins.scr        finishes fid 1-7 of the new base tik (+ coop_skinN)
    coop_mod/challenges.scr          THE UNLOCK: chal_def "wpn_shotgun_v" "support_weapons" "Both Barrels"
                                     "Get 60 kills with the Shotgun" on the EXISTING statistic wpn_shotgun, reward = the
                                     tik. The mod's rule for a gun's sibling ("VARIANT UNLOCK CHAINS": Thompson drum,
                                     MP40 silenced, StG scoped ... = 100 kills with the base gun, between its base (40-50)
                                     and elite (120-150) challenges); the shotgun's are 30 and 90, so 60. It is the LAST
                                     chal_def of the file: the export index of no existing challenge.scr row moves.
    coop_mod/loadoutpick.scr         master switch coop_dbShotgun: 0 = the pick is refused (loadout_setBody), the tile
                                     is hidden and its padlock is off (loadout_ui_exportUnlocks -> client coop_loDbT)
    coop_defaults.cfg                seta coop_dbShotgun 1, seta coop_loDbT "set coop_loP3d 1"
    coop_mod/itemhandler.scr         the tik in getAmmoType ("shotgun") and in isPrimaryWeapon
    coop_mod/recoil_table.txt        8 rows (the base + 7 finishes) from the tik's own `entry viewkick` line
    ui/coop_loadout.urc              tile80 + its lock label, the LAST tile of the heavy tab (no other tile moves; hidden
                                     by the master switch it leaves no empty row). The tile is lit by coop_loP3d (not coop_loP3): the heavy tab
                                     AND the server's master switch. NO generator; checksum-locked (see README)
    ui/loadout/lktab0-5.cfg          the lock cvar and the tile cvar of the new tile (lktab3 = the heavy tab applies them)
    ubermode/get_player_weaponclass.scr, global/giveall.scr      the lists the pump gun is in
GENERATED (run as copies in the scratch repo):
    gen_loadout.py build      ui/loadout/p80 t80 w80_s1 w80_s2 req80 finp80_1..7 .cfg + loadoutroster.scr::roster_ids
    gen_skinbase.py           coop_mod/loadoutskins_base.scr       (finished tik -> its base)
    armory_unlocks.py --emit  coop_mod/unlockreq_gen.scr           (the requirement text)
    gen_loadout.py check
    gen_service_record.py     (--sr) the Service Record pages: one more row on SUPPORT WEAPONS, its reward name
  generator patches: armory_unlocks.py honours HZM_MOD (the rifle lane's patch, identical); gen_service_record.py
  REWARD_NAMES gets the tik -> "Double Barrel Shotgun" and honours HZM_MOD for its chdir.

FINISHES unlock exactly as the pump gun's: fid 1-7 are account-wide (challenges fin_gold ... fin_desert), and a gun
takes finishes once ITS kill challenge is done - loadoutpick.scr::loadout_finMastered asks chal_widFromModel(give),
which answers "shotgun" for coop_dbshotgun.tik (containsText), so the gate is the pump gun's wpn_shotgun (30 kills).
The double barrel has NO statistic of its own: its kills are shotgun kills (same resolver).
"""
import os, re, sys, shutil, difflib, subprocess, zipfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
RW = os.path.normpath(os.path.join(PROP, '..', 'ads_twohand_2026-10-11', 'rifles', 'wire'))
sys.path.insert(0, RW)
import stage_armory_g43irons as OLD        # generic helpers only: one(), nl_of(), res_block()
import stage_armory_gen as GEN             # the scratch repo: seed(), rd(), wr(), tree(), scan()
one, nl_of, res_block, rd, wr = OLD.one, OLD.nl_of, OLD.res_block, GEN.rd, GEN.wr
REPO, MOD, TOOLS, RELEASED = GEN.REPO, GEN.MOD, GEN.TOOLS, GEN.RELEASED
ASSETS = os.path.join(PROP, 'assets')
OUT = os.path.join(HERE, 'gen')
OV = os.path.join(PROP, 'armory_ov')
SCRATCH = os.path.join(os.path.dirname(GEN.SCRATCH), 'dbs', 'armgen')

ID = '80'                                   # 78 = G 43 Irons, 79 = FG 42 Irons (staged by their lanes), 76 / 77 = the MP roster's
HOSTID = '44'                               # the trench gun
HOST_TIK = 'models/weapons/shotgun.tik'
TIK = 'models/weapons/coop_dbshotgun.tik'
STEM = 'coop_dbshotgun'
NAME = 'DOUBLE BARREL'
DESC = '12 GAUGE / BREAK-ACTION'
BARS = ('10', '3', '6', '10')               # DMG RPM ACC MOB  [trench gun 10 1 8 9]: 364 a barrel, two quick shots, 1.4 x the cone, speed 1.00
CLIP = '2'
CHAL = ('wpn_shotgun_v', 'support_weapons', 'Both Barrels', 'Get 60 kills with the Shotgun', 'wpn_shotgun', 60)
REWARD_NAME = 'Double Barrel Shotgun'
FIN = {1: 'gold', 2: 'chrome', 3: 'blued', 4: 'bloody', 5: 'camo_woodland', 6: 'camo_winter', 7: 'camo_desert'}
ROW = 19
TILECVAR = 'coop_loP3d'
NOTE = '[dbshotgun 2026-10-13]'


def roster_case(t):
    assert 'case "%s":' % ID not in t
    m = one(r'^([ \t]*)case "%s":.*?^[ \t]*break[ \t]*\r?\n' % HOSTID, t, re.M | re.S)
    new = m.group(0).replace('case "%s":' % HOSTID, 'case "%s":\t//%s the double-barrel shotgun, its own entry' % (ID, NOTE)).replace(HOST_TIK, TIK).replace('"TRENCH GUN"', '"%s"' % NAME)
    assert new.count(TIK) == 1 and NAME in new and '"shotgun"' in new
    return t[:m.end()] + new + t[m.end():]


def skins(t):
    nl = nl_of(t)
    m = one(r'^([ \t]*)level\.coop_skinGive\["models/weapons/shotgun\.tik"\]\[7\] = [^\n]*\n', t)
    rows = ''.join('%slevel.coop_skinGive["%s"][%d] = "models/weapons/%s_%s.tik"%s' % (m.group(1), TIK, k, STEM, FIN[k], nl) for k in sorted(FIN))
    t = t[:m.end()] + rows + t[m.end():]
    n = int(one(r'level\.coop_skinN = (\d+)', t).group(1))
    return re.sub(r'level\.coop_skinN = \d+', 'level.coop_skinN = %d' % (n + len(FIN)), t)


def challenges(t):
    nl = nl_of(t)
    assert '"%s"' % CHAL[0] not in t
    ms = list(re.finditer(r'^([ \t]*)waitthread chal_def "[^\n]*\n', t, re.M))
    m = ms[-1]
    assert '"obj_the_quiet_type"' in m.group(0), m.group(0)[:80]          # the last definition of the file, as read on 2026-10-13
    row = ('%s//%s VARIANT UNLOCK CHAIN (see the block above): kills with the shotgun unlock its sibling, the double barrel.%s'
           '%s//Rides the existing wpn_shotgun kill stat - the double barrel\'s own kills count on it too (chal_widFromModel).%s'
           '%s//LAST definition on purpose: the export index of every challenge above stays what it was.%s'
           '%swaitthread chal_def "%s" "%s" "%s" "%s" "%s" %d "%s"%s') % (m.group(1), NOTE, nl, m.group(1), nl, m.group(1), nl, m.group(1), CHAL[0], CHAL[1], CHAL[2], CHAL[3], CHAL[4], CHAL[5], TIK, nl)
    return t[:m.end()] + row + t[m.end():]


def loadoutpick(t):
    nl = nl_of(t)
    a = one(r'^\t//slot legality \(the menu enforces this too - re-check server-side\)[ \t]*\r?\n', t)
    deny = ('\t//%s the server\'s master switch: coop_dbShotgun 0 = the double barrel cannot be put in a slot. keepArchive: the%s'
            '\t//client keeps its archived pick, so it comes back by itself on a server that allows the gun.%s'
            '\tif(local.r["give"] == "%s" && getcvar("coop_dbShotgun") == "0"){%s'
            '\t\twaitthread loadout_deny local.player local.slot ("Armory: " + local.r["name"] + " is switched off on this server") 1%s'
            '\t\tend%s'
            '\t}%s') % (NOTE, nl, nl, TIK, nl, nl, nl, nl)
    t = t[:a.start()] + deny + t[a.start():]
    # the tile's visibility + its padlock follow the switch (same archived-command pattern as coop_loLkA<id>)
    b = one(r'^\t\tlocal\.id = level\.coop_loRosterId\[local\.i\][ \t]*\r?\n', t)
    lk = ('\t\t//%s master switch off: no padlock on a tile that is not drawn%s'
          '\t\tif(level.coop_loRosterGive[local.i] == "%s" && getcvar("coop_dbShotgun") == "0"){ local.lk = 0 }%s') % (NOTE, nl, TIK, nl)
    t = t[:b.start()] + lk + t[b.start():]
    c = one(r'^\twaitthread coop_mod/loadoutskins\.scr::skin_init[ \t]*\r?\n\tlocal\.f = 1[ \t]*\r?\n', t)
    vis = ('\t//%s the double barrel\'s tile is lit by %s = the heavy tab AND the server\'s master switch: the heavy%s'
           '\t//tab\'s cfg (ui/loadout/lktab3.cfg) runs `vstr coop_loDbT`, archived here like the padlock commands above%s'
           '\t//(unquoted on the wire, bug-758). Default (coop_defaults.cfg) = shown.%s'
           '\tlocal.dbOn = 1%s'
           '\tif(getcvar("coop_dbShotgun") == "0"){ local.dbOn = 0 }%s'
           '\tif(local.player.flags["coop_loDbTLast"] != local.dbOn){%s'
           '\t\tlocal.player.flags["coop_loDbTLast"] = local.dbOn%s'
           '\t\tlocal.player stufftext ( "seta coop_loDbT set %s " + local.dbOn )%s'
           '\t}%s') % (NOTE, TILECVAR, nl, nl, nl, nl, nl, nl, nl, TILECVAR, nl, nl)
    return t[:c.start()] + vis + t[c.start():]


def defaults(t):
    nl = nl_of(t)
    m = one(r'^seta coop_lmsLateJoin 1[^\n]*\n', t)
    return t[:m.end()] + ('seta coop_dbShotgun 1\t\t// %s the double-barrel shotgun is in the armory (server: 0 = its tile is hidden and the pick refused)%s'
                          'seta coop_loDbT "set %s 1"\t// %s client side of the same switch: what the heavy tab runs to light the tile (the server re-sends it)%s') % (NOTE, nl, TILECVAR, NOTE, nl) + t[m.end():]


def itemhandler(t):
    nl = nl_of(t)
    a = one(r'^(\t\t)case "models/weapons/shotgun\.tik":[ \t]*\r?\n\t\t\tend\("shotgun"\)', t)
    t = t[:a.start()] + '\t\tcase "%s": //%s%s' % (TIK, NOTE, nl) + t[a.start():]
    b = one(r'^(\t\t)case "models/weapons/shotgun\.tik":[ \t]*\r?\n\t\tcase "models/weapons/springfield\.tik":', t)
    return t[:b.start()] + '\t\tcase "%s": //%s%s' % (TIK, NOTE, nl) + t[b.start():]


def recoil(t):
    nl = nl_of(t)
    tik = open(os.path.join(ASSETS, 'models', 'weapons', STEM + '.tik'), encoding='latin-1').read()
    ks = set(re.findall(r'^\s*entry viewkick\s+(.*?)\s*$', tik, re.M))
    assert len(ks) == 1, ks
    v = ks.pop().replace('"', '').split()
    assert len(v) == 9, v
    host = one(r'^shotgun ([^\r\n]*)\r?\n', t).group(1).split()
    row = ' '.join(v + host[9:])                                         # + mindecay maxdecay as the pump gun's row
    assert not re.search(r'(?m)^%s\b' % STEM, t)
    names = [STEM] + ['%s_%s' % (STEM, FIN[k]) for k in sorted(FIN)]
    return t.rstrip('\r\n') + nl + '// %s double-barrel shotgun: its tik\'s own viewkick line, the base and every finish' % NOTE + nl + nl.join('%s %s' % (n, row) for n in sorted(names)) + nl


def urc(t):
    nl = nl_of(t)
    assert 'name "tile%s"' % ID not in t
    a, b = res_block(t, 'tile' + HOSTID)
    y_host = int(one(r'rect \d+ (\d+) \d+ \d+', t[a:b]).group(1))
    tab = one(r'enabledcvar "([^"]+)"', t[a:b]).group(1)
    assert tab == 'coop_loP3', tab
    # 2026-10-13 (fourth pass): the tile is the LAST one of the heavy tab, not the row under the trench gun. With the
    # master switch off the tile is hidden: in the middle of the list that left an empty row; at the end it leaves
    # nothing. No other tile moves (the checksum-locked urc changes by two blocks only).
    ys = []
    for nm in re.findall(r'name "tile(\d+)"', t):
        a, b = res_block(t, 'tile' + nm)
        blk = t[a:b]
        if one(r'enabledcvar "([^"]+)"', blk).group(1) != tab:
            continue
        ys.append(int(one(r'rect (\d+) (\d+) (\d+) (\d+)', blk).group(2)))
    assert len(ys) >= 13 and y_host in ys, ys
    y_new = max(ys) + ROW
    assert y_new <= 403, ('the heavy tab is longer than the longest tab of the menu', y_new)
    moved = []
    a, b = res_block(t, 'tile' + HOSTID)
    tile = t[a:b]
    m = one(r'rect (\d+) (\d+) (\d+) (\d+)', tile)
    tile = tile.replace(m.group(0), 'rect %s %d %s %s' % (m.group(1), y_new, m.group(3), m.group(4)))
    tile = tile.replace('"tile%s"' % HOSTID, '"tile%s"' % ID).replace('title "TRENCH GUN"', 'title "%s"' % NAME).replace('t%s.cfg' % HOSTID, 't%s.cfg' % ID).replace('req%s.cfg' % HOSTID, 'req%s.cfg' % ID)
    tile = tile.replace('enabledcvar "%s"' % tab, 'enabledcvar "%s"' % TILECVAR)
    a2, b2 = res_block(t, 'tilelk' + HOSTID)
    lk = t[a2:b2]
    m2 = one(r'rect (\d+) (\d+) (\d+) (\d+)', lk)
    lk = lk.replace(m2.group(0), 'rect %s %d %s %s' % (m2.group(1), y_new + 1, m2.group(3), m2.group(4))).replace('"tilelk%s"' % HOSTID, '"tilelk%s"' % ID).replace('coop_loLkV' + HOSTID, 'coop_loLkV' + ID)
    assert tile.count(ID) == 3 and NAME in tile and TILECVAR in tile and 'coop_loLkV' + ID in lk and '"tilelk%s"' % ID in lk
    cmt = ('// %s the double-barrel shotgun, its own tile, the last one of the heavy tab. Lit by %s (the heavy tab AND' % (NOTE, TILECVAR) + nl
           + '// the server\'s master switch coop_dbShotgun: ui/loadout/lktab3.cfg runs `vstr coop_loDbT`), not by coop_loP3.' + nl)
    return t[:b2] + nl + cmt + tile + nl + lk + t[b2:], moved, y_new


def lktab(t, k):
    nl = nl_of(t)
    assert 'coop_loLkV%s' % ID not in t and TILECVAR not in t
    ms = list(re.finditer(r'^set coop_loLkV7[0-9] 0[ \t]*\r?\n', t, re.M))
    assert ms
    m = ms[-1]
    t = t[:m.end()] + 'set coop_loLkV%s 0%s' % (ID, nl) + 'set %s 0%s' % (TILECVAR, nl) + t[m.end():]
    if k == 3:                              # the heavy tab
        assert re.search(r'^vstr coop_loLkA%s[ \t]*\r?$' % HOSTID, t, re.M), 'lktab3 is not the heavy tab any more'
        t = t.rstrip('\r\n') + nl + 'vstr coop_loLkA%s%s' % (ID, nl) + 'vstr coop_loDbT%s' % nl
    else:
        assert not re.search(r'^vstr coop_loLkA%s[ \t]*\r?$' % HOSTID, t, re.M)
    return t


def weaponclass(t):
    m = one(r'^([ \t]*)local\.classes\["models/weapons/shotgun\.tik"\] = "shotgun"[ \t]*\r?\n', t)
    return t[:m.end()] + '%slocal.classes["%s"] = "shotgun"\t//%s%s' % (m.group(1), TIK, NOTE, nl_of(t)) + t[m.end():]


def giveall(t):
    m = one(r'^weapon weapons/shotgun\.tik[ \t]*\r?\n', t)
    return t[:m.end()] + 'weapon weapons/%s.tik\t//%s%s' % (STEM, NOTE, nl_of(t)) + t[m.end():]


def tsv(t):
    nl = nl_of(t)
    rows = t.split(nl)
    ih = [i for i, l in enumerate(rows) if l.split('\t')[0] == HOSTID]
    assert len(ih) == 1 and not any(l.split('\t')[0] == ID for l in rows)
    c = rows[ih[0]].split('\t')
    k = c.index('12 GAUGE / PUMP-ACTION')
    assert c[1] == HOST_TIK and c[2] == HOST_TIK and c[k - 1] == 'TRENCH GUN' and c[k + 1:k + 8] == ['10', '1', '8', '9', '5', '5', 'shotgun'], c
    n = list(c)
    n[0] = ID; n[1] = TIK; n[2] = TIK
    n[k - 1] = NAME; n[k] = DESC
    n[k + 1:k + 5] = list(BARS)
    n[k + 5] = CLIP; n[k + 6] = CLIP                 # the round-count picture (clip_2.tga is new, staged) and the printed count
    n[3] = XFM
    while rows and rows[-1] == '':
        rows.pop()
    return nl.join(rows + ['\t'.join(n)]) + nl


XFM = os.environ.get('DBS_XFM', '0 0 0 1.00 0 90 180')      # the armory preview transform, dialled by eye (x y z scale pitch yaw roll)

SOURCES = (('hzm-mohaa-coop-mod/coop_mod/loadoutroster.scr', roster_case), ('hzm-mohaa-coop-mod/coop_mod/loadoutskins.scr', skins),
           ('hzm-mohaa-coop-mod/coop_mod/challenges.scr', challenges), ('hzm-mohaa-coop-mod/coop_mod/loadoutpick.scr', loadoutpick),
           ('hzm-mohaa-coop-mod/coop_defaults.cfg', defaults), ('hzm-mohaa-coop-mod/coop_mod/itemhandler.scr', itemhandler),
           ('hzm-mohaa-coop-mod/coop_mod/recoil_table.txt', recoil),
           ('hzm-mohaa-coop-mod/ubermode/get_player_weaponclass.scr', weaponclass), ('hzm-mohaa-coop-mod/global/giveall.scr', giveall),
           ('docs/tools/loadout_weapons.tsv', tsv))
SR_SEED = ('coop_mod/medals.scr', 'coop_mod/mvchal_gen.scr')


def seed(root):
    GEN.seed(root)
    shutil.copyfile(os.path.join(MOD, 'coop_defaults.cfg'), os.path.join(root, 'hzm-mohaa-coop-mod', 'coop_defaults.cfg'))


def edit_sources(root, log):
    for rel, fn in SOURCES:
        p = os.path.join(root, rel.replace('/', os.sep))
        wr(p, fn(rd(p)))
    p = os.path.join(root, 'hzm-mohaa-coop-mod', 'ui', 'coop_loadout.urc')
    t, moved, y = urc(rd(p)); wr(p, t)
    log.append('tile%s at y %d, the last tile of the heavy tab; tiles moved: %s' % (ID, y, ' '.join(moved) or 'none'))
    for k in range(6):
        p = os.path.join(root, 'hzm-mohaa-coop-mod', 'ui', 'loadout', 'lktab%d.cfg' % k)
        wr(p, lktab(rd(p), k))
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
    p = os.path.join(t, 'gen_service_record.py'); s = rd(p)
    old = 'os.chdir(r"C:\\mohaa-coop-dev\\hzm-mohaa-coop-mod")'
    if 'HZM_MOD' not in s:
        assert s.count(old) == 1
        s = s.replace(old, 'os.chdir(os.environ.get("HZM_MOD") or r"C:\\mohaa-coop-dev\\hzm-mohaa-coop-mod")   # HZM_MOD: a scratch / staged tree (as gen_loadout.py)')
        wr(p, s)
    if not new:
        return
    s = rd(p)
    nl = '\r\n' if '\r\n' in s else '\n'
    m = one(r'^    "models/weapons/bar_pabar\.tik": "[^"]*",[ \t]*\r?\n', s)
    s = s[:m.start()] + '    "%s": "%s",   # %s%s' % (TIK, REWARD_NAME, NOTE, nl) + s[m.start():]
    wr(p, s)


def run_gens(root, log, sr):
    env = dict(os.environ, HZM_MOD=os.path.join(root, 'hzm-mohaa-coop-mod'), PYTHONIOENCODING='utf-8')
    t = os.path.join(root, 'docs', 'tools')
    cmds = [['gen_loadout.py', 'build'], ['gen_skinbase.py'], ['armory_unlocks.py', '--emit'], ['gen_loadout.py', 'check']]
    if sr:
        cmds.append(['gen_service_record.py', 'build'])
    for cmd in cmds:
        r = subprocess.run([sys.executable, os.path.join(t, cmd[0])] + cmd[1:], cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        tail = (r.stdout.strip().splitlines() or ['(no output)'])[-1]
        log.append('%-28s exit %d  %s' % (' '.join(cmd), r.returncode, tail[:150]))
        assert r.returncode == 0, (cmd, r.stdout[-1500:], r.stderr[-2500:])
        for p in (r.stdout + r.stderr).splitlines():
            assert REPO.lower() + '\\hzm-mohaa-coop-mod' not in p.lower() and REPO.lower() + '\\docs' not in p.lower(), 'a generator named the REAL tree: ' + p


def main():
    sr = '--sr' in sys.argv
    stamp = time.strftime('%Y%m%d_%H%M%S')
    base, new = os.path.join(SCRATCH, stamp, 'base'), os.path.join(SCRATCH, stamp, 'new')
    log = []
    for root in (base, new):
        seed(root)
        if sr:
            for d in ('textures/hud/coop_sr', 'textures/mohmenu/coop_sr_reward', 'ui'):
                os.makedirs(os.path.join(root, 'hzm-mohaa-coop-mod', d.replace('/', os.sep)), exist_ok=True)
    patch_generators(base, False); log.append('--- BASE (mod tree as it is)'); run_gens(base, log, sr)
    patch_generators(new, True); log.append('--- NEW (sources edited, generators patched)'); edit_sources(new, log); run_gens(new, log, sr)
    B = dict(GEN.tree(base, 'hzm-mohaa-coop-mod'), **GEN.tree(base, 'docs'))
    N = dict(GEN.tree(new, 'hzm-mohaa-coop-mod'), **GEN.tree(new, 'docs'))
    real = lambda rel: os.path.join(REPO, rel.replace('/', os.sep))
    issr = lambda r: sr and (('/coop_sr' in r) or r.endswith('gen_sr_stamp.scr') or '/textures/' in r)
    drift = sorted(r for r in B if not issr(r) and os.path.isfile(real(r)) and open(real(r), 'rb').read() != B[r] and not r.endswith(('armory_unlocks.py', 'gen_service_record.py')))
    changed = sorted(r for r in N if r in B and N[r] != B[r])
    added = sorted(r for r in N if r not in B and not r.lower().startswith('hzm-mohaa-coop-mod/models/weapons/'))
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    gp, mp = [], []
    for r in changed + ['docs/tools/armory_unlocks.py']:
        if issr(r):
            continue                         # Service Record output: generated by build.ps1 at integration, test install only
        a = rd(real(r)); b = N[r].decode('latin-1')
        if a == b:
            continue
        (gp if r.startswith('docs/') else mp).extend(difflib.unified_diff(a.splitlines(True), b.splitlines(True), 'a/' + r, 'b/' + r, n=2))
    open(os.path.join(OUT, 'generators.patch'), 'w', newline='', encoding='latin-1').write(''.join(gp))
    open(os.path.join(OUT, 'armory_dbs.patch'), 'w', newline='', encoding='latin-1').write(''.join(mp))
    for r in added:
        if not issr(r):
            wr(os.path.join(OUT, 'new', r.replace('/', os.sep)), N[r].decode('latin-1'))
    z = zipfile.ZipFile(RELEASED)
    names = {n.lower(): n for n in z.namelist()}
    notrel, ovfiles, srfiles = [], [], []
    if os.path.isdir(OV):
        shutil.rmtree(OV)
    for r in changed + added:
        if not r.startswith('hzm-mohaa-coop-mod/'):
            continue
        g = r[len('hzm-mohaa-coop-mod/'):]
        if not g.lower().endswith(('.tga', '.png', '.jpg')):
            GEN.scan(g, N[r].decode('latin-1'))
        if issr(r):
            srfiles.append(g)
        elif r in changed:
            relb = z.read(names[g.lower()]) if g.lower() in names else None
            if relb != open(real(r), 'rb').read():
                notrel.append(g + (' (not in the released code pak)' if relb is None else ' (the mod tree is ahead of the release)'))
        d = os.path.join(OV, g.replace('/', os.sep))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        open(d, 'wb').write(N[r])
        ovfiles.append(g)
    rep = ['stage_armory_dbs.py %s   scratch: %s' % (stamp, os.path.join(SCRATCH, stamp))] + log
    rep += ['', 'generator drift already in the tree (BASE differs from the real file; NOT staged): %d' % len(drift)] + ['   ' + r for r in drift]
    rep += ['', 'changed by this weapon: %d' % len([r for r in changed if not issr(r)])] + ['   ' + r for r in changed if not issr(r)]
    rep += ['', 'new files: %d' % len([r for r in added if not issr(r)])] + ['   ' + r for r in added if not issr(r)]
    rep += ['', 'Service Record output that differs (test install only; build.ps1 regenerates it): %d' % len(srfiles)] + ['   ' + r for r in sorted(srfiles)]
    rep += ['', 'overlay files whose mod-tree original is NOT the released file (check before a harness run): %d' % len(notrel)] + ['   ' + r for r in notrel]
    open(os.path.join(OUT, 'report.txt'), 'w', newline='\n').write('\n'.join(rep) + '\n')
    wr(os.path.join(OV, 'MANIFEST.txt'), '\n'.join(sorted(ovfiles)) + '\n')
    print('\n'.join(rep))


if __name__ == '__main__':
    main()
