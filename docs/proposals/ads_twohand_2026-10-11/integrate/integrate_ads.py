"""integrate_ads.py - the aimed-reload (ADS) rollout: lane folders -> docs/tools/assets/fixes + fixes_manifest.json.

    python integrate_ads.py --dry-run [--steps 1,2,3]    list every file: entry kind, gun, action - writes nothing
    python integrate_ads.py [--steps 1,2,3]              write the fixes sources + manifest (idempotent)
    python integrate_ads.py --mod-patches [--steps ...]  ALSO run the script-side patches on the mod tree (code pak)
    python integrate_ads.py --reset                      BACK OUT: docs/tools/assets/fixes + manifest back to the released
                                                         revision (intlib.RELEASED_REV); files the rollout added are MOVED
                                                         to <scratch>/integ_backout_<time>/ (never deleted). Then re-run
                                                         with the steps that stay, and rebuild the pak. A mod-tree patch
                                                         (op P) is backed out with `git revert` in the mod repo.

ONE TABLE PER STEP (step1 / step2 / step3 below; a later step = one more function + one line in STEPS - nothing in the
earlier steps has to change). A step is a list of ops:
  F(lane, rel, gun, dst)       a staged file copied as it is                     (clips, meshes, shaders, sounds ...);
                               `dst` = shipped under ANOTHER game path (a clip whose released file must stay as it is
                               for guns that are not part of the rollout); `tga_flag` = a .tga whose header says
                               "top-down": the engine ignores the flag and warns on every load, so the flag bit is
                               cleared (one header byte; the pixels and the picture the engine shows are unchanged)
  T(lane, rel, gun, allow, strip)  a staged weapon tik: copied as it is, after proving it is the released tik plus
                               lane lines only - a released line may be missing only if it matches `allow`;
                               `strip` = (first-line regex, last-line regex) of a MARKED lane block that is cut out
                               because it belongs to work that is not part of the rollout (its rows would point at
                               clips that do not ship)
  R(rowfile, lane, rows, gun)  ROW MERGE into the fixes copy of an fps_anims file: the named rows are taken line by
                               line from the lane's copy (replace the row if it exists, else append before the closing
                               brace). The lane file is never copied wholesale - it also carries rows of unfinished guns.
  RL(rowfile, row, line, gun)  one row written by the integration itself
  C(gun, weapon name, tiks, skip)  coverage proof (user rule): every mod-tree tik whose weapon name is `name` or
                               `name (...)` must be in `tiks`; `skip` = tiks of that name knowingly left as released
  P(tool, gun)                 a mod-tree patch tool of a lane, run with the mod tree as its argument (--mod-patches)
  M(rel, lane, base, gun)      3-WAY MERGE into a fixes source (git merge-file): `theirs` = the lane's copy, which is a
                               SNAPSHOT of a shared table at an older revision; `base` = that revision -
                               ('docs', rev) = docs/tools/assets/fixes/<rel> at a docs commit, ('mod', rev) = the mod
                               tree's file at a mod commit; `ours` = the same file at PASS1_REV (a fixes source) or
                               the CURRENT mod-tree copy (which then becomes the pinned base). A conflict fails the run.
  G(rel, lane, src, rev, gun)  the same 3-way merge ONTO A MOD-TREE FILE of the code pak (coop_mod/...): written only
                               with --mod-patches; the dry run says whether the mod tree already carries it
A lane name that starts with `@` is a folder beside the lane folders that holds game paths directly (`@ship` = the
pistol lane's frozen ship cut), not `<lane>/assets/`.
Entry kinds (docs/tools/gen_fixes_pak.py): a path already in the manifest keeps its entry; a path the mod tree carries
= `base` (mod-tree copy saved under docs/tools/assets/fixes_base, pinned by md5 + mtime ticks); a path only a
retail / third-party pak carries = `base_pak`; a path nothing carries = `new`. A path that a pak sorting ABOVE the
fixes pak also carries is refused (the override would be dead - the lifted BAR skin, see step1).
After a run: python docs/tools/gen_fixes_pak.py restore / build / check, then
             git -C hzm-mohaa-coop-mod checkout -- models/player/base/
"""
import json, os, re, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intlib as L

MARK = '\t//===================== HZM coop ADS rollout (integrate_ads.py; rows taken from the lane folders) ====================='


def F(lane, rel, gun, dst=None, tga_flag=False):
    return dict(op='F', lane=lane, rel=rel, gun=gun, dst=dst, tga_flag=tga_flag)


def T(lane, rel, gun, allow=(), strip=None):
    return dict(op='T', lane=lane, rel=rel, gun=gun, allow=allow, strip=strip)


def R(rowfile, lane, rows, gun):
    return dict(op='R', rel=rowfile, lane=lane, rows=rows, gun=gun)


def RL(rowfile, row, line, gun):
    return dict(op='RL', rel=rowfile, row=row, line=line, gun=gun)


def C(gun, name, tiks, skip=()):
    return dict(op='C', gun=gun, name=name, tiks=tiks, skip=skip)


def P(lane, tool, gun):
    return dict(op='P', lane=lane, tool=tool, gun=gun)


def M(rel, lane, base, gun, src=None):
    return dict(op='M', rel=rel, lane=lane, base=base, gun=gun, src=src or rel)


def G(rel, lane, src, rev, gun):
    return dict(op='G', rel=rel, lane=lane, src=src, rev=rev, gun=gun)


# Steps that are SHIPPED (pass 1, on the user's install): their lanes go on working in the same folders (the rifles lane
# rewrote its staged Enfield tiks for the aimed reload the day after), so a re-run must not take a changed lane file -
# the copy in docs/tools/assets/fixes is kept and the line says so (bug-3833). After a --reset these steps can only be
# rebuilt from the docs commit (git show PASS1_REV), not from the lane folders.
FROZEN = (1, 2, 3)
PASS1_REV = '76f7b15'       # docs commit of integration pass 1 (steps 1-3) = what is on the user's install


VM = 'models/human/animation/viewmodel/'
W = 'models/weapons/'
FINISH = ('bloody', 'blued', 'camo_desert', 'camo_winter', 'camo_woodland', 'chrome', 'gold')


