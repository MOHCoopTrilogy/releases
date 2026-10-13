"""rowpick.py - which first-person HANDS row (and clip file) each weapon plays, released against integrated.

An offline copy of the row choice in cgame (cg_viewmodelanim.c CG_ViewModelAnimation): prefix row -> per-weapon row
`coopr_<weapon key>_<suffix>` (full name, then the name without its "(finish)") -> `_empty` when the reload starts on
an empty gun -> `_ads` / `_adsb` while aiming. RELEASED = the released row files + the released cgame's rules
(per-weapon rows for the reload rows only; no `_empty`, no `_adsb`, no per-weapon aim pose); INTEGRATED = the working
copy of the fixes row files + the merged cgame's rules. A weapon that is NOT part of the rollout must resolve to the
same clip BYTES in both; a weapon that is must resolve to a row that exists and a clip that loads.

    python rowpick.py            the table + the verdict per weapon (exit 1 when an out-of-scope weapon changed)
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intlib as L

# (weapon name as the tik has it, animation prefix as CG_GetVMAnimPrefixIndex returns it, in the rollout?)
# 2 = not in the rollout AND on another mesh than the rifle its prefix was authored for: CoopAdsClipFitsHeldGun (in the
# released cgame too) keeps such a gun on the hip clips of the four bolt rifles, so the `_ads` row is never chosen
# 3 = not in the rollout and WITHOUT A MAGAZINE (tik: clipsize 0 - the coop binoculars): no reload can start, so the
# reload cases are not compared; every other case must be unchanged
WEAPONS = [
    ('BAR', 'bar', 1), ('BAR (Gold)', 'bar', 1), ('BAR (M1918 Classic)', 'bar', 1), ('BAR (Pacific)', 'bar', 1),
    ('Lewis Gun', 'bar', 0), ('M1919 30cal', 'bar', 0), ('MG42', 'bar', 0),
    ('StG 44', 'mp44', 1), ('StG 44 (Strapped)', 'mp44', 1), ('DP-28', 'dp28', 1), ('DP-28 (Gold)', 'dp28', 1),
    ('Shotgun', 'shotgun', 1), ('Shotgun (Gold)', 'shotgun', 1),
    ('MP40', 'mp40', 1), ('MP40 (Gold)', 'mp40', 1), ('MP40 (Reactivated)', 'mp40', 1), ('Silenced MP40', 'mp40', 1),
    ('MP40 (MP18)', 'mp40', 0), ('M3 Grease Gun', 'mp40', 0), ('Silenced Grease Gun', 'mp40', 0), ('Silenced PPS-43', 'mp40', 0),
    ('Mauser KAR 98K', 'kar98', 1), ('Mauser KAR 98K (Gewehr 98)', 'kar98', 2), ('Arisaka Type 99', 'kar98', 2),
    ("Springfield M1903", 'springfield', 1), ('Mosin Nagant Rifle', 'mosin', 1), ('Lee-Enfield', 'enfield', 1),
    ('Lee-Enfield (P14 Enfield)', 'enfield', 2),
    ('Thompson', 'thompson', 0), ('Sten', 'sten', 0), ('M1 Garand', 'garand', 0), ('FG 42', 'fg42', 0),
    # ---- step 4, pistols (prefix as CG_GetVMAnimPrefixIndex returns it: a pistol-class name it does not list = colt45)
    ('Colt 45', 'colt45', 1), ('Colt 45 (Gold)', 'colt45', 1), ('Colt 45 (Pacific)', 'colt45', 1), ('Silenced Colt .45', 'colt45', 1),
    ('Walther P38', 'p38', 1), ('Walther P38 (Gold)', 'p38', 1), ('Silenced Walther P38', 'colt45', 1),
    ('Beretta', 'beretta', 1), ('Silenced Beretta', 'colt45', 1), ('Luger P08', 'colt45', 1), ('Silenced Luger P08', 'colt45', 1),
    ('Nambu Type 14', 'colt45', 1), ('Walther PPK', 'colt45', 1), ('TT-33 Tokarev', 'colt45', 1), ('Silenced TT-33', 'colt45', 1),
    ('Welrod', 'colt45', 1), ('Welrod (Gold)', 'colt45', 1), ('Hi-Standard Silenced', 'histandard', 1),
    ('Webley Revolver', 'webley', 1), ('Webley Revolver (Gold)', 'webley', 1), ('Webley Mk VI', 'webley', 1),
    ('Nagant Revolver', 'nagantrev', 1), ('Nagant Revolver (Blued)', 'nagantrev', 1),
    # pistol-class weapons that are NOT in the cut (every one the game can load): held on the released clips
    ('Mauser C96', 'p38', 0), ('Mauser C96 (Gold)', 'p38', 0), ('Mauser C96 (Trench C96)', 'p38', 0),
    ('S&W M10 .38', 'm10', 0), ('S&W M10 .38 (Gold)', 'm10', 0), ('Bombing Run', 'colt45', 3), ('Bombing Run (Gold)', 'colt45', 3),
    ('G 43', 'g43', 0), ('G43 Sniper', 'g43', 0), ('G 43 Irons', 'g43', 1), ('G 43 Irons (Gold)', 'g43', 1),
    ('PPSH SMG', 'ppsh', 0), ('Vickers-Berthier', 'vickers', 0), ('Breda', 'breda', 0),
]
# (label, suffix, aiming, empty, braced)
CASES = [('aim pose', 'charge', 0, 0, 0), ('hip reload', 'reload', 0, 0, 0), ('hip reload, emptied', 'reload', 0, 1, 0),
         ('aimed reload', 'reload', 1, 0, 0), ('aimed reload, emptied', 'reload', 1, 1, 0), ('aimed reload, braced', 'reload', 1, 0, 1),
         ('aimed reload, emptied, braced', 'reload', 1, 1, 1),
         ('reload single', 'reload_single', 0, 0, 0), ('aimed reload single', 'reload_single', 1, 0, 0),
         ('reload end', 'reload_end', 0, 1, 0), ('aimed reload end', 'reload_end', 1, 1, 0),
         ('reload end, rounds were left', 'reload_end', 0, 0, 0), ('aimed reload end, rounds were left', 'reload_end', 1, 0, 0),
         ('bolt', 'rechamber', 0, 0, 0), ('aimed bolt', 'rechamber', 1, 0, 0), ('idle', 'idle', 0, 0, 0), ('fire', 'fire', 0, 0, 0),
         ('aimed per-shot cycle (client-only)', 'cycle', 1, 0, 0)]


def key(name):
    out, gap = '', False
    for c in name.lower():
        if c.isascii() and c.isalnum():
            if gap and out:
                out += '_'
            out += c
            gap = False
        else:
            gap = True
    return out


def strip(name):
    m = re.match(r'^(.*\S)\s*\([^()]*\)\s*$', name)
    return m.group(1) if m else None


def table(vfs):
    rows = {}
    for rel in set(vfs.fixnames.values()) | set(vfs.mod.values()):
        if re.match(r'models/player/base/(fps_anims_[^/]+|anims_shared)\.txt$', rel.lower()):
            w = vfs.winner(rel)
            for r in L.tik_rows(vfs.read(rel).decode('latin-1')):
                rows.setdefault(r[0].lower(), 'models/human/animation/' + r[1])
    return rows


GUARDED = ('kar98', 'springfield', 'mosin', 'enfield')


def pick(rows, name, prefix, suffix, aiming, empty, braced, merged, othermesh=False):
    an = '%s_%s' % (prefix, suffix)
    perw = suffix in ('reload', 'reload_single', 'reload_end') or (merged and True)
    if perw:
        for nm in (name, strip(name)):
            if nm is None:
                break
            t = 'coopr_%s_%s' % (key(nm), suffix)
            if t in rows:
                an = t
                break
    if merged and suffix == 'reload_end' and not empty and (an + '_loaded') in rows:
        an += '_loaded'
    if merged and suffix == 'reload' and empty and (an + '_empty') in rows:
        an += '_empty'
    if aiming and suffix in ('reload', 'reload_single', 'reload_end', 'rechamber', 'cycle') and not (othermesh and prefix in GUARDED):
        ads = an + '_ads'
        if merged and braced and (an + '_adsb') in rows:
            ads = an + '_adsb'
        if ads in rows:
            an = ads
    return an


def main():
    old, new = L.Vfs(('git', L.RELEASED_REV)), L.Vfs(L.FIX)
    ro, rn = table(old), table(new)
    bad = 0
    print('weapon | case | released row | integrated row | verdict')
    for name, prefix, inscope in WEAPONS:
        changed = []
        for label, suffix, aiming, empty, braced in CASES:
            if inscope == 3 and suffix.startswith('reload'):
                continue
            a = pick(ro, name, prefix, suffix, aiming, empty, braced, False, inscope == 2)
            b = pick(rn, name, prefix, suffix, aiming, empty, braced, True, inscope == 2)
            if a not in ro and b not in rn:
                continue                      # the weapon has no such row at all (e.g. no bolt)
            ca, cb = ro.get(a), rn.get(b)
            da, db = (old.read(ca) if ca else None), (new.read(cb) if cb else None)
            if cb and db is None:
                print('%s | %s | %s | %s | CLIP DOES NOT LOAD: %s' % (name, label, a, b, cb))
                bad += 1
                continue
            if da == db:
                continue
            changed.append(label)
            if inscope != 1:
                bad += 1
            print('%s | %s | %s -> %s | %s -> %s | %s' % (name, label, a, os.path.basename(ca or '-'), b, os.path.basename(cb or '-'),
                                                         'new clip (in the rollout)' if inscope == 1 else 'CHANGED - NOT IN THE ROLLOUT'))
        if not changed:
            print('%s | all %d cases | | | %s' % (name, len(CASES), 'UNCHANGED (same clip bytes)' + (' - but it is in the rollout?' if inscope == 1 else '')))
    print('GATE: %s' % ('FAIL (%d)' % bad if bad else 'pass - no weapon outside the rollout resolves to a different hands clip'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
