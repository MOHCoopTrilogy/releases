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
import sys, os, re, json, copy, hashlib, math
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
                 hip_row='viewmodel/MP40/reload_mp40_stand.skc', hip_tip_off=0.3, ads_pull=(55.0, 61.0),
                 # 2b: the retail hand pulls 6 u in ONE frame (f61-62) - the handle (and the hand, re-keyed onto it by
                 # smgbake) now take these frames, eased; the sound's two clacks are at f59 and f64.5
                 hip_pull=(58.0, 63.5),
                 # 2b: a gun with rounds left is not cocked - its reload must not SOUND cocked either. `reload` gets the
                 # retail sound faded out over these clip frames (magazine in: 1.15-1.5 s; handle: 1.97 s and 2.15 s);
                 # the EMPTY rows keep the full sound
                 snd_cut=(51.0, 56.0), snd_parms='soundparms 1.5 0.0 1.0 0.05 160 1000 item loaded always maps "m e t dm obj lib"'),
    # Thompson M1A1 (ThompsonSMG.skd, Pak0; also the Gold finish): one bone, NO handle - the slot is painted on the RIGHT
    # of the receiver (x -2.2 .. 3.2, z -3.9; wall at y 0.54) with a knob painted at its FRONT end (x 3.4). The added
    # knob stands out of the wall on the right; back = cocked. The retail first-person clip pulls it with the LEFT hand
    # over the top (index 3.7 -> -1.2 along the gun at f64-66) - the place and travel of this handle. The reload sound
    # (ThompsonReload1a.wav): magazine out f9-13, in f39 / f45-49, handle f57-65: the aimed pull sits on f59-65.
    # Clip names carry the key (`_pre`); the gun's own clips are 71 frames, the hands row 84: `frames`.
    'thompson': dict(tik='models/weapons/thompsonsmg.tik', bone='coop_bolt', parent='tommy gun new', surface='ThompsonSMG1',
                     # se10 (user): a ROUND knob in the retail gun's proportions - the diameter of the ring the retail
                     # texture paints at the slot's front (0.9 u on a receiver 1.6 u tall; the M1A1's knob is about 5/8 in
                     # on a 1.6 in receiver, the painted ring includes its shadow): 0.8 u across, standing 0.7 u out of
                     # the wall, rim chamfered. The painted ring itself is taken off the staged textures (stage_slot.py).
                     back=(-1.6, 0.89, -3.9), size=(0.8, 0.7, 0.8), round=dict(n=14, cham=0.14), travel=5.0, uv_at=(1.0, 0.54, -4.55), side='R', _pre='thompson_',
                     hip_row='viewmodel/smg/reload_tommy_stand.skc', hip_tip_off=0.3, ads_pull=(59.0, 65.0), hip_pull=(63.5, 66.5),
                     frames=84, pull_soft=0.6, snd_cut=(51.0, 56.0),
                     snd_parms='soundparms 1.5 0.0 1.0 0.05 160 1000 item loaded always maps "m e t dm obj lib"'),
}
FIRE = [0.0, 0.55, 1.0, 0.6, 0.2, 0.0]          # forward fraction per 1/60 s frame
FIRE_EMPTY = [0.0, 0.55, 1.0, 1.0]


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def pull_curve(n, a, b, over=0.06, soft=0.0):
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
            # soft: part of the pull starts gently (a handle worked by the FIRING hand: the gun hangs on that hand's
            # keys, and a first step of 2.7 u put it 0.16 u off between two of them - midframe.py)
            v = 1.0 - ((1 - soft) * (1 - (1 - u) ** 2) + soft * (u * u * (3 - 2 * u)))
        out.append(v)
    return out


def hip_curve(g, n):
    """forward fraction per frame for the HIP empty reload: the handle is at the retail hand's index fingertip (minus
    hip_tip_off) along the gun, clamped to the slot; forward before the hand arrives, back once it has been pulled"""
    if g.get('hip_pull'):                    # this lane's own pull: forward until a, eased back by b
        a, b = g['hip_pull']
        return [1.0 - ease((f - a) / float(b - a)) for f in range(n)]
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
TAGS = '// HZM coop [smg rounds-left reload sound]'


