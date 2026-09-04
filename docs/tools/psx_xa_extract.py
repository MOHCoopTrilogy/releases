#!/usr/bin/env python
"""
psx_xa_extract.py - pull the music and speech out of a PlayStation BIN (raw 2352-byte sectors).

WHY
    The original Medal of Honor (PSX) keeps its briefing narration and its score inside .STR
    files - MDEC video with CD-XA ADPCM audio interleaved a sector at a time. The score and the
    voice work are in there at 37800 Hz stereo, which is better than anything the PC games ship.
    This decodes the XA sectors to plain WAV so the mod can use them, the same way the Frontline
    PS3 extraction was done.

WHAT IT DOES
    1. Parses the ISO9660 tree out of the image (Mode 2, user data at sector offset 24).
    2. For each requested file, walks its sectors and keeps only the ones whose subheader submode
       has the AUDIO bit (0x04) set - the rest are MDEC video and are skipped.
    3. Decodes CD-XA 4-bit ADPCM to 16-bit PCM and writes a RIFF WAV.

THE SECTOR LAYOUT, because getting this wrong yields plausible noise rather than an error:
    2352 = 12 sync + 4 header + 8 subheader + 2324 data + 4 EDC
    subheader[2] = submode: 0x04 AUDIO, 0x08 DATA, 0x02 VIDEO, 0x20 form2, 0x40 real-time
    subheader[3] = coding : bits0-1 mono/stereo, bits2-3 37800/18900Hz, bits4-5 4bit/8bit
    The 2324-byte audio area is 18 sound groups of 128 bytes: 16 bytes of block params then
    112 bytes of packed nibbles. Params are stored TWICE (bytes 0-3 mirror 4-7, 8-11 mirror
    12-15); the second copy is the one to read.  For 4-bit stereo the 8 blocks per group
    alternate left/right.

USAGE
    python docs/tools/psx_xa_extract.py --list
    python docs/tools/psx_xa_extract.py --all --out <dir>
    python docs/tools/psx_xa_extract.py --file /MOVIE/INTRO/MEDAL.STR --out <dir>
"""
import argparse, os, struct, sys, wave

RAW, USER, UOFF = 2352, 2048, 24

# CD-XA ADPCM filter coefficients, scaled by 64
K0 = [0.0, 0.9375, 1.796875, 1.53125]
K1 = [0.0, 0.0, -0.8125, -0.859375]


def clamp16(v):
    if v > 32767:
        return 32767
    if v < -32768:
        return -32768
    return int(v)


