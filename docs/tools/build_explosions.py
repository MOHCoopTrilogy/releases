"""Convert licensed explosion recordings into game-ready coop explosion takes.

WHY THIS EXISTS. The trilogy has 366 explosion alias lines, and they all draw on a pool of about
34 distinct wavs. Explo_MetalMed1.wav alone is the tank, the truck, the plane, the jeep, the glider,
the AA gun, the bunker, the door, the K-5 railgun and the radio. That single fact is the whole reason
every explosion in the game sounds like every other explosion, and no amount of alias juggling fixes
it - the pool itself has to grow.

WHAT IT DOES NOT DO. It does not touch the existing aliases. New sounds land under a neutral folder
with new coop_ex_* alias names, so nothing retail is repointed and nothing can lose a first-definition
-wins race against ubersound.scr. Rewiring specific families is a separate, reversible step.

SOURCE PATHS ARE NOT NAMED IN THIS REPO. The licensed libraries must never appear in the mod, its
docs, its filenames or its commit messages - and a hard-coded path is exactly as public as a comment
(that is how it leaked once already). Point these at your local copies:

    set COOP_EX_KIT_DESIGNED=D:\\path\\to\\designed-explosions.zip
    set COOP_EX_KIT_FREE=D:\\path\\to\\free-explosion-pack.zip
    set COOP_EX_KIT_WARFARE=D:\\path\\to\\warfare-sounds.zip

Usage:  python docs/tools/build_explosions.py [--dry]
"""
import io
import math
import os
import struct
import sys
import wave
import zipfile

DRY = '--dry' in sys.argv

DESIGNED = os.environ.get('COOP_EX_KIT_DESIGNED', '')
FREE     = os.environ.get('COOP_EX_KIT_FREE', '')
WARFARE  = os.environ.get('COOP_EX_KIT_WARFARE', '')

OUT = 'C:/mohaa-coop-dev/hzm-mohaa-coop-mod/sound/coop_explosions/'
ALIAS_OUT = 'C:/mohaa-coop-dev/hzm-mohaa-coop-mod/ubersound/coop_explosions.scr'

SR_OUT = 22050
PEAK_TARGET = 0.80   # explosions carry the frame; louder headroom than the 0.72 used for foley
MAX_SECONDS = 6.0    # a tail longer than this is a trailer riser, not a weapon event

# category -> (alias stem, archive, [name substrings to match], how many to take)
# Ordered by what the game is actually missing. "distant" is the biggest gap: MOHAA has no
# off-map vocabulary at all, which is why every explosion reads as close.
PLAN = [
    ('close',   WARFARE,  ['explosion_small_no_tail', 'explosion_small_short',
                           'explosion_large_no_tail'], 12),
    ('grenade', FREE,     ['explo_grenade'], 9),
    ('large',   WARFARE,  ['explosion_large_'], 10),
    ('distant', WARFARE,  ['explosion_far_distant'], 8),
    ('debris',  DESIGNED, ['explosion-debris'], 12),
    ('sub',     WARFARE,  ['explosion_deep_low', 'explosion_med_long_tail'], 3),
    ('bomb',    FREE,     ['explo_bomb'], 6),
]

_zips = {}


def zopen(p):
    if p not in _zips:
        _zips[p] = zipfile.ZipFile(p)
    return _zips[p]


def decode(raw):
    """WAV -> (mono float list, samplerate). Handles 16/24/32-bit, mono or stereo.

    Stereo is folded by AVERAGING, not by taking the left channel. Designed stereo often has
    decorrelated sides, and dropping one channel throws away half the energy of the impact; the
    engine spatialises mono anyway. Phase-cancellation on the fold is possible in principle but
    these are recorded/layered impacts, not mid-side encodes.
    """
    w = wave.open(io.BytesIO(raw))
    p = w.getparams()
    data = w.readframes(p.nframes)
    w.close()
    n = len(data) // p.sampwidth
    if p.sampwidth == 3:
        b4 = bytearray(n * 4)
        b4[1::4] = data[0::3]
        b4[2::4] = data[1::3]
        b4[3::4] = data[2::3]
        v = [x / 2147483648.0 for x in struct.unpack('<%di' % n, bytes(b4))]
    elif p.sampwidth == 2:
        v = [x / 32768.0 for x in struct.unpack('<%dh' % n, data)]
    elif p.sampwidth == 4:
        v = [x / 2147483648.0 for x in struct.unpack('<%di' % n, data)]
    else:
        return None, 0
    if p.nchannels == 2:
        v = [(v[i] + v[i + 1]) * 0.5 for i in range(0, len(v) - 1, 2)]
    elif p.nchannels > 2:
        c = p.nchannels
        v = [sum(v[i:i + c]) / c for i in range(0, len(v) - c + 1, c)]
    return v, p.framerate


