"""clock_scope.py - on which guns does the client clip clock (cg_modelanim.c CoopGunLatchSee, coop_vmGunClipClock) run?

The clock keeps a swapped gun clip playing after the server's row has ended, but only when the swapped clip is LONGER
than the server's row by more than 0.05 s:  reload_ads_loaded / reload_ads_empty / reload_empty  over  reload,
fire_ads  over  fire.  For every weapon tik the game can load (integrated file set) this prints the tiks where that is
the case. A tik outside the allowed list = the clock would change what a gun that is not meant to use it shows.

    python clock_scope.py        exit 1 when the clock engages on a tik that is not in ALLOWED
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import intlib as L

PAIRS = (('reload', 'reload_ads_loaded'), ('reload', 'reload_ads_empty'), ('reload', 'reload_empty'), ('fire', 'fire_ads'))
# tik (regex) -> why the clock is meant to run there
ALLOWED = [
    (r'^(welrod[a-z0-9_]*)\.tik$', 'step 4 Welrod: server rows reload / fire are 1 frame, the aimed reload and the bolt cycle run on the clock'),
    (r'^(tt33[a-z0-9_]*)\.tik$', 'step 4 TT-33 + silenced: server reload row 7 frames'),
    (r'^(silencedpistol[a-z0-9_]*)\.tik$', 'step 4 Hi-Standard: the rack after an aimed shot (fire_ads)'),
    (r'^ppk\.tik$', 'step 4 PPK: its released reload row is 0.10 s shorter than the aimed clips (in the cut, run by the lane with the clock on)'),
    (r'^it_w_beretta[a-z0-9_]*\.tik$', 'step 4 Beretta: the released reload row is a packed Breakthrough clip (length not readable here; the engine decides)'),
    (r'^coop_g43_irons[a-z0-9_]*\.tik$', 'step 5 G 43 Irons: reload_ads_empty (the carrier racked) over the released 56-frame reload'),
]


def main():
    v = L.Vfs(L.FIX)
    tiks = set()
    for low in list(v._low.values()) + [v.mod, v.fixnames]:
        for n in low:
            if re.match(r'models/weapons/[^/]+\.tik$', n):
                tiks.add(n)
    bad = n = 0
    print('tik | swapped row | server row | allowed because')
    for t in sorted(tiks):
        b = v.read(t)
        if b is None:
            continue
        rows = {}
        for r in L.tik_rows(b.decode('latin-1')):
            rows.setdefault(r[0].lower(), r)
        for srv, swap in PAIRS:
            if srv in rows and swap in rows:
                a, c = L.skc_info(v.read(L.clip_path(rows[srv]))), L.skc_info(v.read(L.clip_path(rows[swap])))
                if a is None or c is None:
                    if rows[srv][1].lower() != rows[swap][1].lower():
                        why = next((w for rx, w in ALLOWED if re.match(rx, os.path.basename(t))), None)
                        print('%s | %s %s | %s %s | %s' % (os.path.basename(t), swap, rows[swap][1], srv, rows[srv][1], why or 'LENGTH UNREADABLE (packed clip) - NOT ALLOWED'))
                        bad += why is None
                    continue
                la, lc = a[0] * a[1], c[0] * c[1]
                if lc > la + 0.05:
                    n += 1
                    why = next((w for rx, w in ALLOWED if re.match(rx, os.path.basename(t))), None)
                    if why is None:
                        bad += 1
                    print('%s | %s %.3f s | %s %.3f s | %s' % (os.path.basename(t), swap, lc, srv, la, why or 'NOT ALLOWED'))
    print('%d weapon tiks scanned, the clock engages on %d row pair(s)' % (len(tiks), n))
    print('GATE: %s' % ('FAIL (%d)' % bad if bad else 'pass - the client clip clock only runs on the guns it was made for'))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
