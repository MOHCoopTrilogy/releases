"""AIM-ONLY gun clip for a charger-loaded bolt rifle's reload: the rounds really go DOWN into the magazine under the
thumb (the released clip shows the stack standing still and then hides it), and the empty charger leaves with the hand
that plucks it off (released: it stands until it is hidden). Everything else - bolt, tags - is the released clip, frame
for frame; same length, so nothing the server reads changes.

The cgame shows tik rows `reload_ads_loaded` / `reload_ads_empty` instead of `reload` while the local player reloads
aiming (cg_modelanim.c, the pistols' mechanism; client only - the server still runs `reload` and its surface commands,
so the rounds are still hidden at the released frame and the charger at its released frame).

    cd rifles/assets; python ../tools/chargerclip.py kar98          (after riflereload.py: the charger follows the BAKED hand)

Writes models/weapons/<dir>/<reload clip>_ads.skc and adds the two rows to every staged tik of the family (the
`rechamber_ads` rows and everything else in those tiks stay byte-identical: the block is only inserted).
"""
import sys, os, re, glob, json, struct, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools'))
import staged
import boltnear as BN
import gunskc
V, R = BN.V, BN.R
gungeo, vfs = BN.gungeo, BN.vfs
import skc14to13
NOTE = '// HZM coop [ads rifles 2026-10-13] '
A = 'models/human/animation/'
GUNS = {
    # rounds / charger = the gun clip's bones; sink {clip frame: u the stack has gone down} (the thumb's keys in
    # riflereload.py use the same numbers); the charger is rigid to the hand joint `follow` from `grab` to `gone`
    'kar98': dict(tik='models/weapons/kar98.tik', tiks='kar98*.tik', skip=('kar98_g98', 'kar98sniper', 'kar98_mortar', 'kar98mortar'),
                  rounds='Clip01', charger='Object01', surf_rounds='material7', surf_charger='material8',
                  sink={46: 0.0, 47: 0.9, 48: 1.5, 49: 1.5, 50: 2.3, 51: 3.0}, sunk_until=61,
                  view='viewmodel/rifle/kar98_reload_ads.skc', offhand=(1, 100), follow='Bip01 R Finger02', grab=55, gone=64,
                  spin=(0.0, 0.0, 25.0)),      # deg per frame about the gun's x / y / z once it is off the guide (a tumbling flick)
    # Lee-Enfield: no charger on the gun mesh (the chargers are the server's props in the hand). Its released clip
    # lifts the knob at frames 4-5 and has the bolt back by 11 - 0.13 s after the reload starts, while the aimed
    # rifle is still coming down off the sights. Aim-only clip: the bolt's own channels 4 frames later (up 8-9, back
    # 14-15), nothing else touched (`retime`: bone, frames later, last frame of the shifted span - the bolt stands
    # still, drawn back, from 11 to 94).
    'enfield': dict(tik='models/weapons/enfield.tik', tiks='enfield*.tik', skip=('enfield_p14', 'enfieldl42a1', 'enfield_l42'),
                    retime=dict(bone='enfield_bolt', shift=4, until=40)),
}


def released(g):
    staged.off()
    try:
        txt = vfs.read(g['tik']).decode('latin-1')
        t = gungeo.parse_tik(g['tik'])
        cp = gungeo._res(t, t['anims']['reload'])
        raw = vfs.read(cp)
    finally:
        staged.on()
    if struct.unpack_from('<i', raw, 4)[0] == 14:
        raw = skc14to13.convert(raw)
    return txt, t, cp, raw


def centre(tik, anim, f, surf):
    for s in gungeo.load_gun(tik, anim=anim, frame=f)['surfs']:
        if s['name'] == surf:
            return np.asarray(s['P'], float).mean(0)
    raise KeyError(surf)


