#!/usr/bin/env python3
"""
GLOVE CONTENT GENERATOR (bug-2080).

Authors the glove shader variants onto every model the armory can put a player in - the third-person
body TIK and its first-person `_fps` twin - so one per-surface skin index selects the same glove in
both views.

WHY GENERATED. This touches 135 uniforms x 2 files, and the armory roster changes whenever a skin
pack lands. A hand-edited set would drift the first time somebody added a uniform, and drift
silently (the glove row would just quietly not work on the new skin). Per .wolf/OPENWOLF.md,
anything derivable is generated.

MECHANISM. A TIKI surface takes its skins from repeated `surface <name> shader <x>` lines, in order:
the first is index 0, the next index 1, and so on. The engine resolves
`MDL_SURFACE_SKININDEX(bsurf)` = bits 0,1 and 6 of the per-surface byte, giving 0-7 (q_shared.h).
Index 0 is deliberately left as whatever hand shader the model already had, so no uniform loses its
own look and an un-set player is correct by default.

    python docs/tools/gen_gloves.py            # report what would change
    python docs/tools/gen_gloves.py --write    # do it
"""
import io
import os
import re
import sys
import glob
import zipfile

MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'
PLAYER_DIR = os.path.join(MOD, 'models', 'player')
TAG = '// HZM coop GLOVES [gen_gloves.py] - do not hand-edit'

PAK_ROOTS = [r'G:\GOG\Medal of Honor - Allied Assault War Chest', r'G:\mohaa-gl2']

# ---------------------------------------------------------------------------------------------
# THE ROSTER. Index 0 is the model's own bare hands and is never written here.
# Every shader below already ships in a retail or already-installed pak - no new art, no licence
# exposure. Where a glove has no first-person twin of its own, the nearest existing 1P glove is
# reused rather than shipping a bare-handed first person for a gloved third person; that mismatch
# would read as a bug. Noted per row.
# ---------------------------------------------------------------------------------------------
ROSTER = [
    # idx, name,                 3P shader on `hand`, 1P shader on the three fps hand surfaces
    (1, 'Leather Gloves',        'l_gloves',      'lthr_gloveview'),
    (2, 'Wool Knit Gloves',      'knitgloves1',   'grmn_winter_glove'),
    (3, 'US Winter Gloves',      'handssnow',     'coop_glove_uswinter_view'),
    # These two had no first-person twin in any pak. Rather than show a different glove down the
    # sights, docs/tools/gen_glove_views.py derives a 1P texture from the nearest existing 1P glove
    # (already correct for the 1P UV layout) recoloured to the 3P glove's mean colour.
    (4, 'Wool Mittens',          'mittens2',      'coop_glove_mittens_view'),
    (5, "Seaman's Gloves",       'seaman_gloves', 'coop_glove_seaman_view'),
    # [user 2026-08-23] "if it can be 3p only I dont want those included." Paratrooper Hands was
    # dropped here: its 3P look was real (pt_hands) but its only 1P option was plain `handview` -
    # the SAME texture Bare Hands uses - so down the sights it was indistinguishable from wearing
    # nothing. Every surviving row has a first-person look distinct from bare hands.
    (6, 'Alpine Hands',          'hands_snow1',   'handviewcold'),
]

FPS_HAND_SURFACES = ('triggerhand', 'lefthand', 'garandhand')


def pak_index():
    idx = {}
    paks = []
    for r in PAK_ROOTS:
        for d in ('main', 'mainta', 'maintt'):
            paks += glob.glob(os.path.join(r, d, '*.pk3'))
    for p in sorted(paks):
        if 'zzzzzz_co-op' in os.path.basename(p).lower():
            continue          # our own pk3 - never source content from what we are generating
        try:
            z = zipfile.ZipFile(p)
        except Exception:
            continue
        for n in z.namelist():
            idx[n.lower().replace('\\', '/')] = (p, n)
    return idx


def armory_skins():
    t = io.open(os.path.join(MOD, 'coop_mod', 'helmet.scr'), encoding='utf-8', errors='replace').read()
    t = '\n'.join(l.split('//')[0] for l in t.splitlines())
    return [m.group(1) for m in re.finditer(r'coop_armorySkins\[\d+\]\s*=\s*"([^"]*)"', t)]


def strip_generated(text):
    """Idempotent: remove any lines this generator previously added."""
    return '\n'.join(l for l in text.splitlines() if TAG not in l)


def inject(text, surface, shaders):
    """Insert glove shader lines directly after the LAST existing `surface <surface> shader` line.

    After the last, not the first: a model may already declare gore variants on that surface, and
    the skin index is positional - inserting in the middle would renumber them and silently swap a
    gore tier for a glove.
    """
    # NOTE: this does NOT strip previously-generated lines. It used to, and that was a bug: the 1P
    # path calls inject() three times on the same text (triggerhand / lefthand / garandhand), so
    # each call wiped the lines the previous one had just added and only garandhand survived. The
    # caller strips ONCE before the first inject instead.
    lines = text.split('\n')
    hits = [i for i, l in enumerate(lines)
            if re.match(r'\s*surface\s+' + re.escape(surface) + r'\s+shader\s+\S+', l, re.I)]
    if not hits:
        return None, 0

    # NORMALISE TO EXACTLY ONE BASE SHADER. The skin index is POSITIONAL, so a model that already
    # declares two base shaders on this surface shifts every glove by one. Measured: exactly one
    # armory uniform does - allied_russian_crazy_boris (handsnew AND handssnow) - and on it
    # "Leather Gloves" would have worn US Winter, "Alpine" would have worn Seaman's, and the last
    # glove would have been unreachable past index 7. Nothing selects that second shader today
    # (players never receive gore bits on `hand`, so the index was always 0), so collapsing to the
    # first is lossless and makes the index contract positional-safe on every model.
    if len(hits) > 1:
        for i in reversed(hits[1:]):
            del lines[i]
        hits = [hits[0]]
    at = hits[-1]
    indent = re.match(r'(\s*)', lines[at]).group(1)
    add = ['%ssurface %s shader %s\t%s (%d: %s)' % (indent, surface, sh, TAG, i, nm)
           for (i, nm, sh) in shaders]
    return '\n'.join(lines[:at + 1] + add + lines[at + 1:]), len(add)


