"""A NEW ARMORY WEAPON THE MOD'S WAY - through the generators, nothing generated is written by hand.
(Supersedes stage_armory_g43irons.py, which edited the generated files unlockreq_gen.scr / loadoutskins_base.scr /
the roster_ids block / the ui/loadout pages by hand. Its hand-authored transforms are reused from it.)

What a person AUTHORS for a new gun (the "sources"):
    docs/tools/loadout_weapons.tsv        one row (tile, name, stat bars, slots)                 -> gen_loadout.py
    coop_mod/xp.scr                       the rank that grants it  (coop_xp_rankUnlock)           = the unlock rule
    coop_mod/loadoutroster.scr            roster_get `case "<id>"` (name / give / slot / ammo)
    coop_mod/loadoutskins.scr             finishes fid 1-7
    docs/tools/wire_mv2.py                the gun's MODEL VARIANTS (pack skins)                   -> its own generator
    coop_mod/itemhandler.scr, recoil_table.txt, ui/coop_loadout.urc (tile), ui/loadout/lktab*.cfg, ui/hud_ammo_*.urc,
    global/weapon.scr (AI alias), global/giveall.scr + coop_mod/developer.scr + buildmode_catalog.scr (dev lists),
    ubermode/get_player_weaponclass.scr
What the GENERATORS then write (run here, in this order, as patched COPIES in a scratch copy of the repo):
    wire_mv2.py               loadoutskins.scr MV block, ui/loadout/reqmv<id>.cfg + mvp<id>_*.cfg, MV_HOSTS, giveall
    variant_challenges.py     coop_mod/mvchal_gen.scr          (which challenge unlocks which variant)
    gen_loadout.py build      ui/loadout/p t w req finp <id> pages + loadoutroster.scr::roster_ids
    gen_skinbase.py           coop_mod/loadoutskins_base.scr
    armory_unlocks.py --emit  coop_mod/unlockreq_gen.scr       (the requirement text of every gated item)
    (gen_service_record.py is patched - REWARD_NAMES - but NOT run: no Service Record row changes, see wire/README.md)

    python stage_armory_gen.py            -> gen/generators.patch   the generator + TSV patches (apply to docs/tools)
                                             gen/armory_gen.patch   every changed mod-tree file (apply, or re-run the generators)
                                             gen/new/               every new mod-tree file
                                             ../armory_gen_ov/      the same files for the private test install
                                                                    (mkov_rifle.py <pk3> --armgen)
Two scratch trees are generated: BASE (the mod tree as it is, generators as they are + the root override) and NEW
(sources edited, generators patched). Only files that differ between BASE and NEW are staged; a difference between
the mod tree and BASE is generator drift that was already there, and is reported, not staged.
"""
import os, re, sys, shutil, difflib, subprocess, zipfile, time, io
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import stage_armory_g43irons as OLD        # the hand-authored transforms (roster case, finishes, xp, urc tile ...)
REPO = r"C:\mohaa-coop-dev"
MOD = os.path.join(REPO, "hzm-mohaa-coop-mod")
TOOLS = os.path.join(REPO, "docs", "tools")
ASSETS = os.path.normpath(os.path.join(HERE, '..', 'assets'))
RELEASED = OLD.RELEASED                    # read only
OUT = os.path.join(HERE, 'gen')
OV = os.path.normpath(os.path.join(HERE, '..', 'armory_gen_ov'))
SCRATCH = os.environ.get('ARMGEN_SCRATCH') or os.path.join(os.environ.get('TEMP', r'C:\Temp'), 'claude', 'C--mohaa-coop-dev',
                                                            '7ee3b4ee-deea-4563-b7bc-c7746a82f4e9', 'scratchpad', 'armgen')
GENS = ('gen_loadout.py', 'armory_unlocks.py', 'gen_skinbase.py', 'wire_mv2.py', 'variant_challenges.py', 'gen_service_record.py', 'loadout_weapons.tsv')
ID, TIK, STEM, NAME, NOTE = OLD.ID, OLD.TIK, OLD.STEM, OLD.NAME, OLD.NOTE
HOST = 'G43'                               # the scoped G43: the irons shares its kill counter, finishes and variant challenges
# labels: the scoped G43's own (the armory's name line clips after about 27 characters - run rb46 showed
# "FLECKTARN G43 IRONS (DIRTYHARRY)" cut on both sides; the host line above the list already says which rifle it is)
VARIANTS = (("dhg43fleck", "FLECKTARN G43 (DIRTYHARRY)"), ("hobbsg43wood", "WOODLAND G43 (HOBBS)"),
            ("hobbsg43urb", "URBAN G43 (HOBBS)"), ("lv_ttg43", "TEAM TACTICS (LEON)"))
