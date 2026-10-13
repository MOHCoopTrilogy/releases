"""The side-magazine HOLD tried offline before it is baked: the eye's picture of the settled aim (and the left side) for
a list of roll / out / add values of sidehold.HOLDS[key] - is the magazine (drum) seen past the hand, is the thumb on
the eye's side of the neck?

    cd smg/assets; IRONSIGHT_EXTRA_PAKS=<overlay> python ../tools/holdtry.py mp40_mp18 <out.jpg> --roll 0,-60,-90 [--out 0.85] [--add x,y,z] [--yaw 0] [--side] [--w 640] [--template clip[:frame]]
Each value set is baked into a scratch root (only the `charge` row = the aim pose); nothing under assets is touched.
"""
import sys, os, argparse, tempfile, json, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main():
    from PIL import Image, ImageDraw
    ap = argparse.ArgumentParser()
    ap.add_argument('key'); ap.add_argument('out_jpg')
    ap.add_argument('--roll', default='0'); ap.add_argument('--out', default=None); ap.add_argument('--add', default=None)
    ap.add_argument('--yaw', default=None); ap.add_argument('--side', action='store_true'); ap.add_argument('--w', type=int, default=640)
    ap.add_argument('--cols', type=int, default=3); ap.add_argument('--sight', default=None)
    a = ap.parse_args()
    import sidehold as SH
    import sideview as SV
    SB = SH.SB
    h = SH.HOLDS[a.key]
    if a.out is not None:
        h['out'] = float(a.out)
    if a.add is not None:
        h['add'] = tuple(float(x) for x in a.add.split(','))
    if a.yaw is not None:
        h['yaw'] = float(a.yaw)
    g = SB.GUNS[a.key]
    rx = os.path.join(HERE, 'rows_extra.json')
    keep = open(rx, 'rb').read()
    tmp = tempfile.mkdtemp(prefix='holdtry_')
    ims = []
    try:
        for roll in [float(x) for x in a.roll.split(',')]:
            h['roll'] = roll
            SH.bake(a.key, tmp, only=['charge'])
            p = os.path.join(tmp, 'models', 'human', 'animation', h['vdir'].replace('/', os.sep), 'coop_%s_charge.skc' % a.key)
            c = SB.R.load(p)
            corr = SV.corr_of(p, g['sight'])
            ps = SV.panels(c, c.numFrames - 1, g['sight'], corr, 'idle', a.w, only_eye=not a.side)
            for k, im in enumerate(ps[:2] if a.side else ps[:1]):
                ImageDraw.Draw(im).text((4, 4), 'roll %.0f out %.2f add %s' % (roll, h['out'], h['add']), fill=(0, 0, 0))
                ims.append(im)
    finally:
        open(rx, 'wb').write(keep)          # sidehold.bake rewrites rows_extra.json: put it back as it was
        shutil.rmtree(tmp, ignore_errors=True)
    W, Hh = ims[0].size
    cols = min(a.cols, len(ims))
    S = Image.new('RGB', (W * cols, Hh * ((len(ims) + cols - 1) // cols)), 'white')
    for k, im in enumerate(ims):
        S.paste(im, ((k % cols) * W, (k // cols) * Hh))
    S.save(a.out_jpg, quality=88)
    print(a.out_jpg, S.size)


if __name__ == '__main__':
    main()
