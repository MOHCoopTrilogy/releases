"""The pistols that BORROW the Colt / P38 hand rows (list item D): the gun side of their aimed reloads.

pistolgun.py gives the four pistols with rows of their own a working slide in an aimed reload (reload_ads_loaded: the
slide never moves; reload_ads_empty: locked back, runs forward when the support thumb sweeps the stop). The guns that
share those hand clips had nothing: aimed, the Pacific Colt snapped its slide back in a LOADED reload (run pa6, 3.1 %
of the centre box), the TT-33's 7-frame reload clip racked the slide in the first 0.2 s and an emptied gun never showed
an open slide. This module stages the same set for every such gun whose mesh has a slide bone, timed to the hand clip
it plays under (pistolgun.GUNS[hands]['t']):

    reload_ads_loaded   aimed, rounds left: magazine out / in, slide still
    reload_ads_empty    aimed, empty: slide locked back from frame 0, forward over t['fwd']
    reload_empty        hip, empty (guns with no idle_empty of their own): back until the retail magazine seats
    idle_empty          slide back (guns that have none)
    reload              only where the retail gun clip is shorter than the hand clip (TT-33: 7 frames): the same
                        look padded to 73 frames, so the server's weapon state lasts as long as the hands' reload
                        and the cgame has a `reload` to swap for all of it

    python p12.py <name|all> <stage root>        tiks are read from the mod tree, else from the live install's paks
"""
import sys, os, re
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc, pistolgun
R = gunskc.R
vfs = R.vfs
MOD = pistolgun.MOD
N = 73
LOADED_SND = {'colt45_snd_reload': ('colt45_snd_reload_loaded', 'sound/weapons/foley/coop_colt45_reload_loaded.wav'),
              'p38_snd_reload': ('P38_snd_reload_loaded', 'sound/weapons/foley/coop_p38_reload_loaded.wav')}

SIDE = {
    'coltpa': dict(hands='colt45', dir='models/weapons/coop_coltpa', clip='reload_colt45.skc', idle='colt45.skc', empty='colt45_empty.skc',
                   slide='chamber', mag='clip'),
    'colts': dict(hands='colt45', dir='models/weapons/colt45', clip='reload_colt45.skc', idle='colt45.skc', empty='colt45_empty.skc',
                  slide='chamber', mag='clip', only=['colt_silenced']),
    'ppk': dict(hands='colt45', dir='models/weapons/ppk', clip='PPK_reload.skc', idle='PPK.skc', empty='PPK_empty.skc', slide='Bone3', mag='clip',
                also={'Bone2 rot': 'empty'}),          # the hammer stays cocked with the slide back
    'tt33': dict(hands='colt45', dir='models/weapons/tt33', clip='tt33_reload.skc', idle='tt33.skc', empty=None, slide='selfcock', mag=None,
                 travel=['tt33_fire.skc', 'tt33_reload.skc']),   # no pad (bug-3736): `reload` is the server's row and stays as released
    'berettas': dict(hands='colt45', dir='models/weapons/beretta', clip='beretta_reload.skc', idle='beretta.skc', empty=None, slide='Rechamber',
                     mag='Release', magdrop=4.0, travel=['beretta_reload.skc'], lock=0.9),
    # meshes with NO slide / bolt bone: the part is cut out onto `coop_slide` (bonefit.split; islands from _meshsurvey.py)
    # silenced P38 (S93 remodel, not the retail P38 mesh pistolgun.py splits): slide body + rear sight; the barrel stays
    'p38s': dict(hands='colt45', dir='models/weapons/P38', clip='P38_reload.skc', idle='P38.skc', empty=None, slide='coop_slide', mag='p38clip',
                 only=['p38silenced'], split=dict(skd='P38silenced.skd', parent='Box01', back=2.3, parts=[('1', 236, -0.5), ('1', 72, 0.23)],
                                                    fill=dict(surf='1', c=(1.0, -0.63, -2.57), s=(1.0, 0.44, 1.46), uv_at=(1.5, -1.39, -2.9), park=0.9))),
    # Nambu Type 14: a BOLT with a round cocking knob at the rear (surface Regroup02: knob + bolt body), it comes straight back
    'nambu': dict(hands='colt45', dir='models/weapons/P38', clip='P38_reload.skc', idle='P38.skc', empty=None, slide='coop_slide', mag='p38clip',
                  only=['nambu'], split=dict(skd='nambu.skd', parent='Box01', back=1.9, parts=[('Regroup02', 325, -2.48), ('Regroup02', 78, -1.59)])),
}


