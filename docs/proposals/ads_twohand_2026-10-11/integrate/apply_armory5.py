"""apply_armory5.py - ADS rollout step 5: the G 43 Irons' ARMORY side applied to the REAL tree, the mod's own way.

The rifles lane staged this with rifles/wire/stage_armory_gen.py, which runs patched COPIES of the generators over a
scratch copy of the repo. This tool applies the SAME transforms (imported from that file, nothing retyped) to the real
files and runs the real generators - no generated file is written by hand:

  1. docs/tools: the lane's generator patches (armory_unlocks.py honours HZM_MOD, wire_mv2.py + variant_challenges.py
     know a gun that SHARES its host's variant challenges, gen_service_record.py REWARD_NAMES) and the TSV row
     (id 78; the scoped G43's ACC bar 0 -> 9)
  2. docs/tools/gen_loadout.py + wire_mv2.py: a weapon tik is looked for in the mod tree AND in
     docs/tools/assets/fixes (integration's own patch: a NEW gun's tiks ship in the fixes pak and are not in the mod
     tree - a new file under models/ would re-hash the 1.3 GB assets pak - so without this the generators would not
     arm its finish / variant buttons and `gen_loadout.py check`, which build.ps1 runs, would drift)
  3. the hand-authored sources in the mod tree (roster case, finishes, rank-2 unlock in xp.scr, itemhandler lists,
     recoil rows, armory tile, lktab cfgs, ammo HUD menu, AI alias, dev lists, weapon class) and the state-file row
  4. the generators, in the lane's order: gen_loadout build, wire_mv2, variant_challenges --emit, gen_loadout build,
     gen_skinbase, armory_unlocks --emit, gen_loadout check
  5. --verify <scratch new tree>: every file this changed is byte-identical to the lane tool's own scratch result

    python apply_armory5.py --dry        what would change (runs the lane tool into a scratch folder, touches nothing)
    python apply_armory5.py              apply (idempotent: a second run changes nothing)
Needs the step-5 fixes sources in place first (integrate_ads.py --steps 5): the generators read the new tiks there.
"""
import os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PROP = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(PROP)))
MOD = os.path.join(REPO, 'hzm-mohaa-coop-mod')
TOOLS = os.path.join(REPO, 'docs', 'tools')
sys.path.insert(0, os.path.join(PROP, 'rifles', 'wire'))
import stage_armory_gen as SG       # noqa: E402  the lane's transforms (read only)

rd, wr = SG.rd, SG.wr


def tik_fallback():
    """gen_loadout.py / wire_mv2.py: a weapon tik may live in the fixes sources instead of the mod tree"""
    p = os.path.join(TOOLS, 'gen_loadout.py'); s = rd(p)
    if '_tik_exists' not in s:
        nl = '\r\n' if '\r\n' in s else '\n'
        a = 'MOD = os.environ.get("HZM_MOD") or os.path.join(ROOT, "hzm-mohaa-coop-mod")' + nl
        assert s.count(a) == 1
        s = s.replace(a, a + nl.join([
            '# [ADS rollout step 5] a NEW gun\'s tiks ship in zzzzzzzzzz_coop_fixes.pk3 (docs/tools/assets/fixes) and are NOT in the',
            '# mod tree (a new file under models/ re-hashes the 1.3 GB assets pak): look in both places.',
            'FIXES_WEAPONS = os.path.join(ROOT, "docs", "tools", "assets", "fixes", "models", "weapons")',
            '', '',
            'def _tik_exists(name):',
            '    return os.path.exists(os.path.join(MOD, "models", "weapons", name)) or os.path.exists(os.path.join(FIXES_WEAPONS, name))',
            '']) + nl)
        a = ('        _vt = _os.path.join(MOD, "models", "weapons", "%s_%s.tik" % (_stem, _k))' + nl
             + '        finp.append("exec ui/loadout/finp%s_%d.cfg" % (w["id"], _i + 1) if _os.path.exists(_vt) else "")' + nl)
        assert s.count(a) == 1
        s = s.replace(a, '        finp.append("exec ui/loadout/finp%s_%d.cfg" % (w["id"], _i + 1) if _tik_exists("%s_%s.tik" % (_stem, _k)) else "")' + nl)
        a = ('            _vt = os.path.join(MOD, "models", "weapons",' + nl
             + '                               "%s_%s.tik" % (_stem2, _k))' + nl + '            if os.path.exists(_vt):' + nl)
        assert s.count(a) == 1
        s = s.replace(a, '            if _tik_exists("%s_%s.tik" % (_stem2, _k)):' + nl)
        wr(p, s)
    p = os.path.join(TOOLS, 'wire_mv2.py'); s = rd(p)
    if '_tik_path' not in s:
        nl = '\r\n' if '\r\n' in s else '\n'
        a = 'MOD = "hzm-mohaa-coop-mod/"' + nl
        assert s.count(a) == 1
        s = s.replace(a, a + nl.join([
            '# [ADS rollout step 5] a NEW gun\'s tiks ship in the fixes pak (docs/tools/assets/fixes), not in the mod tree',
            'FIXES = "docs/tools/assets/fixes/"', '', '',
            'def _tik_path(rel):',
            '    import os',
            '    return MOD + rel if os.path.exists(MOD + rel) else FIXES + rel',
            '']) + nl)
        a = 'io.open(MOD + "models/weapons/%s.tik" % stem, encoding="latin-1")'
        assert s.count(a) == 1
        s = s.replace(a, 'io.open(_tik_path("models/weapons/%s.tik" % stem), encoding="latin-1")')
        a = 'assert os.path.exists(MOD + vpath), "variant tik missing: " + vpath'
        assert s.count(a) == 1
        s = s.replace(a, 'assert os.path.exists(_tik_path(vpath)), "variant tik missing: " + vpath')
        wr(p, s)