def sound_alias(alias):
    """the wav an ubersound alias names (the last definition wins, as in the game)"""
    wav = None
    for p in sorted(set(vfs.glob_paths('ubersound/', '.scr'))):
        for ln in vfs.read(p).decode('latin-1').splitlines():
            m = re.match(r'\s*alias(?:cache)?\s+(\S+)\s+(\S+)', ln)
            if m and m.group(1).lower() == alias.lower():
                wav = m.group(2)
    return wav


def cut_wav(wav, cut, dst):
    """the retail reload sound faded out over the clip frames cut[0]..cut[1] (30 fps) and ended there"""
    import io, wave
    w = wave.open(io.BytesIO(vfs.read(wav)))
    sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
    assert sw == 2, 'only 16-bit sounds'
    d = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64).reshape(-1, ch)
    a, b = int(cut[0] / 30.0 * sr), int(cut[1] / 30.0 * sr)
    d = d[:b].copy()
    k = np.linspace(1.0, 0.0, b - a)
    d[a:b] *= (k * k * (3 - 2 * k))[:, None]
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    o = wave.open(dst, 'wb')
    o.setnchannels(ch); o.setsampwidth(2); o.setframerate(sr)
    o.writeframes(d.round().astype(np.int16).tobytes()); o.close()
    return b / float(sr), n / float(sr)


def tight_wav(wav, cut, dst):
    """the retail reload sound with the clip frames cut[0]..cut[1] (30 fps; a silent stretch) taken out, 10 ms crossfade"""
    import io, wave
    w = wave.open(io.BytesIO(vfs.read(wav)))
    sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
    assert sw == 2, 'only 16-bit sounds'
    d = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64).reshape(-1, ch)
    a, b = int(cut[0] / 30.0 * sr), int(cut[1] / 30.0 * sr)
    x = int(0.01 * sr)
    k = np.linspace(0.0, 1.0, x)[:, None]
    mid = d[a - x:a] * (1 - k) + d[b - x:b] * k
    out = np.vstack([d[:a - x], mid, d[b:]])
    peak = float(np.abs(d[a:b]).max()) / max(1.0, float(np.abs(d).max()))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    o = wave.open(dst, 'wb')
    o.setnchannels(ch); o.setsampwidth(2); o.setframerate(sr)
    o.writeframes(out.round().astype(np.int16).tobytes()); o.close()
    return len(out) / float(sr), n / float(sr), peak


