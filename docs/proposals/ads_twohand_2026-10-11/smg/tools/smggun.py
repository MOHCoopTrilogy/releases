"""SMG lane, GUN side: a cocking handle that really moves on the gun model (user 2026-10-12: "functioning slides, bolts,
etc"), for meshes that have none or have it welded on.

Per gun (table GUNS): 1. the handle - a small box ADDED to the mesh on its own bone (ads_bolt add_part.py: existing
vertices, order, UVs and weights untouched, so every finish variant and re-texture keeps working), modelled at the
bone's bind place; 2. the gun's action animations, generated (ads_bolt gen_fire.py's SKAN writer and its numeric
bone-offset solve); 3. the tik rows, patched into EVERY tik in the game that uses this mesh (same path + skelmodel).

OPEN-BOLT SMGs (MP40, Sten, Thompson, PPSh, grease gun, Type 100, MP18): the bolt rests BACK on the sear when the gun
is ready to fire, runs forward and back on every shot, and stays FORWARD after the last round - which is why an empty
gun has to be cocked after the magazine goes in, and a gun with rounds left does not. So:
    bind pose / idle / reload              handle BACK (no clip of the retail gun changes)
    fire                 coop_fire.skc         back -> forward -> back, 6 frames at 1/60 s (restarts on every shot)
    fire_empty           coop_fire_empty.skc   back -> forward, stays (the last round; the server picks it: weapon.cpp)
    idle_empty           coop_idle_empty.skc   forward
    reload_empty         coop_reload_empty.skc     HIP, empty: forward until the retail hand's own pull, back with it
    reload_ads_empty     coop_reload_ads_empty.skc AIMED, empty: forward until this lane's keyed pull, back with it
(`reload_ads_loaded` is not needed: the plain `reload` already shows the handle back and still.)

    cd smg/assets; python ../tools/smggun.py <gun> .           -> models/weapons/<dir>/... + the patched tiks
"""
import sys, os, re, json, copy, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
T = r"C:\mohaa-coop-dev\docs\proposals\ads_bolt_2026-10-04\tools"
sys.path.insert(0, T); _c = os.getcwd(); os.chdir(T)
import vmcam as V
import add_part as AP
import gen_fire as GF
os.chdir(_c)
PR = V.PR; G = PR.gungeo; SK = PR.skdlib; vfs = PR.vfs

GUNS = {
    # MP40 (mp40.skd, Pak0): NO handle geometry - the cocking slot is only painted on the left of the receiver tube
    # (x 4.5 .. 12, z -4.6; tube axis y -0.89, z -4.3, radius 0.94). Handle = a box on the left of the tube.
    'mp40': dict(tik='models/weapons/mp40.tik', bone='coop_bolt', parent='MP40', surface='gun1',
                 # slot measured on the mesh render (gunside.py): z -4.25, front end x 12.0, rear end x 4.3 (+ the notch)
                 # uv_at lands on uv (0.547, 0.4185): plain dark receiver steel - the point the weapon-HD lane already
                 # holds as wear-protected for an MP40 knob (ads_bolt README 8.2)
                 back=(5.0, -2.15, -4.25), size=(0.36, 0.8, 0.36), travel=6.5,       # 0.5 x 0.9 x 0.5 read as a black brick 9 u from the eye (run sb1)
                 uv_at=(9.0, -0.9, -5.3), side='L',
                 # frames (1/30 s, the reload clips' clock): the handle is pulled over pull[0]..pull[1]
                 # HIP, empty: the handle follows the retail cocking hand's index fingertip along the gun (hip_row = the
                 # retail first-person clip), so hand and handle cannot drift apart; AIMED: this lane's keyed pull
                 hip_row='viewmodel/MP40/reload_mp40_stand.skc', hip_tip_off=0.3, ads_pull=(55.0, 61.0)),
}
FIRE = [0.0, 0.55, 1.0, 0.6, 0.2, 0.0]          # forward fraction per 1/60 s frame
FIRE_EMPTY = [0.0, 0.55, 1.0, 1.0]


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def pull_curve(n, a, b, over=0.06):
    """forward fraction per frame of an n-frame reload: 1 (forward) until a, pulled back to 0 by b - the hand's pull is
    quick at first and stops against the rear (ease-out), then the bolt settles a hair forward onto the sear"""
    out = []
    for f in range(n):
        if f <= a:
            v = 1.0
        elif f >= b:
            v = 0.0 + 0.0 * over
        else:
            u = (f - a) / float(b - a)
            v = 1.0 - (1 - (1 - u) ** 2)
        out.append(v)
    return out