def rd(p):
    f = os.path.join(MOD, p.replace('/', os.sep))
    return open(f, 'rb').read() if os.path.isfile(f) else vfs.read(p)


def tik_stems():
    st = {}
    for k in vfs.glob_paths('models/weapons/', '.tik'):
        if k.count('/') == 2:
            st[os.path.basename(k)[:-4]] = None
    for fn in os.listdir(os.path.join(MOD, 'models', 'weapons')):
        if fn.lower().endswith('.tik'):
            st[fn[:-4].lower()] = fn[:-4]
    return st


def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def patch_tik(stem, s, clips, ind_note, sound_cut=True):
    """insert the aimed / empty animations before the tik's `reload` line; returns the new text"""
    # IDEMPOTENT (2026-10-13): a tik that lives only in a pak is read back through the wip overlay, i.e. already
    # patched - every earlier block (they stack right before the `reload` line) and alias line goes first
    s = re.sub(r'(?ims)^[ \t]*// HZM coop \[aimed reload, pistol lane 2026-10-12\].*?(?=^[ \t]*reload[ \t]+\S+\.skc)', '', s)
    s = re.sub(r'(?im)^[ \t]*aliascache[ \t]+\S+_loaded[ \t]+\S+[ \t]+soundparms[^\n]*\n', '', s)
    m = re.search(r'(?im)^(\s*)reload\s+\S+\.skc[^\n]*\n', s)
    ind = m.group(1)
    own = re.search(r'entry\s+sound\s+(\S+)', s[m.end():m.end() + 900])
    own = own.group(1) if own else None
    lsnd = own
    if own and sound_cut and own.lower() in LOADED_SND:
        lsnd = LOADED_SND[own.lower()][0]
    blk = '%s// HZM coop [aimed reload, pistol lane 2026-10-12] %s\n' % (ind, ind_note)
    for an in ('reload_ads_loaded', 'reload_ads_empty', 'reload_empty'):
        if an in clips:
            snd = lsnd if an == 'reload_ads_loaded' else own
            blk += '%s%s\t%s\n' % (ind, an, clips[an])
            if snd:
                blk += '%s{\n%s\tclient\n%s\t{\n%s\t\tentry sound %s item\n%s\t}\n%s}\n' % (ind, ind, ind, ind, snd, ind, ind)
    if 'idle_empty' in clips and not re.search(r'(?im)^\s*idle_empty\s', s):
        blk += '%sidle_empty\t%s\n' % (ind, clips['idle_empty'])
    s = s[:m.start()] + blk + s[m.start():]
    if 'reload' in clips:                                  # the padded hip clip replaces the short retail one
        s = re.sub(r'(?im)^(\s*reload\s+)\S+\.skc', lambda mm: mm.group(1) + clips['reload'], s, count=1)
    if lsnd != own:
        ci = re.search(r'(?m)^init\s*\n\{\n(?:.*\n)*?^\tclient\s*\n\t\{\n', s)
        assert ci, stem + ': no init client block'
        s = s[:ci.end()] + '\t\taliascache %s %s soundparms %s\n' % (lsnd, LOADED_SND[own.lower()][1], pistolgun.PARMS) + s[ci.end():]
    return s


def depth_ok(s, stem):
    dp = 0
    for ln in s.split('\n'):
        c = ln.split('//')[0]
        dp += c.count('{') - c.count('}')
        assert dp >= 0, stem
    assert dp == 0, stem


def write_tik(root, stem_file, s, nl):
    dst = os.path.join(root, 'models', 'weapons', stem_file + '.tik')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(s.replace('\n', nl).encode('latin-1'))


def tiks_for(g, anim='reload'):
    """(file stem, text) of every weapon tik that plays g['clip'] as `anim` from g['dir']"""
    out = []
    for low, real in sorted(tik_stems().items()):
        if g.get('only') and low not in g['only']:
            continue
        raw = rd('models/weapons/%s.tik' % (real or low))
        if raw is None:
            continue
        tx = raw.decode('latin-1')
        if not re.search(r'(?im)^\s*%s\s+%s\b' % (anim, re.escape(g['clip'])), tx) or not re.search(r'(?im)^\s*path\s+%s\s*$' % re.escape(g['dir']), tx):
            continue
        if real is None:
            w = vfs.winner('models/weapons/%s.tik' % low)
            real = os.path.basename(w[1])[:-4]
        out.append((real, tx))
    return out


