"""Webley Mk VI (colt45_colt1911w.tik, its own break-top mesh in models/weapons/coop_colt1911w) on the Webley's rows.

It wears the Webley hands prefix and the Webley's reload states, whose open / close / one-round steps were slowed to
0.8 s (webslow.py). Its own tik still had the released 0.4 / 0.53 / 0.3 s gun clips, so the barrel was open and the
cylinder had turned long before the hands got there. Here ITS OWN gun clips are retimed the way webslow.py retimed the
Webley's (the motion of its break bone found in the clip, then warped onto the Webley's frames), and its tik gets the
Webley's row set:
    reload              coop_mk6_open_hip.skc    20 f   sound at 8
    reload_ads_loaded / reload_ads_empty   coop_mk6_open_ads.skc   20 f   sound at 6
    reload_single       coop_mk6_single_slow.skc 24 f   sound at 20 (cylinder turn on frames 15..23, as the Webley's)
    reload_end          coop_mk6_close_hip.skc   21 f   sound at 18
    reload_end_ads      coop_mk6_close_ads.skc   21 f   sound at 13
All at 1/30 s per frame (the Webley's). The hands still reach for the Webley's barrel and chambers (run tx3): the gun
side is fitted, the hand points are not.

    python mk6.py <stage root>        idempotent (always from the released tik and clips)
"""
import sys, os, re, subprocess
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import p12, gunskc
R = gunskc.R
DIR = 'models/weapons/coop_colt1911w'
STEM = 'colt45_colt1911w'
FT = '0.0333333'


def span(clip, bone='Bone1 rot'):
    """first and last source frame between which the break bone moves"""
    a = R.load(DIR + '/' + clip)
    v = a.V[:, a.names.index(bone)]
    d = np.abs(np.diff(v, axis=0)).max(axis=1)
    idx = np.nonzero(d > 1e-5)[0]
    # Bone1 (barrel, 89.8 deg) and Bone3 (cylinder assembly) move over the SAME frames in both clips (open 0..10 of
    # 13, close 2..5 of 10) and hold afterwards, so the frame the break bone stops on already is the clip's end pose.
    # (Warping to the clip's last frame instead - tried in run pa25 - shut the barrel 0.2 s before the hand.)
    return int(idx[0]), int(idx[-1] + 1), int(a.numFrames)


def rt(root, src, dst, *a):
    out = os.path.join(root, DIR.replace('/', os.sep), dst)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    o = subprocess.run([sys.executable, os.path.join(HERE, 'retime.py'), DIR + '/' + src, out] + list(a) + ['--ft', FT], capture_output=True, text=True)
    assert o.returncode == 0, o.stderr[-600:]
    return dst


def row(s, name, clip, sound_from, sound_to):
    """repoint row `name` to `clip`, move its sound frame"""
    m = re.search(r'(?m)^([ \t]*%s[ \t]+)\S+\.skc' % re.escape(name), s)
    assert m, name
    s = s[:m.start()] + m.group(1) + clip + s[m.end():]
    i = m.start()
    j = s.index('\n\t}', i) if '\n\t}' in s[i:] else len(s)
    blk = s[i:j]
    b2, n = re.subn(r'(?m)^([ \t]*)%s([ \t]+sound[ \t]+\S+)' % sound_from[0], r'\g<1>%d\g<2>' % sound_to, blk, count=1)
    assert n == 1, (name, blk[:200])
    return s[:i] + b2 + s[j:]


def block_of(s, name):
    m = re.search(r'(?m)^[ \t]*%s[ \t]+\S+\.skc[^\n]*\n' % re.escape(name), s)
    i = s.index('{', m.end()); d = 0; j = i
    while True:
        d += (s[j] == '{') - (s[j] == '}'); j += 1
        if d == 0:
            break
    return m.start(), j