def hip_curve(g, n):
    """forward fraction per frame for the HIP empty reload: the handle is at the retail hand's index fingertip (minus
    hip_tip_off) along the gun, clamped to the slot; forward before the hand arrives, back once it has been pulled"""
    R = V.R
    c = R.load(R.ANIM + g['hip_row'])
    xs = []
    for f in range(c.numFrames):
        W = R.evaluate(R.pose_dict(c, f))
        xs.append(float(((W['Bip01 L Finger12'] @ R.inv(W['tag_weapon_right']))[3, 0]) * R.S) - g['hip_tip_off'])
    fwd, back = g['back'][0] + g['travel'], g['back'][0]
    # the pull = the frames after the magazine in which the fingertip passes from ahead of the forward place to behind it
    cand = [f for f in range(40, c.numFrames - 1) if xs[f] >= fwd and xs[f + 1] < fwd]
    f0 = cand[-1]
    out, done = [], False
    for f in range(n):
        if f <= f0 or f >= c.numFrames:
            v = 1.0 if f <= f0 else 0.0
        elif done:
            v = 0.0
        else:
            v = max(0.0, min(1.0, (xs[f] - back) / (fwd - back)))
            done = v <= 0.0
        out.append(v)
    return out


def same_mesh_tiks(base_tik):
    """every weapon tik in the game whose path + skelmodel are the base tik's"""
    t0 = G.parse_tik(base_tik)
    key = (t0['path'].lower(), t0['skel'][0].lower())
    out = []
    for p in sorted(set(vfs.glob_paths('models/weapons/', '.tik'))):
        try:
            t = G.parse_tik(p)
        except Exception:
            continue
        if t.get('skel') and (t['path'].lower(), t['skel'][0].lower()) == key:
            out.append(p)
    return out


def anim_block(txt, name):
    """(start, end, text) of the animation row `name` with its { } block in a tik's animations section"""
    m = re.search(r'(?m)^[ \t]*%s[ \t]+(\S+)[^\r\n]*\r?\n' % re.escape(name), txt)
    if not m:
        return None
    k = m.end()
    mb = re.match(r'[ \t]*\{', txt[k:])
    if not mb:
        return m.start(), k, txt[m.start():k], m.group(1)
    depth = 0
    for i in range(k, len(txt)):
        if txt[i] == '{':
            depth += 1
        elif txt[i] == '}':
            depth -= 1
            if depth == 0:
                e = txt.index('\n', i) + 1
                return m.start(), e, txt[m.start():e], m.group(1)
    raise ValueError('unbalanced block for ' + name)


TAG0, TAG1 = '\t// HZM coop [smg action rows]', '\t// HZM coop [smg action rows end]'


def patch_tik(txt, g):
    """idempotent: fire -> coop_fire.skc; fire_empty (a copy of the fire block), idle_empty, reload_empty,
    reload_ads_empty added after the idle row. The reload rows carry only the client block (the sound): the server
    still runs `reload`; the cgame shows these instead."""
    nl = '\r\n' if '\r\n' in txt else '\n'
    txt = re.sub(r'(?s)' + re.escape(TAG0) + r'.*?' + re.escape(TAG1) + r'[^\n]*\n', '', txt)
    fb = anim_block(txt, 'fire')
    assert fb, 'no fire row'
    s, e, blk, clip = fb
    if clip != 'coop_fire.skc':
        g.setdefault('_orig_fire', clip)
    blk_new = re.sub(r'(?m)^([ \t]*fire[ \t]+)\S+', lambda m_: m_.group(1) + 'coop_fire.skc', blk, count=1)
    txt = txt[:s] + blk_new + txt[e:]
    fe = re.sub(r'(?m)^([ \t]*)fire([ \t]+)\S+', lambda m_: m_.group(1) + 'fire_empty' + m_.group(2) + 'coop_fire_empty.skc', blk, count=1)
    rb = anim_block(txt, 'reload')
    assert rb, 'no reload row'
    rblk = rb[2]
    mc = re.search(r'(?s)([ \t]*client[ \t]*\r?\n[ \t]*\{.*?\n[ \t]*\}[ \t]*\r?\n)', rblk)
    client = mc.group(1) if mc else ''

    def rel(name, clip_):
        return '\t%s\t%s%s\t{%s%s\t}%s' % (name, clip_, nl, nl, client, nl) if client else '\t%s\t%s%s' % (name, clip_, nl)
    add = (TAG0 + ' open bolt: the handle rests back, runs forward and back per shot, stays forward on empty' + nl
           + '\tidle_empty\tcoop_idle_empty.skc' + nl + fe.rstrip('\r\n') + nl
           + rel('reload_empty', 'coop_reload_empty.skc') + rel('reload_ads_empty', 'coop_reload_ads_empty.skc')
           + TAG1 + nl)
    ib = anim_block(txt, 'idle')
    assert ib, 'no idle row'
    txt = txt[:ib[1]] + add + txt[ib[1]:]
    body = '\n'.join(l.split('//')[0] for l in txt.splitlines())
    assert body.count('{') == body.count('}'), 'braces'
    return txt


