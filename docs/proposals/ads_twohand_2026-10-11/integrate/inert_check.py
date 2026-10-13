"""inert_check.py - is the merged cgame's NEW behaviour inert for everything that is not part of the rollout?

The merged cgame (integ-ads) carries code of lanes whose guns are not shipping (pistols, G 43 Irons, FG 42 Irons ...).
Every one of those features is keyed on a NAME - a hands row in models/player/base/*.txt or a gun row in a weapon
tik - and does nothing when the name is absent. This lists every such name the INTEGRATED file set carries, with its
owner, so a name that belongs to no rollout gun stands out.

  hands rows:  coopr_<weapon>_<any suffix> (per-weapon rows; before the merge only the reload rows were looked up),
               <row>_empty[_ads|_adsb], <row>_adsb, <row>_loaded[_ads], <row>_break[_ads], <prefix>_cycle[_ads]
  gun rows:    reload_ads_loaded, reload_ads_empty, reload_empty, reload_end_ads, reload_single_ads, reload_end_loaded,
               rechamber_ads   (in ANY weapon tik the game can load, retail and third-party paks included)
    python inert_check.py      exit 1 when a name has no owner in OWNERS
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intlib as L

HAND_RX = re.compile(r'^(coopr_.*|.*_empty(_ads|_adsb)?|.*_adsb|.*_loaded(_ads)?|.*_break(_ads)?|.*_cycle(_ads)?)$')
GUN_ROWS = ('reload_ads_loaded', 'reload_ads_empty', 'reload_empty', 'reload_end_ads', 'reload_single_ads', 'reload_end_loaded', 'rechamber_ads')
# hands row (regex) -> owner. RELEASED = the row is in the released row files and was already looked up by the released cgame
OWNERS = [
    (r'^coopr_bar_charge$|^bar_reload_(empty|adsb|empty_ads|empty_adsb)$', 'step 1 BAR'),
    (r'^mp44_reload_(empty|adsb|empty_ads|empty_adsb)$', 'step 1 StG 44'),
    (r'^dp28_reload_(empty|adsb|empty_ads|empty_adsb)$', 'step 1 DP-28'),
    (r'^shotgun_reload_end_(loaded|loaded_ads|break|break_ads)$', 'step 1 Shotgun'),
    (r'^shotgun_reload_break$', 'step 1 Shotgun (the TORSO row of the quick break-off, anims_shotgun.txt - played by the state file)'),
    (r'^coopr_mp40_(charge|reload|reload_empty|reload_ads|reload_empty_ads)$', 'step 2 MP40'),
    (r'^coopr_silenced_mp40_(charge|reload|reload_empty|reload_ads|reload_empty_ads)$', 'step 2 Silenced MP40'),
    (r'^coopr_mp40_reactivated_(reload|reload_empty|reload_ads|reload_empty_ads)$', 'step 2 MP40 R2'),
    (r'^coopr_mp40_mp18_charge$', 'step 2 pin: MP18 keeps the released aim pose'),
    (r'^coopr_[a-z0-9_]+_reload(_single|_end)?$', 'RELEASED per-weapon reload row (looked up by the released cgame too)'),
]
GUN_OWNERS = [
    (r'^models/weapons/(bar|bar_(?!bar1918\.)[a-z0-9_]+|dp28[a-z0-9_]*|mp44[a-z0-9_]*)\.tik$', ('reload_ads_loaded', 'reload_ads_empty', 'reload_empty'), 'step 1'),
    (r'^models/weapons/shotgun[a-z0-9_]*\.tik$', ('reload_end_loaded',), 'step 1 Shotgun'),
    (r'^models/weapons/(mp40|mp40_(?!mp18)[a-z0-9_]+|mp40silenced)\.tik$', ('reload_ads_empty', 'reload_empty'), 'step 2'),
    (r'^models/weapons/(kar98|kar98_(?!g98|mortar)[a-z0-9_]+|springfield_unscoped|mosin_nagant_rifle[a-z0-9_]*|enfield|enfield_(?!p14)[a-z0-9_]+)\.tik$',
     ('rechamber_ads',), 'step 3'),
]


def main():
    v = L.Vfs(L.FIX)
    bad = 0
    print('== hands rows the merged cgame newly reacts to (integrated row files)')
    seen = {}
    for rel in set(v.fixnames.values()) | set(v.mod.values()) | {n for low in v._low.values() for n in low.values()}:
        if re.match(r'models/player/base/[^/]+\.txt$', rel.lower()):
            b = v.read(rel)
            for r in L.tik_rows(b.decode('latin-1')):
                if HAND_RX.match(r[0].lower()):
                    seen.setdefault(r[0].lower(), rel.lower().split('/')[-1])
    by = {}
    for row, src in sorted(seen.items()):
        own = next((o for rx, o in OWNERS if re.match(rx, row)), None)
        if own is None:
            bad += 1
            print('  NO OWNER: %s (%s)' % (row, src))
        else:
            by.setdefault(own, []).append(row)
    for own in sorted(by):
        print('  %-70s %d row(s): %s' % (own, len(by[own]), ' '.join(by[own][:6]) + (' ...' if len(by[own]) > 6 else '')))
    print('== gun rows the merged cgame newly shows (every weapon tik the game can load)')
    tiks = set()
    for low in list(v._low.values()) + [v.mod, v.fixnames]:
        for n in (low.keys() if isinstance(low, dict) else low):
            if re.match(r'models/weapons/[^/]+\.tik$', n):
                tiks.add(n)
    cnt = {}
    for t in sorted(tiks):
        b = v.read(t)
        if b is None:
            continue
        for r in L.tik_rows(b.decode('latin-1')):
            if r[0].lower() in GUN_ROWS:
                own = next((o for rx, rows, o in GUN_OWNERS if re.match(rx, t) and r[0].lower() in rows), None)
                if own is None:
                    bad += 1
                    print('  NO OWNER: %s :: %s (%s)' % (t, r[0], v.winner(t)[1]))
                else:
                    cnt[(own, r[0].lower())] = cnt.get((own, r[0].lower()), 0) + 1
    for (own, row), n in sorted(cnt.items()):
        print('  %-16s %-18s in %d tik(s)' % (own, row, n))
    print('%d weapon tiks scanned' % len(tiks))
    print('GATE: %s' % ('FAIL - %d name(s) without an owner' % bad if bad else 'pass - every name the merged cgame reacts to belongs to a rollout gun (or was released)'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