def step1():
    """HEAVY lane: BAR (+ M1918 Classic / A1 / A2, Pacific), StG 44 (+ strapped, finishes), DP-28, pump shotgun.
    NOT shipped from the lane folder: FG 42 Irons (tiks, mesh, shader, clips, its coopr row), the Vickers / Breda aim
    poses (belt-fed lane work, unfinished), the lifted BAR skin + the magazine prop toned to it (textures/models/
    weapons/bar/*: S93_bar.dds is carried by zzzzzzzzzz_coop_hd_m3l1a.pk3, which sorts ABOVE the fixes pak and is off
    limits - the BAR ships with its released skin), coop_mod/player_Torso.st (the lane's test copy: the break-off
    goes in as a PATCH, op P)."""
    h = 'heavy'
    bar = ['bar'] + ['bar_' + s for s in ('bar1918a', 'bar1918a1', 'bar1918a2', 'pabar') + FINISH]
    mp44 = ['mp44'] + ['mp44_' + s for s in ('dhstg44ss', 'guanmp44', 'lv_ttmp44', 'mp44strap') + FINISH]
    dp28 = ['dp28'] + ['dp28_' + s for s in FINISH]
    sg = ['shotgun'] + ['shotgun_' + s for s in ('authwinch', 'dhshotblack', 'dhshotchrome', 'guanshotty', 'hobbsshotty',
                                                 'lv_ttshotgun') + FINISH]
    ops = []
    # ---- BAR
    ops += [T(h, W + t + '.tik', 'BAR') for t in bar]
    ops += [F(h, VM + 'mg/' + c + '.skc', 'BAR') for c in ('bar_reload_ads', 'bar_reload_adsb', 'bar_reload_empty_ads',
                                                           'bar_reload_empty_adsb', 'coop_bar_ads_hand')]
    ops += [F(h, W + d + '/coop_reload_ads_empty.skc', 'BAR') for d in ('BAR', 'bar_lmg', 'coop_pabar')]
    ops += [F(h, 'sound/weapons/foley/coop_bar_reload_loaded.wav', 'BAR + DP-28')]
    ops += [R('models/player/base/fps_anims_mg.txt', h, ['bar_reload_empty', 'bar_reload_empty_ads', 'bar_reload_adsb',
                                                         'bar_reload_empty_adsb'], 'BAR')]
    # The lane repoints `bar_charge` (aim pose: support hand on the BAR's forearm). `bar` is also the FALLBACK prefix
    # of every other MG-class gun (Lewis Gun, M1919, MG42 portable - cg_viewmodelanim.c CG_GetVMAnimPrefixIndex), which
    # are not part of this rollout and must aim as released. So the same clip ships as the BAR's own per-weapon row
    # (weapon key `bar`; finishes and model variants are "BAR (...)" and strip to it) and `bar_charge` stays released.
    ops += [RL('models/player/base/fps_anims_mg.txt', 'coopr_bar_charge',
               '\tcoopr_bar_charge\t\tviewmodel/mg/coop_bar_ads_hand.skc\t\tcrossblend 0.1\t// HZM coop [ads heavy, integrate_ads.py] '
               'BAR only (per-weapon row): aim pose, support hand on the forearm as at the hip; bar_charge stays the fallback MGs\' released pose', 'BAR')]
    ops += [C('BAR', 'BAR', bar)]
    # ---- StG 44
    ops += [T(h, W + t + '.tik', 'StG 44', allow=(r'^\s*reload\s+mp44_reload\.skc\s*$', r'^\s*entry sound mp44_snd_reload item\s*$'))
            for t in mp44]
    ops += [F(h, VM + 'mp44/' + c + '.skc', 'StG 44') for c in ('coop_mp44_reload_hip', 'mp44_reload_ads', 'mp44_reload_adsb',
                                                                'mp44_reload_empty_ads', 'mp44_reload_empty_adsb')]
    ops += [F(h, W + d + '/' + c + '.skc', 'StG 44') for d in ('mp44', 'coop_mp44strap')
            for c in ('coop_reload_ads_empty', 'coop_reload_ads_loaded')]
    ops += [F(h, 'sound/weapons/foley/coop_mp44_reload_loaded.wav', 'StG 44')]
    ops += [R('models/player/base/fps_anims_mg.txt', h, ['mp44_reload', 'mp44_reload_empty', 'mp44_reload_empty_ads',
                                                         'mp44_reload_adsb', 'mp44_reload_empty_adsb'], 'StG 44')]
    ops += [C('StG 44', 'StG 44', mp44)]
    # ---- DP-28
    ops += [T(h, W + t + '.tik', 'DP-28') for t in dp28]
    ops += [F(h, VM + 'coop_dp28/' + c + '.skc', 'DP-28') for c in ('coop_dp28_ads_hand', 'dp28_reload_ads', 'dp28_reload_adsb',
                                                                    'dp28_reload_empty_ads', 'dp28_reload_empty_adsb')]
    ops += [F(h, W + 'coop_dp28/' + c + '.skc', 'DP-28') for c in ('coop_reload_ads_empty', 'coop_reload_ads_loaded')]
    ops += [R('models/player/base/fps_anims_mg.txt', h, ['dp28_charge', 'dp28_reload_empty', 'dp28_reload_empty_ads',
                                                         'dp28_reload_adsb', 'dp28_reload_empty_adsb'], 'DP-28')]
    ops += [C('DP-28', 'DP-28', dp28)]
    # ---- pump shotgun
    ops += [T(h, W + t + '.tik', 'Shotgun') for t in sg]
    ops += [F(h, VM + 'shotgun/' + c + '.skc', 'Shotgun') for c in (
        'shotgun_reload_ads', 'shotgun_reload_single_ads', 'shotgun_reload_end_ads', 'shotgun_reload_end_loaded_ads',
        'shotgun_reload_end_break_ads', 'coop_shotgun_reload_end_loaded', 'coop_shotgun_reload_end_break', 'coop_tps_reload_break')]
    ops += [F(h, W + 'shotgun/coop_shotgun_still32.skc', 'Shotgun'), F(h, W + 'shotgun/shotgun.skd', 'Shotgun'),
            F(h, 'scripts/coop_shotgun_sight.shader', 'Shotgun'), F(h, 'textures/coop_wpn/shotgun_bead.tga', 'Shotgun', tga_flag=True),
            F(h, 'textures/coop_wpn/shotgun_groove.tga', 'Shotgun', tga_flag=True), F(h, 'models/player/base/anims_shotgun.txt', 'Shotgun')]
    ops += [R('models/player/base/fps_anims_shotgun.txt', h, ['shotgun_reload_end_loaded', 'shotgun_reload_end_loaded_ads',
                                                              'shotgun_reload_end_break', 'shotgun_reload_end_break_ads'], 'Shotgun')]
    ops += [C('Shotgun', 'Shotgun', sg)]
    ops += [P(h, 'patch_sgbreak.py', 'Shotgun')]
    return ops


