#!/usr/bin/env python
"""
psx_vb_extract.py - decode the PSX Medal of Honor .VB sound banks to WAV, and split them into
individual effects.

WHAT A .VB IS
    Raw PlayStation SPU-ADPCM: 16-byte blocks, byte0 = (shift | filter<<4), byte1 = flags,
    bytes 2..15 = 28 packed nibbles -> 28 samples. 49 distinct banks, ~160 MB, two per level.

WHY IT SPLITS ON SILENCE RATHER THAN ON THE SAMPLE INDEX
    A normal VAG bank ends each sample with the loop-end flag (byte1 & 0x01), and a .VH header
    lists the sample offsets. This disc has NO .VH anywhere, and the loop-end flags are almost
    entirely absent (0-2 per bank) - so there is no index to cut on. What there IS, reliably, is
    digital silence between effects, because SPU-ADPCM encodes a run of zeroes as blocks that
    decode to exactly 0. Splitting on those runs recovers the individual effects without needing
    the missing table. It is a heuristic: an effect with a long internal gap will split in two,
    and two effects butted together with no gap will come out as one. Both are visible in the
    output rather than silent, which is the point.

USAGE
    python docs/tools/psx_vb_extract.py --out "G:\\PSX_MOH_SFX" [--rate 22050] [--limit N]
    python docs/tools/psx_vb_extract.py --out ... --one M1_1.VB      # test a single bank
"""
import argparse, os, struct, sys, wave

BIN_DEFAULT = r"F:\PS3 Backup\Medal of Honor (USA).bin"
RAW, USER, UOFF = 2352, 2048, 24
F0 = [0.0, 0.9375, 1.796875, 1.53125, 1.90625]
F1 = [0.0, 0.0, -0.8125, -0.859375, -0.9375]


def spu_decode(data):
    """SPU-ADPCM -> list of int16. Kept tight; this runs over ~160 MB."""
    out = []
    ap = out.append
    o1 = o2 = 0.0
    n = len(data) - 15
    i = 0
    while i < n:
        b0 = data[i]
        shift = b0 & 0x0F
        filt = (b0 >> 4) & 0x0F
        if filt > 4:
            filt = 0
        if shift > 12:
            shift = 9
        f0 = F0[filt]
        f1 = F1[filt]
        sh = 12 - shift
        j = i + 2
        for k in range(14):
            byte = data[j + k]
            nib = byte & 0x0F
            s = nib - 16 if nib > 7 else nib
            v = (s << sh) + f0 * o1 + f1 * o2
            if v > 32767.0:
                v = 32767.0
            elif v < -32768.0:
                v = -32768.0
            ap(int(v)); o2 = o1; o1 = v
            nib = (byte >> 4) & 0x0F
            s = nib - 16 if nib > 7 else nib
            v = (s << sh) + f0 * o1 + f1 * o2
            if v > 32767.0:
                v = 32767.0
            elif v < -32768.0:
                v = -32768.0
            ap(int(v)); o2 = o1; o1 = v
        i += 16
    return out


def write_wav(path, samples, rate):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(struct.pack('<%dh' % len(samples), *samples))


def split_on_silence(sig, rate, thresh=180, min_gap_ms=120, min_clip_ms=90):
    """Return [(start,end)] of non-silent runs."""
    gap = int(rate * min_gap_ms / 1000.0)
    minc = int(rate * min_clip_ms / 1000.0)
    runs, start, quiet = [], None, 0
    for i, v in enumerate(sig):
        if -thresh < v < thresh:
            quiet += 1
            if start is not None and quiet >= gap:
                e = i - quiet
                if e - start >= minc:
                    runs.append((start, e))
                start = None
        else:
            if start is None:
                start = max(0, i - int(rate * 0.005))   # 5 ms pre-roll so the attack survives
            quiet = 0
    if start is not None and len(sig) - start >= minc:
        runs.append((start, len(sig)))
    return runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", default=BIN_DEFAULT)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rate", type=int, default=22050)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--one", default="")
    ap.add_argument("--whole", action="store_true", help="also write the undivided bank")
    a = ap.parse_args()

    f = open(a.bin, 'rb')

    def user(n):
        f.seek(n * RAW + UOFF); return f.read(USER)

    def readdir(lba, length):
        buf = b''.join(user(lba + i) for i in range((length + USER - 1) // USER))
        out, off = [], 0
        while off < length:
            rl = buf[off]
            if rl == 0:
                off = (off // USER + 1) * USER; continue
            rec = buf[off:off + rl]
            out.append((rec[33:33 + rec[32]], struct.unpack_from('<I', rec, 2)[0],
                        struct.unpack_from('<I', rec, 10)[0], rec[25]))
            off += rl
        return out

    VBS = []
    def walk(lba, length, path=""):
        for name, elba, elen, flags in readdir(lba, length):
            if name in (b'\x00', b'\x01'):
                continue
            nm = name.decode('latin-1').split(';')[0]
            if flags & 0x02:
                walk(elba, elen, path + "/" + nm)
            elif nm.upper().endswith('.VB'):
                VBS.append((path + "/" + nm, elba, elen))

    pvd = user(16); root = pvd[156:190]
    walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0])
    if a.one:
        VBS = [v for v in VBS if os.path.basename(v[0]).upper() == a.one.upper()]
    if a.limit:
        VBS = VBS[:a.limit]

    os.makedirs(a.out, exist_ok=True)
    total_clips = 0
    print("%-28s %9s %7s %9s" % ("BANK", "seconds", "clips", "written"))
    for path, lba, size in VBS:
        data = b''.join(user(lba + i) for i in range((size + USER - 1) // USER))[:size]
        sig = spu_decode(data)
        if not sig:
            continue
        base = os.path.basename(path).rsplit('.', 1)[0].lower()
        d = os.path.join(a.out, base)
        os.makedirs(d, exist_ok=True)
        if a.whole:
            write_wav(os.path.join(d, "_whole_%s.wav" % base), sig, a.rate)
        runs = split_on_silence(sig, a.rate)
        n = 0
        for idx, (s, e) in enumerate(runs, 1):
            seg = sig[s:e]
            pk = max(abs(x) for x in seg) if seg else 0
            if pk < 400:
                continue
            write_wav(os.path.join(d, "%s_%03d.wav" % (base, idx)), seg, a.rate)
            n += 1
        total_clips += n
        print("%-28s %9.1f %7d %9s" % (base, len(sig) / float(a.rate), n, d))
    print("\n%d clips from %d banks -> %s" % (total_clips, len(VBS), a.out))


if __name__ == "__main__":
    sys.exit(main())