def ensure_local(rel, idx):
    """Return the on-disk path for a player TIK, extracting a pak-only one into the mod first."""
    local = os.path.join(PLAYER_DIR, os.path.basename(rel))
    if os.path.exists(local):
        return local, False
    hit = idx.get(rel.lower())
    if not hit:
        return None, False
    data = zipfile.ZipFile(hit[0]).read(hit[1])
    io.open(local, 'wb').write(data)
    return local, True


def main():
    write = '--write' in sys.argv
    idx = pak_index()
    skins = armory_skins()

    tp = [(i, nm, sh) for (i, nm, sh, _f) in ROSTER]
    fp = [(i, nm, f) for (i, nm, _sh, f) in ROSTER]

    stats = {'3p': 0, '1p': 0, 'nohat': 0, 'extracted': 0, 'no_hand': [], 'no_fps': [], 'fps_nosurf': []}

    for s in skins:
        # ---- third person
        rel = 'models/player/%s.tik' % s
        path, ex = ensure_local(rel, idx)
        if ex:
            stats['extracted'] += 1
        if not path:
            stats['no_hand'].append(s + ' (tik not found at all)')
        else:
            t = strip_generated(io.open(path, encoding='latin-1').read())
            out, n = inject(t, 'hand', tp)
            if out is None:
                stats['no_hand'].append(s)
            else:
                stats['3p'] += 1
                if write:
                    io.open(path, 'w', encoding='latin-1', newline='\n').write(out)

        # ---- the _nohat twin, which is the model an armory player ACTUALLY WEARS.
        # helmet.scr:1381 and player.scr:1282/1320 all dress armory players in the hatless variant
        # (bug-1545), so authoring only <skin>.tik put the gloves on a model nobody wears: numskins
        # stayed 1 on the worn model and the renderer clamped every glove index back to 0. Third
        # person was therefore completely inert while FIRST person worked - precisely the 3P/1P
        # mismatch this feature exists to avoid.
        nrel = 'models/player/%s_nohat.tik' % s
        npath, nex = ensure_local(nrel, idx)
        if nex:
            stats['extracted'] += 1
        if npath:
            t = strip_generated(io.open(npath, encoding='latin-1').read())
            out, n = inject(t, 'hand', tp)
            if out is not None:
                stats['nohat'] += 1
                if write:
                    io.open(npath, 'w', encoding='latin-1', newline='\n').write(out)

        # ---- first person
        frel = 'models/player/%s_fps.tik' % s
        fpath, fex = ensure_local(frel, idx)
        if fex:
            stats['extracted'] += 1
        if not fpath:
            stats['no_fps'].append(s)
            continue
        t = strip_generated(io.open(fpath, encoding='latin-1').read())
        touched = 0
        for surf in FPS_HAND_SURFACES:
            out, n = inject(t, surf, fp)
            if out is not None:
                t = out
                touched += 1
        if not touched:
            stats['fps_nosurf'].append(s)
        else:
            stats['1p'] += 1
            if write:
                io.open(fpath, 'w', encoding='latin-1', newline='\n').write(t)

    print('GLOVE CONTENT GENERATOR  (%s)' % ('WROTE' if write else 'dry run'))
    print('  roster              : %d gloves (index 1-%d; 0 = each model\'s own bare hands)'
          % (len(ROSTER), len(ROSTER)))
    print('  armory uniforms     : %d' % len(skins))
    print('  3P tiks authored    : %d' % stats['3p'])
    print('  _nohat authored     : %d   <- the model armory players actually wear' % stats['nohat'])
    print('  1P _fps authored    : %d' % stats['1p'])
    print('  pulled out of paks  : %d' % stats['extracted'])
    if stats['no_hand']:
        print('  NO `hand` SURFACE (%d) - these uniforms cannot show a 3P glove:' % len(stats['no_hand']))
        for s in stats['no_hand'][:12]:
            print('     ' + s)
    if stats['no_fps']:
        print('  NO _fps TIK (%d) - these uniforms cannot show a 1P glove:' % len(stats['no_fps']))
        for s in stats['no_fps'][:12]:
            print('     ' + s)
        if len(stats['no_fps']) > 12:
            print('     ... and %d more' % (len(stats['no_fps']) - 12))
    if stats['fps_nosurf']:
        print('  _fps HAS NO HAND SURFACE (%d): %s' % (len(stats['fps_nosurf']),
                                                       ', '.join(stats['fps_nosurf'][:6])))
    if not write:
        print('\n  (dry run - pass --write to author the files)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