def build(name, root, ads_pull=None):
    g = dict(GUNS[name])
    if ads_pull:
        g['ads_pull'] = ads_pull
    if os.environ.get('SMG_UVAT'):
        g['uv_at'] = tuple(float(x) for x in os.environ['SMG_UVAT'].split(','))
    t = G.parse_tik(g['tik'])
    sc = t['scale']
    skd_path = G._res(t, t['skel'][0])
    # 1. the handle, modelled at the BACK (cocked) place = the bind pose
    src = vfs.read(skd_path)
    names = [b.name for b in SK.read_skd(src).bones]
    if g['bone'] in names:
        raise SystemExit('the VFS mesh already has %s - build with IRONSIGHT_EXTRA_PAKS unset (the staged overlay must not be mounted)' % g['bone'])
    out, info = AP.add(src, g['tik'], g['bone'], g['parent'], g['surface'], list(g['back']), list(g['size']), list(g['uv_at']))
    old, chk = SK.read_skd(src), SK.read_skd(out)
    for so, sn in zip(old.surfaces, chk.surfaces):
        assert (sn.vert_bytes[:len(so.vert_bytes)] == so.vert_bytes) if so.name == g['surface'] else (sn.vert_bytes == so.vert_bytes)
    gdir = os.path.join(root, t['path'].replace('/', os.sep))
    os.makedirs(gdir, exist_ok=True)
    open(os.path.join(gdir, os.path.basename(skd_path)), 'wb').write(out)
    print('%s: handle %s on %s (%d -> %d bytes) %s' % (name, g['bone'], g['surface'], len(src), len(out), info))
    # 2. the action anims
    idle = GF.read_skc_any(G._res(t, t['anims']['idle']))
    one = copy.deepcopy(idle); one.values = [idle.values[0]]; one.frames = [idle.frames[0]]; one.numFrames = 1
    sk = GF.add_channels(one, g['bone'])
    ci, basep, d = GF.solve_delta(chk, sk, g['bone'], -g['travel'] / sc)       # +x: forward from the bind (back) place
    v0 = [list(v) for v in sk.values[0]]

    def clip(curve, ft):
        vals = []
        for a in curve:
            fr = [list(v) for v in v0]
            p = basep + a * d
            fr[ci] = [float(p[0]), float(p[1]), float(p[2]), v0[ci][3]]
            vals.append(fr)
        return GF.build_skc(sk, vals, ft)
    nrel = GF.read_skc_any(G._res(t, t['anims']['reload'])).numFrames
    hcurve = hip_curve(g, nrel)
    print('   hip handle curve (forward fraction) f56..f68:', ' '.join('%.2f' % v for v in hcurve[56:69]))
    files = {'coop_fire.skc': clip(FIRE, 1 / 60.0), 'coop_fire_empty.skc': clip(FIRE_EMPTY, 1 / 60.0),
             'coop_idle_empty.skc': clip([1.0], 1 / 30.0),
             'coop_reload_empty.skc': clip(hcurve, idle.frameTime),
             'coop_reload_ads_empty.skc': clip(pull_curve(nrel, *g['ads_pull']), idle.frameTime)}
    for fn, b in files.items():
        open(os.path.join(gdir, fn), 'wb').write(b)
        print('   %-28s %6d bytes %s' % (fn, len(b), hashlib.md5(b).hexdigest()[:8]))
    # 3. every tik on this mesh
    tiks = same_mesh_tiks(g['tik'])
    for p in tiks:
        raw = vfs.read(p)
        txt = raw.decode('latin-1')
        new = patch_tik(txt, g)
        dst = os.path.join(root, p.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(new.encode('latin-1'))
    print('   tiks patched (%d): %s' % (len(tiks), ' '.join(os.path.basename(p) for p in tiks)))
    json.dump(dict(gun=name, tiks=tiks, back=g['back'], travel=g['travel'], forward=[g['back'][0] + g['travel'], g['back'][1], g['back'][2]],
                   hip_curve=hcurve, ads_pull=g['ads_pull'], surface=g['surface'], uv=info if not isinstance(info, (bytes, bytearray)) else None),
              open(os.path.join(HERE, 'smggun_%s.json' % name), 'w'), indent=1, default=str)


if __name__ == '__main__':
    ap = None
    if os.environ.get('SMG_ADS_PULL'):
        ap = tuple(float(x) for x in os.environ['SMG_ADS_PULL'].split(','))
    for nm in sys.argv[1].split(','):
        build(nm, sys.argv[2], ap)