def write_clip(raw, n, Vv, names):
    tmp = os.path.join(os.environ.get('TEMP', '.'), '_chargerclip.skc')
    gunskc.write(tmp, raw, n, {names[c]: [list(Vv[f, c]) for f in range(n)] for c in range(len(names))})
    return open(tmp, 'rb').read()


def jac(g, raw, cp, bone, surf, f):
    """gun-frame movement of the surface per unit of the bone's position channel (3x3, rows = channel axes)"""
    a = R.skc_io.read(raw)
    names = list(a.names); n = a.numFrames
    Vv = np.array(a.values, float)
    ip = names.index(bone + ' pos')
    key = cp.lower().replace(chr(92), '/')
    try:
        staged.OVERRIDE[key] = write_clip(raw, n, Vv, names)
        c0 = centre(g['tik'], 'reload', f, surf)
        J = np.zeros((3, 3))
        for ax in range(3):
            W = Vv.copy(); W[f, ip, ax] += 1.0
            staged.OVERRIDE[key] = write_clip(raw, n, W, names)
            J[ax] = centre(g['tik'], 'reload', f, surf) - c0
    finally:
        staged.OVERRIDE.pop(key, None)
    return J


def hand_track(g, n):
    """the follow joint's place in the GUN frame (u) per clip frame, from the baked aimed hands clip"""
    c = R.load(A + g['view'])
    lo, hi = g['offhand']
    out = []
    for f in range(min(n, c.numFrames)):
        W = R.evaluate(R.pose_dict(c, f))
        Tg = W['tag_weapon_left' if lo <= f <= hi else 'tag_weapon_right']
        out.append((W[g['follow']][3, 0:3] - Tg[3, 0:3]) * R.S @ Tg[0:3, 0:3].T)
    return np.array(out)


def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz])


def rows(txt, clip_ads, what='the rounds go down under the thumb, the empty charger leaves with the hand'):
    nl = '\r\n' if '\r\n' in txt else '\n'
    txt = re.sub(r'(?s)[ \t]*// HZM coop \[ads rifles 2026-10-13\] reload_ads.*?// HZM coop \[ads rifles 2026-10-13\] reload_ads end\r?\n', '', txt)
    m = re.search(r'(?m)^([ \t]*)reload[ \t]+(\S+\.skc)[^\n]*\n', txt)
    assert m, 'no reload row'
    i = txt.index('{', m.end()); d = 0; j = i
    while True:
        d += (txt[j] == '{') - (txt[j] == '}'); j += 1
        if d == 0:
            break
    j = txt.index('\n', j) + 1
    ind = m.group(1)
    body = txt[m.end():j]
    blk = (ind + NOTE + 'reload_ads_loaded / reload_ads_empty: the reload as shown while AIMING (cgame, client only; chargerclip.py) - ' + what + '; same length and sound as `reload`' + nl +
           ind + 'reload_ads_loaded\t' + clip_ads + nl + body +
           ind + 'reload_ads_empty\t' + clip_ads + nl + body +
           ind + NOTE + 'reload_ads end' + nl)
    out = txt[:j] + blk + txt[j:]
    dd = 0
    for ln in out.splitlines():
        c = ln.split('//')[0]; dd += c.count('{') - c.count('}')
    assert dd == 0
    return out


