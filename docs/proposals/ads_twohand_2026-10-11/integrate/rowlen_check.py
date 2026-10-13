"""rowlen_check.py - SERVER TIMING gate: does an integrated tik change the length of a row the server reads?

The server holds WEAPON_RELOADING until the weapon TIK's `reload` clip ends (fgame/weapon.cpp SetWeaponAnim + the
done event), paces fire / rechamber the same way, and the torso state machine waits for ANIMDONE_TORSO of the rows in
models/player/base/anims_*.txt. So a staged file may add client-only rows freely, but a row the server plays must keep
its clip LENGTH, or gameplay timing changes.

    python rowlen_check.py                         every weapon tik + anims_*.txt in docs/tools/assets/fixes
    python rowlen_check.py --tiks a.tik,b.tik      only these (game paths or bare names under models/weapons/)
    python rowlen_check.py --full                  print every row, not only the ones that differ
    python rowlen_check.py --intended r1,r2        rows whose change is intended (still printed, do not fail the gate);
                                                   `row` = in every file, `<file glob>:<row>` = only in matching tiks
                                                   (e.g. mp40*.tik:fire)
    python rowlen_check.py --released-rev <rev>    docs-repo commit that holds the released fixes sources

RELEASED = paks of main / mainta / maintt + the mod tree + docs/tools/assets/fixes at --released-rev;
INTEGRATED = the same with the working copy of docs/tools/assets/fixes. Lengths are read from the .skc header
(frames x frame time). Generic: any list of tiks, any step. Exit 1 on an unjustified change.
"""
import fnmatch, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intlib as L

# names fgame plays on a weapon itself (weapon.cpp / player.cpp SetWeaponAnim) ...
SERVER_STATIC = {'charge', 'clear', 'fire', 'fire_empty', 'holster', 'idle', 'idle0', 'idle1', 'idle2', 'idle_empty',
                 'putaway', 'raise', 'reload', 'secondarycharge', 'secondaryfire', 'secondaryfire_empty'}


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def server_names(vfs):
    """... plus every name a torso row or a state file sends with `weaponcommand <hand> anim <name>`"""
    names = set(SERVER_STATIC)
    rels = set()
    for k, low in vfs._low.items():
        for n in low:
            if re.match(r'models/player/base/[^/]+\.txt$', n):
                rels.add(n)
    rels |= {n for n in vfs.mod if re.match(r'models/player/base/[^/]+\.txt$', n) or re.match(r'(coop_mod|global)/[^/]+\.st$', n)}
    rels |= {n for n in vfs.fixnames if re.match(r'models/player/base/[^/]+\.txt$', n)}
    for r in rels:
        b = vfs.read(r)
        if b:
            for m in re.finditer(r'(?i)weaponcommand\s+\w+\s+anim\s+(\w+)', b.decode('latin-1')):
                names.add(m.group(1).lower())
    return names


def rows_of(vfs, rel):
    b = vfs.read(rel)
    if b is None:
        return None
    rows = L.tik_rows(b.decode('latin-1'))
    out = {}
    dflt = 'models/human/animation' if rel.lower().startswith('models/player/base/') else ''
    for r in rows:
        r = (r[0], r[1], r[2] or dflt)
        cp = L.clip_path(r)
        data = vfs.read(cp)
        out.setdefault(r[0].lower(), (r[1], cp, L.skc_info(data), L.md5(data) if data is not None else None))
    return out


def fmt(x):
    if x is None:
        return '-'
    clip, _cp, info, dig = x
    if info is None:
        return '%s (%s)' % (clip, 'NOT FOUND' if dig is None else 'packed clip ' + dig[:8])
    return '%s %df %.3fs' % (os.path.basename(clip), info[0], info[0] * info[1])


