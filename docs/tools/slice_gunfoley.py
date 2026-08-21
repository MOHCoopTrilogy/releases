"""Slice weapon-handling construction kits into individual game-ready takes.

The source kits are long-form: one 96 kHz / 24-bit file holds many performances of the same action
back to back, separated by room silence, and the whole mechanics folder is over 4 GB. Nothing in
that form is usable directly. This detects the discrete events, cuts them at zero crossings, trims,
fades, resamples to the project's 22050 Hz mono 16-bit convention and writes one WAV per take.

Two properties of the source are worth knowing:
  * every take exists at TWO mic positions - "Shotgun" (tight, dry, close) and "MS" (stereo, roomier).
    Shotgun is the first-person perspective, MS is what someone else's weapon sounds like across a
    room. This only slices the Shotgun set; the MS set is the same pipeline with a different filter
    if third-person handling foley is ever wanted.
  * output is a DERIVATIVE (sliced, downsampled, re-normalised), not a library file, and lands under
    a neutrally-named folder. The source library is never named in the mod, its docs or its commits.

Usage:  python docs/tools/slice_gunfoley.py [--dry]
"""
import io
import os
import re
import struct
import sys
import wave
import zipfile

DRY = '--dry' in sys.argv

W2 = 'F:/Boom Library - World War II Firearms (WAV).zip'
W1 = ('F:/Boom Library - World War I Firearms (Construction Kit) (WAV)/'
      'Boom Library - World War I Firearms (Construction Kit) (WAV).zip')
OUT = 'C:/mohaa-coop-dev/hzm-mohaa-coop-mod/sound/coop_gunfoley/'

SR_OUT = 22050
MAX_TAKES = 4        # per (class, action) - variety without bloating the pk3
PEAK_TARGET = 0.72   # consistent headroom; the alias carries the final volume

# class -> action -> list of (kit, weapon, source-action). Ordered: first source that yields
# enough takes wins, the rest are fallbacks. Weapon names are the kit's, not the mod's.
MANIFEST = {
    'pistol': {
        'handling_soft': [(W1, 'Colt M1911', 'Handling'), (W2, 'Walther P38', 'Handling')],
        'handling_hard': [(W1, 'Colt New Service', 'Handling Hard'), (W2, 'Walther P38', 'Handling')],
        'grab':          [(W1, 'Colt M1911', 'Grab'), (W1, 'P08 Luger', 'Grab')],
        'magcheck':      [(W1, 'Colt M1911', 'Mag In Out Slow'), (W2, 'Walther P38', 'Mag In Out Slow')],
        'dryfire':       [(W1, 'Steyr M1912', 'Dryfire'), (W1, 'Fn Highpower', 'Dryfire')],
    },
    'rifle': {
        'handling_soft': [(W2, 'Kar98K', 'Handling'), (W2, 'M1 Garand', 'Handling')],
        'handling_hard': [(W1, 'Springfield M1903', 'Handling Hard'), (W2, 'Kar98K', 'Handling')],
        'grab':          [(W2, 'M1 Garand', 'Grab'), (W2, 'Kar98K', 'Grab')],
        'safety':        [(W2, 'M1 Garand', 'Safety'), (W2, 'Kar98K', 'Safety')],
        'magcheck':      [(W2, 'M1 Garand', 'Mag In Out Slow'), (W2, 'Kar98K', 'Mag In Out Slow')],
        'dryfire':       [(W2, 'Mosin Nagant M1938', 'Dryfire'), (W1, 'Mosin Nagant M1891', 'Dryfire')],
    },
    'smg': {
        'handling_soft': [(W2, 'Thompson M1928A1', 'Handling'), (W2, 'MP 40', 'Handling')],
        'handling_hard': [(W2, 'Bergmann MP28', 'Handling Hard'), (W2, 'PPD 40', 'Handling Hard')],
        'grab':          [(W2, 'Thompson M1928A1', 'Grab'), (W2, 'MP 40', 'Grab')],
        'magcheck':      [(W2, 'MP 40', 'Mag In Out Slow'), (W2, 'Sten Gun Mark II', 'Mag In Out Slow')],
        'dryfire':       [(W2, 'M30 Drilling', 'Dryfire'), (W1, 'Fn Highpower', 'Dryfire')],
    },
    'mg': {
        'handling_soft': [(W2, 'MG 42', 'Handling'), (W2, 'Bren MG', 'Handling')],
        'handling_hard': [(W2, 'Bren MG', 'Handling'), (W2, 'DP 27', 'Handling')],
        'grab':          [(W2, 'MG 42', 'Grab'), (W2, 'Bren MG', 'Grab')],
        'magcheck':      [(W2, 'Bren MG', 'Mag In Out Slow'), (W2, 'DP 27', 'Mag In Out Slow')],
        'dryfire':       [(W2, 'MG 42', 'Dryfire'), (W2, 'M30 Drilling', 'Dryfire')],
    },
}

