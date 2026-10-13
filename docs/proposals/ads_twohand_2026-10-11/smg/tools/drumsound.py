"""The reload SOUND of the two drum Thompsons (Thompson 50rd, Thompson (1928 Tommy)), re-timed to what the hands do.

Both tiks play the stick-magazine Thompson's sound (thompson_snd_reload = ThompsonReload1a.wav: magazine out at clip
frames 9-13, in at 39 / 45-49, the handle at 57-65; 1/30 s frames) over a drum change the reload audit timed otherwise
(the drum leaves at f24-30 and is seated at f54-58), and this lane cocks an EMPTIED drum gun FIRST (f10-16; a Thompson
drum goes in and out only with the bolt held back). Played as it is, the handle would be heard 1.5 s after it is pulled.

So the same recording is laid out again, piece by piece (nothing new is recorded; 6 ms fades at every cut):
    coop_thompson_snd_reload_drum          EMPTY rows (reload_empty, reload_ads_empty): handle, drum out, drum in
    coop_thompson_snd_reload_drum_loaded   `reload` (rounds left): drum out, drum in - no handle
and the two staged tiks are pointed at them (client blocks only; the server reads none of it).

    cd smg/assets;  python ../tools/drumsound.py [--profile]      (after smggun.py; IRONSIGHT_EXTRA_PAKS unset)
"""
import sys, os, io, re, wave
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import smggun as SG
vfs = SG.vfs
SRC_ALIAS = 'thompson_snd_reload'
# (source frames a..b, placed at frame) - 1/30 s frames of the hands' clock
HANDLE = (55.5, 68.0, 8.5)        # the two clacks (source f59, f64.5) land on f12 and f17.5: the pull is f10-16
OUT = (9.0, 26.0, 24.5)           # source out f10-13 (+ its tail) -> f25.5-28.5 (the drum is drawn out f24-30)
IN_ = (37.0, 53.0, 46.0)          # source in f39 / f45-49 -> f48 (the drum meets its grooves) / f54-58 (seated f54-58)
PARMS = 'soundparms 1.5 0.0 1.0 0.05 160 1000 item loaded always maps "m e t dm obj lib"'
TIKS = ('models/weapons/thompson50.tik', 'models/weapons/thompsonsmg_tommy1928d.tik')
TAG = '// HZM coop [ads-smg drum sound]'


def load(wav):
    w = wave.open(io.BytesIO(vfs.read(wav)))
    sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
    assert sw == 2
    return np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float64).reshape(-1, ch), sr


def splice(d, sr, parts, dst):
    end = max(p[2] + (p[1] - p[0]) for p in parts)
    out = np.zeros((int(end / 30.0 * sr) + 1, d.shape[1]))
    fade = int(0.006 * sr)
    for a, b, at in parts:
        s0, s1 = int(a / 30.0 * sr), min(len(d), int(b / 30.0 * sr))
        seg = d[s0:s1].copy()
        k = np.linspace(0.0, 1.0, fade)
        seg[:fade] *= k[:, None]; seg[-fade:] *= k[::-1][:, None]
        o0 = int(at / 30.0 * sr)
        out[o0:o0 + len(seg)] += seg
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    o = wave.open(dst, 'wb')
    o.setnchannels(d.shape[1]); o.setsampwidth(2); o.setframerate(sr)
    o.writeframes(np.clip(out.round(), -32768, 32767).astype(np.int16).tobytes()); o.close()
    return len(out) / float(sr)


def main():
    wav = SG.sound_alias(SRC_ALIAS)
    d, sr = load(wav)
    if '--profile' in sys.argv:
        pk = np.abs(d).max()
        for f in range(int(len(d) / sr * 30) + 1):
            seg = d[int(f / 30.0 * sr):int((f + 1) / 30.0 * sr)]
            if len(seg):
                print('f%2d %5.1f %% %s' % (f, 100 * np.abs(seg).max() / pk, '#' * int(40 * np.abs(seg).max() / pk)))
        return
    t1 = splice(d, sr, [HANDLE, OUT, IN_], os.path.join('.', 'sound', 'weapons', 'foley', 'coop_thompson_snd_reload_drum.wav'))
    t2 = splice(d, sr, [OUT, IN_], os.path.join('.', 'sound', 'weapons', 'foley', 'coop_thompson_snd_reload_drum_loaded.wav'))
    print('%s (%.2f s) -> coop_thompson_snd_reload_drum.wav %.2f s (handle f%.1f, out f%.1f, in f%.1f), ..._drum_loaded.wav %.2f s' % (
        wav, len(d) / float(sr), t1, HANDLE[2], OUT[2], IN_[2], t2))
    for p in TIKS:
        dst = os.path.join('.', p.replace('/', os.sep))
        txt = open(dst, 'rb').read().decode('latin-1')
        nl = '\r\n' if '\r\n' in txt else '\n'
        txt = '\n'.join(l for l in txt.split('\n') if TAG not in l)
        ka = txt.lower().index('\nanimations')
        head, an = txt[:ka], txt[ka:]
        # rounds left: smggun pointed `reload` at the cut stick sound; the EMPTY rows carry the retail alias
        an, n1 = re.subn(r'(entry[ \t]+sound[ \t]+)coop_%s_loaded\b' % SRC_ALIAS, lambda m: m.group(1) + 'coop_%s_drum_loaded' % SRC_ALIAS, an)
        an, n2 = re.subn(r'(entry[ \t]+sound[ \t]+)%s\b' % SRC_ALIAS, lambda m: m.group(1) + 'coop_%s_drum' % SRC_ALIAS, an)
        assert n1 == 1 and n2 == 2, (p, n1, n2)
        mi = re.search(r'(?ms)^init\b.*?^[ \t]*client[ \t]*\r?\n[ \t]*\{[ \t]*\r?\n', head)
        assert mi, 'no init client block'
        line = ''.join('\t\taliascache coop_%s_%s sound/weapons/foley/coop_%s_%s.wav %s %s%s' % (SRC_ALIAS, k, SRC_ALIAS, k, PARMS, TAG, nl) for k in ('drum', 'drum_loaded'))
        head = head[:mi.end()] + line + head[mi.end():]
        open(dst, 'wb').write((head + an).encode('latin-1'))
        print('   %s: reload -> ..._drum_loaded, reload_empty / reload_ads_empty -> ..._drum' % os.path.basename(p))


if __name__ == '__main__':
    main()