def patch_tik(txt, g):
    """idempotent: fire -> coop_fire.skc; fire_empty (a copy of the fire block), idle_empty, reload_empty,
    reload_ads_empty added after the idle row. The reload rows carry only the client block (the sound): the server
    still runs `reload`; the cgame shows these instead."""
    nl = '\r\n' if '\r\n' in txt else '\n'

    def cn(x):
        return 'coop_%s%s.skc' % (g.get('_pre', ''), x)
    txt = re.sub(r'(?s)' + re.escape(TAG0) + r'.*?' + re.escape(TAG1) + r'[^\n]*\n', '', txt)
    fb = anim_block(txt, 'fire')
    assert fb, 'no fire row'
    s, e, blk, clip = fb
    if clip != cn('fire'):
        g.setdefault('_orig_fire', clip)
    blk_new = re.sub(r'(?m)^([ \t]*fire[ \t]+)\S+', lambda m_: m_.group(1) + cn('fire'), blk, count=1)
    txt = txt[:s] + blk_new + txt[e:]
    fe = re.sub(r'(?m)^([ \t]*)fire([ \t]+)\S+', lambda m_: m_.group(1) + 'fire_empty' + m_.group(2) + cn('fire_empty'), blk, count=1)
    rb = anim_block(txt, 'reload')
    assert rb, 'no reload row'
    rblk = rb[2]
    mc = re.search(r'(?s)([ \t]*client[ \t]*\r?\n[ \t]*\{.*?\n[ \t]*\}[ \t]*\r?\n)', rblk)
    client = mc.group(1) if mc else ''
    # `snd_tight`: the aimed EMPTY row plays the reload sound with a stretch of silence taken out (tight_wav)
    client_t = client
    mt = re.search(r'entry[ \t]+sound[ \t]+(\S+)', client) if (client and g.get('snd_tight')) else None
    if mt and mt.group(1).startswith('coop_') and mt.group(1).endswith('_loaded'):      # a tik that was patched before
        mt = None
    if mt:
        g.setdefault('_snd_tight', {})[mt.group(1)] = 'coop_%s_tight' % mt.group(1)
        client_t = client[:mt.start(1)] + 'coop_%s_tight' % mt.group(1) + client[mt.end(1):]

    def rel(name, clip_, client=client):
        return '\t%s\t%s%s\t{%s%s\t}%s' % (name, clip_, nl, nl, client, nl) if client else '\t%s\t%s%s' % (name, clip_, nl)
    add = (TAG0 + ' open bolt: the handle rests back, runs forward and back per shot, stays forward on empty' + nl
           + '\tidle_empty\t' + cn('idle_empty') + nl + fe.rstrip('\r\n') + nl
           + rel('reload_empty', cn('reload_empty')) + rel('reload_ads_empty', cn('reload_ads_empty'), client_t)
           + TAG1 + nl)
    ib = anim_block(txt, 'idle')
    assert ib, 'no idle row'
    txt = txt[:ib[1]] + add + txt[ib[1]:]
    # rounds left: `reload` (hip and aimed - there is no `reload_ads_loaded` row, so cgame shows `reload`) sounds
    # without the cock; the alias is the tik's own (init client), the EMPTY rows above keep the retail sound
    ms = re.search(r'entry[ \t]+sound[ \t]+(\S+)', client)
    if g.get('snd_cut') and ms:
        alias = ms.group(1)
        g.setdefault('_snd', {})[alias] = 'coop_%s_loaded' % alias
        rb = anim_block(txt, 'reload')
        blk2 = re.sub(r'(entry[ \t]+sound[ \t]+)' + re.escape(alias) + r'\b', lambda m_: m_.group(1) + 'coop_%s_loaded' % alias, rb[2], count=1)
        assert blk2 != rb[2]
        txt = txt[:rb[0]] + blk2 + txt[rb[1]:]
        txt = '\n'.join(l for l in txt.split('\n') if TAGS not in l)
        mi = re.search(r'(?ms)^init\b.*?^[ \t]*client[ \t]*\r?\n[ \t]*\{[ \t]*\r?\n', txt)
        assert mi, 'no init client block'
        line = '\t\taliascache coop_%s_loaded sound/weapons/foley/coop_%s_loaded.wav %s %s%s' % (alias, alias, g['snd_parms'], TAGS, nl)
        for al_ in sorted(g.get('_snd_tight', {})):
            line += '\t\taliascache coop_%s_tight sound/weapons/foley/coop_%s_tight.wav %s %s%s' % (al_, al_, g['snd_parms'], TAGS, nl)
        txt = txt[:mi.end()] + line + txt[mi.end():]
    if g.get('_repoint'):                    # step 3: every row that shows one of the gun's retail clips -> its coop_ copy
        ka = txt.lower().index('\nanimations')
        head, an = txt[:ka], txt[ka:]
        for old, new in g['_repoint'].items():
            an = re.sub(r'(?m)^([ \t]*[A-Za-z0-9_]+[ \t]+)' + re.escape(old) + r'(?=[ \t\r\n])', lambda m_: m_.group(1) + new, an)
        txt = head + an
    body = '\n'.join(l.split('//')[0] for l in txt.splitlines())
    assert body.count('{') == body.count('}'), 'braces'
    return txt


