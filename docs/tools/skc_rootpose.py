#!/usr/bin/env python3
"""
Dump (and optionally neutralise) the ROOT-BONE POSE inside a MOHAA .skc animation.

WHY THIS EXISTS (2026-08-23, bug-2085). Three armory helmets - Brit Beret, German Beret, Soviet
Seaman Hat - render but sit off the player's head. The helmet system's own history says exactly why
this happens and it is not the mesh: a JT_POSROT root bone's placement comes from the idle SKC
CHANNELS ("<bone> pos" / "<bone> rot"), not from the skd base data. The US helmet hit this in
July - its 1-frame idle carried rot = (-0.7071, 0, 0, 0.7071), a -90 degree X rotation that silently
pre-rotated the transplanted geometry - and the fix was to patch those frame values to an identity
quaternion. These three point at their own retail .skc (which is correct for loading), and those
carry whatever pose the hat had on its ORIGINAL character rather than an identity at the head bone.

    python docs/tools/skc_rootpose.py <file.skc>            # dump channels + frame 0 values
    python docs/tools/skc_rootpose.py <file.skc> --identity <out.skc>

Format per code/tools/md5_2_skX/skx_format.h:
    skcHeader_t = 48 bytes: ident, version, flags, ofsEnd, frameTime, totalDelta[3],
                            totalAngleDelta, numChannels, ofsChannels, numFrames
    frames follow the header, skcFrame_t = 48 bytes each, each with ofsValues
    channel NAMES live at ofsChannels, 32 bytes each
"""
import io
import struct
import sys

HDR = 48
FRAME = 48
NAMELEN = 32


def load(p):
    return bytearray(io.open(p, 'rb').read())


def parse(b):
    ident, ver, flags, ofsEnd, ftime = struct.unpack_from('<4siiif', b, 0)
    tdx, tdy, tdz, tad, nch, ofsCh, nfr = struct.unpack_from('<ffffiii', b, 20)
    names = []
    for i in range(nch):
        raw = bytes(b[ofsCh + i * NAMELEN: ofsCh + (i + 1) * NAMELEN])
        names.append(raw.split(b'\0')[0].decode('latin-1'))
    frames = []
    for f in range(nfr):
        off = HDR + f * FRAME
        ofsValues = struct.unpack_from('<i', b, off + 44)[0]
        frames.append(off + ofsValues)
    return {'ident': ident, 'ver': ver, 'nch': nch, 'ofsCh': ofsCh, 'nfr': nfr,
            'names': names, 'framevals': frames}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    p = sys.argv[1]
    b = load(p)
    m = parse(b)
    print('%s' % p)
    print('  ident=%s ver=%d channels=%d frames=%d' % (m['ident'], m['ver'], m['nch'], m['nfr']))
    if not m['nfr']:
        print('  no frames')
        return 0
    base = m['framevals'][0]
    off = base
    for i, nm in enumerate(m['names']):
        low = nm.lower()
        n = 4 if low.endswith('rot') else (4 if low.endswith('pos') else 4)
        vals = struct.unpack_from('<%df' % n, b, off)
        print('    %-28s @%-8d %s' % (nm, off, ' '.join('%.4f' % v for v in vals)))
        off += n * 4

    if '--identity' in sys.argv:
        out = sys.argv[sys.argv.index('--identity') + 1]
        off = base
        for nm in m['names']:
            low = nm.lower()
            if low.endswith('rot'):
                struct.pack_into('<4f', b, off, 0.0, 0.0, 0.0, 1.0)
            elif low.endswith('pos'):
                struct.pack_into('<4f', b, off, 0.0, 0.0, 0.0, 0.0)
            off += 16
        io.open(out, 'wb').write(bytes(b))
        print('  -> wrote %s with an identity root pose' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