def step2():
    """SMG lane: MP40 (open-bolt handle on the mesh, 11 tiks), Silenced MP40 (raised-sights mesh; its sight row is in
    the merged cgame), MP40 R2 ("MP40 (Reactivated)").
    NOT shipped: Thompson, Sten, MP18 (tiks, meshes, clips, rows), the sten / ppsh / moschetto / type100 aim poses.
    ISOLATION. The lane repoints the generic `mp40_*` rows (aim pose, hip + aimed reload). `mp40` is also the prefix of
    guns that are NOT part of this rollout - M3 Grease Gun, Silenced Grease Gun, Silenced PPS-43, and the MP18
    ("MP40 (MP18)") - so the generic rows and the released clip `MP40/mp40_reload_ads.skc` stay exactly as released,
    and the MP40's clips ship as per-weapon rows `coopr_mp40_*` (weapon key of "MP40" and of every "MP40 (finish)"),
    the new aimed clip under its own file name. "Silenced MP40" has its own key (no finish suffix to strip), so it
    gets its own aim-pose row; the MP18's name strips to "MP40", so it is PINNED to the released aim pose by a
    `coopr_mp40_mp18_charge` row (its reload already has its own released row in anims_shared.txt)."""
    s = 'smg'
    mp40 = ['mp40'] + ['mp40_' + x for x in ('guanmp40', 'guanmp40s', 'lv_mp75') + FINISH]
    rowf = 'models/player/base/fps_anims_smg.txt'
    tag = '\t// HZM coop [ads smg, integrate_ads.py] '
    ops = []
    allow = (r'^\s*(idle|reload|fire|secondaryfire|guardfire_a|guardfire_b)\s+\S+\.skc\s*$', r'^\s*entry sound mp40_snd_reload item\s*$')
    # ---- MP40
    ops += [T(s, W + t + '.tik', 'MP40', allow=allow) for t in mp40]
    ops += [F(s, W + 'mp40/mp40.skd', 'MP40')]
    ops += [F(s, W + 'mp40/' + c + '.skc', 'MP40') for c in ('coop_fire', 'coop_fire_empty', 'coop_idle_empty', 'coop_reload_ads_empty', 'coop_reload_empty')]
    ops += [F(s, VM + 'mp40/' + c + '.skc', 'MP40') for c in ('coop_mp40_ads_mag', 'coop_mp40_reload_hip', 'coop_mp40_reload_empty_hip', 'mp40_reload_empty_ads')]
    ops += [F(s, VM + 'mp40/mp40_reload_ads.skc', 'MP40', dst=VM + 'mp40/coop_mp40_reload_ads.skc')]
    ops += [F(s, 'sound/weapons/foley/coop_mp40_snd_reload_loaded.wav', 'MP40 family')]
    for row, clip, xb, why in (
            ('coopr_mp40_charge', 'coop_mp40_ads_mag', '0.25', 'MP40 + finishes only (per-weapon row): aim pose, support hand on the magazine housing'),
            ('coopr_mp40_reload', 'coop_mp40_reload_hip', '0.1', 'MP40 + finishes only: hip reload, rounds left (no cocking)'),
            ('coopr_mp40_reload_empty', 'coop_mp40_reload_empty_hip', '0.1', 'MP40 + finishes only: hip reload of an emptied gun'),
            ('coopr_mp40_reload_ads', 'coop_mp40_reload_ads', '0.1', 'MP40 + finishes only: aimed reload, rounds left (the lane clip mp40_reload_ads.skc under its own name; the released file stays for the other mp40-prefix guns)'),
            ('coopr_mp40_reload_empty_ads', 'mp40_reload_empty_ads', '0.1', 'MP40 + finishes only: aimed reload of an emptied gun')):
        ops += [RL(rowf, row, '\t%s\t\tviewmodel/mp40/%s.skc\t\tcrossblend %s%s%s' % (row, clip, xb, tag, why), 'MP40')]
    ops += [RL(rowf, 'coopr_mp40_mp18_charge', '\tcoopr_mp40_mp18_charge\t\tviewmodel/mp40_stand_idle00.skc\t\tcrossblend 0.25' + tag
               + 'PIN: the MP18 ("MP40 (MP18)") is not part of the rollout and keeps the RELEASED aim pose', 'MP18 pin')]
    ops += [C('MP40', 'MP40', mp40 + ['mp40_mp40r2'], skip=('mp40_mp18',))]
    # ---- Silenced MP40 (tik + mesh live in zzzzz_xw_weapons.pk3)
    ops += [T(s, W + 'mp40silenced.tik', 'Silenced MP40', allow=allow)]
    ops += [F(s, W + 'mp40/mp40silenced.skd', 'Silenced MP40')]
    ops += [F(s, W + 'mp40/coop_silenced_mp40_' + c + '.skc', 'Silenced MP40') for c in ('fire', 'fire_empty', 'held_mp40', 'idle_empty', 'reload', 'reload_ads_empty', 'reload_empty')]
    ops += [F(s, VM + 'mp40/' + c + '.skc', 'Silenced MP40') for c in ('coop_silenced_mp40_reload_hip', 'coop_silenced_mp40_reload_empty_hip', 'silenced_mp40_reload_ads', 'silenced_mp40_reload_empty_ads')]
    ops += [R(rowf, s, ['coopr_silenced_mp40_reload', 'coopr_silenced_mp40_reload_empty', 'coopr_silenced_mp40_reload_ads', 'coopr_silenced_mp40_reload_empty_ads'], 'Silenced MP40')]
    ops += [RL(rowf, 'coopr_silenced_mp40_charge', '\tcoopr_silenced_mp40_charge\t\tviewmodel/mp40/coop_mp40_ads_mag.skc\t\tcrossblend 0.25' + tag
               + 'Silenced MP40 (its own weapon key): the MP40 aim pose', 'Silenced MP40')]
    # ---- MP40 R2
    ops += [T(s, W + 'mp40_mp40r2.tik', 'MP40 R2', allow=allow)]
    ops += [F(s, W + 'coop_mp40r2/coop_mp40_reactivated_' + c + '.skc', 'MP40 R2') for c in ('fire', 'fire_empty', 'held_idle_mp40', 'held_mp40', 'idle_empty', 'reload', 'reload_ads_empty', 'reload_empty')]
    ops += [F(s, VM + 'mp40/' + c + '.skc', 'MP40 R2') for c in ('coop_mp40_reactivated_reload_hip', 'coop_mp40_reactivated_reload_empty_hip', 'mp40_reactivated_reload_ads', 'mp40_reactivated_reload_empty_ads')]
    ops += [R(rowf, s, ['coopr_mp40_reactivated_reload', 'coopr_mp40_reactivated_reload_empty', 'coopr_mp40_reactivated_reload_ads', 'coopr_mp40_reactivated_reload_empty_ads'], 'MP40 R2')]
    return ops


