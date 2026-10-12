"""The GUN side of the aimed magazine-pistol reloads (user 2026-10-12: "functioning slides, bolts, etc"; "on a reload
with a round chambered there is no slide action") and the ONE spec both sides read (pistolbake.py imports GUNS).

The retail gun clips snap the slide back on frame 1 of EVERY reload (Colt, Beretta) or have no slide at all (P38,
Hi-Standard: slidesplit.py cuts one out of the mesh, bone `coop_slide`). The cgame (ads-next) shows, instead of the
weapon tik's `reload`:
    reload_ads_loaded   aimed, rounds in the gun: the slide never moves; the magazine drops, a new one is pushed in
    reload_ads_empty    aimed, empty: the slide is locked back from the first frame and RUNS forward when released
    reload_empty        at the hip, empty (split-slide guns only: their retail clip has no slide channel)
and every tik gets `idle_empty` (slide back) if it has none. All clips keep the retail length, so the server's timing
is untouched (it still runs `reload`). The aimed loaded reload gets its own sound: the retail sample cut before the
slide noises.

    python pistolgun.py <gun|all> <stage root>
"""
import sys, os, re, io, wave, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
R = gunskc.R
vfs = R.vfs
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'

# t: the clip's events in frames - off: support hand leaves over (a, b); rel: magazine button; out: magazine leaves over
# (a, b); seat: the push (a, b); on: hand back on the grip over (a, b); press: the support thumb starts down on the
# slide stop (2 frames); fwd: the slide runs forward over (a, b) - it starts the frame the thumb is down.
# Timed to the retail reload sound's clicks (sndenv.py / pistolinfo.py), not to the retail gun clip.
# rel: retail hands-clip frame at which the server takes the magazine prop out of the hand (the hand-over frame).
GUNS = {
    'colt45': dict(row='colt45_reload', sight='colt_45', aim='viewmodel/pistol/colt45_ads2h.skc', cls='pistol', vdir='viewmodel/pistol',
                   dir='models/weapons/colt45', clip='reload_colt45.skc', empty='colt45_empty.skc', slide='chamber', mag='clip',
                   snd='colt45_snd_reload', wav='sound/weapons/foley/Colt45Reload1b.wav', cut=46, rel=40,
                   t=dict(off=(3, 9), rel=8, out=(12, 17), seat=(33, 36), on=(41, 50), press=51, fwd=(53, 56))),
    'p38': dict(row='p38_reload', sight='walther_p38', aim='viewmodel/pistol/p38_ads2h.skc', cls='pistol', vdir='viewmodel/pistol',
                dir='models/weapons/P38', clip='P38_reload.skc', empty=None, slide='coop_slide', mag='p38clip',
                snd='P38_snd_reload', wav='sound/weapons/foley/P38Reload1.wav', cut=44, rel=40,
                t=dict(off=(2, 8), rel=6, out=(12, 17), seat=(31, 34), on=(41, 49), press=49, fwd=(51, 53))),
    'histandard': dict(row='histandard_reload', sight='hi_standard_silenced', aim='viewmodel/pistol/histandard_ads2h.skc', cls='pistol',
                       vdir='viewmodel/pistol', dir='models/weapons/highstandard', clip='hs_pistol_reload.skc', empty=None, slide='coop_slide',
                       mag='clip', magup=(0.5, 0.0, -1.9), snd='silencer_snd_reload', wav='sound/weapons/foley/SilencerReload1.wav', cut=43, rel=40,
                       # HAND-CYCLED (fire delay 1.0 s; the retail hip fire and hip reload both rack it, the reload sound's
                       # rack is at frames 50-54): no lock-back, no slide stop - the reload ENDS in the same rack as the
                       # per-shot cycle (cyclebake.py). rack: hand at the slide / slide back over / forward over / on the grip
                       rack=dict(reach=46, pull=(49, 51), fwd=(53, 54), on=64),
                       t=dict(off=(3, 9), rel=9, out=(12, 18), seat=(30, 33), on=(40, 47), press=47, fwd=(49, 51))),
    'beretta': dict(row='beretta_reload', sight='beretta', aim='viewmodel/beretta/beretta_ads2h.skc', cls='pistol', vdir='viewmodel/beretta',
                    dir='models/weapons/Beretta', clip='A_W_MOD34Pistol_reload_W.skc', empty='A_W_MOD34Pistol_empty_W.skc', slide='Rechamber',
                    mag=None, magup=(0.3, 0.0, -1.2), snd='beretta_snd_reload', wav='sound/weapons/foley/Beretta_reload.wav', cut=39, rel=33,
                    park=True,    # TT art: the magazine prop is rigid in the hand from frame 0 to the LAST frame

                    t=dict(off=(2, 7), rel=9, out=(10, 14), seat=(29, 32), on=(38, 45), press=45, fwd=(47, 49))),
}
PARMS = '0.9 0.2 1.0 0.0 160 1000 item loaded always maps "dm obj lib"'      # `always`: without it a tik alias is dropped (bLoadForMap)


