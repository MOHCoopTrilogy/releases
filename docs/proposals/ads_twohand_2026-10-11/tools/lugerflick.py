"""Luger P08 (+ silenced): the toggle FLICKS on every shot (pistol lane, 2026-10-13 pm; follow-up cut).

The released `fire` row of both Lugers is the idle clip luger.skc (5 frames x 0.25 s = 1.25 s, nothing moves). It is a
row the server plays, so its LENGTH stays: the new clips are 50 frames x 0.025 s = 1.25 s.
    fire        coop_luger_fire.skc       the toggle breaks up to the hold-open angle and snaps shut inside 0.125 s
                                          (the breech goes back by what the linkage gives) - hip, aimed, and on the
                                          gun other players see, because it IS the server's row
    fire_last   coop_luger_fire_last.skc  CLIENT row (cgame ads-next, coop_vmFireLast): shown instead of `fire` for the
                                          shot that empties the gun - the toggle goes up and STAYS up, so there is no
                                          shut toggle between the last shot and the hold-open (`idle_empty`)
Run AFTER luger.py's gun step (it rewrites the two tiks from the mod tree); idempotent.

    cd stage; python ../lugerflick.py .          IRONSIGHT_EXTRA_PAKS = _ov_wip.pk3;_bases.pk3
"""
import sys, os, re
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bonefit as BF
import p12, gunskc
import luger as LG
NF, FT = 50, 0.025
UP = [0.0, 0.70, 1.0, 0.78, 0.34, 0.0]            # share of the hold-open angle, frame by frame (25 ms each)


def build(root):
    DIR = LG.DIR
    A, o = BF.fit('models/weapons/lugerp08.tik', 'Box01')
    raw = p12.rd(DIR + '/luger.skc')
    idle = gunskc.R.load(DIR + '/luger.skc')
    assert abs(idle.numFrames * idle.frameTime - NF * FT) < 1e-4, (idle.numFrames, idle.frameTime)

    def clip(fn, prof):
        tp, tq, bp, bq = [], [], [], []
        for f in range(NF):
            th = LG.TH * prof(f)
            p, q = BF.chan(A, o, BF.rot_rows((0, 1, 0), th), (LG.AXLE[0], 0.0, LG.AXLE[1]))
            tp.append(p); tq.append(q)
            p, q = BF.chan(A, o, np.eye(3), (0, 0, 0), (-LG.back_of(th), 0.0, 0.0))
            bp.append(p); bq.append(q)
        gunskc.write(os.path.join(root, (DIR + '/' + fn).replace('/', os.sep)), raw, NF,
                     {'coop_tog pos': tp, 'coop_tog rot': tq, 'coop_slide pos': bp, 'coop_slide rot': bq}, frame_time=FT)
        return fn
    fire = clip('coop_luger_fire.skc', lambda f: UP[f] if f < len(UP) else 0.0)
    last = clip('coop_luger_fire_last.skc', lambda f: UP[f] if f < 3 else 1.0)
    done = []
    for stem in LG.TIKS:
        fn = os.path.join(root, 'models', 'weapons', stem + '.tik')
        raw_t = open(fn, 'rb').read().decode('latin-1')
        nl = '\r\n' if '\r\n' in raw_t else '\n'
        s = raw_t.replace('\r\n', '\n')
        if 'coop_luger_fire_last.skc' in s:
            done.append(stem + ' (already)'); continue
        mm = re.search(r'(?m)^([ \t]*)fire([ \t]+)luger\.skc[^\n]*\n', s)
        assert mm, stem
        i = s.index('{', mm.end()); d = 0; j = i
        while True:
            d += (s[j] == '{') - (s[j] == '}')
            j += 1
            if d == 0:
                break
        ind = mm.group(1)
        blk = ('%s// HZM coop [toggle flick, pistol lane 2026-10-13] fire = the toggle breaks open and snaps shut (same 1.25 s as the released row);\n'
               '%s// fire_last = shown by the cgame instead of `fire` for the shot that empties the gun: the toggle stays up\n' % (ind, ind)
               + '%sfire_last%s%s\n%s%s\n' % (ind, mm.group(2), last, ind, s[i:j]))
        s = s[:mm.start()] + blk + '%sfire%s%s\n' % (ind, mm.group(2), fire) + s[mm.end():]
        p12.depth_ok(s, stem)
        open(fn, 'wb').write(s.replace('\n', nl).encode('latin-1'))
        done.append(stem)
    print('luger flick: %s, %s (%d x %.3f s) | tiks %s' % (fire, last, NF, FT, done))


if __name__ == '__main__':
    build(sys.argv[1])