def build(name, root):
    g = SIDE[name]
    t = pistolgun.GUNS[g['hands']]['t']
    raw = rd(g['dir'] + '/' + g['clip'])
    a = R.load(g['dir'] + '/' + g['clip'])
    idle = R.load(g['dir'] + '/' + g['idle'])
    sl = g['slide'] + ' pos'
    sp = g.get('split')
    if sp:
        import bonefit as BF
        tik = 'models/weapons/%s.tik' % g['only'][0]
        BF.split(tik, g['dir'] + '/' + sp['skd'], {'coop_slide': sp['parts']}, os.path.join(root, (g['dir'] + '/' + sp['skd']).replace('/', os.sep)))
        A_, o_ = BF.fit(tik, sp['parent'])
        if sp.get('fill'):                 # a steel block inside the cut-out slide's open rear (it rides with the slide): no dark slot when it is back
            import add_part as AP
            fl = sp['fill']; skf = os.path.join(root, (g['dir'] + '/' + sp['skd']).replace('/', os.sep))
            d_ = open(skf, 'rb').read()
            d_ = d_[:AP.SK.read_skd(d_).ofsEnd]              # split_bone leaves a few padding bytes after ofsEnd; add() wants none
            out_, info_ = AP.add(d_, tik, 'coop_fill', 'coop_slide', fl['surf'], fl['c'], fl['s'], fl.get('uv_at'))
            open(skf, 'wb').write(out_)
            print('   fill', name, info_)
        fwd_v = np.zeros(4)
        back_v = np.r_[np.array([-sp['back'], 0.0, 0.0]) @ np.linalg.inv(A_), 0.0]
    else:
        fwd_v = idle.V[0, idle.names.index(sl)].copy()
    if sp:
        pass
    elif g.get('empty'):
        e = R.load(g['dir'] + '/' + g['empty'])
        back_v = e.V[0, e.names.index(sl)].copy()
    else:
        best = (0.0, fwd_v)
        for c in g['travel']:
            k = R.load(g['dir'] + '/' + c)
            V = k.V[:, k.names.index(sl)]
            d = np.linalg.norm(V[:, :3] - fwd_v[:3], axis=1)
            if d.max() > best[0]:
                best = (float(d.max()), V[int(np.argmax(d))].copy())
        back_v = fwd_v + (best[1] - fwd_v) * g.get('lock', 1.0)
    travel = float(np.linalg.norm((back_v - fwd_v)[:3]) * R.S)
    clips = {}

    def write(fn, keyed, frames=N):
        dst = os.path.join(root, (g['dir'] + '/' + fn).replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        kd = {k: [list(v[f]) for f in range(frames)] for k, v in keyed.items()}
        if sp and sp.get('fill') and sl in kd:      # the filler block comes flush with the slide's rear only as the slide goes back
            pv = np.r_[np.array([-sp['fill']['park'], 0.0, 0.0]) @ np.linalg.inv(A_), 0.0]
            tot = float(np.linalg.norm((back_v - fwd_v)[:3])) or 1.0
            kd['coop_fill pos'] = [list(pv * min(1.0, float(np.linalg.norm((np.asarray(kd[sl][f]) - fwd_v)[:3])) / tot)) for f in range(frames)]
        gunskc.write(dst, raw, frames, kd, frame_time=1 / 30.0)
        return fn

    def slide_track(f0, f1, n=N):
        o = np.zeros((n, 4))
        for f in range(n):
            u = min(1.0, max(0.0, (f - f0) / float(f1 - f0)))
            o[f, :3] = back_v[:3] + (fwd_v[:3] - back_v[:3]) * (u * u)
        return o
    still = np.zeros((N, 4)); still[:, :3] = fwd_v[:3]
    mag = {}
    if g.get('mag'):
        cm = a.names.index(g['mag'] + ' pos')
        seat_v = idle.V[0, idle.names.index(g['mag'] + ' pos')].copy() if (g['mag'] + ' pos') in idle.names else a.V[0, cm].copy()
        d = np.linalg.norm(a.V[:, cm, :3] - seat_v[:3], axis=1)
        far_v = a.V[int(np.argmax(d)), cm].copy()
        if g.get('magdrop'):                       # a retail magazine that flies 40 u: keep the direction, a short way
            far_v = seat_v + (far_v - seat_v) * min(1.0, g['magdrop'] / max(1e-6, float(d.max() * R.S)))
        o0, o1 = t['out']; s0, s1 = t['seat']
        Vm = np.zeros((N, 4))
        for f in range(N):
            w = smooth((f - o0) / float(o1 - o0)) if f < s0 - 6 else 1.0 - smooth((f - (s0 - 6)) / float(s1 - (s0 - 6)))
            Vm[f, :3] = seat_v[:3] + (far_v[:3] - seat_v[:3]) * w
        mag = {g['mag'] + ' pos': Vm}

    def also(which):
        o = {}
        for ch, src in (g.get('also') or {}).items():
            if src == 'empty' and which == 'empty':
                e2 = R.load(g['dir'] + '/' + g['empty'])
                v = e2.V[0, e2.names.index(ch)].copy()
                i = idle.V[0, idle.names.index(ch)].copy()
                tr = np.tile(i, (N, 1))
                for f in range(N):
                    if f <= t['fwd'][1]:
                        tr[f] = v                 # cocked while the slide is back and as it runs home (it stays cocked: held to the end)
                    else:
                        tr[f] = v
                o[ch] = tr
        return o
    reuse = name == 'colts'
    if sp:                                       # a new bone: every clip carries its rotation too (identity)
        _w0 = write

        def write(fn, keyed, frames=N):
            keyed = dict(keyed); keyed.setdefault(g['slide'] + ' rot', np.tile(np.array([0, 0, 0, 1.0]), (frames, 1)))
            return _w0(fn, keyed, frames)
    pre = 'coop_colt45' if reuse else 'coop_' + name
    k = dict(mag); k[sl] = still
    clips['reload_ads_loaded'] = pre + '_reload_ads_loaded.skc' if reuse else write(pre + '_reload_ads_loaded.skc', k)
    k = dict(mag); k[sl] = slide_track(*t['fwd']); k.update(also('empty'))
    clips['reload_ads_empty'] = pre + '_reload_ads_empty.skc' if reuse else write(pre + '_reload_ads_empty.skc', k)
    if not g.get('empty'):
        # hip, emptied gun: the retail clip knows no lock-back. Retail motion otherwise; slide back until the magazine is in
        n0 = a.numFrames
        k = {nm: np.array([a.V[min(f, n0 - 1), c] for f in range(N)]) for c, nm in enumerate(a.names)}
        for nm in k:
            if nm.endswith(' pos'):
                k[nm][:, 3] = 0.0
        k[sl] = slide_track(N - 16, N - 14)
        clips['reload_empty'] = write(pre + '_reload_empty.skc', k)
        b1 = np.zeros((1, 4)); b1[0, :3] = back_v[:3]
        clips['idle_empty'] = write(pre + '_idle_empty.skc', dict({sl: b1}, **({g['slide'] + ' rot': np.array([[0, 0, 0, 1.0]])} if sp else {})), frames=1)
    if g.get('pad') and a.numFrames < N:
        n0 = a.numFrames
        k = {nm: np.array([a.V[min(f, n0 - 1), c] for f in range(N)]) for c, nm in enumerate(a.names)}
        for nm in k:
            if nm.endswith(' pos'):
                k[nm][:, 3] = 0.0
        k[sl] = np.array([a.V[f, a.names.index(sl)] if f < n0 else np.r_[fwd_v[:3], 0.0] for f in range(N)])
        k[sl][:, 3] = 0.0
        clips['reload'] = write(pre + '_reload_hip.skc', k)
    nt = []
    for stem, tx in tiks_for(g):
        nl = '\r\n' if '\r\n' in tx else '\n'
        s = patch_tik(stem, tx.replace('\r\n', '\n'), clips, 'shown by the cgame instead of `reload` (aimed; hip when empty): the slide works')
        depth_ok(s, stem)
        write_tik(root, stem, s, nl)
        nt.append(stem)
    print('%-9s hands %-7s slide %-10s travel %.2f u | clips %s | tiks %d: %s' % (name, g['hands'], g['slide'], travel, ' '.join(sorted(clips)), len(nt), ' '.join(nt)))


if __name__ == '__main__':
    for nm in (list(SIDE) if sys.argv[1] == 'all' else sys.argv[1].split(',')):
        build(nm, sys.argv[2])