def main():
    rel_rev = arg('--released-rev', L.RELEASED_REV)
    intended = [x.lower() for x in (arg('--intended', '') or '').split(',') if x]

    def is_intended(f, row):
        for x in intended:
            g, _c, r = x.rpartition(':')
            if r == row and (not g or fnmatch.fnmatch(os.path.basename(f).lower(), g)):
                return True
        return False
    full = '--full' in sys.argv
    old, new = L.Vfs(('git', rel_rev)), L.Vfs(L.FIX)
    if '--tiks' in sys.argv:
        files = [t if '/' in t else 'models/weapons/' + t for t in arg('--tiks').split(',')]
    else:
        files = sorted(v for k, v in new.fixnames.items()
                       if (k.startswith('models/weapons/') and k.endswith('.tik') and k.count('/') == 2)
                       or re.match(r'models/player/base/anims_[^/]+\.txt$', k))
    srv = server_names(new)
    bad = n_same = n_rows = 0
    counts = {}
    print('released = fixes @ %s | integrated = working copy | %d file(s)' % (rel_rev, len(files)))
    print('file | row | released | integrated | verdict')
    for f in files:
        a, b = rows_of(old, f), rows_of(new, f)
        if b is None:
            print('%s | - | - | - | NOT IN THE INTEGRATED SET' % f)
            bad += 1
            continue
        torso = f.lower().startswith('models/player/base/')
        a = a or {}
        for row in sorted(set(a) | set(b)):
            n_rows += 1
            x, y = a.get(row), b.get(row)
            server = torso or row in srv
            if x is not None and y is not None and x[1].lower() == y[1].lower() and x[3] == y[3] and (x[3] is None or x[2] is None):
                n_same += 1          # the same clip token and the same bytes (or a retail row that resolves in neither set)
                if full:
                    print('%s | %s | %s | %s | same%s' % (f, row, fmt(x), fmt(y), ' (unresolved in both)' if x[3] is None else ' (same bytes)'))
                continue
            if y is not None and y[3] is None:
                verdict = 'CLIP NOT FOUND'
            elif y is not None and y[2] is None:
                verdict = 'LENGTH UNREADABLE (packed clip), SERVER-READ' if server else 'length unreadable (packed clip), client-only'
            elif x is None:
                verdict = 'new row, ' + ('SERVER-READ' if server else 'client-only (no server name)')
            elif y is None:
                verdict = 'ROW REMOVED' + (' (server-read)' if server else '')
            elif x[2] is None:
                verdict = 'released clip not found'
            elif x[2] == y[2] and x[1].lower() == y[1].lower():
                if new.winner(y[1]) == old.winner(x[1]) and new.read(y[1]) == old.read(x[1]):
                    n_same += 1
                    if full:
                        print('%s | %s | %s | %s | same' % (f, row, fmt(x), fmt(y)))
                    continue
                verdict = 'clip replaced, SAME LENGTH' + (' (server-read)' if server else '')
            elif x[2] == y[2]:
                verdict = 'other clip, SAME LENGTH' + (' (server-read)' if server else '')
            else:
                verdict = 'LENGTH CHANGED' + (', SERVER-READ' if server else ' (client-only row)')
            fail = ('CLIP NOT FOUND' in verdict or 'ROW REMOVED (server' in verdict or 'SERVER-READ' in verdict)
            if fail and is_intended(f, row):
                verdict += ' - INTENDED'
                fail = False
            bad += fail
            counts[verdict] = counts.get(verdict, 0) + 1
            print('%s | %s | %s | %s | %s' % (f, row, fmt(x), fmt(y), verdict))
    print('---')
    print('%d rows in %d files: %d untouched' % (n_rows, len(files), n_same))
    for k in sorted(counts):
        print('  %4d  %s' % (counts[k], k))
    print('GATE: %s' % ('FAIL - %d unjustified server-read change(s)' % bad if bad else 'pass - no server-read row changed length'
                        + (' except the intended rows' if any('INTENDED' in k for k in counts) else '')))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