class Disc:
    def __init__(self, path):
        self.f = open(path, 'rb')
        self.nsec = os.path.getsize(path) // RAW

    def raw(self, n):
        self.f.seek(n * RAW)
        return self.f.read(RAW)

    def user(self, n):
        self.f.seek(n * RAW + UOFF)
        return self.f.read(USER)

    def tree(self):
        pvd = self.user(16)
        if pvd[1:6] != b'CD001':
            raise SystemExit("not an ISO9660 Mode 2 image (no CD001 at sector 16)")
        root = pvd[156:190]
        files = []
        self._walk(struct.unpack_from('<I', root, 2)[0],
                   struct.unpack_from('<I', root, 10)[0], "", files)
        return files

    def _readdir(self, lba, length):
        buf = b''.join(self.user(lba + i) for i in range((length + USER - 1) // USER))
        out, off = [], 0
        while off < length:
            rl = buf[off]
            if rl == 0:
                off = (off // USER + 1) * USER
                continue
            rec = buf[off:off + rl]
            out.append((rec[33:33 + rec[32]], struct.unpack_from('<I', rec, 2)[0],
                        struct.unpack_from('<I', rec, 10)[0], rec[25]))
            off += rl
        return out

    def _walk(self, lba, length, path, files, depth=0):
        if depth > 8:
            return
        for name, elba, elen, flags in self._readdir(lba, length):
            if name in (b'\x00', b'\x01'):
                continue
            nm = name.decode('latin-1').split(';')[0]
            if flags & 0x02:
                self._walk(elba, elen, path + "/" + nm, files, depth + 1)
            else:
                files.append((path + "/" + nm, elba, elen))


def decode_group(group, stereo, left, right, state):
    """One 128-byte sound group -> appends samples. state = [prevL, prev2L, prevR, prev2R]"""
    for blk in range(8):
        p = group[4 + blk]
        shift = p & 0x0F
        filt = (p >> 4) & 0x03
        if shift > 12:          # invalid shift: the hardware treats it as 9
            shift = 9
        ch = (blk & 1) if stereo else 0
        o1 = state[0] if ch == 0 else state[2]
        o2 = state[1] if ch == 0 else state[3]
        out = left if ch == 0 else right
        for s in range(28):
            word = struct.unpack_from('<I', group, 16 + s * 4)[0]
            nib = (word >> (blk * 4)) & 0x0F
            if nib > 7:
                nib -= 16
            v = nib << (12 - shift)
            v += K0[filt] * o1 + K1[filt] * o2
            v = clamp16(v)
            out.append(v)
            o2, o1 = o1, v
        if ch == 0:
            state[0], state[1] = o1, o2
        else:
            state[2], state[3] = o1, o2


def extract(disc, lba, nbytes, outpath):
    nsec = (nbytes + USER - 1) // USER
    left, right, state = [], [], [0.0, 0.0, 0.0, 0.0]
    stereo = None
    rate = 37800
    used = 0
    for i in range(nsec * 2):                     # STR sectors are form2; scan generously
        if lba + i >= disc.nsec:
            break
        sec = disc.raw(lba + i)
        if len(sec) < RAW:
            break
        submode, coding = sec[18], sec[19]
        if not (submode & 0x04):                  # not an audio sector
            if submode & 0x80:                    # EOF
                break
            continue
        if stereo is None:
            stereo = bool(coding & 0x03)
            rate = 18900 if ((coding >> 2) & 0x03) == 1 else 37800
            if (coding >> 4) & 0x03:
                print("   !! 8-bit XA in %s - not handled, skipping" % outpath)
                return 0
        data = sec[24:24 + 2324]
        for g in range(18):
            decode_group(data[g * 128:(g + 1) * 128], stereo, left, right, state)
        used += 1
    if not left:
        return 0
    with wave.open(outpath, 'wb') as w:
        w.setnchannels(2 if stereo else 1)
        w.setsampwidth(2)
        w.setframerate(rate)
        if stereo:
            n = min(len(left), len(right))
            inter = bytearray()
            for i in range(n):
                inter += struct.pack('<hh', left[i], right[i])
            w.writeframes(bytes(inter))
        else:
            w.writeframes(struct.pack('<%dh' % len(left), *left))
    return used


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", default=r"F:\PS3 Backup\Medal of Honor (USA).bin")
    ap.add_argument("--out", default=r"C:\mohaa-coop-dev\_psx_moh")
    ap.add_argument("--file")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--ext", default=".STR")
    a = ap.parse_args()

    disc = Disc(a.bin)
    files = disc.tree()
    if a.list:
        for p, l, s in sorted(files):
            if p.upper().endswith(a.ext.upper()):
                print("%-46s %12s  lba %d" % (p, format(s, ","), l))
        return 0

    targets = [t for t in files if (a.file and t[0].upper() == a.file.upper())
               or (a.all and t[0].upper().endswith(a.ext.upper()))]
    if not targets:
        print("no matching files")
        return 1
    os.makedirs(a.out, exist_ok=True)
    for p, lba, size in targets:
        name = p.strip("/").replace("/", "_").rsplit(".", 1)[0] + ".wav"
        dest = os.path.join(a.out, name)
        n = extract(disc, lba, size, dest)
        if n:
            secs = os.path.getsize(dest) / 4 / 37800.0
            print("  %-40s <- %5d audio sectors  %6.1f s  %s" %
                  (name, n, secs, format(os.path.getsize(dest), ",")))
        else:
            print("  %-40s <- no audio sectors" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