def round_mesh(n=12, cham=0.12):
    """a round knob in place of add_part's box, same call (c = centre, s = (diameter, length, diameter)): a cylinder
    along y (out of the receiver's wall) with a chamfered rim and a flat end on the +y side (side='R') or the -y side.
    Returns add_part.box_mesh's (verts [(pos, normal)], tris) with its winding rule (cross(b-a, c-a) . n < 0)."""
    def mesh(c, s):
        c = np.asarray(c, float); r = float(s[0]) / 2.0; h = float(s[1]) / 2.0
        ch = cham * r / 0.4
        sg = 1.0 if c[1] >= 0 else -1.0                 # which way the knob stands out of the gun
        ang = [2 * math.pi * k / n for k in range(n)]
        rad = [np.array([math.cos(a), 0.0, math.sin(a)]) for a in ang]
        ax = np.array([0.0, sg, 0.0])
        verts, tris = [], []

        def ring(y, rr, nf):
            b = len(verts)
            for d in rad:
                nn = nf(d); verts.append((c + ax * y + d * rr, nn / np.linalg.norm(nn)))
            return b

        def band(b0, b1):
            for k in range(n):
                k2 = (k + 1) % n
                for t in ((b0 + k, b0 + k2, b1 + k2), (b0 + k, b1 + k2, b1 + k)):
                    pa, pb, pc = (verts[i][0] for i in t)
                    nn = verts[t[0]][1] + verts[t[1]][1] + verts[t[2]][1]
                    tris.append((t[0], t[2], t[1]) if np.cross(pb - pa, pc - pa) @ nn > 0 else t)
        a0 = ring(-h, r, lambda d: d); a1 = ring(h - ch, r, lambda d: d); band(a0, a1)
        b0 = ring(h - ch, r, lambda d: d + ax); b1 = ring(h, r - ch, lambda d: d + ax); band(b0, b1)
        c0 = ring(h, r - ch, lambda d: ax)
        cc = len(verts); verts.append((c + ax * h, ax))
        for k in range(n):
            t = (cc, c0 + k, c0 + (k + 1) % n)
            pa, pb, pc = (verts[i][0] for i in t)
            tris.append((t[0], t[2], t[1]) if np.cross(pb - pa, pc - pa) @ ax > 0 else t)
        return verts, tris
    return mesh


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
    _box = AP.box_mesh
    if g.get('round'):
        AP.box_mesh = round_mesh(**g['round'])
    try:
        out, info = AP.add(src, g['tik'], g['bone'], g['parent'], g['surface'], list(g['back']), list(g['size']), list(g['uv_at']))
    finally:
        AP.box_mesh = _box
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
    nrel = g.get('frames') or GF.read_skc_any(G._res(t, t['anims']['reload'])).numFrames
    hcurve = hip_curve(g, nrel)
    print('   hip handle curve (forward fraction) f56..f68:', ' '.join('%.2f' % v for v in hcurve[56:69]))
    pre = g.get('_pre', '')
    files = {'coop_%sfire.skc' % pre: clip(FIRE, 1 / 60.0), 'coop_%sfire_empty.skc' % pre: clip(FIRE_EMPTY, 1 / 60.0),
             'coop_%sidle_empty.skc' % pre: clip([1.0], 1 / 30.0),
             'coop_%sreload_empty.skc' % pre: clip(hcurve, idle.frameTime),
             'coop_%sreload_ads_empty.skc' % pre: clip(pull_curve(nrel, *g['ads_pull'], soft=g.get('pull_soft', 0.0)), idle.frameTime)}
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
    for alias, new in sorted(g.get('_snd', {}).items()):
        wav = sound_alias(alias)
        t1, t0 = cut_wav(wav, g['snd_cut'], os.path.join(root, 'sound', 'weapons', 'foley', new + '.wav'))
        print('   sound %s = %s cut to %.2f s of %.2f s (no cock) -> the `reload` row of every tik above' % (new, wav, t1, t0))
    json.dump(dict(gun=name, tiks=tiks, back=g['back'], travel=g['travel'], forward=[g['back'][0] + g['travel'], g['back'][1], g['back'][2]],
                   side=g.get('side', 'L'), pull_soft=g.get('pull_soft', 0.0),
                   hip_curve=hcurve, ads_pull=g['ads_pull'], surface=g['surface'], uv=info if not isinstance(info, (bytes, bytearray)) else None),
              open(os.path.join(HERE, 'smggun_%s.json' % name), 'w'), indent=1, default=str)