# ---- the ONE rack motion of a hand-cycled pistol (per-shot cycle and reload end): the support hand slides UP from
# its grip along the left side of the gun to the slide (it stays left of the sight line - an overhand grasp or a
# pinch from behind covers the sights), takes it, pulls it back by the slide's travel and lets it run forward
RACK_UP = (0.3, 0.5, 1.7)          # camera frame (fwd, left, up) from the aim grip to the slide
RACK_PULL = 0.92                   # of the slide's travel


def rack_hand(reach, pull, fwd, travel, fing):
    """left_path keys {frame: spec} from the hand arriving at the slide to it leaving; `fing` = a curled-finger
    reference frame of the hip clip being baked"""
    FG = ('mix', fing, 0.35)
    ON = dict(aim=1, cam_add=RACK_UP, fing=FG)
    BACK = dict(aim=1, cam_add=RACK_UP, gun_add=(-travel * RACK_PULL, 0.0, 0.0), fing=FG)
    return {reach: ON, pull[0]: ON, pull[1]: BACK, fwd[0]: BACK,
            fwd[1]: dict(aim=1, cam_add=RACK_UP, gun_add=(-0.5, 0.0, 0.0), fing=FG),          # the slide leaves the fingers
            fwd[1] + 3: dict(aim=1, cam_add=tuple(0.5 * x for x in RACK_UP), fing='aim')}


def rack_slide(f, pull, fwd):
    """how far back the slide is at frame f (0..RACK_PULL of its travel)"""
    if f <= pull[0]:
        u = 0.0
    elif f <= pull[1]:
        u = (f - pull[0]) / float(pull[1] - pull[0]); u = u * u * (3 - 2 * u)
    elif f <= fwd[0]:
        u = 1.0
    else:
        u = max(0.0, 1.0 - ((f - fwd[0]) / float(fwd[1] - fwd[0])) ** 2)
    return u * RACK_PULL


def read_game(p):
    f = os.path.join(MOD, p.replace('/', os.sep))
    return open(f, 'rb').read() if os.path.isfile(f) else vfs.read(p)