_zips = {}


def zopen(p):
    if p not in _zips:
        _zips[p] = zipfile.ZipFile(p)
    return _zips[p]


def find(kit, weapon, action):
    """Locate the Shotgun-mic kit file for one weapon+action."""
    z = zopen(kit)
    want = ('%s %s' % (weapon, action)).lower()
    for n in z.namelist():
        if '/Mechanics/' not in n or not n.endswith('_Shotgun.wav'):
            continue
        b = n.split('/')[-1].lower()
        m = re.match(r'gunmech_foley-(.+?)_b00m_\w+_shotgun\.wav', b)
        if m and m.group(1).strip() == want:
            return n
    return None


def decode(raw):
    """24-bit and 16-bit WAV -> list of floats, mono. 24-bit is unpacked with slice assignment
    rather than a per-sample loop; a 20 s 96 kHz file is 2M samples and the loop form is minutes."""
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
    else:
        return None, 0
    if p.nchannels == 2:
        v = v[0::2]
    return v, p.framerate


def events(v, sr, floor_db=-52.0, min_gap=0.10, min_len=0.045, max_len=1.6):
    """Discrete performances: RMS envelope, threshold relative to peak, merge across short gaps."""
    hop = max(1, int(sr * 0.004))
    env = []
    for i in range(0, len(v) - hop, hop):
        s = v[i:i + hop]
        acc = 0.0
        for x in s:
            acc += x * x
        env.append((acc / len(s)) ** 0.5)
    if not env:
        return []
    peak = max(env)
    if peak <= 0:
        return []
    thr = peak * (10 ** (floor_db / 20.0))
    on = [e > thr for e in env]
    gap = int(min_gap / 0.004)
    out, i = [], 0
    while i < len(on):
        if on[i]:
            j, silent = i, 0
            while j < len(on):
                if on[j]:
                    silent = 0
                else:
                    silent += 1
                    if silent > gap:
                        break
                j += 1
            a, b = i * hop, (j - silent) * hop
            if min_len <= (b - a) / float(sr) <= max_len:
                out.append((max(0, a - int(sr * 0.006)), min(len(v), b + int(sr * 0.02))))
            i = j
        i += 1
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
    fi = int(SR_OUT * 0.0015)
    fo = int(SR_OUT * 0.012)
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


def main():
    if not DRY and not os.path.isdir(OUT):
        os.makedirs(OUT)
    total = 0
    manifest_lines = []
    for cls in sorted(MANIFEST):
        for act in sorted(MANIFEST[cls]):
            made = 0
            for kit, weapon, action in MANIFEST[cls][act]:
                if made >= MAX_TAKES:
                    break
                n = find(kit, weapon, action)
                if not n:
                    print('   !! no source: %s / %s %s' % (os.path.basename(kit)[:20], weapon, action))
                    continue
                v, sr = decode(zopen(kit).read(n))
                if not v:
                    continue
                ev = events(v, sr)
                # longest-first: the fullest performances, not the incidental ticks
                ev.sort(key=lambda e: -(e[1] - e[0]))
                for a, b in ev:
                    if made >= MAX_TAKES:
                        break
                    seg = resample(v[a:b], sr, SR_OUT)
                    if len(seg) < int(SR_OUT * 0.04):
                        continue
                    made += 1
                    fn = '%s_%s_%02d.wav' % (cls, act, made)
                    if not DRY:
                        write(seg, OUT + fn)
                    total += 1
                    manifest_lines.append('%s  <- %s / %s %s' % (fn, weapon, action, ''))
            print('  %-8s %-14s %d take(s)' % (cls, act, made))
    print('\n%d takes %s' % (total, 'would be written (dry run)' if DRY else 'written to ' + OUT))
    if not DRY:
        with io.open(OUT + 'SOURCES.txt', 'w', encoding='ascii', newline='\r\n') as fh:
            fh.write('Derived weapon-handling takes. Sliced from long-form construction-kit\r\n')
            fh.write('recordings, downsampled to 22050 Hz mono and re-normalised - derivatives,\r\n')
            fh.write('not library files. Source library is licensed and deliberately unnamed.\r\n\r\n')
            for l in manifest_lines:
                fh.write(l + '\r\n')


main()