def lowpass(v, sr_in, sr_out):
    """Anti-alias before decimating. 96k -> 22.05k is a 4.35:1 ratio; without this every component
    above 11 kHz folds back down into the audible band as inharmonic grit, which on transient-heavy
    material is exactly where an explosion's character lives. A windowed-sinc FIR at 0.45*sr_out,
    applied only when actually downsampling."""
    if sr_in <= sr_out:
        return v
    fc = 0.45 * sr_out / sr_in          # normalised cutoff
    taps = 63
    half = taps // 2
    h = []
    for i in range(taps):
        k = i - half
        x = 2.0 * fc * (1.0 if k == 0 else math.sin(2.0 * math.pi * fc * k) / (2.0 * math.pi * fc * k))
        x *= 0.54 - 0.46 * math.cos(2.0 * math.pi * i / (taps - 1))   # Hamming
        h.append(x)
    s = sum(h)
    h = [x / s for x in h]
    n = len(v)
    out = [0.0] * n
    for i in range(n):
        acc = 0.0
        for j in range(taps):
            k = i + j - half
            if 0 <= k < n:
                acc += v[k] * h[j]
        out[i] = acc
    return out


def resample(v, sr_in, sr_out):
    ratio = sr_in / float(sr_out)
    n = int(len(v) / ratio)
    out = [0.0] * n
    for i in range(n):
        x = i * ratio
        i0 = int(x)
        f = x - i0
        a = v[i0] if i0 < len(v) else 0.0
        b = v[i0 + 1] if i0 + 1 < len(v) else a
        out[i] = a + (b - a) * f
    return out


def write(v, path):
    pk = max(abs(x) for x in v) or 1.0
    g = PEAK_TARGET / pk
    fi = int(SR_OUT * 0.0008)            # 0.8ms - never soften an explosion's attack
    fo = int(SR_OUT * 0.020)
    n = len(v)
    o = []
    for i, x in enumerate(v):
        s = x * g
        if i < fi:
            s *= i / float(fi)
        if i > n - fo:
            s *= max(0.0, (n - i) / float(fo))
        o.append(max(-32768, min(32767, int(s * 32767))))
    w = wave.open(path, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR_OUT)
    w.writeframes(struct.pack('<%dh' % len(o), *o))
    w.close()


def pick(archive, subs, want):
    """Matching names in the archive, deduped, deterministic order."""
    z = zopen(archive)
    names = []
    for n in z.namelist():
        if not n.lower().endswith('.wav'):
            continue
        b = n.split('/')[-1].lower()
        if '__macosx' in n.lower():
            continue
        if any(sub.lower() in b for sub in subs):
            names.append(n)
    names.sort()
    return names[:want]


def main():
    missing = [k for k, v in (('COOP_EX_KIT_DESIGNED', DESIGNED), ('COOP_EX_KIT_FREE', FREE),
                              ('COOP_EX_KIT_WARFARE', WARFARE)) if not v]
    if missing:
        sys.exit('Set %s to the source archives (deliberately not hard-coded).' % ', '.join(missing))

    if not DRY and not os.path.isdir(OUT):
        os.makedirs(OUT)

    made = []
    for stem, archive, subs, want in PLAN:
        got = pick(archive, subs, want)
        if not got:
            print('')
    print('Now regenerate the alias file - it also carries the coop-owned overrides,')
    print('which this converter deliberately does not know about:')
    print('    python docs/tools/gen_explosion_aliases.py')


main()