def gun_facts(name):
    """slide forward / back values and the magazine's travel (gun frame) for one gun"""
    g = GUNS[name]
    a = R.load(g['dir'] + '/' + g['clip'])
    n = a.numFrames
    f = dict(n=n, a=a)
    sj = os.path.join(HERE, 'slide_%s.json' % name)
    if g['slide'] == 'coop_slide':
        sp = json.load(open(sj))
        f['fwd_v'] = np.zeros(4); f['back_v'] = np.r_[np.array(sp['back']) * sp['travel'], 0.0]
    else:
        cs = a.names.index(g['slide'] + ' pos')
        f['fwd_v'] = a.V[n - 1, cs].copy(); f['back_v'] = a.V[n // 3, cs].copy()
        if g['empty']:
            e = R.load(g['dir'] + '/' + g['empty'])
            f['back_v'] = e.V[0, e.names.index(g['slide'] + ' pos')].copy()      # exactly where idle_empty leaves the slide
    if g['mag']:
        cm = a.names.index(g['mag'] + ' pos')
        seat_v = a.V[0, cm].copy()
        d = np.linalg.norm(a.V[:, cm, :3] - seat_v[:3], axis=1)
        low_v = a.V[int(np.argmax(d * (np.arange(n) > n // 2))), cm].copy()      # the new magazine held under the well
        # the bone's own frame is not always the gun's (Hi-Standard): an explicit `magup` (gun frame, u) wins
        f.update(cm=cm, seat_v=seat_v, low_v=low_v, magup=g.get('magup') or tuple(float(x) * R.S for x in (seat_v - low_v)[:3]))
    else:
        f['magup'] = g['magup']
    return f


def build(name, root):
    g = GUNS[name]
    raw = read_game(g['dir'] + '/' + g['clip'])
    F = gun_facts(name)
    a, n = F['a'], F['n']
    t = g['t']
    chans = {nm: a.V[:, c].copy() for c, nm in enumerate(a.names)}
    for nm in chans:
        if nm.endswith(' pos'):
            chans[nm][:, 3] = 0.0                    # a pos channel's 4th value is unused (garbage in the retail file)
    sl = g['slide'] + ' pos'
    if g['mag']:
        s0, s1 = t['seat']
        Vm = chans[g['mag'] + ' pos']
        for f in range(n):
            if f >= s1:
                Vm[f, :3] = F['seat_v'][:3]
            elif f >= s0 - 4:
                u = max(0.0, (f - s0) / float(s1 - s0)); u = u * u * (3 - 2 * u)
                Vm[f, :3] = F['low_v'][:3] + (F['seat_v'][:3] - F['low_v'][:3]) * u

    def slide_track(f0, f1):
        out = np.zeros((n, 4))
        for f in range(n):
            u = min(1.0, max(0.0, (f - f0) / float(f1 - f0)))
            out[f, :3] = F['back_v'][:3] + (F['fwd_v'][:3] - F['back_v'][:3]) * (u * u)       # spring-driven: it accelerates into the stop
        return out

    def write(fn, keyed, frames=n):
        dst = os.path.join(root, (g['dir'] + '/' + fn).replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        gunskc.write(dst, raw, frames, {k: [list(v[f]) for f in range(frames)] for k, v in keyed.items()})
        print(name, '->', g['dir'] + '/' + fn, frames, 'frames')
        return fn
    still = np.zeros((n, 4)); still[:, :3] = F['fwd_v'][:3]
    rack = g.get('rack')
    if rack:                                     # hand-cycled: the slide is forward, and racked at the end - always
        for f in range(n):
            still[f, :3] = F['fwd_v'][:3] + (F['back_v'][:3] - F['fwd_v'][:3]) * rack_slide(f, rack['pull'], rack['fwd'])
    rot = {} if g['slide'] != 'coop_slide' else {g['slide'] + ' rot': np.tile(np.array([0, 0, 0, 1.0]), (n, 1))}
    outs = {}
    k = dict(chans); k.update(rot); k[sl] = still
    outs['reload_ads_loaded'] = write('coop_%s_reload_ads_loaded.skc' % name, k)
    k = dict(chans); k.update(rot); k[sl] = still if rack else slide_track(*t['fwd'])
    outs['reload_ads_empty'] = write('coop_%s_reload_ads_empty.skc' % name, k)
    if g['slide'] == 'coop_slide' and not rack:
        # the retail clips of these guns have no slide channel: an emptied gun needs its own idle and hip reload
        k = {nm: a.V[:, c].copy() for c, nm in enumerate(a.names)}; k.update(rot)
        k[sl] = slide_track(n - 16, n - 14)                                   # hip: forward right after the retail magazine seats
        outs['reload_empty'] = write('coop_%s_reload_empty.skc' % name, k)
        back1 = np.zeros((1, 4)); back1[0, :3] = F['back_v'][:3]
        outs['idle_empty'] = write('coop_%s_idle_empty.skc' % name, {sl: back1, g['slide'] + ' rot': np.array([[0, 0, 0, 1.0]])}, frames=1)
    # ---- the aimed loaded sound: the retail sample up to the slide noises, faded out
    w = wave.open(io.BytesIO(vfs.read(g['wav'])))
    sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
    d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16 if sw == 2 else np.uint8).astype(np.float64)
    if sw == 1:
        d = (d - 128.0) * 256.0
    d = d.reshape(-1, ch)
    kk = int(sr * g['cut'] / 30.0)
    d = d[:kk].copy()
    fl = int(sr * 0.08)
    d[-fl:] *= np.linspace(1.0, 0.0, fl)[:, None]
    wav_out = 'sound/weapons/foley/coop_%s_reload_loaded.wav' % name
    dst = os.path.join(root, wav_out.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    wo = wave.open(dst, 'wb'); wo.setnchannels(ch); wo.setsampwidth(2); wo.setframerate(sr)
    wo.writeframes(np.clip(d, -32768, 32767).astype('<i2').tobytes()); wo.close()
    # ---- every weapon tik that plays this gun clip gets the animations and the alias
    n_t = 0
    wd = os.path.join(MOD, 'models', 'weapons')
    for fn in sorted(os.listdir(wd)):
        if not fn.lower().endswith('.tik'):
            continue
        tx = open(os.path.join(wd, fn), 'rb').read().decode('latin-1')
        if not re.search(r'(?im)^\s*reload\s+%s\b' % re.escape(g['clip']), tx) or not re.search(r'(?im)^\s*path\s+%s\s*$' % re.escape(g['dir']), tx):
            continue
        nl = '\r\n' if '\r\n' in tx else '\n'
        s = tx.replace('\r\n', '\n')
        m = re.search(r'(?im)^(\s*)reload\s+%s[^\n]*\n' % re.escape(g['clip']), s)
        ind = m.group(1)
        own = re.search(r'entry\s+sound\s+(\S+)', s[m.end():m.end() + 400])
        own = own.group(1) if own else g['snd']                               # this tik's own reload sound
        lsnd = (g['snd'] + '_loaded') if (own.lower() == g['snd'].lower() and not rack) else own
        blk = '%s// HZM coop [aimed reload 2026-10-12] shown by the cgame instead of `reload` (aimed; hip when empty)\n' % ind
        for an in ('reload_ads_loaded', 'reload_ads_empty', 'reload_empty'):
            if an in outs:
                blk += '%s%s\t%s\n%s{\n%s\tclient\n%s\t{\n%s\t\tentry sound %s item\n%s\t}\n%s}\n' % (
                    ind, an, outs[an], ind, ind, ind, ind, lsnd if an == 'reload_ads_loaded' else own, ind, ind)
        if 'idle_empty' in outs and not re.search(r'(?im)^\s*idle_empty\s', s):
            blk += '%sidle_empty\t%s\n' % (ind, outs['idle_empty'])
        s = s[:m.start()] + blk + s[m.start():]
        ci = re.search(r'(?m)^init\s*\n\{\n(?:.*\n)*?^\tclient\s*\n\t\{\n', s)
        assert ci, fn + ': no init client block'
        if lsnd != own:
            s = s[:ci.end()] + '\t\taliascache %s %s soundparms %s\n' % (lsnd, wav_out, PARMS) + s[ci.end():]
        dp = 0
        for ln in s.split('\n'):
            c = ln.split('//')[0]
            dp += c.count('{') - c.count('}')
            assert dp >= 0, fn
        assert dp == 0, fn
        dst = os.path.join(root, 'models', 'weapons', fn)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(s.replace('\n', nl).encode('latin-1'))
        n_t += 1
    print(name, 'loaded sound', wav_out, round(kk / float(sr), 2), 's | staged tiks:', n_t, '| magazine travel (gun u):', np.round(F['magup'], 2))


if __name__ == '__main__':
    for nm in (list(GUNS) if sys.argv[1] == 'all' else sys.argv[1].split(',')):
        build(nm, sys.argv[2])