def step3():
    """RIFLES lane: the between-shot BOLT CYCLE while aiming - Kar98, Springfield, Mosin, Lee-Enfield: the four hands
    clips (released paths, rows already in the released row file) + the aim-only capped gun clip `rechamber_ads` and
    its row in every tik that shares the mesh (19 + 1 + 18 + 18).
    NOT shipped: the Kar98 aimed reload (kar98_reload_ads row + clip), G 43 Irons (tiks, mesh, clips, rows, shader, HUD
    icon), the lane's player_torso.st. kar98_g98 / enfield_p14 (own meshes) stay as released: the cgame's mesh guard
    keeps them on the hip clips."""
    r = 'rifles'
    wdir = os.path.join(L.PROP, r, 'assets', 'models', 'weapons')
    fam = {'Kar98': r'^kar98(_|\.)', 'Springfield': r'^springfield_unscoped\.', 'Mosin': r'^mosin_nagant_rifle(_|\.)', 'Lee-Enfield': r'^enfield(_|\.)'}
    ops, got = [], {}
    for g, rx in fam.items():
        got[g] = sorted(f[:-4] for f in os.listdir(wdir) if f.lower().endswith('.tik') and re.match(rx, f.lower()))
        # the Kar98 tiks also carry the gun rows of the Kar98 AIMED RELOAD (reload_ads_loaded / reload_ads_empty ->
        # reload_KAR98_ads.skc) - not part of the rollout, and the merged cgame would show those rows in an aimed reload
        ops += [T(r, W + t + '.tik', g, strip=(r'HZM coop \[ads rifles 2026-10-13\] reload_ads_loaded', r'HZM coop \[ads rifles 2026-10-13\] reload_ads end',
                                               'Kar98 aimed reload gun rows') if g == 'Kar98' else None) for t in got[g]]
    ops += [F(r, VM + 'rifle/kar98_rechamber_ads.skc', 'Kar98'), F(r, W + 'KAR98/rechamber_kar98_ads.skc', 'Kar98'),
            F(r, VM + 'rifle/springfield_rechamber_ads.skc', 'Springfield'), F(r, W + 'springfield/spring_recham_ads.skc', 'Springfield'),
            F(r, VM + 'mosin_nagant/mosin_rechamber_ads.skc', 'Mosin'), F(r, W + 'mosin_nagant/mosin_nagant_rechamber_ads.skc', 'Mosin'),
            F(r, VM + 'enfield/enfield_rechamber_ads.skc', 'Lee-Enfield'), F(r, W + 'enfield/enfield_rechamber_ads.skc', 'Lee-Enfield')]
    ops += [C('Kar98', 'Mauser KAR 98K', got['Kar98'], skip=('kar98_g98',)), C('Mosin', 'Mosin Nagant Rifle', got['Mosin']),
            C('Lee-Enfield', 'Lee-Enfield', got['Lee-Enfield'], skip=('enfield_p14',))]
    return ops