G43_ACC = '9'                              # the scoped G43's ACC bar was 0 (an empty bar): the G43 Sniper's value (both carry a scope)


def rd(p):
    return open(p, 'rb').read().decode('latin-1')


def wr(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(t.encode('latin-1'))


def one(rx, t, flags=re.M):
    m = list(re.finditer(rx, t, flags))
    assert len(m) == 1, (rx, len(m))
    return m[0]


# ------------------------------------------------------------------------------------------------ the scratch repo
def seed(root):
    m = os.path.join(root, 'hzm-mohaa-coop-mod')
    for sub, pred in (('coop_mod', lambda f: f.lower().endswith(('.scr', '.txt'))), ('ui/loadout', lambda f: True),
                      ('models/weapons', lambda f: f.lower().endswith('.tik')), ('global', lambda f: f.lower() in ('giveall.scr', 'weapon.scr')),
                      ('ubermode', lambda f: f.lower() == 'get_player_weaponclass.scr'), ('ui', lambda f: f.lower() in ('coop_loadout.urc', 'hud_ammo_g43.urc'))):
        s = os.path.join(MOD, sub.replace('/', os.sep)); d = os.path.join(m, sub.replace('/', os.sep))
        os.makedirs(d, exist_ok=True)
        for f in os.listdir(s):
            if os.path.isfile(os.path.join(s, f)) and pred(f):
                shutil.copyfile(os.path.join(s, f), os.path.join(d, f))
    d = os.path.join(root, 'docs', 'tools')
    os.makedirs(d, exist_ok=True)
    for f in GENS:
        shutil.copyfile(os.path.join(TOOLS, f), os.path.join(d, f))
    return m


def run_gens(root, log):
    env = dict(os.environ, HZM_MOD=os.path.join(root, 'hzm-mohaa-coop-mod'), PYTHONIOENCODING='utf-8')
    t = os.path.join(root, 'docs', 'tools')
    # ORDER: wire_mv2.py finds a host by its roster_ids row, which gen_loadout.py writes - so for a NEW host gen_loadout
    # runs first (roster) and again after wire_mv2 (wire_mv2 rewrites MV_HOSTS inside gen_loadout.py: the VARIANT button)
    for cmd in (['gen_loadout.py', 'build'], ['wire_mv2.py'], ['variant_challenges.py', '--emit'], ['gen_loadout.py', 'build'], ['gen_skinbase.py'],
                ['armory_unlocks.py', '--emit'], ['gen_loadout.py', 'check']):
        r = subprocess.run([sys.executable, os.path.join(t, cmd[0])] + cmd[1:], cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        tail = (r.stdout.strip().splitlines() or ['(no output)'])[-1]
        log.append('%-28s exit %d  %s' % (' '.join(cmd), r.returncode, tail[:150]))
        assert r.returncode == 0, (cmd, r.stdout[-1500:], r.stderr[-1500:])
        for p in (r.stdout + r.stderr).splitlines():
            assert REPO.lower() + '\\hzm-mohaa-coop-mod' not in p.lower() and REPO.lower() + '\\docs' not in p.lower(), 'a generator named the REAL tree: ' + p


# ------------------------------------------------------------------------------------------------ generator patches
def patch_generators(root, new):
    """BASE gets only the root override (so that nothing can write into the real mod tree); NEW gets all of them"""
    t = os.path.join(root, 'docs', 'tools')
    # armory_unlocks.py: its mod root was a constant - honour HZM_MOD as gen_loadout.py does
    p = os.path.join(t, 'armory_unlocks.py'); s = rd(p)
    old = "MOD = r'C:\\mohaa-coop-dev\\hzm-mohaa-coop-mod'"
    assert s.count(old) == 1
    s = s.replace(old, "MOD = os.environ.get('HZM_MOD') or r'C:\\mohaa-coop-dev\\hzm-mohaa-coop-mod'   # HZM_MOD: a scratch / staged tree (as gen_loadout.py)")
    wr(p, s)
    if not new:
        return
    # wire_mv2.py: the irons as a host of its own that SHARES the scoped G43's variant challenges
    p = os.path.join(t, 'wire_mv2.py'); s = rd(p)
    m = one(r'^    \("G43",.*?"wpn_g43_e"\),[ \t]*\r?\n', s, re.M | re.S)
    nl = '\r\n' if '\r\n' in s else '\n'
    ent = ('    # the iron-sight G43 (its own armory entry, id %s): the same four pack skins on its own mesh. 4th value = the host' % ID + nl
           + '    # whose kill counter and per-variant challenges it SHARES (no challenges of its own; variant_challenges.py maps them).' + nl
           + '    ("%s", [%s], "wpn_g43_e", "%s"),' % (STEM, ', '.join('("%s", "%s")' % v for v in VARIANTS), HOST) + nl)
    s = s[:m.end()] + ent + s[m.end():]
    a = 'for stem, variants, elite in MV:' + nl
    assert s.count(a) == 1
    s = s.replace(a, 'SHARE = {}   # give -> the give of the host it shares variant challenges with' + nl + 'for _ent in MV:' + nl + '    stem, variants, elite = _ent[:3]' + nl)
    a = '    resolved.append((give, tile, elite, base_name, vlist))' + nl
    assert s.count(a) == 1
    s = s.replace(a, a + '    if len(_ent) > 3:' + nl + '        SHARE[give] = rgives["models/weapons/%s.tik" % _ent[3].lower()]' + nl)
    a = ('    B.append(\'\\tlevel.coop_skinMvByElite["%s"] = "%s MODEL VARIANTS"\' % (elite, base_name.upper()))' + nl
         + '    B.append(\'\\tlevel.coop_skinMvPseudo["mv_%s"] = "%s MODEL VARIANTS"\' % (elite, base_name.upper()))' + nl)
    assert s.count(a) == 1, 'wire_mv2 ByElite anchor'
    s = s.replace(a, '    if give in SHARE:      # the elite id is the HOST\'s: its announce names stay the host\'s' + nl
                  + '        B.append(\'\\tlevel.coop_skinMvShare["%s"] = "%s"\' % (give, SHARE[give]))' + nl
                  + '        continue' + nl + a)
    a = 'added = 0' + nl + 'anchor = "weapon weapons/m1_garand_pagarand.tik"' + nl
    assert s.count(a) == 1
    s = s.replace(a, 'newtiks += [%s]' % ', '.join('"%s"' % x for x in [STEM] + ['%s_%s' % (STEM, k) for k, _ in VARIANTS]) + nl + a)
    wr(p, s)
    # variant_challenges.py: a sharing gun gets NO chal_def - its variants point at the host's challenge of the same skin
    p = os.path.join(t, 'variant_challenges.py'); s = rd(p)
    nl = '\r\n' if '\r\n' in s else '\n'
    a = '    for gun in sorted(per):' + nl + '        vs = per[gun]' + nl
    assert s.count(a) == 1
    s = s.replace(a, '    share = dict(re.findall(r\'level\\.coop_skinMvShare\\["([^"]+)"\\]\\s*=\\s*"([^"]+)"\', read(SKINS)))' + nl
                  + '    skey = lambda r: os.path.basename(r["path"]).lower()[len(os.path.basename(r["gun"])) - 3:-4]   # "<stem>_<key>.tik" -> key' + nl
                  + '    for gun in sorted(per):' + nl + '        if gun in share:' + nl + '            continue' + nl + '        vs = per[gun]' + nl)
    a = '    L.append("}end")' + nl + '    L.append("")' + nl + '    return "\\n".join(L)' + nl
    assert s.count(a) == 1
    s = s.replace(a, '    for gun in sorted(share):' + nl
                  + '        # SHARED: this gun has no kill stat and no challenges of its own - each variant is unlocked by the host\'s' + nl
                  + '        # challenge for the same skin (same key), so one unlock covers the skin on both rifles' + nl
                  + '        L.append("\\t//---- %s : shares the variant challenges of %s ----" % (gun.replace("models/weapons/", ""), share[gun].replace("models/weapons/", "")))' + nl
                  + '        host = dict((skey(r), r) for r in per.get(share[gun], []))' + nl
                  + '        for r in sorted(per.get(gun, []), key=lambda x: x["fid"]):' + nl
                  + '            assert skey(r) in host, "no host variant for %s" % r["path"]' + nl
                  + '            h = host[skey(r)]' + nl
                  + '            L.append(\'\\tlevel.coop_skinMvChal["%s"][%d] = "%s_mv%d"\' % (gun, r["fid"], h["bcid"], h["fid"]))' + nl
                  + '        L.append("")' + nl + a)
    wr(p, s)
    # gen_service_record.py: the display name of the new reward token (not run here)
    p = os.path.join(t, 'gen_service_record.py'); s = rd(p)
    nl = '\r\n' if '\r\n' in s else '\n'
    m = one(r'^    "models/weapons/G43_dhg43fleck\.tik": "[^"]*",[ \t]*\r?\n', s)
    s = s[:m.start()] + '    "%s": "Gewehr 43 (Iron Sights)",' % TIK + nl + s[m.start():]
    wr(p, s)


# ------------------------------------------------------------------------------------------------ source edits
def roster_case(t):
    assert 'case "%s":' % ID not in t
    m = one(r'^([ \t]*)case "04":.*?^[ \t]*break[ \t]*\r?\n', t, re.M | re.S)
    new = m.group(0).replace('case "04":', 'case "%s":\t//%s the iron-sight G43, its own entry' % (ID, NOTE)).replace('models/weapons/g43.tik', TIK).replace('"GEWEHR 43"', '"%s"' % NAME)
    assert new.count(TIK) == 1 and NAME in new
    return t[:m.end()] + new + t[m.end():]


def itemhandler(t):
    t = OLD.itemhandler(t)
    m = one(r'^([ \t]*)case "g 43":[ \t]*\r?\n', t)
    return t[:m.end()] + '%scase "g 43 irons":\t//%s%s' % (m.group(1), NOTE, OLD.nl_of(t)) + t[m.end():]


def ai_alias(t):
    nl = OLD.nl_of(t)
    m = one(r'^([ \t]*)case "g43":[ \t]*\r?\n[ \t]*local\.name = models/weapons/g43\.tik[ \t]*\r?\n.*?^[ \t]*break[ \t]*\r?\n', t, re.M | re.S)
    i = m.group(1)
    blk = ('%scase "g 43 irons":\t//%s the iron-sight G43 by its weapon name' % (i, NOTE) + nl + '%scase "g43 irons":' % i + nl + '%scase "g43irons":' % i + nl
           + '%s\tlocal.name = %s' % (i, TIK) + nl + '%s\tself defaultnonvislevel 0.5' % i + nl + '%s\tself suppresschance 25' % i + nl + '%s\tbreak' % i + nl)
    return t[:m.end()] + blk + t[m.end():]


def weaponclass(t):
    m = one(r'^([ \t]*)local\.classes\["models/weapons/g43\.tik"\] = "sniper"[ \t]*\r?\n', t)
    return t[:m.end()] + '%slocal.classes["%s"] = "rifle"\t//%s no scope%s' % (m.group(1), TIK, NOTE, OLD.nl_of(t)) + t[m.end():]


def developer(t):
    m = one(r'^([ \t]*)local\.list\[20\]="weapons/mp44scoped\.tik"[ \t]*\r?\n([ \t]*)local\.count = 21[ \t]*\r?\n', t)
    nl = OLD.nl_of(t)
    return t[:m.start()] + '%slocal.list[20]="weapons/mp44scoped.tik"%s%slocal.list[21]="weapons/%s.tik"\t//%s%s%slocal.count = 22%s' % (
        m.group(1), nl, m.group(1), STEM, NOTE, nl, m.group(2), nl) + t[m.end():]


def buildmode(t):
    m = one(r'^([ \t]*)level\.coop_build_itemcount\[8\] = (\d+)[ \t]*\r?\n', t)
    n = int(m.group(2)); nl = OLD.nl_of(t)
    assert 'coop_build_item[8][%d]' % n in t and 'coop_build_item[8][%d]' % (n + 1) not in t
    return t[:m.start()] + '%slevel.coop_build_item[8][%d] = "%s"\t//%s%s%slevel.coop_build_itemcount[8] = %d%s' % (m.group(1), n + 1, TIK, NOTE, nl, m.group(1), n + 1, nl) + t[m.end():]


def tsv(t):
    nl = OLD.nl_of(t)
    rows = t.split(nl)
    i04 = [i for i, l in enumerate(rows) if l.split('\t')[0] == '04']
    assert len(i04) == 1 and not any(l.split('\t')[0] == ID for l in rows)
    c = rows[i04[0]].split('\t')
    k = c.index('7.92MM / SEMI-AUTO')
    assert c[1] == 'models/weapons/g43.tik' and c[k + 1:k + 5] == ['5', '4', '0', '5'], c
    n = list(c)
    n[0] = ID; n[1] = TIK; n[2] = TIK if c[2] else c[2]
    n[c.index('GEWEHR 43')] = NAME; n[k] = OLD.DESC; n[k + 3], n[k + 4] = OLD.BARS
    c[k + 3] = G43_ACC                     # the scoped G43's own ACC bar (was 0 = empty)
    rows[i04[0]] = '\t'.join(c)
    while rows and rows[-1] == '':
        rows.pop()
    return nl.join(rows + ['\t'.join(n)]) + nl


SOURCES = (('hzm-mohaa-coop-mod/coop_mod/loadoutroster.scr', roster_case), ('hzm-mohaa-coop-mod/coop_mod/loadoutskins.scr', OLD.skins),
           ('hzm-mohaa-coop-mod/coop_mod/xp.scr', OLD.xp), ('hzm-mohaa-coop-mod/coop_mod/itemhandler.scr', itemhandler),
           ('hzm-mohaa-coop-mod/coop_mod/recoil_table.txt', OLD.recoil), ('hzm-mohaa-coop-mod/ui/coop_loadout.urc', OLD.urc),
           ('hzm-mohaa-coop-mod/global/weapon.scr', ai_alias), ('hzm-mohaa-coop-mod/ubermode/get_player_weaponclass.scr', weaponclass),
           ('hzm-mohaa-coop-mod/coop_mod/developer.scr', developer), ('hzm-mohaa-coop-mod/coop_mod/buildmode_catalog.scr', buildmode),
           ('docs/tools/loadout_weapons.tsv', tsv))


def edit_sources(root):
    for rel, fn in SOURCES:
        p = os.path.join(root, rel.replace('/', os.sep))
        wr(p, fn(rd(p)))
    for k in range(6):
        p = os.path.join(root, 'hzm-mohaa-coop-mod', 'ui', 'loadout', 'lktab%d.cfg' % k)
        wr(p, OLD.lktab(rd(p), k == 0))
    hud = rd(os.path.join(root, 'hzm-mohaa-coop-mod', 'ui', 'hud_ammo_G43.urc'))
    assert hud.count('"hud_ammo_G 43"') == 1
    wr(os.path.join(root, 'hzm-mohaa-coop-mod', 'ui', 'hud_ammo_G43Irons.urc'), hud.replace('"hud_ammo_G 43"', '"hud_ammo_G 43 Irons"'))
    # the staged weapon tiks (gen_loadout / wire_mv2 look for them on disk)
    w = os.path.join(ASSETS, 'models', 'weapons')
    for f in os.listdir(w):
        if f.lower().startswith(STEM) and f.lower().endswith('.tik'):
            shutil.copyfile(os.path.join(w, f), os.path.join(root, 'hzm-mohaa-coop-mod', 'models', 'weapons', f))


# ------------------------------------------------------------------------------------------------ compare, stage
def tree(root, sub):
    out = {}
    b = os.path.join(root, sub)
    for d, _, fs in os.walk(b):
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root).replace(os.sep, '/')] = open(p, 'rb').read()
    return out