def main():
    root = os.path.abspath(sys.argv[1])
    a0, a1, an = span('webley_reload_start.skc')
    c0, c1, cn = span('webley_reload_end.skc')
    print('open: break bone moves over source frames %d..%d of %d; close: %d..%d of %d' % (a0, a1, an, c0, c1, cn))
    a1 = min(a1, an - 1); c1 = min(c1, cn - 1)
    s0, s1, sn = span('webley_reload_single.skc', 'Bone3 rot')
    clips = dict(
        open_hip=rt(root, 'webley_reload_start.skc', 'coop_mk6_open_hip.skc', 'warp', '0:0,8:%d,19:%d' % (a0, a1), '--frames', '20'),
        open_ads=rt(root, 'webley_reload_start.skc', 'coop_mk6_open_ads.skc', 'warp', '0:0,6:%d,18:%d,19:%d' % (a0, a1, a1), '--frames', '20'),
        close_hip=rt(root, 'webley_reload_end.skc', 'coop_mk6_close_hip.skc', 'warp', '0:0,11:%d,20:%d' % (c0, c1), '--frames', '21'),
        close_ads=rt(root, 'webley_reload_end.skc', 'coop_mk6_close_ads.skc', 'warp', '0:0,5:%d,15:%d,20:%d' % (c0, c1, c1), '--frames', '21'),
        # the Webley's cylinder turns over retail frames 10..15 of 16 = 15..23 of the slowed 24: the Mk VI's turn (its Bone3)
        # is put on the same frames, so the cylinder stands still while the hand brings the round
        single=rt(root, 'webley_reload_single.skc', 'coop_mk6_single_slow.skc', 'warp', '0:0,15:%d,23:%d' % (s0, min(s1, sn - 1)), '--frames', '24'))
    real = p12.tik_stems().get(STEM) or STEM
    tx = p12.rd('models/weapons/%s.tik' % real).decode('latin-1')
    nl = '\r\n' if '\r\n' in tx else '\n'
    s = tx.replace('\r\n', '\n')
    assert 'coop_mk6_' not in s
    # the aimed rows are copies of the hip rows' blocks (client sound only), inserted before the hip row
    i, j = block_of(s, 'reload')
    blk = s[i:j]
    ind = re.match(r'[ \t]*', blk).group(0)
    note = ind + '// HZM coop [Webley Mk VI on the slowed Webley rows 2026-10-13, mk6.py] shown by the cgame instead of `reload` / `reload_end` while aiming\n'
    ads = ''
    for nm in ('reload_ads_loaded', 'reload_ads_empty'):
        b = re.sub(r'^([ \t]*)reload([ \t]+)\S+\.skc', lambda m: m.group(1) + nm + '\t' + clips['open_ads'], blk, count=1)
        b = re.sub(r'(?m)^([ \t]*)7([ \t]+sound[ \t]+webley_snd_reload_start)', r'\g<1>6\g<2>', b)
        ads += b + '\n'
    s = s[:i] + note + ads + s[i:]
    i, j = block_of(s, 'reload_end')
    blk = s[i:j]
    b = re.sub(r'^([ \t]*)reload_end([ \t]+)\S+\.skc', lambda m: m.group(1) + 'reload_end_ads\t' + clips['close_ads'], blk, count=1)
    b = re.sub(r'(?m)^([ \t]*)3([ \t]+sound[ \t]+webley_snd_reload_end)', r'\g<1>13\g<2>', b)
    b = re.sub(r'(?m)^[ \t]*last[ \t]+idle[^\n]*\n', '', b)          # the server never plays the aimed row
    s = s[:i] + b + '\n' + s[i:]
    s = row(s, 'reload', clips['open_hip'], '7', 8)
    s = row(s, 'reload_single', clips['single'], '3', 20)
    s = row(s, 'reload_end', clips['close_hip'], '3', 18)
    p12.depth_ok(s, STEM)
    p12.write_tik(root, real, s, nl)
    print('wrote', real + '.tik', '| clips', ' '.join(sorted(clips.values())))


if __name__ == '__main__':
    main()