def step4():
    """PISTOLS - the pistol lane's frozen SHIP CUT v2 (PISTOLS_SHIP.md, folder ship/, docs commit ddd502c): 17 pistols
    + the Webley Mk VI, every finish and model-variant tik (98 tiks).
    NOT shipped: Mauser C96 + Trench C96, S&W M10 + finishes (held out by the lane; nothing of theirs is in ship/),
    the texture lifts (ship_awaiting_approval/), ship/LEFT_OUT.txt.
    SHARED TABLES are merged, never copied: fps_anims_pistol.txt (op M against the pass-1 fixes copy),
    anims_shared.txt (op M: the lane's snapshot of mod commit 6cf61e58 onto the CURRENT mod-tree file, which also has
    the low-turret rows; the result ships in the fixes pak over the pinned mod-tree copy), coop_mod/player_torso.st
    (op G: the snapshot of mod commit 12e9faf6 onto the current file, which also has the turret rows and the shotgun
    break-off; code pak, mod commit).
    ISOLATION. The lane repoints the generic rows colt45_idle / colt45_charge / p38_idle / p38_charge (+ the bytes of
    the released clips colt45_reload_ads / p38_reload_ads ...). Pistol-class weapons that are NOT in the cut (complete
    scan of every tik the game can load, pistolclass.py): Mauser C96 + finishes + Trench (prefix p38), S&W M10 (own
    prefix m10, rows untouched), "Bombing Run" = the coop binoculars + finishes (weapontype pistol, no named prefix ->
    the FALLBACK prefix colt45). They are PINNED to the released clips by per-weapon rows (the lane's own
    coopr_mauser_c96_charge + the rows below); proof: rowpick.py."""
    s = '@ship'
    root = os.path.join(L.PROP, 'ship')
    rowf = 'models/player/base/fps_anims_pistol.txt'
    tag = '\t// HZM coop [ads pistols, integrate_ads.py] PIN: '
    d2 = {  # released lines a D2 gun (declared server-side pace change) replaces
        'webley': (r'^\s*reload(_end|_single)?\s+webley_(revolver_)?reload_(start|end|single)\.skc\s*$',
                   r'^\s*\d+\s+sound webley_snd_reload_(start|end|single)\s*$', r'^\s*\d+\s+surface shellmetal_cull [+-]nodraw\s*$',
                   r'^\s*\d+ tagspawn tag_eject\s*$', r'^\s*[()]\s*$',
                   r'^\s*(count 1|model models/ammo/pistolshell\.tik|spawnrange 1024|scale \.75|velocity 50|randvelaxis range 1 2 range 1 2 0'
                   r'|emitterangles 0 0 45|avelocity crandom 90 crandom 90 0|accel 0 0 -800|physicsrate 20|life 2\.0|fadedelay 1\.7'
                   r'|collision|bouncefactor 0\.2|bouncesoundonce snd_pistol_shell)\s*$'),
        'nagant': (r'^\s*reload_single\s+nagant_reload_loop\.skc\s*$',)}
    ops, byname = [], {}
    for dp, _dn, fn in sorted(os.walk(root)):
        for f in sorted(fn):
            rel = os.path.relpath(os.path.join(dp, f), root).replace(os.sep, '/')
            low = rel.lower()
            if '/' not in rel:
                continue                                    # LEFT_OUT.txt
            if low == 'coop_mod/player_torso.st':
                ops.append(G('coop_mod/player_torso.st', s, rel, '12e9faf6', 'pistols (state file)'))
            elif low == rowf:
                ops.append(M(rowf, s, ('docs', PASS1_REV), 'pistols (hands rows)'))
            elif low == 'models/player/base/anims_shared.txt':
                ops.append(M(rel, s, ('mod', '6cf61e58'), 'pistols (torso rows)'))
            elif low.endswith('.tik'):
                txt = open(os.path.join(dp, f), 'rb').read().decode('latin-1')
                name = L.tik_name(txt)
                stem = re.sub(r'\s*\([^()]*\)\s*$', '', name)
                stem = 'Colt 45' if name == 'Colt 45 (Pacific)' else stem
                byname.setdefault(stem, []).append(f[:-4])
                allow = d2['webley'] if (f.lower().startswith('webley_revolver') or f.lower() == 'colt45_colt1911w.tik') else \
                    d2['nagant'] if f.lower().startswith('nagant_revolver') else ()
                ops.append(T(s, rel, name if name == 'Webley Mk VI' else stem, allow=allow))
            else:
                gun = 'pistols'
                for key, g in (('webley', 'Webley'), ('coop_colt1911w', 'Webley Mk VI'), ('mk6', 'Webley Mk VI'), ('nagan', 'Nagant'), ('m10', 'M10 torso clip (named by a shared table)'),
                               ('beretta', 'Beretta'), ('luger', 'Luger'), ('welrod', 'Welrod'), ('tt33', 'TT-33'), ('ppk', 'PPK'),
                               ('nambu', 'Nambu'), ('histandard', 'Hi-Standard'), ('highstandard', 'Hi-Standard'), ('hs_pistol', 'Hi-Standard'),
                               ('p38', 'P38'), ('colt', 'Colt 45'), ('prone', 'prone pistol reload')):
                    if key in low:
                        gun = g
                        break
                ops.append(F(s, rel, gun))
    for stem, tiks in sorted(byname.items()):
        # coverage is proved against the mod tree; 7 pistols of the cut live only in zzzzz_xw_weapons.pk3 (one tik each)
        inmod = [t for t in tiks if os.path.isfile(os.path.join(L.MOD, 'models', 'weapons', t + '.tik'))]
        if inmod:
            ops.append(C(stem, stem, inmod))
    # ---- pins: pistol-class weapons outside the cut keep the RELEASED clips of the generic rows the lane repointed
    for key, what in (('mauser_c96', 'Mauser C96 + finishes + Trench C96 (held out; prefix p38)'),
                      ('bombing_run', 'Bombing Run = the coop binoculars + finishes (pistol class, fallback prefix colt45)')):
        ops.append(RL(rowf, 'coopr_%s_idle' % key, '\tcoopr_%s_idle\t\tviewmodel/pistol/coltpose.skc\t\tcrossblend 0.3%s%s keeps the RELEASED hip idle' % (key, tag, what), 'pin'))
        if key != 'mauser_c96':     # the C96's aim-pose pin is the lane's own row (in the merged file)
            ops.append(RL(rowf, 'coopr_%s_charge' % key, '\tcoopr_%s_charge\t\tviewmodel/coltpose00.skc\t\tcrossblend 0.3%s%s keeps the RELEASED aim pose' % (key, tag, what), 'pin'))
    return ops


def step5():
    """G 43 IRONS - a NEW weapon (rifles lane, closed): 12 tiks `coop_g43_irons*` (base, 7 finishes, 4 pack-skin
    variants) on its own mesh with its own sight surface, aim pose, aimed reloads, the aim-only gun row
    reload_ads_empty (the carrier racked; kept on the client clip clock), loot-feed picture. Every file is `new`
    (nothing of it is in the mod tree: a new file there would re-hash the 1.3 GB assets pak). The server-read rows of
    the tiks are the scoped G43's released clips (rowlen_check.py --like).
    The armory entry (roster id 78, rank 2), state-file row, recoil rows, AI alias, dev lists are CODE-pak files:
    integrate/apply_armory5.py runs the lane's source edits + the generators on the real tree.
    NOT shipped: models/weapons/g43/coop_g43_irons_reload.skc (no tik row names it any more), the *_phys.json notes."""
    r = 'rifles'
    tiks = ['coop_g43_irons'] + ['coop_g43_irons_' + s for s in FINISH + ('dhg43fleck', 'hobbsg43urb', 'hobbsg43wood', 'lv_ttg43')]
    wdir = os.path.join(L.PROP, r, 'assets', 'models', 'weapons')
    staged = sorted(f[:-4].lower() for f in os.listdir(wdir) if f.lower().endswith('.tik')
                    and (L.tik_name(open(os.path.join(wdir, f), 'rb').read().decode('latin-1')) or '').startswith('G 43 Irons'))
    assert staged == sorted(tiks), ('G 43 Irons: staged tiks and the list differ', staged)
    ops = [F(r, W + t + '.tik', 'G 43 Irons') for t in tiks]
    ops += [F(r, VM + 'g43/' + c + '.skc', 'G 43 Irons') for c in ('coop_g43_irons_aim', 'coop_g43_irons_reload_ads', 'coop_g43_irons_reload_empty_ads')]
    ops += [F(r, W + 'g43/coop_g43_irons.skd', 'G 43 Irons'), F(r, W + 'g43/coop_g43_irons_reload_ads_empty.skc', 'G 43 Irons'),
            F(r, 'scripts/coop_g43_sight.shader', 'G 43 Irons'), F(r, 'textures/coop_wpn/g43_sight.tga', 'G 43 Irons', tga_flag=True),
            F(r, 'textures/hud/loot/w_g43irons.tga', 'G 43 Irons', tga_flag=True)]
    ops += [R('models/player/base/fps_anims_rifle.txt', r, ['coopr_g_43_irons_charge', 'coopr_g_43_irons_reload', 'coopr_g_43_irons_reload_empty',
                                                            'coopr_g_43_irons_reload_ads', 'coopr_g_43_irons_reload_empty_ads'], 'G 43 Irons')]
    return ops


STEPS = {1: step1, 2: step2, 3: step3, 4: step4, 5: step5}


# ------------------------------------------------------------------------------------------------------------------
def lane_file(lane, rel):
    if lane.startswith('@'):
        return os.path.join(L.PROP, lane[1:], *rel.split('/'))
    return os.path.join(L.PROP, lane, 'assets', *rel.split('/'))


