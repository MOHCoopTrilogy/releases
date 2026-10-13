"""AIM-ONLY gun clip of a bolt rifle's between-shot cycle: `rechamber_ads` = the gun's own `rechamber` with the bolt's
rearward TRAVEL capped, so the rear of the bolt (cocking piece, bolt body, handle) never comes nearer to the eye than
`near` u. The hip clip keeps its full stroke. (User / coordinator 2026-10-12: with the rifle locked on the sights the
full stroke brings every bolt to 0.0-0.9 u from the eye - the cocking piece / the handle balloon over the bottom
centre of the picture: Mosin 'a huge flat grey mass', Springfield 'a long thick bar to the right edge'.)

ONE RULE FOR EVERY BOLT RIFLE: nearest bolt vertex >= max(NEAR u, settled distance / GROW) in front of the eye in every
frame of the aimed clip - never nearer than 2.5 u and never drawn more than 1.5 x its size in the settled aim
(measured offline in the staged aimed view clip, standing). The stroke is scaled uniformly (same timing, same lift),
so the bolt still unlocks, comes back, stops, goes forward and locks - it just stops short of the eye.
Optional `lift`: the handle's lift in degrees (Springfield M1903: 90, the retail clip turns it 80.5).

    cd rifles/assets; python ../tools/boltcap.py kar98,springfield,mosin,enfield [--near 2.5] [--k 0.6]
writes  models/weapons/<dir>/<clip>_ads.skc  and the staged  models/weapons/<tik>  (released tik + the row
`rechamber_ads`, a copy of the `rechamber` block: same sound, same case), and prints the stroke kept.
The cgame (ads-rifle-next) shows `rechamber_ads` instead of `rechamber` on the local player's held gun while aiming.
"""
import sys, os, re, json, glob, struct, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import staged
import boltnear as BN
import gunskc
V, R = BN.V, BN.R
gungeo, skdlib, vfs = BN.gungeo, BN.skdlib, BN.vfs
import skc14to13
NEAR = 2.5
GROW = 1.5
NOTE = '// HZM coop [ads rifles 2026-10-12] '
GUNS = {
    'kar98': dict(lift=None),
    'springfield': dict(lift=90.0),
    'mosin': dict(lift=None),
    'enfield': dict(lift=None),
}


def hip(name):
    """released tik text, hip rechamber clip path, v13 bytes"""
    staged.off()
    try:
        tik = V.SIGHTS[BN.GUNS[name][0]]['tik']
        txt = vfs.read(tik).decode('latin-1')
        t = gungeo.parse_tik(tik)
        cp = gungeo._res(t, t['anims']['rechamber'])
        raw = vfs.read(cp)
    finally:
        staged.on()
    if struct.unpack_from('<i', raw, 4)[0] == 14:
        raw = skc14to13.convert(raw)
    return tik, txt, cp, raw


def slerp_x(q0, q1, s):
    """slerp that extrapolates (s > 1 turns further about the same axis)"""
    q0 = np.asarray(q0, float); q1 = np.asarray(q1, float)
    d = float(q0 @ q1)
    if d < 0:
        q1, d = -q1, -d
    th = np.arccos(min(1.0, d))
    if th < 1e-6:
        return q0.copy()
    return (np.sin((1 - s) * th) * q0 + np.sin(s * th) * q1) / np.sin(th)


def keyed(raw, bone, k, lift=None):
    a = R.skc_io.read(raw)
    Vv = np.array(a.values, float)
    names = list(a.names)
    ip, iq = names.index(bone + ' pos'), names.index(bone + ' rot')
    P = Vv[:, ip].copy(); Q = Vv[:, iq].copy()
    travel = float(np.linalg.norm(P[:, 0:3] - P[0, 0:3], axis=1).max())
    P[:, 0:3] = P[0, 0:3] + k * (P[:, 0:3] - P[0, 0:3])
    ang = np.degrees(2 * np.arccos(np.clip(np.abs(Q @ Q[0]), 0, 1)))
    s = 1.0
    if lift:
        s = lift / float(ang.max())
        Q = np.array([slerp_x(Q[0], q, s) for q in Q])
    kd = {nm: Vv[:, c] for c, nm in enumerate(names)}      # every channel of every frame as the hip clip has it
    kd[bone + ' pos'] = P; kd[bone + ' rot'] = Q
    return a, kd, travel, float(ang.max()) * s


def near_with(name, tik, txt_ads, cp_ads, clip_bytes):
    staged.OVERRIDE[tik.lower()] = txt_ads.encode('latin-1')
    staged.OVERRIDE[cp_ads.lower()] = clip_bytes
    BN.V.PR._gcache.clear()
    try:
        return BN.measure(name, 'rechamber_ads', quiet=True)
    finally:
        staged.OVERRIDE.pop(tik.lower(), None); staged.OVERRIDE.pop(cp_ads.lower(), None)
        BN.V.PR._gcache.clear()