def build(name):
    g = GUNS[name]
    txt, t, cp, raw = released(g)
    a = R.skc_io.read(raw)
    names = list(a.names); n = a.numFrames
    Vv = np.array(a.values, float)
    sc = float(t['scale'])
    Jr = None
    if g.get('retime'):
        rt = g['retime']
        for sfx in (' pos', ' rot'):
            c = names.index(rt['bone'] + sfx)
            O = Vv[:, c].copy()
            assert np.abs(O[rt['until'] - rt['shift']:rt['until'] + 1] - O[rt['until']]).max() < 1e-5, 'the bone still moves at the end of the retimed span'
            for f in range(0, rt['until'] + 1):
                Vv[f, c] = O[max(0, f - rt['shift'])]
    if g.get('rounds'):
        f0 = min(g['sink'])
        Jr = jac(g, raw, cp, g['rounds'], g['surf_rounds'], f0)
        Jc = jac(g, raw, cp, g['charger'], g['surf_charger'], f0)
        ir, ic, iq = names.index(g['rounds'] + ' pos'), names.index(g['charger'] + ' pos'), names.index(g['charger'] + ' rot')
        # 1. the rounds: down the gun's +z (down) by the keyed depth, then held sunk until the released clip parks them
        ks = sorted(g['sink'])
        on = Vv[f0, ir].copy()                    # the stack standing in the charger (released value)
        for f in range(f0, g['sunk_until'] + 1):
            d = float(np.interp(f, ks, [g['sink'][k] for k in ks]))
            Vv[f, ir] = on
            Vv[f, ir, 0:3] = on[0:3] + np.linalg.solve(Jr.T, np.array([0.0, 0.0, d]))
        # 2. the empty charger: rigid to the hand joint from `grab`, tumbling, until `gone`
        hs = hand_track(g, n)
        onc = Vv[g['grab'], ic].copy(); q0 = Vv[g['grab'], iq].copy()
        for f in range(g['grab'], min(n, g['gone'] + 1)):
            dg = hs[f] - hs[g['grab']]
            Vv[f, ic] = onc
            Vv[f, ic, 0:3] = onc[0:3] + np.linalg.solve(Jc.T, dg)
            k = max(0, f - g['grab'] - 2)         # two frames to come off the guide, then it turns
            if k and any(g.get('spin', (0, 0, 0))):
                sx, sy, sz = [np.radians(v * k) / 2 for v in g['spin']]
                qs = qmul(qmul([np.sin(sx), 0, 0, np.cos(sx)], [0, np.sin(sy), 0, np.cos(sy)]), [0, 0, np.sin(sz), np.cos(sz)])
                Vv[f, iq] = qmul(q0, qs)
    out = write_clip(raw, n, Vv, names)
    base, ext = os.path.splitext(os.path.basename(cp))
    clip_ads = base + '_ads' + ext
    cp_ads = os.path.dirname(cp) + '/' + clip_ads
    dst = staged.path(cp_ads); os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(out)
    done = []
    for fn in sorted(glob.glob(staged.path('models/weapons/' + g['tiks']))):
        b = os.path.basename(fn)[:-4]
        if any(b.startswith(s) for s in g['skip']):
            continue
        tx = open(fn, 'rb').read().decode('latin-1')
        if not re.search(r'(?m)^[ \t]*reload[ \t]+' + re.escape(os.path.basename(cp)), tx):
            print('   NOT covered (no `reload %s` row): %s' % (os.path.basename(cp), b)); continue
        new = rows(tx, clip_ads, g.get('what', 'the rounds go down under the thumb, the empty charger leaves with the hand') if not g.get('retime') else 'the bolt is opened %d frames later (the rifle is still coming down off the sights before that)' % g['retime']['shift'])
        open(fn, 'wb').write(new.encode('latin-1'))
        done.append(b)
    for fn in glob.glob(os.path.join(BN.anahip.CACHE, '*_reload_ads*.json')):
        os.remove(fn)
    info = dict(gun=name, clip=cp_ads, frames=n, md5=hashlib.md5(out).hexdigest(), sink=g.get('sink'), grab=g.get('grab'), gone=g.get('gone'),
                retime=g.get('retime'), tiks=done,
                rounds_u_per_channel=[[round(float(x), 4) for x in r] for r in Jr] if Jr is not None else None)
    json.dump(info, open(dst[:-4] + '_charger.json', 'w'), indent=1)
    print('%s -> %s  %d frames  %s; rows in %d tiks: %s' % (name, cp_ads, n, info['md5'][:8], len(done), ' '.join(done)))
    return info


if __name__ == '__main__':
    for nm in sys.argv[1].split(','):
        build(nm)
