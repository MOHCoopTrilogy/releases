"""The GUN side of the aimed magazine-pistol reloads (user 2026-10-12: "functioning slides, bolts, etc"; "on a reload
with a round chambered there is no slide action").

The retail gun clip snaps the slide back on frame 1 of EVERY reload and snaps it forward again a frame after the
magazine. For the aimed reload the cgame (ads-next) shows one of two animations of the weapon tik instead of `reload`:
    reload_ads_loaded   the slide never moves; the magazine drops and a new one is pushed in
    reload_ads_empty    the slide is locked back from the first frame (as idle_empty leaves it) and RUNS forward
                        over a few frames when the stop is released
Both keep the retail clip's length, so the server's timing is untouched (it still runs `reload`). The loaded one gets
its own sound: the retail sample cut before the slide noises.

    python pistolgun.py <gun|all> <stage root>
"""
import sys, os, re, io, wave, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gunskc
R = gunskc.R
vfs = R.vfs
MOD = r'C:\mohaa-coop-dev\hzm-mohaa-coop-mod'

GUNS = {
    # clip: the retail gun reload clip; slide / mag: the bones; seat: frames the magazine rises over; fwd: frames the
    # slide runs forward over; cut: the loaded sound ends here (clip frame); events are also read by pistolbake.py
    'colt45': dict(dir='models/weapons/colt45', clip='reload_colt45.skc', empty='colt45_empty.skc', slide='chamber', mag='clip',
                   seat=(33, 36), fwd=(54, 56), snd='colt45_snd_reload', wav='sound/weapons/foley/Colt45Reload1b.wav', cut=46,
                   parms='0.9 0.2 1.0 0.0 160 1000 item loaded always maps "dm obj lib"'),      # `always`: without it a tik alias is dropped (bLoadForMap)
}


def read_game(p):
    f = os.path.join(MOD, p.replace('/', os.sep))
    return open(f, 'rb').read() if os.path.isfile(f) else vfs.read(p)


def build(name, root):
    g = GUNS[name]
    raw = read_game(g['dir'] + '/' + g['clip'])
    a = R.load(g['dir'] + '/' + g['clip'])
    n = a.numFrames
    V = a.V.copy()
    cs, cm = a.names.index(g['slide'] + ' pos'), a.names.index(g['mag'] + ' pos')
    fwd_v, back_v, seat_v = V[n - 1, cs].copy(), V[n // 2, cs].copy(), V[0, cm].copy()
    e = R.load(g['dir'] + '/' + g['empty'])
    if g['slide'] + ' pos' in e.names:
        back_v = e.V[0, e.names.index(g['slide'] + ' pos')].copy()          # exactly where idle_empty leaves the slide
    low_v = V[g['fwd'][0] - 6, cm].copy()                                    # the new magazine held under the well
    s0, s1 = g['seat']
    Vm = V[:, cm].copy()
    for f in range(n):
        if f >= s1:
            Vm[f] = seat_v
        elif f >= s0 - 4:
            u = max(0.0, (f - s0) / float(s1 - s0))
            u = u * u * (3 - 2 * u)
            Vm[f] = low_v + (seat_v - low_v) * u
    outs = {}
    for kind in ('loaded', 'empty'):
        Vk = V.copy()
        Vk[:, cm] = Vm
        if kind == 'loaded':
            Vk[:, cs] = V[0, cs]
        else:
            f0, f1 = g['fwd']
            for f in range(n):
                u = min(1.0, max(0.0, (f - f0) / float(f1 - f0)))
                Vk[f, cs] = back_v + (fwd_v - back_v) * (u * u)              # spring-driven: it accelerates into the stop
        out = '%s/coop_%s_reload_ads_%s.skc' % (g['dir'], name, kind)
        dst = os.path.join(root, out.replace('/', os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        for c_ in (cs, cm):
            Vk[:, c_, 3] = 0.0                    # a pos channel's 4th value is unused (garbage in the retail file)
        gunskc.write(dst, raw, n, {nm: [list(Vk[f, c]) for f in range(n)] for c, nm in enumerate(a.names)})
        outs[kind] = os.path.basename(out)
        print(name, kind, '->', out, n, 'frames')
    # ---- the loaded sound: the retail sample up to the slide noises, faded out
    w = wave.open(io.BytesIO(vfs.read(g['wav'])))
    sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
    d = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16 if sw == 2 else np.uint8).astype(np.float64)
    if sw == 1:
        d = (d - 128.0) * 256.0
    d = d.reshape(-1, ch)
    k = int(sr * g['cut'] / 30.0)
    d = d[:k].copy()
    fl = int(sr * 0.08)
    d[-fl:] *= np.linspace(1.0, 0.0, fl)[:, None]
    wav_out = 'sound/weapons/foley/coop_%s_reload_loaded.wav' % name
    dst = os.path.join(root, wav_out.replace('/', os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    wo = wave.open(dst, 'wb'); wo.setnchannels(ch); wo.setsampwidth(2); wo.setframerate(sr)
    wo.writeframes(np.clip(d, -32768, 32767).astype('<i2').tobytes()); wo.close()
    print(name, 'loaded sound ->', wav_out, round(k / float(sr), 2), 's')
    # ---- every weapon tik that plays this gun clip gets the two animations and the alias
    n_t = 0
    wd = os.path.join(MOD, 'models', 'weapons')
    for fn in sorted(os.listdir(wd)):
        if not fn.lower().endswith('.tik'):
            continue
        t = open(os.path.join(wd, fn), 'rb').read().decode('latin-1')
        if not re.search(r'(?im)^\s*reload\s+%s\b' % re.escape(g['clip']), t) or not re.search(r'(?im)^\s*path\s+%s\s*$' % re.escape(g['dir']), t):
            continue
        nl = '\r\n' if '\r\n' in t else '\n'
        s = t.replace('\r\n', '\n')
        m = re.search(r'(?m)^(\s*)reload\s+%s[^\n]*\n' % re.escape(g['clip']), s)
        ind = m.group(1)
        own = re.search(r'entry\s+sound\s+(\S+)', s[m.end():m.end() + 400])
        own = own.group(1) if own else g['snd']                               # this tik's own reload sound
        blk = ''.join('%s%s\t%s\n%s{\n%s\tclient\n%s\t{\n%s\t\tentry sound %s item\n%s\t}\n%s}\n' % (
            ind, an, outs[kind], ind, ind, ind, ind, snd, ind, ind)
            for an, kind, snd in (('reload_ads_loaded', 'loaded', (g['snd'] + '_loaded') if own == g['snd'] else own),
                                  ('reload_ads_empty', 'empty', own)))
        if own != g['snd']:
            print('   ', fn, 'has its own reload sound', own, '- kept for both')
        s = s[:m.start()] + ('%s// HZM coop [aimed reload 2026-10-12] shown by the cgame instead of `reload` while the AIMED reload clip plays\n' % ind) + blk + s[m.start():]
        ci = re.search(r'(?m)^init\s*\n\{\n(?:.*\n)*?^\tclient\s*\n\t\{\n', s)
        assert ci, fn + ': no init client block'
        s = s[:ci.end()] + '\t\taliascache %s_loaded %s soundparms %s\n' % (g['snd'], wav_out, g['parms']) + s[ci.end():]
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
    print(name, 'staged tiks:', n_t)


if __name__ == '__main__':
    for nm in (list(GUNS) if sys.argv[1] == 'all' else sys.argv[1].split(',')):
        build(nm, sys.argv[2])
