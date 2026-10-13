"""The heavy lane's rows: fps_anims_mg.txt / fps_anims_shotgun.txt = the RELEASED fixes-pak copy + the edits below.

Both files are this lane's (no other lane stages them), so the full patched copy is written into heavy/assets; the
edits stay declarative here so the copy can be rebuilt on a newer released file (apply-on-top).

    python stage_rows.py [--without row,row]     -> assets/models/player/base/fps_anims_{mg,shotgun}.txt
`--without` leaves those rows as released (a BEFORE overlay for a still pair).
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hv

# class -> [(row, clip, crossblend or None = keep / default 0.1, comment)]: an existing row is repointed, a new one is
# appended before the file's closing brace
EDITS = {
    'mg': [
        # step 1 (2026-10-12): aim pose with the support hand where the hip pose has it (handpose.py)
        ('bar_charge', 'viewmodel/mg/coop_bar_ads_hand.skc', None, 'support hand on the forearm as at the hip'),
        ('dp28_charge', 'viewmodel/coop_dp28/coop_dp28_ads_hand.skc', None, 'support hand on the forend as at the hip'),
        ('vickers_charge', 'viewmodel/Vickers/coop_vickers_ads_hand.skc', None, 'support hand on the forend as at the hip'),
        ('breda_charge', 'viewmodel/breda/coop_breda_ads_hand.skc', None, 'support hand under the receiver as at the hip'),
        # step 2: BAR aimed reload to the three rules (heavybake.py); an EMPTY gun gets the handle work
        ('bar_reload_ads', 'viewmodel/mg/bar_reload_ads.skc', None, 'aimed, rounds left: magazine only'),
        ('bar_reload_empty', 'viewmodel/mg/reload_bar.skc', 0.3, 'retail: hip reload of an empty gun (the retail clip; the row lets cgame find _empty_ads)'),
        ('bar_reload_empty_ads', 'viewmodel/mg/bar_reload_empty_ads.skc', 0.1, 'aimed, empty: magazine, then the left hand works the operating handle'),
        # 2b: braced variants (cgame ads-heavy-next picks <row>_adsb when the brace envelope is up): half the sag
        ('bar_reload_adsb', 'viewmodel/mg/bar_reload_adsb.skc', 0.1, 'aimed + braced, rounds left'),
        ('bar_reload_empty_adsb', 'viewmodel/mg/bar_reload_empty_adsb.skc', 0.1, 'aimed + braced, empty'),
        # step 3: StG 44 (heavybake.py mp44). mp44_reload_ads keeps its path: the staged clip REPLACES the shipped one
        ('mp44_reload_ads', 'viewmodel/mp44/mp44_reload_ads.skc', None, 'aimed, rounds left: magazine only (closed bolt, one in the chamber)'),
        # hip, rounds left (heavybake.py mp44 --hip): the retail clip cocked in EVERY reload - now only an empty gun does
        ('mp44_reload', 'viewmodel/mp44/coop_mp44_reload_hip.skc', None, 'hip, rounds left: magazine only, no cock (closed bolt, one in the chamber)'),
        ('mp44_reload_empty', 'viewmodel/mp44/mp44_reload.skc', 0.3, 'retail: hip reload of an empty gun (the retail clip; the row lets cgame find _empty_ads)'),
        ('mp44_reload_empty_ads', 'viewmodel/mp44/mp44_reload_empty_ads.skc', 0.1, 'aimed, empty: magazine, then the left hand cocks the handle and lets it fly'),
        ('mp44_reload_adsb', 'viewmodel/mp44/mp44_reload_adsb.skc', 0.1, 'aimed + braced, rounds left'),
        ('mp44_reload_empty_adsb', 'viewmodel/mp44/mp44_reload_empty_adsb.skc', 0.1, 'aimed + braced, empty'),
        # step 4: DP-28 (heavybake.py dp28). dp28_reload_ads keeps its path: the staged clip REPLACES the shipped one
        ('dp28_reload_ads', 'viewmodel/coop_dp28/dp28_reload_ads.skc', None, 'aimed, rounds left: the pan swapped under the box (open bolt held by the sear: no handle)'),
        ('dp28_reload_empty', 'viewmodel/coop_dp28/dp28_reload.skc', 0.3, 'retail: hip reload of an empty gun (the pack clip; the row lets cgame find _empty_ads)'),
        ('dp28_reload_empty_ads', 'viewmodel/coop_dp28/dp28_reload_empty_ads.skc', 0.1, 'aimed, empty: the pan, then the left hand hauls the handle and lets it fly'),
        ('dp28_reload_adsb', 'viewmodel/coop_dp28/dp28_reload_adsb.skc', 0.1, 'aimed + braced, rounds left'),
        ('dp28_reload_empty_adsb', 'viewmodel/coop_dp28/dp28_reload_empty_adsb.skc', 0.1, 'aimed + braced, empty'),
        # FG 42 Irons (fg42irons.py / fg42tik.py / fg42pose.py): the per-weapon aim pose; the scoped FG 42 has none
        ('coopr_fg_42_irons_charge', 'viewmodel/fg42/coop_fg42_irons_aim.skc', 0.1, 'FG 42 Irons: aim pose (StG pose pushed out, support hand on the wooden handguard)'),
        # FG 42, both guns (fg42bake.py): the HIP reload rebuilt - magazine in from the left with a closed hand; an
        # EMPTY gun gets the right-side charging handle worked by the firing hand (91 frames = the weapon row's 3.0 s)
        ('fg42_reload', 'viewmodel/fg42/coop_fg42_reload_hip.skc', None, 'FG 42 hip, rounds left: side magazine, no handle'),
        ('fg42_reload_empty', 'viewmodel/fg42/coop_fg42_reload_hip_empty.skc', 0.05, 'FG 42 hip, empty: side magazine, then the firing hand works the charging handle'),
        # FG 42 Irons only (the scoped gun's scope picture is not ours): the per-weapon base rows let cgame find _ads
        ('coopr_fg_42_irons_reload', 'viewmodel/fg42/coop_fg42_reload_hip.skc', 0.05, 'FG 42 Irons hip, rounds left (= fg42_reload)'),
        ('coopr_fg_42_irons_reload_empty', 'viewmodel/fg42/coop_fg42_reload_hip_empty.skc', 0.05, 'FG 42 Irons hip, empty (= fg42_reload_empty)'),
        ('coopr_fg_42_irons_reload_ads', 'viewmodel/fg42/fg42_irons_reload_ads.skc', 0.1, 'FG 42 Irons aimed, rounds left'),
        ('coopr_fg_42_irons_reload_empty_ads', 'viewmodel/fg42/fg42_irons_reload_empty_ads.skc', 0.1, 'FG 42 Irons aimed, empty: + the charging handle'),
        ('coopr_fg_42_irons_reload_adsb', 'viewmodel/fg42/fg42_irons_reload_adsb.skc', 0.1, 'FG 42 Irons aimed + braced, rounds left'),
        ('coopr_fg_42_irons_reload_empty_adsb', 'viewmodel/fg42/fg42_irons_reload_empty_adsb.skc', 0.1, 'FG 42 Irons aimed + braced, empty'),
        # M1919 .30 cal portable (m1919sights.py / handpose.py m1919 / beltbake.py) - the BAR's hands prefix, so every row is
        # a per-weapon row. The hip row for rounds left, coopr_m1919_30cal_reload, is in the SHARED anims_shared.txt:
        # wire/patch_m1919_rows.py repoints it (a patch, not a staged copy)
        ('coopr_m1919_30cal_charge', 'viewmodel/mg/coop_m1919_ads_hand.skc', 0.1, 'M1919: aim pose, the support hand cups the receiver as at the hip'),
        ('coopr_m1919_30cal_reload_empty', 'viewmodel/coop_m1919/coop_m1919_reload_hip_empty.skc', 0.3, 'M1919 hip, empty: cover, belt, cover, then the firing hand works the charging handle'),
        ('coopr_m1919_30cal_reload_ads', 'viewmodel/coop_m1919/m1919_reload_ads.skc', 0.1, 'M1919 aimed, rounds left: down under the box, cover, belt, cover, back to the aim'),
        ('coopr_m1919_30cal_reload_empty_ads', 'viewmodel/coop_m1919/m1919_reload_empty_ads.skc', 0.1, 'M1919 aimed, empty: the same, then the charging handle worked in the aim'),
    ],
    'shotgun': [
        # shotgun reload (sgbake.py): the three aimed rows keep their SHIPPED paths - the staged clips replace them.
        # The pump only when the gun was empty (cgame ads-heavy-next, apply_sgpump.py): `_loaded` end rows
        ('shotgun_reload_end_loaded', 'viewmodel/shotgun/coop_shotgun_reload_end_loaded.skc', 0.05, 'hip, rounds were left: the retail end with the pump cut out'),
        ('shotgun_reload_end_loaded_ads', 'viewmodel/shotgun/shotgun_reload_end_loaded_ads.skc', 0.1, 'aimed, rounds were left: back up into the aim, no pump'),
        # the reload broken off by the trigger with a round chambered (state file: patch_sgbreak.py stage 2; cgame apply_sgbreak.py)
        ('shotgun_reload_end_break', 'viewmodel/shotgun/coop_shotgun_reload_end_break.skc', 0.12, 'hip, break-off with a round chambered: hand to the forend in 0.37 s, no pump'),
        ('shotgun_reload_end_break_ads', 'viewmodel/shotgun/shotgun_reload_end_break_ads.skc', 0.12, 'aimed, break-off with a round chambered: up into the aim in 0.37 s'),
        # FOLLOW-UP 2026-10-13 (SHOTGUN_PUMP_FIX.md; user: "the shotgun doesnt have the pumping action when in ads"): the
        # aimed per-shot cycle - cgame apply_cyclewpn.py plays coopr_<weapon key>_cycle_ads when the clip ammo drops in
        # the aim (the server holds the hands at `charge` through an aimed shot). Per-weapon rows: the pump gun only
        ('coopr_shotgun_cycle', 'viewmodel/shotgun/fire_shotgun_stand.skc', 0.05, 'retail: the hip fire clip (pump stroke at the same frames) - what an aim let go in mid-pump hands over to'),
        ('coopr_shotgun_cycle_ads', 'viewmodel/shotgun/coop_shotgun_cycle_ads.skc', 0.05, 'aimed, after a shot with rounds left: the support hand racks the forend, the gun stays on target (sgpump.py)'),
        ('coopr_shotgun_cyclelast', 'viewmodel/shotgun/fire_shotgun_stand.skc', 0.05, 'retail: as coopr_shotgun_cycle, after the last round'),
        ('coopr_shotgun_cyclelast_ads', 'viewmodel/shotgun/coop_shotgun_cycle_ads.skc', 0.05, 'aimed, after the LAST round: the same stroke (the hip clip pumps after every shot)'),
    ],
}


PIN = '993f706'      # base revision of the released rows files; `--live` = the working copy instead


def build(cls, without=()):
    rel = 'models/player/base/fps_anims_%s.txt' % cls
    if PIN:        # the released copy AS COMMITTED at PIN (the coordinator's integration rewrites the working copy while it runs)
        import subprocess
        txt = subprocess.check_output(['git', '-C', r'C:\mohaa-coop-dev', 'show', '%s:docs/tools/assets/fixes/%s' % (PIN, rel)]).decode('latin-1')
    else:
        txt = open(os.path.join(hv.FIXES, rel.replace('/', os.sep)), 'rb').read().decode('latin-1')
    nl ='\r\n' if '\r\n' in txt else '\n'
    new = []
    for row, clip, xb, why in EDITS[cls]:
        if row in without:
            continue
        rx = re.compile(r'(?m)^(\s*%s\s+)(\S+)([^\r\n]*)' % re.escape(row))
        ms = [m for m in rx.finditer(txt) if not m.group(0).lstrip().startswith('//')]
        if ms:
            assert len(ms) == 1, (row, len(ms))
            m = ms[0]
            rest = m.group(3)
            if xb is not None:
                rest = re.sub(r'crossblend\s+[\d.]+', 'crossblend %s' % xb, rest) if 'crossblend' in rest else rest + '\tcrossblend %s' % xb
            txt = txt[:m.start()] + m.group(1) + clip + rest + txt[m.end():]
        else:
            new.append('\t%s\t\t%s\t\tcrossblend %s\t// HZM coop [ads heavy] %s' % (row, clip, xb if xb is not None else 0.1, why))
        chk = [l for l in (txt.splitlines() + new) if l.split('//')[0].split()[:1] == [row]]
        assert len(chk) == 1 and clip in chk[0], (row, chk)
    if new:
        k = txt.rstrip().rfind('}')
        txt = txt[:k] + '\t//===================== HZM coop ADS heavy lane (staged 2026-10-12) =====================' + nl + nl.join(new) + nl + txt[k:]
    # every clip a row of ours names must exist in the staging tree
    for row, clip, xb, why in EDITS[cls]:
        if row not in without and not why.startswith('retail:'):
            assert os.path.isfile(hv.staged('models/human/animation/' + clip)), 'missing staged clip ' + clip
    dst = hv.staged(rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(txt.encode('latin-1'))
    print('%s: %d edits (%d skipped) -> %s' % (cls, len(EDITS[cls]), len([e for e in EDITS[cls] if e[0] in without]), rel))


if __name__ == '__main__':
    wo = ()
    if '--live' in sys.argv:     # base = the working copy (carries the coordinator's integration rows while it runs)
        PIN = None
    if '--without' in sys.argv:
        wo = tuple(sys.argv[sys.argv.index('--without') + 1].split(','))
    for c in EDITS:
        build(c, wo)