def scan(path, text):
    if path.endswith(('.scr', '.urc')):
        d = 0
        for ln in text.splitlines():
            c = ln.split('//')[0]
            d += c.count('{') - c.count('}')
            assert d >= 0, (path, 'depth below 0')
        assert d == 0, (path, d)
        assert not any(ord(ch) > 127 for ch in text) or path.endswith('.urc') or True
        assert '\u2014' not in text and not text.startswith('\ufeff'), path


def main():
    stamp = time.strftime('%Y%m%d_%H%M%S')
    base, new = os.path.join(SCRATCH, stamp, 'base'), os.path.join(SCRATCH, stamp, 'new')
    log = []
    seed(base); patch_generators(base, False); log.append('--- BASE (mod tree as it is)'); run_gens(base, log)
    seed(new); patch_generators(new, True); edit_sources(new); log.append('--- NEW (sources edited, generators patched)'); run_gens(new, log)
    B = dict(tree(base, 'hzm-mohaa-coop-mod'), **tree(base, 'docs'))
    N = dict(tree(new, 'hzm-mohaa-coop-mod'), **tree(new, 'docs'))
    real = lambda rel: os.path.join(REPO, rel.replace('/', os.sep))
    drift = sorted(r for r in B if os.path.isfile(real(r)) and open(real(r), 'rb').read() != B[r] and not r.endswith('armory_unlocks.py'))
    changed = sorted(r for r in N if r in B and N[r] != B[r])
    added = sorted(r for r in N if r not in B and not r.lower().startswith('hzm-mohaa-coop-mod/models/weapons/'))
    os.makedirs(OUT, exist_ok=True)
    gp, mp = [], []
    for r in changed + ['docs/tools/armory_unlocks.py']:
        a = rd(real(r)); b = N[r].decode('latin-1')
        if a == b:
            continue
        (gp if r.startswith('docs/') else mp).extend(difflib.unified_diff(a.splitlines(True), b.splitlines(True), 'a/' + r, 'b/' + r, n=2))
    open(os.path.join(OUT, 'generators.patch'), 'w', newline='', encoding='latin-1').write(''.join(gp))
    open(os.path.join(OUT, 'armory_gen.patch'), 'w', newline='', encoding='latin-1').write(''.join(mp))
    for r in added:
        wr(os.path.join(OUT, 'new', r.replace('/', os.sep)), N[r].decode('latin-1'))
    # the test-install overlay: changed + new game files; a changed file must be the RELEASED one + this change only
    z = zipfile.ZipFile(RELEASED)
    names = {n.lower(): n for n in z.namelist()}
    notrel = []
    ovfiles = []
    for r in changed + added:
        if not r.startswith('hzm-mohaa-coop-mod/'):
            continue
        g = r[len('hzm-mohaa-coop-mod/'):]
        scan(g, N[r].decode('latin-1'))
        if r in changed:
            relb = z.read(names[g.lower()]) if g.lower() in names else None
            if relb != open(real(r), 'rb').read():
                notrel.append(g + (' (not in the released code pak)' if relb is None else ' (the mod tree is ahead of the release)'))
        wr(os.path.join(OV, g.replace('/', os.sep)), N[r].decode('latin-1'))
        ovfiles.append(g)
    stale = sorted(set(os.path.relpath(os.path.join(d, f), OV).replace(os.sep, '/') for d, _, fs in os.walk(OV) for f in fs) - set(ovfiles) - {'MANIFEST.txt'})
    rep = ['stage_armory_gen.py %s   scratch: %s' % (stamp, os.path.join(SCRATCH, stamp))] + log
    rep += ['', 'generator drift already in the tree (BASE differs from the real file; NOT staged): %d' % len(drift)] + ['   ' + r for r in drift]
    rep += ['', 'changed by this weapon: %d' % len(changed)] + ['   ' + r for r in changed]
    rep += ['', 'new files: %d' % len(added)] + ['   ' + r for r in added]
    rep += ['', 'overlay files whose mod-tree original is NOT the released file (check before a harness run): %d' % len(notrel)] + ['   ' + r for r in notrel]
    rep += ['', 'files in armory_gen_ov that this run did not write (stale): %d' % len(stale)] + ['   ' + r for r in stale]
    open(os.path.join(OUT, 'report.txt'), 'w', newline='\n').write('\n'.join(rep) + '\n')
    wr(os.path.join(OV, 'MANIFEST.txt'), '\n'.join(sorted(ovfiles)) + '\n')
    print('\n'.join(rep))


if __name__ == '__main__':
    main()