def merge3(ours, base, theirs):
    """git merge-file on LF text; returns (merged bytes in the line ending of `ours`, number of conflicts)"""
    import tempfile
    crlf = b'\r\n' in ours
    d = tempfile.mkdtemp(prefix='integ_m3_')
    names = []
    for n, x in (('ours', ours), ('base', base), ('theirs', theirs)):
        fp = os.path.join(d, n)
        open(fp, 'wb').write(x.replace(b'\r\n', b'\n'))
        names.append(fp)
    r = subprocess.run(['git', 'merge-file', '-p'] + names, capture_output=True)
    out = r.stdout
    for fp in names:
        os.remove(fp)
    os.rmdir(d)
    if crlf:
        out = out.replace(b'\n', b'\r\n')
    return out, (r.returncode if r.returncode >= 0 else 999)


def git_show(repo, rev, path):
    # the working tree is case-insensitive, the object store is not (coop_mod/player_Torso.st on disk, player_torso.st in git)
    for n in subprocess.run(['git', '-C', repo, 'ls-tree', '-r', '--name-only', rev, os.path.dirname(path) + '/'], capture_output=True, text=True).stdout.splitlines():
        if n.lower() == path.lower():
            path = n
    return subprocess.run(['git', '-C', repo, 'show', '%s:%s' % (rev, path)], capture_output=True, check=True).stdout


def row_of(line):
    t = line.split('//')[0].split()
    return t[0] if len(t) >= 2 else None


def mixed_endings(data):
    crlf, lf = data.count(b'\r\n'), data.count(b'\n')
    return bool(crlf and crlf != lf)


def reset():
    import time
    rel = 'docs/tools/assets/fixes'
    aside = os.path.join(L.CACHE, 'integ_backout_' + time.strftime('%Y%m%d_%H%M%S'))
    tracked = set(subprocess.run(['git', '-C', L.ROOT, 'ls-tree', '-r', '--name-only', L.RELEASED_REV, rel + '/', rel + '_base/'],
                                 capture_output=True, text=True, check=True).stdout.splitlines())
    n = 0
    for top in (L.FIX, L.FIXBASE):
        for dp, _dn, fn in os.walk(top):
            for f in fn:
                p = os.path.join(dp, f)
                r = os.path.relpath(p, L.ROOT).replace(os.sep, '/')
                if r not in tracked:
                    dst = os.path.join(aside, r.replace('/', os.sep))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(p, dst)
                    n += 1
    # Written from the object store (the shared git index is never touched). core.autocrlf is on, so git cannot say
    # which line ending a text file had on disk - and the pak is built from the bytes on disk: the pinned bases are
    # chosen by their pinned md5, the text sources by released_style.json (recorded from the released working copy).
    style = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'released_style.json')))['style']
    show = lambda r: subprocess.run(['git', '-C', L.ROOT, 'show', L.RELEASED_REV + ':' + r], capture_output=True, check=True).stdout
    pins = json.loads(show(rel + '/fixes_manifest.json').decode('utf-8'))
    for r in sorted(tracked):
        data = show(r)
        lf = data.replace(b'\r\n', b'\n')
        crlf = lf.replace(b'\n', b'\r\n')
        if r.startswith(rel + '_base/'):
            pin = pins[r[len(rel + '_base/'):]]['base_md5']
            cand = [x for x in (data, lf, crlf) if L.md5(x) == pin]
            assert cand, (r, 'no line-ending variant matches its pinned md5')
            data = cand[0]
        elif r[len(rel) + 1:] in style:
            data = crlf if style[r[len(rel) + 1:]] == 'crlf' else lf
        pth = os.path.join(L.ROOT, *r.split('/'))
        if not os.path.isfile(pth) or open(pth, 'rb').read() != data:
            os.makedirs(os.path.dirname(pth), exist_ok=True)
            open(pth, 'wb').write(data)
    print('reset to %s: %d added file(s) moved to %s' % (L.RELEASED_REV, n, aside))
    return 0