# ------------------------------------------------------------------------------------------------------------
# Guns whose mesh HAS a moving bolt / handle bone (step 3). The retail clips work it like a closed bolt (forward at
# rest, back and forward in every reload). Nothing is changed on the mesh: every gun clip the tik names is re-issued
# with that bone's channel rewritten to the open-bolt story (table at the top), under coop_<name>, and the tik rows
# are pointed at them.
OWN = {
    'silenced_mp40': dict(tik='models/weapons/mp40silenced.tik', bone='eject', side='L'),
    'm3_grease_gun': dict(tik='models/weapons/greasegun.tik', bone='Bone1', side='R'),
    'silenced_grease_gun': dict(tik='models/weapons/greasegun_silenced.tik', bone='Bone1', side='R'),
    # MP18: the pack's own first-person reload (coopr_mp40_mp18_reload) works the right-side handle with the RIGHT hand
    # at f52-58 - the handle keeps those frames (hip and aimed), so that clip's hand stays on it
    # (2026-10-13: both hands clips are rebuilt now - smgbake GUNS['mp40_mp18'] - so the handle takes the default frames, on the sound)
    'mp40_mp18': dict(tik='models/weapons/mp40_mp18.tik', bone='Bone2', side='R', pull_soft=0.6),
    # the pack's own clips already tell the open-bolt story (rest BACK, forward on the shot; its reload runs the bolt
    # forward at once and pulls it back at the end = the EMPTY case): rest='back'
    # PPS-43: the handle is a surface of its own on the right of the receiver (x 9.6-10.6, forward), on the main bone
    'silenced_pps_43': dict(tik='models/weapons/ppsh43silenced.tik', bone='coop_bolt', side='R', split=('PPS43_lever',), travel=6.0),
    'mp40_reactivated': dict(tik='models/weapons/mp40_mp40r2.tik', bone='Bone1', side='L', rest='back'),
    # Sten (retail TA mesh): `Sten_Bolt`, a knob on the right, forward x 7.8, travel 8.8. The retail first-person clip
    # (91 frames; the gun's own 79) works it with the LEFT hand over the top at f68-72 - the hip handle keeps those
    # frames. The reload sound (wpn_Sten_reload.wav, 2.56 s): magazine out f10-11, in f44-47, a slap f58-59, the bolt
    # f71 and f74.5 - 0.1 s before the server ends the reload (f78). AIMED, the firing hand has to be back on the grip
    # by then, so the aimed EMPTY row plays the sound with the 0.2 s of silence before the bolt taken out
    # (`snd_tight`: clacks at f65 and f68.5) and the handle is pulled over f62-68. Rounds left: cut after the slap.
    'sten': dict(tik='models/weapons/sten.tik', bone='Sten_Bolt', side='R', pull_soft=0.6, hip_pull=(68.0, 72.0), ads_pull=(68.0, 74.0),
                 # run se16: the reload lasts 187 capture frames = the WHOLE 91-frame hands row (3.0 s), not the gun clip's 79 frames
                 # (bug-3725 corrected) - the aimed pull sits on the retail sound's own clacks (f68-74) and the hand
                 # has until f90 to get home: no `snd_tight` (the option stays in the tool, unused)
                 snd_cut=(61.0, 66.0)),
}
OWN_DEFAULTS = dict(hip_pull=(58.0, 63.5), ads_pull=(55.0, 61.0), snd_cut=(51.0, 56.0),
                    snd_parms='soundparms 1.5 0.0 1.0 0.05 160 1000 item loaded always maps "m e t dm obj lib"')


def moving_part(tik, anim, frame, side):
    """the vertices that move between the gun's rest (idle 0) and (anim, frame): their travel (gun frame, u) and the
    KNOB = the part of them that stands out furthest on `side` (L / R / T): where a finger hooks it"""
    g0 = G.load_gun(tik, anim='idle', frame=0)
    g1 = G.load_gun(tik, anim=anim, frame=frame)
    P0 = np.vstack([s['P'] for s in g0['surfs']]); P1 = np.vstack([s['P'] for s in g1['surfs']])
    d = P1 - P0
    mv = np.linalg.norm(d, axis=1) > 0.5
    if not mv.any():
        return None
    trav = d[mv].mean(0)
    Pm = P0[mv]
    ax, sg = {'L': (1, -1.0), 'R': (1, 1.0), 'T': (2, -1.0)}[side]
    ext = (Pm[:, ax] * sg).max()
    kn = Pm[(Pm[:, ax] * sg) > ext - 0.45]
    return dict(n=int(mv.sum()), travel=trav, knob=kn.mean(0), front=float(kn[:, 0].max()), lo=Pm.min(0), hi=Pm.max(0),
                kn_lo=kn.min(0), kn_hi=kn.max(0))