def tik_with_row(txt, clip_ads):
    nl = '\r\n' if '\r\n' in txt else '\n'
    txt = re.sub(r'(?s)[ \t]*// HZM coop \[ads rifles 2026-10-12\] rechamber_ads.*?// HZM coop \[ads rifles 2026-10-12\] rechamber_ads end\r?\n', '', txt)
    m = re.search(r'(?m)^([ \t]*)rechamber[ \t]+(\S+\.skc)[^\n]*\n', txt)
    assert m, 'no rechamber row'
    i = txt.index('{', m.end()); d = 0; j = i
    while True:
        d += (txt[j] == '{') - (txt[j] == '}'); j += 1
        if d == 0:
            break
    j = txt.index('\n', j) + 1
    ind = m.group(1)
    blk = (ind + NOTE + 'rechamber_ads: the cycle as shown while AIMING - the bolt stops short of the eye (boltcap.py); same sound and case' + nl +
           ind + 'rechamber_ads\t' + clip_ads + nl + txt[m.end():j] + ind + NOTE + 'rechamber_ads end' + nl)
    out = txt[:j] + blk + txt[j:]
    dd = 0
    for ln in out.splitlines():
        c = ln.split('//')[0]; dd += c.count('{') - c.count('}')
    assert dd == 0
    return out


def build(name, near=NEAR, kfix=None):
    g = GUNS[name]
    tik, txt, cp, raw = hip(name)
    bone = V.BOLT[os.path.basename(tik)]
    base, ext = os.path.splitext(os.path.basename(cp))
    clip_ads = base + '_ads' + ext
    cp_ads = os.path.dirname(cp) + '/' + clip_ads
    txt_ads = tik_with_row(txt, clip_ads)

    def clip(k):
        a, kd, travel, lift = keyed(raw, bone, k, g.get('lift'))
        tmp = os.path.join(os.environ.get('TEMP', '.'), '_boltcap_%s.skc' % name)
        gunskc.write(tmp, raw, a.numFrames, {c: [list(v) for v in kd[c]] for c in kd})
        return open(tmp, 'rb').read(), travel, lift
    b0, travel, lift = clip(0.0)
    b1, _, _ = clip(1.0)
    n0 = np.array([r['near'] for r in near_with(name, tik, txt_ads, cp_ads, b0)])
    n1 = np.array([r['near'] for r in near_with(name, tik, txt_ads, cp_ads, b1)])
    # THE CAP (one rule, every bolt rifle): never nearer than NEAR u, and never nearer than its settled distance / GROW
    # (the bolt's rear is then drawn at most GROW x its size in the settled aim: the Mosin's cocking piece sits 4.5 u
    # out and is a large light knob - at 2.5 u it is 1.8 x, at 3.0 u 1.5 x)
    settled = float(n0[0])
    near = max(near, settled / GROW)
    if kfix is None:
        ks =[(n0[f] - near) / (n0[f] - n1[f]) for f in range(len(n0)) if n1[f] < near and n0[f] - n1[f] > 0.05]
        k = float(max(0.0, min([1.0] + ks)))
    else:
        k = kfix
    bk, _, _ = clip(k)
    rows = near_with(name, tik, txt_ads, cp_ads, bk)
    mn = min(rows, key=lambda r: r['near']); mb = max(rows, key=lambda r: r['bbox'])
    sc = gungeo.parse_tik(tik)['scale']
    dst = staged.path(cp_ads); os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(bk)
    dt = staged.path(tik); os.makedirs(os.path.dirname(dt), exist_ok=True)
    open(dt, 'wb').write(txt_ads.encode('latin-1'))
    for fn in glob.glob(os.path.join(BN.anahip.CACHE, os.path.basename(tik) + '_rechamber_ads*.json')):
        os.remove(fn)       # the knob / bolt trajectories key_bolt caches per (tik, anim)
    info = dict(gun=name, near_cap=round(near, 2), settled_near=round(settled, 2), grow=round(settled / mn['near'], 2), k=round(k, 3), stroke_full_u=round(travel * sc, 2), stroke_kept_u=round(travel * sc * k, 2),
                lift_deg=round(lift, 1), nearest_full=round(float(n1.min()), 2), nearest_now=mn['near'], bbox_full=max(r['bbox'] for r in near_with(name, tik, txt_ads, cp_ads, b1)),
                bbox_now=mb['bbox'], clip=cp_ads, tik=tik)
    json.dump(info, open(dst[:-4] + '_cap.json', 'w'), indent=1)
    print('%-11s stroke %.2f u -> %.2f u (x%.2f), lift %.1f deg; nearest bolt vertex %.2f u -> %.2f u; bolt screen bbox max %.0f %% -> %.0f %%   %s' % (
        name, info['stroke_full_u'], info['stroke_kept_u'], k, lift, info['nearest_full'], mn['near'], info['bbox_full'], mb['bbox'], cp_ads))
    return info


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('guns'); ap.add_argument('--near', type=float, default=NEAR); ap.add_argument('--k', type=float)
    a = ap.parse_args()
    for g in a.guns.split(','):
        build(g, a.near, a.k)