def main():
    if '--reset' in sys.argv:
        return reset()
    dry = '--dry-run' in sys.argv
    modp = '--mod-patches' in sys.argv
    steps = sorted(STEPS)
    if '--steps' in sys.argv:
        steps = [int(x) for x in sys.argv[sys.argv.index('--steps') + 1].split(',')]
    man = json.load(open(L.MAN, encoding='utf-8'))
    mankey = {k.lower(): k for k in man}
    vfs = L.Vfs(L.FIX)
    out = {}            # manifest key -> bytes to write
    owner = {}          # manifest key -> (gun, step, what)
    rowfiles = {}       # rel -> [lines], nl
    fails, report = [], []

    dircase = {}        # lower-case directory -> the spelling the fixes sources already use (the generator compares
    for k in man:       # the manifest with a walk of the folder, and on Windows `mp40/x` lands in an existing `MP40/`)
        parts = k.split('/')[:-1]
        for i in range(1, len(parts) + 1):
            dircase.setdefault('/'.join(parts[:i]).lower(), '/'.join(parts[:i]))

    def key_of(rel):
        if rel.lower() in mankey:
            return mankey[rel.lower()]
        parts = rel.split('/')
        for i in range(len(parts) - 1, 0, -1):
            d = '/'.join(parts[:i]).lower()
            if d in dircase:
                rel = dircase[d] + '/' + '/'.join(parts[i:])
                break
        parts = rel.split('/')[:-1]
        for i in range(1, len(parts) + 1):
            dircase.setdefault('/'.join(parts[:i]).lower(), '/'.join(parts[:i]))
        return rel

    def rowfile(rel):
        if rel not in rowfiles:
            b = open(os.path.join(L.FIX, *key_of(rel).split('/')), 'rb').read()
            nl = b'\r\n' if b'\r\n' in b else b'\n'
            rowfiles[rel] = [b.split(nl), nl]
        return rowfiles[rel]

    def put_row(rel, row, line, gun, step, src):
        lines, nl = rowfile(rel)
        line_b = line.rstrip('\r\n').encode('latin-1')
        hit = [i for i, l in enumerate(lines) if row_of(l.decode('latin-1')) == row]
        if len(hit) > 1:
            fails.append('%s: row %s defined %d times' % (rel, row, len(hit)))
        if hit and step in FROZEN and lines[hit[0]] != line_b:
            act = 'KEPT (shipped step: the lane row has changed since pass 1)'
        elif hit:
            act = 'same' if lines[hit[0]] == line_b else 'REPOINT'
            lines[hit[0]] = line_b
        else:
            act = 'ADD'
            close = max(i for i, l in enumerate(lines) if l.strip() == b'}')
            mark = MARK.encode('latin-1')
            if mark not in lines:
                lines.insert(close, mark)
                close += 1
            lines.insert(close, line_b)
        report.append((step, gun, 'row', rel + ' :: ' + row, act + ' (' + src + ')'))
        # the clip the row points at must be shipped or already loadable
        clip = line.split('//')[0].split()[1]
        owner.setdefault(('rowclip', 'models/human/animation/' + clip), (gun, step, rel + ' :: ' + row))

    for st in steps:
        for o in STEPS[st]():
            if o['op'] == 'M':
                theirs = open(lane_file(o['lane'], o['src']), 'rb').read()
                k = key_of(o['rel'])
                if o['base'][0] == 'docs':
                    base = git_show(L.ROOT, o['base'][1], 'docs/tools/assets/fixes/' + k)
                    wc = open(os.path.join(L.FIX, *k.split('/')), 'rb').read()
                    ours = git_show(L.ROOT, PASS1_REV, 'docs/tools/assets/fixes/' + k).replace(b'\r\n', b'\n')
                    if b'\r\n' in wc:
                        ours = ours.replace(b'\n', b'\r\n')
                    kind = 'manifest (base)'
                else:
                    mp = vfs.mod[o['rel'].lower()]
                    base = git_show(L.MOD, o['base'][1], mp)
                    ours = open(os.path.join(L.MOD, *mp.split('/')), 'rb').read()
                    kind = 'manifest (base)' if k in man else 'base'
                data, nconf = merge3(ours, base, theirs)
                if nconf:
                    fails.append('%s: 3-way merge of the lane snapshot has %d conflict(s)' % (o['rel'], nconf))
                    continue
                note = ' [3-way merge: lane snapshot (base %s %s) onto %s]' % (o['base'][0], o['base'][1], 'the pass-1 fixes copy' if o['base'][0] == 'docs' else 'the current mod-tree file')
                if o['base'][0] == 'docs':
                    nl_ = b'\r\n' if b'\r\n' in data else b'\n'
                    rowfiles[o['rel']] = [data.split(nl_), nl_]
                    report.append((st, o['gun'], 'merge', k, 'merged' + note))
                else:
                    out[k] = data
                    owner[k] = (o['gun'], st, kind)
                    fp = os.path.join(L.FIX, *k.split('/'))
                    report.append((st, o['gun'], kind, k, ('same' if os.path.isfile(fp) and open(fp, 'rb').read() == data else 'WRITE') + note))
                continue
            if o['op'] == 'G':
                mp = vfs.mod[o['rel'].lower()]
                fp = os.path.join(L.MOD, *mp.split('/'))
                ours = open(fp, 'rb').read()
                data, nconf = merge3(ours, git_show(L.MOD, o['rev'], mp), open(lane_file(o['lane'], o['src']), 'rb').read())
                if nconf:
                    fails.append('%s: 3-way merge onto the mod tree has %d conflict(s)' % (o['rel'], nconf))
                    continue
                if data == ours:
                    res = 'already in the mod tree'
                elif modp and not dry:
                    open(fp, 'wb').write(data)
                    res = 'MERGED into the mod tree (commit it in the mod repo)'
                else:
                    res = 'NOT in the mod tree yet (give --mod-patches)'
                report.append((st, o['gun'], 'mod merge', mp + ' <= %s/%s (snapshot of mod %s)' % (o['lane'], o['src'], o['rev']), res))
                continue
            if o['op'] in ('F', 'T'):
                src = lane_file(o['lane'], o['rel'])
                if not os.path.isfile(src):
                    fails.append('%s: not staged in lane %s' % (o['rel'], o['lane']))
                    continue
                data = open(src, 'rb').read()
                if o.get('dst'):
                    o = dict(o, rel=o['dst'], src_rel=o['rel'])
                tganote = ''
                if o.get('strip'):
                    nl_ = b'\r\n' if b'\r\n' in data else b'\n'
                    lines_ = data.split(nl_)
                    a_ = [i for i, l in enumerate(lines_) if re.search(o['strip'][0], l.decode('latin-1'))]
                    b_ = [i for i, l in enumerate(lines_) if re.search(o['strip'][1], l.decode('latin-1'))]
                    if len(a_) != 1 or len(b_) != 1 or b_[0] < a_[0]:
                        fails.append('%s: the block to strip is not marked exactly once' % o['rel'])
                    else:
                        data = nl_.join(lines_[:a_[0]] + lines_[b_[0] + 1:])
                        tganote = ' [lane block cut out: %d lines, %s]' % (b_[0] - a_[0] + 1, o['strip'][2])
                if o.get('tga_flag') and len(data) > 18 and data[17] & 0x20:
                    data = data[:17] + bytes([data[17] & ~0x20 & 0xff]) + data[18:]
                    tganote = ' [tga top-down flag cleared]'
                k = key_of(o['rel'])
                fpk = os.path.join(L.FIX, *k.split('/'))
                if st in FROZEN and k in man and os.path.isfile(fpk) and open(fpk, 'rb').read() != data:
                    data = open(fpk, 'rb').read()
                    tganote += ' [SHIPPED step: the lane file has changed since pass 1 - the shipped copy is KEPT]'
                below, above = vfs.below_fixes(o['rel'])
                if above:
                    fails.append('%s: also carried by %s, which sorts ABOVE the fixes pak - the override would be dead' % (o['rel'], above))
                if k in man:
                    kind = 'manifest (%s)' % ('base_pak' if 'base_pak' in man[k] else 'new' if man[k].get('new') else 'base')
                elif below and below[1] == L.MODPAK:
                    kind = 'base'
                elif below:
                    kind = 'base_pak ' + below[0] + '/' + below[1]
                else:
                    kind = 'new'
                note = tganote
                if o['rel'].lower().endswith(('.tik', '.shader', '.txt', '.scr')) and mixed_endings(data):
                    # the released file is itself mixed and the lane kept it; the generator refuses mixed endings in an
                    # override, so the copy is written with ONE ending (CRLF) - the text is unchanged
                    data = data.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
                    note += ' [line endings made uniform CRLF]'
                if o['op'] == 'T':
                    if not below:
                        fails.append('%s: a weapon tik with no released base (%s)' % (o['rel'], kind))
                    else:
                        base = vfs.read_from(below, o['rel']).decode('latin-1').splitlines()
                        new = data.decode('latin-1').splitlines()
                        newset = {}
                        for l in new:
                            newset[l] = newset.get(l, 0) + 1
                        lost = []
                        for l in base:
                            if newset.get(l, 0) > 0:
                                newset[l] -= 1
                            else:
                                lost.append(l)
                        bad = [l for l in lost if not any(re.search(a, l) for a in o['allow'])]
                        if bad:
                            fails.append('%s: released lines missing from the lane tik: %r' % (o['rel'], bad[:3]))
                        note += ' [released tik + %d lane lines, %d released lines replaced]' % (len(new) - len(base) + len(lost), len(lost))
                if below and vfs.read_from(below, o['rel']) == data and k not in man:
                    report.append((st, o['gun'], 'skip', o['rel'], 'identical to its base - not shipped'))
                    continue
                if k in out and out[k] != data:
                    fails.append('%s: two ops write different bytes' % k)
                out[k] = data
                owner[k] = (o['gun'], st, kind)
                report.append((st, o['gun'], kind, k + (' <= lane file ' + o['src_rel'] if o.get('src_rel') else ''), ('same' if os.path.isfile(os.path.join(L.FIX, *k.split('/'))) and
                               open(os.path.join(L.FIX, *k.split('/')), 'rb').read() == data else 'WRITE') + note))
            elif o['op'] == 'R':
                src = open(lane_file(o['lane'], o['rel']), 'rb').read().decode('latin-1').splitlines()
                for row in o['rows']:
                    hit = [l for l in src if row_of(l) == row]
                    if len(hit) != 1:
                        fails.append('%s: row %s found %d times in lane %s' % (o['rel'], row, len(hit), o['lane']))
                        continue
                    put_row(o['rel'], row, hit[0], o['gun'], st, 'lane ' + o['lane'])
            elif o['op'] == 'RL':
                put_row(o['rel'], o['row'], o['line'], o['gun'], st, 'integration')
            elif o['op'] == 'C':
                have = set()
                wdir = os.path.join(L.MOD, 'models', 'weapons')
                for f in os.listdir(wdir):
                    if f.lower().endswith('.tik'):
                        n = L.tik_name(open(os.path.join(wdir, f), 'rb').read().decode('latin-1'))
                        if n and (n == o['name'] or n.startswith(o['name'] + ' (')):
                            have.add(f[:-4].lower())
                want = {t.lower() for t in o['tiks']}
                left = {t.lower() for t in o['skip']} & have
                have -= left
                if have != want:
                    fails.append('coverage %s: mod-tree tiks named "%s" / "%s (...)" not covered %s, covered but not that gun %s'
                                 % (o['gun'], o['name'], o['name'], sorted(have - want), sorted(want - have)))
                report.append((st, o['gun'], 'coverage', '%d tiks named "%s" / "%s (...)"' % (len(have), o['name'], o['name']),
                               ('all covered' if have == want else 'MISMATCH') + (', left as released on purpose: %s' % sorted(left) if left else '')))
            elif o['op'] == 'P':
                tool = os.path.join(L.PROP, o['lane'], 'tools', o['tool'])
                if modp and not dry:
                    r = subprocess.run([sys.executable, tool, L.MOD], capture_output=True, text=True)
                    res = (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else 'rc %d' % r.returncode
                    if r.returncode:
                        fails.append('%s failed: %s' % (o['tool'], res))
                else:
                    res = 'not run (give --mod-patches)'
                report.append((st, o['gun'], 'mod patch', o['lane'] + '/tools/' + o['tool'] + ' <mod tree>', res))

    # row files: write-out bytes + every row clip must resolve (shipped now, or loadable from the released set)
    for rel, (lines, nl) in rowfiles.items():
        data = nl.join(lines)
        if mixed_endings(data):
            fails.append('%s: mixed line endings after the row merge' % rel)
        k = key_of(rel)
        out[k] = data
        owner[k] = ('row file', 0, 'manifest (base)')
        report.append((0, 'row file', 'manifest (base)', k, 'same' if open(os.path.join(L.FIX, *k.split('/')), 'rb').read() == data else 'WRITE'))
    shipped = {k.lower() for k in out}
    for k, v in list(owner.items()):
        if isinstance(k, tuple):
            clip = k[1]
            if clip.lower() not in shipped and not vfs.holders(clip):
                fails.append('row %s points at %s, which is neither shipped nor loadable' % (v[2], clip))
            del owner[k]

    for st, gun, kind, what, act in sorted(report, key=lambda r: (r[0], r[1], r[2] == 'coverage', r[3].lower())):
        print('step %d | %-12s | %-34s | %s | %s' % (st, gun, kind, what, act))
    for f in fails:
        print('FAIL', f)
    if fails:
        return 1
    if dry:
        print('dry run: %d files, nothing written' % len(out))
        return 0
    n = 0
    for k, data in sorted(out.items()):
        dst = os.path.join(L.FIX, *k.split('/'))
        if k not in man:
            kind = owner[k][2]
            if kind == 'base':
                mp = os.path.join(L.MOD, *vfs.mod[k.lower()].split('/'))
                bp = os.path.join(L.FIXBASE, *k.split('/'))
                os.makedirs(os.path.dirname(bp), exist_ok=True)
                shutil.copy2(mp, bp)
                man[k] = {'base_md5': L.md5(open(mp, 'rb').read()), 'base_ticks': L.ticks_of(mp),
                          'base_from': 'docs/tools/assets/fixes_base/' + k}
            elif kind.startswith('base_pak'):
                below, _a = vfs.below_fixes(k)
                man[k] = {'base_pak': below[1], 'base_md5': L.md5(vfs.read_from(below, k))}
            else:
                assert kind == 'new', kind
                man[k] = {'new': 'True'}
        if not os.path.isfile(dst) or open(dst, 'rb').read() != data:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(data)
            n += 1
    txt = json.dumps(man, indent=1, sort_keys=True) + '\n'
    cur = open(L.MAN, encoding='utf-8').read()
    style = json.dumps(json.loads(cur), indent=1, sort_keys=True) + '\n'
    if style != cur:            # keep the manifest's own formatting when it is not ours
        for ind in (2, 4, 1):
            for sk in (True, False):
                if json.dumps(json.loads(cur), indent=ind, sort_keys=sk) + '\n' == cur or json.dumps(json.loads(cur), indent=ind, sort_keys=sk) == cur:
                    txt = json.dumps(man, indent=ind, sort_keys=sk) + ('\n' if cur.endswith('\n') else '')
    if txt != cur:
        open(L.MAN, 'w', encoding='utf-8', newline='').write(txt)
    print('wrote %d file(s); manifest %d entries' % (n, len(man)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