def build_own(name, root):
    g = dict(OWN_DEFAULTS); g.update(OWN[name])
    bone, ch = g['bone'], g['bone'] + ' pos'
    t = G.parse_tik(g['tik'])
    txt0 = vfs.read(g['tik']).decode('latin-1')
    rows = dict(re.findall(r'(?m)^[ \t]+([A-Za-z0-9_]+)[ \t]+(\S+\.skc)', txt0[txt0.lower().index('\nanimations'):]))
    clip = {r: GF.read_skc_any(G._res(t, c)) for r, c in rows.items() if r in ('idle', 'fire', 'reload')}
    idle, rel = clip['idle'], clip['reload']
    back_rest = g.get('rest') == 'back'
    if g.get('split'):
        # the handle is modelled on the mesh but hangs on the gun's main bone: its vertices get their OWN bone
        # (ads_bolt split_bone.py: weights re-pointed in place, nothing else changes; no channel = where they are)
        import split_bone as SPL
        skd_path = G._res(t, t['skel'][0])
        raw = vfs.read(skd_path)
        if bone in [b_.name for b_ in SK.read_skd(raw).bones]:
            raise SystemExit('the VFS mesh already has %s - build with IRONSIGHT_EXTRA_PAKS unset' % bone)
        new, parent, nsel = SPL.split(raw, bone, lambda s_, vi, p_: s_.name in g['split'])
        gdir0 = os.path.join(root, t['path'].replace('/', os.sep))
        os.makedirs(gdir0, exist_ok=True)
        open(os.path.join(gdir0, os.path.basename(skd_path)), 'wb').write(new)
        one0 = copy.deepcopy(idle); one0.values = [idle.values[0]]; one0.frames = [idle.frames[0]]; one0.numFrames = 1
        _, pf, d = GF.solve_delta(SK.read_skd(new), GF.add_channels(one0, bone), bone, g['travel'] / t['scale'])
        pb = pf + d
        g0 = G.load_gun(g['tik'], anim='idle', frame=0)
        Pm = np.vstack([s_['P'] for s_ in g0['surfs'] if s_['name'] in g['split']])
        ax, sg = {'L': (1, -1.0), 'R': (1, 1.0), 'T': (2, -1.0)}[g['side']]
        kn = Pm[(Pm[:, ax] * sg) > (Pm[:, ax] * sg).max() - 0.45]
        part = dict(n=len(Pm), travel=np.array([-g['travel'], 0.0, 0.0]), knob=kn.mean(0), front=float(kn[:, 0].max()), kn_lo=kn.min(0), kn_hi=kn.max(0))
        srow, kb = 'split', 0
        print('%s: %d vertices of %s split from bone %s onto %s (%d -> %d bytes)' % (name, nsel, g['split'], parent, bone, len(raw), len(new)))
    else:
        pf, pb, part, srow, kb = _own_travel(g, clip, ch, back_rest)
    if part is None:
        print('%s: bone %s moves in %s (frame %d) but NO vertex of the mesh follows it - nothing to work on this model' % (name, bone, srow, kb))
        return
    print('%s: bone %s, rear end of its travel = %s frame %d; %d vertices move %s u; knob (side %s) at %s, front face x %.2f' % (
        name, bone, srow, kb, part['n'], np.round(part['travel'], 2), g['side'], np.round(part['knob'], 2), part['front']))
    _build_own_clips(name, root, g, t, rows, clip, pf, pb, part, back_rest)


def _own_travel(g, clip, ch, back_rest):
    # where the bone is at rest (forward, the retail closed-bolt look) and at the rear end of its travel
    src = max((clip['fire'], clip['reload']), key=lambda c: (np.ptp(np.array(c.values)[:, c.names.index(ch), :3], axis=0).max() if ch in c.names else 0.0))
    srow = 'fire' if src is clip['fire'] else 'reload'
    ci = src.names.index(ch)
    P = np.array(src.values)[:, ci, :3]
    pf = P[0].copy()
    kb = int(np.argmax(np.linalg.norm(P - pf, axis=1)))
    pb = P[kb].copy()
    if back_rest:
        pf, pb = pb, pf
    return pf, pb, moving_part(g['tik'], srow, kb, g['side']), srow, kb