def torso_row():
    p = os.path.join(MOD, 'coop_mod', 'player_torso.st'); s = rd(p)
    if '"G 43 Irons"' in s:
        return
    nl = '\r\n' if '\r\n' in s else '\n'
    m = SG.one(r'^([ \t]*)g43_reload([ \t]*): IS_WEAPON_ACTIVE "mainhand" "G 43"[ \t]*\r?\n', s)
    add = ('%s//[g43 irons 2026-10-12] the iron-sight G43: the G43\'s own torso reload (no hand-over of the gun)' % m.group(1) + nl
           + '%sg43_reload%s: IS_WEAPON_ACTIVE "mainhand" "G 43 Irons"' % (m.group(1), m.group(2)) + nl)
    wr(p, s[:m.end()] + add + s[m.end():])


def apply():
    done = '"%s"' % SG.STEM in rd(os.path.join(TOOLS, 'wire_mv2.py'))
    if not done:
        SG.patch_generators(REPO, True)
        for rel, fn in SG.SOURCES:
            p = os.path.join(REPO, rel.replace('/', os.sep))
            wr(p, fn(rd(p)))
        for k in range(6):
            p = os.path.join(MOD, 'ui', 'loadout', 'lktab%d.cfg' % k)
            wr(p, SG.OLD.lktab(rd(p), k == 0))
        hud = rd(os.path.join(MOD, 'ui', 'hud_ammo_G43.urc'))
        assert hud.count('"hud_ammo_G 43"') == 1
        wr(os.path.join(MOD, 'ui', 'hud_ammo_G43Irons.urc'), hud.replace('"hud_ammo_G 43"', '"hud_ammo_G 43 Irons"'))
    tik_fallback()
    torso_row()
    for f in os.listdir(os.path.join(PROP, 'rifles', 'assets', 'models', 'weapons')):
        if f.lower().startswith(SG.STEM) and f.lower().endswith('.tik'):
            assert os.path.isfile(os.path.join(TOOLS, 'assets', 'fixes', 'models', 'weapons', f)), 'run integrate_ads.py --steps 5 first: ' + f
            assert not os.path.isfile(os.path.join(MOD, 'models', 'weapons', f)), 'a new tik must not be in the mod tree: ' + f
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    env.pop('HZM_MOD', None)
    for cmd in (['gen_loadout.py', 'build'], ['wire_mv2.py'], ['variant_challenges.py', '--emit'], ['gen_loadout.py', 'build'], ['gen_skinbase.py'],
                ['armory_unlocks.py', '--emit'], ['gen_loadout.py', 'check']):
        r = subprocess.run([sys.executable, os.path.join(TOOLS, cmd[0])] + cmd[1:], cwd=REPO, env=env, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        print('%-28s exit %d  %s' % (' '.join(cmd), r.returncode, ((r.stdout.strip().splitlines() or ['(no output)'])[-1])[:150]))
        assert r.returncode == 0, (cmd, r.stdout[-1500:], r.stderr[-1500:])


def verify(newroot):
    """every file of the lane tool's scratch NEW tree (generated + edited) against the real tree"""
    bad = n = 0
    for sub in ('hzm-mohaa-coop-mod', 'docs'):
        for dp, _dn, fn in os.walk(os.path.join(newroot, sub)):
            for f in fn:
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, newroot).replace(os.sep, '/')
                if rel.lower().startswith('hzm-mohaa-coop-mod/models/weapons/'):
                    continue
                real = os.path.join(REPO, rel.replace('/', os.sep))
                n += 1
                a = open(p, 'rb').read()
                b = open(real, 'rb').read() if os.path.isfile(real) else None
                if a != b:
                    # the two generators carry the integration's tik fallback on top of the lane's patch
                    if rel in ('docs/tools/gen_loadout.py', 'docs/tools/wire_mv2.py', 'docs/tools/armory_unlocks.py'):
                        print('  (generator, differs by the integration patch / root override: %s)' % rel)
                        continue
                    bad += 1
                    print('  DIFFERS from the lane tool\'s result: %s' % rel)
    print('verify: %d files compared with %s, %d differ' % (n, newroot, bad))
    return bad


if __name__ == '__main__':
    if '--dry' in sys.argv:
        scratch = os.path.join(os.environ.get('TEMP', '.'), 'integ_ads_cache', 'armgen5')
        SG.OUT, SG.OV, SG.SCRATCH = os.path.join(scratch, 'gen'), os.path.join(scratch, 'ov'), os.path.join(scratch, 'scratch')
        SG.main()
        sys.exit(0)
    if '--verify' in sys.argv:
        sys.exit(1 if verify(sys.argv[sys.argv.index('--verify') + 1]) else 0)
    apply()