def _build_own_clips(name, root, g, t, rows, clip, pf, pb, part, back_rest):
    bone, ch = g['bone'], g['bone'] + ' pos'
    idle, rel = clip['idle'], clip['reload']

    def with_bone(c, fracs):
        """clip c with the bolt bone at fracs[f] (1 = forward, 0 = back) on every frame"""
        s = c if ch in c.names else GF.add_channels(c, bone)
        k = s.names.index(ch)
        vals = []
        for f in range(len(fracs)):
            fr = [list(v) for v in s.values[min(f, len(s.values) - 1)]]
            p = pb + fracs[f] * (pf - pb)
            fr[k] = [float(p[0]), float(p[1]), float(p[2]), fr[k][3]]
            vals.append(fr)
        return GF.build_skc(s, vals, c.frameTime)

    def on_clock(c, curve30):
        """a curve given per 1/30 s frame (the hands' clock), sampled at the gun clip's own frames"""
        return [curve30[min(len(curve30) - 1, int(round(f * c.frameTime * 30.0)))] for f in range(c.numFrames)]
    one = copy.deepcopy(idle); one.values = [idle.values[0]]; one.frames = [idle.frames[0]]; one.numFrames = 1
    one.frameTime = 1 / 60.0
    n30 = int(round(rel.numFrames * rel.frameTime * 30.0)) + 1
    g['_pre'] = pre = name + '_'          # the model directory may be shared with other guns (see patch_tik)
    files = {'coop_%sfire.skc' % pre: with_bone(one, FIRE), 'coop_%sfire_empty.skc' % pre: with_bone(one, FIRE_EMPTY),
             'coop_%sidle_empty.skc' % pre: with_bone(one, [1.0]),
             'coop_%sreload.skc' % pre: with_bone(rel, [0.0] * rel.numFrames),
             'coop_%sreload_empty.skc' % pre: with_bone(rel, on_clock(rel, hip_curve(g, n30))),
             'coop_%sreload_ads_empty.skc' % pre: with_bone(rel, on_clock(rel, pull_curve(n30, *g['ads_pull'], soft=g.get('pull_soft', 0.0))))}
    repoint = {rows['reload']: 'coop_%sreload.skc' % pre}
    for c_ in sorted(set(rows.values())):               # every other clip the tik shows the gun with: the bolt held BACK
        if c_ in (rows['fire'], rows['reload']) and c_ != rows['idle']:
            continue
        cc = GF.read_skc_any(G._res(t, c_))
        nm = 'coop_%sheld_' % pre + os.path.basename(c_)
        files[nm] = with_bone(cc, [0.0] * cc.numFrames)
        if c_ != rows['reload']:
            repoint[c_] = nm
    g['_repoint'] = repoint
    gdir = os.path.join(root, t['path'].replace('/', os.sep))
    os.makedirs(gdir, exist_ok=True)
    for fn, b in files.items():
        open(os.path.join(gdir, fn), 'wb').write(b)
        print('   %-30s %6d bytes %s' % (fn, len(b), hashlib.md5(b).hexdigest()[:8]))
    tiks = same_mesh_tiks(g['tik'])
    for p in tiks:
        txt = vfs.read(p).decode('latin-1')
        new = patch_tik(txt, g)
        dst = os.path.join(root, p.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(new.encode('latin-1'))
    print('   tiks patched (%d): %s; rows repointed: %s' % (len(tiks), ' '.join(os.path.basename(p) for p in tiks), repoint))
    for alias, new in sorted(g.get('_snd', {}).items()):
        wav = sound_alias(alias)
        t1, t0 = cut_wav(wav, g['snd_cut'], os.path.join(root, 'sound', 'weapons', 'foley', new + '.wav'))
        print('   sound %s = %s cut to %.2f s of %.2f s' % (new, wav, t1, t0))
    for alias, new in sorted(g.get('_snd_tight', {}).items()):
        wav = sound_alias(alias)
        t1, t0, pk = tight_wav(wav, g['snd_tight'], os.path.join(root, 'sound', 'weapons', 'foley', new + '.wav'))
        print('   sound %s = %s with f%.0f-%.0f taken out (%.2f s of %.2f s; the loudest sample in the part taken out is %.1f %% of the file\'s peak) -> reload_ads_empty' % (
            new, wav, g['snd_tight'][0], g['snd_tight'][1], t1, t0, 100 * pk))
    kn = part['knob'] + (part['travel'] if back_rest else 0.0)
    # the json's `forward` = the point smgbake hooks (as the MP40's added box: 0.18 behind the front face, 0.4 in from
    # the knob's outer end), at the FORWARD end of the travel
    if g['side'] == 'L':
        kn[1] = part['kn_lo'][1] + 0.4
    elif g['side'] == 'R':
        kn[1] = part['kn_hi'][1] - 0.4
    else:
        kn[2] = part['kn_lo'][2] + 0.4
    part['front'] += float(part['travel'][0]) if back_rest else 0.0
    part['travel'] = -part['travel'] if back_rest else part['travel']
    json.dump(dict(gun=name, tiks=tiks, bone=bone, side=g['side'], pull_soft=g.get('pull_soft', 0.0), travel=float(np.linalg.norm(part['travel'])), dir=[float(v) for v in part['travel'] / np.linalg.norm(part['travel'])],
                   forward=[part['front'] - 0.18, float(kn[1]), float(kn[2])], rest=g.get('rest', 'fwd'),
                   hip_curve=hip_curve(g, n30), ads_pull=g['ads_pull'], reload_frames=rel.numFrames, reload_ft=rel.frameTime),
              open(os.path.join(HERE, 'smggun_%s.json' % name), 'w'), indent=1, default=str)


if __name__ == '__main__':
    if sys.argv[1] == 'survey':              # smggun.py survey <tik>:<bone>:<L|R|T> ...   what moves, where the knob is
        for spec in sys.argv[2:]:
            tik_, bone_, side_ = spec.split(':')
            tik_ = tik_ if '/' in tik_ else 'models/weapons/' + tik_
            t_ = G.parse_tik(tik_)
            best = None
            for row_ in ('fire', 'reload'):
                c_ = GF.read_skc_any(G._res(t_, t_['anims'][row_]))
                if bone_ + ' pos' not in c_.names:
                    continue
                P_ = np.array(c_.values)[:, c_.names.index(bone_ + ' pos'), :3]
                k_ = int(np.argmax(np.linalg.norm(P_ - P_[0], axis=1)))
                d_ = float(np.linalg.norm(P_[k_] - P_[0]))
                if best is None or d_ > best[0]:
                    best = (d_, row_, k_)
            pt = moving_part(tik_, best[1], best[2], side_) if best and best[0] > 0 else None
            if pt is None:
                print('%-34s %-10s no vertex follows it' % (os.path.basename(tik_), bone_))
                continue
            # the firing shoulder in the mp40 aim pose is at (-20.2, 2.8, 0.8), arm 26.8 u; wrist about 4 u behind the knob
            reach = np.linalg.norm(pt['knob'] - np.array([4.0, 0, 0]) - np.array([-20.2, 2.8, 0.8])) / 26.8
            print('%-34s %-10s %3d verts, travel %s (from %s f%d), knob (side %s) at rest %s, front x %.1f | firing hand: %3.0f %% of the arm' % (
                os.path.basename(tik_), bone_, pt['n'], np.round(pt['travel'], 1), best[1], best[2], side_, np.round(pt['knob'], 1), pt['front'], 100 * reach))
        sys.exit(0)
    if sys.argv[1].split(',')[0] in OWN or sys.argv[1] == 'own':
        for nm in (sorted(OWN) if sys.argv[1] == 'own' else sys.argv[1].split(',')):
            build_own(nm, sys.argv[2])
        sys.exit(0)
    ap = None
    if os.environ.get('SMG_ADS_PULL'):
        ap = tuple(float(x) for x in os.environ['SMG_ADS_PULL'].split(','))
    for nm in sys.argv[1].split(','):
        build(nm, sys.argv[2], ap)
